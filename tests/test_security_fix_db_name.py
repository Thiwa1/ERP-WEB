import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock everything required to load app.py
sys.modules['flask'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

os.environ['SECRET_KEY'] = 'testkey'

import app

class TestSecurityFixDbName(unittest.TestCase):
    def test_is_safe_db_name(self):
        self.assertTrue(app.is_safe_db_name("good_db_name_123"))
        self.assertTrue(app.is_safe_db_name("DBNAME"))
        self.assertFalse(app.is_safe_db_name("bad`db`name"))
        self.assertFalse(app.is_safe_db_name("db_name; DROP TABLE users;"))
        self.assertFalse(app.is_safe_db_name("some-name")) # hyphens aren't allowed by regex

if __name__ == '__main__':
    unittest.main()
