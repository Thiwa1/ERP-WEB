import time

class MockCursor:
    def __init__(self):
        self.queries_executed = 0

    def execute(self, query, params=None):
        self.queries_executed += 1
        # Simulate network latency of 1ms per query
        time.sleep(0.001)

    def executemany(self, query, params):
        self.queries_executed += 1
        # Simulate network latency of 1ms per query
        time.sleep(0.001)

def original_logic(updates, cursor):
    query = "UPDATE new_account_table SET account_name_of_catogory_PL = %s, account_hold_possion_PL = %s WHERE id = %s"
    for u in updates:
        cursor.execute(query, u)

def optimized_logic(updates, cursor):
    query = "UPDATE new_account_table SET account_name_of_catogory_PL = %s, account_hold_possion_PL = %s WHERE id = %s"
    cursor.executemany(query, updates)

def run_benchmark():
    n_updates = 100
    updates = [('Category ' + str(i), str(i), str(i)) for i in range(1, n_updates + 1)]

    print(f"Benchmarking with {n_updates} updates (simulated 1ms latency per query)...")

    cursor1 = MockCursor()
    start_time = time.time()
    original_logic(updates, cursor1)
    end_time = time.time()
    original_duration = end_time - start_time
    print(f"Original logic took: {original_duration:.4f} seconds ({cursor1.queries_executed} queries)")

    cursor2 = MockCursor()
    start_time = time.time()
    optimized_logic(updates, cursor2)
    end_time = time.time()
    optimized_duration = end_time - start_time
    print(f"Optimized logic took: {optimized_duration:.4f} seconds ({cursor2.queries_executed} queries)")

    improvement = (original_duration - optimized_duration) / original_duration * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    run_benchmark()
