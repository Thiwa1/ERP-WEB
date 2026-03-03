import unittest
import sys
import os

# Use mock_env to avoid dependency issues when importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tests.mock_env

# Import the function to test
from app import validate_db_config

class TestValidateDbConfig(unittest.TestCase):

    def test_valid_configs(self):
        """Test with valid database configurations."""
        valid_configs = [
            {'user': 'root', 'database': 'my_db_1', 'host': '127.0.0.1'},
            {'user': 'admin_user', 'database': 'db-prod', 'host': 'localhost'},
            {'user': 'dbuser123', 'database': 'company_db', 'host': 'mysql.server.local'},
            {'user': 'u', 'database': 'd', 'host': 'h'},
            {'user': 'abc-123_def', 'database': 'abc-123_def', 'host': 'abc-123_def.com'},
        ]

        for config in valid_configs:
            with self.subTest(config=config):
                self.assertTrue(validate_db_config(config))

    def test_missing_or_empty_fields(self):
        """Test configs where fields are missing or empty (should be treated as valid if other fields are valid)."""
        valid_configs = [
            {}, # All missing
            {'user': '', 'database': '', 'host': ''}, # All empty
            {'user': 'root'}, # Only user
            {'database': 'my_db'}, # Only database
            {'host': 'localhost'}, # Only host
            {'user': 'root', 'password': 'my-complex-password!@#'} # Password is not validated by this func
        ]

        for config in valid_configs:
            with self.subTest(config=config):
                self.assertTrue(validate_db_config(config))

    def test_invalid_user(self):
        """Test with invalid user names."""
        invalid_users = [
            '-root', # Starts with dash
            'root;', # Semicolon
            'user name', # Space
            'root" OR 1=1--', # SQL injection
            'admin@local', # At sign (not allowed by strict_pattern)
            'user.name', # Dot not allowed in user
            123, # Not a string
            ['root'], # Not a string
        ]

        for user in invalid_users:
            with self.subTest(user=user):
                config = {'user': user, 'database': 'db', 'host': 'localhost'}
                self.assertFalse(validate_db_config(config))

    def test_invalid_database(self):
        """Test with invalid database names."""
        invalid_dbs = [
            '-mydb', # Starts with dash
            'my db', # Space
            'db; DROP TABLE users;', # SQL injection
            'db.name', # Dot not allowed in database
            123, # Not a string
        ]

        for db in invalid_dbs:
            with self.subTest(database=db):
                config = {'user': 'root', 'database': db, 'host': 'localhost'}
                self.assertFalse(validate_db_config(config))

    def test_invalid_host(self):
        """Test with invalid host names."""
        invalid_hosts = [
            '-localhost', # Starts with dash
            'local host', # Space
            'localhost;', # Semicolon
            '127.0.0.1 & echo "hacked"', # Command injection
            123, # Not a string
            # colons aren't allowed by host_pattern `^[a-zA-Z0-9_.-]+$`
            '127.0.0.1:3306',
            '[::1]',
        ]

        for host in invalid_hosts:
            with self.subTest(host=host):
                config = {'user': 'root', 'database': 'db', 'host': host}
                self.assertFalse(validate_db_config(config))

if __name__ == '__main__':
    unittest.main()
