import unittest
from unittest.mock import MagicMock, patch
import sys

# 1. Setup Mocks for Dependencies (Isolated via test file, but pollution remains for session)
# In a real scenario, we would use patch.dict(sys.modules, ...) but app imports at top level.
# So we must mock before import.
# To minimize impact, we could use importlib.reload in tearDown if we cared about restoring state,
# but for this task, ensuring this test file runs standalone is key.

sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql'] = MagicMock()

# Mock Flask
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask

# Configure Flask Mock
mock_app_instance = MagicMock()
mock_flask.Flask.return_value = mock_app_instance

# Mock decorators to return function unmodified
def identity_decorator(f):
    return f

def route_side_effect(*args, **kwargs):
    return identity_decorator

def template_filter_side_effect(*args, **kwargs):
    return identity_decorator

mock_app_instance.route.side_effect = route_side_effect
mock_app_instance.context_processor.side_effect = identity_decorator
mock_app_instance.template_filter.side_effect = template_filter_side_effect

# 2. Import app
import app as app_module

class TestInventoryTransfer(unittest.TestCase):
    def setUp(self):
        # Mock DB
        self.mock_db = MagicMock()
        app_module.db = self.mock_db
        app_module.app_initialized = True

        # Mock Session
        self.mock_session = app_module.session
        # Setup session to pass login_required
        session_dict = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}

        self.mock_session.__getitem__ = MagicMock(side_effect=lambda k: session_dict[k])
        self.mock_session.get = MagicMock(side_effect=lambda k, d=None: session_dict.get(k, d))
        self.mock_session.__contains__ = MagicMock(side_effect=lambda k: k in session_dict)

        # Mock Global Helpers
        app_module.url_for = MagicMock(return_value='/inventory_transfer')
        app_module.redirect = MagicMock(return_value='Redirected')
        app_module.flash = MagicMock()
        app_module.get_current_user_id = MagicMock(return_value=1)

    def tearDown(self):
        pass

    def test_submit_transfer_success(self):
        # Mock Request
        mock_request = MagicMock()
        mock_request.method = 'POST'

        form_data = {
            'transfer_date': '2023-10-27',
            'job_no': 'JOB-001',
            'from_location': 'Warehouse A',
            'to_location': 'Warehouse B',
            'narration': 'Test Transfer'
        }
        mock_request.form.get = MagicMock(side_effect=lambda k, d=None: form_data.get(k, d))

        def getlist(key):
            if key == 'item_name[]': return ['Item 1', 'Item 2']
            if key == 'item_code[]': return ['C001', 'C002']
            if key == 'item_unit[]': return ['pcs', 'kg']
            if key == 'item_cost[]': return ['100', '50']
            if key == 'qty[]': return ['10', '5']
            return []
        mock_request.form.getlist = MagicMock(side_effect=getlist)

        app_module.request = mock_request

        with patch('app.check_permission', return_value=True):
            # Mock DB Connection
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 100

            response = app_module.submit_inventory_transfer()

            self.assertEqual(response, 'Redirected')
            mock_conn.commit.assert_called_once()

            calls = mock_cursor.execute.call_args_list
            # Verify correct table name usage (inventory_recod)
            inv_calls = [c for c in calls if "INSERT INTO inventory_recod" in c[0][0]]
            self.assertEqual(len(inv_calls), 4)

    def test_submit_transfer_same_location(self):
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.form.get = MagicMock(side_effect=lambda k, d=None: {'from_location': 'A', 'to_location': 'A'}.get(k, d))
        mock_request.form.getlist = MagicMock(return_value=['Item 1'])
        app_module.request = mock_request

        with patch('app.check_permission', return_value=True):
            response = app_module.submit_inventory_transfer()

            self.assertEqual(response, 'Redirected')
            app_module.flash.assert_called_with('Source and Destination locations must be different', 'danger')
            self.mock_db.get_connection.assert_not_called()

    def test_submit_transfer_no_items(self):
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.form.get = MagicMock(return_value='A')
        mock_request.form.getlist = MagicMock(return_value=[]) # No items
        app_module.request = mock_request

        with patch('app.check_permission', return_value=True):
            response = app_module.submit_inventory_transfer()

            self.assertEqual(response, 'Redirected')
            app_module.flash.assert_called_with('No items to transfer', 'danger')
            self.mock_db.get_connection.assert_not_called()

    def test_submit_transfer_db_error(self):
        mock_request = MagicMock()
        mock_request.method = 'POST'
        mock_request.form.get = MagicMock(side_effect=lambda k, d=None: {'from_location': 'A', 'to_location': 'B'}.get(k, d))

        def getlist(key):
            if key in ['item_name[]', 'item_code[]', 'item_unit[]', 'item_cost[]', 'qty[]']:
                return ['1']
            return []
        mock_request.form.getlist = MagicMock(side_effect=getlist)
        app_module.request = mock_request

        with patch('app.check_permission', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            mock_cursor.execute.side_effect = Exception("DB Error")

            response = app_module.submit_inventory_transfer()

            self.assertEqual(response, 'Redirected')
            mock_conn.rollback.assert_called_once()
            args, _ = app_module.flash.call_args
            self.assertIn('Error processing transfer', args[0])

if __name__ == '__main__':
    unittest.main()
