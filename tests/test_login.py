import sys
import unittest
from unittest.mock import MagicMock, patch

# --- Conditional Dependency Mocking ---
# This allows the test to run in the restricted sandbox environment (where flask/mysql are missing)
# while remaining valid and safe in a production environment (where they exist).
try:
    import flask
    import mysql.connector
    IS_SANDBOX = False
except ImportError:
    IS_SANDBOX = True

    # Mock MySQL
    mock_mysql = MagicMock()
    sys.modules['mysql'] = mock_mysql
    sys.modules['mysql.connector'] = mock_mysql

    # Mock Flask
    mock_flask = MagicMock()
    sys.modules['flask'] = mock_flask

    # Mock Flask Globals
    mock_request = MagicMock()
    mock_session = {}
    mock_flask.request = mock_request
    mock_flask.session = mock_session

    # Mock Helpers
    mock_flask.render_template = MagicMock(return_value="RENDERED_TEMPLATE")
    mock_flask.redirect = MagicMock(side_effect=lambda x: f"REDIRECT:{x}")
    mock_flask.url_for = MagicMock(side_effect=lambda x: f"/{x}")
    mock_flask.flash = MagicMock()

    # Mock Flask Application
    class MockFlaskObj:
        def __init__(self, name):
            self.config = {}
            self.secret_key = None
            self.view_functions = {}

        def route(self, rule, **options):
            def decorator(f):
                self.view_functions[rule] = f
                return f
            return decorator

        def context_processor(self, f): return f
        def template_filter(self, name=None):
            def decorator(f): return f
            return decorator
        def before_request(self, f): return f
        def run(self, **kwargs): pass

        def test_client(self):
            return MockTestClient(self)

    # Mock Test Client to simulate requests in Sandbox
    class MockTestClient:
        def __init__(self, app):
            self.app = app

        def _handle(self, method, url, data=None):
            mock_request.method = method
            mock_request.form = data or {}

            # Simple router for the purpose of this test
            # app.py defines @app.route('/login', ...)
            handler = self.app.view_functions.get(url)

            response = MagicMock()
            if handler:
                try:
                    res = handler()
                    # Flask views return string or Response.
                    # Our mocks (redirect/render) return strings.
                    response.data = str(res).encode('utf-8')
                    response.status_code = 200
                except Exception as e:
                    print(f"Handler Error: {e}")
                    response.status_code = 500
            else:
                response.status_code = 404
            return response

        def get(self, url, **kwargs):
            return self._handle('GET', url)

        def post(self, url, data=None, **kwargs):
            return self._handle('POST', url, data)

        def __enter__(self): return self
        def __exit__(self, *args): pass

    mock_flask.Flask = MockFlaskObj

# Import app after potential mocking
import app

class TestLogin(unittest.TestCase):
    def setUp(self):
        # Bypass app initialization to prevent DB connection attempts
        app.app_initialized = True
        app.app.config['TESTING'] = True
        app.app.secret_key = 'test_secret'

        self.client = app.app.test_client()

        # Patch the database object
        self.db_patcher = patch('app.db')
        self.mock_db = self.db_patcher.start()
        self.mock_db.last_error = None

        # Reset session for Sandbox (Flask handles this automatically in client)
        if IS_SANDBOX:
            app.session.clear()

    def tearDown(self):
        self.db_patcher.stop()

    def test_login_page_loads(self):
        """Test GET /login renders login template."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

        if IS_SANDBOX:
            self.assertIn(b'RENDERED_TEMPLATE', response.data)
            app.render_template.assert_called_with('login.html')
        else:
            self.assertIn(b'Login', response.data)

    def test_login_missing_credentials(self):
        """Test POST with missing credentials."""
        response = self.client.post('/login', data={'username': '', 'password': ''}, follow_redirects=True)

        if IS_SANDBOX:
            app.flash.assert_called_with('Please enter both username and password.', 'danger')
            self.assertIn(b'REDIRECT:/login', response.data)
        else:
            self.assertIn(b'Please enter both username and password.', response.data)

    def test_login_user_not_found(self):
        """Test login with non-existent user."""
        self.mock_db.execute_query.return_value = [] # Empty list = No user

        response = self.client.post('/login', data={'username': 'nobody', 'password': '123'}, follow_redirects=True)

        if IS_SANDBOX:
            app.flash.assert_called_with('User not found.', 'danger')
            self.assertIn(b'REDIRECT:/login', response.data)
        else:
            self.assertIn(b'User not found.', response.data)

    def test_login_incorrect_password(self):
        """Test login with correct username but incorrect password."""
        user = {'id': 1, 'User_Code': 'U1', 'Password': 'realpassword'}
        self.mock_db.execute_query.return_value = [user]

        response = self.client.post('/login', data={'username': 'user', 'password': 'wrong'}, follow_redirects=True)

        if IS_SANDBOX:
            app.flash.assert_called_with('Incorrect password.', 'danger')
            self.assertIn(b'REDIRECT:/login', response.data)
        else:
            self.assertIn(b'Incorrect password.', response.data)

    def test_login_success(self):
        """Test successful login."""
        user = {'id': 99, 'User_Code': 'ADMIN', 'Password': 'realpassword'}
        self.mock_db.execute_query.return_value = [user]

        with self.client:
            response = self.client.post('/login', data={'username': 'user', 'password': 'realpassword'}, follow_redirects=True)

            # Check Session
            if IS_SANDBOX:
                self.assertEqual(app.session['user_id'], 'ADMIN')
                self.assertEqual(app.session['user_pk'], 99)
                self.assertIn(b'REDIRECT:/index', response.data)
            else:
                from flask import session
                self.assertEqual(session['user_id'], 'ADMIN')
                self.assertEqual(session['user_pk'], 99)
                # Redirect usually loads index page content

    def test_login_db_error(self):
        """Test login when DB connection fails."""
        self.mock_db.execute_query.return_value = None
        self.mock_db.last_error = "Connection Refused"

        response = self.client.post('/login', data={'username': 'u', 'password': 'p'}, follow_redirects=True)

        if IS_SANDBOX:
            # Check if flash was called with a string containing the error
            args, _ = app.flash.call_args
            self.assertIn("Connection Refused", args[0])
        else:
            self.assertIn(b'Connection Refused', response.data)

if __name__ == '__main__':
    unittest.main()
