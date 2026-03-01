import ast
with open('app.py', 'r') as f:
    text = f.read()

try:
    ast.parse(text)
    print("Parsed OK")
except SyntaxError as e:
    print(f"Error {e.msg} at line {e.lineno}, offset {e.offset}")
    print(e.text)
