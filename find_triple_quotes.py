import re
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

pos = 0
count = 0
while True:
    pos = text.find('"""', pos)
    if pos == -1:
        break
    count += 1
    lineno = text.count('\n', 0, pos) + 1
    print(f"Triple quote {count} at line {lineno}")
    pos += 3
print(f"Total: {count}")
