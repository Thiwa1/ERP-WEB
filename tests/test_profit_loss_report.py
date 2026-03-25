import unittest
from unittest.mock import MagicMock
from datetime import date
from profit_loss_report import ProfitLossReportGenerator


class MockForm(dict):
    def getlist(self, key):
        val = self.get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]


class TestProfitLossReportGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.generator = ProfitLossReportGenerator(self.mock_db)
        self.mock_request = MagicMock()

    def test_get_profit_loss_periods_get(self):
        self.mock_request.method = 'GET'

        periods = self.generator._get_profit_loss_periods(self.mock_request)

        self.assertEqual(len(periods), 1)
        today = date.today()
        expected_start = today.replace(day=1).strftime('%Y-%m-%d')
        expected_end = today.strftime('%Y-%m-%d')

        self.assertEqual(periods[0]['start'], expected_start)
        self.assertEqual(periods[0]['end'], expected_end)

    def test_get_profit_loss_periods_post(self):
        self.mock_request.method = 'POST'
        self.mock_request.form = MockForm({
            'start_date[]': ['2023-01-01', '2023-02-01'],
            'end_date[]': ['2023-01-31', '2023-02-28']
        })

        periods = self.generator._get_profit_loss_periods(self.mock_request)

        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0]['start'], '2023-01-01')
        self.assertEqual(periods[0]['end'], '2023-01-31')
        self.assertEqual(periods[1]['start'], '2023-02-01')
        self.assertEqual(periods[1]['end'], '2023-02-28')

    def test_get_profit_loss_periods_post_empty(self):
        self.mock_request.method = 'POST'
        self.mock_request.form = MockForm()

        periods = self.generator._get_profit_loss_periods(self.mock_request)

        self.assertEqual(len(periods), 1)
        today = date.today()
        self.assertEqual(periods[0]['start'], today.replace(day=1).strftime('%Y-%m-%d'))

    def test_fetch_profit_loss_accounts(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_hold_possion_PL': 1, 'account_income': 1, 'account_expenses': 0},
            {'account_name': 'COGS', 'account_name_of_catogory_PL': 'Cost of Sales', 'account_hold_possion_PL': 2, 'account_income': 0, 'account_expenses': 1}
        ]

        periods = [{'start': '2023-01-01', 'end': '2023-01-31'}, {'start': '2023-02-01', 'end': '2023-02-28'}]
        acc_map = self.generator._fetch_profit_loss_accounts(mock_cursor, periods)

        self.assertEqual(len(acc_map), 2)
        self.assertIn('Sales', acc_map)
        self.assertIn('COGS', acc_map)

        # Verify structure
        self.assertEqual(acc_map['Sales']['meta']['account_name'], 'Sales')
        self.assertEqual(len(acc_map['Sales']['values']), 2)
        self.assertEqual(acc_map['Sales']['values'], [0.0, 0.0])

    def test_fetch_profit_loss_data(self):
        mock_cursor = MagicMock()

        # Simulate sum rows from entry_details
        mock_cursor.fetchall.return_value = [
            {'account_name': 'Sales', 'dr_0': 100, 'cr_0': 1100, 'dr_1': 0, 'cr_1': 1500},
            {'account_name': 'COGS', 'dr_0': 600, 'cr_0': 0, 'dr_1': 700, 'cr_1': 50}
        ]

        periods = [{'start': '2023-01-01', 'end': '2023-01-31'}, {'start': '2023-02-01', 'end': '2023-02-28'}]
        acc_map = {
            'Sales': {'meta': {'account_income': 1, 'account_expenses': 0}, 'values': [0.0, 0.0]},
            'COGS': {'meta': {'account_income': 0, 'account_expenses': 1}, 'values': [0.0, 0.0]}
        }

        updated_map = self.generator._fetch_profit_loss_data(mock_cursor, periods, acc_map)

        # Sales (Income) -> CR - DR
        # Period 0: 1100 - 100 = 1000
        # Period 1: 1500 - 0 = 1500
        self.assertEqual(updated_map['Sales']['values'][0], 1000.0)
        self.assertEqual(updated_map['Sales']['values'][1], 1500.0)

        # COGS (Expense) -> DR - CR
        # Period 0: 600 - 0 = 600
        # Period 1: 700 - 50 = 650
        self.assertEqual(updated_map['COGS']['values'][0], 600.0)
        self.assertEqual(updated_map['COGS']['values'][1], 650.0)

    def test_fetch_profit_loss_data_no_periods(self):
        mock_cursor = MagicMock()
        acc_map = {'Sales': {}}

        updated_map = self.generator._fetch_profit_loss_data(mock_cursor, [], acc_map)
        self.assertEqual(updated_map, acc_map)
        mock_cursor.execute.assert_not_called()

    def test_process_profit_loss_categories(self):
        acc_map = {
            'Sales': {'meta': {'account_name_of_catogory_PL': 'Revenue', 'account_income': 1, 'account_hold_possion_PL': 1}, 'values': [1000.0, 1500.0]},
            'Interest': {'meta': {'account_name_of_catogory_PL': 'Other Income', 'account_income': 1, 'account_hold_possion_PL': 2}, 'values': [100.0, 200.0]},
            'COGS': {'meta': {'account_name_of_catogory_PL': 'Cost of Sales', 'account_income': 0, 'account_hold_possion_PL': 3}, 'values': [600.0, 650.0]},
            'Rent': {'meta': {'account_name_of_catogory_PL': 'Admin', 'account_income': 0, 'account_hold_possion_PL': 4}, 'values': [100.0, 100.0]},
            'ZeroBal': {'meta': {'account_name_of_catogory_PL': 'Admin', 'account_income': 0, 'account_hold_possion_PL': 5}, 'values': [0.0, 0.0]}
        }
        periods = [1, 2] # Dummy length

        report_data = self.generator._process_profit_loss_categories(acc_map, periods)

        # Income categories
        self.assertEqual(len(report_data['income_categories']), 2)
        self.assertEqual(report_data['income_categories'][0]['name'], 'Revenue')
        self.assertEqual(report_data['income_categories'][0]['total'], [1000.0, 1500.0])

        self.assertEqual(report_data['income_categories'][1]['name'], 'Other Income')
        self.assertEqual(report_data['income_categories'][1]['total'], [100.0, 200.0])

        # Expense categories
        self.assertEqual(len(report_data['expense_categories']), 2)
        self.assertEqual(report_data['expense_categories'][0]['name'], 'Cost of Sales')
        self.assertEqual(report_data['expense_categories'][0]['total'], [600.0, 650.0])

        self.assertEqual(report_data['expense_categories'][1]['name'], 'Admin')
        self.assertEqual(report_data['expense_categories'][1]['total'], [100.0, 100.0])

        # Zero balance was filtered out
        self.assertEqual(len(report_data['expense_categories'][1]['accounts']), 1)
        self.assertEqual(report_data['expense_categories'][1]['accounts'][0]['name'], 'Rent')

        # Totals
        self.assertEqual(report_data['total_income'], [1100.0, 1700.0])
        self.assertEqual(report_data['total_expense'], [700.0, 750.0])
        self.assertEqual(report_data['net_profit'], [400.0, 950.0])

    def test_generate_success(self):
        self.mock_request.method = 'GET'

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Accounts
        mock_cursor.fetchall.side_effect = [
            [{'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_hold_possion_PL': 1, 'account_income': 1, 'account_expenses': 0}],
            [{'account_name': 'Sales', 'dr_0': 0, 'cr_0': 1000}]
        ]

        periods, report_data, start, end = self.generator.generate(self.mock_request)

        self.assertEqual(len(periods), 1)
        self.assertEqual(report_data['total_income'], [1000.0])
        self.assertEqual(report_data['net_profit'], [1000.0])

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_generate_db_failure(self):
        self.mock_db.get_connection.return_value = None
        self.mock_request.method = 'GET'

        with self.assertRaises(Exception) as context:
            self.generator.generate(self.mock_request)

        self.assertEqual(str(context.exception), 'Database connection failed')

if __name__ == '__main__':
    unittest.main()
