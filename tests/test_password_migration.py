import unittest
from unittest.mock import patch, MagicMock

try:
    import tests.mock_env
except ImportError:
    pass

from app import app, db, login

class TestPasswordMigrationSecurity(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.test_request_context('/login', method='POST', data=dict(
            company_name='Test Company',
            username='testuser',
            password='plain_password'
        ))
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.db.execute_query')
    @patch('app.master_db.execute_query')
    @patch('app.logging.error')
    @patch('app.session', new_callable=dict)
    @patch('app.flash')
    @patch('app.redirect')
    @patch('app.render_template')
    @patch('sys.stdout', new_callable=MagicMock)
    @patch('sys.stderr', new_callable=MagicMock)
    def test_password_migration_error_logging_safe(self, mock_stderr, mock_stdout, mock_render, mock_redirect, mock_flash, mock_session, mock_logging_error, mock_master_db, mock_execute_query):
        mock_session['db_name'] = 'test_db'
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.form = {'company_name': 'Test Company', 'username': 'testuser', 'password': 'plain_password'}
            def mock_query(query, params=None, commit=False):
                if "UPDATE Login_Table SET Password =" in query: raise Exception("DB_MIGRATION_ERROR_SIMULATION")
                return [{'id': 999, 'User_Code': 'EMP001', 'User_Name': 'testuser', 'Password': 'plain_password'}]
            def mock_master_query(query, params=None, commit=False):
                return [{'id': 1, 'company_name': 'Test Company', 'db_name': 'test_db'}]
            mock_execute_query.side_effect = mock_query
            mock_master_db.side_effect = mock_master_query
            login()
            for call_args in mock_logging_error.call_args_list:
                log_msg = str(call_args[0][0])
                self.assertNotIn('999', log_msg, "User ID exposed in error log.")
                self.assertNotIn('DB_MIGRATION_ERROR_SIMULATION', log_msg, "Exception exposed in error log.")
            for call_args in mock_stdout.write.call_args_list:
                output = str(call_args[0][0])
                self.assertNotIn('999', output, "User ID printed.")
                self.assertNotIn('DB_MIGRATION_ERROR_SIMULATION', output, "Exception printed.")
if __name__ == '__main__':
    unittest.main()
