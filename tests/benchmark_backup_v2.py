import time
import unittest
import sys
import os

# Import mock environment FIRST
import tests.mock_env

from unittest.mock import MagicMock, patch

# Now import app (it will use the mocks)
import app

class TestBackupPerformance(unittest.TestCase):
    def setUp(self):
        pass

    @patch('subprocess.Popen')
    def test_backup_streaming_performance(self, mock_popen):
        """Measures the time taken for the streaming backup request."""

        print("\n--- Benchmarking Backup Route (Streaming) ---")

        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None # Initially running

        # Simulate stdout as a file-like object that yields chunks
        # We need to control this to measure TTFB vs Total Time if we were doing true network test
        # But here we are calling the function which returns a Response object IMMEDIATELY with a generator

        mock_process.stdout.read.side_effect = [b"Chunk 1", b"Chunk 2", b""] # simulate chunks
        mock_process.poll.side_effect = [None, None, 0] # Running, Running, Done
        mock_process.return_value = 0

        mock_popen.return_value = mock_process

        app.session['user_id'] = 'admin'

        start_time = time.time()

        # Call the route handler
        # It should return almost instantly now because it just returns a Response wrapper around a generator
        response = app.system_backup()

        end_time = time.time()

        duration = end_time - start_time
        print(f"Streaming Backup Response Init Duration: {duration:.4f} seconds")

        # Verify Response Type
        # app.Response is a MagicMock class from mock_env
        # But in app.py: return Response(stream_with_context(generate()), ...)
        # app.Response should be called

        app.Response.assert_called()

        # Get arguments passed to Response
        args, kwargs = app.Response.call_args
        # First arg is stream_with_context result
        # We can check if stream_with_context was called
        app.stream_with_context.assert_called()

        # IMPORTANT: Performance Verification
        # The duration should be significantly less than 2 seconds (the hypothetical DB dump time)
        # because it returns immediately.
        self.assertTrue(duration < 0.1, f"Expected < 0.1s, got {duration}s")

        # Verify Headers
        headers = kwargs.get('headers', {})
        self.assertIn('Content-Disposition', headers)
        self.assertEqual(headers['Content-Type'], 'application/sql')

if __name__ == '__main__':
    unittest.main()
