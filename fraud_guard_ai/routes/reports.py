import os
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, send_file, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from database.database import db
from database.models import Report, DetectionHistory, ActivityLog
from services.report_generator import ReportGenerator

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('reports.html', reports=reports)

@reports_bp.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    data = request.get_json() or {}
    report_type = data.get('type', 'Daily Report')
    now = datetime.utcnow()
    
    if report_type == 'Daily Report':
        start_date = now - timedelta(days=1)
        period_str = now.strftime('%Y-%m-%d')
    elif report_type == 'Weekly Report':
        start_date = now - timedelta(days=7)
        period_str = f"{(now - timedelta(days=7)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"
    else:
        start_date = now - timedelta(days=30)
        period_str = f"{(now - timedelta(days=30)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"
        
    incidents = DetectionHistory.query.filter(DetectionHistory.timestamp >= start_date).order_by(DetectionHistory.timestamp.desc()).all()
    
    total_count = len(incidents)
    critical_count = sum(1 for i in incidents if i.risk_level == 'CRITICAL')
    high_count = sum(1 for i in incidents if i.risk_level == 'HIGH')
    confirmed_count = sum(1 for i in incidents if i.status == 'Confirmed')
    avg_conf = (sum(i.confidence for i in incidents) / total_count * 100) if total_count > 0 else 95.0
    
    summary_stats = {
        'total': total_count,
        'critical': critical_count,
        'high': high_count,
        'confirmed': confirmed_count,
        'avg_conf': avg_conf
    }
    
    reports_dir = Path(current_app.config['REPORTS_FOLDER'])
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    ts = int(now.timestamp())
    title = f"{report_type} — {now.strftime('%b %d, %Y')}"
    pdf_filename = f"report_{ts}.pdf"
    excel_filename = f"report_{ts}.xlsx"
    
    pdf_path = reports_dir / pdf_filename
    excel_path = reports_dir / excel_filename
    
    # Generate both formats
    ReportGenerator.generate_pdf_report(title, period_str, incidents, summary_stats, pdf_path)
    ReportGenerator.generate_excel_report(title, period_str, incidents, summary_stats, excel_path)
    
    # Save Report record to DB
    rep = Report(
        title=title,
        type=report_type,
        period=period_str,
        generated_by=current_user.full_name or current_user.username,
        file_path=pdf_filename,
        format='pdf',
        total_incidents=total_count,
        critical_count=critical_count
    )
    db.session.add(rep)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='REPORT_GENERATED',
        details=f"Generated {report_type} for period {period_str}"
    ))
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'report_id': rep.id,
        'title': title,
        'pdf_url': url_for('reports.download_report', report_id=rep.id, fmt='pdf'),
        'excel_url': url_for('reports.download_report', report_id=rep.id, fmt='xlsx')
    })

@reports_bp.route('/reports/download/<int:report_id>')
@login_required
def download_report(report_id):
    rep = Report.query.get_or_404(report_id)
    fmt = request.args.get('fmt', 'pdf').lower()
    reports_dir = Path(current_app.config['REPORTS_FOLDER'])
    
    base_stem = rep.file_path.rsplit('.', 1)[0]
    filename = f"{base_stem}.{fmt}"
    file_path = reports_dir / filename
    
    if not file_path.exists():
        # Fallback to whatever exists
        file_path = reports_dir / rep.file_path
        
    mimetype = 'application/pdf' if fmt == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return send_file(str(file_path), as_attachment=True, download_name=f"FraudGuard_{rep.title.replace(' ', '_')}.{fmt}", mimetype=mimetype)

@reports_bp.route('/reports/view/<int:report_id>')
@login_required
def view_report(report_id):
    rep = Report.query.get_or_404(report_id)
    return render_template('report_view.html', report=rep)
