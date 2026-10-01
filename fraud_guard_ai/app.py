import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from config import config_by_name, Config
from database.database import db
from database.models import User, DetectionHistory, Alert, Setting, ActivityLog, Report
from routes import (
    auth_bp, dashboard_bp, live_bp, upload_bp,
    history_bp, alerts_bp, analytics_bp, reports_bp,
    employees_bp, settings_bp, profile_bp, api_bp
)
from services.video_service import VideoService
from services.detector_engine import FraudDetectorEngine

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this security module.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_name='production'):
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, Config))
    
    # Initialize storage directories
    Config.init_app(app)
    
    # Initialize DB & Login
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(live_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)
    
    # Template context processors & globals
    app.jinja_env.globals['int'] = int
    app.jinja_env.globals['round'] = round
    
    @app.context_processor
    def inject_global_vars():
        theme = Setting.get_value('theme', 'light')
        alert_sound = Setting.get_value('alert_sound', 'true') == 'true'
        unread_alerts_count = Alert.query.filter_by(acknowledged=False).count() if db.engine else 0
        critical_unread = Alert.query.filter_by(acknowledged=False, priority='CRITICAL').count() if db.engine else 0
        return {
            'app_theme': theme,
            'alert_sound_enabled': alert_sound,
            'unread_alerts_count': unread_alerts_count,
            'has_critical_alert': critical_unread > 0,
            'now': datetime.utcnow()
        }
        
    # Error Handlers
    @app.errorhandler(403)
    def forbidden_page(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_page(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error_page(e):
        return render_template('errors/500.html'), 500
        
    # Database initialization & default seeding
    with app.app_context():
        db.create_all()
        seed_initial_data(app)
        
        # Initialize Detection & Video Engine
        detector = FraudDetectorEngine(weights_dir=app.config['WEIGHTS_FOLDER'])
        video_service = VideoService.get_instance(app=app, detector=detector)
        
    return app

def seed_initial_data(app):
    """Seeds default accounts, configuration, and demonstration records."""
    # 1. Admin User
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@eyematrix.ai',
            full_name='System Administrator',
            role='admin',
            status='active'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("[FraudGuardAI] Created default administrator: admin / admin123")

    # 2. Guard User
    guard = User.query.filter_by(username='guard').first()
    if not guard:
        guard = User(
            username='guard',
            email='security@eyematrix.ai',
            full_name='Duty Security Officer',
            role='guard',
            status='active'
        )
        guard.set_password('guard123')
        db.session.add(guard)
        print("[FraudGuardAI] Created default guard: guard / guard123")

    # 3. Default Settings
    default_settings = {
        'detection_sensitivity': 'medium',
        'default_camera': '0',
        'alert_sound': 'true',
        'desktop_notifications': 'true',
        'theme': 'light',
        'language': 'en',
        'storage_retention_days': '30'
    }
    for k, v in default_settings.items():
        if not Setting.query.filter_by(key=k).first():
            db.session.add(Setting(key=k, value=v))
            
    # 4. Realistic Demo Incidents if database is newly created
    if DetectionHistory.query.count() == 0:
        print("[FraudGuardAI] Seeding realistic demonstration surveillance events...")
        cameras = ['CAM-01 (Store Front)', 'CAM-02 (Electronics Aisle)', 'CAM-03 (Cosmetics Counter)', 'CAM-04 (Exit Checkout)']
        classes = [
            ('theft', 'CRITICAL', 0.96, 'Subject concealed high-value fragrance item in coat pocket', 'Confirmed'),
            ('theft', 'CRITICAL', 0.92, 'Merchandise placed directly into personal backpack without scanning', 'Confirmed'),
            ('suspicious', 'HIGH', 0.78, 'Prolonged loitering and looking at ceiling cameras near luxury displays', 'Investigating'),
            ('suspicious', 'MEDIUM', 0.65, 'Frequent switching of product tags observed', 'Investigating'),
            ('theft', 'HIGH', 0.88, 'Rapid exit evasion through disabled emergency door', 'Confirmed'),
            ('suspicious', 'LOW', 0.52, 'Multiple shoppers crowding cashier counter during shift handover', 'Resolved')
        ]
        
        now = datetime.utcnow()
        for idx, (cls_name, r_level, conf, note, status) in enumerate(classes):
            time_offset = now - timedelta(days=random.randint(0, 6), hours=random.randint(1, 14), minutes=random.randint(5, 55))
            cam = random.choice(cameras)
            inc = DetectionHistory(
                timestamp=time_offset,
                camera=cam,
                object_class=cls_name,
                confidence=conf,
                risk_level=r_level,
                status=status,
                image_path=None,
                source='Live Camera',
                details=f'{{"reasons": ["{note}"], "recommended_action": "Security team dispatched to {cam}."}}'
            )
            db.session.add(inc)
            db.session.flush()
            
            if r_level in ['CRITICAL', 'HIGH']:
                db.session.add(Alert(
                    detection_id=inc.id,
                    priority=r_level,
                    message=f"{cls_name.upper()} flagged in {cam}: {note}",
                    acknowledged=(status == 'Resolved'),
                    created_at=time_offset
                ))
                
        db.session.add(ActivityLog(
            user_id=None,
            action='SYSTEM_INITIALIZED',
            details='Database and seed intelligence verified successfully',
            timestamp=now
        ))

    db.session.commit()

# Expose WSGI application
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    print(f"\n=======================================================")
    print(f"  FRAUD GUARD AI — EYE MATRIX SECURITY PLATFORM")
    print(f"  Running on http://{host}:{port}")
    print(f"  Default Admin: admin / admin123")
    print(f"  Default Guard: guard / guard123")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=False)
