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
app.master_db.execute_query.return_value = [] # Force fallback to legacy login
app.db = MagicMock()

mock_user = {
    'id': 1,
    'User_Code': 'USR001',
    'Password': 'secret',
    'User_Name': 'admin'
}
app.db.execute_query.return_value = [mock_user]
app.db.last_error = None

# Mock flask module completely inside app.py scope
app.request.method = 'POST'
app.request.form = {'username': 'admin', 'password': 'secret'}
app.session = {}

response = app.login()
print("app.session:", app.session)

print("DB CALLS:")
for call in app.db.execute_query.call_args_list:
    print(call)
