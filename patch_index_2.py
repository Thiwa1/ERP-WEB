with open('templates/index.html', 'r') as f:
    content = f.read()

new_bs_card = """                <div class="col">
                    <a href="/balance_sheet_custom" class="tile-link">
                        <div class="tile">
                            <i class="fas fa-file-invoice-dollar"></i>
                            <span>Custom<br>Bal Sheet</span>
                        </div>
                    </a>
                </div>
"""

# Find balance_sheet
pieces = content.split('href="/balance_sheet"')
if len(pieces) > 1:
    part2 = pieces[1]
    end_col_idx = part2.find('</div>\n                </div>\n') + len('</div>\n                </div>\n')
    new_content = pieces[0] + 'href="/balance_sheet"' + part2[:end_col_idx] + new_bs_card + part2[end_col_idx:]
    with open('templates/index.html', 'w') as f:
        f.write(new_content)
    print("Patched index.html after Balance Sheet")
else:
    print("Could not find balance_sheet")
