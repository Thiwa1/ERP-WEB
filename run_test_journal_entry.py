import unittest
import sys
from unittest.mock import MagicMock

mock_flask = MagicMock()
mock_mysql = MagicMock()
mock_jinja2 = MagicMock()
mock_werkzeug = MagicMock()
mock_dotenv = MagicMock()
mock_socketio = MagicMock()
mock_pypdf2 = MagicMock()
mock_requests = MagicMock()
mock_num2words = MagicMock()

def route_mock(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_flask.Flask.return_value.route.side_effect = route_mock

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql
sys.modules['jinja2'] = mock_jinja2
sys.modules['werkzeug'] = mock_werkzeug
sys.modules['werkzeug.security'] = mock_werkzeug
sys.modules['werkzeug.utils'] = mock_werkzeug
sys.modules['dotenv'] = mock_dotenv
sys.modules['flask_socketio'] = mock_socketio
sys.modules['PyPDF2'] = mock_pypdf2
sys.modules['requests'] = mock_requests
sys.modules['num2words'] = mock_num2words

import os
os.environ['SECRET_KEY'] = 'test-secret-key-for-mock-env'

from tests.test_journal_entry_save import TestJournalEntrySave

if __name__ == '__main__':
    unittest.main()
