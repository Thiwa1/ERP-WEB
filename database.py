import mysql.connector
from datetime import datetime
from contextlib import contextmanager

class Database:
    def __init__(self, config):
        self.config = config
        self.last_error = None

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except mysql.connector.Error as err:
            self.last_error = str(err)
            print(f"Error connecting to database: {err}")
            return None

    def execute_query(self, query, params=None, commit=False):
        conn = self.get_connection()
        if not conn:
            return None

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                return last_id
            else:
                return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Query Error: {err}")
            if commit:
                conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    def execute_transaction(self, queries):
        """
        Executes a list of queries as a transaction.
        queries: list of tuples (query, params)
        """
        conn = self.get_connection()
        if not conn:
            return False

        cursor = conn.cursor()
        try:
            conn.start_transaction()
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Transaction Error: {err}")
            conn.rollback()
            raise err
        finally:
            cursor.close()
            conn.close()

    @contextmanager
    def transaction_cursor(self):
        """
        Context manager for database transactions.
        Yields a cursor.
        Commits on success, rolls back on exception.
        """
        conn = self.get_connection()
        if not conn:
            raise Exception("Failed to connect to database")

        cursor = conn.cursor()
        try:
            conn.start_transaction()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
