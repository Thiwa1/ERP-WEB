import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# --- System-level Mocks for Flask and MySQL ---
# We need to define these BEFORE importing app.py

# 1. Mock Flask App Instance
mock_flask_app = MagicMock()
mock_flask_app.config = {}

# Define passthrough decorators
def passthrough_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

def simple_passthrough(f):
    return f

# Configure app methods to be passthrough
mock_flask_app.route = passthrough_decorator
mock_flask_app.context_processor = simple_passthrough
mock_flask_app.template_filter = passthrough_decorator
mock_flask_app.before_request = simple_passthrough

# 2. Mock Flask Module
mock_flask_module = MagicMock()
mock_flask_module.Flask.return_value = mock_flask_app
mock_flask_module.request = MagicMock()
mock_flask_module.session = {}
mock_flask_module.redirect = MagicMock()
mock_flask_module.url_for = MagicMock()
mock_flask_module.flash = MagicMock()
mock_flask_module.make_response = MagicMock()
mock_flask_module.Response = MagicMock()
mock_flask_module.stream_with_context = MagicMock()
mock_flask_module.render_template = MagicMock(return_value="")

# Apply to sys.modules
sys.modules['flask'] = mock_flask_module
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Define pass_context explicitly
def mock_pass_context(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        return args[0]
    def decorator(f):
        return f
    return decorator

# Create mock module
class MockJinja2:
    pass_context = mock_pass_context
    Environment = MagicMock()
    FileSystemLoader = MagicMock()
    select_autoescape = MagicMock()

sys.modules['jinja2'] = MockJinja2()

sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['requests'] = MagicMock()

sys.path.append('.')
os.environ['SECRET_KEY'] = 'test-secret-key-for-mock-env'

# --- Import App ---
import app as app_module

class TestSendSmsOtp(unittest.TestCase):
    def setUp(self):
        # Mock Database
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        # Backup environment variables
        self.original_user_id = os.getenv('NOTIFY_USER_ID')
        self.original_api_key = os.getenv('NOTIFY_API_KEY')
        self.original_sender_id = os.getenv('NOTIFY_SENDER_ID')

        # Clean environment variables for testing isolation
        if 'NOTIFY_USER_ID' in os.environ: del os.environ['NOTIFY_USER_ID']
        if 'NOTIFY_API_KEY' in os.environ: del os.environ['NOTIFY_API_KEY']
        if 'NOTIFY_SENDER_ID' in os.environ: del os.environ['NOTIFY_SENDER_ID']

    def tearDown(self):
        # Restore environment variables
        if self.original_user_id is not None:
            os.environ['NOTIFY_USER_ID'] = self.original_user_id
        elif 'NOTIFY_USER_ID' in os.environ:
            del os.environ['NOTIFY_USER_ID']

        if self.original_api_key is not None:
            os.environ['NOTIFY_API_KEY'] = self.original_api_key
        elif 'NOTIFY_API_KEY' in os.environ:
            del os.environ['NOTIFY_API_KEY']

        if self.original_sender_id is not None:
            os.environ['NOTIFY_SENDER_ID'] = self.original_sender_id
        elif 'NOTIFY_SENDER_ID' in os.environ:
            del os.environ['NOTIFY_SENDER_ID']

    @patch('app.requests.get')
    def test_send_sms_success_with_db_settings(self, mock_get):
        # Setup mock db to return valid settings
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # We must support context managers for connection and cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # When fetching settings from site_settings table
        mock_cursor.fetchall.return_value = [
            {'setting_key': 'sms_user_id', 'setting_value': 'DB_USER_123'},
            {'setting_key': 'sms_api_key', 'setting_value': 'DB_API_KEY_456'},
            {'setting_key': 'sms_sender_id', 'setting_value': 'DB_SENDER'}
        ]

        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success'}
        mock_response.text = '{"status": "success"}'
        mock_get.return_value = mock_response

        # Call the function
        result = app_module.send_sms_otp('0771234567', '999999')

        # Assertions
        self.assertTrue(result)

        # Verify requests.get was called with the correct parameters from the DB
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://app.notify.lk/api/v1/send")
        self.assertEqual(kwargs['params']['user_id'], 'DB_USER_123')
        self.assertEqual(kwargs['params']['api_key'], 'DB_API_KEY_456')
        self.assertEqual(kwargs['params']['sender_id'], 'DB_SENDER')
        self.assertEqual(kwargs['params']['to'], '94771234567')
        self.assertIn('999999', kwargs['params']['message'])

        # Verify it logged to the DB (second execute block)
        # 1st block was retrieving settings. 2nd block is inserting logs.
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO sms_delivery_logs" in c for c in calls))

    @patch('app.requests.get')
    def test_send_sms_fallback_env_vars(self, mock_get):
        # DB fetching fails, falling back to environment variables
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Table doesn't exist")

        os.environ['NOTIFY_USER_ID'] = 'ENV_USER_123'
        os.environ['NOTIFY_API_KEY'] = 'ENV_API_KEY_456'
        os.environ['NOTIFY_SENDER_ID'] = 'ENV_SENDER'

        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success'}
        mock_response.text = '{"status": "success"}'
        mock_get.return_value = mock_response

        # Call the function
        result = app_module.send_sms_otp('0771234567', '999999')

        # Assertions
        self.assertTrue(result)

        # Verify requests.get was called with the correct parameters from ENV
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs['params']['user_id'], 'ENV_USER_123')
        self.assertEqual(kwargs['params']['api_key'], 'ENV_API_KEY_456')
        self.assertEqual(kwargs['params']['sender_id'], 'ENV_SENDER')

    def test_send_sms_missing_credentials(self):
        # Setup mock db to return empty list (no settings)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        # Call the function (env variables are empty due to setUp)
        result = app_module.send_sms_otp('0771234567', '999999')

        # Assertions
        self.assertFalse(result)

    @patch('app.requests.get')
    def test_send_sms_api_failure(self, mock_get):
        # Setup mock db to return valid settings
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'setting_key': 'sms_user_id', 'setting_value': 'USER'},
            {'setting_key': 'sms_api_key', 'setting_value': 'API_KEY'},
            {'setting_key': 'sms_sender_id', 'setting_value': 'SENDER'}
        ]

        # Mock requests.get response for failed API
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'failed', 'message': 'Invalid credentials'}
        mock_response.text = '{"status": "failed", "message": "Invalid credentials"}'
        mock_get.return_value = mock_response

        # Call the function
        result = app_module.send_sms_otp('0771234567', '999999')

        # Assertions
        self.assertFalse(result)

        # Log to DB should still occur for the failed response
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO sms_delivery_logs" in c for c in calls))

    @patch('app.requests.get')
    def test_send_sms_request_exception(self, mock_get):
        # Setup mock db to return valid settings
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'setting_key': 'sms_user_id', 'setting_value': 'USER'},
            {'setting_key': 'sms_api_key', 'setting_value': 'API_KEY'}
        ]

        # Mock requests.get to raise an exception
        mock_get.side_effect = Exception("Connection Timeout")

        # Call the function
        result = app_module.send_sms_otp('0771234567', '999999')

        # Assertions
        self.assertFalse(result)

    @patch('app.requests.get')
    def test_send_sms_phone_formatting(self, mock_get):
        # DB fetching fails, falling back to environment variables
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = False
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Table doesn't exist")

        os.environ['NOTIFY_USER_ID'] = 'USER'
        os.environ['NOTIFY_API_KEY'] = 'API_KEY'

        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success'}
        mock_get.return_value = mock_response

        # Test various phone formats
        phone_formats = [
            ('0771234567', '94771234567'),
            ('+94771234567', '94771234567'),
            ('94771234567', '94771234567'),
            ('771234567', '94771234567'),
            (' 077-123 4567 ', '94771234567')
        ]

        for input_phone, expected_phone in phone_formats:
            app_module.send_sms_otp(input_phone, '123')
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs['params']['to'], expected_phone)


if __name__ == '__main__':
    unittest.main()
