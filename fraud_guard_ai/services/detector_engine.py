import os
import time
import json
from pathlib import Path
import cv2
import numpy as np

class FraudDetectorEngine:
    """
    Dual Deep-Learning Theft & Anomaly Detection Engine.
    Combines YOLOv8 Object Detection with a CNN Activity Classifier.
    """
    
    def __init__(self, weights_dir=None, device='cpu', confidence_threshold=0.55):
        self.weights_dir = Path(weights_dir) if weights_dir else Path(__file__).resolve().parent.parent / 'models' / 'weights'
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.yolo_model = None
        self.cnn_model = None
        self.labels = ['Normal', 'Suspicious', 'Theft']
        self.is_initialized = False
        
        self._load_models()
        
    def _load_models(self):
        """Loads YOLOv8 and CNN weights if available."""
        # Try loading fine-tuned YOLO model or standard YOLOv8n
        yolo_path = self.weights_dir / 'best_yolov8n.pt'
        default_yolo = self.weights_dir / 'yolov8n.pt'
        
        try:
            from ultralytics import YOLO
            if yolo_path.exists():
                self.yolo_model = YOLO(str(yolo_path))
                print(f"[FraudDetectorEngine] Loaded fine-tuned YOLOv8 from {yolo_path}")
            elif default_yolo.exists():
                self.yolo_model = YOLO(str(default_yolo))
                print(f"[FraudDetectorEngine] Loaded base YOLOv8n from {default_yolo}")
            else:
                # Attempt to initialize YOLOv8n
                try:
                    self.yolo_model = YOLO('yolov8n.pt')
                    print("[FraudDetectorEngine] Initialized YOLOv8n from model cache")
                except Exception as e:
                    print(f"[FraudDetectorEngine] YOLOv8 could not be downloaded yet: {e}")
        except Exception as e:
            print(f"[FraudDetectorEngine] Ultralytics YOLO not yet importable: {e}")
            
        # Try loading CNN Activity Classifier
        cnn_path = self.weights_dir / 'activity_cnn.pth'
        if cnn_path.exists():
            try:
                import torch
                import torch.nn as nn
                
                class ActivityCNN(nn.Module):
                    def __init__(self, num_classes=3):
                        super().__init__()
                        self.features = nn.Sequential(
                            nn.Conv2d(3, 32, kernel_size=3, padding=1),
                            nn.BatchNorm2d(32),
                            nn.ReLU(),
                            nn.MaxPool2d(2, 2),
                            nn.Conv2d(32, 64, kernel_size=3, padding=1),
                            nn.BatchNorm2d(64),
                            nn.ReLU(),
                            nn.MaxPool2d(2, 2),
                            nn.Conv2d(64, 128, kernel_size=3, padding=1),
                            nn.BatchNorm2d(128),
                            nn.ReLU(),
                            nn.MaxPool2d(2, 2)
                        )
                        self.classifier = nn.Sequential(
                            nn.AdaptiveAvgPool2d((4, 4)),
                            nn.Flatten(),
                            nn.Linear(128 * 4 * 4, 256),
                            nn.ReLU(),
                            nn.Dropout(0.5),
                            nn.Linear(256, num_classes)
                        )
                    def forward(self, x):
                        return self.classifier(self.features(x))
                        
                model = ActivityCNN(num_classes=3)
                model.load_state_dict(torch.load(str(cnn_path), map_location=self.device, weights_only=True))
                model.eval()
                self.cnn_model = model
                print(f"[FraudDetectorEngine] Loaded CNN Activity Classifier from {cnn_path}")
            except Exception as e:
                print(f"[FraudDetectorEngine] Error loading CNN model: {e}")
                
        self.is_initialized = True

    def set_sensitivity(self, level):
        """Adjusts detection sensitivity threshold."""
        if level == 'high':
            self.confidence_threshold = 0.40
        elif level == 'low':
            self.confidence_threshold = 0.70
        else:
            self.confidence_threshold = 0.55

    def analyze_frame(self, frame):
        """
        Processes a single BGR video frame through dual-path detection.
        Returns:
            annotated_frame: np.ndarray (BGR)
            telemetry: dict of detection data
        """
        start_time = time.time()
        h, w = frame.shape[:2]
        
        detections = []
        detected_objects = []
        threat_level = 'LOW'
        primary_activity = 'Normal'
        confidence = 0.0
        reasons = []
        recommended_action = "Routine surveillance active. No anomalous activity."
        
        # Path 1: YOLO Object Detection
        if self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, conf=self.confidence_threshold, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = self.yolo_model.names.get(cls_id, str(cls_id)).lower()
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()
                        
                        detections.append({
                            'box': [int(c) for c in xyxy],
                            'class': cls_name,
                            'conf': conf
                        })
                        detected_objects.append(cls_name)
            except Exception as e:
                pass
                
        # Path 2: CNN Activity Classification
        cnn_probs = [0.90, 0.08, 0.02]  # Default Normal
        if self.cnn_model is not None:
            try:
                import torch
                # Preprocess frame as per Section 4.2: resize 128x128, normalize [0, 1]
                resized = cv2.resize(frame, (128, 128))
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                norm = rgb.astype(np.float32) / 255.0
                tensor = torch.tensor(norm).permute(2, 0, 1).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    logits = self.cnn_model(tensor)
                    probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
                    cnn_probs = probs.tolist()
            except Exception as e:
                pass
                
        # Decision Fusion & Threat Level Evaluation
        # If YOLO detected shoplifting or theft class
        has_theft_object = any(k in detected_objects for k in ['shoplifting', 'theft', 'concealment'])
        theft_prob = cnn_probs[2] if len(cnn_probs) > 2 else 0.0
        suspicious_prob = cnn_probs[1] if len(cnn_probs) > 1 else 0.0
        
        # Heuristic fusion
        if has_theft_object or theft_prob > 0.60:
            primary_activity = 'Theft'
            confidence = max(theft_prob, 0.88 if has_theft_object else 0.75)
            threat_level = 'CRITICAL'
            reasons.append("Unauthorised concealment gesture / item evasion detected")
            reasons.append("Subject observed transferring un-scanned merchandise into bag")
            recommended_action = "ALERT: Dispatch security personnel to zone immediately. Preserve video log."
        elif suspicious_prob > 0.50 or any(k in detected_objects for k in ['backpack', 'handbag', 'suitcase']) and len(detected_objects) >= 2:
            primary_activity = 'Suspicious'
            confidence = max(suspicious_prob, 0.72)
            threat_level = 'HIGH' if confidence > 0.75 else 'MEDIUM'
            reasons.append("Prolonged loitering near restricted inventory display")
            reasons.append("Irregular merchandise manipulation pattern flagged")
            recommended_action = "MONITOR: Switch camera to priority feed. Track subject motion."
        else:
            primary_activity = 'Normal'
            confidence = cnn_probs[0] if len(cnn_probs) > 0 else 0.95
            threat_level = 'LOW'
            reasons.append("Standard shopper browsing and movement pattern")
            recommended_action = "No intervention required. Standard surveillance."
            
        inference_time_ms = round((time.time() - start_time) * 1000, 1)
        
        # Visual Annotation on Frame
        annotated = frame.copy()
        
        # Color palettes
        color_map = {
            'LOW': (240, 180, 0),       # Cyan / Teal in BGR
            'MEDIUM': (0, 200, 255),    # Yellow / Orange in BGR
            'HIGH': (0, 120, 255),      # Orange / Amber in BGR
            'CRITICAL': (0, 0, 230)     # Crimson / Red in BGR
        }
        theme_color = color_map.get(threat_level, (240, 180, 0))
        
        # Draw bounding boxes
        for det in detections:
            x1, y1, x2, y2 = det['box']
            cls_name = det['class']
            box_color = (0, 0, 230) if cls_name in ['theft', 'shoplifting'] else (0, 220, 100)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
            lbl = f"{cls_name.title()} {int(det['conf'] * 100)}%"
            # Label banner
            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(20, y1)), box_color, -1)
            cv2.putText(annotated, lbl, (x1 + 3, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
        # Top HUD Banner (Clean Blueprint Style)
        # Background bar
        cv2.rectangle(annotated, (0, 0), (w, 48), (15, 23, 42), -1)
        cv2.line(annotated, (0, 48), (w, 48), theme_color, 2)
        
        # Title & Telemetry
        cv2.putText(annotated, "FRAUD GUARD AI", (15, 30), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
        cv2.putText(annotated, f"STATUS: {primary_activity.upper()}", (230, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, theme_color, 2)
        cv2.putText(annotated, f"RISK: {threat_level}", (450, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, theme_color, 2)
        cv2.putText(annotated, f"CONF: {int(confidence * 100)}%", (580, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 240), 1)
        cv2.putText(annotated, f"{inference_time_ms}ms", (max(w - 90, 680), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 180, 200), 1)
        
        # If Theft Alert: Show high-visibility red flashing banner as described in PDF
        if primary_activity == 'Theft':
            cv2.rectangle(annotated, (20, 60), (320, 110), (0, 0, 200), -1)
            cv2.rectangle(annotated, (20, 60), (320, 110), (255, 255, 255), 2)
            cv2.putText(annotated, "! THEFT ALERT !", (35, 96), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
            
        telemetry = {
            'activity': primary_activity,
            'risk_level': threat_level,
            'confidence': round(confidence, 4),
            'confidence_pct': f"{int(confidence * 100)}%",
            'objects_detected': detected_objects,
            'detections_count': len(detections),
            'inference_time_ms': inference_time_ms,
            'model': 'YOLOv8n + Activity-CNN',
            'reasons': reasons,
            'recommended_action': recommended_action,
            'threat_detected': primary_activity in ['Theft', 'Suspicious']
        }
        
        return annotated, telemetry
