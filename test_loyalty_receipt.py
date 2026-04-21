from app import app, db
import json
with app.app_context():
    # Let's see what is in pos_sales_invoice_01
    res = db.execute_query("SELECT Invoice_No, Loyalty_No, SllingPrice, ItemLoyalityPrice, Loyalty_Price_Active, Total_Value FROM pos_sales_invoice_01 ORDER BY jv DESC LIMIT 5")
    for r in res:
        print(r)
