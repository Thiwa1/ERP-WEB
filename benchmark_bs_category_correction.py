import time
import random

class MockCursor:
    def __init__(self):
        self.executed_queries = []
        self.executemany_queries = []

    def execute(self, query, params=None):
        # Simulate network and I/O latency for individual query
        time.sleep(0.0001)
        self.executed_queries.append((query, params))

    def executemany(self, query, params_list):
        # Simulate batch processing latency
        time.sleep(0.0001 + len(params_list) * 0.00001)
        self.executemany_queries.append((query, params_list))

def generate_updates(n=1000):
    updates = []
    for i in range(n):
        updates.append((f"Category {i % 10}", i % 5, i))
    return updates

def original_logic(updates, cursor):
    query = "UPDATE new_account_table SET account_name_of_catogory_Balace_sheet = %s, account_hold_possion_Balace_Sheet = %s WHERE id = %s"
    for u in updates:
        cursor.execute(query, u)

def optimized_logic(updates, cursor):
    query = "UPDATE new_account_table SET account_name_of_catogory_Balace_sheet = %s, account_hold_possion_Balace_Sheet = %s WHERE id = %s"
    cursor.executemany(query, updates)

def run_benchmark():
    n = 2000 # 2000 updates to simulate a reasonably large category correction
    print(f"Generating {n} updates...")
    updates = generate_updates(n)

    cursor1 = MockCursor()
    print("Running original logic...")
    start_time = time.time()
    original_logic(updates, cursor1)
    end_time = time.time()
    original_duration = end_time - start_time
    print(f"Original logic took: {original_duration:.6f} seconds")

    cursor2 = MockCursor()
    print("Running optimized logic...")
    start_time = time.time()
    optimized_logic(updates, cursor2)
    end_time = time.time()
    optimized_duration = end_time - start_time
    print(f"Optimized logic took: {optimized_duration:.6f} seconds")

    # Verification checks
    assert len(cursor1.executed_queries) == n
    assert len(cursor2.executemany_queries) == 1
    assert len(cursor2.executemany_queries[0][1]) == n

    print("Results match.")

    improvement = (original_duration - optimized_duration) / original_duration * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    run_benchmark()
