import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.mock_env

# Mock libraries that might not be present
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Setup mocks for app.py imports
mock_flask = MagicMock()
mock_app = MagicMock()

# Define passthrough decorators to preserve the original functions
def passthrough_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

def simple_passthrough(f):
    return f

mock_app.context_processor = simple_passthrough
mock_app.template_filter = passthrough_decorator

mock_flask.Flask.return_value = mock_app
sys.modules['flask'].Flask = mock_flask.Flask
sys.modules['flask'].render_template = MagicMock()
sys.modules['flask'].request = MagicMock()
sys.modules['flask'].redirect = MagicMock()
sys.modules['flask'].url_for = MagicMock()
sys.modules['flask'].flash = MagicMock()
sys.modules['flask'].session = MagicMock()
sys.modules['flask'].make_response = MagicMock()
sys.modules['flask'].Response = MagicMock()
sys.modules['flask'].stream_with_context = MagicMock()

# Mock Database class before importing app
mock_database_module = MagicMock()
mock_db_class = MagicMock()
mock_database_module.Database = mock_db_class
sys.modules['database'] = mock_database_module

# Now import the functions to test
import app

class MockContext(dict):
    pass

class TestCurrencyLogic(unittest.TestCase):
    def setUp(self):
        # Reset DB mock for each test
        app.db.execute_query = MagicMock()

    def test_inject_currency_default(self):
        # Mock DB to raise exception or return empty to test default
        app.db.execute_query.side_effect = Exception("DB Error")

        result = app.inject_globals()
        self.assertEqual(result.get('company_currency'), 'LKR')

    def test_inject_currency_success(self):
        # Mock DB to return a currency
        app.db.execute_query.return_value = [{'company_curency': 'USD'}]
        app.db.execute_query.side_effect = None

        result = app.inject_globals()
        self.assertEqual(result.get('company_currency'), 'USD')

    def test_currency_filter_basic(self):
        ctx = MockContext()
        self.assertEqual(app.currency_filter(ctx, 1234.56), "1,234.56")
        self.assertEqual(app.currency_filter(ctx, 1000), "1,000.00")
        self.assertEqual(app.currency_filter(ctx, 0), "0.00")

    def test_currency_filter_string(self):
        ctx = MockContext()
        self.assertEqual(app.currency_filter(ctx, "1234.56"), "1,234.56")

    def test_currency_filter_none(self):
        ctx = MockContext()
        self.assertEqual(app.currency_filter(ctx, None), "0.00")

    def test_currency_filter_invalid(self):
        ctx = MockContext()
        self.assertEqual(app.currency_filter(ctx, "invalid"), "0.00")

    def test_currency_filter_unformattable(self):
        ctx = MockContext()
        # Test an unformattable object such as a list or a dict
        self.assertEqual(app.currency_filter(ctx, []), "0.00")
        self.assertEqual(app.currency_filter(ctx, {}), "0.00")

if __name__ == '__main__':
    unittest.main()
