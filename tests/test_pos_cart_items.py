import sys
import os
import unittest
from unittest.mock import MagicMock
from datetime import datetime

os.environ['SECRET_KEY'] = 'test_secret_key'
import tests.mock_env

from app import _process_pos_cart_items

class TestProcessPOSCartItems(unittest.TestCase):
    def test_process_pos_cart_items_params(self):
        mock_cursor = MagicMock()
        cart = [{
            'code': 'ITEM01',
            'name': 'Test Item',
            'unit': 'PCS',
            'price_market': 100,
            'price_special': 90,
            'price_loyalty': 80,
            'qty': 2,
            'cost': 50,
            'total': 200
        }]
        settings = {
            'market_active': 1,
            'special_active': 0,
            'loyalty_active': 0,
            'location': 'Store1',
            'cash_ac': 'CashInHand',
            'bank_ac': 'Bank1'
        }
        payment = {'method': 1}
        customer = {'loyalty_no': '123'}
        current_user = 'ADM01'
        current_user_pk = 1
        invoice_no = 'INV001'
        jv_no = 100
        today_date = datetime.now().date()

        _process_pos_cart_items(mock_cursor, cart, settings, current_user, current_user_pk, payment, customer, invoice_no, jv_no, today_date)

        self.assertTrue(mock_cursor.executemany.called)

        args, _ = mock_cursor.executemany.call_args_list[0]
        query, params_list = args

        self.assertEqual(len(params_list[0]), 21)

        params = params_list[0]
        self.assertEqual(params[0], 'ITEM01') # ItemCoude
        self.assertEqual(params[1], 'Test Item') # ItemName
        self.assertEqual(params[9], 1) # RecodeUserId (current_user_pk)
        self.assertEqual(params[10], 'Store1') # Location

if __name__ == '__main__':
    unittest.main()
