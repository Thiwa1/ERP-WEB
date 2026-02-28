import sys
from unittest.mock import MagicMock

# Mock missing modules
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Now run the test
import unittest
# We need to manually patch app.py imports inside the test file or before import
# Since the test file imports app, we need to ensure app.py can be imported.
# But app.py imports flask at top level.
# So we mock it here before importing the test module.

from tests import benchmark_inventory_transfer
unittest.main(module=benchmark_inventory_transfer)
