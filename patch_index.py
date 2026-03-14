import re

with open('templates/index.html', 'r') as f:
    content = f.read()

new_bs_card = """
                    <div class="col">
                        <a href="{{ url_for('balance_sheet_custom') }}" class="text-decoration-none">
                            <div class="card h-100 tile-card text-center text-white border-0 shadow-sm" style="background: rgba(43, 91, 128, 0.75);">
                                <div class="card-body py-4 d-flex flex-column align-items-center justify-content-center">
                                    <i class="fas fa-file-invoice-dollar fa-3x mb-3 tile-icon"></i>
                                    <h5 class="card-title fw-bold mb-1">Custom BS Format</h5>
                                    <p class="card-text small opacity-75">Design custom balance sheet reports</p>
                                </div>
                            </div>
                        </a>
                    </div>
"""

# Let's insert it after Custom PL Format or Balance Sheet Category
if 'profit_loss_custom' in content:
    content = content.replace('profit_loss_custom', 'profit_loss_custom') # Just a dummy to check

    # insert after the PL custom card
    pieces = content.split('url_for(\'profit_loss_custom\')')
    if len(pieces) > 1:
        # find the end of that col div
        part2 = pieces[1]
        end_col_idx = part2.find('</div>\n                    </div>') + len('</div>\n                    </div>')

        new_content = pieces[0] + 'url_for(\'profit_loss_custom\')' + part2[:end_col_idx] + new_bs_card + part2[end_col_idx:]
        with open('templates/index.html', 'w') as f:
            f.write(new_content)
        print("Patched index.html near profit_loss_custom")
else:
    # Just append it at the end of the Dashboard container, before the script
    # Or in the Reports grid if we find it
    pieces = content.split('<!-- Analytics & Reports -->')
    if len(pieces) > 1:
        # insert into the Analytics & Reports section
        part2 = pieces[1]
        row_start_idx = part2.find('<div class="row row-cols-1 row-cols-md-3 row-cols-lg-4 g-4 mt-2">') + len('<div class="row row-cols-1 row-cols-md-3 row-cols-lg-4 g-4 mt-2">')
        new_content = pieces[0] + '<!-- Analytics & Reports -->' + part2[:row_start_idx] + new_bs_card + part2[row_start_idx:]
        with open('templates/index.html', 'w') as f:
            f.write(new_content)
        print("Patched index.html in Analytics & Reports section")
    else:
        print("Could not find a good place to insert Custom BS")
