from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import signal

def test_ui():
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-secret"
    proc = subprocess.Popen(["python", "run_mock_app.py"], env=env, preexec_fn=os.setsid)
    time.sleep(5) # Give app more time to start up

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://127.0.0.1:5000/")

            # Check footer
            footer_exists = page.locator(".win11-page-footer").count() > 0
            print(f"Footer exists: {footer_exists}")

            # Check invoicing icons in quick actions
            page.click("button.btn-add-new-pro") # Open quick actions
            time.sleep(1)

            invoice_exists = page.locator("text=Sales Inv").count() > 0
            proforma_exists = page.locator("text=Proforma Inv").count() > 0
            print(f"Sales Invoice in Quick Actions: {invoice_exists}")
            print(f"Proforma Invoice in Quick Actions: {proforma_exists}")

            # Click an icon and check scroll top behavior
            page.click("text=Sales Inv")
            time.sleep(0.5)
            scroll_y = page.evaluate("window.scrollY")
            print(f"Scroll Y after click: {scroll_y}")
            loader_visible = page.evaluate("!document.getElementById('globalPageLoader').classList.contains('hidden')")
            print(f"Loader visible after click: {loader_visible}")

            browser.close()
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

test_ui()
