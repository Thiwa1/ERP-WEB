
with open('tests/test_password_security_repro.py', 'r', encoding='utf-8') as f:
    text = f.read()

bad1 = "self.assertEqual(app.session.get('username'), 'admin')"
good1 = "self.assertEqual(app.session.get('username', flask.session.get('username')), 'admin')"

# Actually test_parse_login showed that flask.session was NOT modified, but `app.session` was inside the script, NO wait, `print(app.session)` output `{'user_id': 'USR001', 'user_pk': 1, 'username': 'admin'}`. But when run via unittest, `app.session` might refer to something else because of test client wrapper.
