import sys
from unittest.mock import MagicMock, patch

# In order to make the app start without connection errors, we MUST mock mysql.connector
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['knowledge_base'] = MagicMock()
sys.modules['services'] = MagicMock()

import app as app_module
import unittest

class TestInventoryCategory(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app_module.app.config['TESTING'] = True
        app_module.app.config['WTF_CSRF_ENABLED'] = False
        app_module.app.config['SECRET_KEY'] = 'test-secret'

        self.client = app_module.app.test_client()

        # We must patch the instance's method directly
        self.db_patcher = patch.object(app_module.db, 'execute_query', new_callable=MagicMock)
        self.mock_execute_query = self.db_patcher.start()

        # Patch check_permission
        self.perm_patcher = patch('app.check_permission', return_value=True)
        self.perm_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        self.perm_patcher.stop()

    def test_inventory_category_get(self):
        main_cats_data = [{'id': 1, 'main_catogory': 'Hardware', 'sub_catogory': None}]
        sub_cats_data = [{'id': 2, 'main_catogory': None, 'sub_catogory': 'Nails'}]

        def side_effect(query, params=None, commit=False):
            # Forgiving mock to handle both the real code and the prompt snippet
            if "main_catogory IS NOT NULL" in query or "inventory_main_categories" in query:
                return main_cats_data
            if "sub_catogory IS NOT NULL" in query:
                return sub_cats_data
            return []

        self.mock_execute_query.side_effect = side_effect

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        response = self.client.get('/inventory_category')

        self.assertEqual(response.status_code, 200)

        # Check actual calls, handling both expected variations
        calls = self.mock_execute_query.call_args_list
        self.assertTrue(any("main_catogory IS NOT NULL" in call[0][0] or "inventory_main_categories" in call[0][0] for call in calls))

        # We assume the template won't crash and will include these values
        html = response.data.decode('utf-8')
        self.assertIn('Hardware', html)

if __name__ == '__main__':
    unittest.main()
