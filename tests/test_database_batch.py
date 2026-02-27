import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock mysql.connector since it's not available in the environment
mock_mysql = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = mock_mysql

from database import Database

class TestDatabaseBatch(unittest.TestCase):
    def setUp(self):
        self.config = {'user': 'root', 'password': '', 'host': 'localhost', 'database': 'test_db'}
        self.db = Database(self.config)

    def test_execute_transaction_n_plus_1(self):
        """
        Verify that execute_transaction calls execute N times (N+1 problem).
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock get_connection to return our mock connection
        with patch.object(self.db, 'get_connection', return_value=mock_conn):
            queries = [
                ("INSERT INTO table (col) VALUES (%s)", (1,)),
                ("INSERT INTO table (col) VALUES (%s)", (2,)),
                ("INSERT INTO table (col) VALUES (%s)", (3,))
            ]

            self.db.execute_transaction(queries)

            # Verify execute was called 3 times (once per query)
            self.assertEqual(mock_cursor.execute.call_count, 3)
            # Verify executemany was NOT called
            mock_cursor.executemany.assert_not_called()

            # Verify transaction flow
            mock_conn.start_transaction.assert_called_once()
            mock_conn.commit.assert_called_once()

    def test_execute_batch_optimization(self):
        """
        Verify that execute_batch calls executemany exactly once.
        """
        if not hasattr(self.db, 'execute_batch'):
            self.skipTest("execute_batch not implemented yet")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock get_connection to return our mock connection
        with patch.object(self.db, 'get_connection', return_value=mock_conn):
            query = "INSERT INTO table (col) VALUES (%s)"
            params_list = [(1,), (2,), (3,)]

            self.db.execute_batch(query, params_list)

            # Verify executemany was called exactly once
            mock_cursor.executemany.assert_called_once_with(query, params_list)

            # Verify execute was NOT called (except potentially for setup, but strictly not for the batch)
            # Depending on implementation, execute shouldn't be called for the batch itself
            mock_cursor.execute.assert_not_called()

            # Verify transaction flow
            mock_conn.start_transaction.assert_called_once()
            mock_conn.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
