import re

with open('templates/bulk_upload_tb_review.html', 'r') as f:
    content = f.read()

# Add Action column to header
content = content.replace(
    '<th>Cash Flow</th>\n                                </tr>',
    '<th>Cash Flow</th>\n                                    <th>Action</th>\n                                </tr>'
)

# Remove the hidden action input and add it as a TD
hidden_action = '<input type="hidden" name="action[]" value="save">'
content = content.replace(hidden_action, '')

select_action = """
                                    <td>
                                        <select class="form-select form-select-sm" name="action[]">
                                            <option value="save">Save</option>
                                            <option value="skip">Skip</option>
                                        </select>
                                    </td>
                                </tr>
"""

content = content.replace(
    '                                    </td>\n                                </tr>\n                                {% endfor %}',
    '                                    </td>' + select_action + '                                {% endfor %}'
)

# Add select2 to Type
content = content.replace(
    '<select class="form-select form-select-sm" name="account_type[]" required>',
    '<select class="form-select form-select-sm select2" name="account_type[]" required>'
)

# Add select2 to CF Category
content = content.replace(
    '<select class="form-select form-select-sm" name="cf_category[]">',
    '<select class="form-select form-select-sm select2" name="cf_category[]">'
)

with open('templates/bulk_upload_tb_review.html', 'w') as f:
    f.write(content)
