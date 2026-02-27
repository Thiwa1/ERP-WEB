import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module
import json

class TestJVEnhancements(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        self.patchers = []
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        p_perm = patch('app.check_permission', return_value=True)
        self.mock_perm = p_perm.start()
        self.patchers.append(p_perm)

        p_render = patch('app.render_template')
        self.mock_render = p_render.start()
        self.patchers.append(p_render)

        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_get_sub_accounts(self):
        self.mock_request.args = {'account_name': 'TestAccount'}

        self.mock_db.execute_query.return_value = [
            {'code': 101, 'name': 'Sub A'},
            {'code': 102, 'name': 'Sub B'}
        ]

        json_str = app_module.api_get_sub_accounts()

        self.assertNotIsInstance(json_str, MagicMock)

        data = json.loads(json_str)

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Sub A')

    def test_jv_print_route(self):
        def side_effect(query, params=None):
            if "SELECT j.jv_user_code" in query:
                return [{'jv_user_code': 'JV001', 'jv_naration': 'Test JV', 'entry_date': '2023-01-01', 'total_amount': 100}]
            if "SELECT account_name" in query:
                return [{'account_name': 'Acc 1', 'enty_values_DR': 100, 'enty_values_CR': 0, 'entry_sub_account_code': 0, 'entry_naration': 'Line 1'}]
            if "SELECT * FROM company" in query:
                return [{'company_name': 'Test Co'}]
            return []

        self.mock_db.execute_query.side_effect = side_effect

        app_module.print_journal_voucher(1)

        self.mock_render.assert_called()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], 'jv_print.html')
        self.assertEqual(kwargs['header']['jv_user_code'], 'JV001')
        self.assertEqual(kwargs['company']['company_name'], 'Test Co')

if __name__ == '__main__':
    unittest.main()
