import time
from vat_helper import VATReportGenerator

class MockDB:
    def __init__(self):
        self.query_count = 0

    def execute_query(self, query, params=None):
        self.query_count += 1
        if "acc.account_income = 1" in query and "Amendment" not in query:
            # Main schedule_07 query
            return [{'entry_jv': i, 'invoice_no': f'INV-{i}', 'date': '2023-01-01', 'description': 'desc', 'fc_amount': 100, 'currency_code': 'USD', 'exchange_rate': 300, 'lkr_value': 30000} for i in range(1, 1001)]
        elif "SELECT account_name FROM entry_details WHERE entry_jv = %s" in query:
            return [{'account_name': f'ACC-{params[0]}'}, {'account_name': f'ACC2-{params[0]}'}]
        elif "SELECT entry_jv, account_name FROM entry_details WHERE entry_jv IN (" in query:
            # Simulated optimized dr query
            res = []
            for p in params:
                res.append({'entry_jv': p, 'account_name': f'ACC-{p}'})
                res.append({'entry_jv': p, 'account_name': f'ACC2-{p}'})
            return res
        elif "SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number = %s" in query:
            if params[0].startswith('ACC2'):
                return [{'bank_bookcol_account_number': params[0]}]
            return []
        elif "SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number IN (" in query:
            # Simulated optimized bank query
            res = []
            for p in params:
                if p.startswith('ACC2'):
                    res.append({'bank_bookcol_account_number': p})
            return res
        return []

db = MockDB()
generator = VATReportGenerator(db, '2023-01-01', '2023-12-31')

start_time = time.time()
generator.generate_schedule_07()
end_time = time.time()

print(f"Optimized Time: {end_time - start_time:.4f} seconds")
print(f"Optimized Query Count: {db.query_count}")
