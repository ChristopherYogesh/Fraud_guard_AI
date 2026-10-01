from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from database.database import db
from database.models import User, ActivityLog

employees_bp = Blueprint('employees', __name__)

def admin_required(func):
    """Decorator ensuring current user has Administrator privileges."""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@employees_bp.route('/employees')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.id.asc()).all()
    return render_template('employees.html', users=users)

@employees_bp.route('/api/employees', methods=['POST'])
@login_required
@admin_required
def create_employee():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    full_name = data.get('full_name', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'guard')
    
    if not username or not email or not password or not full_name:
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': f'Username "{username}" is already taken.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': f'Email "{email}" is already registered.'}), 400
        
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        status='active'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='EMPLOYEE_CREATED',
        details=f"Created user account {username} ({role})"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'user': user.to_dict()})

@employees_bp.route('/api/employees/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    if user_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'You cannot deactivate your own account.'}), 400
    user = User.query.get_or_404(user_id)
    user.status = 'inactive' if user.status == 'active' else 'active'
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='EMPLOYEE_STATUS_CHANGED',
        details=f"User {user.username} status set to {user.status}"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'status_state': user.status})

@employees_bp.route('/api/employees/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_role(user_id):
    if user_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'You cannot change your own role.'}), 400
    data = request.get_json() or {}
    new_role = data.get('role')
    if new_role not in ['admin', 'guard']:
        return jsonify({'status': 'error', 'message': 'Invalid role specified.'}), 400
    user = User.query.get_or_404(user_id)
    user.role = new_role
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='EMPLOYEE_ROLE_CHANGED',
        details=f"User {user.username} role changed to {new_role}"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'role': new_role})

@employees_bp.route('/api/employees/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    data = request.get_json() or {}
    new_password = data.get('password')
    if not new_password or len(new_password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters.'}), 400
    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='EMPLOYEE_PASSWORD_RESET',
        details=f"Password reset for user {user.username}"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Password for {user.username} has been reset.'})

@employees_bp.route('/api/employees/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_employee(user_id):
    if user_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'You cannot delete your own account.'}), 400
    user = User.query.get_or_404(user_id)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='EMPLOYEE_DELETED',
        details=f"Account {user.username} deleted"
    ))
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'User deleted successfully.'})
