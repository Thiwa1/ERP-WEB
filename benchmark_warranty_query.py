import time
import sqlite3
import random

class InvoiceBatchContext:
    def __init__(self, inv_items, cursor):
        self.inv_items = inv_items
        self.cursor = cursor
        self.jv_no = 'JV-123'
        self.current_user = 1
        self.customer_name = 'Test'
        self.outstanding_id = 1
        self.location = 'Loc'
        self.inv_date = '2023-01-01'
        self.invoice_no = 'INV-123'

def original_logic(ctx):
    for item in ctx.inv_items:
        w_end_date = None
        ctx.cursor.execute("""
            SELECT yeas_, month, date_ FROM inventory_vorenty_period
            WHERE name = ? LIMIT 1
        """, (item['name'],))
        w_res = ctx.cursor.fetchone()
        if w_res:
            try:
                years, months, days = w_res
                pass
            except Exception as e:
                pass

def optimized_logic(ctx):
    if not ctx.inv_items:
        return

    names = list(set([item['name'] for item in ctx.inv_items]))
    placeholders = ','.join(['?'] * len(names))

    ctx.cursor.execute(f"""
        SELECT name, yeas_, month, date_ FROM inventory_vorenty_period
        WHERE name IN ({placeholders})
    """, tuple(names))

    results = ctx.cursor.fetchall()
    warranty_map = {row[0]: (row[1], row[2], row[3]) for row in results}

    for item in ctx.inv_items:
        w_end_date = None
        w_res = warranty_map.get(item['name'])
        if w_res:
            try:
                years, months, days = w_res
                pass
            except Exception as e:
                pass

def run_benchmark():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE inventory_vorenty_period (
            name TEXT,
            yeas_ INTEGER,
            month INTEGER,
            date_ INTEGER
        )
    """)

    item_names = [f"Item_{i}" for i in range(1000)]
    for name in item_names:
        cursor.execute("INSERT INTO inventory_vorenty_period VALUES (?, 1, 0, 0)", (name,))
    conn.commit()

    # 5000 items in the invoice, drawing from the 1000 products
    inv_items = [{'name': random.choice(item_names)} for _ in range(5000)]

    ctx = InvoiceBatchContext(inv_items, cursor)

    print("Running original logic (N+1 queries)...")
    start_time = time.time()
    original_logic(ctx)
    original_duration = time.time() - start_time
    print(f"Original logic took: {original_duration:.6f} seconds")

    print("Running optimized logic (1 query)...")
    start_time = time.time()
    optimized_logic(ctx)
    optimized_duration = time.time() - start_time
    print(f"Optimized logic took: {optimized_duration:.6f} seconds")

    improvement = (original_duration - optimized_duration) / original_duration * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    run_benchmark()
