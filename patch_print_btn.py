with open('templates/service_entry_reversal.html', 'r') as f:
    content = f.read()

# Add a Print button next to the Reverse button
if 'fa-print' not in content:
    content = content.replace(
        '<button type="submit" class="btn btn-sm btn-outline-danger">',
        '<a href="/service_entry/print/{{ row.jv }}" class="btn btn-sm btn-outline-primary me-1" target="_blank"><i class="fas fa-print"></i> Print</a>\n                                            <button type="submit" class="btn btn-sm btn-outline-danger">'
    )
    with open('templates/service_entry_reversal.html', 'w') as f:
        f.write(content)
