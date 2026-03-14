import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix 1: Remove na.account_cost_of_good_solds = 1 from calculate_retained_earnings
content = content.replace(
    'WHERE (na.account_income = 1 OR na.account_expenses = 1 OR na.account_cost_of_good_solds = 1)',
    'WHERE (na.account_income = 1 OR na.account_expenses = 1)'
)

with open('app.py', 'w') as f:
    f.write(content)
