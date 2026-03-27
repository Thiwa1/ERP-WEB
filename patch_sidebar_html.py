import re

with open("templates/base.html", "r") as f:
    content = f.read()

# Add the sidebar collapse toggle button inside sidebar-header
collapse_btn_html = """        <div class="sidebar-collapse-btn" id="win11SidebarToggle">
            <i class="fas fa-chevron-left"></i>
        </div>
"""

content = re.sub(
    r'(<div class="sidebar-header">)',
    r'\1\n' + collapse_btn_html,
    content
)

# Wrap text in .sidebar-brand
content = re.sub(
    r'(<a href="/" class="sidebar-brand">)\s*<i class="fas fa-chart-line"></i>\s*SUWIN ERP',
    r'\1\n                <i class="fas fa-chart-line"></i>\n                <span class="nav-text">SUWIN ERP</span>',
    content
)

# Wrap text in .nav-link
# This matches lines like: <a href="/something" class="nav-link"><i class="fas fa-icon"></i> Text Here</a>
# and turns them into: <a href="/something" class="nav-link"><i class="fas fa-icon"></i> <span class="nav-text">Text Here</span></a>
content = re.sub(
    r'(<a[^>]*class="nav-link[^>]*>.*?<i[^>]*></i>)\s*([^<]+)</a>',
    r'\1 <span class="nav-text">\2</span></a>',
    content
)

# Wrap text in btn-add-new-pro
content = re.sub(
    r'(<button class="btn-add-new-pro".*?>\s*<i class="fas fa-plus"></i>)\s*NEW ITEM\s*</button>',
    r'\1 <span class="nav-text">NEW ITEM</span>\n                </button>',
    content
)

with open("templates/base.html", "w") as f:
    f.write(content)
