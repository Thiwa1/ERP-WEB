import sys
import unittest
import os
import json

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We conditionally import mock_env if flask is not present to avoid ModuleNotFoundError in sandbox
try:
    import flask
    import mysql.connector
except ImportError:
    import tests.mock_env

# Import app module
import app

class TestPredictAccountType(unittest.TestCase):
    def setUp(self):
        # By creating a real Flask test_client, we test the actual Flask route
        # and response serialization without custom mocks.
        self.app = app.app
        self.app.testing = True
        self.client = self.app.test_client()

    def test_no_name_provided(self):
        """Test the endpoint returns error when no name is provided"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'error': 'No name provided'})

        response = self.client.get('/api/predict_account_type?name=')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'error': 'No name provided'})

    def test_exact_match_asset(self):
        """Test exact match on an asset account"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=Petty%20cash%20balance')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Petty cash balance')
        self.assertEqual(result['original_type'], 'Assets Account')
        self.assertEqual(result['mapped_type'], 'asset')
        self.assertEqual(result['confidence'], 1.0)

    def test_exact_match_expense(self):
        """Test exact match on an expense/cost account"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=Basic%20salary')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Basic salary')
        self.assertEqual(result['original_type'], 'Cost Account')
        self.assertEqual(result['mapped_type'], 'expense')
        self.assertEqual(result['confidence'], 1.0)

    def test_fuzzy_match(self):
        """Test fuzzy matching handles typos or shortened names correctly"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=Petty%20cash')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Petty cash balance')
        self.assertEqual(result['original_type'], 'Assets Account')
        self.assertEqual(result['mapped_type'], 'asset')
        self.assertTrue(0 < result['confidence'] < 1.0)

    def test_no_match(self):
        """Test when no matches are found"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=Xylophone%20Zebra')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result, {'confidence': 0})

    def test_different_mapped_types(self):
        """Test that different knowledge base types are mapped correctly to the UI types"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=Land')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'asset')

        response = self.client.get('/api/predict_account_type?name=Share%20Capital')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'equity')

        response = self.client.get('/api/predict_account_type?name=Sales%20Revenue')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'income')

        response = self.client.get('/api/predict_account_type?name=Accounts%20payable')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'liability')

        response = self.client.get('/api/predict_account_type?name=Sofwarre')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mapped_type'], 'asset')

    def test_case_insensitivity(self):
        """Test that fuzzy matching is effectively case insensitive in calculation"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        response = self.client.get('/api/predict_account_type?name=basic%20salary')
        self.assertEqual(response.status_code, 200)
        result = response.json
        self.assertEqual(result['match'], 'Basic salary')
        self.assertEqual(result['original_type'], 'Cost Account')
        self.assertEqual(result['mapped_type'], 'expense')
        self.assertTrue(result['confidence'] > 0.9)

if __name__ == '__main__':
    unittest.main()
