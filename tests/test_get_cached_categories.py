import unittest
from unittest.mock import MagicMock
import app

class TestGetCachedCategories(unittest.TestCase):
    def setUp(self):
        # Clear the cache before each test to ensure a clean state
        app._category_cache.clear()

        # Create a mock database object
        self.mock_db = MagicMock()

        # Define the expected return values from the database
        self.mock_bs_data = [{'name_of_category': 'BS Cat 1', 'holding_position': 1}]
        self.mock_pl_data = [{'name_of_category': 'PL Cat 1', 'holding_position': 2}]
        self.mock_cf_data = [{'catogory_name': 'CF Cat 1'}]

        # Configure the mock to return specific values based on the query
        def side_effect(query):
            if "balance_sheet_category" in query:
                return self.mock_bs_data
            elif "p&l_category" in query:
                return self.mock_pl_data
            elif "cf_catogory" in query:
                return self.mock_cf_data
            return []

        self.mock_db.execute_query.side_effect = side_effect

    def test_cache_miss(self):
        """Test that the cache is populated and data is fetched from the DB on a cache miss."""
        bs, pl, cf = app.get_cached_categories(self.mock_db)

        # Verify the database was queried 3 times
        self.assertEqual(self.mock_db.execute_query.call_count, 3)

        # Verify the returned data matches the mocked DB data
        self.assertEqual(bs, self.mock_bs_data)
        self.assertEqual(pl, self.mock_pl_data)
        self.assertEqual(cf, self.mock_cf_data)

        # Verify the cache was updated
        self.assertIn('bs_cats', app._category_cache)
        self.assertIn('pl_cats', app._category_cache)
        self.assertIn('cf_cats', app._category_cache)

    def test_cache_hit(self):
        """Test that data is fetched from the cache and DB is not queried on a cache hit."""
        # First call to populate the cache
        app.get_cached_categories(self.mock_db)

        # Reset the mock to track calls for the second invocation
        self.mock_db.execute_query.reset_mock()

        # Second call should hit the cache
        bs, pl, cf = app.get_cached_categories(self.mock_db)

        # Verify the database was NOT queried
        self.mock_db.execute_query.assert_not_called()

        # Verify the returned data still matches the expected data
        self.assertEqual(bs, self.mock_bs_data)
        self.assertEqual(pl, self.mock_pl_data)
        self.assertEqual(cf, self.mock_cf_data)

if __name__ == '__main__':
    unittest.main()
