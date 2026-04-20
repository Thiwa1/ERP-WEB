with open('app.py', 'r') as f:
    code = f.read()

import re

match = re.search(r"@app\.route\('/customer_receipt/get_history'\)\n@login_required\ndef get_customer_receipt_history\(\):(.*?)\n@app\.route\('/receipt/print/<int:jv_no>'\)", code, flags=re.DOTALL)
if match:
    body = match.group(1)
    if "cursor = db.get_connection().cursor()" in body:
        new_body = body.replace("cursor = db.get_connection().cursor()", """conn = db.get_connection()
    if not conn: return {'error': '2055: Cursor is not connected'}, 500
    cursor = conn.cursor()""")
        code = code[:match.start()] + "@app.route('/customer_receipt/get_history')\n@login_required\ndef get_customer_receipt_history():" + new_body + "\n@app.route('/receipt/print/<int:jv_no>')" + code[match.end():]

        with open('app.py', 'w') as f:
            f.write(code)
        print("Patched.")
    else:
        print("Cursor not found directly")
else:
    print("Match failed")
