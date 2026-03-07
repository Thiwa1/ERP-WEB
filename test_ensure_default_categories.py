import sys
from unittest.mock import MagicMock
import unittest
from datetime import date

# Mock external dependencies
sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['jinja2'] = MagicMock()

import app

class TestEnsureDefaultCategories(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()

        self.mock_db.get_connection.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        app.db = self.mock_db
        app.clear_category_cache = MagicMock()
        app.logging = MagicMock()

    def test_empty_database(self):
        self.mock_cursor.fetchone.return_value = None
        self.mock_cursor.fetchall.return_value = []

        app.ensure_default_categories()

        total_calls = self.mock_cursor.execute.call_count + self.mock_cursor.executemany.call_count
        self.assertTrue(total_calls > 0)
        self.mock_conn.commit.assert_called_once()
        app.clear_category_cache.assert_called_once()

    def test_populated_database(self):
        self.mock_cursor.fetchone.return_value = (1,)

        def fetchall_side_effect():
            # Return a mix of ints and strings to cover all cases
            return [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,),
                    ('Operating Activities',), ('Investing Activities',), ('Financing Activities',),
                    ('Adjustments',), ('Changes In Working Capital',)]

        self.mock_cursor.fetchall.side_effect = fetchall_side_effect

        app.ensure_default_categories()

        # Ensure no INSERTs were executed
        for call in self.mock_cursor.execute.call_args_list:
            args, _ = call
            self.assertFalse(args[0].startswith("INSERT"))

        for call in self.mock_cursor.executemany.call_args_list:
            args, _ = call
            self.assertFalse(args[0].startswith("INSERT"))

if __name__ == '__main__':
    unittest.main()
