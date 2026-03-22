import sys
import os
import unittest

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import knowledge_base

class TestKnowledgeBase(unittest.TestCase):
    def test_account_types_exists_and_is_dict(self):
        """Test that account_types exists in knowledge_base and is a dictionary"""
        self.assertTrue(hasattr(knowledge_base, 'account_types'))
        self.assertIsInstance(knowledge_base.account_types, dict)

    def test_common_accounts_present(self):
        """Test that common accounts are present in account_types"""
        common_accounts = [
            'Cash',
            'Savings account',
            'Petty cash balance',
            'Accounts receivable',
            'Accounts payable',
            'Sales Revenue',
            'Retained earnings'
        ]
        for account in common_accounts:
            self.assertIn(account, knowledge_base.account_types)

    def test_account_mappings_are_correct(self):
        """Test that common accounts are mapped to correct types"""
        expected_mappings = {
            'Cash': 'Assets Account',
            'Savings account': 'Assets Account',
            'Accounts payable': 'Liabilities Account',
            'Sales Revenue': 'Income Account',
            'Basic salary': 'Cost Account',
            'Retained earnings': 'Equity Accont', # note the typo in the actual file
            'Land': 'Fixed Asset'
        }
        for account, expected_type in expected_mappings.items():
            self.assertEqual(knowledge_base.account_types[account], expected_type)

    def test_all_keys_and_values_are_strings(self):
        """Test that all keys and values in account_types are strings"""
        for key, value in knowledge_base.account_types.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

if __name__ == '__main__':
    unittest.main()
