import tests.mock_env
# Add mock setup first
from tests import mock_setup
import unittest
from app import parse_float

class TestCSVFormatting(unittest.TestCase):
    def test_parse_float_basics(self):
        self.assertEqual(parse_float("123.45"), 123.45)
        self.assertEqual(parse_float(100), 100.0)
        self.assertEqual(parse_float(None), 0.0)
        self.assertEqual(parse_float(""), 0.0)

    def test_parse_float_formatting(self):
        self.assertEqual(parse_float("1,234.56"), 1234.56)
        self.assertEqual(parse_float(" 12,345.67 "), 12345.67)
        self.assertEqual(parse_float("1,234,567.89"), 1234567.89)

    def test_parse_float_invalid(self):
        self.assertEqual(parse_float("invalid"), 0.0)
        self.assertEqual(parse_float("12.34.56"), 0.0)

    def test_parse_float_errors(self):
        # Pass a dictionary which should raise TypeError
        self.assertEqual(parse_float({"key": "value"}), 0.0)
        # Pass a list which should raise TypeError
        self.assertEqual(parse_float([1, 2, 3]), 0.0)
        # Pass a complex number which raises TypeError when passed to float()
        self.assertEqual(parse_float(complex(1, 2)), 0.0)

if __name__ == '__main__':
    unittest.main()
