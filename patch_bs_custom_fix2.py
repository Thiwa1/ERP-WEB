import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix 1: Remove na.account_cost_of_good_solds = 1 from calculate_retained_earnings
content = content.replace(
    'WHERE (na.account_income = 1 OR na.account_expenses = 1 OR na.account_cost_of_good_solds = 1)',
    'WHERE (na.account_income = 1 OR na.account_expenses = 1)'
)

# Fix 2: Update _safe_eval_expression to handle ast.Constant
# Let's see how _safe_eval_expression is implemented in app.py
if '_safe_eval_expression' in content:
    pass
