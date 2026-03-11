import unittest
from benchmark_ensure_default_accounts import original_logic, optimized_logic

class MockDB:
    def __init__(self, existing):
        self.existing = set(existing)
        self.inserts = []

    def execute_query(self, query, params=None, commit=False):
        if "INSERT" in query.upper():
            self.inserts.append(params)
            return None
        elif query.startswith("SELECT id"):
            name = params[0]
            if name in self.existing:
                return [{'id': 1}]
            return []
        elif query.startswith("SELECT account_name"):
            format_strings = ','.join(['%s'] * len(params))
            return [{'account_name': name} for name in params if name in self.existing]
        return None

class TestEnsureDefaultAccounts(unittest.TestCase):
    def setUp(self):
        self.defaults = [
            ('Account Payable', 6, 'Current liabilities', None, None, 'liabilities'),
            ('Account Receivable', 3, 'Current assets', None, None, 'assets'),
            ('Cost Of Goods Sold', None, None, 2, 'Cost Of Sales', 'expenses'),
            ('Sales', None, None, 1, 'Revenue', 'income'),
            ('Inventory', 3, 'Current assets', None, None, 'assets'),
            ('VAT Control', 6, 'Current liabilities', None, None, 'liabilities'),
            ('Cash In Hand', 3, 'Current assets', None, None, 'assets')
        ]

    def test_all_missing(self):
        db_orig = MockDB([])
        db_opt = MockDB([])

        original_logic(self.defaults, db_orig)
        optimized_logic(self.defaults, db_opt)

        self.assertEqual(len(db_orig.inserts), 7)
        self.assertEqual(len(db_opt.inserts), 7)
        self.assertEqual(db_orig.inserts, db_opt.inserts)

    def test_all_existing(self):
        existing = [acc[0] for acc in self.defaults]
        db_orig = MockDB(existing)
        db_opt = MockDB(existing)

        original_logic(self.defaults, db_orig)
        optimized_logic(self.defaults, db_opt)

        self.assertEqual(len(db_orig.inserts), 0)
        self.assertEqual(len(db_opt.inserts), 0)

    def test_some_existing(self):
        existing = ['Account Payable', 'Sales', 'Cash In Hand']
        db_orig = MockDB(existing)
        db_opt = MockDB(existing)

        original_logic(self.defaults, db_orig)
        optimized_logic(self.defaults, db_opt)

        self.assertEqual(len(db_orig.inserts), 4)
        self.assertEqual(len(db_opt.inserts), 4)
        self.assertEqual(db_orig.inserts, db_opt.inserts)

if __name__ == '__main__':
    unittest.main()
