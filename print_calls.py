import sys
import unittest
from unittest.mock import MagicMock, patch
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import tests.mock_env
except ImportError:
    pass

sys.modules['database'] = MagicMock()
import app

app.master_db = MagicMock()
app.master_db.execute_query.return_value = []

mock_user = {
    'id': 1,
    'User_Code': 'USR001',
    'Password': 'secret',
    'User_Name': 'admin'
}
app.db.execute_query.return_value = [mock_user]
app.db.last_error = None

# Mock request in mock_env manually
sys.modules['flask'].request.method = 'POST'
sys.modules['flask'].request.form = {'username': 'admin', 'password': 'secret'}

print(app.login())

print("MOCK DB CALLS:")
for c in app.db.execute_query.call_args_list:
    print(c)
