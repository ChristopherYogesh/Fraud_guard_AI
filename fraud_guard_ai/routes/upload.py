import os
import time
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import cv2
from database.database import db
from database.models import DetectionHistory, Alert, ActivityLog
from services.detector_engine import FraudDetectorEngine

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload')
@login_required
def index():
    return render_template('upload.html')

@upload_bp.route('/api/upload', methods=['POST'])
@login_required
def process_video_upload():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No video file provided in request.'}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Selected file is empty.'}), 400
        
    upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = Path(current_app.config['EVIDENCE_FOLDER'])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_prefix = int(time.time())
    safe_filename = f"{timestamp_prefix}_{file.filename.replace(' ', '_')}"
    filepath = upload_dir / safe_filename
    file.save(str(filepath))
    
    # Process video frame-by-frame
    cap = cv2.VideoCapture(str(filepath))
    if not cap.isOpened():
        return jsonify({'status': 'error', 'message': 'Could not open uploaded video file.'}), 400
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    duration_sec = round(total_frames / fps, 1) if fps > 0 else 0
    
    detector = FraudDetectorEngine()
    processed_count = 0
    threats_detected = 0
    incidents_saved = []
    
    sample_rate = max(1, int(fps / 2))  # Analyze 2 frames per second for speed and precision
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % sample_rate == 0:
            processed_count += 1
            annotated, telemetry = detector.analyze_frame(frame)
            
            if telemetry.get('threat_detected'):
                threats_detected += 1
                sec_offset = round(frame_idx / fps, 1)
                
                # Save evidence frame
                evidence_filename = f"upload_inc_{timestamp_prefix}_{frame_idx}.jpg"
                evidence_path = evidence_dir / evidence_filename
                cv2.imwrite(str(evidence_path), annotated)
                
                # Insert incident
                incident = DetectionHistory(
                    camera=f"Offline Upload: {file.filename}",
                    object_class=telemetry['activity'].lower(),
                    confidence=telemetry['confidence'],
                    risk_level=telemetry['risk_level'],
                    status='Investigating',
                    image_path=f"evidence/{evidence_filename}",
                    source='Uploaded Video',
                    details=str(telemetry)
                )
                db.session.add(incident)
                db.session.flush()
                
                # Insert Alert
                alert = Alert(
                    detection_id=incident.id,
                    priority='CRITICAL' if telemetry['risk_level'] == 'CRITICAL' else 'HIGH',
                    message=f"Uploaded video audit flagged {telemetry['activity']} at {sec_offset}s (Risk: {telemetry['risk_level']})",
                    acknowledged=False
                )
                db.session.add(alert)
                incidents_saved.append({
                    'id': incident.id,
                    'timestamp_sec': sec_offset,
                    'activity': telemetry['activity'],
                    'confidence': telemetry['confidence_pct'],
                    'risk_level': telemetry['risk_level'],
                    'thumbnail': f"/static/evidence/{evidence_filename}"
                })
                
        frame_idx += 1
        
    cap.release()
    
    # Audit log
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='VIDEO_AUDIT_PROCESSED',
        details=f"Analyzed {file.filename}: {total_frames} frames, {threats_detected} threats flagged"
    ))
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'filename': file.filename,
        'total_frames': total_frames,
        'duration_sec': duration_sec,
        'analyzed_frames': processed_count,
        'threats_detected': threats_detected,
        'incidents': incidents_saved
    })
