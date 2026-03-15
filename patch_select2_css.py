import re

with open('templates/bulk_upload_tb_review.html', 'r') as f:
    content = f.read()

# Select2 needs specific handling in Bootstrap tables to prevent width collapse
content = content.replace(
    'class="form-select form-select-sm select2"',
    'class="select2"'
)

with open('templates/bulk_upload_tb_review.html', 'w') as f:
    f.write(content)

with open('templates/bulk_upload_review.html', 'r') as f:
    content = f.read()

content = content.replace(
    'class="form-select form-select-sm select2"',
    'class="select2"'
)

with open('templates/bulk_upload_review.html', 'w') as f:
    f.write(content)
