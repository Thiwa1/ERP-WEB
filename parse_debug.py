import ast
import io

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
for j in range(8600, len(lines)):
    block = "\n".join(lines[:j])
    try:
        ast.parse(block)
    except SyntaxError as e:
        if "invalid syntax" in e.msg and "EOF" not in e.msg:
            print(f"Invalid syntax at j={j} ({e.lineno})")
            break
