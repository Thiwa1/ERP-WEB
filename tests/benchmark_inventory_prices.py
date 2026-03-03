import time
import sys
import os
import unittest

os.environ['PYTHONPATH'] = '.'

import tests.mock_env
import app
from unittest.mock import patch, MagicMock

class TestBenchmarkInventoryPrices(unittest.TestCase):
    def test_run_benchmark(self):
        num_items = 1000
        item_ids = [str(i) for i in range(1, num_items + 1)]
        market_prices = [str(100.0)] * num_items
        spm_prices = [str(20.0)] * num_items
        loyalty_prices = [str(95.0)] * num_items

        def mock_getlist(key):
            if key == 'item_ids[]': return item_ids
            if key == 'market_prices[]': return market_prices
            if key == 'spm_prices[]': return spm_prices
            if key == 'loyalty_prices[]': return loyalty_prices
            return []

        app.request = MagicMock()
        app.request.form.getlist.side_effect = mock_getlist

        app.queries_run = []

        # We need to simulate database latency to show real world impact
        def mock_execute_query(query, params=None, commit=False):
            # simulate 1ms latency per query typical of a local db connection
            time.sleep(0.001)
            app.queries_run.append((query, params))
            if "SELECT inventory_price_link FROM inventory_price_recod" in query:
                # Return even IDs
                results = []
                for p in params:
                    try:
                        val = int(p)
                        if val % 2 == 0:
                            results.append({"inventory_price_link": val})
                    except:
                        pass
                return results
            return None

        with patch.object(app.db, 'execute_query', side_effect=mock_execute_query):
            print(f"Running optimized benchmark with {num_items} items (simulating 1ms DB latency per query)...")

            # We'll run fewer iterations because of the sleep
            start_time = time.time()
            for _ in range(2):
                try:
                    if hasattr(app.update_inventory_prices, '__wrapped__'):
                        app.update_inventory_prices.__wrapped__()
                    else:
                        app.update_inventory_prices()
                except Exception as e:
                    pass
            end_time = time.time()

            print(f"Time taken for 2 iterations: {end_time - start_time:.4f} seconds")

            selects = len([q for q, _ in app.queries_run if "SELECT inventory_price_link FROM inventory_price_recod" in q])
            updates = len([q for q, _ in app.queries_run if "UPDATE inventory_price_recod" in q])
            inserts = len([q for q, _ in app.queries_run if "INSERT INTO inventory_price_recod" in q])

            print(f"Total SELECTs (2 iterations): {selects} ({selects // 2} per iteration)")
            print(f"Total UPDATEs (2 iterations): {updates} ({updates // 2} per iteration)")
            print(f"Total INSERTs (2 iterations): {inserts} ({inserts // 2} per iteration)")

            # Since the old implementation would have 1000 SELECTs, 500 UPDATEs, and 500 INSERTs per iteration,
            # we expect exactly 1 SELECT per iteration now
            self.assertEqual(selects // 2, 1)

if __name__ == '__main__':
    unittest.main()
