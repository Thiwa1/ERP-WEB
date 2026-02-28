import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add app directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock flask and mysql.connector to allow app import
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

import importlib

class TestSecurityFix(unittest.TestCase):
    def setUp(self):
        # Clear DB_PASSWORD from environment before each test
        if 'DB_PASSWORD' in os.environ:
            del os.environ['DB_PASSWORD']

        # Remove app from sys.modules to force reload
        if 'app' in sys.modules:
            del sys.modules['app']

    def tearDown(self):
        # Clean up environment
        if 'DB_PASSWORD' in os.environ:
            del os.environ['DB_PASSWORD']

    def test_db_password_default_none(self):
        """Test that db_config['password'] is None when DB_PASSWORD is not set."""
        import app
        importlib.reload(app)
        self.assertIsNone(app.db_config.get('password'))

    def test_db_password_set(self):
        """Test that db_config['password'] takes the value from environment."""
        os.environ['DB_PASSWORD'] = 'secure_password'
        import app
        importlib.reload(app)
        self.assertEqual(app.db_config.get('password'), 'secure_password')

    def test_db_password_empty_string(self):
        """Test that db_config['password'] can be explicitly set to empty string."""
        os.environ['DB_PASSWORD'] = ''
        import app
        importlib.reload(app)
        self.assertEqual(app.db_config.get('password'), '')

if __name__ == '__main__':
    unittest.main()
