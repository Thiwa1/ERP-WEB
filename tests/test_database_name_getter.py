import unittest
from unittest.mock import MagicMock
import sys

# Mock mysql.connector since it's not available in the environment
mock_mysql = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = mock_mysql

from database import Database

class TestDatabaseNameGetter(unittest.TestCase):
    def setUp(self):
        self.config = {'user': 'root', 'password': '', 'host': 'localhost', 'database': 'test_db'}
        self.db = Database(self.config)

    def test_set_db_name_getter(self):
        """
        Verify that set_db_name_getter correctly assigns the callable to get_db_name.
        """
        # Define a simple getter function
        def mock_getter():
            return "dynamic_db_name"

        # Initially, get_db_name should be None (or not set)
        if hasattr(self.db, 'get_db_name'):
            self.assertIsNone(self.db.get_db_name)
        elif hasattr(self.db, 'db_name_getter'):
            self.assertIsNone(self.db.db_name_getter)

        # Call set_db_name_getter with our mock getter
        self.db.set_db_name_getter(mock_getter)

        # Verify that get_db_name or db_name_getter is now our mock getter
        if hasattr(self.db, 'get_db_name'):
            self.assertEqual(self.db.get_db_name, mock_getter)
            self.assertEqual(self.db.get_db_name(), "dynamic_db_name")
        elif hasattr(self.db, 'db_name_getter'):
            self.assertEqual(self.db.db_name_getter, mock_getter)
            self.assertEqual(self.db.db_name_getter(), "dynamic_db_name")

if __name__ == '__main__':
    unittest.main()
