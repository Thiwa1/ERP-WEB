import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Use existing mock environment
import tests.mock_env

# The app import will now use the mocked modules
from app import app
import flask

class TestReversalBlock(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        tests.mock_env.mock_flask.flash.reset_mock()
        tests.mock_env.mock_flask.redirect.reset_mock()

    @patch('app.db')
    @patch('app.session', {'user_id': '1001', 'user_pk': 1})
    @patch('app.check_permission', return_value=True)
    def test_pos_reversal_blocked_when_reconciled(self, mock_perm, mock_db_instance):
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_instance.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock reconciled check: COUNT(*) > 0
        mock_cursor.fetchone.return_value = [1]

        # Directly call the function as it's decorated with passthrough route in mock_env
        from app import pos_reversal_process

        # Mock request.form
        with patch('app.request') as mock_request:
            mock_request.form = {'jv': '100'}

            response = pos_reversal_process()

            # Check if flash was called with correct message
            tests.mock_env.mock_flask.flash.assert_called_with(
                "This transaction is reconciled. To process, first remove the reconciliation.",
                "danger"
            )
            # Check if redirect was called
            tests.mock_env.mock_flask.redirect.assert_called()

    @patch('app.db')
    @patch('app.session', {'user_id': '1001', 'user_pk': 1})
    @patch('app.check_permission', return_value=True)
    def test_journal_entry_reverse_blocked_when_reconciled(self, mock_perm, mock_db_instance):
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_instance.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock reconciled check: COUNT(*) > 0
        mock_cursor.fetchone.return_value = [1]

        from app import reverse_journal_entry

        with patch('app.request') as mock_request:
            mock_request.form = {'jv_no': '100'}

            response = reverse_journal_entry()

            # This route returns a dict or JSON response. In mock env it might be a tuple if flask.jsonify is mocked.
            if isinstance(response, tuple):
                response = response[0]
            self.assertEqual(response['error'], 'This transaction is reconciled. To process, first remove the reconciliation.')

    @patch('app.db')
    @patch('app.session', {'user_id': '1001', 'user_pk': 1})
    @patch('app.check_permission', return_value=True)
    def test_bank_payment_reversal_blocked_when_reconciled(self, mock_perm, mock_db_instance):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_instance.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]

        from app import bank_payment_reversal_process
        with patch('app.request') as mock_request:
            mock_request.form = {'jv': '100'}
            response = bank_payment_reversal_process()
            tests.mock_env.mock_flask.flash.assert_called_with(
                "This transaction is reconciled. To process, first remove the reconciliation.",
                "danger"
            )

    @patch('app.db')
    @patch('app.session', {'user_id': '1001', 'user_pk': 1})
    @patch('app.check_permission', return_value=True)
    def test_cash_payment_reversal_blocked_when_reconciled(self, mock_perm, mock_db_instance):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_instance.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]

        from app import cash_payment_reversal_process
        with patch('app.request') as mock_request:
            mock_request.form = {'jv': '100'}
            response = cash_payment_reversal_process()
            tests.mock_env.mock_flask.flash.assert_called_with(
                "This transaction is reconciled. To process, first remove the reconciliation.",
                "danger"
            )

    @patch('app.db')
    @patch('app.session', {'user_id': '1001', 'user_pk': 1})
    @patch('app.check_permission', return_value=True)
    def test_direct_payment_reversal_blocked_when_reconciled(self, mock_perm, mock_db_instance):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_instance.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]

        from app import direct_payment_reversal_process
        with patch('app.request') as mock_request:
            mock_request.form = {'jv': '100'}
            response = direct_payment_reversal_process()
            tests.mock_env.mock_flask.flash.assert_called_with(
                "This transaction is reconciled. To process, first remove the reconciliation.",
                "danger"
            )

if __name__ == '__main__':
    unittest.main()
