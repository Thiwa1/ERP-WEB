import sys
from unittest.mock import MagicMock
import unittest
import os

# Mock modules
sys.modules['flask'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql'] = MagicMock()

# Add current directory to path
sys.path.append(os.getcwd())

if __name__ == '__main__':
    # Discover and run tests
    loader = unittest.TestLoader()
    # We point to 'tests' directory.
    # Note: The existing tests import 'app' which is in the root.
    # Since we added os.getcwd() to sys.path, 'import app' should work.

    suite = loader.discover('tests', pattern='test_*.py')

    runner = unittest.TextTestRunner()
    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)
