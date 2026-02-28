
import unittest
from app import app

class TestRegisterPage(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()

    def test_register_page_loads(self):
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Start your free trial', response.data)
        self.assertIn(b'Company Name', response.data)
        self.assertIn(b'name="company_name"', response.data)

if __name__ == '__main__':
    unittest.main()
