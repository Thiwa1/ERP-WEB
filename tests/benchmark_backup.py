import time
import unittest
from unittest.mock import MagicMock, patch
import app
from app import app as flask_app

class TestBackupPerformance(unittest.TestCase):
    def setUp(self):
        self.app = flask_app.test_client()
        self.app.testing = True
        # Mock session to bypass login
        with self.app.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

    @patch('subprocess.Popen')
    def test_backup_synchronous_blocking(self, mock_popen):
        """Measures the time taken for the synchronous backup request."""

        # Mock process to simulate delay
        mock_process = MagicMock()
        mock_process.communicate = MagicMock(side_effect=lambda: (time.sleep(2) or b"Simulated SQL Dump", b""))
        mock_process.return_value = 0
        mock_popen.return_value = mock_process

        start_time = time.time()
        response = self.app.get('/system_backup')
        end_time = time.time()

        duration = end_time - start_time
        print(f"\nSynchronous Backup Duration: {duration:.4f} seconds")

        # In current state, it should be > 2 seconds
        self.assertTrue(duration >= 2.0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/sql')

if __name__ == '__main__':
    unittest.main()
