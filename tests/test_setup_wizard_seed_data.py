import sys
import unittest
from unittest.mock import MagicMock, call

# Mock mysql and mysql.connector before importing setup_wizard
mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Add current directory to path so we can import setup_wizard
sys.path.append('.')

import setup_wizard

class TestSetupWizardSeedData(unittest.TestCase):

    def test_seed_default_data_company_insert(self):
        # Create a mock configuration
        config = {
            'app_db_name': 'Test_DB_Name',
            'vat_registered': 1
        }

        # Create a mock cursor
        mock_cursor = MagicMock()

        # Setup the mock cursor to return 0 for the count check (company table)
        # We need it to return 0 so it proceeds to insert into the company table.
        # It's called for sub_accont_for_new_account, customer, suppliers, Login_Table, company
        # 5 times total, so we return [0] each time.
        mock_cursor.fetchone.return_value = [0]

        # Also need to mock fetchall for the SHOW COLUMNS FROM User_Rights call
        mock_cursor.fetchall.return_value = []

        # Call the function
        setup_wizard.seed_default_data(config, mock_cursor)

        # Verify that cursor.execute was called to insert default company details
        # with the correct arguments (config['app_db_name'])

        company_insert_calls = []
        for call_obj in mock_cursor.execute.call_args_list:
            query = call_obj[0][0]
            if "INSERT INTO company" in query:
                company_insert_calls.append(call_obj)

        self.assertEqual(len(company_insert_calls), 1, "Should execute exactly one INSERT INTO company statement for default company")

        # Check the arguments passed to the insert
        query = company_insert_calls[0][0][0]
        params = company_insert_calls[0][0][1]

        self.assertIn("INSERT INTO company (id, company_name, company_curency, vat_registered)", query)
        self.assertIn("VALUES (0, 'My Company', 'LKR', %s)", query)
        self.assertEqual(params, (1,))

if __name__ == '__main__':
    unittest.main()
