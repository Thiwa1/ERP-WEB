# The frontend calculates `newPrice` correctly.
# If loyalty_price == 1 && loyaltyCustomer, newPrice = item.price_loyalty.
# It sets item.price = newPrice, item.total = qty * newPrice.
# The cart is passed to `_process_pos_cart_items`.
# The backend saves `item.get('total')` to DB `Total_Value`.
# BUT wait! In `pos_receipt(jv_no)` in `app.py`:
# It fetches the invoice from DB. It calculates:
#         if is_loyalty and loyalty_active == 1:
#             active_price = loyalty_price
#         elif special_active == 1:
#             active_price = special_price
#         elif market_active == 1:
#             active_price = selling_price

# WAIT! In C#: `GetItemPrice`
#         private double GetItemPrice(account_Details item)
#         {
#             if (Loyality_costomer_Find == 1 && Loyalty_Price == "1") return item.ItemLoyalityPrice;
#             else if (Sales_with_market_price == "1") return item.SllingPrice;
#             else if (Sales_with_Special_price == "1") return item.ItemPriceComen;
#             return item.SllingPrice; // Default fallback
#         }

# Wait. In C#, Market comes BEFORE Special!
# If BOTH Market and Special are "1", C# uses Market (SllingPrice).
# Python uses Special.

# Let's look at the user screenshot. "Sales with Market Price" is ON. "Loyalty Price Enabled" is ON. "Sales with Special Price" is OFF.
# So `loyalty_active = 1`. `market_active = 1`. `special_active = 0`.
# Is `is_loyalty` True in Python?
