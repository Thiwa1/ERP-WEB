import sys

with open("tests/mock_env.py", "r") as f:
    content = f.read()

new_mock = """import sys
from unittest.mock import MagicMock
if 'requests' not in sys.modules:
    mock_requests = MagicMock()
    sys.modules['requests'] = mock_requests

"""

if 'mock_requests' not in content:
    with open("tests/mock_env.py", "w") as f:
        f.write(new_mock + content)
