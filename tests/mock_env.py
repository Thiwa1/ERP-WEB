
import sys
from unittest.mock import MagicMock

# -------------------------------------------------------------------------
# MOCKING FLASK AND MYSQL-CONNECTOR (Since they are not installed)
# -------------------------------------------------------------------------

# Mock mysql.connector
if 'mysql' not in sys.modules:
    mock_mysql = MagicMock()
    sys.modules['mysql'] = mock_mysql
    sys.modules['mysql.connector'] = mock_mysql

# Mock flask
if 'flask' not in sys.modules:
    mock_flask = MagicMock()
    sys.modules['flask'] = mock_flask

    # Create a mock Flask app instance
    mock_app_instance = MagicMock()
    mock_flask.Flask.return_value = mock_app_instance
    mock_app_instance.route = lambda *args, **kwargs: lambda f: f
    mock_app_instance.context_processor = lambda f: f
    mock_app_instance.template_filter = lambda *args: lambda f: f
    mock_app_instance.before_request = lambda f: f

    # Mock request, session, etc.
    mock_request = MagicMock()
    mock_flask.request = mock_request
    mock_session = MagicMock()
    mock_flask.session = mock_session
    mock_redirect = MagicMock()
    mock_flask.redirect = mock_redirect
    mock_url_for = MagicMock()
    mock_flask.url_for = mock_url_for
    mock_flash = MagicMock()
    mock_flask.flash = mock_flash
    mock_render_template = MagicMock()
    mock_flask.render_template = mock_render_template
    # Mock Response
    mock_response_cls = MagicMock()
    mock_flask.Response = mock_response_cls
    mock_stream_context = MagicMock()
    mock_flask.stream_with_context = mock_stream_context
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
import sys
from unittest.mock import MagicMock

if 'jinja2' not in sys.modules:
    mock_jinja = MagicMock()
    mock_jinja.pass_context = lambda f: f
    sys.modules['jinja2'] = mock_jinja

mock_jinja = MagicMock()
mock_jinja.pass_context = lambda f: f
sys.modules['jinja2'] = mock_jinja

if 'werkzeug.security' not in sys.modules:
    mock_wz = MagicMock()
    mock_wz.generate_password_hash = lambda x: f"hashed_{x}"
    mock_wz.check_password_hash = lambda h, p: h == f"hashed_{p}"
    sys.modules['werkzeug.security'] = mock_wz
if 'num2words' not in sys.modules:
    mock_n2w = MagicMock()
    mock_n2w.num2words = lambda n, **kwargs: str(n)
    sys.modules['num2words'] = mock_n2w

if 'flask_wtf' not in sys.modules:
    mock_flask_wtf = MagicMock()
    sys.modules['flask_wtf'] = mock_flask_wtf
    mock_csrf = MagicMock()
    mock_flask_wtf.csrf = mock_csrf
    mock_csrf.CSRFProtect = MagicMock()

if 'dotenv' not in sys.modules:
    mock_dotenv = MagicMock()
    sys.modules['dotenv'] = mock_dotenv

# Set SECRET_KEY in environment to satisfy app.py initialization
import os
if 'SECRET_KEY' not in os.environ:
    os.environ['SECRET_KEY'] = 'mocked_secret_key_for_testing'

import sys
from unittest.mock import MagicMock

# Mock PyPDF2
mock_pypdf2 = MagicMock()
sys.modules['PyPDF2'] = mock_pypdf2
