import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Set dummy environment variables for app import
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USER'] = 'test'
os.environ['DB_PASSWORD'] = 'test'
os.environ['DB_NAME'] = 'test'

import flask
from app import app, db

class TestReversalReconciliationCheck(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        self.client = app.test_client()
        self.db_mock = MagicMock()
        # Mock the db object in app.py
        self.patcher = patch('app.db', self.db_mock)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('app.get_current_user_id', return_value='test_user')
    @patch('app.db.get_connection')
    def test_pos_reversal_reconciled(self, mock_conn_factory, mock_get_user):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_factory.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock reconciliation check: 1 means it IS reconciled
        mock_cursor.fetchone.return_value = [1]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_pk'] = 1
        response = self.client.post('/pos_reversal/process', data={'jv': 'JV001'}, follow_redirects=True)

        self.assertIn(b"This transaction is reconciled. To process, first remove the reconciliation.", response.data)
        # Ensure the actual reversal SP wasn't called
        for call in mock_cursor.execute.call_args_list:
            self.assertNotIn("CALL JV_Entry_Revers", call[0][0])

    @patch('app.get_current_user_id', return_value='test_user')
    @patch('app.db.get_connection')
    @patch('app.check_permission', return_value=True)
    def test_bank_payment_reversal_reconciled(self, mock_check_perm, mock_conn_factory, mock_get_user):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_factory.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [1]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_pk'] = 1
        response = self.client.post('/bank_payment_reversal/process', data={'jv': 'JV001'}, follow_redirects=True)

        self.assertIn(b"This transaction is reconciled. To process, first remove the reconciliation.", response.data)

    @patch('app.get_current_user_id', return_value='test_user')
    @patch('app.db.get_connection')
    @patch('app.check_permission', return_value=True)
    def test_cash_payment_reversal_reconciled(self, mock_check_perm, mock_conn_factory, mock_get_user):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_factory.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [1]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_pk'] = 1
        response = self.client.post('/cash_payment_reversal/process', data={'jv': 'JV001'}, follow_redirects=True)

        self.assertIn(b"This transaction is reconciled. To process, first remove the reconciliation.", response.data)

    @patch('app.get_current_user_id', return_value='test_user')
    @patch('app.db.get_connection')
    @patch('app.check_permission', return_value=True)
    def test_direct_payment_reversal_reconciled(self, mock_check_perm, mock_conn_factory, mock_get_user):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_factory.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [1]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_pk'] = 1
        response = self.client.post('/direct_payment_reversal/process', data={'jv': 'JV001'}, follow_redirects=True)

        self.assertIn(b"This transaction is reconciled. To process, first remove the reconciliation.", response.data)

    @patch('app.get_current_user_id', return_value='test_user')
    @patch('app.db.get_connection')
    @patch('app.check_permission', return_value=True)
    def test_journal_entry_reversal_reconciled(self, mock_check_perm, mock_conn_factory, mock_get_user):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_factory.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = [1]

        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test_user'
            sess['user_pk'] = 1
        response = self.client.post('/journal_entry/reverse', data={'jv_no': 'JV001'})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"This transaction is reconciled. To process, first remove the reconciliation.", response.data)

if __name__ == '__main__':
    unittest.main()
