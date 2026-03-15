import re

# Add select2 to account_type and cf_category
def add_select2(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Re-add select2 class
    content = content.replace(
        'class="form-select form-select-sm" name="account_type[]"',
        'class="form-select form-select-sm select2" name="account_type[]" style="width: 100%;"'
    )
    content = content.replace(
        'class="form-select form-select-sm" name="cf_category[]"',
        'class="form-select form-select-sm select2" name="cf_category[]" style="width: 100%;"'
    )

    # Note: On GL Upload review page, account_type[] has onchange="updateRowColor(this)"
    content = content.replace(
        'class="form-select form-select-sm" name="account_type[]" onchange="updateRowColor(this)"',
        'class="form-select form-select-sm select2" name="account_type[]" onchange="updateRowColor(this)" style="width: 100%;"'
    )

    with open(filepath, 'w') as f:
        f.write(content)

add_select2('templates/bulk_upload_tb_review.html')
add_select2('templates/bulk_upload_review.html')

print("Added select2 class and style width 100% to dropdowns")
