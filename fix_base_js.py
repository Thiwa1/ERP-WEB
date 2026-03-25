import re

with open('templates/base.html', 'r') as f:
    content = f.read()

js_to_add = '''
            // Windows 11 Modal Search Functionality
            const qaSearch = document.getElementById('qaSearch');
            if (qaSearch) {
                qaSearch.addEventListener('input', function(e) {
                    const term = e.target.value.toLowerCase();
                    const apps = document.querySelectorAll('.win11-app-item, .win11-list-item');

                    apps.forEach(app => {
                        const text = app.textContent.toLowerCase();
                        if (text.includes(term)) {
                            app.style.display = '';
                        } else {
                            app.style.display = 'none';
                        }
                    });
                });

                // Auto-focus search when modal opens
                const quickActionsModal = document.getElementById('quickActionsModal');
                quickActionsModal.addEventListener('shown.bs.modal', function () {
                    qaSearch.focus();
                });

                // Clear search when modal closes
                quickActionsModal.addEventListener('hidden.bs.modal', function () {
                    qaSearch.value = '';
                    const apps = document.querySelectorAll('.win11-app-item, .win11-list-item');
                    apps.forEach(app => app.style.display = '');
                });
            }
'''

content = content.replace('        });\n    </script>\n</body>', js_to_add + '\n        });\n    </script>\n</body>')

with open('templates/base.html', 'w') as f:
    f.write(content)
