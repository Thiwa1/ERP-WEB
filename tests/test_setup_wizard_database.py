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

class TestSetupWizardDatabase(unittest.TestCase):

    def setUp(self):
        self.config = {
            'app_db_name': 'test_db',
            'app_user': 'test_user',
            'app_pass': 'test_pass'
        }
        self.mock_cursor = MagicMock()

    def test_setup_database_and_user_success(self):
        """Test database and user creation when no errors occur."""
        setup_wizard.setup_database_and_user(self.config, self.mock_cursor)

        # Verify exact sequence of execute calls
        expected_calls = [
            call("CREATE DATABASE IF NOT EXISTS `test_db`"),
            call("CREATE USER IF NOT EXISTS 'test_user'@'%' IDENTIFIED BY 'test_pass'"),
            call("GRANT ALL PRIVILEGES ON `test_db`.* TO 'test_user'@'%'"),
            call("FLUSH PRIVILEGES")
        ]
        self.mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_cursor.execute.call_count, 4)

    def test_setup_database_and_user_user_exists(self):
        """Test fallback to ALTER USER if user creation fails with mysql.connector.Error."""
        # Set up a side effect to raise an error only on the CREATE USER statement
        def execute_side_effect(query, *args, **kwargs):
            if query.startswith("CREATE USER IF NOT EXISTS"):
                raise mock_mysql.connector.Error("User already exists")
            return None

        self.mock_cursor.execute.side_effect = execute_side_effect

        setup_wizard.setup_database_and_user(self.config, self.mock_cursor)

        # Verify that ALTER USER was called instead of failing
        expected_calls = [
            call("CREATE DATABASE IF NOT EXISTS `test_db`"),
            call("CREATE USER IF NOT EXISTS 'test_user'@'%' IDENTIFIED BY 'test_pass'"),
            call("ALTER USER 'test_user'@'%' IDENTIFIED BY 'test_pass'"),
            call("GRANT ALL PRIVILEGES ON `test_db`.* TO 'test_user'@'%'"),
            call("FLUSH PRIVILEGES")
        ]
        self.mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_cursor.execute.call_count, 5)

if __name__ == '__main__':
    unittest.main()
