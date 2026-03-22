import time

class SlowMockDB:
    def __init__(self):
        self.queries = []
        self.latency = 0.001 # 1ms latency per query

    def execute_query(self, query, params=None):
        time.sleep(self.latency)
        self.queries.append((query, params))
        if "query_sched07_amd" in query or "JOIN new_account_table acc ON ed.account_name = acc.account_name" in query and "%%Amendment%%" in query and "LKR" in query:
            # mock sched07_amd_rows
            return [
                {
                    'entry_jv': i,
                    'invoice_no': f'INV-{i}',
                    'date': '2023-01-01',
                    'description': f'Desc {i}',
                    'fc_amount': 100,
                    'currency_code': 'USD',
                    'exchange_rate': 300,
                    'lkr_value': 30000
                }
                for i in range(1, 1001) # 1000 rows
            ]
        elif "SELECT account_name FROM entry_details WHERE entry_jv =" in query:
            # dr_res
            return [{'account_name': f'Bank-{params[0]}'}]
        elif "SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number =" in query:
            # chk_bank
            return [{'bank_bookcol_account_number': params[0]}]
        elif "SELECT ed.entry_jv, ed.account_name" in query and "JOIN bank_book b ON ed.account_name = b.bank_bookcol_account_number" in query:
            return [{'entry_jv': int(jv), 'account_name': f'Bank-{jv}'} for jv in params]
        return []

def main():
    from vat_helper import VATReportGenerator
    db = SlowMockDB()
    generator = VATReportGenerator(db, '2023-01-01', '2023-01-31')

    start_time = time.time()
    res = generator._generate_amendment_07()
    end_time = time.time()

    print(f"Rows generated: {len(res['schedule_07_amendment'])}")
    print(f"Queries executed: {len(db.queries)}")
    print(f"Execution time: {end_time - start_time:.4f} seconds")

if __name__ == '__main__':
    main()
