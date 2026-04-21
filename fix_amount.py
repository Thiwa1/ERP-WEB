with open('templates/customer_receipt.html', 'r') as f:
    code = f.read()

# Replace hardcoded $ with {{ company_currency }}
search = """<div class="mb-1"><span class="fw-bold">Amount:</span> $<span id="revAmount"></span></div>"""
replace = """<div class="mb-1"><span class="fw-bold">Amount:</span> {{ company_currency }} <span id="revAmount"></span></div>"""

code = code.replace(search, replace)

with open('templates/customer_receipt.html', 'w') as f:
    f.write(code)
print("Amount symbol fixed in modal.")
