from flask import Flask, render_template

app = Flask(__name__)

@app.context_processor
def inject_theme():
    return dict(current_theme={'primary': '#0d6efd', 'secondary': '#6c757d', 'background': '#f8f9fa'}, session={'user_name': 'Mock Admin', 'is_superadmin': False})

@app.route('/service_entry')
def service_entry():
    return render_template('service_entry.html',
                           suppliers=[{'sup_id': 1, 'supplier_name': 'Test Supplier', 'supplier_code': 'SUP001'}],
                           accounts=[{'account_name': 'Test Expense Account'}],
                           sub_accounts=[{'sub_account_code': 'SUB001', 'sub_sub_accaount_name': 'Test Sub'}],
                           jobs=[{'job_number': 'JOB001'}],
                           today_date='2026-04-29')

@app.route('/service_entry/save', methods=['POST'])
def save_service_entry():
    return "saved"

@app.route('/service_entry_reversal')
def service_entry_reversal():
    return render_template('service_entry_reversal.html',
                           rows=[{
                               'jv': 100,
                               'jv_user_code': 'JV FORM SEN INVOICE',
                               'SupplierName': 'Test Supplier',
                               'InvoiceNo': 'INV-100',
                               'Date': '2026-04-29',
                               'Amount': 1000.00
                           }])

@app.route('/service_entry_reversal/process', methods=['POST'])
def service_entry_reversal_process():
    return "reversed"

if __name__ == '__main__':
    app.run(port=5001)
