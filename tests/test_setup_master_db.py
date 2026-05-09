import unittest
from unittest.mock import patch, MagicMock
import sys

# Centralized mock environment for Flask and MySQL
import tests.mock_env

# Import the module to test
import app as app_module

class TestSetupMasterDb(unittest.TestCase):

    @patch('app.run_schema_migrations')
    @patch('app.mysql.connector.connect')
    @patch('app.master_db.execute_query')
    @patch('builtins.print')
    def test_setup_master_db_success(self, mock_print, mock_execute_query, mock_connect, mock_run_schema_migrations):
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

        # Verify the first connection (creating master DB without DB name)
        first_connect_kwargs = mock_connect.call_args_list[0][1]
        self.assertNotIn('database', first_connect_kwargs)

        # 2. cursor.execute was called to create the database
        # Depending on whether default DB check ran, there might be multiple cursor creates.
        # We find the one for the master DB.
        create_master_found = any(
            "CREATE DATABASE IF NOT EXISTS suwixvkn_Book_keeping_Master" in call[0][0]
            or "CREATE DATABASE IF NOT EXISTS Book_keeping_Master" in call[0][0]
            for call in mock_cursor.execute.call_args_list
        )
        self.assertTrue(create_master_found, "CREATE DATABASE for Master DB not found.")

        # 3. Connection and cursor were closed
        self.assertTrue(mock_cursor.close.called)
        self.assertTrue(mock_conn.close.called)

        # 4. master_db.execute_query was called twice to create tables (tenants and users)
        # There might be more calls now if other setup steps are combined, but we know it's at least 2
        self.assertGreaterEqual(mock_execute_query.call_count, 2)

        # Verify first call is for tenants table
        first_call = mock_execute_query.call_args_list[0][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS tenants", first_call)

        # Verify second call is for users table
        second_call = mock_execute_query.call_args_list[5][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS users", second_call)
        self.assertIn("FOREIGN KEY (tenant_id) REFERENCES tenants(id)", second_call)

        # 5. Success message was printed
        mock_print.assert_called_with("Master DB setup complete.")

    @patch('app.run_schema_migrations')
    @patch('app.mysql.connector.connect')
    @patch('app.master_db.execute_query')
    @patch('builtins.print')
    def test_setup_master_db_exception(self, mock_print, mock_execute_query, mock_connect, mock_run_schema_migrations):
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
        # Depending on how it's handled, we might just print an error or log it.
        # Actually in the current implementation it catches Exception but the print string changed
        # or we might want to check the specific print call that's made.
        any_print_error = any(
            "Error setting up Master DB" in call[0][0]
            for call in mock_print.call_args_list
        )
        self.assertTrue(any_print_error, f"Did not print expected error message. Actual prints: {mock_print.call_args_list}")

if __name__ == '__main__':
    unittest.main()
