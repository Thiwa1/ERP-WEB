import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# --- Mocking mysql.connector ---
# We use a trick here: we want `mysql.connector.Error` to be a real exception class.
# But database.py imports mysql.connector.
# So we create a mock module.

class MockMySQLModule(MagicMock):
    pass

class MockConnector(MagicMock):
    pass

class MockError(Exception):
    pass

# Create the mock structure
# mysql = MockMySQLModule()
# mysql.connector = MockConnector()
# mysql.connector.Error = MockError # This is the key: Error must be a class, not an instance (MagicMock)

# However, sys.modules replacement needs to be robust.
# If database.py does `import mysql.connector`, it looks for `mysql` package then `connector` submodule.

mock_mysql_module = MagicMock()
mock_connector_module = MagicMock()
mock_connector_module.Error = MockError
mock_mysql_module.connector = mock_connector_module

sys.modules["mysql"] = mock_mysql_module
sys.modules["mysql.connector"] = mock_connector_module

# Add parent directory to path to import database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import database
from database import Database

class TestDatabaseErrorHandling(unittest.TestCase):
    def setUp(self):
        self.config = {'user': 'test', 'password': '', 'host': 'localhost', 'database': 'test_db'}
        self.db = Database(self.config)

    def test_execute_query_rollback_on_error(self):
        """Test that rollback is called when an error occurs during commit=True"""

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        with patch.object(self.db, 'get_connection', return_value=mock_conn):
            mock_conn.cursor.return_value = mock_cursor

            # Raise MockError
            error_message = "Simulated database error"
            mock_cursor.execute.side_effect = MockError(error_message)

            # execute_query calls `except mysql.connector.Error`
            # Since `mysql.connector.Error` IS `MockError`, it should catch it.

            with self.assertRaises(MockError) as cm:
                self.db.execute_query("INSERT INTO test (col) VALUES (%s)", ('val',), commit=True)

            self.assertEqual(str(cm.exception), error_message)

            # Verify rollback
            mock_conn.rollback.assert_called_once()

            # Verify close
            mock_cursor.close.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_execute_query_no_rollback_on_select_error(self):
        """Test that rollback is NOT called for select queries (commit=False)"""

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        with patch.object(self.db, 'get_connection', return_value=mock_conn):
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = MockError("Select Error")

            with self.assertRaises(MockError):
                self.db.execute_query("SELECT * FROM test", commit=False)

            # Verify NO rollback
            mock_conn.rollback.assert_not_called()

            mock_cursor.close.assert_called_once()
            mock_conn.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
