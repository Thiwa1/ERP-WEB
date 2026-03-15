
import sys
from unittest.mock import MagicMock
if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()
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
mock_session = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}
mock_flask_module.session = mock_session

# Import app
import app as app_module

# Force reload to ensure it picks up our sys.modules['flask']
importlib.reload(app_module)

class TestAddMainCategory(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_flask_module.request.reset_mock()
        mock_flask_module.flash.reset_mock()
        mock_flask_module.redirect.reset_mock()
        mock_flask_module.url_for.reset_mock()

        # Reset Session
        mock_session.clear()
        mock_session.update({'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'})

        # Patch app.db (Instance)
        self.mock_db = MagicMock()
        self.db_patcher = patch('app.db', self.mock_db)
        self.db_patcher.start()

        # Update our references to the mocks used by the app
        self.actual_request_mock = app_module.request
        self.actual_flash_mock = app_module.flash
        self.actual_redirect_mock = app_module.redirect
        self.actual_url_for_mock = app_module.url_for
        self.actual_url_for_mock.return_value = '/inventory_category'

    def tearDown(self):
        self.db_patcher.stop()

    def test_add_main_category_success(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        # Setup form data
        form_data = {'main_category': 'Electronics'}
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        # Execute
        res = app_module.add_main_category()

        # Assertions
        self.mock_db.execute_query.assert_called_once_with(
            "INSERT INTO inventory_carogory (id, main_catogory, sub_catogory) VALUES (0, %s, NULL)",
            ('Electronics',),
            commit=True
        )
        self.actual_flash_mock.assert_called_once_with('Main category added', 'success')
        self.actual_url_for_mock.assert_called_once_with('inventory_category')
        self.actual_redirect_mock.assert_called_once_with('/inventory_category')

    def test_add_main_category_missing_name(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        # Setup empty form data
        form_data = {'main_category': ''}
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        # Execute
        res = app_module.add_main_category()

        # Assertions
        self.mock_db.execute_query.assert_not_called()
        self.actual_flash_mock.assert_not_called()
        self.actual_url_for_mock.assert_called_once_with('inventory_category')
        self.actual_redirect_mock.assert_called_once_with('/inventory_category')

if __name__ == '__main__':
    unittest.main()
