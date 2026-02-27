
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
