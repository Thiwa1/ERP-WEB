with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. create_default_user
old_admin = """            # Using 'admin' / '123'
            db.execute_query(query, ('admin', '123', 'ADM001', 1, '0000000000', 'admin@example.com'), commit=True)
            logging.info("Default user created: admin / 123")"""

new_admin = """            # Using 'admin' / '123'
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash('123')
            db.execute_query(query, ('admin', pw_hash, 'ADM001', 1, '0000000000', 'admin@example.com'), commit=True)
            logging.info("Default user created: admin / 123 (hashed)")"""

if old_admin in text: text = text.replace(old_admin, new_admin)

# 2. Add hashing to POST /admin/users/add
old_add_user = """        cursor.execute(\"\"\"
            INSERT INTO Login_Table (User_Name, Password, Mobile_No, Email, User_Active)
            VALUES (%s, %s, %s, %s, 1)
        \"\"\", (username, password, mobile, email))"""

new_add_user = """        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash(password)
        cursor.execute(\"\"\"
            INSERT INTO Login_Table (User_Name, Password, Mobile_No, Email, User_Active)
            VALUES (%s, %s, %s, %s, 1)
        \"\"\", (username, pw_hash, mobile, email))"""
if old_add_user in text: text = text.replace(old_add_user, new_add_user)

# 3. Add hashing to POST /admin/users/update_details
old_update_user = """        if password:
            query = \"\"\"
                UPDATE Login_Table
                SET User_Name = %s, Password = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            \"\"\"
            params = (username, password, mobile, email, active, user_id)"""

new_update_user = """        if password:
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash(password)
            query = \"\"\"
                UPDATE Login_Table
                SET User_Name = %s, Password = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            \"\"\"
            params = (username, pw_hash, mobile, email, active, user_id)"""
if old_update_user in text: text = text.replace(old_update_user, new_update_user)

# 4. Modify POS cashier add
old_pos = """        db.execute_query(\"\"\"
            INSERT INTO pose_setting_table (Id, User_Name, Password, Mobile_Number)
            VALUES (0, %s, %s, %s)
        \"\"\", (username, password, mobile), commit=True)"""

new_pos = """        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash(password)
        db.execute_query(\"\"\"
            INSERT INTO pose_setting_table (Id, User_Name, Password, Mobile_Number)
            VALUES (0, %s, %s, %s)
        \"\"\", (username, pw_hash, mobile), commit=True)"""
if old_pos in text: text = text.replace(old_pos, new_pos)

# 5. Handle POS Login fallback
old_pos_login = """    if users:
        settings = users[0]
        if settings['Password'] == password:"""

new_pos_login = """    if users:
        settings = users[0]
        stored_password = settings['Password']
        is_valid = False
        is_legacy = False

        from werkzeug.security import check_password_hash, generate_password_hash

        if stored_password and (stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:')):
            if check_password_hash(stored_password, password):
                is_valid = True
        elif stored_password == password:
            is_valid = True
            is_legacy = True

        if is_valid:
            if is_legacy:
                try:
                    new_hash = generate_password_hash(password)
                    db.execute_query("UPDATE pose_setting_table SET Password = %s WHERE Id = %s", (new_hash, settings['Id']), commit=True)
                except Exception as e:
                    print(f"Error migrating POS password: {e}")"""
if old_pos_login in text: text = text.replace(old_pos_login, new_pos_login)

# 6. Handle main Login fallback
old_login = """        elif users:
            user = users[0]
            if user['Password'] == password:
                session['user_id'] = user['User_Code']
                session['user_pk'] = user['id']
                session['username'] = username"""

new_login = """        elif users:
            user = users[0]
            stored_password = user['Password']
            verified = False

            try:
                from werkzeug.security import check_password_hash, generate_password_hash
                if stored_password and (stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:')):
                    if check_password_hash(stored_password, password):
                        verified = True
                elif stored_password == password:
                    verified = True
                    # Migrate to hash
                    try:
                        new_hash = generate_password_hash(password)
                        db.execute_query("UPDATE Login_Table SET Password = %s WHERE id = %s", (new_hash, user['id']), commit=True)
                    except Exception as e:
                        print(f"Migration error: {e}")
            except Exception as e:
                print(f"Password check error: {e}")

            if verified:
                session['user_id'] = user['User_Code']
                session['user_pk'] = user['id']
                session['username'] = username"""
if old_login in text: text = text.replace(old_login, new_login)


with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
