import sys
with open("tests/test_balance_sheet.py", "r") as f:
    content = f.read()

# Update the test to match the new query logic for retained earnings
target = """        def side_effect(query, params=None):
            q = " ".join(query.split())
            if "account_assets = 1" in q: return assets_data
            if "account_liabilities = 1" in q: return liabilities_data
            if "account_equity = 1" in q: return equity_data
            if "account_income = 1" in q: return income_data
            if "account_expenses = 1" in q: return expense_data
            return []"""

replacement = """        def side_effect(query, params=None):
            q = " ".join(query.split())
            if "account_assets = 1" in q: return assets_data
            if "account_liabilities = 1" in q: return liabilities_data
            if "account_equity = 1" in q: return equity_data
            if "na.account_income = 1 OR na.account_expenses = 1" in q:
                return [
                    {'account_income': 1, 'account_expenses': 0, 'account_basment': 'CR', 'total_cr': 500, 'total_dr': 0},
                    {'account_income': 0, 'account_expenses': 1, 'account_basment': 'DR', 'total_cr': 0, 'total_dr': 200}
                ]
            if "account_income = 1" in q: return income_data
            if "account_expenses = 1" in q: return expense_data
            return []"""

content = content.replace(target, replacement)

with open("tests/test_balance_sheet.py", "w") as f:
    f.write(content)
