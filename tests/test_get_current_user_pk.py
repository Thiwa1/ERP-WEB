import sys
import unittest
from unittest.mock import MagicMock
import os

os.environ['SECRET_KEY'] = 'test_secret'

import tests.mock_env

# 2. Import app
import app
app.session = tests.mock_env.mock_flask.session

class TestGetCurrentUserPk(unittest.TestCase):
    def setUp(self):
        app.session.clear()

    def test_get_current_user_pk_valid_int(self):
        app.session['user_pk'] = 5
        self.assertEqual(app.get_current_user_pk(), 5)

    def test_get_current_user_pk_valid_string(self):
        app.session['user_pk'] = "10"
        self.assertEqual(app.get_current_user_pk(), 10)

    def test_get_current_user_pk_missing(self):
        self.assertEqual(app.get_current_user_pk(), 0)

    def test_get_current_user_pk_invalid_string(self):
        app.session['user_pk'] = "abc"
        self.assertEqual(app.get_current_user_pk(), 0)

    def test_get_current_user_pk_type_error(self):
        app.session['user_pk'] = [1, 2, 3] # lists cannot be cast to int, raising TypeError
        self.assertEqual(app.get_current_user_pk(), 0)

if __name__ == '__main__':
    unittest.main()
