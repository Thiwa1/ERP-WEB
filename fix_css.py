with open('templates/customer_receipt.html', 'r') as f:
    code = f.read()

# Add scroll view to OUTSTANDING INVOICES table
if '<div class="table-responsive">' not in code:
    print("Trying to add table responsive")

# Let's just wrap the invoiceTable in a div with max-height
search = """                        <table class="table table-hover table-sm align-middle" id="invoiceTable">"""
replace = """                    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                        <table class="table table-hover table-sm align-middle" id="invoiceTable">"""

code = code.replace(search, replace)

search2 = """                        </table>"""
replace2 = """                        </table>
                    </div>"""

code = code.replace(search2, replace2, 1)

with open('templates/customer_receipt.html', 'w') as f:
    f.write(code)
print("CSS Patched.")
