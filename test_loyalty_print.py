# The user issue: "now printer not corecly print.it amount not chainge"
# Look at my previous fix:
#         loyalty_active = int(r['Loyalty_Price_Active'] or 0)
#         special_active = int(r['Sales_with_Special_price_Active'] or 0)
#         market_active = int(r['Sales_with_market_price_Active'] or 0)

# What if `posSettings` sends strings from the frontend, but `_process_pos_cart_items` saves them into TINYINT?
# MySQL converts strings to TINYINT automatically. So DB holds 1 or 0.
# The user says "in this code you can find the print but dont chainge the other fixing beacase this code is given to you 4 time .ok"
# The provided C# code:
#             // Calculate Total_Value inline based on conditions
#             Total_Value =
#             (Sales_with_market_price == "1" && Loyality_costomer_Find == 0) ? Price_of_items * Convert.ToDouble(QuntitySaleText.Text) :
#             (Sales_with_Special_price == "1") ? ItemPriceComen * Convert.ToDouble(QuntitySaleText.Text) :
#             (Loyalty_Price == "1" && Loyality_costomer_Find == 1) ? ItemLoyalityPrice * Convert.ToDouble(QuntitySaleText.Text) :
#             Price_of_items * Convert.ToDouble(QuntitySaleText.Text) // Default fallback

# Look at C# precedence for POS CART ITEMS saving logic:
# 1. Market Price
# 2. Special Price
# 3. Loyalty Price
# Wait, no. If Market is 1 AND NOT Loyalty.
# If Special is 1.
# If Loyalty is 1 AND Loyalty.

# In Python `_process_pos_cart_items`:
# It calculates `total = parse_float(item.get('total', 0))`
# The frontend `pos.html` ALREADY CALCULATES the total based on `posSettings`!
