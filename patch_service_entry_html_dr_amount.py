with open('templates/service_entry.html', 'r') as f:
    content = f.read()

# Make the DR amount column even wider and remove 'text-end' if that's causing issues.
# Wait, let's change width to 20% and Narration to 15%
content = content.replace('<th style="width: 15%" class="text-end">DR Amount</th>', '<th style="width: 20%" class="text-end">DR Amount</th>')
content = content.replace('<th style="width: 20%">Narration</th>', '<th style="width: 15%">Narration</th>')

# Also, the input type="number" has arrows. We can hide the spin buttons with CSS if needed,
# or just ensure the width is sufficient.
# Let's add a style block to hide the spin buttons to avoid squishing.
style_block = """
    <style>
        /* Hide number input spin buttons */
        input[type="number"]::-webkit-outer-spin-button,
        input[type="number"]::-webkit-inner-spin-button {
            -webkit-appearance: none;
            margin: 0;
        }
        input[type="number"] {
            -moz-appearance: textfield;
        }
    </style>
"""

content = content.replace('{% block content %}', '{% block content %}\n' + style_block)

with open('templates/service_entry.html', 'w') as f:
    f.write(content)
