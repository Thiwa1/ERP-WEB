import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module

class TestBulkUpload(unittest.TestCase):
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

        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_bulk_upload_tally_check_fail(self):
        self.mock_request.method = 'POST'
        self.mock_request.files = {}

        form_data = {'save_tb': '1', 'opening_date': '2023-01-01'}

        # Configure Request Form Mock properly
        # request.form in bulk_upload_tb uses 'save_tb' in request.form
        # AND getlist()

        mock_form = MagicMock()
        self.mock_request.form = mock_form

        # .get() behavior not strictly needed if we mock __contains__ but
        # app uses 'save_tb' in request.form
        mock_form.__contains__.side_effect = lambda k: k in form_data

        # app uses request.form.getlist for arrays
        def getlist_side_effect(key):
            if key == 'account_name[]': return ['Acc1', 'Acc2']
            if key == 'dr[]': return ['100', '0']
            if key == 'cr[]': return ['0', '50'] # Diff 50
            return []
        mock_form.getlist.side_effect = getlist_side_effect

        # app also accesses form['opening_date'] or form.get('opening_date')
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)
        mock_form.__getitem__.side_effect = lambda k: form_data[k]

        app_module.bulk_upload_tb()

        found = False
        for call in self.mock_flash.call_args_list:
            if "Totals do not match" in call[0][0]:
                found = True
                break
        self.assertTrue(found, "Should flash totals do not match")

    def test_bulk_upload_tally_check_pass(self):
        self.mock_request.method = 'POST'
        self.mock_request.files = {}

        form_data = {'save_tb': '1', 'opening_date': '2023-01-01'}

        mock_form = MagicMock()
        self.mock_request.form = mock_form
        mock_form.__contains__.side_effect = lambda k: k in form_data

        def getlist_side_effect(key):
            if key == 'account_name[]': return ['Acc1', 'Acc2']
            if key == 'dr[]': return ['100', '0']
            if key == 'cr[]': return ['0', '100'] # Balanced
            return []
        mock_form.getlist.side_effect = getlist_side_effect
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)
        mock_form.__getitem__.side_effect = lambda k: form_data[k]

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 123

        app_module.bulk_upload_tb()

        found = False
        for call in self.mock_flash.call_args_list:
            if "TB Uploaded successfully" in call[0][0]:
                found = True
                break
        self.assertTrue(found, "Should flash success")

        found_date = False
        for call in mock_cursor.execute.call_args_list:
            args = call[0]
            if "INSERT INTO entry_details" in args[0]:
                params = args[1]
                if params[3] == '2023-01-01':
                    found_date = True
        self.assertTrue(found_date, "Should use provided opening date")

if __name__ == '__main__':
    unittest.main()
