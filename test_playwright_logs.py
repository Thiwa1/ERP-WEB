from playwright.sync_api import sync_playwright
import os
import threading
from app import app
from werkzeug.serving import make_server

os.environ['SECRET_KEY'] = 'test-secret-key'

import database
from unittest.mock import MagicMock
app.db = MagicMock()
app.db.get_connection.return_value.__enter__.return_value = MagicMock()

@app.before_request
def mock_login():
    from flask import session
    session['username'] = 'Admin'
    session['user_id'] = 'ADM001'
    session['user_pk'] = 1
    session['role'] = 'Admin'

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5006, app)
        self.ctx = app.app_context()
        self.ctx.push()
    def run(self):
        self.server.serve_forever()
    def shutdown(self):
        self.server.shutdown()

server = ServerThread(app)
server.start()

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Browser Error: {exc}"))
        page.goto("http://127.0.0.1:5006/")
        page.wait_for_timeout(2000)
        print("Checking if loader is visible...")
        loader = page.locator("#globalPageLoader")
        print("Loader display:", loader.evaluate("el => el.style.display"))
        print("Loader pointerEvents:", loader.evaluate("el => el.style.pointerEvents"))
        print("Loader classList:", loader.evaluate("el => Array.from(el.classList)"))
        browser.close()
finally:
    server.shutdown()
