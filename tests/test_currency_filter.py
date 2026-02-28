import unittest
from jinja2 import Environment, pass_context

# Mock the filter logic to test independently before applying to app.py
@pass_context
def currency_filter(context, value, symbol=True):
    try:
        if value is None:
            value = 0

        # Parse float safely
        if isinstance(value, str):
            value = value.replace(',', '').strip()
            if not value: value = 0

        float_val = float(value)
        formatted = "{:,.2f}".format(float_val)

        if not symbol:
            return formatted

        # Get symbol from context
        curr_symbol = context.get('company_currency', '')
        if curr_symbol:
            return f"{curr_symbol} {formatted}"
        return formatted

    except (ValueError, TypeError):
        return "0.00"

class TestCurrencyFilter(unittest.TestCase):
    def setUp(self):
        self.env = Environment()
        self.env.filters['currency'] = currency_filter

    def test_with_symbol_in_context(self):
        context = {'company_currency': 'LKR'}
        template = self.env.from_string("{{ 1234.56 | currency }}")
        result = template.render(context)
        self.assertEqual(result, "LKR 1,234.56")

    def test_different_symbol(self):
        context = {'company_currency': 'USD'}
        template = self.env.from_string("{{ 1234.56 | currency }}")
        result = template.render(context)
        self.assertEqual(result, "USD 1,234.56")

    def test_no_symbol_in_context(self):
        context = {}
        template = self.env.from_string("{{ 1234.56 | currency }}")
        result = template.render(context)
        self.assertEqual(result, "1,234.56")

    def test_suppress_symbol(self):
        context = {'company_currency': 'LKR'}
        template = self.env.from_string("{{ 1234.56 | currency(symbol=False) }}")
        result = template.render(context)
        self.assertEqual(result, "1,234.56")

    def test_none_value(self):
        context = {'company_currency': 'LKR'}
        template = self.env.from_string("{{ None | currency }}")
        result = template.render(context)
        self.assertEqual(result, "LKR 0.00")

    def test_string_number(self):
        context = {'company_currency': 'LKR'}
        template = self.env.from_string("{{ '5000' | currency }}")
        result = template.render(context)
        self.assertEqual(result, "LKR 5,000.00")

    def test_invalid_value(self):
        context = {'company_currency': 'LKR'}
        template = self.env.from_string("{{ 'abc' | currency }}")
        result = template.render(context)
        self.assertEqual(result, "0.00")

if __name__ == '__main__':
    unittest.main()
