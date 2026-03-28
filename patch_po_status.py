import re

# In app.py:
# def list_purchase_orders():
# We need to filter where `status` != 2 (assuming 2 = Completed/GRN matched) or similar.
# Wait, OP_NO_Table added `status` defaulting to 1.
# Let's say status = 2 means "Converted to GRN".

with open("app.py", "r") as f:
    content = f.read()

query_search = """        FROM OP_NO_Table h
        WHERE h.Delete_PO = 0"""

query_replace = """        FROM OP_NO_Table h
        WHERE h.Delete_PO = 0 AND h.status = 1"""

content = content.replace(query_search, query_replace)

# Now, we need to update the GRN submission to set PO status = 2 if it's auto-filled from a PO.
# Check templates/grn.html to see if po_id is sent in the POST.

with open("app.py", "w") as f:
    f.write(content)
