with open('templates/base.html', 'r') as f:
    content = f.read()

js_logic = """
        // Quick Actions Win10 Search Filtering
        const win10SearchInput = document.getElementById('win10SearchInput');
        if (win10SearchInput) {
            win10SearchInput.addEventListener('input', function(e) {
                const term = e.target.value.toLowerCase();

                // Filter tiles and categories
                const categories = document.querySelectorAll('#win10GridContainer .win10-category');
                categories.forEach(cat => {
                    const tiles = cat.querySelectorAll('.win10-tile');
                    let hasVisible = false;
                    tiles.forEach(tile => {
                        const name = tile.getAttribute('data-name') || '';
                        if (name.includes(term)) {
                            tile.style.display = 'flex';
                            hasVisible = true;
                        } else {
                            tile.style.display = 'none';
                        }
                    });
                    cat.style.display = hasVisible ? 'block' : 'none';
                });

                // Filter recents
                const recentCat = document.getElementById('win10RecentCategory');
                if (recentCat) {
                    const recents = recentCat.querySelectorAll('.win10-recent-item');
                    let hasVisible = false;
                    recents.forEach(recent => {
                        const name = recent.getAttribute('data-name') || '';
                        if (name.includes(term)) {
                            recent.style.display = 'flex';
                            hasVisible = true;
                        } else {
                            recent.style.display = 'none';
                        }
                    });
                    recentCat.style.display = hasVisible ? 'block' : 'none';
                }
            });

            const modalEl = document.getElementById('quickActionsModal');
            if (modalEl) {
                modalEl.addEventListener('show.bs.modal', function() {
                    win10SearchInput.value = '';
                    win10SearchInput.dispatchEvent(new Event('input'));
                });
                modalEl.addEventListener('shown.bs.modal', function() {
                    win10SearchInput.focus();
                });
            }
        }
"""

if "// Quick Actions Win10 Search Filtering" not in content:
    idx = content.find("function updateGlobalCustomer()")
    if idx != -1:
        content = content[:idx] + js_logic + "\n        " + content[idx:]
        with open('templates/base.html', 'w') as f:
            f.write(content)
        print("JS Patched.")
