import sys
import unittest
from unittest.mock import MagicMock, patch
from io import StringIO

# 1. Mock dependencies BEFORE importing app
# Mock mysql.connector
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Mock flask
flask_mock = MagicMock()
flask_mock.Flask = MagicMock(return_value=MagicMock())
session_mock = {}
flask_mock.session = session_mock
flask_mock.request = MagicMock()
sys.modules['flask'] = flask_mock

# Mock database
db_mock = MagicMock()
sys.modules['database'] = db_mock

# Mock knowledge_base
sys.modules['knowledge_base'] = MagicMock()

# 2. Import app
import app
app.session = session_mock

class TestCheckPermission(unittest.TestCase):
    def setUp(self):
        app.db = MagicMock()
        app.session.clear()

    def test_check_permission_missing_column_fix(self):
        """
        Verification Test:
        Verifies that with the new implementation, requesting a non-existent permission
        does NOT raise an exception and returns False quietly.
        """
        app.session['user_pk'] = 1
        perm_name = "NonExistentPerm"

        # Mock DB returning a row that does NOT have the requested permission key
        # simulating "SELECT * ..." where the column doesn't exist
        app.db.execute_query.return_value = [{'ExistingPerm': 1}]

        # Capture output to ensure NO error is printed
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = app.check_permission(perm_name)

            # Should return False
            self.assertFalse(result)

            # Should NOT print "Permission check error"
            output = fake_out.getvalue()
            self.assertNotIn("Permission check error", output)

    def test_check_permission_valid_column(self):
        """
        Verifies that valid permissions still work.
        """
        app.session['user_pk'] = 1
        perm_name = "ValidPerm"

        # Mock DB returning a row WITH the permission
        app.db.execute_query.return_value = [{'ValidPerm': 1}]

        result = app.check_permission(perm_name)
        self.assertTrue(result)

    def test_check_permission_denied(self):
        """
        Verifies denied permission (value 0).
        """
        app.session['user_pk'] = 1
        perm_name = "ValidPerm"

        # Mock DB returning 0
        app.db.execute_query.return_value = [{'ValidPerm': 0}]

        result = app.check_permission(perm_name)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
