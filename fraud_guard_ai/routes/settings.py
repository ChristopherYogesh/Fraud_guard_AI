from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from database.database import db
from database.models import Setting, ActivityLog
from services.video_service import VideoService

settings_bp = Blueprint('settings', __name__)

DEFAULT_SETTINGS = {
    'detection_sensitivity': 'medium',
    'default_camera': '0',
    'alert_sound': 'true',
    'desktop_notifications': 'true',
    'theme': 'light',
    'language': 'en',
    'storage_retention_days': '30'
}

@settings_bp.route('/settings')
@login_required
def index():
    settings = {}
    for k, v in DEFAULT_SETTINGS.items():
        settings[k] = Setting.get_value(k, v)
    return render_template('settings.html', settings=settings)

@settings_bp.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json() or {}
    for key, val in data.items():
        Setting.set_value(key, val)
        
    # Update video detector sensitivity if changed
    if 'detection_sensitivity' in data:
        video_service = VideoService.get_instance()
        if video_service and video_service.detector:
            video_service.detector.set_sensitivity(data['detection_sensitivity'])
            
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='SETTINGS_UPDATED',
        details=f"System settings modified by {current_user.username}"
    ))
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Settings saved successfully.'})
