import unittest
from benchmark_bs_category_correction import original_logic, optimized_logic, generate_updates, MockCursor

class TestBenchmarkBSCategoryCorrection(unittest.TestCase):
    def test_original_vs_optimized(self):
        # Generate some mock data
        updates = generate_updates(50)

        # Run original
        cursor1 = MockCursor()
        original_logic(updates, cursor1)

        # Run optimized
        cursor2 = MockCursor()
        optimized_logic(updates, cursor2)

        # Check results for original
        self.assertEqual(len(cursor1.executed_queries), 50)
        self.assertEqual(len(cursor1.executemany_queries), 0)

        # Check results for optimized
        self.assertEqual(len(cursor2.executed_queries), 0)
        self.assertEqual(len(cursor2.executemany_queries), 1)
        self.assertEqual(len(cursor2.executemany_queries[0][1]), 50)

        # Check that the queries and parameters are equivalent
        query = "UPDATE new_account_table SET account_name_of_catogory_Balace_sheet = %s, account_hold_possion_Balace_Sheet = %s WHERE id = %s"

        # Check query strings
        for q, p in cursor1.executed_queries:
            self.assertEqual(q, query)

        self.assertEqual(cursor2.executemany_queries[0][0], query)

        # Check parameters
        original_params = [p for q, p in cursor1.executed_queries]
        optimized_params = cursor2.executemany_queries[0][1]

        self.assertEqual(original_params, optimized_params)

    def test_empty_updates(self):
        # Ensure it works correctly with empty data
        updates = []

        cursor1 = MockCursor()
        original_logic(updates, cursor1)
        self.assertEqual(len(cursor1.executed_queries), 0)

        cursor2 = MockCursor()
        optimized_logic(updates, cursor2)
        self.assertEqual(len(cursor2.executemany_queries), 1)
        self.assertEqual(len(cursor2.executemany_queries[0][1]), 0)

if __name__ == '__main__':
    unittest.main()
