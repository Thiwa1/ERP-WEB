import re

with open("templates/base.html", "r") as f:
    content = f.read()

js_to_add = """
        // Win11 Desktop Sidebar Collapse
        const win11SidebarToggle = document.getElementById('win11SidebarToggle');
        if (win11SidebarToggle) {
            win11SidebarToggle.addEventListener('click', function(e) {
                e.preventDefault();
                document.body.classList.toggle('sidebar-collapsed');
                if(document.body.classList.contains('sidebar-collapsed')) {
                    localStorage.setItem('sidebarCollapsed', 'true');
                } else {
                    localStorage.setItem('sidebarCollapsed', 'false');
                }
            });

            // Apply saved state
            if(localStorage.getItem('sidebarCollapsed') === 'true') {
                document.body.classList.add('sidebar-collapsed');
            }
        }
"""

content = content.replace("// Sidebar Toggle Script for Mobile", js_to_add + "\n        // Sidebar Toggle Script for Mobile")

with open("templates/base.html", "w") as f:
    f.write(content)
