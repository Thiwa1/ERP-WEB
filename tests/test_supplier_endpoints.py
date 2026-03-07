import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock modules before importing app
sys.modules['flask'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['num2words'] = MagicMock()

def mock_login_required(f):
    return f

import app
app.login_required = mock_login_required

class TestSupplierEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        app.db = self.mock_db

        self.mock_request = MagicMock()
        app.request = self.mock_request

    def test_get_supplier_base_data_found(self):
        # Setup mock db returns
        self.mock_db.execute_query.side_effect = [
            # Supplier Details
            [{'supplier_code': 'S001', 'supplier_address_1': '123 St', 'supplier_address_2': 'City',
              'suppliers_teli_1': '123456', 'suppliers_e_mail': 'test@test.com', 'suppliers_vat_regidter_no': 'VAT123',
              'sup_id': 1}],
            # Outstanding Invoices
            [{'s_i_id': 10, 'suppliers_invoice_number': 'INV-001', 'suppliers_invoice_date': '2023-01-01',
              'suppliers_invoice_final_date': '2023-01-31', 'suppliers_invoice_total_oustanding': '100.00',
              'suppliers_invoice_total_payment': '50.00', 'suppliers_invoice_oustanding': '50.00'}]
        ]

        details, inv_list, sup_id = app._get_supplier_base_data('Test Supplier')

        self.assertEqual(sup_id, 1)
        self.assertEqual(details['code'], 'S001')
        self.assertEqual(len(inv_list), 1)
        self.assertEqual(inv_list[0]['invoice_no'], 'INV-001')
        self.assertEqual(self.mock_db.execute_query.call_count, 2)

    def test_get_supplier_base_data_not_found(self):
        self.mock_db.execute_query.return_value = []
        details, inv_list, sup_id = app._get_supplier_base_data('Missing Supplier')
        self.assertIsNone(details)
        self.assertIsNone(inv_list)
        self.assertIsNone(sup_id)

if __name__ == '__main__':
    unittest.main()
