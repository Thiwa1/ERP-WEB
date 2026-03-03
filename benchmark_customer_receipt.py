import time

class MockCursor:
    def __init__(self):
        self.queries_executed = 0

    def execute(self, query, params=None):
        self.queries_executed += 1
        # Simulate network latency of 1ms per query
        time.sleep(0.001)

    def fetchone(self):
        return (100.0,)

    def fetchall(self):
        return [(str(i), 100.0) for i in range(1, 101)]

    def executemany(self, query, params):
        self.queries_executed += 1
        # Simulate network latency of 1ms per query
        time.sleep(0.001)

def original_logic(payments, cursor):
    for p in payments:
        cursor.execute("SELECT invoice_oustanding_Patment FROM Invoice_Oustanding WHERE Id = %s", (p['id'],))
        res = cursor.fetchone()
        if res:
            current_paid = float(res[0])
            new_paid = current_paid + p['amount']
            cursor.execute("UPDATE Invoice_Oustanding SET invoice_oustanding_Patment = %s WHERE Id = %s", (new_paid, p['id']))

def optimized_logic(payments, cursor):
    if not payments:
        return

    ids = [p['id'] for p in payments]
    format_strings = ','.join(['%s'] * len(ids))
    cursor.execute(f"SELECT Id, invoice_oustanding_Patment FROM Invoice_Oustanding WHERE Id IN ({format_strings})", tuple(ids))

    res = cursor.fetchall()
    current_balances = {str(row[0]): float(row[1]) for row in res}

    update_data = []
    for p in payments:
        current_paid = current_balances.get(str(p['id']))
        if current_paid is not None:
            new_paid = current_paid + p['amount']
            update_data.append((new_paid, p['id']))

    if update_data:
        cursor.executemany("UPDATE Invoice_Oustanding SET invoice_oustanding_Patment = %s WHERE Id = %s", update_data)

def run_benchmark():
    n_payments = 100
    payments = [{'id': str(i), 'amount': 10.0} for i in range(1, n_payments + 1)]

    print(f"Benchmarking with {n_payments} payments (simulated 1ms latency per query)...")

    cursor1 = MockCursor()
    start_time = time.time()
    original_logic(payments, cursor1)
    end_time = time.time()
    original_duration = end_time - start_time
    print(f"Original logic took: {original_duration:.4f} seconds ({cursor1.queries_executed} queries)")

    cursor2 = MockCursor()
    start_time = time.time()
    optimized_logic(payments, cursor2)
    end_time = time.time()
    optimized_duration = end_time - start_time
    print(f"Optimized logic took: {optimized_duration:.4f} seconds ({cursor2.queries_executed} queries)")

    improvement = (original_duration - optimized_duration) / original_duration * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    run_benchmark()
