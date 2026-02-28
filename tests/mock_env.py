import sys
from unittest.mock import MagicMock

# Mock mysql.connector
mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Mock flask
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask

# Configure specific Flask mocks that are imported directly
# When Flask() is instantiated, it returns a MagicMock
# We need to ensure that instance has .config dictionary
def flask_app_side_effect(*args, **kwargs):
    app_mock = MagicMock()
    app_mock.config = {}
    # Also mock .route decorator to return the function itself (passthrough)
    def route_decorator(rule, **options):
        def decorator(f):
            return f
        return decorator
    app_mock.route = MagicMock(side_effect=route_decorator)

    # Mock template_filter decorator
    def template_filter_side_effect(name=None):
        def decorator(f):
            return f
        return decorator
    app_mock.template_filter = MagicMock(side_effect=template_filter_side_effect)

    # Mock context_processor
    def context_processor_side_effect(f):
        return f
    app_mock.context_processor = MagicMock(side_effect=context_processor_side_effect)

    # Mock before_request
    def before_request_side_effect(f):
        return f
    app_mock.before_request = MagicMock(side_effect=before_request_side_effect)

    return app_mock

mock_flask.Flask = MagicMock(side_effect=flask_app_side_effect)
mock_flask.render_template = MagicMock()
mock_flask.request = MagicMock()
# Important: redirect and url_for should be instances (callables) not classes,
# to avoid MagicMock(spec=Mock) issue if called with args.
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()

# Also mock werkzeug.security
mock_werkzeug = MagicMock()
sys.modules['werkzeug'] = mock_werkzeug
sys.modules['werkzeug.security'] = mock_werkzeug

print("Mocks initialized for flask and mysql.connector")
