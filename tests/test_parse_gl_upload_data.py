import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tests.mock_env
import app

class MockFile:
    def __init__(self, content, filename='test.csv'):
        self.stream = io.BytesIO(content)
        self.filename = filename

    def read(self):
        return self.stream.read()

class TestParseGLUploadData(unittest.TestCase):
    @patch('app.parse_csv_file')
    def test_parse_gl_upload_data_success(self, mock_parse_csv_file):
        # Setup mock behavior for parse_csv_file
        mock_csv_content = "Account Name,Debit,Credit\nBank,100,0\nCash,0,100\n"
        mock_parse_csv_file.return_value = mock_csv_content

        file = MockFile(b"dummy_content")
        result = app.parse_gl_upload_data(file)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['Account Name'], 'Bank')
        self.assertEqual(result[0]['Debit'], '100')
        self.assertEqual(result[0]['Credit'], '0')
        self.assertEqual(result[1]['Account Name'], 'Cash')
        self.assertEqual(result[1]['Debit'], '0')
        self.assertEqual(result[1]['Credit'], '100')

    @patch('app.parse_csv_file')
    def test_parse_gl_upload_data_ignores_missing_account_name(self, mock_parse_csv_file):
        # Should ignore the row without Account Name
        mock_csv_content = "Account Name,Debit,Credit\nBank,100,0\n,0,100\n"
        mock_parse_csv_file.return_value = mock_csv_content

        file = MockFile(b"dummy_content")
        result = app.parse_gl_upload_data(file)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Bank')

    @patch('app.parse_csv_file')
    def test_parse_gl_upload_data_cleans_whitespace(self, mock_parse_csv_file):
        mock_csv_content = " Account Name , Debit , Credit \n  Bank  ,  100  ,  0  \n"
        mock_parse_csv_file.return_value = mock_csv_content

        file = MockFile(b"dummy_content")
        result = app.parse_gl_upload_data(file)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Bank')
        self.assertEqual(result[0]['Debit'], '100')
        self.assertEqual(result[0]['Credit'], '0')

    @patch('app.parse_csv_file')
    def test_parse_gl_upload_data_ignores_empty_keys(self, mock_parse_csv_file):
        # Trailing comma causes an empty key in csv.DictReader
        mock_csv_content = "Account Name,Debit,Credit,\nBank,100,0,\n"
        mock_parse_csv_file.return_value = mock_csv_content

        file = MockFile(b"dummy_content")
        result = app.parse_gl_upload_data(file)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Bank')
        self.assertEqual(result[0]['Debit'], '100')
        self.assertEqual(result[0]['Credit'], '0')
        # Ensure empty key was ignored
        self.assertNotIn('', result[0])

    @patch('app.parse_csv_file')
    def test_parse_gl_upload_data_error_handling(self, mock_parse_csv_file):
        mock_parse_csv_file.side_effect = Exception("Parse error")

        file = MockFile(b"dummy_content")
        with self.assertRaises(ValueError) as cm:
            app.parse_gl_upload_data(file)
        self.assertIn("Error parsing CSV data: Parse error", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
