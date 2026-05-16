import os
import re

db_suport_name = 'suwixvkn'
_raw_db_name = os.environ.get('DB_NAME', 'Book_keeping')
safe_raw_name = re.sub(r'[^a-zA-Z0-9_]', '_', _raw_db_name)
if safe_raw_name.startswith(db_suport_name + '_'):
    _final_db_name = safe_raw_name
else:
    _final_db_name = f"{db_suport_name}_{safe_raw_name}"

print(_final_db_name)
print(f"{db_suport_name}_Book_keeping_Master")
