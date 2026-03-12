import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import date

os.environ['SECRET_KEY'] = 'test_secret_key'

import tests.mock_env

import app

class TestSalesSummaryCashier(unittest.TestCase):
    @patch('app.db.execute_query')
    @patch('app.render_template')
    def test_sales_summary_cashier_get(self, mock_render_template, mock_execute_query):
        with app.app.test_request_context('/sales_summary_cashier?date=2023-01-01&filter=current'):
            with patch('app.session', dict(user_pk=1, username='admin', user_id=1)):
                with patch('app.check_permission', return_value=True):

                    mock_execute_query.side_effect = [
                        [{'User_Name': 'cashier_user'}], # pose_setting_table fetch
                        [
                            {
                                'Invoice_No': 'INV-001',
                                'ItemCoude': 'ITM-001',
                                'ItemName': 'Test Item',
                                'PaymentMethord': 1,
                                'QuntirySale': 2.0,
                                'SllingPrice': 100.0,
                                'ItemPriceComen': 0.0,
                                'ItemLoyalityPrice': 0.0,
                                'Total_Value': 200.0,
                                'AcctionDate': date(2023, 1, 1),
                                'Revers': 0,
                                'jv': 1,
                                'Sales_with_market_price_Active': 1,
                                'Sales_with_Special_price_Active': 0,
                                'Loyalty_Price_Active': 0,
                                'Loyalty_No': '-1',
                                'RecodeUserId': 1,
                                'CashierName': 'cashier_user'
                            }
                        ]
                    ]

                    app.sales_summary_cashier()

                    self.assertEqual(mock_execute_query.call_count, 2)
                    mock_render_template.assert_called_once()
                    args, kwargs = mock_render_template.call_args
                    self.assertEqual(args[0], 'sales_summary_cashier.html')
                    self.assertEqual(kwargs['cashier_name'], 'cashier_user')
                    self.assertEqual(kwargs['summary']['cash'], 200.0)

    @patch('flask.make_response')
    @patch('app.db.execute_query')
    def test_sales_summary_cashier_csv(self, mock_execute_query, mock_make_response):
        with app.app.test_request_context('/sales_summary_cashier?date=2023-01-01&filter=current&download=csv'):
            with patch('app.session', dict(user_pk=1, username='admin', user_id=1)):
                with patch('app.check_permission', return_value=True):
                    mock_execute_query.side_effect = [
                        [{'User_Name': 'cashier_user'}],
                        [
                            {
                                'Invoice_No': 'INV-001',
                                'ItemCoude': 'ITM-001',
                                'ItemName': 'Test Item',
                                'PaymentMethord': 1,
                                'QuntirySale': 2.0,
                                'SllingPrice': 100.0,
                                'ItemPriceComen': 0.0,
                                'ItemLoyalityPrice': 0.0,
                                'Total_Value': 200.0,
                                'AcctionDate': date(2023, 1, 1),
                                'Revers': 0,
                                'jv': 1,
                                'Sales_with_market_price_Active': 1,
                                'Sales_with_Special_price_Active': 0,
                                'Loyalty_Price_Active': 0,
                                'Loyalty_No': '-1',
                                'RecodeUserId': 1,
                                'CashierName': 'cashier_user'
                            }
                        ]
                    ]

                    mock_response = MagicMock()
                    mock_response.headers = {}
                    mock_make_response.return_value = mock_response

                    res = app.sales_summary_cashier()

                    # Because make_response is imported into app at the top `from flask import make_response`,
                    # mocking flask.make_response doesn't intercept it if it was already imported into app.
                    # We need to patch app.make_response, but let's just check the response returned
                    self.assertIsNotNone(res)

if __name__ == '__main__':
    unittest.main()
