import unittest
from unittest.mock import MagicMock, patch
from datetime import date
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module

class TestVATSchedule03(unittest.TestCase):
    def setUp(self):
        self.app = app_module.app.test_client()
        self.app.testing = True

        self.original_db = app_module.db
        app_module.db = MagicMock()
        app_module.app_initialized = True

        # Patch db directly on the module instance used by tests
        self.mock_execute = MagicMock(side_effect=self.mock_db_query)
        app_module.db.execute_query = self.mock_execute

    def tearDown(self):
        app_module.db = self.original_db

    def mock_db_query(self, query, params=None, commit=False):
        q_lower = query.lower()

        # Return empty/default for other queries to avoid noise
        if "pos_sales_invoice_01" in q_lower: return []
        if "invoice_oustanding" in q_lower: return []
        if "suppliers_invoice_data" in q_lower: return []
        if "select company_curency" in q_lower: return [{'company_curency': 'LKR'}]
        if "select * from company" in q_lower: return [{'company_curency': 'LKR'}]
        if "tax_rates" in q_lower: return [{'rate': 18.0}]

        # Schedule 03 Query (Main Import Schedule)
        # Distinguish by selecting 'cusdec_no' or joining 'jv_numbers'
        if "cusdec_no" in q_lower and "entry_details" in q_lower:
            return [
                {
                    'entry_jv': 606,
                    'cusdec_no': 'CUSDEC-ORIG-001',
                    'serial_id': 'SER-001',
                    'date': date(2023, 10, 10),
                    'narration': 'Import VAT Payment for CUSDEC-ORIG-001',
                    'vat_upfront': 7500.0,
                    'vat_deferred': 0.0,
                    'cusdec_reg_date': date(2023, 10, 10),
                    'cusdec_office_id': '-'
                }
            ]

        # Schedule 02 (Other Inputs)
        # It selects 'vat_amount' and filters OUT Import/Amendment
        # My updated logic in app.py checks for NOT LIKE Import AND NOT LIKE Amendment
        # But wait, my mock condition above was triggering because it matched "import".
        # So I need to handle the query that has "NOT LIKE '%Import%'" specifically here if needed, or just let it fall through to empty list.

        # If the query contains "vat_amount" (Schedule 02), return empty list or valid mock
        if "vat_amount" in q_lower:
            return []

        return []

    @patch('app.render_template')
    def test_report_generation(self, mock_render):
        # Ensure side effect is set
        app_module.db.execute_query.side_effect = self.mock_db_query

        with self.app.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        with patch('app.check_permission', return_value=True):
            self.app.get('/vat_report?from_date=2023-10-01&to_date=2023-10-31')

            # Check render call
            self.assertTrue(mock_render.called, "render_template was not called")

            args, kwargs = mock_render.call_args
            sched03 = kwargs.get('schedule_03', [])

            self.assertTrue(len(sched03) > 0, "Schedule 03 should not be empty")
            row = sched03[0]
            self.assertEqual(row['cusdec_no'], 'CUSDEC-ORIG-001')
            self.assertEqual(row['vat_upfront'], 7500.0)

if __name__ == '__main__':
    unittest.main()
