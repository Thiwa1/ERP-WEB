import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestDashboardKPIs(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch('app.db.get_connection')
    def test_dashboard_kpis_endpoint(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Setup mock return values for the 4 queries


        def mock_fetchone(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Return appropriate data based on call_count or what query was executed.
            # Easiest way: look at mock_cursor.execute.call_args[0][0]
            last_query = mock_cursor.execute.call_args[0][0] if mock_cursor.execute.call_args else ""
            if "POS_Sales_Invoice_01" in last_query:
                return {'total': 142580}
            elif "cash_book_recode" in last_query:
                return {'total': 50000}
            elif "bank_book_recod" in last_query:
                return {'total': 39340}
            elif "suppliers_invoice_data" in last_query:
                return {'total': 34210}
            elif "OP_NO_Table" in last_query:
                return {'count': 3}
            # For permission or user queries:
            return {'permissions': 'all', 'user_id': 'ADM001', 'id': 1}

        call_count = 0
        mock_cursor.fetchone.side_effect = mock_fetchone



        with app.test_request_context(), app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 'ADM001'
                sess['user_pk'] = 1

            response = client.get('/api/dashboard/kpis?start_date=2023-01-01&end_date=2023-01-31')

            self.assertEqual(response.status_code, 200)
            data = response.get_json()

            self.assertTrue(data['success'])
            self.assertEqual(data['kpis']['total_revenue'], 142580)
            self.assertEqual(data['kpis']['cash_receipts'], 89340)
            self.assertEqual(data['kpis']['outstanding_payables'], 34210)
            self.assertEqual(data['kpis']['pending_approvals'], 3)

            # Verify the queries were called correctly
            pass

if __name__ == '__main__':
    unittest.main()
