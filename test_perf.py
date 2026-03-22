import sys
import time

class DummyCursor:
    def __init__(self):
        self.queries = 0

    def execute(self, query, params=None):
        self.queries += 1

    def fetchone(self):
        return (1, 0, 0)

class InvoiceBatchContext:
    def __init__(self, inv_items):
        self.inv_items = inv_items
        self.cursor = DummyCursor()
        self.jv_no = 'JV-123'
        self.current_user = 1
        self.customer_name = 'Test'
        self.outstanding_id = 1
        self.location = 'Loc'
        self.inv_date = '2023-01-01'
        self.invoice_no = 'INV-123'

# Original code snippet to optimize
def original_code(ctx):
    # Inventory Items
    for item in ctx.inv_items:
        # Fetch warranty period for item
        w_end_date = None
        ctx.cursor.execute("""
            SELECT yeas_, month, date_ FROM inventory_vorenty_period
            WHERE name = %s LIMIT 1
        """, (item['name'],))
        w_res = ctx.cursor.fetchone()
        if w_res:
            try:
                years, months, days = w_res
                pass
            except Exception as e:
                pass

def optimized_code(ctx):
    # Prepare batch data
    names = [item['name'] for item in ctx.inv_items]
    if not names:
        return

    format_strings = ','.join(['%s'] * len(names))
    ctx.cursor.execute(f"""
        SELECT name, yeas_, month, date_ FROM inventory_vorenty_period
        WHERE name IN ({format_strings})
    """, tuple(names))

    # Normally fetchall(), but dummy cursor just does queries

def run_benchmark():
    n = 1000
    items = [{'name': f'Item {i}', 'qty': 1, 'price': 10, 'unit': 'Pcs', 'code': f'C{i}', 'cost': 5} for i in range(n)]

    ctx1 = InvoiceBatchContext(items)
    t0 = time.time()
    original_code(ctx1)
    t1 = time.time()

    ctx2 = InvoiceBatchContext(items)
    t2 = time.time()
    optimized_code(ctx2)
    t3 = time.time()

    print(f"Original: {ctx1.cursor.queries} queries, {t1-t0:.6f} s")
    print(f"Optimized: {ctx2.cursor.queries} queries, {t3-t2:.6f} s")

if __name__ == '__main__':
    run_benchmark()
