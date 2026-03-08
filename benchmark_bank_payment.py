import time
import random

class CursorMock:
    def __init__(self, data_map):
        self.data_map = data_map
        self.current_res = None
        self.execute_count = 0

    def execute(self, query, params=None):
        self.execute_count += 1
        time.sleep(0.001) # Simulate real DB network latency
        if "IN" in query:
            self.current_res = list(self.data_map.values())
        else:
            if params and len(params) == 1:
                self.current_res = [self.data_map.get(params[0])]
            else:
                self.current_res = []

    def executemany(self, query, params_list):
        self.execute_count += 1
        time.sleep(0.005) # Simulate real DB bulk update latency

    def fetchone(self):
        if self.current_res:
            return self.current_res.pop(0)
        return None

    def fetchall(self):
        res = self.current_res
        self.current_res = None
        return res

def original_logic(payments, cursor):
    for p in payments:
        cursor.execute("SELECT suppliers_invoice_oustanding, suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE s_i_id = %s", (p['id'],))
        res = cursor.fetchone()
        if not res: continue

        current_outstanding = float(res[0])
        current_paid = float(res[1])

        if p['amount'] > current_outstanding:
            raise Exception(f"Payment amount {p['amount']} exceeds outstanding {current_outstanding} for invoice ID {p['id']}")

        new_total_paid = current_paid + p['amount']
        cursor.execute("UPDATE suppliers_invoice_data SET suppliers_invoice_total_payment = %s WHERE s_i_id = %s", (new_total_paid, p['id']))


def optimized_logic(payments, cursor):
    if not payments: return

    inv_ids = tuple(p['id'] for p in payments)
    format_strings = ','.join(['%s'] * len(inv_ids))
    cursor.execute(f"SELECT s_i_id, suppliers_invoice_oustanding, suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE s_i_id IN ({format_strings})", inv_ids)

    res = cursor.fetchall()
    invoice_data = {r[0]: (r[1], r[2]) for r in res}

    update_data = []

    for p in payments:
        inv_d = invoice_data.get(p['id'])
        if not inv_d: continue

        current_outstanding = float(inv_d[0])
        current_paid = float(inv_d[1])

        if p['amount'] > current_outstanding:
            raise Exception(f"Payment amount {p['amount']} exceeds outstanding {current_outstanding} for invoice ID {p['id']}")

        new_total_paid = current_paid + p['amount']
        update_data.append((new_total_paid, p['id']))

    if update_data:
        cursor.executemany("UPDATE suppliers_invoice_data SET suppliers_invoice_total_payment = %s WHERE s_i_id = %s", update_data)

if __name__ == '__main__':
    num_invoices = 50 # Realistic batch size

    payments = [{'id': i, 'amount': random.uniform(1, 100)} for i in range(num_invoices)]
    db_map_orig = {i: (1000.0, 0.0) for i in range(num_invoices)}
    db_map_opt = {i: (i, 1000.0, 0.0) for i in range(num_invoices)}

    cursor_orig = CursorMock(db_map_orig)
    start = time.time()
    original_logic(payments, cursor_orig)
    time_orig = time.time() - start

    cursor_opt = CursorMock(db_map_opt)
    start = time.time()
    optimized_logic(payments, cursor_opt)
    time_opt = time.time() - start

    print(f"Original logic time: {time_orig:.4f}s")
    print(f"Optimized logic time: {time_opt:.4f}s")
    print(f"Original DB calls: {cursor_orig.execute_count}")
    print(f"Optimized DB calls: {cursor_opt.execute_count}")
