with open('templates/base.html', 'r') as f:
    content = f.read()

if 'href="/service_entry_reversal"' not in content:
    content = content.replace(
        '<a href="/direct_payment_reversal" class="nav-link"><i class="fas fa-sync"></i> <span class="nav-text">Direct Pay Reversal</span></a>',
        '<a href="/direct_payment_reversal" class="nav-link"><i class="fas fa-sync"></i> <span class="nav-text">Direct Pay Reversal</span></a>\n                <a href="/service_entry_reversal" class="nav-link"><i class="fas fa-file-invoice"></i> <span class="nav-text">SRN Reversal</span></a>'
    )
    with open('templates/base.html', 'w') as f:
        f.write(content)
