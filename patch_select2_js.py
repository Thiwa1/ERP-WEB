with open('templates/bulk_upload_tb_review.html', 'r') as f:
    content = f.read()

# We need to make sure the modal initializes select2 when it's opened to prevent duplicate rendering issues.
# Wait, base.html does this:
# $('.select2').each(function() { ... dropdownParent: dropdownParent ... })
# This works for static elements, but if they are inside a modal, sometimes it glitches if the modal is hidden during page load.
# The best way to fix select2 in Bootstrap modals is to re-initialize them when the modal is shown.

js_block = """
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
});
</script>
"""

# append to end of file before {% endblock %}
if '<script>' not in content:
    content = content.replace('{% endblock %}', js_block + '\n{% endblock %}')
    with open('templates/bulk_upload_tb_review.html', 'w') as f:
        f.write(content)
    print("Added modal select2 JS")
