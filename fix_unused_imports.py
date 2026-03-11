import os

def fix_unused_date_import_in_vat_helper():
    """
    Automates the removal of the unused 'from datetime import date' import
    from vat_helper.py.
    """
    filepath = os.path.join(os.path.dirname(__file__), 'vat_helper.py')

    if not os.path.exists(filepath):
        print("vat_helper.py not found.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    removed = False

    for line in lines:
        if line.strip() == 'from datetime import date':
            removed = True
            continue # Skip this unused import
        fixed_lines.append(line)

    if removed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print("Successfully removed unused import 'date' from vat_helper.py.")
    else:
        print("No unused import 'date' found in vat_helper.py.")

if __name__ == '__main__':
    fix_unused_date_import_in_vat_helper()
