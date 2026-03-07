import time
import os
import random
from unittest.mock import MagicMock
from datetime import date
from datetime import date

# Set mock db


def original_logic(defaults, db):
    current_user = 0 # System

    for acc in defaults:
        name, bs_pos, bs_cat, pl_pos, pl_cat, acc_type = acc
        res = db.execute_query("SELECT id FROM new_account_table WHERE account_name = %s", (name,))

        if not res:
            basement = 'DR' if acc_type in ['expenses', 'assets'] else 'CR'

            query = """
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                    account_hold_possion_PL, account_name_of_catogory_PL,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    accont_create_date, account_create_user, account_active, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """
            db.execute_query(query, (
                name, bs_pos, bs_cat, pl_pos, pl_cat,
                1 if acc_type=='income' else 0, 1 if acc_type=='expenses' else 0,
                1 if acc_type=='assets' else 0, 1 if acc_type=='liabilities' else 0, 0,
                date.today(), current_user, basement
            ), commit=True)

def optimized_logic(defaults, db):
    current_user = 0 # System

    if not defaults:
        return

    # Extract all account names
    account_names = [acc[0] for acc in defaults]

    # Check existing accounts using a single batch query
    format_strings = ','.join(['%s'] * len(account_names))
    query = f"SELECT account_name FROM new_account_table WHERE account_name IN ({format_strings})"

    existing_rows = db.execute_query(query, tuple(account_names))

    # Store existing account names in a set for O(1) lookups
    existing_names = {row['account_name'] for row in (existing_rows or [])}

    for acc in defaults:
        name, bs_pos, bs_cat, pl_pos, pl_cat, acc_type = acc

        # Check against the set instead of making a DB query
        if name not in existing_names:
            basement = 'DR' if acc_type in ['expenses', 'assets'] else 'CR'

            query = """
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                    account_hold_possion_PL, account_name_of_catogory_PL,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    accont_create_date, account_create_user, account_active, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """
            db.execute_query(query, (
                name, bs_pos, bs_cat, pl_pos, pl_cat,
                1 if acc_type=='income' else 0, 1 if acc_type=='expenses' else 0,
                1 if acc_type=='assets' else 0, 1 if acc_type=='liabilities' else 0, 0,
                date.today(), current_user, basement
            ), commit=True)

def benchmark():
    defaults = [
        ('Account Payable', 6, 'Current liabilities', None, None, 'liabilities'),
        ('Account Receivable', 3, 'Current assets', None, None, 'assets'),
        ('Cost Of Goods Sold', None, None, 2, 'Cost Of Sales', 'expenses'),
        ('Sales', None, None, 1, 'Revenue', 'income'),
        ('Inventory', 3, 'Current assets', None, None, 'assets'),
        ('VAT Control', 6, 'Current liabilities', None, None, 'liabilities'),
        ('Cash In Hand', 3, 'Current assets', None, None, 'assets')
    ]

    class MockDB:
        def __init__(self, existing):
            self.existing = existing
            self.query_count = 0

        def execute_query(self, query, params=None, commit=False):
            self.query_count += 1
            if query.startswith("SELECT id"):
                name = params[0]
                if name in self.existing:
                    return [{'id': 1}]
                return []
            elif query.startswith("SELECT account_name"):
                return [{'account_name': name} for name in params if name in self.existing]
            return None

    # Scenario 1: No accounts exist
    print("Scenario 1: No accounts exist")

    # Original
    db1 = MockDB(set())
    start = time.perf_counter()
    for _ in range(1000):
        original_logic(defaults, db1)
    orig_time = time.perf_counter() - start
    print(f"Original logic: {orig_time:.4f}s (Queries: {db1.query_count})")

    # Optimized
    db2 = MockDB(set())
    start = time.perf_counter()
    for _ in range(1000):
        optimized_logic(defaults, db2)
    opt_time = time.perf_counter() - start
    print(f"Optimized logic: {opt_time:.4f}s (Queries: {db2.query_count})")
    print(f"Improvement: {orig_time / opt_time:.2f}x")
    print()

    # Scenario 2: All accounts exist
    print("Scenario 2: All accounts exist")
    existing_all = {acc[0] for acc in defaults}

    # Original
    db3 = MockDB(existing_all)
    start = time.perf_counter()
    for _ in range(1000):
        original_logic(defaults, db3)
    orig_time = time.perf_counter() - start
    print(f"Original logic: {orig_time:.4f}s (Queries: {db3.query_count})")

    # Optimized
    db4 = MockDB(existing_all)
    start = time.perf_counter()
    for _ in range(1000):
        optimized_logic(defaults, db4)
    opt_time = time.perf_counter() - start
    print(f"Optimized logic: {opt_time:.4f}s (Queries: {db4.query_count})")
    print(f"Improvement: {orig_time / opt_time:.2f}x")

if __name__ == '__main__':
    benchmark()
