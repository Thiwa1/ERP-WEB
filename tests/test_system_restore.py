import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import sys
import io

# Mock Flask and mysql.connector before importing app
sys.modules['flask'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql'] = MagicMock()

# Mock app module dependencies
mock_flask = MagicMock()
app_mock = MagicMock()
app_mock.config = {}
app_mock.context_processor = MagicMock()
app_mock.template_filter = MagicMock()
app_mock.route = MagicMock()
app_mock.before_request = MagicMock()

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

# Import app
import app as app_module

class TestSystemRestore(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.mock_request = MagicMock()
        app_module.request = self.mock_request

        self.mock_session = MagicMock()
        app_module.session = self.mock_session
        self.mock_session.get.return_value = 1
        self.mock_session.__contains__.return_value = True

        app_module.flash = MagicMock()
        app_module.redirect = MagicMock()
        app_module.url_for = MagicMock(return_value='/index')
        app_module.render_template = MagicMock(return_value='Template rendered')

    def test_restore_get_request(self):
        self.mock_request.method = 'GET'

        response = app_module.system_restore()

        app_module.render_template.assert_called_with('system_restore.html')
        self.assertEqual(response, 'Template rendered')

    def test_restore_post_no_file_part(self):
        self.mock_request.method = 'POST'
        self.mock_request.files = {}
        self.mock_request.url = '/system_restore'

        app_module.system_restore()

        app_module.flash.assert_called_with('No file part', 'danger')
        app_module.redirect.assert_called_with('/system_restore')

    def test_restore_post_empty_filename(self):
        self.mock_request.method = 'POST'
        mock_file = MagicMock()
        mock_file.filename = ''
        self.mock_request.files = {'backup_file': mock_file}
        self.mock_request.url = '/system_restore'

        app_module.system_restore()

        app_module.flash.assert_called_with('No selected file', 'danger')
        app_module.redirect.assert_called_with('/system_restore')

    def test_restore_post_invalid_extension(self):
        self.mock_request.method = 'POST'
        mock_file = MagicMock()
        mock_file.filename = 'backup.txt'
        self.mock_request.files = {'backup_file': mock_file}
        self.mock_request.url = '/system_restore'

        app_module.system_restore()

        app_module.flash.assert_called_with('Invalid file format. Please upload a .sql file.', 'danger')
        app_module.redirect.assert_called_with('/system_restore')

    @patch('shutil.which')
    def test_restore_post_success(self, mock_which):
        # Mocking to allow the happy path
        self.mock_request.method = 'POST'
        mock_file = MagicMock()
        mock_file.filename = 'backup.sql'
        mock_file.read.return_value = b'DROP TABLE users;'
        self.mock_request.files = {'backup_file': mock_file}

        mock_which.return_value = '/usr/bin/mysql'
        app_module.get_session_db_name = MagicMock(return_value='test_db')
        app_module.is_safe_db_name = MagicMock(return_value=True)

        with patch('subprocess.Popen') as mock_popen:
            process_mock = MagicMock()
            process_mock.communicate.return_value = (b'', b'')
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            with patch.dict(app_module.db_config, {'user': 'root', 'host': 'localhost', 'database': 'test_db', 'password': 'pass'}):
                app_module.system_restore()

                mock_popen.assert_called()
                args, kwargs = mock_popen.call_args
                self.assertIn('/usr/bin/mysql', args[0])
                self.assertIn('test_db', args[0])
                app_module.flash.assert_called_with('Database restored successfully', 'success')
                app_module.redirect.assert_called_with('/index')

if __name__ == '__main__':
    unittest.main()
