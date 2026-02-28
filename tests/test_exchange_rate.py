import unittest
import sys
import json
import time
from unittest.mock import MagicMock, patch

# --- Mocks Setup ---

# Create Flask Mock
class MockFlask:
    def __init__(self, name):
        self.config = {}
        self.name = name
        self.secret_key = 'test'

    def context_processor(self, f): return f
    def template_filter(self, name=None):
        def dec(f): return f
        return dec
    def route(self, rule, **options):
        def dec(f): return f
        return dec
    def run(self, **kwargs): pass
    def before_request(self, f): return f

# Create mock module
mock_flask_module = MagicMock()
mock_flask_module.Flask = MockFlask
mock_flask_module.render_template = MagicMock()
mock_flask_module.request = MagicMock()
mock_flask_module.redirect = MagicMock()
mock_flask_module.url_for = MagicMock()
mock_flask_module.flash = MagicMock()
mock_flask_module.session = {}
mock_flask_module.make_response = MagicMock()
mock_flask_module.Response = MagicMock()
mock_flask_module.stream_with_context = MagicMock()

sys.modules['flask'] = mock_flask_module
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Import app
import app

# --- Test Class ---

class TestExchangeRate(unittest.TestCase):
    def setUp(self):
        # Reset cache
        app.exchange_rate_cache = {}
        # Reset Mock Request
        app.request.args = {}
        # Bypass login
        app.session['user_id'] = 123

    @patch('urllib.request.urlopen')
    def test_live_api_success(self, mock_urlopen):
        # Setup Mock Response
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "rates": {"LKR": 325.50}
        }).encode('utf-8')
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        mock_urlopen.return_value = mock_resp

        # Set Args
        app.request.args = {'from': 'USD', 'to': 'LKR'}

        # Execute
        res = app.get_exchange_rate()

        # Assert
        self.assertEqual(res['rate'], 325.50)
        mock_urlopen.assert_called_once()
        self.assertIn('api.exchangerate-api.com', mock_urlopen.call_args[0][0])

    @patch('urllib.request.urlopen')
    def test_cache_hit(self, mock_urlopen):
        # First call success
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"rates": {"LKR": 320.0}}).encode('utf-8')
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        mock_urlopen.return_value = mock_resp

        app.request.args = {'from': 'USD', 'to': 'LKR'}
        app.get_exchange_rate()

        # Second call
        app.get_exchange_rate()

        # Should only call API once
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('urllib.request.urlopen')
    def test_api_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection Error")

        app.request.args = {'from': 'USD', 'to': 'LKR'}
        res = app.get_exchange_rate()

        # Fallback to Mock (~300)
        self.assertTrue(295 <= res['rate'] <= 305)

    def test_missing_params(self):
        app.request.args = {}
        res, status = app.get_exchange_rate()
        self.assertEqual(status, 400)

if __name__ == '__main__':
    unittest.main()
