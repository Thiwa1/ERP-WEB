import unittest
import sys
from unittest.mock import MagicMock

# Mock dependencies before importing app
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

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

if __name__ == '__main__':
    unittest.main()
