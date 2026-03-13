import sys
import glob

with open("tests/test_balance_sheet.py", "r") as f:
    content = f.read()

content = "import tests.mock_env\n" + content
with open("tests/test_balance_sheet.py", "w") as f:
    f.write(content)
