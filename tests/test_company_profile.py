import os
import unittest
from unittest.mock import patch, MagicMock
import base64

os.environ['SECRET_KEY'] = 'test_secret'

import tests.mock_env
import app

class TestCompanyProfile(unittest.TestCase):
    def setUp(self):
        # Ensure testing config is active
        app.app.config['TESTING'] = True

        # Reset mocks that tests.mock_env sets up on the app module directly
        app.render_template.reset_mock()
        app.request.reset_mock()
        app.flash.reset_mock()
        app.redirect.reset_mock()
        app.url_for.reset_mock()

        # Patch the database execute_query function
        self.mock_db = MagicMock()
        self.db_patcher = patch.object(app, 'db', self.mock_db)
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()

    def test_company_profile_get_no_data(self):
        """Test GET request when no company data is available."""
        def side_effect(query, *args, **kwargs):
            if "User_Rights" in query:
                return [{'Add_New_User': 1}]
            return []

        self.mock_db.execute_query.side_effect = side_effect

        # In mock_env, request is a MagicMock, set method directly
        app.request.method = 'GET'
        app.request.files = {}

        # We also need session if @login_required is used
        with patch.dict('app.session', {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}):
            app.company_profile()

        self.mock_db.execute_query.assert_any_call("SELECT * FROM company LIMIT 1")
        self.mock_db.execute_query.assert_any_call("SELECT currency_code, currency_name FROM currency_table")
        app.render_template.assert_called_once()
        args, kwargs = app.render_template.call_args
        self.assertEqual(args[0], 'company_profile.html')
        self.assertEqual(kwargs['company'], {})
        self.assertEqual(kwargs['currencies'], [{'currency_code': 'LKR', 'currency_name': 'Sri Lankan Rupee'}])

    def test_company_profile_get_with_base64_bytes(self):
        """Test GET request when company logo is base64 bytes (decode succeeds)."""
        sample_logo_str = "base64_encoded_string"
        sample_logo_bytes = sample_logo_str.encode('utf-8')

        def side_effect(query, *args, **kwargs):
            if "User_Rights" in query:
                return [{'Add_New_User': 1}]
            return [{'company_log': sample_logo_bytes}]

        self.mock_db.execute_query.side_effect = side_effect

        app.request.method = 'GET'
        app.request.files = {}
        with patch.dict('app.session', {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}):
            app.company_profile()

        app.render_template.assert_called_once()
        args, kwargs = app.render_template.call_args
        self.assertEqual(args[0], 'company_profile.html')
        self.assertEqual(kwargs['company']['company_log'], sample_logo_str)

    def test_company_profile_get_with_raw_image_bytes(self):
        """Test GET request when company logo is raw image bytes (decode fails, fallback to b64encode)."""
        raw_image_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'

        def side_effect(query, *args, **kwargs):
            if "User_Rights" in query:
                return [{'Add_New_User': 1}]
            return [{'company_log': raw_image_bytes}]

        self.mock_db.execute_query.side_effect = side_effect

        app.request.method = 'GET'
        app.request.files = {}
        with patch.dict('app.session', {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}):
            app.company_profile()

        app.render_template.assert_called_once()
        args, kwargs = app.render_template.call_args
        self.assertEqual(args[0], 'company_profile.html')

        expected_base64 = base64.b64encode(raw_image_bytes).decode('utf-8')
        self.assertEqual(kwargs['company']['company_log'], expected_base64)

if __name__ == '__main__':
    unittest.main()
