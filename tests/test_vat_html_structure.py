import unittest
from unittest.mock import MagicMock, patch
from datetime import date
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module

class TestVATHTML(unittest.TestCase):
    def setUp(self):
        self.app = app_module.app.test_client()
        self.app.testing = True

        self.original_db = app_module.db
        app_module.db = MagicMock()
        app_module.app_initialized = True

        # Patch db directly
        self.mock_execute = MagicMock(side_effect=self.mock_db_query)
        app_module.db.execute_query = self.mock_execute

    def tearDown(self):
        app_module.db = self.original_db

    def mock_db_query(self, query, params=None, commit=False):
        q_lower = query.lower()

        # Return empty/default for other queries
        if "pos_sales_invoice_01" in q_lower: return []
        if "invoice_oustanding" in q_lower: return []
        if "suppliers_invoice_data" in q_lower: return []
        if "select company_curency" in q_lower: return [{'company_curency': 'LKR'}]
        if "select * from company" in q_lower: return [{'company_curency': 'LKR'}]
        if "tax_rates" in q_lower: return [{'rate': 18.0}]

        # Schedule 03 Query
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

        if "vat_amount" in q_lower: return []

        return []

    def test_html_structure(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        with patch('app.check_permission', return_value=True):
            response = self.app.get('/vat_report?from_date=2023-10-01&to_date=2023-10-31')
            html = response.data.decode('utf-8')

            # Check Tabs
            self.assertIn('id="schedule03-tab"', html, "Schedule 03 Tab ID missing")
            self.assertIn('Schedule 03 (Imports)', html, "Schedule 03 Tab Label missing")

            # Check Content Div
            self.assertIn('id="schedule03"', html, "Schedule 03 Content Div missing")
            self.assertIn('Schedule 03 - Input Schedule for Imports', html, "Schedule 03 Header missing")

            # Check Table Headers
            self.assertIn('Cusdec No', html)
            self.assertIn('VAT Upfront', html)
            self.assertIn('VAT Deferred', html)

            # Check Data
            self.assertIn('CUSDEC-ORIG-001', html, "Mock Data missing")
            self.assertIn('7,500.00', html, "Mock Value missing")

if __name__ == '__main__':
    unittest.main()
