import unittest
from unittest.mock import MagicMock, call
import services

class TestServices(unittest.TestCase):
    def test_create_grn_success(self):
        # Setup mocks
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 123  # Mock generated JV ID

        # Input data
        current_user = 1
        supplier_info = {'code': 'SUP001', 'id': 5}
        invoice_info = {
            'no': 'INV-100',
            'date': '2023-10-26',
            'due_date': '2023-11-26',
            'narration': 'Test GRN',
            'job_no': 'JOB-001',
            'location': 'Main Warehouse',
            'total_value': 1000.0,
            'vat_rate': 10.0,
            'vat_amount': 100.0,
            'grand_total': 1100.0
        }
        items = [
            {'name': 'Item 1', 'code': 'ITM001', 'unit': 'Nos', 'cost': 100.0, 'qty': 5},
            {'name': 'Item 2', 'code': 'ITM002', 'unit': 'Kg', 'cost': 50.0, 'qty': 10}
        ]

        # Call function
        jv_no = services.create_grn(mock_db, current_user, supplier_info, invoice_info, items)

        # Assertions
        self.assertEqual(jv_no, 123)
        mock_conn.start_transaction.assert_called_once()
        mock_conn.commit.assert_called_once()

        # Verify executed queries (simplified check)
        self.assertTrue(mock_cursor.execute.called)

        # Check specific calls
        calls = mock_cursor.execute.call_args_list

        # 1. JV Number Generation
        self.assertIn("INSERT INTO jv_numbers", calls[0][0][0])

        # 2. Invoice Data
        self.assertIn("INSERT INTO suppliers_invoice_data", calls[1][0][0])
        self.assertEqual(calls[1][0][1][0], 'SUP001') # Supplier Code
        self.assertEqual(calls[1][0][1][1], 'INV-100') # Invoice No

        # 3. GL Entries
        # Account Payable
        self.assertIn("INSERT INTO entry_details", calls[2][0][0])
        self.assertEqual(calls[2][0][1][0], 'Account Payable')

        # Inventory
        self.assertIn("INSERT INTO entry_details", calls[3][0][0])
        self.assertEqual(calls[3][0][1][0], 'Inventory')

        # VAT Control
        self.assertIn("INSERT INTO entry_details", calls[4][0][0])
        self.assertEqual(calls[4][0][1][0], 'VAT Control')

        # 4. Inventory Records (2 items)
        self.assertIn("INSERT INTO inventory_recod", calls[5][0][0])
        self.assertEqual(calls[5][0][1][0], 'Item 1')

        self.assertIn("INSERT INTO inventory_recod", calls[6][0][0])
        self.assertEqual(calls[6][0][1][0], 'Item 2')

    def test_create_grn_failure_rollback(self):
        # Setup mocks to raise exception
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simulate error on second query
        mock_cursor.execute.side_effect = [None, Exception("DB Error")]

        current_user = 1
        supplier_info = {'code': 'SUP001', 'id': 5}
        invoice_info = {
            'no': 'INV-100',
            'date': '2023-10-26',
            'due_date': '2023-11-26',
            'narration': 'Test GRN',
            'job_no': 'JOB-001',
            'location': 'Main Warehouse',
            'total_value': 1000.0,
            'vat_rate': 10.0,
            'vat_amount': 100.0,
            'grand_total': 1100.0
        }
        items = []

        with self.assertRaises(Exception) as context:
            services.create_grn(mock_db, current_user, supplier_info, invoice_info, items)

        self.assertTrue("DB Error" in str(context.exception))
        mock_conn.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main()
