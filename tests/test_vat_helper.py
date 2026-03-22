import unittest
from unittest.mock import MagicMock
from vat_helper import VATReportGenerator

class TestVATReportGeneratorLogic(unittest.TestCase):
    def test_vat_report_generator_init(self):
        """Test that VATReportGenerator initializes with correct parameters."""
        mock_db = MagicMock()
        from_date = '2023-01-01'
        to_date = '2023-01-31'

        generator = VATReportGenerator(mock_db, from_date, to_date)

        self.assertEqual(generator.db, mock_db)
        self.assertEqual(generator.from_date, from_date)
        self.assertEqual(generator.to_date, to_date)

    def test_check_vat_registered(self):
        """Test the check_vat_registered method."""
        mock_db = MagicMock()
        generator = VATReportGenerator(mock_db, '2023-01-01', '2023-01-31')

        # Test case 1: VAT registered
        mock_db.execute_query.return_value = [{'vat_registered': 1}]
        self.assertTrue(generator.check_vat_registered())

        # Test case 2: VAT not registered
        mock_db.execute_query.return_value = [{'vat_registered': 0}]
        self.assertFalse(generator.check_vat_registered())

        # Test case 3: Empty query result
        mock_db.execute_query.return_value = []
        self.assertFalse(generator.check_vat_registered())

    def test_generate_schedule_01(self):
        """Test Schedule 01 - Output Tax (Sales)."""
        mock_db = MagicMock()
        generator = VATReportGenerator(mock_db, '2023-01-01', '2023-01-31')

        # Credit Sales Query Output
        credit_sales_data = [{
            'date': '2023-01-15',
            'invoice_no': 'INV-100',
            'purchaser': 'Customer A',
            'tin': '111',
            'total': 118.0,
            'rate': 18.0
        }]

        # POS Sales Query Output
        pos_sales_data = [{
            'date': '2023-01-16',
            'narration': 'VAT on POS',
            'vat_amount': 18.0,
            'gross_total': 118.0,
            'invoice_no': 'POS-200'
        }]

        mock_db.execute_query.side_effect = [credit_sales_data, pos_sales_data]

        result = generator.generate_schedule_01()

        # Verify 2 rows returned
        self.assertEqual(len(result['rows']), 2)

        # Credit sale: net = 118 / 1.18 = 100, vat = 18
        # POS sale: gross = 118, vat = 18, net = 100
        # Total Value: 200, Total VAT: 36
        self.assertAlmostEqual(result['total_value'], 200.0)
        self.assertAlmostEqual(result['total_vat'], 36.0)

    def test_generate_schedule_02(self):
        """Test Schedule 02 - Input Tax (Purchases)."""
        mock_db = MagicMock()
        generator = VATReportGenerator(mock_db, '2023-01-01', '2023-01-31')

        credit_purchases_data = [{
            'date': '2023-01-20',
            'invoice_no': 'SUP-500',
            'supplier': 'Supplier X',
            'tin': '222',
            'total': 236.0,
            'rate': 18.0,
            'suppliers_invoice_JV': 'JV-001'
        }]

        other_inputs_data = [{
            'date': '2023-01-21',
            'narration': 'Other Input VAT',
            'vat_amount': 10.0,
            'entry_jv': 'JV-002'
        }]

        mock_db.execute_query.side_effect = [credit_purchases_data, other_inputs_data]

        result = generator.generate_schedule_02()

        self.assertEqual(len(result['rows']), 2)
        # Purchase: net = 236 / 1.18 = 200, vat = 36
        # Other input: vat = 10
        # Total Value: 200, Total VAT: 46
        self.assertAlmostEqual(result['total_value'], 200.0)
        self.assertAlmostEqual(result['total_vat'], 46.0)

    def test_generate_schedule_03(self):
        """Test Schedule 03 - Input Schedule for Imports."""
        mock_db = MagicMock()
        generator = VATReportGenerator(mock_db, '2023-01-01', '2023-01-31')

        sched03_data = [{
            'entry_jv': 55,
            'cusdec_no': 'CD-100',
            'serial_id': 'SID-100',
            'date': '2023-01-22',
            'narration': 'Import VAT',
            'vat_upfront': 500.0
        }]

        mock_db.execute_query.return_value = sched03_data

        result = generator.generate_schedule_03()

        self.assertEqual(len(result['rows']), 1)
        self.assertAlmostEqual(result['total_vat'], 500.0)
        self.assertEqual(result['rows'][0]['cusdec_no'], 'CD-100')
        self.assertEqual(result['rows'][0]['vat_upfront'], 500.0)

if __name__ == '__main__':
    unittest.main()
