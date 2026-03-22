import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock mysql.connector since it's not available in the environment
mock_mysql = MagicMock()
mock_mysql_connector = MagicMock()
mock_mysql.connector = mock_mysql_connector

# Mock mysql.connector.Error to be a real exception type
class MockError(Exception):
    pass
mock_mysql_connector.Error = MockError

sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql_connector

from database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_mysql_connector.reset_mock()
        mock_mysql_connector.connect.side_effect = None

        self.config = {'user': 'root', 'password': 'password', 'host': 'localhost', 'database': 'test_db'}
        self.db = Database(self.config)

    def test_init(self):
        """Test that Database initializes correctly."""
        self.assertEqual(self.db.config, self.config)
        self.assertIsNone(self.db.last_error)
        self.assertIsNone(self.db.db_name_getter)

    def test_set_db_name_getter(self):
        """Test that set_db_name_getter sets the getter correctly."""
        def mock_getter():
            return "dynamic_db_name"

        self.db.set_db_name_getter(mock_getter)
        self.assertEqual(self.db.db_name_getter, mock_getter)
        self.assertEqual(self.db.db_name_getter(), "dynamic_db_name")

    def test_get_connection_success(self):
        """Test get_connection with static config."""
        mock_conn = MagicMock()
        mock_mysql_connector.connect.return_value = mock_conn

        conn = self.db.get_connection()

        self.assertEqual(conn, mock_conn)
        mock_mysql_connector.connect.assert_called_once_with(**self.config)

    def test_get_connection_dynamic_db(self):
        """Test get_connection uses dynamic DB name if getter is set."""
        mock_conn = MagicMock()
        mock_mysql_connector.connect.return_value = mock_conn

        def mock_getter():
            return "dynamic_db_name"
        self.db.set_db_name_getter(mock_getter)

        conn = self.db.get_connection()

        self.assertEqual(conn, mock_conn)
        expected_config = self.config.copy()
        expected_config['database'] = "dynamic_db_name"
        mock_mysql_connector.connect.assert_called_once_with(**expected_config)

    def test_get_connection_error(self):
        """Test get_connection sets last_error and returns None on error."""
        error_message = "Connection failed"
        mock_mysql_connector.connect.side_effect = MockError(error_message)

        conn = self.db.get_connection()

        self.assertIsNone(conn)
        self.assertEqual(self.db.last_error, error_message)

    def test_execute_query_select(self):
        """Test execute_query with commit=False (select query)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql_connector.connect.return_value = mock_conn

        expected_result = [{'id': 1, 'name': 'test'}]
        mock_cursor.fetchall.return_value = expected_result

        query = "SELECT * FROM table"
        params = (1,)
        result = self.db.execute_query(query, params, commit=False)

        self.assertEqual(result, expected_result)
        mock_conn.cursor.assert_called_once_with(dictionary=True)
        mock_cursor.execute.assert_called_once_with(query, params)
        mock_cursor.fetchall.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_execute_query_insert(self):
        """Test execute_query with commit=True (insert query)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql_connector.connect.return_value = mock_conn

        # Mock lastrowid as a property on the cursor mock
        type(mock_cursor).lastrowid = unittest.mock.PropertyMock(return_value=123)

        query = "INSERT INTO table (col) VALUES (%s)"
        params = (1,)
        result = self.db.execute_query(query, params, commit=True)

        self.assertEqual(result, 123)
        mock_conn.cursor.assert_called_once_with(dictionary=True)
        mock_cursor.execute.assert_called_once_with(query, params)
        mock_cursor.fetchall.assert_not_called()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_execute_query_connection_fail(self):
        """Test execute_query returns None if get_connection fails."""
        mock_mysql_connector.connect.side_effect = MockError("Connection failed")

        result = self.db.execute_query("SELECT * FROM table")

        self.assertIsNone(result)

    def test_execute_batch_success(self):
        """Test execute_batch uses executemany inside a transaction."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql_connector.connect.return_value = mock_conn

        query = "INSERT INTO table (col) VALUES (%s)"
        params_list = [(1,), (2,)]
        result = self.db.execute_batch(query, params_list)

        self.assertTrue(result)
        mock_conn.cursor.assert_called_once()
        mock_conn.start_transaction.assert_called_once()
        mock_cursor.executemany.assert_called_once_with(query, params_list)
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_execute_batch_connection_fail(self):
        """Test execute_batch returns False if get_connection fails."""
        mock_mysql_connector.connect.side_effect = MockError("Connection failed")

        result = self.db.execute_batch("INSERT INTO table (col) VALUES (%s)", [(1,)])

        self.assertFalse(result)

    def test_execute_transaction_success(self):
        """Test execute_transaction executes a list of queries sequentially inside a transaction."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql_connector.connect.return_value = mock_conn

        queries = [
            ("INSERT INTO table (col) VALUES (%s)", (1,)),
            ("UPDATE table SET col = %s", (2,))
        ]
        result = self.db.execute_transaction(queries)

        self.assertTrue(result)
        mock_conn.cursor.assert_called_once()
        mock_conn.start_transaction.assert_called_once()
        self.assertEqual(mock_cursor.execute.call_count, 2)
        mock_cursor.execute.assert_any_call(*queries[0])
        mock_cursor.execute.assert_any_call(*queries[1])
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_execute_transaction_connection_fail(self):
        """Test execute_transaction returns False if get_connection fails."""
        mock_mysql_connector.connect.side_effect = MockError("Connection failed")

        result = self.db.execute_transaction([("SELECT 1", None)])

        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
