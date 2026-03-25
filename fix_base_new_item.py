with open('templates/base.html', 'r') as f:
    content = f.read()

# Add missing items
inventory_house_html = '''                            <a href="/inventory_locations" class="win11-app-item">
                                <div class="win11-icon-box bg-warning-light">
                                    <i class="fas fa-warehouse text-warning"></i>
                                </div>
                                <span>Inventory House</span>
                            </a>'''

create_job_html = '''                            <a href="/create_job" class="win11-app-item">
                                <div class="win11-icon-box bg-dark-light">
                                    <i class="fas fa-tools text-dark"></i>
                                </div>
                                <span>Create Job</span>
                            </a>'''

# Inject them after 'New Account'
content = content.replace('<span>New Account</span>\n                            </a>', f'<span>New Account</span>\n                            </a>\n{inventory_house_html}\n{create_job_html}')

with open('templates/base.html', 'w') as f:
    f.write(content)
