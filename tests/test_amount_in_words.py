import sys
import unittest
from unittest.mock import MagicMock

# Import the real num2words before mock_env to ensure it's not mocked
import num2words

import tests.mock_env

# Even if tests.mock_env tries to mock it, it checks `if 'num2words' not in sys.modules`.
# Since we imported it first, it won't mock it!

import app

class TestAmountInWords(unittest.TestCase):
    def test_zero_amount(self):
        self.assertEqual(app.amount_in_words(0), "Zero Rupees Only")
        self.assertEqual(app.amount_in_words("0"), "Zero Rupees Only")
        self.assertEqual(app.amount_in_words(0.0), "Zero Rupees Only")

    def test_normal_amount(self):
        # 123.45 should be: one hundred and twenty-three Rupees, forty-five Cents (Title Case)
        # Without title() it's "one hundred and twenty-three dollars, forty-five cents"
        # So it should become "One Hundred And Twenty-Three Rupees, Forty-Five Cents"
        result = app.amount_in_words(123.45)
        self.assertIn("Rupees", result)
        self.assertIn("Cents", result)
        self.assertNotIn("Dollars", result, "Should not contain 'Dollars'")
        self.assertNotIn("Cents", result.replace("Cents", "")) # checking it replaced correctly

        # Let's check exactly what is outputted by num2words in Title Case
        expected = num2words.num2words(123.45, to='currency', currency='USD', lang='en')
        expected = expected.replace('dollars', 'Rupees').replace('dollar', 'Rupee')
        expected = expected.replace('cents', 'Cents').replace('cent', 'Cent')
        expected = expected.title()

        self.assertEqual(result, expected)

    def test_singular_amount(self):
        # 1.01 -> One Rupee, One Cent
        result = app.amount_in_words(1.01)
        expected = num2words.num2words(1.01, to='currency', currency='USD', lang='en')
        expected = expected.replace('dollars', 'Rupees').replace('dollar', 'Rupee')
        expected = expected.replace('cents', 'Cents').replace('cent', 'Cent')
        expected = expected.title()
        self.assertEqual(result, expected)
        self.assertIn("One Rupee, One Cent", result)

    def test_invalid_input(self):
        # Should throw an error and be caught
        result = app.amount_in_words("invalid_string")
        self.assertTrue(result.startswith("Error converting amount:"))

    def test_negative_input(self):
        # Handle negative inputs if necessary, though num2words might just say "minus"
        result = app.amount_in_words(-50.25)
        expected = num2words.num2words(-50.25, to='currency', currency='USD', lang='en')
        expected = expected.replace('dollars', 'Rupees').replace('dollar', 'Rupee')
        expected = expected.replace('cents', 'Cents').replace('cent', 'Cent')
        expected = expected.title()
        self.assertEqual(result, expected)
        self.assertIn("Minus", result)

if __name__ == '__main__':
    unittest.main()
