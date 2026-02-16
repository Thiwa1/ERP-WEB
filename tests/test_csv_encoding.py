import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from app import app
import io

class TestCSVEncoding(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.secret_key = 'test'
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'ADM001'
            sess['user_pk'] = 1
            sess['username'] = 'admin'

        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_bulk_upload_gl_utf16(self):
        def side_effect(query, params=None, commit=False):
            if "User_Rights" in query:
                return [{'Access_Accounting': 1}]
            if "new_account_table" in query:
                return []
            if "balance_sheet_category" in query:
                return []
            if "p&l_category" in query:
                return []
            if "cf_catogory" in query:
                return []
            return []

        self.mock_db.execute_query.side_effect = side_effect

        content = "Account Name,Account Type,Category,CF Category\nTestAcc,Asset,Current Assets,Operating\n"
        csv_bytes = content.encode('utf-16')

        data = {
            'file': (io.BytesIO(csv_bytes), 'test.csv')
        }

        response = self.client.post('/bulk_upload_gl', data=data, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TestAcc', response.data)

if __name__ == '__main__':
    unittest.main()
