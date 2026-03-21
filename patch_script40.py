with open("app.py", "r") as f:
    lines = f.readlines()

new_code = """@app.route('/pos_login', methods=['GET', 'POST'])
def pos_web_login():
"""

for i, line in enumerate(lines):
    if "def pos_web_login():" in line:
        start_idx = i
        break

with open("app.py", "w") as f:
    f.writelines(lines[:start_idx] + [new_code] + lines[start_idx+1:])
