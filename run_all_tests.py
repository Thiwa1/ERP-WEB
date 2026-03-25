import unittest
loader = unittest.TestLoader()
tests = loader.discover('tests', pattern='test_*.py')
testRunner = unittest.runner.TextTestRunner()
testRunner.run(tests)
