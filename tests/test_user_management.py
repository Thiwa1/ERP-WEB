import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock Flask and MySQL before importing app
mock_flask = MagicMock()
mock_mysql = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Define mocks for Flask objects
# Flask class
class MockFlask:
    def __init__(self, name):
        self.config = {}
        self.secret_key = 'test_key'

    def context_processor(self, f):
        return f

    def template_filter(self, name):
        def decorator(f):
            return f
        return decorator

    def route(self, rule, **options):
        def decorator(f):
            return f
        return decorator

    def before_request(self, f):
        return f

mock_flask.Flask = MockFlask
mock_flask.render_template = MagicMock(return_value="rendered_template")
mock_flask.request = MagicMock()
mock_flask.redirect = MagicMock(return_value="redirected")
mock_flask.url_for = MagicMock(return_value="url")
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.stream_with_context = MagicMock()
mock_flask.Response = MagicMock()

# Now import app
import app as app_module
from app import app
import json

class TestUserManagement(unittest.TestCase):
    def setUp(self):
        # Setup session for login check
        # Since we mock session at module level, we manipulate it there
        app_module.session = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}

        # Mock DB
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_add_new_user_success(self):
        with patch('app.check_permission', return_value=True):
            # Setup DB Mock
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Mock lastrowid for user ID (e.g., 5)
            mock_cursor.lastrowid = 5

            data = {
                'username': 'newuser',
                'password': 'password123',
                'confirm_password': 'password123',
                'mobile': '1234567890',
                'email': 'newuser@example.com'
            }

            # Approach: Invoke function directly
            with patch('app.request') as mock_request:
                mock_request.form = data
                mock_request.method = 'POST'

                # Mock redirect/url_for/flash
                with patch('app.flash') as mock_flash, \
                     patch('app.redirect') as mock_redirect, \
                     patch('app.url_for') as mock_url_for:

                    app_module.add_new_user()

                    # Verify DB Calls
                    found_insert = False
                    found_update = False
                    found_rights = False

                    for call in mock_cursor.execute.call_args_list:
                        query = call[0][0]
                        if "INSERT INTO Login_Table" in query:
                            params = call[0][1]
                            # params[1] is a hashed password, so just check username
                            if params[0] == 'newuser':
                                found_insert = True

                        if "UPDATE Login_Table SET User_Code" in query:
                            params = call[0][1]
                            if params[0] == 50005 and params[1] == 5:
                                found_update = True

                        if "INSERT INTO User_Rights" in query:
                            params = call[0][1]
                            if params[0] == 5:
                                found_rights = True

                    self.assertTrue(found_insert, "Failed to insert user into Login_Table")
                    self.assertTrue(found_update, "Failed to update User_Code")
                    self.assertTrue(found_rights, "Failed to insert default User_Rights")

                    mock_conn.commit.assert_called()
                    mock_flash.assert_called_with('User newuser created successfully.', 'success')

    def test_add_new_user_missing_fields(self):
         with patch('app.check_permission', return_value=True):
             with patch('app.request') as mock_request:
                mock_request.form = {
                    'username': '',
                    'password': 'password123',
                    'confirm_password': 'password123'
                }

                with patch('app.flash') as mock_flash, \
                     patch('app.redirect') as mock_redirect:

                    app_module.add_new_user()
                    mock_flash.assert_called_with('Username and Password are required', 'danger')

    def test_add_new_user_password_mismatch(self):
         with patch('app.check_permission', return_value=True):
             with patch('app.request') as mock_request:
                mock_request.form = {
                    'username': 'user2',
                    'password': 'password123',
                    'confirm_password': 'password456'
                }

                with patch('app.flash') as mock_flash, \
                     patch('app.redirect') as mock_redirect:

                    app_module.add_new_user()
                    mock_flash.assert_called_with('Passwords do not match', 'danger')

    def test_add_new_user_db_error(self):
        with patch('app.check_permission', return_value=True):
            # Setup DB Mock for Exception
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = Exception("DB Fail")

            with patch('app.request') as mock_request:
                mock_request.form = {
                    'username': 'user3',
                    'password': 'password123',
                    'confirm_password': 'password123'
                }

                with patch('app.flash') as mock_flash, \
                     patch('app.redirect') as mock_redirect:

                    app_module.add_new_user()

                    mock_flash.assert_called_with('Error creating user: DB Fail', 'danger')
                    mock_conn.rollback.assert_called()

if __name__ == '__main__':
    unittest.main()
