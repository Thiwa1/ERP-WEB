import unittest
from unittest.mock import MagicMock
from vat_helper import VATReportGenerator
from datetime import date

class TestVATReportGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.from_date = '2023-01-01'
        self.to_date = '2023-01-31'
        self.generator = VATReportGenerator(self.mock_db, self.from_date, self.to_date)

    def test_check_vat_registered_true(self):
        self.mock_db.execute_query.return_value = [{'vat_registered': 1}]
        self.assertTrue(self.generator.check_vat_registered())

    def test_check_vat_registered_false(self):
        self.mock_db.execute_query.return_value = [{'vat_registered': 0}]
        self.assertFalse(self.generator.check_vat_registered())

    def test_generate_schedule_01(self):
        # Mock responses for Credit Sales and POS Sales
        self.mock_db.execute_query.side_effect = [
            [{'date': '2023-01-01', 'invoice_no': 'INV001', 'purchaser': 'Cust A', 'tin': '123', 'total': 1180, 'rate': 18}], # Credit Sales
            [{'date': '2023-01-02', 'gross_total': 2360, 'invoice_no': 'POS001', 'vat_amount': 360}] # POS Sales
        ]

        result = self.generator.generate_schedule_01()

        # Credit Sale: Net = 1180 / 1.18 = 1000, VAT = 180
        # POS Sale: Net = 2360 - 360 = 2000, VAT = 360
        # Total Value: 3000, Total VAT: 540

        self.assertEqual(len(result['rows']), 2)
        self.assertAlmostEqual(result['total_value'], 3000.0)
        self.assertAlmostEqual(result['total_vat'], 540.0)

    def test_generate_schedule_02(self):
        # Mock responses for Credit Purchases and Other Inputs
        self.mock_db.execute_query.side_effect = [
            [{'date': '2023-01-01', 'invoice_no': 'SUP001', 'supplier': 'Sup A', 'tin': '456', 'total': 1180, 'rate': 18, 'suppliers_invoice_JV': 10}], # Credit Purchase
            [{'date': '2023-01-03', 'narration': 'Petty Cash', 'vat_amount': 90, 'entry_jv': 11}] # Other Input
        ]

        result = self.generator.generate_schedule_02()

        # Credit Purchase: Net = 1000, VAT = 180
        # Other Input: VAT = 90
        # Total Value: 1000 (only credit purchase has explicit value calc in this logic), Total VAT: 270

        self.assertEqual(len(result['rows']), 2)
        self.assertAlmostEqual(result['total_value'], 1000.0)
        self.assertAlmostEqual(result['total_vat'], 270.0)

    def test_generate_amendments(self):
        # Mock responses for all 7 amendment queries + rate check + helper queries inside loops
        # This is complex to mock due to loops executing queries.
        # We will test a simplified scenario or just ensure it runs without error given empty returns.

        self.mock_db.execute_query.return_value = [] # Default empty list for all queries

        result = self.generator.generate_amendments()

        self.assertIn('schedule_01_amendment', result)
        self.assertIn('schedule_07_amendment', result)
        self.assertEqual(result['total_sched01_amd_vat'], 0)

    def test_generate_full(self):
        # Mock all method calls by mocking the generator methods themselves to avoid DB complexity
        # This tests the aggregation logic in `generate`

        self.generator.generate_schedule_01 = MagicMock(return_value={'rows': [], 'total_value': 1000, 'total_vat': 180})
        self.generator.generate_schedule_02 = MagicMock(return_value={'rows': [], 'total_value': 500, 'total_vat': 90})
        self.generator.generate_schedule_03 = MagicMock(return_value={'rows': [], 'total_vat': 50})
        self.generator.generate_schedule_04 = MagicMock(return_value={'rows': [], 'total_value': 100, 'total_vat': 18})
        self.generator.generate_schedule_05 = MagicMock(return_value={'rows': [], 'total_liable': 0, 'total_non_liable': 0, 'total_credit': 20})
        self.generator.generate_schedule_07 = MagicMock(return_value={'rows': []})
        self.generator.generate_amendments = MagicMock(return_value={
            'schedule_01_amendment': [], 'total_sched01_amd_value': 0, 'total_sched01_amd_vat': 10,
            'schedule_02_amendment': [], 'total_sched02_amd_value': 0, 'total_sched02_amd_vat': 5,
            'schedule_03_amendment': [], 'total_sched03_amd_vat': 5,
            'schedule_04_amendment': [], 'total_sched04_amd_value': 0, 'total_sched04_amd_vat': 2,
            'schedule_05_amendment': [], 'total_sched05_amd_credit': 0,
            'schedule_06_amendment': [],
            'schedule_07_amendment': []
        })
        self.generator.generate_reconciliation = MagicMock(return_value={})

        result = self.generator.generate()

        # Net VAT Calculation:
        # Output: 180 + 10 = 190
        # Input: 90 + 5 + 50 + 5 = 150
        # Credit Note: 18 + 2 = 20
        # Deemed: 20 + 0 = 20
        # Net = 190 - 150 - 20 - 20 = 0

        self.assertEqual(result['summary']['net_vat'], 0)
        self.assertEqual(result['summary']['total_output_value'], 1000)
import sys
from unittest.mock import MagicMock, ANY

# Mock dependencies before importing app
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

import unittest
from unittest.mock import patch
import app as app_module
from datetime import date

# Configure app mock
mock_flask_class = MagicMock()
mock_app_instance = MagicMock()

def route_side_effect(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_app_instance.route.side_effect = route_side_effect
mock_flask_class.return_value = mock_app_instance
sys.modules['flask'].Flask = mock_flask_class

# Reload app to apply mock
if 'app' in sys.modules:
    del sys.modules['app']
import app as app_module

# Configure globals
app_module.render_template = MagicMock(return_value="Rendered Template")
app_module.request = MagicMock()
mock_session_store = {}
app_module.session = mock_session_store
app_module.redirect = MagicMock()
app_module.url_for = MagicMock()
app_module.flash = MagicMock()

class TestVatReport(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        app_module.db = self.mock_db
        app_module.app_initialized = True

        mock_session_store.clear()
        mock_session_store['user_id'] = 'ADM001'
        mock_session_store['user_pk'] = 1
        mock_session_store['username'] = 'admin'

        # Reset mocks
        app_module.render_template.reset_mock()

    def test_vat_not_registered(self):
        """Test response when company is not VAT registered."""
        def side_effect(query, params=None, commit=False):
            if "SELECT Access_Reports FROM User_Rights" in query:
                return [{'Access_Reports': 1}]
            if "SELECT vat_registered FROM company" in query:
                return [{'vat_registered': 0}]
            return []

        self.mock_db.execute_query.side_effect = side_effect

        response = app_module.vat_report()

        self.assertEqual(response, "Rendered Template")
        args, kwargs = app_module.render_template.call_args
        self.assertEqual(args[0], 'vat_report.html')
        self.assertEqual(kwargs['vat_enabled'], False)

    def test_vat_report_happy_path(self):
        """Test successful VAT report generation with mocked data."""
        app_module.request.args = {'from_date': '2023-10-01', 'to_date': '2023-10-31'}

        def side_effect(query, params=None, commit=False):
            # Normalize query for matching
            q_norm = ' '.join(query.split())

            # --- Specific Complex Queries (Prioritized) ---

            # Schedule 01 - Credit Sales
            if "FROM Invoice_Oustanding io" in q_norm:
                return [{
                    'date': date(2023, 10, 1),
                    'invoice_no': 'INV-001',
                    'purchaser': 'Test Customer',
                    'tin': '123456789',
                    'total': 1180.0,
                    'rate': 18.0
                }]

            # Schedule 01 - POS Sales
            if "FROM entry_details ed" in q_norm and "VAT Control" in q_norm and "enty_values_CR > 0" in q_norm and "POS" in q_norm:
                return [{
                    'date': date(2023, 10, 2),
                    'narration': 'VAT on POS Sale POS-001',
                    'vat_amount': 180.0,
                    'gross_total': 1180.0,
                    'invoice_no': 'POS-001'
                }]

            # Schedule 02 - Credit Purchases
            if "FROM suppliers_invoice_data sid" in q_norm and "suppliers_VAT_rate > 0" in q_norm:
                return [{
                    'date': date(2023, 10, 3),
                    'invoice_no': 'SUP-001',
                    'supplier': 'Test Supplier',
                    'tin': '987654321',
                    'total': 590.0,
                    'rate': 18.0
                }]

            # Schedule 04 - Reversals (Credit/Debit Notes)
            # Match this specifically before the subquery check for 'rate' matches it
            if "FROM pos_sales_invoice_01 p" in q_norm:
                return []

            # Schedule 05 - Deemed Input
            if "FROM suppliers_invoice_data sid" in q_norm and "suppliers_vat_regidter_no IS NULL" in q_norm:
                return []

            # Other specific report queries returning empty lists
            if "FROM entry_details ed" in q_norm:
                return [] # Catch-all for other GL queries (imports, amendments, etc)

            # --- Simple/Metadata Queries ---

            if "SELECT Access_Reports FROM User_Rights" in q_norm:
                return [{'Access_Reports': 1}]
            if "SELECT vat_registered FROM company" in q_norm:
                return [{'vat_registered': 1}]

            # This is the dangerous one that was matching subqueries
            if "SELECT rate FROM tax_rates" in q_norm and "pos_sales_invoice_01" not in q_norm:
                return [{'rate': 18.0}]

            if "SELECT SUM(enty_values_CR) - SUM(enty_values_DR) as movement" in q_norm:
                return [{'movement': 270.0}]
            if "SELECT SUM(enty_values_CR) - SUM(enty_values_DR) as balance" in q_norm:
                return [{'balance': 270.0}]
            if "SELECT suppliers_invoice_JV FROM suppliers_invoice_data" in q_norm:
                return [{'suppliers_invoice_JV': 100}]

            # Catch-all
            return []

        self.mock_db.execute_query.side_effect = side_effect

        response = app_module.vat_report()

        self.assertEqual(response, "Rendered Template")
        args, kwargs = app_module.render_template.call_args
        self.assertEqual(args[0], 'vat_report.html')
        self.assertEqual(kwargs['vat_enabled'], True)

        summary = kwargs['summary']
        # Output: 1000 + 1000 = 2000 Base. VAT: 180 + 180 = 360.
        # Input: 500 Base. VAT: 90.
        # Net: 360 - 90 = 270.

        self.assertEqual(summary['total_output_vat'], 360.0)
        self.assertEqual(summary['total_input_vat'], 90.0)
        self.assertEqual(summary['net_vat'], 270.0)

if __name__ == '__main__':
    unittest.main()
