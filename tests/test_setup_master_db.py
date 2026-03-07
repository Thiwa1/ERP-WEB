import unittest
from unittest.mock import patch, MagicMock
import sys

# Centralized mock environment for Flask and MySQL
import tests.mock_env

# Import the module to test
import app as app_module

class TestSetupMasterDb(unittest.TestCase):

    @patch('app.mysql.connector.connect')
    @patch('app.master_db.execute_query')
    @patch('builtins.print')
    def test_setup_master_db_success(self, mock_print, mock_execute_query, mock_connect):
        """Test that setup_master_db correctly initializes the master DB and tables."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Call the function
        app_module.setup_master_db()

        # Assertions
        # 1. Connect was called with a config lacking the 'database' key
        self.assertTrue(mock_connect.called)
        connect_kwargs = mock_connect.call_args[1]
        self.assertNotIn('database', connect_kwargs)

        # 2. cursor.execute was called to create the database
        mock_cursor.execute.assert_called_once()
        create_db_call = mock_cursor.execute.call_args[0][0]
        self.assertIn("CREATE DATABASE IF NOT EXISTS Book_keeping_Master", create_db_call)

        # 3. Connection and cursor were closed
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        # 4. master_db.execute_query was called twice to create tables
        self.assertEqual(mock_execute_query.call_count, 2)

        # Verify first call is for tenants table
        first_call = mock_execute_query.call_args_list[0][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS tenants", first_call)

        # Verify second call is for users table
        second_call = mock_execute_query.call_args_list[1][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS users", second_call)
        self.assertIn("FOREIGN KEY (tenant_id) REFERENCES tenants(id)", second_call)

        # 5. Success message was printed
        mock_print.assert_called_with("Master DB setup complete.")

    @patch('app.mysql.connector.connect')
    @patch('app.master_db.execute_query')
    @patch('builtins.print')
    def test_setup_master_db_exception(self, mock_print, mock_execute_query, mock_connect):
        """Test that setup_master_db handles exceptions gracefully."""
        # Make the connection fail
        mock_connect.side_effect = Exception("Connection Failed")

        # Call the function
        app_module.setup_master_db()

        # Assertions
        # 1. Connect was called
        self.assertTrue(mock_connect.called)

        # 2. execute_query should not have been called because connection failed
        mock_execute_query.assert_not_called()

        # 3. Error message was printed
        mock_print.assert_called_with("Error setting up Master DB: Connection Failed")

if __name__ == '__main__':
    unittest.main()
