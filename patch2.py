with open('app.py', 'r') as f:
    text = f.read()

# Let's fix calculate_retained_earnings, it needs to be defined BEFORE it's used or at the module level.
# Python evaluates function calls dynamically so calling a module-level function defined later in the same file is fine.

# Let's make sure _safe_eval_expression is accessible. It's defined at the module level in app.py.
if '_safe_eval_expression' in text:
    print("_safe_eval_expression found.")
else:
    print("_safe_eval_expression NOT found. That's a problem.")
