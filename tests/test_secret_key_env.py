import sys
from unittest.mock import MagicMock
import os
import unittest

# Add parent directory to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock flask and mysql.connector
flask_mock = MagicMock()
sys.modules['flask'] = flask_mock

mysql_mock = MagicMock()
sys.modules['mysql.connector'] = mysql_mock
sys.modules['mysql'] = MagicMock()

class TestSecretKeyEnv(unittest.TestCase):
    def test_secret_key_from_env(self):
        test_key = "my_super_secret_test_key"
        os.environ['SECRET_KEY'] = test_key

        # Set up mocks before importing app
        sys.modules['jinja2'] = MagicMock()
        sys.modules['num2words'] = MagicMock()
        sys.modules['dotenv'] = MagicMock()
        sys.modules['PyPDF2'] = MagicMock()
        sys.modules['werkzeug'] = MagicMock()
        sys.modules['werkzeug.security'] = MagicMock()

        # We need to reload app to pick up the env var change because
        # app.secret_key is set at module level
        if 'app' in sys.modules:
            del sys.modules['app']

        import app

        print(f"Testing with SECRET_KEY env var: {test_key}")
        print(f"app.secret_key: {app.app.secret_key}")

        self.assertEqual(app.app.secret_key, test_key, "app.secret_key should match the environment variable")

if __name__ == '__main__':
    unittest.main()
