import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import tests.mock_env
except ImportError:
    pass

sys.modules['database'] = MagicMock()

class TestPasswordSecurity(unittest.TestCase):
    def setUp(self):
        import app
        self.app = app
        self.app.app.config['TESTING'] = True
        self.app.app.config['WTF_CSRF_ENABLED'] = False

        self.app.master_db = MagicMock()
        self.app.master_db.execute_query.return_value = [] # Force fallback to legacy login
        self.app.db = MagicMock()

        import flask
        flask.flash = MagicMock()

    def test_legacy_plain_text_login_migrates(self):
        mock_user = {
            'id': 1,
            'User_Code': 'USR001',
            'Password': 'secret',
            'User_Name': 'admin'
        }
        self.app.db.execute_query.return_value = [mock_user]
        self.app.db.last_error = None

        import flask
        flask.request.method = 'POST'
        flask.request.form = {'username': 'admin', 'password': 'secret'}

        self.app.session = {}

        response = self.app.login()

        update_calls = [c for c in self.app.db.execute_query.call_args_list if len(c[0]) > 0 and "UPDATE Login_Table SET Password = %s" in c[0][0]]
        self.assertTrue(len(update_calls) > 0, "Expected password migration UPDATE query to be called for legacy password.")
        self.assertEqual(self.app.session.get('username'), 'admin')

    def test_secure_hashed_password_login(self):
        from werkzeug.security import generate_password_hash
        hashed_pw = generate_password_hash('secure_password')

        mock_user = {
            'id': 1,
            'User_Code': 'USR001',
            'Password': hashed_pw,
            'User_Name': 'admin'
        }
        self.app.db.execute_query.return_value = [mock_user]
        self.app.db.last_error = None

        import flask
        flask.request.method = 'POST'
        flask.request.form = {'username': 'admin', 'password': 'secure_password'}

        self.app.session = {}

        response = self.app.login()

        update_calls = [c for c in self.app.db.execute_query.call_args_list if len(c[0]) > 0 and "UPDATE Login_Table SET Password = %s" in c[0][0]]
        self.assertEqual(len(update_calls), 0, "No migration should occur for already hashed passwords.")
        self.assertEqual(self.app.session.get('username'), 'admin')

if __name__ == '__main__':
    unittest.main()
