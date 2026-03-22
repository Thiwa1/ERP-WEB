import time
import os
import sys
import json
from unittest.mock import MagicMock

# Mock necessary modules
sys.modules['flask'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['services'] = MagicMock()
sys.modules['knowledge_base'] = MagicMock()
sys.modules['migrations'] = MagicMock()

os.environ['SECRET_KEY'] = 'test-secret-key-for-mock-env'

import app

# Mock database responses with delay
def mock_execute_query(*args, **kwargs):
    time.sleep(0.01) # 10ms per query to simulate network/IO delay
    if 'IN (' in args[0]:
        # Return a mock row for each item in the batch
        ids = args[1]
        return [{'inventory_price_selling': 100.0, 'inventory_price_link': link_id} for link_id in ids]
    else:
        return [{'inventory_price_selling': 100.0, 'inventory_price_link': args[1][0] if len(args) > 1 and args[1] else 1}]

app.db.execute_query.side_effect = mock_execute_query

start = time.time()
batch_ids = ",".join(str(i) for i in range(1, 51))
app.api_get_item_prices(batch_ids)
end = time.time()
print(f"Optimized (1 batch request for 50 items): {end - start:.4f} seconds")
