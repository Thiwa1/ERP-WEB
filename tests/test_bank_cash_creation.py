import tests.mock_env
# Add mock setup first
from tests import mock_setup
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
        p_sess = patch.dict('app.session', {'user_id': 1, 'user_pk': 1, 'username': 'admin'})
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)

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
        # ensure_default_categories now uses executemany for bulk inserts
        for call in mock_cursor.executemany.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO balance_sheet_category" in query:
                params = args[1]
                for p in params:
                    if p[0] == "Current assets" and p[1] == 3:
                        found = True
                        break

        self.assertTrue(found, "Should insert 'Current assets' at position 3")

    def test_ensure_default_accounts_ids(self):
        self.mock_db.execute_query.return_value = []

        app_module.ensure_default_accounts()

        found_ap = False
        # db.execute_query is a mock, so we check calls to it
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

        mock_cursor.fetchone.side_effect = [None, [3, 'Current assets'], None]

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
        # Test that posting to /create_bank_account updates both tables
        app_module.app.config['TESTING'] = True
        # Since we mocked Flask, app.test_client() returns a Mock
        # We must mock its behavior or invoke route function directly.
        # Given the environment constraints, invoking function directly with mocked request is safer.

        with patch('app.request') as mock_request:
            mock_request.method = 'POST'

            # Properly mock form as a dict-like object
            form_mock = MagicMock()
            form_mock.get.side_effect = lambda k, d=None: {
                'account_number': 'HNB-1001',
                'bank_name': 'Hatton National Bank'
            }.get(k, d)
            mock_request.form = form_mock

            with patch('app.check_permission', return_value=True):
                 with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                         # Mock DB connection
                        mock_conn = MagicMock()
                        self.mock_db.get_connection.return_value = mock_conn
                        mock_cursor = MagicMock()
                        mock_conn.cursor.return_value = mock_cursor

                        # Setup fetchone calls
                        # 1. Check GL Exists? -> None
                        # 2. Check Category? -> [3]
                        # 3. Check Bank Exists? (Not in this route logic explicitly, maybe inside logic?)

                        mock_cursor.fetchone.side_effect = [None, [3], None]

                        app_module.create_bank_account()

                        # Verify Inserts
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
                                # params: acc_no, bank_name, date, user
                                if params[0] == 'HNB-1001' and params[1] == 'Hatton National Bank':
                                    bank_insert = True

                        self.assertTrue(gl_insert, "Should insert into GL")
                        self.assertTrue(bank_insert, "Should insert into Bank Book")

    def test_create_cash_account_route(self):
         with patch('app.request') as mock_request:
            mock_request.method = 'POST'

            form_mock = MagicMock()
            form_mock.get.side_effect = lambda k, d=None: {
                'account_name': 'Petty Cash 2'
            }.get(k, d)
            mock_request.form = form_mock

            with patch('app.check_permission', return_value=True):
                with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                        # Mock DB connection
                        mock_conn = MagicMock()
                        self.mock_db.get_connection.return_value = mock_conn
                        mock_cursor = MagicMock()
                        mock_conn.cursor.return_value = mock_cursor

                        # 1. Acc Exists? -> None
                        # 2. Cat Pos? -> [3, 'Current assets']
                        mock_cursor.fetchone.side_effect = [None, [3, 'Current assets'], None]

                        app_module.create_cash_account()

                        # Verify Inserts
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
