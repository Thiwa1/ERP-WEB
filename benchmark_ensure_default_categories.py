import sys
import time
from unittest.mock import MagicMock
from datetime import date

# Mock external dependencies
sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['jinja2'] = MagicMock()

import app

# Mock logging to avoid spam
app.logging = MagicMock()

def original_logic(cursor):
    # Balance Sheet Categories
    bs_cats = [
        ('ASSETS', 1),
        ('Non-current assets', 2),
        ('Current assets', 3),
        ('EQUITY AND LIABILITIES', 4),
        ('Capital and reserves', 5),
        ('Current liabilities', 6)
    ]
    for name, pos in bs_cats:
        cursor.execute("SELECT id FROM balance_sheet_category WHERE holding_position = %s", (pos,))
        if not cursor.fetchone():
            try:
                cursor.execute("INSERT INTO balance_sheet_category (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))
            except Exception as e:
                pass

    # P&L Categories
    pl_cats = [
        ('Revenue', 1),
        ('Cost of sales', 2),
        ('Gross profit', 3),
        ('Distribution costs', 4),
        ('Administrative expenses', 5),
        ('Other operating expenses', 6),
        ('Finance cost', 7),
        ('Income from associates', 8),
        ('Income tax expenses', 9),
        ('Minority interest', 10),
        ('Extraordinary items', 11)
    ]
    for name, pos in pl_cats:
        cursor.execute("SELECT id FROM `p&l_category` WHERE holding_position = %s", (pos,))
        if not cursor.fetchone():
            try:
                cursor.execute("INSERT INTO `p&l_category` (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))
            except Exception as e:
                pass

    # CF Categories
    cf_cats = [
        ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
        ('Adjustments', 0), ('Changes In Working Capital', 0)
    ]
    for name, pos in cf_cats:
         cursor.execute("SELECT id FROM cf_catogory WHERE catogory_name = %s", (name,))
         if not cursor.fetchone():
             try:
                 cursor.execute("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", (name, pos))
             except Exception as e:
                 pass

def optimized_logic(cursor):
    # Balance Sheet Categories
    bs_cats = [
        ('ASSETS', 1),
        ('Non-current assets', 2),
        ('Current assets', 3),
        ('EQUITY AND LIABILITIES', 4),
        ('Capital and reserves', 5),
        ('Current liabilities', 6)
    ]
    try:
        cursor.execute("SELECT holding_position FROM balance_sheet_category")
        existing_bs_positions = {row[0] for row in cursor.fetchall()}
    except Exception:
        existing_bs_positions = set()

    bs_inserts = []
    for name, pos in bs_cats:
        if pos not in existing_bs_positions:
            bs_inserts.append((name, pos, date.today()))

    if bs_inserts:
        try:
            cursor.executemany("INSERT INTO balance_sheet_category (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", bs_inserts)
        except Exception as e:
            pass

    # P&L Categories
    pl_cats = [
        ('Revenue', 1),
        ('Cost of sales', 2),
        ('Gross profit', 3),
        ('Distribution costs', 4),
        ('Administrative expenses', 5),
        ('Other operating expenses', 6),
        ('Finance cost', 7),
        ('Income from associates', 8),
        ('Income tax expenses', 9),
        ('Minority interest', 10),
        ('Extraordinary items', 11)
    ]
    try:
        cursor.execute("SELECT holding_position FROM `p&l_category`")
        existing_pl_positions = {row[0] for row in cursor.fetchall()}
    except Exception:
        existing_pl_positions = set()

    pl_inserts = []
    for name, pos in pl_cats:
        if pos not in existing_pl_positions:
            pl_inserts.append((name, pos, date.today()))

    if pl_inserts:
        try:
            cursor.executemany("INSERT INTO `p&l_category` (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", pl_inserts)
        except Exception as e:
            pass

    # CF Categories
    cf_cats = [
        ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
        ('Adjustments', 0), ('Changes In Working Capital', 0)
    ]
    try:
        cursor.execute("SELECT catogory_name FROM cf_catogory")
        existing_cf_names = {row[0] for row in cursor.fetchall()}
    except Exception:
        existing_cf_names = set()

    cf_inserts = []
    for name, pos in cf_cats:
        if name not in existing_cf_names:
            cf_inserts.append((name, pos))

    if cf_inserts:
        try:
            cursor.executemany("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", cf_inserts)
        except Exception as e:
            pass


class MockCursor:
    def __init__(self, populate=False):
        self.populate = populate
        self.execute_calls = 0
        self.executemany_calls = 0
        self.fetchone_calls = 0
        self.fetchall_calls = 0

    def execute(self, query, params=None):
        self.execute_calls += 1

    def executemany(self, query, params=None):
        self.executemany_calls += 1

    def fetchone(self):
        self.fetchone_calls += 1
        if self.populate:
            return (1,)
        return None

    def fetchall(self):
        self.fetchall_calls += 1
        if self.populate:
            return [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,)]
        return []

def run_benchmark(iterations=1000):
    print("--- EMPTY DATABASE (All inserts) ---")

    # Original
    cursor_orig = MockCursor(populate=False)
    start = time.time()
    for _ in range(iterations):
        original_logic(cursor_orig)
    orig_time = time.time() - start

    # Optimized
    cursor_opt = MockCursor(populate=False)
    start = time.time()
    for _ in range(iterations):
        optimized_logic(cursor_opt)
    opt_time = time.time() - start

    print(f"Original Time:  {orig_time:.5f}s (Queries: {cursor_orig.execute_calls})")
    print(f"Optimized Time: {opt_time:.5f}s (Queries: {cursor_opt.execute_calls + cursor_opt.executemany_calls})")
    print(f"Improvement:    {(orig_time / opt_time):.2f}x faster\n")

    print("--- POPULATED DATABASE (No inserts) ---")

    # Original
    cursor_orig_pop = MockCursor(populate=True)
    start = time.time()
    for _ in range(iterations):
        original_logic(cursor_orig_pop)
    orig_time_pop = time.time() - start

    # Optimized
    cursor_opt_pop = MockCursor(populate=True)
    start = time.time()
    for _ in range(iterations):
        optimized_logic(cursor_opt_pop)
    opt_time_pop = time.time() - start

    print(f"Original Time:  {orig_time_pop:.5f}s (Queries: {cursor_orig_pop.execute_calls})")
    print(f"Optimized Time: {opt_time_pop:.5f}s (Queries: {cursor_opt_pop.execute_calls + cursor_opt_pop.executemany_calls})")
    print(f"Improvement:    {(orig_time_pop / opt_time_pop):.2f}x faster")

run_benchmark()
