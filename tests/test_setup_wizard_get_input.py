import sys
import unittest
import getpass
from unittest.mock import patch, MagicMock

# Mock mysql, mysql.connector, and pymysql before importing setup_wizard
mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql
sys.modules['pymysql'] = mock_mysql

import setup_wizard

class TestSetupWizardGetInput(unittest.TestCase):

    @patch('builtins.input')
    def test_get_input_no_default_valid_input(self, mock_input):
        mock_input.return_value = 'my_value'
        result = setup_wizard.get_input('Prompt')
        mock_input.assert_called_once_with('Prompt: ')
        self.assertEqual(result, 'my_value')

    @patch('builtins.input')
    def test_get_input_with_default_empty_input(self, mock_input):
        mock_input.return_value = ''
        result = setup_wizard.get_input('Prompt', default='my_default')
        mock_input.assert_called_once_with('Prompt [my_default]: ')
        self.assertEqual(result, 'my_default')

    @patch('builtins.input')
    def test_get_input_with_default_valid_input(self, mock_input):
        mock_input.return_value = 'my_new_value'
        result = setup_wizard.get_input('Prompt', default='my_default')
        mock_input.assert_called_once_with('Prompt [my_default]: ')
        self.assertEqual(result, 'my_new_value')

    @patch('getpass.getpass')
    def test_get_input_is_password(self, mock_getpass):
        mock_getpass.return_value = 'my_password'
        result = setup_wizard.get_input('Prompt', is_password=True)
        mock_getpass.assert_called_once_with('Prompt: ')
        self.assertEqual(result, 'my_password')

class TestGetUserInputs(unittest.TestCase):
    @patch('setup_wizard.get_input')
    def test_get_user_inputs_vat_yes(self, mock_get_input):
        mock_get_input.side_effect = [
            '127.0.0.1', # root_host
            'admin_root', # root_user
            'root_pass', # root_password
            'my_app_db', # app_db_name
            'yes', # vat_registered
            'app_admin', # app_user
            'app_pass', # app_pass
        ]

        config = setup_wizard.get_user_inputs()

        self.assertEqual(config['root_host'], '127.0.0.1')
        self.assertEqual(config['root_user'], 'admin_root')
        self.assertEqual(config['root_password'], 'root_pass')
        self.assertEqual(config['app_db_name'], 'my_app_db')
        self.assertEqual(config['vat_registered'], 1)
        self.assertEqual(config['app_user'], 'app_admin')
        self.assertEqual(config['app_pass'], 'app_pass')
        self.assertEqual(mock_get_input.call_count, 7)

    @patch('setup_wizard.get_input')
    def test_get_user_inputs_vat_no(self, mock_get_input):
        mock_get_input.side_effect = [
            'localhost', # root_host
            'root', # root_user
            '', # root_password
            'Book_keeping', # app_db_name
            'n', # vat_registered
            'bookkeeper', # app_user
            'bookkeeper123', # app_pass
        ]

        config = setup_wizard.get_user_inputs()

        self.assertEqual(config['root_host'], 'localhost')
        self.assertEqual(config['root_user'], 'root')
        self.assertEqual(config['root_password'], '')
        self.assertEqual(config['app_db_name'], 'Book_keeping')
        self.assertEqual(config['vat_registered'], 0)
        self.assertEqual(config['app_user'], 'bookkeeper')
        self.assertEqual(config['app_pass'], 'bookkeeper123')
        self.assertEqual(mock_get_input.call_count, 7)

if __name__ == '__main__':
    unittest.main()
