import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock Flask and mysql.connector before importing app
sys.modules['flask'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql'] = MagicMock()

# Mock app module dependencies
mock_flask = MagicMock()
# Mock the Flask class constructor to return our app mock
app_mock = MagicMock()
app_mock.config = {}
app_mock.context_processor = MagicMock()
app_mock.template_filter = MagicMock()
app_mock.route = MagicMock()
app_mock.before_request = MagicMock()

# Important: decorators return a function that takes a function and returns a function
# so @app.template_filter('currency') means calling template_filter('currency') which returns a decorator
def mock_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

app_mock.context_processor = lambda f: f
app_mock.template_filter.side_effect = mock_decorator
app_mock.route.side_effect = mock_decorator
app_mock.before_request = lambda f: f

mock_flask.Flask.return_value = app_mock
sys.modules['flask'] = mock_flask

# Now import app
import app as app_module

class TestBackupSafety(unittest.TestCase):
    def setUp(self):
        # Mock request, session, url_for, redirect, flash, make_response
        self.mock_request = MagicMock()
        app_module.request = self.mock_request

        self.mock_session = MagicMock()
        app_module.session = self.mock_session
        self.mock_session.get.return_value = 1 # user_id/pk
        self.mock_session.__contains__.return_value = True # user_id in session

        app_module.flash = MagicMock()
        app_module.redirect = MagicMock()
        app_module.url_for = MagicMock()
        app_module.make_response = MagicMock()

    @patch('shutil.which')
    def test_backup_success(self, mock_which):
        # Mock mysqldump existence
        mock_which.return_value = '/usr/bin/mysqldump'

        # Mock subprocess
        with patch('subprocess.Popen') as mock_popen:
            process_mock = MagicMock()
            process_mock.communicate.return_value = (b'SQL DUMP CONTENT', b'')
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Setup db_config
            with patch.dict(app_module.db_config, {'user': 'root', 'host': 'localhost', 'database': 'test_db', 'password': 'pass'}):
                # Call function
                response = app_module.system_backup()

                # Verify logic
                mock_popen.assert_called()
                args = mock_popen.call_args[0][0]
                self.assertIn('mysqldump', args)

                # Check response
                app_module.make_response.assert_called_with(b'SQL DUMP CONTENT')

    @patch('shutil.which')
    def test_backup_success_with_ip_host(self, mock_which):
        # Mock mysqldump existence
        mock_which.return_value = '/usr/bin/mysqldump'

        # Mock subprocess
        with patch('subprocess.Popen') as mock_popen:
            process_mock = MagicMock()
            process_mock.communicate.return_value = (b'SQL DUMP CONTENT', b'')
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Setup db_config with IP address
            with patch.dict(app_module.db_config, {'user': 'root', 'host': '127.0.0.1', 'database': 'test_db', 'password': 'pass'}):
                # Call function
                app_module.system_backup()

                # Verify logic
                mock_popen.assert_called()
                app_module.make_response.assert_called_with(b'SQL DUMP CONTENT')

    def test_backup_invalid_config_injection(self):
        # Suspicious config
        suspicious_db = '; rm -rf /'

        with patch('subprocess.Popen') as mock_popen:
            with patch.dict(app_module.db_config, {'user': 'root', 'host': 'localhost', 'database': suspicious_db, 'password': ''}):

                # Call function
                app_module.system_backup()

                # Expectation: Currently it DOES call Popen (Vulnerable)
                # After fix: Should NOT call Popen

                mock_popen.assert_not_called()
                app_module.flash.assert_called_with('Invalid database configuration', 'danger')

    @patch('shutil.which')
    def test_backup_missing_mysqldump(self, mock_which):
        mock_which.return_value = None

        with patch('subprocess.Popen') as mock_popen:
            with patch.dict(app_module.db_config, {'user': 'root', 'host': 'localhost', 'database': 'test_db', 'password': ''}):

                app_module.system_backup()

                # This assertion checks for the specific error message we plan to add.
                app_module.flash.assert_called()
                args, _ = app_module.flash.call_args
                self.assertIn('mysqldump not found', args[0])
                mock_popen.assert_not_called()

if __name__ == '__main__':
    unittest.main()
