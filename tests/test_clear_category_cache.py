import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

# Need to set up mocks before importing app
import tests.mock_env

import unittest
import app

class TestClearCategoryCache(unittest.TestCase):
    def test_clear_category_cache(self):
        # Set up initial state with mock data
        app._category_cache = {
            'bs_cats': [{'id': 1, 'name': 'Assets'}],
            'pl_cats': [{'id': 1, 'name': 'Revenue'}],
            'cf_cats': [{'id': 1, 'name': 'Operating Activities'}]
        }

        # Verify cache is populated
        self.assertTrue(len(app._category_cache) > 0)

        # Call the function
        app.clear_category_cache()

        # Verify cache is cleared
        self.assertEqual(len(app._category_cache), 0)

if __name__ == '__main__':
    unittest.main()
