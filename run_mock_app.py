import os
import sys
import logging

os.environ['SECRET_KEY'] = 'test_key'
sys.path.append('.')

from tests import mock_env
import app

@app.app.before_request
def mock_auth():
    from flask import session
    session['user_id'] = 'ADM001'
    session['user_pk'] = 1
    session['username'] = 'Admin'

if __name__ == "__main__":
    app.app.run(port=5000, host="0.0.0.0", debug=True, use_reloader=False)
