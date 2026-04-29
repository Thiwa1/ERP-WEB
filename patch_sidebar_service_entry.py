with open('templates/base.html', 'r') as f:
    content = f.read()

if 'href="/service_entry"' not in content:
    content = content.replace(
        '<a href="/journal_entry" class="nav-link"><i class="fas fa-book"></i> <span class="nav-text">Journal Entry</span></a>',
        '<a href="/journal_entry" class="nav-link"><i class="fas fa-book"></i> <span class="nav-text">Journal Entry</span></a>\n                <a href="/service_entry" class="nav-link"><i class="fas fa-file-invoice"></i> <span class="nav-text">Service Entry (SRN)</span></a>'
    )
    with open('templates/base.html', 'w') as f:
        f.write(content)
