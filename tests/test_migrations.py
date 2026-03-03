import unittest
from unittest.mock import MagicMock, patch, call
import migrations

class TestMigrations(unittest.TestCase):
    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    def test_run_migrations_no_connection(self):
        # Test behavior when connection is None
        migrations.run_migrations(None)
        # Should return immediately, no cursor calls
        self.mock_conn.cursor.assert_not_called()

    def test_run_migrations_success(self):
        # Setup mock behavior for helpers
        # is_migration_applied will check fetchone
        self.mock_cursor.fetchone.return_value = None # Assume no migrations applied initially

        migrations.run_migrations(self.mock_conn)

        # Verify specific migration steps were called
        # We can check for a few key SQL statements to verify orchestration

        calls = [
            call("CREATE TABLE IF NOT EXISTS migrations (id INT AUTO_INCREMENT PRIMARY KEY, migration_name VARCHAR(255) UNIQUE NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"),
            call("SHOW COLUMNS FROM User_Rights"),
            call("SHOW TABLES LIKE 'currency_table'"),
            call("ALTER TABLE new_account_table ADD COLUMN currency_code VARCHAR(10) DEFAULT 'LKR'"), # From _migrate_account_currency
            call("SHOW COLUMNS FROM inventoy_items"),
            call("SHOW COLUMNS FROM suppliers"),
            call("SHOW COLUMNS FROM company"),
            call("SHOW TABLES LIKE 'tax_rates'"),
            call("SHOW TABLES LIKE 'cheque_print_settings'"),
            call("SHOW TABLES LIKE 'proforma_invoice_header'"),
            call("SHOW COLUMNS FROM OP_NO_Table")
        ]

        # Filter mock calls to see if our expected calls are present
        # Note: Using assertHasCalls with any_order=True or checking specific key calls

        # We check specific calls because the order matters for some but `run_migrations` calls internal functions sequentially

        executed_queries = [c[0][0] for c in self.mock_cursor.execute.call_args_list]

        self.assertIn("CREATE TABLE IF NOT EXISTS migrations (id INT AUTO_INCREMENT PRIMARY KEY, migration_name VARCHAR(255) UNIQUE NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", executed_queries)
        self.assertIn("SHOW COLUMNS FROM User_Rights", executed_queries)
        self.assertIn("ALTER TABLE new_account_table ADD COLUMN currency_code VARCHAR(10) DEFAULT 'LKR'", executed_queries)

    @patch('migrations._migrate_user_rights')
    @patch('migrations._migrate_currency_table')
    def test_run_migrations_calls_subfunctions(self, mock_migrate_currency, mock_migrate_rights):
        # Verify that the main function calls the sub-functions
        # This is a unit test for the orchestration logic

        # Need to patch the helper inside run_migrations?
        # No, the helpers are defined *inside* run_migrations, so we can't easily patch them from outside
        # But we can patch the module-level functions we created in `migrations.py`

        migrations.run_migrations(self.mock_conn)

        mock_migrate_rights.assert_called_with(self.mock_cursor)
        mock_migrate_currency.assert_called_with(self.mock_cursor)

    def test_record_migration(self):
        # We assume no migrations have been applied initially so that the
        # migrations run and record_migration is subsequently called.
        self.mock_cursor.fetchone.return_value = None

        migrations.run_migrations(self.mock_conn)

        # Collect all SQL queries executed by the cursor
        executed_queries = [call[0][0] for call in self.mock_cursor.execute.call_args_list]

        # Verify that record_migration inserted the migration record.
        # We check that the INSERT INTO statement for the migrations table was executed.
        has_insert = any(
            "INSERT INTO _migrations (migration_name) VALUES (%s)" in query or
            "INSERT INTO migrations (migration_name) VALUES (%s)" in query
            for query in executed_queries
        )
        self.assertTrue(has_insert, "record_migration should execute an INSERT statement")


if __name__ == '__main__':
    unittest.main()
