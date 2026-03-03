import sys
from unittest.mock import patch
import tests.mock_env
import app

def test_get_session_db_name_with_db_name():
    # Mock the session dictionary to contain 'db_name'
    with app.app.test_request_context():
        with patch.dict('app.session', {'db_name': 'test_db_name'}):
            db_name = app.get_session_db_name()
            assert db_name == 'test_db_name'

def test_get_session_db_name_without_db_name():
    # Mock the session dictionary to not contain 'db_name'
    with app.app.test_request_context():
        with patch.dict('app.session', {}, clear=True):
            # The function should return db_config['database']
            with patch.dict('app.db_config', {'database': 'default_db_name'}):
                db_name = app.get_session_db_name()
                assert db_name == 'default_db_name'
