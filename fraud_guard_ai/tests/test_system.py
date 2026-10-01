import unittest
import os
import tempfile
from pathlib import Path
import numpy as np

# Set environment
os.environ['FLASK_ENV'] = 'testing'

from app import create_app
from database.database import db
from database.models import User, DetectionHistory, Alert, Setting, ActivityLog, Report
from services.system_monitor import SystemMonitor
from services.report_generator import ReportGenerator
from services.detector_engine import FraudDetectorEngine

class FraudGuardSystemTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Create test users
        self.admin = User(username='testadmin', email='testadmin@eye.ai', full_name='Test Admin', role='admin')
        self.admin.set_password('adminpass123')
        db.session.add(self.admin)
        
        self.guard = User(username='testguard', email='testguard@eye.ai', full_name='Test Guard', role='guard')
        self.guard.set_password('guardpass123')
        db.session.add(self.guard)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_health_api(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('system', data)

    def test_auth_success_and_logout(self):
        res = self.login('testadmin', 'adminpass123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Surveillance Command Dashboard', res.data)
        
        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'Secure Access', res_logout.data)

    def test_auth_invalid_password(self):
        res = self.login('testadmin', 'wrongpassword')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid username or password', res.data)

    def test_unauthenticated_redirect(self):
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_system_monitor_metrics(self):
        metrics = SystemMonitor.get_system_metrics()
        self.assertIn('cpu_pct', metrics)
        self.assertIn('ram_pct', metrics)
        self.assertIn('disk_free_gb', metrics)

    def test_detector_engine_synthetic_frame(self):
        engine = FraudDetectorEngine()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        annotated, telemetry = engine.analyze_frame(frame)
        self.assertEqual(annotated.shape, (480, 640, 3))
        self.assertIn('activity', telemetry)
        self.assertIn('risk_level', telemetry)
        self.assertIn('confidence', telemetry)

    def test_report_generator_pdf_and_excel(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / 'test_report.pdf'
            xlsx_path = Path(tmpdir) / 'test_report.xlsx'
            
            inc = DetectionHistory(
                camera='CAM-01',
                object_class='theft',
                confidence=0.95,
                risk_level='CRITICAL',
                status='Confirmed'
            )
            db.session.add(inc)
            db.session.commit()
            
            res_pdf = ReportGenerator.generate_pdf_report(
                "Test Daily Audit", "2026-09-10", [inc],
                {'total': 1, 'critical': 1, 'high': 0, 'confirmed': 1, 'avg_conf': 95.0},
                pdf_path
            )
            self.assertTrue(res_pdf)
            self.assertTrue(pdf_path.exists())
            
            res_xlsx = ReportGenerator.generate_excel_report(
                "Test Daily Audit", "2026-09-10", [inc],
                {'total': 1, 'critical': 1, 'high': 0, 'confirmed': 1, 'avg_conf': 95.0},
                xlsx_path
            )
            self.assertTrue(res_xlsx)
            self.assertTrue(xlsx_path.exists())

    def test_alerts_acknowledge_api(self):
        self.login('testadmin', 'adminpass123')
        alert = Alert(priority='HIGH', message='Suspicious movement flagged', acknowledged=False)
        db.session.add(alert)
        db.session.commit()
        
        res = self.client.post(f'/api/alerts/acknowledge/{alert.id}')
        self.assertEqual(res.status_code, 200)
        
        updated = Alert.query.get(alert.id)
        self.assertTrue(updated.acknowledged)

    def test_admin_employee_management(self):
        self.login('testadmin', 'adminpass123')
        # Create new employee
        res = self.client.post('/api/employees', json={
            'username': 'newguard',
            'email': 'newguard@eye.ai',
            'full_name': 'New Guard Officer',
            'role': 'guard',
            'password': 'password123'
        })
        self.assertEqual(res.status_code, 200)
        created = User.query.filter_by(username='newguard').first()
        self.assertIsNotNone(created)

if __name__ == '__main__':
    unittest.main()
