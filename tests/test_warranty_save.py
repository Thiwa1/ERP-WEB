import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib

# 1. Setup global mocks before import
import tests.mock_env

# Add mocks specifically needed
mock_flask_module = sys.modules['flask']

# Ensure 'request' has 'form' mock
mock_request = mock_flask_module.request
mock_request.form = MagicMock()

# Mock session as a dict
mock_session = {'user_id': 'admin', 'user_pk': 1, 'username': 'admin'}
mock_flask_module.session = mock_session

# Import app
import app as app_module

# Force reload to ensure it picks up our sys.modules['flask']
importlib.reload(app_module)

class TestWarrantySave(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_flask_module.request.reset_mock()
        mock_flask_module.flash.reset_mock()
        mock_flask_module.redirect.reset_mock()
        mock_flask_module.url_for.reset_mock()

        # Reset Session
        mock_session.clear()
        mock_session.update({'user_id': 'admin', 'user_pk': 1, 'username': 'admin'})

        # Patch app.db
        self.mock_db = MagicMock()
        self.db_patcher = patch('app.db', self.mock_db)
        self.db_patcher.start()

        # Update our references to the mocks used by the app
        self.actual_request_mock = app_module.request
        self.actual_flash_mock = app_module.flash
        self.actual_redirect_mock = app_module.redirect
        self.actual_url_for_mock = app_module.url_for
        self.actual_url_for_mock.return_value = '/warranty_period'

        # Setup mock connection and cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_db.get_connection.return_value = self.mock_conn

    def tearDown(self):
        self.db_patcher.stop()

    def test_warranty_save_insert(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        form_data = {
            'id[]': ['0'],
            'name[]': ['Item 1'],
            'year[]': ['1'],
            'month[]': ['0'],
            'day[]': ['0']
        }
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.getlist.side_effect = lambda k: form_data.get(k, [])

        # Execute
        res = app_module.warranty_save()

        # Assertions
        self.assertTrue(self.mock_conn.start_transaction.called)

        # Verify insert execution
        self.assertEqual(self.mock_cursor.execute.call_count, 1)
        args, kwargs = self.mock_cursor.execute.call_args
        query = args[0]
        params = args[1]
        self.assertIn('INSERT INTO inventory_vorenty_period', query)
        self.assertEqual(params, ('1', '0', '0', 'Item 1'))

        self.assertTrue(self.mock_conn.commit.called)
        self.assertTrue(self.mock_cursor.close.called)
        self.assertTrue(self.mock_conn.close.called)

        self.actual_flash_mock.assert_called_once_with('Warranty data saved successfully', 'success')
        self.actual_url_for_mock.assert_called_once_with('warranty_period')
        self.actual_redirect_mock.assert_called_once_with('/warranty_period')

    def test_warranty_save_update(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        form_data = {
            'id[]': ['5'],
            'name[]': ['Item 2'],
            'year[]': ['2'],
            'month[]': ['6'],
            'day[]': ['15']
        }
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.getlist.side_effect = lambda k: form_data.get(k, [])

        # Execute
        res = app_module.warranty_save()

        # Assertions
        # Verify update execution
        self.assertEqual(self.mock_cursor.execute.call_count, 1)
        args, kwargs = self.mock_cursor.execute.call_args
        query = args[0]
        params = args[1]
        self.assertIn('UPDATE inventory_vorenty_period', query)
        self.assertEqual(params, ('2', '6', '15', 'Item 2', 5))

        self.assertTrue(self.mock_conn.commit.called)
        self.actual_flash_mock.assert_called_once_with('Warranty data saved successfully', 'success')

    def test_warranty_save_mixed(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        form_data = {
            'id[]': ['0', '10'],
            'name[]': ['New Item', 'Existing Item'],
            'year[]': ['1', '3'],
            'month[]': ['0', '0'],
            'day[]': ['0', '0']
        }
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.getlist.side_effect = lambda k: form_data.get(k, [])

        # Execute
        res = app_module.warranty_save()

        # Assertions
        self.assertEqual(self.mock_cursor.execute.call_count, 2)

        # Call 1 (Insert)
        args1, kwargs1 = self.mock_cursor.execute.call_args_list[0]
        self.assertIn('INSERT INTO inventory_vorenty_period', args1[0])
        self.assertEqual(args1[1], ('1', '0', '0', 'New Item'))

        # Call 2 (Update)
        args2, kwargs2 = self.mock_cursor.execute.call_args_list[1]
        self.assertIn('UPDATE inventory_vorenty_period', args2[0])
        self.assertEqual(args2[1], ('3', '0', '0', 'Existing Item', 10))

        self.assertTrue(self.mock_conn.commit.called)
        self.actual_flash_mock.assert_called_once_with('Warranty data saved successfully', 'success')

    def test_warranty_save_exception(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        form_data = {
            'id[]': ['0'],
            'name[]': ['Item Error'],
            'year[]': ['1'],
            'month[]': ['0'],
            'day[]': ['0']
        }
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.getlist.side_effect = lambda k: form_data.get(k, [])

        # Make cursor.execute raise an exception
        self.mock_cursor.execute.side_effect = Exception("DB Error")

        # Execute
        res = app_module.warranty_save()

        # Assertions
        # Verify execution was attempted
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

        # Verify commit was not called
        self.assertFalse(self.mock_conn.commit.called)

        # Check flash message
        self.actual_flash_mock.assert_called_once_with('Error saving data: DB Error', 'danger')

if __name__ == '__main__':
    unittest.main()
