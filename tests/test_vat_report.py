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

if __name__ == '__main__':
    unittest.main()
