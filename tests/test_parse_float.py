import unittest
from unittest.mock import MagicMock
import sys
import os

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock missing modules
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Mock database module since it imports mysql.connector
sys.modules['database'] = MagicMock()

# Mock environment variables to avoid key error if app tries to read them
os.environ['SECRET_KEY'] = 'test_key'
os.environ['DB_USER'] = 'test_user'
os.environ['DB_PASSWORD'] = 'test_pass'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'test_db'

# Import the function to test
try:
    from app import parse_float
except ImportError:
    import app
    parse_float = app.parse_float

class TestParseFloat(unittest.TestCase):

    def test_integers(self):
        """Test integer inputs convert to float."""
        self.assertEqual(parse_float(100), 100.0)
        self.assertEqual(parse_float(0), 0.0)
        self.assertEqual(parse_float(-50), -50.0)

    def test_floats(self):
        """Test float inputs are returned as is."""
        self.assertEqual(parse_float(100.5), 100.5)
        self.assertEqual(parse_float(0.0), 0.0)
        self.assertEqual(parse_float(-50.25), -50.25)

    def test_strings_simple(self):
        """Test simple numeric strings."""
        self.assertEqual(parse_float("100.5"), 100.5)
        self.assertEqual(parse_float("0"), 0.0)
        self.assertEqual(parse_float("-50.25"), -50.25)

    def test_strings_with_commas(self):
        """Test strings with commas are handled correctly."""
        self.assertEqual(parse_float("1,000.50"), 1000.5)
        self.assertEqual(parse_float("1,234,567.89"), 1234567.89)

    def test_none(self):
        """Test None input returns 0.0."""
        self.assertEqual(parse_float(None), 0.0)

    def test_empty_strings(self):
        """Test empty or whitespace-only strings return 0.0."""
        self.assertEqual(parse_float(""), 0.0)
        self.assertEqual(parse_float("   "), 0.0)

    def test_invalid_strings(self):
        """Test non-numeric strings return 0.0."""
        self.assertEqual(parse_float("abc"), 0.0)
        self.assertEqual(parse_float("12.34.56"), 0.0) # Invalid float format

    def test_whitespace_handling(self):
        """Test strings with leading/trailing whitespace."""
        self.assertEqual(parse_float(" 123.45 "), 123.45)

    def test_mixed_invalid(self):
        """Test strings that look like numbers but are invalid."""
        # 12,34,56 -> 123456 (valid if commas removed)
        self.assertEqual(parse_float("12,34,56"), 123456.0)
        # $100 -> 0.0 (ValueError)
        self.assertEqual(parse_float("$100"), 0.0)

if __name__ == '__main__':
    unittest.main()
