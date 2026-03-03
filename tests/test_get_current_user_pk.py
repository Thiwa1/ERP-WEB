import pytest
import tests.mock_env  # MUST BE FIRST
from unittest.mock import patch, MagicMock
from app import get_current_user_pk

@pytest.fixture
def mock_session():
    with patch('app.session', new_callable=dict) as mock_sess:
        yield mock_sess

def test_get_current_user_pk_success(mock_session):
    mock_session['user_pk'] = '123'
    assert get_current_user_pk() == 123

def test_get_current_user_pk_missing(mock_session):
    assert get_current_user_pk() == 0

def test_get_current_user_pk_invalid_type(mock_session):
    mock_session['user_pk'] = {'invalid': 'type'}
    assert get_current_user_pk() == 0

def test_get_current_user_pk_value_error(mock_session):
    mock_session['user_pk'] = 'abc'
    assert get_current_user_pk() == 0
