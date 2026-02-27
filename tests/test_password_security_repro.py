import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database module before importing app
sys.modules['database'] = MagicMock()
from database import Database

# Mock the database instance in app
# We need to import app now
from app import app, login

class TestPasswordSecurity(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.db')
    def test_vulnerable_plain_text_login(self, mock_db):
        """
        Verify the current vulnerability: A plain text password allows login.
        """
        # Mock database response for user lookup
        # Simulate a user with plain text password 'secret'
        mock_user = {
            'id': 1,
            'User_Code': 'USR001',
            'Password': 'secret',
            'User_Name': 'admin'
        }

        # When execute_query is called, return the mock user
        mock_db.execute_query.return_value = [mock_user]
        mock_db.last_error = None

        # Attempt login with the plain text password
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'secret'
        }, follow_redirects=True)

        # Check if login succeeded (redirects to index or shows success)
        # In the vulnerable code, this should SUCCEED
        # A successful login redirects to index

        # We can check if session has user_id or if we are on index page
        # But mocking session inside client test is tricky without checking final URL or content
        # If login fails, it flashes 'Incorrect password.' or 'User not found.'

        response_text = response.data.decode('utf-8')

        # If vulnerable, we expect NOT to see "Incorrect password"
        self.assertNotIn("Incorrect password.", response_text)
        self.assertNotIn("User not found.", response_text)

        # And we expect to be redirected to index (status code 200 after follow_redirects)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
