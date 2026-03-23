import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import os

if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()

# Setup global mocks before import
if 'flask' not in sys.modules:
    mock_flask = MagicMock()
    sys.modules['flask'] = mock_flask
    mock_app_instance = MagicMock()
    mock_flask.Flask.return_value = mock_app_instance
    mock_app_instance.route = lambda *args, **kwargs: lambda f: f
    mock_app_instance.context_processor = lambda f: f
    mock_app_instance.template_filter = lambda *args: lambda f: f
    # Mock session
    mock_flask.session = {'user_id': 'test_user'}

if 'mysql' not in sys.modules:
    mock_mysql = MagicMock()
    sys.modules['mysql'] = mock_mysql
    sys.modules['mysql.connector'] = mock_mysql

sys.modules['jinja2'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()

os.environ['SECRET_KEY'] = 'test-secret-key-for-mock-env'

import app

class TestApiGetItemPrices(unittest.TestCase):
    def setUp(self):
        # Reset the mock before each test
        app.db.execute_query = MagicMock()

    def test_empty_item_ids(self):
        # Empty string
        result = app.api_get_item_prices("")
        self.assertEqual(result, json.dumps({}))
        app.db.execute_query.assert_not_called()

        # Whitespace
        result = app.api_get_item_prices("   ")
        self.assertEqual(result, json.dumps({}))
        app.db.execute_query.assert_not_called()

        # Invalid strings
        result = app.api_get_item_prices("a, b, c")
        self.assertEqual(result, json.dumps({}))
        app.db.execute_query.assert_not_called()

        # Mixed spaces and invalid strings
        result = app.api_get_item_prices(" , x, y ")
        self.assertEqual(result, json.dumps({}))
        app.db.execute_query.assert_not_called()

    def test_valid_item_ids(self):
        # Mock database return
        app.db.execute_query.return_value = [
            {'inventory_price_link': 1, 'inventory_price_selling': 100},
            {'inventory_price_link': 1, 'inventory_price_selling': 110},
            {'inventory_price_link': 2, 'inventory_price_selling': 200}
        ]

        result_str = app.api_get_item_prices("1, 2")
        result = json.loads(result_str)

        self.assertEqual(result, {'1': [100, 110], '2': [200]})

        # Check query and tuple passed
        args, kwargs = app.db.execute_query.call_args
        query, tuple_args = args
        self.assertIn("SELECT inventory_price_link, inventory_price_selling", query)
        self.assertIn("IN (%s, %s)", query)
        self.assertEqual(tuple_args, ('1', '2'))

    def test_with_mixed_valid_and_invalid_item_ids(self):
        # Mock database return for a single valid ID
        app.db.execute_query.return_value = [
            {'inventory_price_link': 1, 'inventory_price_selling': 100}
        ]

        # Call with mixed inputs
        app.db.execute_query.return_value = [
            {'inventory_price_link': 1, 'inventory_price_selling': 100},
            {'inventory_price_link': 2, 'inventory_price_selling': 200}
        ]

        result_str = app.api_get_item_prices("1, invalid, 2 ")
        result = json.loads(result_str)

        self.assertEqual(result, {'1': [100], '2': [200]})

        args, kwargs = app.db.execute_query.call_args
        query, tuple_args = args
        self.assertIn("IN (%s, %s)", query)
        self.assertEqual(tuple_args, ('1', '2'))
