import re

with open('app.py', 'r') as f:
    content = f.read()

# Make sure we catch FileNotFoundError in subprocess call
old_try = '''        # Execute
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)'''

new_try = '''        # Execute
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            flash(f"Backup tool '{dump_cmd}' not found on the server. Please contact your administrator.", 'danger')
            return redirect(url_for('index'))'''

content = content.replace(old_try, new_try)

with open('app.py', 'w') as f:
    f.write(content)
