import sys
import unittest

# Try to mock flask before importing anything
try:
    import tests.mock_env
except ImportError:
    pass

import tests.test_password_security_repro as ts
suite = unittest.TestLoader().loadTestsFromModule(ts)
unittest.TextTestRunner(verbosity=2).run(suite)
