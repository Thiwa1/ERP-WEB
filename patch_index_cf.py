with open('templates/index.html', 'r') as f:
    content = f.read()

new_cf_card = """                <div class="col">
                    <a href="/cash_flow" class="tile-link">
                        <div class="tile">
                            <i class="fas fa-money-bill-wave"></i>
                            <span>Cash<br>Flow</span>
                        </div>
                    </a>
                </div>
"""

pieces = content.split('href="/balance_sheet_custom"')
if len(pieces) > 1:
    part2 = pieces[1]
    end_col_idx = part2.find('</div>\n                </div>\n') + len('</div>\n                </div>\n')
    new_content = pieces[0] + 'href="/balance_sheet_custom"' + part2[:end_col_idx] + new_cf_card + part2[end_col_idx:]
    with open('templates/index.html', 'w') as f:
        f.write(new_content)
    print("Patched index.html with Cash Flow")
else:
    print("Could not find balance_sheet_custom")
