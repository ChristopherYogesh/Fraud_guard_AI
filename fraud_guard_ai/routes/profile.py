from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from database.database import db
from database.models import User, ActivityLog

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def index():
    return render_template('profile.html', user=current_user)

@profile_bp.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    
    if not full_name or not email:
        return jsonify({'status': 'error', 'message': 'Full name and email are required.'}), 400
        
    existing = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Email is already used by another account.'}), 400
        
    current_user.full_name = full_name
    current_user.email = email
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='PROFILE_UPDATED',
        details="User updated personal contact information"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Profile updated successfully.'})

@profile_bp.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    confirm_pw = data.get('confirm_password', '')
    
    if not current_user.check_password(current_pw):
        return jsonify({'status': 'error', 'message': 'Current password does not match.'}), 400
    if len(new_pw) < 6:
        return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters.'}), 400
    if new_pw != confirm_pw:
        return jsonify({'status': 'error', 'message': 'New password and confirmation do not match.'}), 400
        
    current_user.set_password(new_pw)
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='PASSWORD_CHANGED',
        details="User changed account password"
    ))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Password updated successfully.'})
