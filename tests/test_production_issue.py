import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module

class TestProductionIssue(unittest.TestCase):
    def setUp(self):
        # Setup DB Mock
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        self.patchers = []

        # Patch Request
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        # Patch Session
        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)

        # Configure Session to pass login_required
        # session is treated as dict. 'user_id' in session
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

        # Patch Flash
        p_flash = patch('app.flash')
        self.mock_flash = p_flash.start()
        self.patchers.append(p_flash)

        # Patch Redirect
        p_red = patch('app.redirect')
        self.mock_redirect = p_red.start()
        self.patchers.append(p_red)

        # Patch URL For
        p_url = patch('app.url_for')
        self.mock_url_for = p_url.start()
        self.patchers.append(p_url)

        # Patch Permissions
        p_perm = patch('app.check_permission', return_value=True)
        self.mock_perm = p_perm.start()
        self.patchers.append(p_perm)

        # Patch User ID
        p_user = patch('app.get_current_user_id', return_value=1)
        self.mock_user = p_user.start()
        self.patchers.append(p_user)

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_submit_production_issue_success(self):
        self.mock_request.method = 'POST'

        form_data = {
            'issue_date': '2023-10-27',
            'job_no': 'JOB-001',
            'source_location': 'Warehouse A',
            'cost_account': 'Cost of Goods Sold',
            'narration': 'Test Issue'
        }

        mock_form = MagicMock()
        self.mock_request.form = mock_form

        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        def getlist_side_effect(key):
            if key == 'item_name[]': return ['Item 1', 'Item 2']
            if key == 'item_code[]': return ['I001', 'I002']
            if key == 'item_unit[]': return ['pcs', 'pcs']
            if key == 'unit_cost[]': return ['10.00', '20.00']
            if key == 'qty[]': return ['5', '3']
            return []

        mock_form.getlist.side_effect = getlist_side_effect

        # Configure DB
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 100

        # Call Route
        app_module.submit_production_issue()

        # Verify Flash
        self.mock_flash.assert_called_with('Production Issue recorded successfully. JV: 100', 'success')

        # Verify DB Calls
        jv_created = False
        for call in mock_cursor.execute.call_args_list:
            if "INSERT INTO jv_numbers" in call[0][0]:
                jv_created = True
                break
        self.assertTrue(jv_created, "JV Header should be created")

    def test_submit_production_issue_no_items(self):
        self.mock_request.method = 'POST'

        form_data = {
            'issue_date': '2023-10-27',
            'job_no': 'JOB-001',
            'source_location': 'Warehouse A',
            'cost_account': 'Cost of Goods Sold',
            'narration': 'Test Issue'
        }

        mock_form = MagicMock()
        self.mock_request.form = mock_form
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)
        mock_form.getlist.return_value = []

        app_module.submit_production_issue()

        self.mock_flash.assert_called_with('No items to issue', 'danger')

    def test_submit_production_issue_db_error(self):
        self.mock_request.method = 'POST'

        form_data = {
            'issue_date': '2023-10-27',
            'job_no': 'JOB-001',
            'source_location': 'Warehouse A',
            'cost_account': 'Cost of Goods Sold',
            'narration': 'Test Issue'
        }

        mock_form = MagicMock()
        self.mock_request.form = mock_form
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        def getlist_side_effect(key):
            if key == 'item_name[]': return ['Item 1']
            if key == 'item_code[]': return ['I001']
            if key == 'item_unit[]': return ['pcs']
            if key == 'unit_cost[]': return ['10.00']
            if key == 'qty[]': return ['5']
            return []

        mock_form.getlist.side_effect = getlist_side_effect

        # DB Error
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Connection Failed")

        app_module.submit_production_issue()

        found_error = False
        for call in self.mock_flash.call_args_list:
            args = call[0]
            if "Error processing issue" in args[0] and args[1] == 'danger':
                found_error = True
                break
        self.assertTrue(found_error, "Should flash error message on DB failure")
        mock_conn.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main()
