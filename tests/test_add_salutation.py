
import sys
from unittest.mock import MagicMock
if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()
import sys
from unittest.mock import MagicMock, patch
import tests.mock_env

# Import app after mocking
import app as app_module
import unittest

app_module.app.config = {'TESTING': True}

class TestAddSalutation(unittest.TestCase):
    def setUp(self):
        # Reset mocks from mock_env
        self.actual_request_mock = app_module.request
        self.actual_flash_mock = app_module.flash
        self.actual_redirect_mock = app_module.redirect
        self.actual_url_for_mock = app_module.url_for

        self.actual_request_mock.reset_mock()
        self.actual_flash_mock.reset_mock()
        self.actual_redirect_mock.reset_mock()
        self.actual_url_for_mock.reset_mock()

        # Reset Session
        self.actual_session = app_module.session
        self.actual_session.clear()
        self.actual_session.update({'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'})

        # Patch app.db
        self.mock_db = MagicMock()
        self.db_patcher = patch('app.db', self.mock_db)
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()

    def test_add_salutation_post_success(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        # Mocking form.get
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.return_value = 'Dr.'

        # Execute
        app_module.add_salutation()

        # Assertions
        self.mock_db.execute_query.assert_called_once_with(
            "INSERT INTO suplier_suporting_1 (id, salutation) VALUES (%s, %s)",
            (0, 'Dr.'), commit=True
        )
        self.actual_flash_mock.assert_called_with('Salutation added.', 'success')
        self.actual_url_for_mock.assert_called_with('add_customer')
        self.actual_redirect_mock.assert_called_once()

    def test_add_salutation_post_empty(self):
        # Setup Request with empty salutation
        self.actual_request_mock.method = 'POST'

        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.return_value = ''

        # Execute
        app_module.add_salutation()

        # Assertions
        self.mock_db.execute_query.assert_not_called()
        self.actual_flash_mock.assert_not_called()
        self.actual_url_for_mock.assert_called_with('add_customer')
        self.actual_redirect_mock.assert_called_once()

    def test_add_salutation_post_error(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.return_value = 'Dr.'

        # Setup DB error
        self.mock_db.execute_query.side_effect = Exception("DB Error")

        # Execute
        app_module.add_salutation()

        # Assertions
        self.mock_db.execute_query.assert_called_once()
        self.actual_flash_mock.assert_called_with('Error adding salutation: DB Error', 'danger')
        self.actual_url_for_mock.assert_called_with('add_customer')
        self.actual_redirect_mock.assert_called_once()

if __name__ == '__main__':
    unittest.main()
