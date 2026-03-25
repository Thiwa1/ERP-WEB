import sys
import unittest
from unittest.mock import MagicMock, call

# Mock mysql and mysql.connector before importing setup_wizard
mock_mysql = MagicMock()
class MockMySQLError(Exception):
    pass
mock_mysql.connector.Error = MockMySQLError
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

import setup_wizard

class TestSetupWizard(unittest.TestCase):

    def test_write_env_file(self):
        import tempfile
        import os

        config = {
            'root_host': 'test_host',
            'app_user': 'test_app_user',
            'app_pass': 'test_app_pass',
            'app_db_name': 'test_db_name'
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                setup_wizard.write_env_file(config)
                self.assertTrue(os.path.exists('.env'))
                with open('.env', 'r') as f:
                    content = f.read()
                self.assertIn('DB_HOST=test_host', content)
                self.assertIn('DB_USER=test_app_user', content)
                self.assertIn('DB_PASSWORD=test_app_pass', content)
                self.assertIn('DB_NAME=test_db_name', content)
            finally:
                os.chdir(old_cwd)

if __name__ == '__main__':
    unittest.main()
