from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from database.database import db
from database.models import User, ActivityLog

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            if user.status != 'active':
                flash('Your account has been deactivated. Please contact your system administrator.', 'danger')
                return render_template('login.html')
                
            user.last_login = datetime.utcnow()
            db.session.add(ActivityLog(
                user_id=user.id,
                action='USER_LOGIN',
                details=f"Successful login from {request.remote_addr}"
            ))
            db.session.commit()
            
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    db.session.add(ActivityLog(
        user_id=current_user.id,
        action='USER_LOGOUT',
        details="User logged out"
    ))
    db.session.commit()
    logout_user()
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('auth.login'))
