import re

with open('app.py', 'r') as f:
    content = f.read()

# Instead of blindly removing the check, fallback to mariadb-dump
old_code = '''    # Check for mysqldump
    if False:
        flash('mysqldump not found', 'danger')
        return redirect(url_for('index'))'''

new_code = '''    # Check for mysqldump or mariadb-dump
    dump_cmd = shutil.which('mysqldump')
    if not dump_cmd:
        dump_cmd = shutil.which('mariadb-dump')

    if not dump_cmd:
        flash('mysqldump or mariadb-dump not found on server', 'danger')
        return redirect(url_for('index'))'''

content = content.replace(old_code, new_code)

old_cmd = '''            cmd = [
                'mysqldump',
                f'--defaults-extra-file={defaults_file.name}','''

new_cmd = '''            cmd = [
                dump_cmd,
                f'--defaults-extra-file={defaults_file.name}','''

content = content.replace(old_cmd, new_cmd)

with open('app.py', 'w') as f:
    f.write(content)
