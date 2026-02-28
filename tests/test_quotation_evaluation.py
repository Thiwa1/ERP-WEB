
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Dependencies
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

class MockFlask:
    def __init__(self, name):
        self.config = {}
        self.secret_key = None
        self.view_functions = {}

    def route(self, rule, **options):
        def decorator(f):
            self.view_functions[rule] = f
            return f
        return decorator

    def context_processor(self, f):
        return f

    def template_filter(self, name=None):
        def decorator(f):
            return f
        return decorator

    def before_request(self, f):
        return f

    def run(self, **kwargs):
        pass

mock_flask.Flask = MockFlask
mock_flask.render_template = MagicMock()
mock_flask.request = MagicMock()
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()

# Import app
import app

class TestQuotationEvaluation(unittest.TestCase):
    def setUp(self):
        # Setup any necessary context
        pass

    def test_price_priority_winner(self):
        # Mock request data
        data = {
            'constraints': {'priority': 'price', 'max_days': 20},
            'suppliers': [
                {'name': 'SupA', 'price': 100, 'days': 10, 'quality': 5},
                {'name': 'SupB', 'price': 200, 'days': 5, 'quality': 5}
            ]
        }

        # Mock request.json and session
        with patch('app.request') as mock_req:
            mock_req.json = data
            # Use 'user_id' in session to bypass @login_required check
            with patch('app.session', {'user_id': 'admin'}):
                # Call function
                response = app.evaluate_quotations()

                # Check results
                self.assertIn('results', response)
                results = response['results']
                self.assertEqual(len(results), 2)

                # Verify Winner (Lowest Price)
                # SupA Price 100 < SupB Price 200
                self.assertEqual(results[0]['name'], 'SupA')
                self.assertTrue(results[0].get('is_winner'))
                self.assertEqual(results[0]['win_reason'], 'Best price')

    def test_speed_priority_winner(self):
        data = {
            'constraints': {'priority': 'speed', 'max_days': 20},
            'suppliers': [
                {'name': 'SupA', 'price': 100, 'days': 10, 'quality': 5},
                {'name': 'SupB', 'price': 200, 'days': 5, 'quality': 5}
            ]
        }

        with patch('app.request') as mock_req:
            mock_req.json = data
            with patch('app.session', {'user_id': 'admin'}):
                response = app.evaluate_quotations()
                results = response['results']

                # Verify Winner (Fastest)
                # SupB Days 5 < SupA Days 10
                self.assertEqual(results[0]['name'], 'SupB')
                self.assertTrue(results[0].get('is_winner'))
                self.assertEqual(results[0]['win_reason'], 'Fastest delivery within constraints')

    def test_quality_priority_winner(self):
        data = {
            'constraints': {'priority': 'quality', 'max_days': 20},
            'suppliers': [
                {'name': 'SupA', 'price': 100, 'days': 10, 'quality': 3},
                {'name': 'SupB', 'price': 200, 'days': 10, 'quality': 5}
            ]
        }

        with patch('app.request') as mock_req:
            mock_req.json = data
            with patch('app.session', {'user_id': 'admin'}):
                response = app.evaluate_quotations()
                results = response['results']

                # Verify Winner (Best Quality)
                # SupB Quality 5 > SupA Quality 3
                self.assertEqual(results[0]['name'], 'SupB')
                self.assertTrue(results[0].get('is_winner'))
                self.assertEqual(results[0]['win_reason'], 'Best quality rating')

    def test_constraints_filtering(self):
        data = {
            'constraints': {'priority': 'price', 'max_days': 5},
            'suppliers': [
                {'name': 'SupA', 'price': 100, 'days': 10, 'quality': 5}, # Should be excluded
                {'name': 'SupB', 'price': 200, 'days': 4, 'quality': 5}    # Should be included
            ]
        }

        with patch('app.request') as mock_req:
            mock_req.json = data
            with patch('app.session', {'user_id': 'admin'}):
                response = app.evaluate_quotations()
                results = response['results']

                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]['name'], 'SupB')

    def test_no_suppliers(self):
        data = {
            'constraints': {'priority': 'price'},
            'suppliers': []
        }

        with patch('app.request') as mock_req:
            mock_req.json = data
            with patch('app.session', {'user_id': 'admin'}):
                response = app.evaluate_quotations()
                self.assertEqual(len(response['results']), 0)
                # Error: The existing code returns a message but it might not be a key in dict
                # It returns {'results': [], 'message': ...}
                self.assertIn('message', response)

if __name__ == '__main__':
    unittest.main()
