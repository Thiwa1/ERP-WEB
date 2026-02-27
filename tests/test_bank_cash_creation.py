import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module

class TestBankCashCreation(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        self.patchers = []
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        p_flash = patch('app.flash')
        self.mock_flash = p_flash.start()
        self.patchers.append(p_flash)

        p_red = patch('app.redirect')
        self.mock_redirect = p_red.start()
        self.patchers.append(p_red)

        p_perm = patch('app.check_permission', return_value=True)
        self.mock_perm = p_perm.start()
        self.patchers.append(p_perm)

        p_user = patch('app.get_current_user_id', return_value=1)
        self.mock_user = p_user.start()
        self.patchers.append(p_user)

        # FIX: Patch Session to satisfy login_required
        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_ensure_default_categories(self):
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None

        app_module.ensure_default_categories()

        found = False
        for call in mock_cursor.execute.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO balance_sheet_category" in query:
                params = args[1]
                if params[0] == "Current assets" and params[1] == 3:
                    found = True
                    break

        self.assertTrue(found, "Should insert 'Current assets' at position 3")

    def test_ensure_default_accounts_ids(self):
        self.mock_db.execute_query.return_value = []

        app_module.ensure_default_accounts()

        found_ap = False
        for call in self.mock_db.execute_query.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO new_account_table" in query:
                params = args[1]
                if params[0] == "Account Payable":
                    if params[1] == 6:
                        found_ap = True

        self.assertTrue(found_ap, "Account Payable should use BS Position 6")

    def test_create_bank_account_route(self):
        self.mock_request.method = 'POST'

        form_data = {
            'account_number': 'HNB-1001',
            'bank_name': 'Hatton National Bank'
        }
        self.mock_request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [None, [3], None]

        app_module.create_bank_account()

        self.mock_flash.assert_called_with('New bank account created', 'success')

        gl_insert = False
        bank_insert = False

        for call in mock_cursor.execute.call_args_list:
            args = call[0]
            query = args[0]

            if "INSERT INTO new_account_table" in query:
                params = args[1]
                if params[0] == 'HNB-1001': gl_insert = True

            if "INSERT INTO bank_book" in query:
                params = args[1]
                if params[0] == 'HNB-1001' and params[1] == 'Hatton National Bank':
                    bank_insert = True

        self.assertTrue(gl_insert, "Should insert into GL")
        self.assertTrue(bank_insert, "Should insert into Bank Book")

    def test_create_cash_account_route(self):
        self.mock_request.method = 'POST'

        form_data = {
            'account_name': 'Petty Cash 2'
        }
        self.mock_request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [None, [3], None]

        app_module.create_cash_account()

        self.mock_flash.assert_called_with('New cash account created', 'success')

        gl_insert = False
        cash_insert = False

        for call in mock_cursor.execute.call_args_list:
            args = call[0]
            query = args[0]

            if "INSERT INTO new_account_table" in query:
                params = args[1]
                if params[0] == 'Petty Cash 2': gl_insert = True

            if "INSERT INTO cash_book" in query:
                params = args[1]
                if params[0] == 'Petty Cash 2':
                    cash_insert = True

        self.assertTrue(gl_insert, "Should insert into GL")
        self.assertTrue(cash_insert, "Should insert into Cash Book")

if __name__ == '__main__':
    unittest.main()
