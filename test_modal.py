import re

with open('templates/base.html', 'r') as f:
    content = f.read()

# Wait, why are there two modals? Did I fail to replace the original?
print(content.count('id="quickActionsModal"'))
