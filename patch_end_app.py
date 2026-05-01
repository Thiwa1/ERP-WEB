with open('app.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "if __name__ == '__main__':":
        break
    new_lines.append(line)

new_lines.extend([
    "if __name__ == '__main__':\n",
    "    app.run(port=5000)\n"
])

with open('app.py', 'w') as f:
    f.writelines(new_lines)
