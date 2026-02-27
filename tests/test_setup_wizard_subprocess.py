
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# Mock mysql and mysql.connector before importing setup_wizard
mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Add current directory to path so we can import setup_wizard
sys.path.append('.')

import setup_wizard

class TestSetupWizardSubprocess(unittest.TestCase):

    @patch('setup_wizard.input')
    @patch('builtins.print') # Suppress print output globally
    @patch('mysql.connector.connect') # Patch where it is used or defined
    @patch('os.system')
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open, read_data="SCHEMA SQL DATA")
    @patch('os.path.exists')
    def test_schema_import_uses_subprocess(self, mock_exists, mock_file, mock_subprocess_run, mock_os_system, mock_connect, mock_print, mock_input):
        # Setup mocks
        # inputs: root_host, root_user, root_pass, db_name, vat, app_user, app_pass
        mock_input.side_effect = [
            'localhost', 'root', 'rootpass', # Root creds
            'Book_keeping', # DB Name
            'n', # VAT
            'bookkeeper', 'bkpass' # App creds
        ]

        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchone for checks (e.g. user exists checks)
        # setup_wizard checks existence of several tables/rows.
        # It calls fetchone() repeatedly.
        # We need it to return [0] (count=0) so it proceeds to insert data.
        mock_cursor.fetchone.return_value = [0]
        mock_cursor.lastrowid = 1
        mock_cursor.fetchall.return_value = [] # for SHOW COLUMNS

        # Mock os.path.exists to return True for fixed_assets.sql
        mock_exists.return_value = True

        # Mock subprocess.run return value
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Run main
        setup_wizard.main()

        # Verification

        # This test is designed to verify the FIX.
        # Before the fix, subprocess.run is NOT called, so this assertion should FAIL.
        # After the fix, it should PASS.

        # Verify subprocess.run was called twice (once for schema, once for fixed assets)
        self.assertEqual(mock_subprocess_run.call_count, 2, "subprocess.run should be called twice")

        # Check first call (database_schema.sql)
        call_args1, call_kwargs1 = mock_subprocess_run.call_args_list[0]
        # We expect the command to be: ['mysql', '-h', 'localhost', '-u', 'root', '-prootpass', 'Book_keeping']
        # Note: The password flag might be attached or separate depending on implementation details in next step.
        # The plan says: f'-p{root_password}' which means attached.

        expected_cmd = ['mysql', '-h', 'localhost', '-u', 'root', '-prootpass', 'Book_keeping']
        self.assertEqual(call_args1[0], expected_cmd)
        self.assertIn('stdin', call_kwargs1)

        # Check second call (fixed_assets.sql)
        call_args2, call_kwargs2 = mock_subprocess_run.call_args_list[1]
        self.assertEqual(call_args2[0], expected_cmd)
        self.assertIn('stdin', call_kwargs2)

        # Verify os.system was NOT called for these commands
        # It might be called for other things? The original code only uses it for mysql commands.
        # So we can assert call_count is 0 if we remove all os.system calls.
        mock_os_system.assert_not_called()

if __name__ == '__main__':
    unittest.main()
