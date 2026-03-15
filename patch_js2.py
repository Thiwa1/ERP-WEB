import re

with open('templates/bulk_upload_review.html', 'r') as f:
    content = f.read()

script = """
<script>
    function updateRowColor(select) {
        const row = select.closest('tr');
        const type = select.value;
        // Optional: Change visual cues based on type if needed
        // e.g., if (type === 'Income' || type === 'Expense') row.classList.add('table-info');
    }

    document.addEventListener('DOMContentLoaded', function() {
        var form = document.querySelector('form');
        if(form) {
            form.addEventListener('submit', function(e) {
                var actions = document.getElementsByName('action[]');
                var categories = document.getElementsByName('category[]');

                for(var i=0; i<actions.length; i++) {
                    if(actions[i].value === 'save') {
                        if(!categories[i].value) {
                            alert('Please select a Category for all rows marked to be saved.');
                            e.preventDefault();
                            $(categories[i]).select2('open');
                            return;
                        }
                    }
                }
            });
        }
    });
</script>
"""

content = re.sub(r'<script>.*?</script>', script, content, flags=re.DOTALL)

with open('templates/bulk_upload_review.html', 'w') as f:
    f.write(content)

print("Patched bulk_upload_review.html")
