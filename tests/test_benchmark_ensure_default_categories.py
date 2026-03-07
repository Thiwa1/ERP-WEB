import unittest
import sqlite3
import re

from benchmark_ensure_default_categories import original_logic, optimized_logic

class DummyCursor:
    def __init__(self, c):
        self.c = c
    def execute(self, sql, params=None):
        sql = re.sub(r'%s', '?', sql)
        if params:
            self.c.execute(sql, params)
        else:
            self.c.execute(sql)
    def executemany(self, sql, params):
        sql = re.sub(r'%s', '?', sql)
        self.c.executemany(sql, params)
    def fetchone(self):
        return self.c.fetchone()
    def fetchall(self):
        return self.c.fetchall()
    def close(self):
        pass

class DummyConn:
    def __init__(self, c):
        self.c = c
    def cursor(self):
        return DummyCursor(self.c.cursor())
    def commit(self):
        self.c.commit()
    def close(self):
        pass

class TestBenchmarkEnsureDefaultCategories(unittest.TestCase):
    def setUp(self):
        self.conn_orig = sqlite3.connect(":memory:")
        self.conn_opt = sqlite3.connect(":memory:")

        for conn in [self.conn_orig, self.conn_opt]:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE cf_catogory (id INTEGER PRIMARY KEY AUTOINCREMENT, catogory_name TEXT, hold_level INTEGER)")
            conn.commit()

    def tearDown(self):
        self.conn_orig.close()
        self.conn_opt.close()

    def get_all_rows(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT catogory_name, hold_level FROM cf_catogory ORDER BY catogory_name")
        return cursor.fetchall()

    def test_logic_equivalence_empty(self):
        # Empty DB initially
        original_logic(DummyConn(self.conn_orig))
        optimized_logic(DummyConn(self.conn_opt))

        orig_rows = self.get_all_rows(self.conn_orig)
        opt_rows = self.get_all_rows(self.conn_opt)

        self.assertEqual(orig_rows, opt_rows)

    def test_logic_equivalence_partial(self):
        # Add partial data
        for conn in [self.conn_orig, self.conn_opt]:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (?, ?)", ('Operating Activities', 1))
            cursor.execute("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (?, ?)", ('Adjustments', 0))
            conn.commit()

        original_logic(DummyConn(self.conn_orig))
        optimized_logic(DummyConn(self.conn_opt))

        orig_rows = self.get_all_rows(self.conn_orig)
        opt_rows = self.get_all_rows(self.conn_opt)

        self.assertEqual(orig_rows, opt_rows)

    def test_logic_equivalence_full(self):
        # Add full data
        cf_cats = [
            ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
            ('Adjustments', 0), ('Changes In Working Capital', 0)
        ]
        for conn in [self.conn_orig, self.conn_opt]:
            cursor = conn.cursor()
            for name, pos in cf_cats:
                cursor.execute("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (?, ?)", (name, pos))
            conn.commit()

        original_logic(DummyConn(self.conn_orig))
        optimized_logic(DummyConn(self.conn_opt))

        orig_rows = self.get_all_rows(self.conn_orig)
        opt_rows = self.get_all_rows(self.conn_opt)

        self.assertEqual(orig_rows, opt_rows)

if __name__ == '__main__':
    unittest.main()
