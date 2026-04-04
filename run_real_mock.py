import os
import sys
import logging

os.environ['SECRET_KEY'] = 'test_key'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = ''

import app

# Mock DB layer correctly for lambda
app.db = type('MockDB', (), {
    'get_connection': lambda config=None: type('MockConn', (), {
        'cursor': lambda *args, **kwargs: type('MockCursor', (), {
            'execute': lambda *a, **k: None,
            'fetchall': lambda: [],
            'fetchone': lambda: None,
            'close': lambda: None
        })(),
        'commit': lambda: None,
        'rollback': lambda: None,
        'close': lambda: None
    })()
})()

@app.app.before_request
def mock_auth():
    from flask import session
    session['user_id'] = 'ADM001'
    session['user_pk'] = 1
    session['username'] = 'Admin'
    session['db_name'] = 'test_db'

if __name__ == "__main__":
    app.app.run(port=5000, host="0.0.0.0", debug=True, use_reloader=False)