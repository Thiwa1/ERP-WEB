import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask

# Setup Flask Mock structure to support app.config
mock_app_instance = MagicMock()
mock_app_instance.config = {} # Simulate dict
mock_flask.Flask.return_value = mock_app_instance

sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['database'] = MagicMock()

import app

class MockFile:
    def __init__(self, content, filename='test.csv'):
        self.stream = io.BytesIO(content)
        self.filename = filename

    def read(self):
        return self.stream.read()

class TestCSVParser(unittest.TestCase):
    def test_valid_utf8(self):
        content = b"Account Name,Debit,Credit\nBank,100,0\n"
        file = MockFile(content)
        result = app.parse_csv_file(file)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Bank')

    def test_valid_utf8_sig(self):
        content = b"\xef\xbb\xbfAccount Name,Debit,Credit\nBank,100,0\n"
        file = MockFile(content)
        result = app.parse_csv_file(file)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Bank')

    def test_valid_latin1(self):
        # 'Café' in latin1 is \x43\x61\x66\xe9
        content = b"Account Name,Debit,Credit\nCaf\xe9,100,0\n"
        file = MockFile(content)
        result = app.parse_csv_file(file)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Account Name'], 'Café')

    def test_required_columns_success(self):
        content = b"Account Name,Debit,Credit\nBank,100,0\n"
        file = MockFile(content)
        result = app.parse_csv_file(file, required_columns=['Account Name', 'Debit'])
        self.assertEqual(len(result), 1)

    def test_required_columns_missing(self):
        content = b"Account Name,Debit,Credit\nBank,100,0\n"
        file = MockFile(content)
        # 'Type' is missing
        with self.assertRaises(ValueError) as cm:
            app.parse_csv_file(file, required_columns=['Account Name', 'Type'])
        self.assertIn("Missing required columns: Type", str(cm.exception))

    def test_empty_file(self):
        content = b""
        file = MockFile(content)
        # Should raise error if columns required
        with self.assertRaises(ValueError) as cm:
             app.parse_csv_file(file, required_columns=['Account Name'])
        self.assertIn("File is empty", str(cm.exception))

    def test_empty_file_no_requirements(self):
        content = b""
        file = MockFile(content)
        result = app.parse_csv_file(file)
        self.assertEqual(result, [])

    def test_short_row_handling(self):
        # Header has 3 columns, row has 2
        content = b"Col1,Col2,Col3\nVal1,Val2\n"
        file = MockFile(content)
        result = app.parse_csv_file(file)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0]['Col1'], 'Val1')
        self.assertEqual(result[0]['Col2'], 'Val2')

        # Missing column should be None in DictReader, converted to '' by helper logic
        self.assertEqual(result[0]['Col3'], '')

if __name__ == '__main__':
    unittest.main()
