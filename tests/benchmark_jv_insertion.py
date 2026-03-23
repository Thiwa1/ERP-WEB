import unittest
from unittest.mock import MagicMock
import json
from datetime import datetime

# Import the NEW logic (simulation of what is now in app.py)
# This mimics the changes I'll apply to app.py
def save_journal_entry_optimized(db_mock, form_data, session, current_user, current_user_pk):
    jv_user_code = form_data.get('jv_user_code')
    entry_date = form_data.get('entry_date')
    main_narration = form_data.get('main_narration')
    entries_json = form_data.get('entries_json')

    entries = json.loads(entries_json)

    conn = db_mock.get_connection()
    cursor = conn.cursor()
    # conn.start_transaction()

    # Check Workflow
    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
    res_set = cursor.fetchone()
    workflow_enabled = res_set and res_set[0] == '1'
    status = 0 if workflow_enabled else 1

    # 1. Create JV Header
    cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, %s)",
                   (jv_user_code, main_narration, status))
    jv_no = cursor.lastrowid

    # 2. Insert Entries using executemany
    entry_records = []

    # We define a helper parse_float similar to app.py
    def parse_float(val):
        try:
            if not val:
                return 0.0
            return float(str(val).replace(',', ''))
        except (ValueError, TypeError):
            return 0.0

    today_date = datetime.now().date()

    for e in entries:
        # Handle sub account
        sub_code = 0
        if e.get('sub_account'):
            # Format "Code - Name" -> split
            parts = e['sub_account'].split(' - ')
            if parts: sub_code = parts[0]

        # Handle Job No
        job_no = e.get('job_no') if e.get('job_no') else None

        # Currency Info
        curr_code = e.get('currency', 'LKR')
        fc_amt = parse_float(e.get('fc_amount', 0))
        rate = parse_float(e.get('rate', 1))

        entry_records.append((
            e['account'], parse_float(e.get('dr', 0)), parse_float(e.get('cr', 0)),
            entry_date, today_date, e['narration'],
            current_user, jv_no, sub_code, job_no,
            curr_code, fc_amt, rate
        ))

    if entry_records:
        cursor.executemany("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, enty_values_CR,
                entry_effective_date, entry_create_date, entry_naration,
                entry_create_user, entry_jv, entry_sub_account_code, entry_job_number,
                currency_code, fc_amount, exchange_rate
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, entry_records)

    # conn.commit()
    cursor.close()
    conn.close()

def save_journal_entry_unoptimized(db_mock, form_data, session, current_user, current_user_pk):
    jv_user_code = form_data.get('jv_user_code')
    entry_date = form_data.get('entry_date')
    main_narration = form_data.get('main_narration')
    entries_json = form_data.get('entries_json')

    entries = json.loads(entries_json)

    conn = db_mock.get_connection()
    cursor = conn.cursor()
    # conn.start_transaction()

    # Check Workflow
    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
    res_set = cursor.fetchone()
    workflow_enabled = res_set and res_set[0] == '1'
    status = 0 if workflow_enabled else 1

    # 1. Create JV Header
    cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, %s)",
                   (jv_user_code, main_narration, status))
    jv_no = cursor.lastrowid

    # 2. Insert Entries using executemany
    entry_records = []

    # We define a helper parse_float similar to app.py
    def parse_float(val):
        try:
            if not val:
                return 0.0
            return float(str(val).replace(',', ''))
        except (ValueError, TypeError):
            return 0.0

    today_date = datetime.now().date()

    for e in entries:
        # Handle sub account
        sub_code = 0
        if e.get('sub_account'):
            # Format "Code - Name" -> split
            parts = e['sub_account'].split(' - ')
            if parts: sub_code = parts[0]

        # Handle Job No
        job_no = e.get('job_no') if e.get('job_no') else None

        # Currency Info
        curr_code = e.get('currency', 'LKR')
        fc_amt = parse_float(e.get('fc_amount', 0))
        rate = parse_float(e.get('rate', 1))

        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, enty_values_CR,
                entry_effective_date, entry_create_date, entry_naration,
                entry_create_user, entry_jv, entry_sub_account_code, entry_job_number,
                currency_code, fc_amount, exchange_rate
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            e['account'], parse_float(e.get('dr', 0)), parse_float(e.get('cr', 0)),
            entry_date, today_date, e['narration'],
            current_user, jv_no, sub_code, job_no,
            curr_code, fc_amt, rate
        ))

    # conn.commit()
    cursor.close()
    conn.close()

class TestJournalEntryBenchmark(unittest.TestCase):
    def setUp(self):
        self.db_mock = MagicMock()
        self.conn_mock = MagicMock()
        self.cursor_mock = MagicMock()
        self.db_mock.get_connection.return_value = self.conn_mock
        self.conn_mock.cursor.return_value = self.cursor_mock

        self.cursor_mock.fetchone.return_value = ('0',)
        self.cursor_mock.lastrowid = 123

    def test_benchmark_optimized_implementation(self):
        num_items = 500
        entries = []
        for i in range(num_items):
            entries.append({
                'account': f'Acc {i}',
                'dr': 100 if i % 2 == 0 else 0,
                'cr': 100 if i % 2 != 0 else 0,
                'narration': f'Test {i}',
                'sub_account': 'Sub - Name',
                'job_no': f'JOB{i}',
                'currency': 'LKR',
                'fc_amount': 0,
                'rate': 1
            })

        form_data = {
            'jv_user_code': 'JV-001',
            'entry_date': '2023-10-01',
            'main_narration': 'Benchmark JV',
            'entries_json': json.dumps(entries)
        }

        save_journal_entry_unoptimized(self.db_mock, form_data, {}, 'user1', 1)

        executes_unopt = self.cursor_mock.execute.call_count
        executemanys_unopt = self.cursor_mock.executemany.call_count
        total_calls_unopt = executes_unopt + executemanys_unopt

        self.setUp() # reset mocks

        save_journal_entry_optimized(self.db_mock, form_data, {}, 'user1', 1)

        executes_opt = self.cursor_mock.execute.call_count
        executemanys_opt = self.cursor_mock.executemany.call_count
        total_calls_opt = executes_opt + executemanys_opt

        print(f"Unoptimized Implementation: Executed {total_calls_unopt} queries (Execute: {executes_unopt}, Executemany: {executemanys_unopt}) for {num_items} items.")
        print(f"Optimized Implementation: Executed {total_calls_opt} queries (Execute: {executes_opt}, Executemany: {executemanys_opt}) for {num_items} items.")

        # Expect 1 execute for workflow, 1 execute for JV header, 1 executemany for details
        self.assertEqual(executes_opt, 2)
        self.assertEqual(executemanys_opt, 1)

if __name__ == '__main__':
    unittest.main()
