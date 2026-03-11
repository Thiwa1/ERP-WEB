import sys
from unittest.mock import MagicMock

# --- System-level Mocks for Flask and MySQL ---
# We need to define these BEFORE importing app.py

# 1. Mock Flask App Instance
mock_flask_app = MagicMock()
mock_flask_app.config = {}

# Define passthrough decorators
def passthrough_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

def simple_passthrough(f):
    return f

# Configure app methods to be passthrough
# @app.route(...)
mock_flask_app.route = passthrough_decorator
# @app.context_processor
mock_flask_app.context_processor = simple_passthrough
# @app.template_filter(...)
mock_flask_app.template_filter = passthrough_decorator
# @app.before_request
mock_flask_app.before_request = simple_passthrough

# 2. Mock Flask Module
mock_flask_module = MagicMock()
mock_flask_module.Flask.return_value = mock_flask_app
# Mock other flask objects that app.py imports
mock_flask_module.request = MagicMock()
mock_flask_module.session = {}
mock_flask_module.redirect = MagicMock()
mock_flask_module.url_for = MagicMock()
mock_flask_module.flash = MagicMock()
mock_flask_module.make_response = MagicMock()
mock_flask_module.Response = MagicMock()
mock_flask_module.stream_with_context = MagicMock()
# render_template returning empty string is fine for now, or mock if needed
mock_flask_module.render_template = MagicMock(return_value="")

# Apply to sys.modules
sys.modules['flask'] = mock_flask_module
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()


# Define pass_context explicitly
def mock_pass_context(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        return args[0]
    def decorator(f):
        return f
    return decorator

# Create mock module
class MockJinja2:
    pass_context = mock_pass_context
    Environment = MagicMock()
    FileSystemLoader = MagicMock()
    select_autoescape = MagicMock()

sys.modules['jinja2'] = MockJinja2()

sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()


# --- Import App ---
import app as app_module
import unittest
from unittest.mock import patch
import json
from datetime import date

class TestPOSSale(unittest.TestCase):
    def setUp(self):
        # Ensure testing mode
        app_module.app.config['TESTING'] = True

        # Setup Session (simulate logged in user)
        # We manipulate the dict that app.py imported as 'session'
        app_module.session.clear()
        app_module.session.update({
            'user_id': 'ADM001',
            'user_pk': 1,
            'username': 'admin'
        })

        # Mock Database
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        # Mock Permission Check (globally for this test class)
        self.patcher_perm = patch('app.check_permission', return_value=True)
        self.patcher_perm.start()

    def tearDown(self):
        self.patcher_perm.stop()

    def test_submit_pos_sale_success_cash_no_vat(self):
        # Prepare Request Data
        payload = {
            'cart': [{
                'code': 'I001', 'name': 'Item A', 'unit': 'Nos',
                'price_market': 100, 'price_special': 0, 'price_loyalty': 0,
                'qty': 1, 'cost': 50, 'total': 100
            }],
            'payment': {'method': 1}, # Cash
            'settings': {
                'cash_ac': 'Cash Main',
                'bank_ac': 'Bank A',
                'vat_enable': 0,
                'location': 'Store',
                'market_active': 1
            },
            'customer': {'loyalty_no': 'L001'}
        }

        # Mock Database Connection/Cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.lastrowid = 100
        mock_cursor.fetchone.return_value = None

        # Mock Request Object
        with patch.object(app_module, 'request') as mock_request:
            mock_request.json = payload
            mock_request.method = 'POST'

            # CALL THE FUNCTION
            # submit_pos_sale is wrapped by login_required.
            # login_required checks session. We set session in setUp.
            response = app_module.submit_pos_sale()

            # Assertions
            # The function returns a dict {success: True, ...}
            self.assertTrue(response['success'])
            expected_inv = f'{date.today().year}POS-100'
            self.assertEqual(response['invoice_no'], expected_inv)

            # Verify SQL
            calls = [str(call) for call in mock_cursor.execute.call_args_list]

            # Tables touched
            self.assertTrue(any("INSERT INTO pos_invoice_no" in c for c in calls))
            self.assertTrue(any("UPDATE pos_invoice_no" in c for c in calls))
            self.assertTrue(any("INSERT INTO jv_numbers" in c for c in calls))
            self.assertTrue(any("INSERT INTO pos_sales_invoice_01" in c for c in [str(call) for call in mock_cursor.executemany.call_args_list]))
            self.assertTrue(any("INSERT INTO inventory_recod" in c for c in [str(call) for call in mock_cursor.executemany.call_args_list]))

            # Verify GL Entries (Cash & Sales)
            # We look for param matches in the call args
            cash_found = False
            sales_found = False
            cogs_found = False

            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                sql = args[0]
                if "INSERT INTO entry_details" in sql:
                    params = args[1]
                    # params usually: (account_name, dr, cr/eff_date... wait query structure)
                    # Query in app.py:
                    # VALUES (%s, %s, %s, %s, %s, %s, %s)
                    # (ac_name, total_sale_value, today_date, today_date, nar, user, jv)
                    # So params[0] is name, params[1] is DR

                    if params[0] == 'Cash Main' and params[1] == 100:
                        cash_found = True

                    # Credit Sales
                    # VALUES (%s, %s, %s, %s, %s, %s, %s)
                    # (Sales, net_sales, ...)
                    # WAIT.
                    # Debit Query: VALUES (ac_name, total_sale_value, ...)
                    # Credit Query: VALUES ('Sales', net_sales, ...)
                    # BOTH use the SAME query structure in app.py?
                    # Let's check app.py code read previously.
                    # Debit: enty_values_DR is 2nd column.
                    # Credit: enty_values_CR is 2nd column.
                    # app.py:
                    # Debit: INSERT INTO entry_details (account_name, enty_values_DR, ...) VALUES ...
                    # Credit: INSERT INTO entry_details (account_name, enty_values_CR, ...) VALUES ...
                    # So params[1] is amount in BOTH cases.

                    if params[0] == 'Sales' and params[1] == 100:
                        sales_found = True

                    if params[0] == 'Cost Of Goods Sold' and params[1] == 50:
                        cogs_found = True

            self.assertTrue(cash_found, "Cash Debit entry not found")
            self.assertTrue(sales_found, "Sales Credit entry not found")
            self.assertTrue(cogs_found, "COGS Debit entry not found")

            mock_conn.commit.assert_called()

    def test_submit_pos_sale_success_card_vat(self):
        payload = {
            'cart': [{
                'code': 'I001', 'name': 'Item A', 'unit': 'Nos',
                'price_market': 118, 'price_special': 0, 'price_loyalty': 0,
                'qty': 1, 'cost': 50, 'total': 118
            }],
            'payment': {'method': 2}, # Card/Bank
            'settings': {
                'cash_ac': 'Cash Main',
                'bank_ac': 'Bank A',
                'vat_enable': 1,
                'location': 'Store'
            }
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 100
        # fetchone used for VAT rate check. Return [18.0]
        mock_cursor.fetchone.return_value = [18.0]

        with patch.object(app_module, 'request') as mock_request:
            mock_request.json = payload
            mock_request.method = 'POST'

            response = app_module.submit_pos_sale()
            self.assertTrue(response['success'])

            bank_found = False
            sales_found = False
            vat_found = False

            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                sql = args[0]
                if "INSERT INTO entry_details" in sql:
                    params = args[1]
                    # Bank Debit 118
                    if params[0] == 'Bank A' and abs(params[1] - 118.0) < 0.01:
                        bank_found = True
                    # Sales Credit 100 (118 / 1.18)
                    if params[0] == 'Sales' and abs(params[1] - 100.0) < 0.01:
                        sales_found = True
                    # VAT Credit 18
                    if params[0] == 'VAT Control' and abs(params[1] - 18.0) < 0.01:
                        vat_found = True

            self.assertTrue(bank_found, "Bank Debit incorrect")
            self.assertTrue(sales_found, "Sales Credit incorrect")
            self.assertTrue(vat_found, "VAT Credit incorrect")

    def test_submit_pos_sale_empty_cart(self):
        with patch.object(app_module, 'request') as mock_request:
            mock_request.json = {'cart': []}
            mock_request.method = 'POST'

            # Expecting tuple ({'error':...}, 400)
            response = app_module.submit_pos_sale()
            self.assertEqual(response[0], {'error': 'Cart is empty'})
            self.assertEqual(response[1], 400)

    def test_submit_pos_sale_db_error(self):
        payload = {'cart': [{'code': 'A', 'total': 10, 'qty':1, 'cost':5, 'name':'A', 'unit':'u'}]}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Fail")

        with patch.object(app_module, 'request') as mock_request:
            mock_request.json = payload
            mock_request.method = 'POST'

            # Expecting tuple ({'error':...}, 500)
            response = app_module.submit_pos_sale()
            self.assertEqual(response[1], 500)
            mock_conn.rollback.assert_called()

if __name__ == '__main__':
    unittest.main()
