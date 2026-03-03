import sys
import time

# Create a mock database connection
class MockCursor:
    def __init__(self):
        self.execute_calls = 0
        self.executemany_calls = 0
        self.lastrowid = 123

    def execute(self, query, params=None):
        self.execute_calls += 1
        time.sleep(0.001) # 1ms latency per query

    def executemany(self, query, params_seq):
        self.executemany_calls += 1
        time.sleep(0.005) # 5ms latency per batch

    def close(self):
        pass

# Original code snippet
def original_insert(items, po_id):
    cursor = MockCursor()
    start = time.time()

    query_detail = """
        INSERT INTO PO_Recode_Details (
            Link_OP_NO_Table, Item, Discription, QTY, Unit_price, Mesurment
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    for item in items:
        cursor.execute(query_detail, (
            po_id, item['item'], item['description'],
            item['qty'], item['price'], item['unit']
        ))

    end = time.time()
    return end - start, cursor

# Optimized code snippet
def optimized_insert(items, po_id):
    cursor = MockCursor()
    start = time.time()

    query_detail = """
        INSERT INTO PO_Recode_Details (
            Link_OP_NO_Table, Item, Discription, QTY, Unit_price, Mesurment
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    # Create the list of tuples for executemany
    batch_data = [(
        po_id, item['item'], item['description'],
        item['qty'], item['price'], item['unit']
    ) for item in items]

    if batch_data:
        cursor.executemany(query_detail, batch_data)

    end = time.time()
    return end - start, cursor

# Run benchmark
if __name__ == "__main__":
    po_id = 42

    for item_count in [10, 100, 500, 1000]:
        print(f"\nBenchmarking with {item_count} items...")

        items = [{'item': f'Item {i}', 'description': f'Desc {i}', 'qty': 10, 'price': 5.5, 'unit': 'pcs'} for i in range(item_count)]

        orig_time, orig_cursor = original_insert(items, po_id)
        print(f"Original Time: {orig_time:.4f}s | execute() called {orig_cursor.execute_calls} times")

        opt_time, opt_cursor = optimized_insert(items, po_id)
        print(f"Optimized Time: {opt_time:.4f}s | executemany() called {opt_cursor.executemany_calls} times")

        speedup = orig_time / opt_time if opt_time > 0 else float('inf')
        print(f"Speedup: {speedup:.2f}x")
