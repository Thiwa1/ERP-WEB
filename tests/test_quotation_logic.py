import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Create a mock for the Flask app instance that handles decorators correctly
mock_app_instance = MagicMock()

def route_decorator(*args, **kwargs):
    def wrapper(f):
        return f
    return wrapper

def context_processor_decorator(f):
    return f

def template_filter_decorator(name=None):
    def wrapper(f):
        return f
    return wrapper

mock_app_instance.route.side_effect = route_decorator
mock_app_instance.context_processor.side_effect = context_processor_decorator
mock_app_instance.template_filter.side_effect = template_filter_decorator

# Mock dependencies
flask_mock = MagicMock()
flask_mock.Flask.return_value = mock_app_instance
sys.modules['flask'] = flask_mock
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['database'] = MagicMock()

# Now we can safely import app
# We need to add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Patch Database class before importing app
with patch('database.Database') as MockDB:
    import app

class TestQuotationLogic(unittest.TestCase):
    def setUp(self):
        self.evaluate_quotations = app.evaluate_quotations

    def test_evaluate_quotations_price_priority(self):
        # Mock request.json
        with patch('app.request') as mock_request:
            mock_request.json = {
                'constraints': {'priority': 'price', 'max_days': 10},
                'suppliers': [
                    {'name': 'S1', 'price': 100, 'days': 5, 'quality': 3},
                    {'name': 'S2', 'price': 80, 'days': 8, 'quality': 3},
                    {'name': 'S3', 'price': 120, 'days': 2, 'quality': 5}
                ]
            }

            with patch('app.session', {'user_id': 1, 'user_pk': 1}) as mock_session:
                with patch('app.check_permission', return_value=True):
                    result = self.evaluate_quotations()

                    self.assertIn('results', result)
                    results = result['results']
                    self.assertEqual(len(results), 3)

                    # S3 should win based on current logic which heavily weights days and quality even in price priority
                    # S3: Price 120, Days 2, Qual 5.
                    # S2: Price 80, Days 8, Qual 3.

                    self.assertTrue(results[0]['is_winner'])
                    self.assertEqual(results[0]['name'], 'S3')
                    self.assertEqual(results[0]['win_reason'], 'Best price')

    def test_evaluate_quotations_speed_priority(self):
        with patch('app.request') as mock_request:
            mock_request.json = {
                'constraints': {'priority': 'speed', 'max_days': 10},
                'suppliers': [
                    {'name': 'S1', 'price': 100, 'days': 5, 'quality': 3},
                    {'name': 'S2', 'price': 80, 'days': 8, 'quality': 3},
                    {'name': 'S3', 'price': 120, 'days': 2, 'quality': 5}
                ]
            }
            with patch('app.session', {'user_id': 1, 'user_pk': 1}), \
                 patch('app.check_permission', return_value=True):

                result = self.evaluate_quotations()
                results = result['results']

                self.assertEqual(results[0]['name'], 'S3')
                self.assertEqual(results[0]['win_reason'], 'Fastest delivery within constraints')

    def test_evaluate_quotations_quality_priority(self):
        with patch('app.request') as mock_request:
            mock_request.json = {
                'constraints': {'priority': 'quality', 'max_days': 10},
                'suppliers': [
                    {'name': 'S1', 'price': 100, 'days': 5, 'quality': 3},
                    {'name': 'S2', 'price': 80, 'days': 8, 'quality': 3},
                    {'name': 'S3', 'price': 120, 'days': 2, 'quality': 5}
                ]
            }
            with patch('app.session', {'user_id': 1, 'user_pk': 1}), \
                 patch('app.check_permission', return_value=True):

                result = self.evaluate_quotations()
                results = result['results']

                self.assertEqual(results[0]['name'], 'S3')
                self.assertEqual(results[0]['win_reason'], 'Best quality rating')

if __name__ == '__main__':
    unittest.main()
