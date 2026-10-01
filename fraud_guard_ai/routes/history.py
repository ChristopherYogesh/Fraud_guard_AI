import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, Response, send_file
from flask_login import login_required, current_user
from database.database import db
from database.models import DetectionHistory, ActivityLog

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    risk_filter = request.args.get('risk', '').strip().upper()
    status_filter = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    query = DetectionHistory.query
    
    if search:
        query = query.filter(
            (DetectionHistory.camera.ilike(f'%{search}%')) |
            (DetectionHistory.object_class.ilike(f'%{search}%')) |
            (DetectionHistory.risk_level.ilike(f'%{search}%'))
        )
    if risk_filter and risk_filter != 'ALL':
        query = query.filter_by(risk_level=risk_filter)
    if status_filter and status_filter != 'ALL':
        query = query.filter_by(status=status_filter)
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d')
            d_end = datetime(d.year, d.month, d.day, 23, 59, 59)
            query = query.filter(DetectionHistory.timestamp >= d, DetectionHistory.timestamp <= d_end)
        except Exception:
            pass
            
    pagination = query.order_by(DetectionHistory.timestamp.desc()).paginate(page=page, per_page=12, error_out=False)
    
    return render_template(
        'history.html',
        incidents=pagination.items,
        pagination=pagination,
        search=search,
        risk_filter=risk_filter,
        status_filter=status_filter,
        date_filter=date_filter
    )

@history_bp.route('/api/history/<int:incident_id>')
@login_required
def get_incident(incident_id):
    inc = DetectionHistory.query.get_or_404(incident_id)
    return jsonify(inc.to_dict())

@history_bp.route('/api/history/<int:incident_id>/status', methods=['POST'])
@login_required
def update_status(incident_id):
    inc = DetectionHistory.query.get_or_404(incident_id)
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status in ['Investigating', 'Confirmed', 'Dismissed', 'Resolved']:
        inc.status = new_status
        db.session.add(ActivityLog(
            user_id=current_user.id,
            action='INCIDENT_STATUS_UPDATED',
            details=f"Incident #{inc.id} status changed to {new_status}"
        ))
        db.session.commit()
        return jsonify({'status': 'success', 'new_status': new_status})
    return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

@history_bp.route('/api/history/<int:incident_id>', methods=['DELETE'])
@login_required
def delete_incident(incident_id):
    inc = DetectionHistory.query.get_or_404(incident_id)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='INCIDENT_DELETED',
        details=f"Incident #{incident_id} removed by {current_user.username}"
    ))
    db.session.delete(inc)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Incident #{incident_id} deleted.'})

@history_bp.route('/history/export/csv')
@login_required
def export_csv():
    incidents = DetectionHistory.query.order_by(DetectionHistory.timestamp.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Incident ID', 'Timestamp', 'Camera', 'Class', 'Confidence', 'Risk Level', 'Status', 'Source'])
    for inc in incidents:
        cw.writerow([
            inc.id,
            inc.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            inc.camera,
            inc.object_class,
            inc.confidence,
            inc.risk_level,
            inc.status,
            inc.source
        ])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=fraud_guard_history_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
