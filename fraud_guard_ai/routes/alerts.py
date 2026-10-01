from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database.database import db
from database.models import Alert, ActivityLog

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/alerts')
@login_required
def index():
    priority_filter = request.args.get('priority', '').strip().upper()
    ack_filter = request.args.get('ack', '').strip()
    
    query = Alert.query
    if priority_filter and priority_filter != 'ALL':
        query = query.filter_by(priority=priority_filter)
    if ack_filter == 'unack':
        query = query.filter_by(acknowledged=False)
        
    alerts = query.order_by(Alert.created_at.desc()).all()
    
    # Counts
    total_count = Alert.query.count()
    critical_count = Alert.query.filter_by(priority='CRITICAL').count()
    high_count = Alert.query.filter_by(priority='HIGH').count()
    unack_count = Alert.query.filter_by(acknowledged=False).count()
    
    return render_template(
        'alerts.html',
        alerts=alerts,
        total_count=total_count,
        critical_count=critical_count,
        high_count=high_count,
        unack_count=unack_count,
        priority_filter=priority_filter
    )

@alerts_bp.route('/api/alerts/acknowledge/<int:alert_id>', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.acknowledged = True
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='ALERT_ACKNOWLEDGED',
        details=f"Alert #{alert_id} acknowledged"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'alert_id': alert_id})

@alerts_bp.route('/api/alerts/clear-all', methods=['POST'])
@login_required
def clear_all_alerts():
    Alert.query.filter_by(acknowledged=False).update({'acknowledged': True})
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='ALL_ALERTS_CLEARED',
        details="All pending alerts marked as acknowledged"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'All alerts marked as acknowledged.'})

@alerts_bp.route('/api/alerts/unread')
@login_required
def unread_count():
    unack = Alert.query.filter_by(acknowledged=False).order_by(Alert.created_at.desc()).limit(5).all()
    count = Alert.query.filter_by(acknowledged=False).count()
    critical_unack = Alert.query.filter_by(acknowledged=False, priority='CRITICAL').count()
    return jsonify({
        'count': count,
        'has_critical': critical_unack > 0,
        'recent': [a.to_dict() for a in unack]
    })
