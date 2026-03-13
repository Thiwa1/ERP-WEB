
import sys
from unittest.mock import MagicMock
if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()
import sys
from unittest.mock import MagicMock

# Define Mocks
mock_flask = MagicMock()
class MockFlask:
    def __init__(self, name):
        self.config = {}
        self.routes = {}
        self.view_functions = {}
        self.before_request_funcs = []

    def route(self, rule, **options):
        def decorator(f):
            # Normalization: simple routes
            self.routes[rule] = f
            endpoint = options.get('endpoint', f.__name__)
            self.view_functions[endpoint] = f
            return f
        return decorator

    def template_filter(self, name=None):
        return lambda f: f

    def context_processor(self, f):
        return f

    def before_request(self, f):
        self.before_request_funcs.append(f)
        return f

    def test_client(self):
        return MockTestClient(self)

    def run(self, *args, **kwargs): pass

class MockTestClient:
    def __init__(self, app):
        self.app = app
        self.cookie_jar = {}

    def session_transaction(self):
        class SessionContext:
            def __enter__(self):
                return mock_flask.session
            def __exit__(self, *args):
                pass
        return SessionContext()

    def _request(self, method, path, data=None, follow_redirects=False):
        mock_flask.request.method = method
        mock_flask.request.form = MagicMock()
        mock_flask.request.form.get = lambda k, d=None: data.get(k, d) if data else d

        def getlist(k):
            if data and k in data:
                val = data[k]
                return val if isinstance(val, list) else [val]
            return []
        mock_flask.request.form.getlist = getlist

        # Handle query args for GET
        mock_flask.request.args = {}
        if '?' in path:
            base, query = path.split('?', 1)
            path = base
            # Simple query parse
            for pair in query.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    mock_flask.request.args[k] = v

        mock_flask.request.files = {}

        # Route matching
        import re
        handler = self.app.routes.get(path)
        route_kwargs = {}

        # Try dynamic routes if exact match fails
        if not handler:
            for route, func in self.app.routes.items():
                if '<' in route:
                    pattern = route

                    def replacer(match):
                        inner = match.group(1)
                        if ':' in inner:
                            type_, name = inner.split(':', 1)
                            if type_ == 'int':
                                return f'(?P<{name}>\\d+)'
                            elif type_ == 'string':
                                return f'(?P<{name}>[^/]+)'
                            else:
                                return f'(?P<{name}>[^/]+)'
                        else:
                            return f'(?P<{inner}>[^/]+)'

                    pattern = re.sub(r'<([^>]+)>', replacer, pattern)
                    pattern = f"^{pattern}$"

                    match = re.match(pattern, path)
                    if match:
                        handler = func
                        for k, v in match.groupdict().items():
                            if f'<int:{k}>' in route:
                                route_kwargs[k] = int(v)
                            else:
                                route_kwargs[k] = v
                        break
                elif route == path:
                    handler = func
                    break

        if not handler:
            return MagicMock(status_code=404, data=b"Not Found")

        try:
            mock_flask.get_flashed_messages.side_effect = None
            # Clear previous flashes
            mock_flask.session['_flashes'] = []

            # Call handler with correctly extracted arguments
            import inspect
            sig = inspect.signature(handler)
            call_kwargs = {}
            for param_name in sig.parameters:
                if param_name in route_kwargs:
                    call_kwargs[param_name] = route_kwargs[param_name]
                else:
                    # Provide a fallback if signature expects an argument not in path,
                    # though in well-formed routes all non-default args should match path vars.
                    call_kwargs[param_name] = None

            resp = handler(**call_kwargs)

            # Helper to build response data with flash messages appended
            def build_response_data(base_data):
                flashes = [m[1] for m in mock_flask.session.get('_flashes', [])]
                msg_str = " ".join(flashes)
                if isinstance(base_data, bytes):
                    return base_data + msg_str.encode('utf-8')
                return str(base_data).encode('utf-8') + msg_str.encode('utf-8')

            if hasattr(resp, 'status_code') and resp.status_code == 302:
                if follow_redirects:
                    # Mock redirect following by returning 200 with flash messages
                    return MagicMock(status_code=200, data=build_response_data(b"Redirected"))
                else:
                    return resp

            # Regular response
            return MagicMock(status_code=200, data=build_response_data(resp))

        except Exception as e:
            return MagicMock(status_code=500, data=str(e).encode('utf-8'))

    def get(self, path, **kwargs):
        return self._request('GET', path, **kwargs)

    def post(self, path, data=None, **kwargs):
        return self._request('POST', path, data=data, **kwargs)

mock_flask.Flask = MockFlask
# Ensure render_template returns bytes-compatible string for consistency
mock_flask.render_template = MagicMock(return_value="RENDERED_TEMPLATE")
mock_flask.request = MagicMock()
mock_flask.redirect = lambda loc, code=302: MagicMock(status_code=code, location=loc, data=b"Redirecting")
mock_flask.url_for = lambda endpoint, **values: f"/{endpoint}"
mock_flask.session = {'_flashes': []}

def flash(message, category='message'):
    if '_flashes' not in mock_flask.session:
        mock_flask.session['_flashes'] = []
    mock_flask.session['_flashes'].append((category, message))
mock_flask.flash = flash

mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()
mock_flask.wraps = lambda f: f

# Inject ALL Mocks BEFORE imports
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Mock other external dependencies
mock_jinja2 = MagicMock()
mock_jinja2.pass_context = lambda f: f
sys.modules['jinja2'] = mock_jinja2

mock_flask_wtf = MagicMock()
sys.modules['flask_wtf'] = mock_flask_wtf
mock_flask_wtf.csrf = MagicMock()

sys.modules['dotenv'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['pymysql'] = MagicMock()

# Now import app
import app as app_module
import unittest
from unittest.mock import patch

class TestAddNewAccount(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db
        self.client = app_module.app.test_client()

        mock_flask.session['user_id'] = 'admin'
        mock_flask.session['user_pk'] = 1

    def test_get_page(self):
        with patch('app.check_permission', return_value=True):
            self.mock_db.execute_query.side_effect = [
                [{'name_of_category': 'BS1', 'holding_position': 1}],
                [{'name_of_category': 'PL1', 'holding_position': 1}],
                [{'catogory_name': 'CF1'}],
                [{'account_name': 'Acc1'}],
                [{'currency_code': 'LKR', 'currency_name': 'Rupee'}]
            ]

            response = self.client.get('/add_new_account')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'RENDERED_TEMPLATE', response.data)

    def test_add_account_success(self):
        with patch('app.check_permission', return_value=True):
            data = {
                'action': 'add_account',
                'account_name': 'Test Asset',
                'bs_category': 'BS1,1',
                'cf_category': 'CF1',
                'account_type': 'asset'
            }

            response = self.client.post('/add_new_account', data=data, follow_redirects=True)
            self.assertIn(b'New account created successfully', response.data)

            found = False
            for call in self.mock_db.execute_query.call_args_list:
                if "INSERT INTO new_account_table" in call[0][0]:
                    params = call[0][1]
                    if params[0] == 'Test Asset' and params[2] == '1' and params[7] == 1:
                        found = True
            self.assertTrue(found)

    def test_add_account_validation_missing_name(self):
        with patch('app.check_permission', return_value=True):
            data = {'action': 'add_account', 'account_name': ''}
            response = self.client.post('/add_new_account', data=data, follow_redirects=True)
            self.assertIn(b'Please enter an account name', response.data)

    def test_add_account_validation_missing_category(self):
        with patch('app.check_permission', return_value=True):
            data = {
                'action': 'add_account', 'account_name': 'Test',
                'bs_category': '', 'income_category': '', 'cf_category': 'CF1'
            }
            response = self.client.post('/add_new_account', data=data, follow_redirects=True)
            self.assertIn(b'Please select a category', response.data)

    def test_add_sub_account_success(self):
        with patch('app.check_permission', return_value=True):
            data = {
                'action': 'add_sub_account',
                'sub_account_name': 'Sub 1',
                'main_account_select': 'Main 1'
            }
            response = self.client.post('/add_new_account', data=data, follow_redirects=True)
            self.assertIn(b'Sub account created successfully', response.data)

            found = False
            for call in self.mock_db.execute_query.call_args_list:
                if "INSERT INTO sub_accont_for_new_account" in call[0][0]:
                    if call[0][1][0] == 'Sub 1':
                        found = True
            self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
