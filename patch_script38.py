with open("app.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def extract_vat_from_pdf():" in line:
        start_idx = i
        break

for i in range(start_idx, start_idx + 40):
    print(lines[i].rstrip())
