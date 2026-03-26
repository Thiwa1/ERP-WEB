import re

with open('app.py', 'r') as f:
    content = f.read()

# If both tools are missing on the user's host (e.g. shared hosting), we should just tell them
# it's unavailable or disable the check and rely on the try/except block.
# However, if it's truly not on the server, `subprocess.run` will raise FileNotFoundError anyway.
# We'll just provide a better fallback message or remove the strict checking entirely.
# Let's see how the user wants to handle it. Actually, if they are on a shared host, they might have
# the binaries in a non-standard PATH, or they might not have shell access at all.

old_code = '''    # Check for mysqldump or mariadb-dump
    dump_cmd = shutil.which('mysqldump')
    if not dump_cmd:
        dump_cmd = shutil.which('mariadb-dump')

    if not dump_cmd:
        flash('mysqldump or mariadb-dump not found on server', 'danger')
        return redirect(url_for('index'))'''

new_code = '''    # Attempt to find the dump binary
    dump_cmd = shutil.which('mysqldump')
    if not dump_cmd:
        dump_cmd = shutil.which('mariadb-dump')

    # Fallback to string name if shutil.which fails due to PATH issues on some hosts
    if not dump_cmd:
        dump_cmd = 'mysqldump' '''

content = content.replace(old_code, new_code)

with open('app.py', 'w') as f:
    f.write(content)
