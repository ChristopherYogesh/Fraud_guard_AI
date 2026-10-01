from flask import Blueprint, render_template, Response, jsonify, request
from flask_login import login_required
from services.video_service import VideoService
from services.system_monitor import SystemMonitor

live_bp = Blueprint('live', __name__)

@live_bp.route('/live')
@login_required
def index():
    video_service = VideoService.get_instance()
    telemetry = video_service.latest_telemetry
    sys_metrics = SystemMonitor.get_system_metrics()
    return render_template(
        'live.html',
        telemetry=telemetry,
        sys_metrics=sys_metrics,
        is_running=video_service.is_running,
        detection_paused=video_service.detection_paused
    )

@live_bp.route('/video_feed')
@login_required
def video_feed():
    video_service = VideoService.get_instance()
    return Response(
        video_service.generate_mjpeg_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@live_bp.route('/api/live/telemetry')
@login_required
def live_telemetry():
    video_service = VideoService.get_instance()
    sys_metrics = SystemMonitor.get_system_metrics()
    telemetry = video_service.latest_telemetry.copy()
    telemetry['gpu_util'] = sys_metrics.get('gpu_util_pct', 0)
    telemetry['gpu_name'] = sys_metrics.get('gpu_name', 'N/A')
    telemetry['detection_paused'] = video_service.detection_paused
    telemetry['is_running'] = video_service.is_running
    return jsonify(telemetry)

@live_bp.route('/api/live/control', methods=['POST'])
@login_required
def control():
    data = request.get_json() or {}
    action = data.get('action')
    video_service = VideoService.get_instance()
    
    if action == 'start':
        video_service.start_camera(int(data.get('camera_index', 0)))
        return jsonify({'status': 'success', 'message': 'Camera started'})
    elif action == 'stop':
        video_service.stop_camera()
        return jsonify({'status': 'success', 'message': 'Camera stopped'})
    elif action == 'toggle_pause':
        active = video_service.toggle_detection()
        return jsonify({'status': 'success', 'active': active})
    elif action == 'snapshot':
        path = video_service.capture_snapshot()
        return jsonify({'status': 'success', 'image_path': path})
    elif action == 'switch_camera':
        cam_idx = int(data.get('camera_index', 0))
        video_service.stop_camera()
        video_service.start_camera(cam_idx)
        return jsonify({'status': 'success', 'camera_index': cam_idx})
        
    return jsonify({'status': 'error', 'message': 'Unknown action'}), 400
