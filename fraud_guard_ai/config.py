import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base Configuration for Fraud Guard AI (EyeMatrix AI)"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fraudguard-dev-secret-key-964281')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI', 
        f'sqlite:///{BASE_DIR / "fraud_guard.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Paths
    BASE_DIR = BASE_DIR
    UPLOAD_FOLDER = BASE_DIR / 'data' / 'uploads'
    EVIDENCE_FOLDER = BASE_DIR / 'static' / 'evidence'
    REPORTS_FOLDER = BASE_DIR / 'data' / 'reports'
    WEIGHTS_FOLDER = BASE_DIR / 'models' / 'weights'
    
    # App Settings
    MAX_CONTENT_LENGTH = 250 * 1024 * 1024  # 250 MB max video upload
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'jpg', 'jpeg', 'png'}
    
    # AI Engine Defaults
    DEFAULT_CONFIDENCE = float(os.environ.get('DEFAULT_CONFIDENCE_THRESHOLD', 0.55))
    DEFAULT_IOU = float(os.environ.get('DEFAULT_IOU_THRESHOLD', 0.45))
    DEFAULT_SENSITIVITY = os.environ.get('DETECTION_SENSITIVITY', 'medium')
    
    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    @classmethod
    def init_app(cls, app):
        """Ensure all storage directories exist."""
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.EVIDENCE_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.WEIGHTS_FOLDER.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
