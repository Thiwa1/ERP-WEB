import re

with open('templates/bulk_upload_tb_review.html', 'r') as f:
    content = f.read()

# Replace document.addEventListener('DOMContentLoaded' ... with simpler code
new_script = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    var myModalEl = document.getElementById('createMissingModal');
    if(myModalEl) {
        myModalEl.addEventListener('shown.bs.modal', function (event) {
            $(this).find('.select2').select2({
                theme: 'bootstrap-5',
                width: '100%',
                dropdownParent: $('#createMissingModal')
            });
        });
    }

    var quickCreateForm = document.getElementById('quickCreateForm');
    if(quickCreateForm) {
        quickCreateForm.addEventListener('submit', function(e) {
            var actions = document.getElementsByName('action[]');
            var categories = document.getElementsByName('category[]');
            var types = document.getElementsByName('account_type[]');

            for(var i=0; i<actions.length; i++) {
                if(actions[i].value === 'save') {
                    if(!categories[i].value || !types[i].value) {
                        alert('Please select both Type and Category for all accounts marked to be saved.');
                        e.preventDefault();
                        if(!types[i].value) {
                            $(types[i]).select2('open');
                        } else {
                            $(categories[i]).select2('open');
                        }
                        return;
                    }
                }
            }
        });
    }
});
</script>
"""

# Find the script tag and replace it
content = re.sub(r'<!-- Modal for Quick Create -->\n<script>.*?</script>', new_script, content, flags=re.DOTALL)

# Handle cases where the comment is missing
if '<script>' in content:
    content = re.sub(r'<script>.*?</script>\s*$', new_script, content, flags=re.DOTALL)

with open('templates/bulk_upload_tb_review.html', 'w') as f:
    f.write(content)

print("Updated script in bulk_upload_tb_review.html")
