from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from database.database import db
from database.models import DetectionHistory, Alert, ActivityLog
from services.system_monitor import SystemMonitor

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@dashboard_bp.route('/')
@login_required
def index():
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    # KPI 1: Today's Detections
    today_detections = DetectionHistory.query.filter(DetectionHistory.timestamp >= today_start).count()
    
    # KPI 2: Total Alerts
    total_alerts = Alert.query.count()
    
    # KPI 3: Critical Alerts
    critical_alerts = Alert.query.filter_by(priority='CRITICAL', acknowledged=False).count()
    
    # KPI 4: Threat Status
    threat_status = "CRITICAL THREAT ACTIVE" if critical_alerts > 0 else "ALL SYSTEMS SECURE"
    threat_color = "crimson" if critical_alerts > 0 else "emerald"
    
    # 7-Day Trend
    seven_days_ago = today_start - timedelta(days=6)
    daily_records = db.session.query(
        func.date(DetectionHistory.timestamp).label('day'),
        func.count(DetectionHistory.id).label('count')
    ).filter(DetectionHistory.timestamp >= seven_days_ago)\
     .group_by('day').all()
     
    day_map = {str(r.day): r.count for r in daily_records}
    labels_7d = []
    data_7d = []
    for i in range(7):
        d = (seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d')
        labels_7d.append((seven_days_ago + timedelta(days=i)).strftime('%b %d'))
        data_7d.append(day_map.get(d, 0))
        
    # Risk Distribution Doughnut
    risk_counts = db.session.query(
        DetectionHistory.risk_level,
        func.count(DetectionHistory.id)
    ).group_by(DetectionHistory.risk_level).all()
    
    risk_dict = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
    for r_level, count in risk_counts:
        if r_level in risk_dict:
            risk_dict[r_level] = count
            
    # Recent Events Table
    recent_events = DetectionHistory.query.order_by(DetectionHistory.timestamp.desc()).limit(6).all()
    
    # Activity Log
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(8).all()
    
    # System Health
    sys_metrics = SystemMonitor.get_system_metrics()
    
    return render_template(
        'dashboard.html',
        today_detections=today_detections,
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        threat_status=threat_status,
        threat_color=threat_color,
        labels_7d=labels_7d,
        data_7d=data_7d,
        risk_data=[risk_dict['LOW'], risk_dict['MEDIUM'], risk_dict['HIGH'], risk_dict['CRITICAL']],
        recent_events=recent_events,
        recent_logs=recent_logs,
        sys_metrics=sys_metrics
    )
