import sys
import os
from unittest.mock import MagicMock

# Mock missing modules
sys.modules['flask'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['jinja2'] = MagicMock()

os.environ['SECRET_KEY'] = 'test-key'
sys.path.append('.')

import unittest
from tests import benchmark_warranty_save
unittest.main(module=benchmark_warranty_save)
