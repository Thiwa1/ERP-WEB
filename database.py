import mysql.connector
from datetime import datetime

class Database:
    def __init__(self, config):
        self.config = config
        self.last_error = None
        self.db_name_getter = None

    def set_db_name_getter(self, getter):
        self.db_name_getter = getter

    def get_connection(self):
        try:
            config = self.config.copy()
            if self.db_name_getter:
                dynamic_db = self.db_name_getter()
                if dynamic_db:
                    config['database'] = dynamic_db

            return mysql.connector.connect(**config)
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
