import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database module before importing app
sys.modules['database'] = MagicMock()
from database import Database

# Mock the database instance in app
from app import app, login

class TestPasswordSecurityFix(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.db')
    def test_legacy_plain_text_login_and_migration(self, mock_db):
        """
        Verify that a user with a plain text password can still login (fallback),
        and that their password is automatically migrated to a hash.
        """
        mock_user = {
            'id': 1,
            'User_Code': 'USR001',
            'Password': 'secret',
            'User_Name': 'admin'
        }

        def side_effect(query, params=None, commit=False):
            if "SELECT id, User_Code, Password FROM Login_Table" in query:
                return [mock_user]
            return []

        mock_db.execute_query.side_effect = side_effect
        mock_db.last_error = None

        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'secret'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Incorrect password.", response.data.decode('utf-8'))

        update_called = False
        for call in mock_db.execute_query.call_args_list:
            args, _ = call
            query = args[0]
            if "UPDATE Login_Table SET Password =" in query:
                update_called = True
                break

        self.assertTrue(update_called, "Password migration UPDATE not found")
        self.assertIn("Login successful. Your password security has been upgraded.", response.data.decode('utf-8'))

    @patch('app.db')
    def test_hashed_password_login(self, mock_db):
        """
        Verify that a user with a hashed password can login.
        """
        hashed_pw = generate_password_hash('secret')
        mock_user = {
            'id': 2,
            'User_Code': 'USR002',
            'Password': hashed_pw,
            'User_Name': 'user2'
        }

        def side_effect(query, params=None, commit=False):
            if "SELECT id, User_Code, Password FROM Login_Table" in query:
                return [mock_user]
            return []

        mock_db.execute_query.side_effect = side_effect
        mock_db.last_error = None

        response = self.client.post('/login', data={
            'username': 'user2',
            'password': 'secret'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Incorrect password.", response.data.decode('utf-8'))

        update_called = False
        for call in mock_db.execute_query.call_args_list:
            args, _ = call
            query = args[0]
            if "UPDATE Login_Table SET Password =" in query:
                update_called = True
                break

        self.assertFalse(update_called, "Migration UPDATE should not be called for already hashed password")

    @patch('app.db')
    def test_incorrect_password(self, mock_db):
        """
        Verify that an incorrect password fails for hashed user.
        """
        hashed_pw = generate_password_hash('secret')
        mock_user = {
            'id': 2,
            'User_Code': 'USR002',
            'Password': hashed_pw,
            'User_Name': 'user2'
        }

        def side_effect(query, params=None, commit=False):
            if "SELECT id, User_Code, Password FROM Login_Table" in query:
                return [mock_user]
            return []

        mock_db.execute_query.side_effect = side_effect

        response = self.client.post('/login', data={
            'username': 'user2',
            'password': 'wrong_password'
        }, follow_redirects=True)

        self.assertIn("Incorrect password.", response.data.decode('utf-8'))

    @patch('app.db')
    def test_create_user_hashes_password(self, mock_db):
        """
        Verify that creating a new user hashes the password.
        """
        # Ensure execute_query returns harmless results
        mock_db.execute_query.return_value = []
        # Ensure conn.cursor().lastrowid works for returning ID
        mock_db.get_connection.return_value.cursor.return_value.lastrowid = 100

        # Patch session and check_permission
        with patch('app.session', dict(user_id='ADM001', user_pk=1)):
            with patch('app.check_permission', return_value=True):

                # IMPORTANT: mock_db needs to be the same object used by app
                # Since we patched 'app.db' in the decorator, it should be.

                response = self.client.post('/admin/users/add', data={
                    'username': 'newuser',
                    'password': 'newpassword',
                    'confirm_password': 'newpassword',
                    'mobile': '123',
                    'email': 'a@a.com'
                }, follow_redirects=True)

                # Check for Flash message success
                self.assertIn('User newuser created successfully.', response.data.decode('utf-8'))

                # Find the INSERT call via the cursor execute since app uses connection.cursor() for transaction
                # execute_query is not used for transaction blocks in app.py for add_new_user

                # We need to inspect the cursor mock
                # mock_db.get_connection() -> connection mock
                # connection mock .cursor() -> cursor mock
                cursor_mock = mock_db.get_connection.return_value.cursor.return_value

                insert_called = False
                for call in cursor_mock.execute.call_args_list:
                    args, _ = call
                    query = args[0]
                    params = args[1] if len(args) > 1 else None

                    if "INSERT INTO Login_Table" in query:
                        insert_called = True
                        stored_pw = params[1] # Password is 2nd param
                        self.assertNotEqual(stored_pw, 'newpassword')
                        self.assertTrue(stored_pw.startswith('scrypt:') or stored_pw.startswith('pbkdf2:'), "Password should be hashed")
                        break

                self.assertTrue(insert_called, "INSERT query not found on cursor")

if __name__ == '__main__':
    unittest.main()
