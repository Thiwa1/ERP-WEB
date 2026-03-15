import re

files = ['templates/bulk_upload_tb_review.html', 'templates/bulk_upload_review.html']

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()

    # Remove 'required' from select tags
    # <select class="select2" name="account_type[]" style="width: 100%;" required>
    content = content.replace('required>', '>')
    content = content.replace(' required>', '>')
    content = content.replace('required >', '>')

    with open(filepath, 'w') as f:
        f.write(content)

print("Removed required attributes")
