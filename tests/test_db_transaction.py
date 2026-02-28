import unittest
from unittest.mock import MagicMock, patch
import sys
from contextlib import contextmanager

# 1. Create a dummy mysql module structure
mock_mysql = MagicMock()
mock_mysql_connector = MagicMock()
mock_mysql.connector = mock_mysql_connector

# Mock mysql.connector.Error to be a real exception type
class MockError(Exception):
    pass
mock_mysql_connector.Error = MockError

# 2. Inject it into sys.modules
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql_connector

# Now we can safely import database
from database import Database

class TestDatabaseTransaction(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_mysql_connector.reset_mock()
        # IMPORTANT: Clear side_effect from previous tests
        mock_mysql_connector.connect.side_effect = None

        self.db = Database({'user': 'test'})
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Patch connect to return our mock connection
        mock_mysql_connector.connect.return_value = self.mock_conn

    def test_transaction_success(self):
        """Test commit is called on success."""
        with self.db.transaction_cursor() as cursor:
            cursor.execute("SELECT 1")

        mock_mysql_connector.connect.assert_called()
        self.mock_conn.cursor.assert_called()
        self.mock_conn.start_transaction.assert_called_once()
        self.mock_cursor.execute.assert_called_with("SELECT 1")
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.rollback.assert_not_called()
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_transaction_exception(self):
        """Test rollback is called on exception."""
        with self.assertRaises(ValueError):
            with self.db.transaction_cursor() as cursor:
                cursor.execute("SELECT 1")
                raise ValueError("Boom")

        self.mock_conn.start_transaction.assert_called_once()
        self.mock_conn.commit.assert_not_called()
        self.mock_conn.rollback.assert_called_once()
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_transaction_connection_failure(self):
        """Test handling when get_connection fails."""
        mock_mysql_connector.connect.side_effect = MockError("Connection Failed")

        # When get_connection raises Error, it is caught in get_connection and returns None.
        # Then transaction_cursor raises Exception("Failed to connect...")

        with self.assertRaises(Exception) as cm:
            with self.db.transaction_cursor() as cursor:
                pass
        self.assertIn("Failed to connect", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
