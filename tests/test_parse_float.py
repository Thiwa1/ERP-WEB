import unittest
import sys
from unittest.mock import MagicMock

# Mock dependencies before importing app
from unittest.mock import MagicMock
import sys
import os

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables before app import
os.environ['SECRET_KEY'] = 'test_secret_key'

# Mock missing modules
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['mysql.connector.pooling'] = MagicMock()

from app import parse_float

class TestParseFloat(unittest.TestCase):
    def test_basic_numbers(self):
        """Test with integers and floats."""
        self.assertEqual(parse_float(123), 123.0)
        self.assertEqual(parse_float(123.45), 123.45)
        self.assertEqual(parse_float(-123.45), -123.45)
        self.assertEqual(parse_float(0), 0.0)

    def test_string_numbers(self):
        """Test with simple numeric strings."""
        self.assertEqual(parse_float("123"), 123.0)
        self.assertEqual(parse_float("123.45"), 123.45)
        self.assertEqual(parse_float("-123.45"), -123.45)
        self.assertEqual(parse_float("0"), 0.0)

    def test_comma_formatting(self):
        """Test strings with commas."""
        self.assertEqual(parse_float("1,234.56"), 1234.56)
        self.assertEqual(parse_float("1,234,567.89"), 1234567.89)
        self.assertEqual(parse_float("-1,234.56"), -1234.56)

    def test_whitespace(self):
        """Test strings with leading/trailing whitespace."""
        self.assertEqual(parse_float("  123.45  "), 123.45)
        self.assertEqual(parse_float("  1,234.56  "), 1234.56)

    def test_none_and_empty(self):
        """Test None, empty strings, and whitespace-only strings."""
        self.assertEqual(parse_float(None), 0.0)
        self.assertEqual(parse_float(""), 0.0)
        self.assertEqual(parse_float("   "), 0.0)

    def test_invalid_inputs(self):
        """Test invalid strings and unsupported types."""
        self.assertEqual(parse_float("abc"), 0.0)
        self.assertEqual(parse_float("12.34.56"), 0.0)
        self.assertEqual(parse_float("12,34,56"), 123456.0) # This is how float("123456") behaves
        self.assertEqual(parse_float([]), 0.0)
        self.assertEqual(parse_float({}), 0.0)

    def test_value_error(self):
        """Test explicit ValueError scenarios."""
        # A string that float() cannot parse raises ValueError
        self.assertEqual(parse_float("invalid_float_string"), 0.0)
        # Strings with symbols instead of numbers
        self.assertEqual(parse_float("$100"), 0.0)
        self.assertEqual(parse_float("100%"), 0.0)

    def test_type_error(self):
        """Test explicit TypeError scenarios."""
        # Complex numbers or objects that float() rejects as unconvertible types
        self.assertEqual(parse_float(1+2j), 0.0)
        self.assertEqual(parse_float(object()), 0.0)
        self.assertEqual(parse_float([1, 2, 3]), 0.0)

if __name__ == '__main__':
    unittest.main()
