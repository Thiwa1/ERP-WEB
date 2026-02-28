import sys
from unittest.mock import MagicMock

# Create Mocks
mock_flask = MagicMock()
mock_mysql = MagicMock()

# Apply to sys.modules
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Define Mock Flask Class
class MockFlask:
    def __init__(self, name):
        self.config = {}
        self.secret_key = 'test_key'

    def context_processor(self, f):
        return f

    def template_filter(self, name):
        def decorator(f):
            return f
        return decorator

    def route(self, rule, **options):
        def decorator(f):
            return f
        return decorator

    def before_request(self, f):
        return f

# Configure Mock Attributes
mock_flask.Flask = MockFlask
mock_flask.render_template = MagicMock(return_value="rendered_template")
mock_flask.request = MagicMock()
mock_flask.redirect = MagicMock(return_value="redirected")
mock_flask.url_for = MagicMock(return_value="url")
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.stream_with_context = MagicMock()
mock_flask.Response = MagicMock()
