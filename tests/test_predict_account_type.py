import sys
import unittest
import os
import json
from unittest.mock import MagicMock, patch

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We conditionally import mock_env if flask is not present to avoid ModuleNotFoundError in sandbox
try:
    import flask
    import mysql.connector
    IS_SANDBOX = False
except ImportError:
    import tests.mock_env
    IS_SANDBOX = True

# Import app module
import app

class TestPredictAccountType(unittest.TestCase):
    def setUp(self):
        # By creating a real Flask test_client, we test the actual Flask route
        # and response serialization without custom mocks.
        app.app_initialized = True

        if IS_SANDBOX:
            # Recreate test client using the pattern from test_login.py and test_add_new_account.py
            # Since mock_env.py sets up a mock_flask, we need to create a test client.
            # `tests.mock_env.mock_flask.Flask` is mocked to return `app_mock`.
            # We can mock `app.app.test_client()` to return a MockTestClient.
            pass
        else:
            self.app = app.app
            self.app.testing = True
            self.client = self.app.test_client()

    def call_predict(self, name_param):
        if IS_SANDBOX:
            # We must mock flask.request.args.get and session
            with patch.object(app, 'request') as mock_request, patch.object(app, 'session', {'user_id': 1}):
                mock_request.args.get.return_value = name_param

                # Call the function directly
                result = app.predict_account_type()

                # Wrap the returned dict in a mock response object
                return MagicMock(status_code=200, json=result)
        else:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
            if name_param is None:
                return self.client.get('/api/predict_account_type')
            return self.client.get(f'/api/predict_account_type?name={name_param}')

    def test_no_name_provided(self):
        """Test the endpoint returns error when no name is provided"""
        response = self.call_predict(None)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'error': 'No name provided'})

        response = self.call_predict('')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'error': 'No name provided'})

    def test_exact_match_asset(self):
        """Test exact match on an asset account"""
        response = self.call_predict('Petty cash balance')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Petty cash balance')
        self.assertEqual(result['original_type'], 'Assets Account')
        self.assertEqual(result['mapped_type'], 'asset')
        self.assertEqual(result['confidence'], 1.0)

    def test_exact_match_expense(self):
        """Test exact match on an expense/cost account"""
        response = self.call_predict('Basic salary')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Basic salary')
        self.assertEqual(result['original_type'], 'Cost Account')
        self.assertEqual(result['mapped_type'], 'expense')
        self.assertEqual(result['confidence'], 1.0)

    def test_fuzzy_match(self):
        """Test fuzzy matching handles typos or shortened names correctly"""
        response = self.call_predict('Petty cash')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Petty cash balance')
        self.assertEqual(result['original_type'], 'Assets Account')
        self.assertEqual(result['mapped_type'], 'asset')
        self.assertTrue(0 < result['confidence'] < 1.0)

    def test_no_match(self):
        """Test when no matches are found"""
        response = self.call_predict('Xylophone Zebra')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result, {'confidence': 0})

    def test_different_mapped_types(self):
        """Test that different knowledge base types are mapped correctly to the UI types"""
        response = self.call_predict('Land')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'asset')

        response = self.call_predict('Share Capital')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'equity')

        response = self.call_predict('Sales Revenue')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'income')

        response = self.call_predict('Accounts payable')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'liability')

        response = self.call_predict('Sofwarre')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'asset')

    def test_case_insensitivity(self):
        """Test that fuzzy matching is effectively case insensitive in calculation"""
        response = self.call_predict('basic salary')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Basic salary')
        self.assertEqual(result['original_type'], 'Cost Account')
        self.assertEqual(result['mapped_type'], 'expense')
        self.assertTrue(result['confidence'] > 0.9)

if __name__ == '__main__':
    unittest.main()
