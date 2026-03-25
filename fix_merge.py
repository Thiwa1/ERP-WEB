with open('app.py', 'r') as f:
    content = f.read()

merge_str = """<<<<<<< HEAD
    # Check for mysqldump or mariadb-dump
    dump_cmd = shutil.which('mysqldump')
    if not dump_cmd:
        dump_cmd = shutil.which('mariadb-dump')

    if not dump_cmd:
        flash('mysqldump or mariadb-dump not found on server', 'danger')
=======
    # Get the user's specific database name
    db_name = get_session_db_name()
    if not is_safe_db_name(db_name):
        flash('Invalid database name', 'danger')
        return redirect(url_for('index'))

    # Check for mysqldump
    if not shutil.which('mysqldump'):
        flash('mysqldump not found', 'danger')
>>>>>>> origin/add-db-schema-15069424110250862180"""

fixed_str = """    # Get the user's specific database name
    db_name = get_session_db_name()
    if not is_safe_db_name(db_name):
        flash('Invalid database name', 'danger')
        return redirect(url_for('index'))

    # Check for mysqldump or mariadb-dump
    dump_cmd = shutil.which('mysqldump')
    if not dump_cmd:
        dump_cmd = shutil.which('mariadb-dump')

    if not dump_cmd:
        flash('mysqldump or mariadb-dump not found on server', 'danger')"""

content = content.replace(merge_str, fixed_str)

with open('app.py', 'w') as f:
    f.write(content)
