import os
import time
import threading
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np

class VideoService:
    """
    Manages live camera capture, synthetic test patterns, frame processing,
    Motion-JPEG streaming, and incident persistence.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls, app=None, detector=None):
        if cls._instance is None:
            cls._instance = cls(app, detector)
        return cls._instance
        
    def __init__(self, app=None, detector=None):
        self.app = app
        self.detector = detector
        self.camera_index = 0
        self.cap = None
        self.is_running = False
        self.detection_paused = False
        self.lock = threading.Lock()
        
        self.current_frame = None
        self.annotated_frame = None
        self.latest_telemetry = {
            'activity': 'Normal',
            'risk_level': 'LOW',
            'confidence': 0.95,
            'confidence_pct': '95%',
            'objects_detected': ['person'],
            'detections_count': 1,
            'inference_time_ms': 12.4,
            'model': 'YOLOv8n + Activity-CNN',
            'frame_id': 0,
            'fps': 0.0,
            'threat_detected': False,
            'reasons': ['Standard shopper movement observed'],
            'recommended_action': 'Standard surveillance active.'
        }
        
        self.last_incident_time = 0
        self.incident_cooldown = 6.0  # seconds between auto-saved incidents
        self.is_recording = False
        self.record_out = None
        self.simulated_mode = False
        self.simulated_counter = 0
        
        # Test images from dataset for realistic simulation when camera isn't attached
        self.demo_images = []
        self._load_demo_images()

    def _load_demo_images(self):
        """Loads a small carousel of dataset images for offline demo streaming if no camera is available."""
        dataset_dirs = [
            Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8\test\images"),
            Path(r"D:\college\mini project\dataset\Shoplifting.v1i.yolov8\valid\images")
        ]
        for d in dataset_dirs:
            if d.exists():
                for f in list(d.glob("*.jpg"))[:30]:
                    self.demo_images.append(str(f))
        print(f"[VideoService] Loaded {len(self.demo_images)} demo frames for simulated surveillance feed")

    def start_camera(self, camera_index=0):
        with self.lock:
            if self.is_running:
                return True
            self.camera_index = camera_index
            try:
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
                if not self.cap or not self.cap.isOpened():
                    print(f"[VideoService] Physical camera index {camera_index} not accessible. Engaging simulated surveillance feed.")
                    self.simulated_mode = True
                else:
                    self.simulated_mode = False
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            except Exception as e:
                print(f"[VideoService] Camera error: {e}. Defaulting to simulated mode.")
                self.simulated_mode = True
                
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            return True

    def stop_camera(self):
        with self.lock:
            self.is_running = False
            if self.cap:
                self.cap.release()
                self.cap = None
            if self.record_out:
                self.record_out.release()
                self.record_out = None
            self.is_recording = False

    def toggle_detection(self):
        self.detection_paused = not self.detection_paused
        return not self.detection_paused

    def _generate_synthetic_frame(self):
        """Generates realistic surveillance frame from local dataset or technical canvas."""
        if self.demo_images:
            idx = (self.simulated_counter // 15) % len(self.demo_images)
            img = cv2.imread(self.demo_images[idx])
            if img is not None:
                img = cv2.resize(img, (640, 480))
                # Add timestamp watermark
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(img, f"CAM-01 [STORE A-4] {ts}", (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                return img
                
        # Pure procedural fallback
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (30, 25, 20)
        # Grid lines
        for y in range(0, 480, 40):
            cv2.line(frame, (0, y), (640, y), (45, 40, 35), 1)
        for x in range(0, 640, 40):
            cv2.line(frame, (x, 0), (x, 480), (45, 40, 35), 1)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"FEED-01 (ACTIVE) {ts}", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        return frame

    def _capture_loop(self):
        """Continuous capture & detection worker thread."""
        frame_id = 0
        fps_start = time.time()
        fps_counter = 0
        current_fps = 15.0

        while self.is_running:
            raw_frame = None
            if not self.simulated_mode and self.cap and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if not ret:
                    raw_frame = self._generate_synthetic_frame()
            else:
                raw_frame = self._generate_synthetic_frame()
                self.simulated_counter += 1
                time.sleep(0.04)  # ~25 FPS pacing

            if raw_frame is None:
                time.sleep(0.05)
                continue

            frame_id += 1
            fps_counter += 1
            if time.time() - fps_start >= 1.0:
                current_fps = round(fps_counter / (time.time() - fps_start), 1)
                fps_counter = 0
                fps_start = time.time()

            # Process frame through Detector
            if self.detector and not self.detection_paused:
                annotated, telemetry = self.detector.analyze_frame(raw_frame)
            else:
                annotated = raw_frame.copy()
                telemetry = self.latest_telemetry.copy()
                telemetry['activity'] = 'Paused' if self.detection_paused else 'Normal'

            telemetry['frame_id'] = frame_id
            telemetry['fps'] = current_fps

            with self.lock:
                self.current_frame = raw_frame
                self.annotated_frame = annotated
                self.latest_telemetry = telemetry

            # Auto-save incident if threat detected and cooldown elapsed
            if telemetry.get('threat_detected') and (time.time() - self.last_incident_time > self.incident_cooldown):
                self._persist_incident(annotated, telemetry)
                self.last_incident_time = time.time()

            # Recording support
            if self.is_recording and self.record_out:
                self.record_out.write(annotated)

    def _persist_incident(self, frame, telemetry):
        """Saves threat evidence screenshot and inserts record into Database."""
        if not self.app:
            return
            
        try:
            with self.app.app_context():
                from database.database import db
                from database.models import DetectionHistory, Alert, ActivityLog
                
                # Save evidence snapshot
                evidence_dir = Path(self.app.config['EVIDENCE_FOLDER'])
                evidence_dir.mkdir(parents=True, exist_ok=True)
                filename = f"incident_{int(time.time())}_{telemetry['activity'].lower()}.jpg"
                filepath = evidence_dir / filename
                cv2.imwrite(str(filepath), frame)
                
                # Web-accessible relative path
                rel_path = f"evidence/{filename}"
                
                # Insert incident
                incident = DetectionHistory(
                    camera='CAM-01 (Store Front)',
                    object_class=telemetry['activity'].lower(),
                    confidence=telemetry['confidence'],
                    risk_level=telemetry['risk_level'],
                    status='Investigating',
                    image_path=rel_path,
                    source='Live Camera',
                    details=str(telemetry)
                )
                db.session.add(incident)
                db.session.flush()
                
                # Insert Alert
                priority_map = {
                    'CRITICAL': 'CRITICAL',
                    'HIGH': 'HIGH',
                    'MEDIUM': 'MEDIUM',
                    'LOW': 'LOW'
                }
                alert = Alert(
                    detection_id=incident.id,
                    priority=priority_map.get(telemetry['risk_level'], 'HIGH'),
                    message=f"{telemetry['activity']} detected with {telemetry['confidence_pct']} confidence in CAM-01",
                    acknowledged=False
                )
                db.session.add(alert)
                
                # Insert Activity Log
                log = ActivityLog(
                    user_id=None,
                    action="THEFT_DETECTION_ALERT",
                    details=f"Automated alert triggered: {telemetry['activity']} ({telemetry['risk_level']})"
                )
                db.session.add(log)
                db.session.commit()
                print(f"[VideoService] Saved incident #{incident.id} with alert #{alert.id}")
        except Exception as e:
            print(f"[VideoService] Error persisting incident: {e}")

    def generate_mjpeg_stream(self):
        """Yields continuous multipart JPEG stream for browser <img> tag."""
        if not self.is_running:
            self.start_camera(self.camera_index)

        while True:
            with self.lock:
                frame = self.annotated_frame
            if frame is None:
                time.sleep(0.04)
                continue

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.04)  # ~25 fps throttle for browser responsiveness

    def capture_snapshot(self):
        """Captures a snapshot frame and returns relative path."""
        with self.lock:
            frame = self.annotated_frame
        if frame is None:
            return None
            
        evidence_dir = Path(self.app.config['EVIDENCE_FOLDER'])
        evidence_dir.mkdir(parents=True, exist_ok=True)
        filename = f"snapshot_{int(time.time())}.jpg"
        filepath = evidence_dir / filename
        cv2.imwrite(str(filepath), frame)
        return f"evidence/{filename}"
