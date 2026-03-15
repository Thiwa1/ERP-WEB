with open('templates/bulk_upload_review.html', 'r') as f:
    content = f.read()

content = content.replace(
    '<select class="form-select form-select-sm" name="account_type[]" onchange="updateRowColor(this)">',
    '<select class="form-select form-select-sm select2" name="account_type[]" onchange="updateRowColor(this)">'
)

content = content.replace(
    '<select class="form-select form-select-sm" name="cf_category[]">',
    '<select class="form-select form-select-sm select2" name="cf_category[]">'
)

with open('templates/bulk_upload_review.html', 'w') as f:
    f.write(content)
