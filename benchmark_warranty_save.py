import time
import os
import sys

sys.path.append('.')

class MockForm(dict):
    def getlist(self, key):
        return self[key]

class MockRequest:
    def __init__(self, data):
        self.form = MockForm(data)

# Dummy mock object for cursor
class MockCursor:
    def __init__(self):
        self.execute_count = 0
        self.executemany_count = 0

    def execute(self, query, params=None):
        self.execute_count += 1
        # Simulate some delay to represent network overhead
        time.sleep(0.0005)

    def executemany(self, query, params_list):
        self.executemany_count += 1
        # Simulate network overhead for a single batch call + small per-item delay
        time.sleep(0.001 + (len(params_list) * 0.0001))

    def close(self):
        pass

class MockConnection:
    def start_transaction(self):
        pass

    def commit(self):
        pass

    def cursor(self):
        return MockCursor()

    def close(self):
        pass

def get_mock_connection():
    return MockConnection()

def run_benchmark():
    num_items = 500
    ids_insert = ['0'] * num_items
    names = [f'Name {i}' for i in range(num_items)]
    years = ['1'] * num_items
    months = ['0'] * num_items
    days = ['0'] * num_items

    # We also need some fake existing IDs for the update test
    ids_update = [str(i+1) for i in range(num_items)]

    # Define the original unoptimized logic
    def warranty_save_unoptimized(request):
        ids = request.form.getlist('id[]')
        names = request.form.getlist('name[]')
        years = request.form.getlist('year[]')
        months = request.form.getlist('month[]')
        days = request.form.getlist('day[]')

        conn = get_mock_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        for i in range(len(ids)):
            wid = int(ids[i])
            if wid == 0: # Insert
                cursor.execute("""
                    INSERT INTO inventory_vorenty_period (yeas_, month, date_, name)
                    VALUES (%s, %s, %s, %s)
                """, (years[i], months[i], days[i], names[i]))
            else: # Update
                cursor.execute("""
                    UPDATE inventory_vorenty_period
                    SET yeas_ = %s, month = %s, date_ = %s, name = %s
                    WHERE id = %s
                """, (years[i], months[i], days[i], names[i], wid))

        conn.commit()
        cursor.close()

    # Define the optimized logic using executemany
    def warranty_save_optimized(request):
        ids = request.form.getlist('id[]')
        names = request.form.getlist('name[]')
        years = request.form.getlist('year[]')
        months = request.form.getlist('month[]')
        days = request.form.getlist('day[]')

        insert_params = []
        update_params = []

        for i in range(len(ids)):
            wid = int(ids[i])
            if wid == 0:
                insert_params.append((years[i], months[i], days[i], names[i]))
            else:
                update_params.append((years[i], months[i], days[i], names[i], wid))

        conn = get_mock_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        if insert_params:
            cursor.executemany("""
                INSERT INTO inventory_vorenty_period (yeas_, month, date_, name)
                VALUES (%s, %s, %s, %s)
            """, insert_params)

        if update_params:
            cursor.executemany("""
                UPDATE inventory_vorenty_period
                SET yeas_ = %s, month = %s, date_ = %s, name = %s
                WHERE id = %s
            """, update_params)

        conn.commit()
        cursor.close()

    # Benchmark Unoptimized Insert
    req_insert = MockRequest(data={
        'id[]': ids_insert, 'name[]': names, 'year[]': years, 'month[]': months, 'day[]': days
    })

    start = time.time()
    warranty_save_unoptimized(req_insert)
    end = time.time()
    print(f"Unoptimized Insert ({num_items} items): {end - start:.4f}s")

    # Benchmark Unoptimized Update
    req_update = MockRequest(data={
        'id[]': ids_update, 'name[]': names, 'year[]': years, 'month[]': months, 'day[]': days
    })

    start = time.time()
    warranty_save_unoptimized(req_update)
    end = time.time()
    print(f"Unoptimized Update ({num_items} items): {end - start:.4f}s")


    # Benchmark Optimized Insert
    start = time.time()
    warranty_save_optimized(req_insert)
    end = time.time()
    print(f"Optimized Insert ({num_items} items): {end - start:.4f}s")

    # Benchmark Optimized Update
    start = time.time()
    warranty_save_optimized(req_update)
    end = time.time()
    print(f"Optimized Update ({num_items} items): {end - start:.4f}s")

if __name__ == '__main__':
    run_benchmark()
