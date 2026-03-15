import re

with open('templates/bulk_upload_tb_review.html', 'r') as f:
    content = f.read()

# Add a script that disables the 'required' check if action is 'skip'
script = """
<!-- Modal for Quick Create -->
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
            var hasError = false;

            for(var i=0; i<actions.length; i++) {
                if(actions[i].value === 'save') {
                    if(!categories[i].value) {
                        alert('Please select a Category for the row to be saved.');
                        $(categories[i]).select2('open');
                        hasError = true;
                        e.preventDefault();
                        break;
                    }
                }
            }
        });
    }
});
</script>
"""

content = re.sub(r'<!-- Modal for Quick Create -->\s*<script>.*?</script>', script, content, flags=re.DOTALL)

with open('templates/bulk_upload_tb_review.html', 'w') as f:
    f.write(content)

print("Patched bulk_upload_tb_review.html")
