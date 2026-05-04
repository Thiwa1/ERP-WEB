import requests

try:
    s = requests.Session()
    # Login
    res = s.post('http://127.0.0.1:5000/login', data={'username': 'admin', 'password': '123'})

    # Get Customer P&L
    res = s.get('http://127.0.0.1:5000/customer_profit_loss')
    print("GET P&L status:", res.status_code)
    html = res.text
    if 'id="periods-container"' in html:
        print("Found periods-container")
    else:
        print("NO periods-container in HTML")

    # Get Customer BS
    res = s.get('http://127.0.0.1:5000/customer_balance_sheet')
    print("GET BS status:", res.status_code)
    html = res.text
    if 'card-header' in html:
        print("Found card-header in BS")

except Exception as e:
    print(e)
