with open('tests/test_password_security_repro.py', 'r') as f:
    text = f.read()

bad1 = "import flask\n        self.assertEqual(flask.session.get('username'), 'admin')"
good1 = "self.assertEqual(app.session.get('username'), 'admin')"
text = text.replace(bad1, good1)

bad2 = "app.session = {}"
good2 = "flask.session = {}\n        app.session = flask.session"
text = text.replace(bad2, good2)

with open('tests/test_password_security_repro.py', 'w') as f:
    f.write(text)
