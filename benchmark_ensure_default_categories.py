import time
import logging

def original_logic(conn):
    cursor = conn.cursor()
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
                 logging.error(f"Error inserting CF category {name}: {e}")
    conn.commit()
    cursor.close()

def optimized_logic(conn):
    cursor = conn.cursor()
    cf_cats = [
        ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
        ('Adjustments', 0), ('Changes In Working Capital', 0)
    ]

    # Fetch existing
    cat_names = [c[0] for c in cf_cats]
    format_strings = ','.join(['%s'] * len(cat_names))
    cursor.execute(f"SELECT catogory_name FROM cf_catogory WHERE catogory_name IN ({format_strings})", tuple(cat_names))

    existing_cats = {row[0] for row in cursor.fetchall()}

    # Insert new ones
    to_insert = [(name, pos) for name, pos in cf_cats if name not in existing_cats]
    if to_insert:
        try:
            cursor.executemany("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", to_insert)
        except Exception as e:
            logging.error(f"Error inserting CF categories: {e}")
    conn.commit()
    cursor.close()

def main():
    import sqlite3
    import re
    # Setup sqlite DB in memory
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE cf_catogory (id INTEGER PRIMARY KEY, catogory_name TEXT, hold_level INTEGER)")
    conn.commit()

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

    dummy_conn = DummyConn(conn)

    def sqlite_setup():
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cf_catogory")
        conn.commit()

    # Increase iterations to 10000 for better measurement
    iterations = 10000

    # Measure original (first insertion)
    start_time = time.time()
    for _ in range(iterations):
        sqlite_setup()
        original_logic(dummy_conn)
    original_time_insert = time.time() - start_time
    print(f"Original Time (Insertions): {original_time_insert:.4f} seconds")

    # Measure original (already existing)
    start_time = time.time()
    for _ in range(iterations):
        original_logic(dummy_conn)
    original_time_exist = time.time() - start_time
    print(f"Original Time (Already existing): {original_time_exist:.4f} seconds")

    sqlite_setup()

    # Measure optimized (first insertion)
    start_time = time.time()
    for _ in range(iterations):
        sqlite_setup()
        optimized_logic(dummy_conn)
    optimized_time_insert = time.time() - start_time
    print(f"Optimized Time (Insertions): {optimized_time_insert:.4f} seconds")

    # Measure optimized (already existing)
    start_time = time.time()
    for _ in range(iterations):
        optimized_logic(dummy_conn)
    optimized_time_exist = time.time() - start_time
    print(f"Optimized Time (Already existing): {optimized_time_exist:.4f} seconds")

    print(f"Speedup (Insertions): {original_time_insert / optimized_time_insert:.2f}x")
    print(f"Speedup (Already existing): {original_time_exist / optimized_time_exist:.2f}x")

if __name__ == '__main__':
    main()
