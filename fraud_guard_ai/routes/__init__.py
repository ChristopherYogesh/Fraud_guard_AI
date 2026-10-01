from .auth import auth_bp
from .dashboard import dashboard_bp
from .live import live_bp
from .upload import upload_bp
from .history import history_bp
from .alerts import alerts_bp
from .analytics import analytics_bp
from .reports import reports_bp
from .employees import employees_bp
from .settings import settings_bp
from .profile import profile_bp
from .api import api_bp

__all__ = [
    'auth_bp', 'dashboard_bp', 'live_bp', 'upload_bp',
    'history_bp', 'alerts_bp', 'analytics_bp', 'reports_bp',
    'employees_bp', 'settings_bp', 'profile_bp', 'api_bp'
]
