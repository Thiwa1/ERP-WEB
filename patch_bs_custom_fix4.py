import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix 2: Update safe_eval_math to handle ast.Constant (for Python 3.8+)
old_eval = """
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(f"Unsupported mathematical operation: {node}")
"""

new_eval = """
    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError("Only numbers are allowed")
        elif getattr(ast, 'Num', None) and isinstance(node, getattr(ast, 'Num')):
            return node.n
        elif isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(f"Unsupported mathematical operation: {node}")
"""

content = content.replace(old_eval, new_eval)

with open('app.py', 'w') as f:
    f.write(content)
