import re
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Find the unclosed triple quote that causes the error at the EOF.
# We will just append a """ at the end of the file if needed, or fix the last one.
# Wait, let's just use ast to find the line.

import ast
try:
    ast.parse(text)
    print("Syntax is fine.")
except SyntaxError as e:
    print(f"Error at line {e.lineno}, offset {e.offset}: {e.msg}")
