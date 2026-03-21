The user said: `db_suport_name = "sri" new db NEED CREATE WITH db_suport_name = "sri" LINE 151`
Line 151 in `app.py`:
```python
# Force prefix onto database name to handle shared hosting constraints
_raw_db_name = os.environ.get('DB_NAME', 'Book_keeping')
if _raw_db_name.startswith(f"{db_suport_name}_"):
    _final_db_name = _raw_db_name
else:
    _final_db_name = f"{db_suport_name}_{_raw_db_name}"
```

But what if the user wants me to add `db_suport_name` to the DB creation at line 151?
Wait! In `app.py`, maybe the user is pointing out a typo or something.
Ah! In `app.py` line 147: `db_suport_name = "sri"`
Maybe they want to ensure that ANY new database created (e.g., through `create_tenant_db` or during initial startup) respects this variable.
Actually, let's look at `create_tenant_db`:
```python
def create_tenant_db(company_name, username, password, email, mobile=None):
    """Creates a new tenant DB, runs schema, and registers in Master DB."""
    import re

    safe_name = re.sub(r'[^a-z0-9]', '_', company_name.lower())
    db_name = f"{db_suport_name}_{safe_name}"
```
This already uses `db_suport_name` correctly!

Wait! I bet they mean when creating the `MASTER_DB_NAME` or the `default_db_name` (Book_keeping).
Line 183: `MASTER_DB_NAME = os.environ.get('MASTER_DB_NAME', 'master_db')`
Wait, does it have `sri_`?
Let's check line 183 in `app.py`!
