from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .database import db

class User(UserMixin, db.Model):
    """User account model supporting Administrator and Security/Guard roles."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='guard')  # 'admin' or 'guard'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active' or 'inactive'
    avatar = db.Column(db.String(255), default='default_avatar.png')
    last_login = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_admin(self):
        return self.role == 'admin'
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'status': self.status,
            'avatar': self.avatar,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class DetectionHistory(db.Model):
    """Records every logged theft or suspicious activity incident."""
    __tablename__ = 'detection_history'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    camera = db.Column(db.String(64), default='CAM-01 (Main Aisle)')
    object_class = db.Column(db.String(64), nullable=False)  # e.g., 'theft', 'suspicious', 'concealment'
    confidence = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(20), nullable=False, index=True)  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    status = db.Column(db.String(30), default='Investigating')  # 'Investigating', 'Confirmed', 'Dismissed', 'Resolved'
    image_path = db.Column(db.String(255), nullable=True)  # Path to saved evidence frame
    source = db.Column(db.String(30), default='Live Camera')  # 'Live Camera' or 'Uploaded Video'
    details = db.Column(db.Text, default='{}')  # JSON string of bounding boxes, activity prob, etc.
    
    # Relationship
    alerts = db.relationship('Alert', backref='detection', cascade='all, delete-orphan', lazy=True)
    
    @property
    def parsed_details(self):
        try:
            return json.loads(self.details or '{}')
        except Exception:
            return {}
            
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'date': self.timestamp.strftime('%Y-%m-%d'),
            'time': self.timestamp.strftime('%H:%M:%S'),
            'camera': self.camera,
            'object_class': self.object_class,
            'confidence': round(self.confidence, 4),
            'confidence_pct': f"{int(self.confidence * 100)}%",
            'risk_level': self.risk_level,
            'status': self.status,
            'image_path': self.image_path,
            'source': self.source,
            'details': self.parsed_details
        }

class Alert(db.Model):
    """Prioritised real-time security alerts generated from detections."""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detection_history.id', ondelete='CASCADE'), nullable=True)
    priority = db.Column(db.String(20), nullable=False, index=True)  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    message = db.Column(db.String(255), nullable=False)
    acknowledged = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'detection_id': self.detection_id,
            'priority': self.priority,
            'message': self.message,
            'acknowledged': self.acknowledged,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': self.get_time_ago()
        }
        
    def get_time_ago(self):
        diff = datetime.utcnow() - self.created_at
        seconds = diff.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        else:
            return f"{int(seconds // 86400)}d ago"

class Report(db.Model):
    """Daily, Weekly, and Monthly security and compliance reports."""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # 'Daily Report', 'Weekly Report', 'Monthly Report'
    period = db.Column(db.String(60), nullable=False)  # e.g., '2026-09-03 to 2026-09-10'
    generated_by = db.Column(db.String(64), default='System Automated')
    file_path = db.Column(db.String(255), nullable=False)
    format = db.Column(db.String(10), default='pdf')  # 'pdf' or 'xlsx'
    total_incidents = db.Column(db.Integer, default=0)
    critical_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'period': self.period,
            'generated_by': self.generated_by,
            'file_path': self.file_path,
            'format': self.format,
            'total_incidents': self.total_incidents,
            'critical_count': self.critical_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Setting(db.Model):
    """System configuration key-value store."""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    
    @classmethod
    def get_value(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        return item.value if item else default

    @classmethod
    def set_value(cls, key, value):
        item = cls.query.filter_by(key=key).first()
        if item:
            item.value = str(value)
        else:
            item = cls(key=key, value=str(value))
            db.session.add(item)
        db.session.commit()

class ActivityLog(db.Model):
    """Audit trail of user actions and automated security events."""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref=db.backref('activity_logs', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'System',
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
