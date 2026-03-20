with open("app.py", "r") as f:
    lines = f.readlines()

import re

for i, line in enumerate(lines):
    if "def send_sms_otp" in line:
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if "def pos_web_login" in lines[i]:
        end_idx = i
        break

new_code = """def send_sms_otp(mobile, code):
    \"\"\"Sends OTP via Notify.lk Gateway mirroring the legacy PHP logic.\"\"\"
    settings = {}

    # Try to load credentials from active tenant DB site_settings if available
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Handle cases where table doesn't exist yet gracefully
        try:
            cursor.execute("SELECT setting_key, setting_value FROM site_settings WHERE setting_key IN ('sms_user_id', 'sms_api_key', 'sms_sender_id')")
            settings = {r['setting_key']: r['setting_value'] for r in cursor.fetchall()}
        except Exception:
            pass
    except Exception as e:
        logging.error(f"Settings Load Error: {e}")
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()

    user_id = settings.get('sms_user_id') or os.getenv('NOTIFY_USER_ID', '')
    api_key = settings.get('sms_api_key') or os.getenv('NOTIFY_API_KEY', '')
    sender_id = settings.get('sms_sender_id') or os.getenv('NOTIFY_SENDER_ID', 'NotifyDEMO')

    if not api_key or not user_id:
        logging.error("NOTIFY_API_KEY or NOTIFY_USER_ID is not set. Skipping SMS delivery.")
        return False

    # Format number like the PHP script
    phone = str(mobile).strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif not phone.startswith("94"):
        phone = "94" + phone

    url = "https://app.notify.lk/api/v1/send"
    # Using GET method as demonstrated in the user's curl/example call
    # The API also accepts POST but to be extremely safe, we'll mimic the query string format exactly
    # And use the exact parameters specified in the user documentation.

    params = {
        'user_id': user_id,
        'api_key': api_key,
        'sender_id': sender_id,
        'to': phone,
        'message': f"Your SUWIN verification code is {code}."
    }

    try:
        logging.info(f"Sending SMS via Notify.lk to {phone} with sender {sender_id}")
        response = requests.post(url, data=params, timeout=10, verify=False)
        result = response.json()
        if result.get('status') == 'success':
            logging.info(f"SMS delivered successfully to {phone}.")
            return True
        else:
            logging.error(f"NotifySMS API Error: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Failed to send SMS: {e}")
        return False

"""

with open("app.py", "w") as f:
    f.writelines(lines[:start_idx] + [new_code] + lines[end_idx:])
