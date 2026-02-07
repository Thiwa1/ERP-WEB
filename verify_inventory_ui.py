from playwright.sync_api import sync_playwright
import time

def verify_inventory_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Login
            print("Navigating to login...")
            page.goto("http://localhost:5000/login")
            print("Filling credentials...")
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "123")
            print("Clicking submit...")
            page.click("button[type='submit']")

            # Check if we are redirected to index
            try:
                page.wait_for_url("http://localhost:5000/", timeout=5000)
                print("Login successful.")
            except:
                print("Login failed or timed out. Current URL:", page.url)
                page.screenshot(path="login_fail.png")
                # print body
                print(page.inner_text("body"))
                return

            # 2. Visit Inventory Transfer
            print("Navigating to Inventory Transfer...")
            page.goto("http://localhost:5000/inventory_transfer")
            page.wait_for_selector("h2")
            page.screenshot(path="inventory_transfer.png")
            print("Captured inventory_transfer.png")

            # 3. Visit Manufacturing
            print("Navigating to Inventory Production...")
            page.goto("http://localhost:5000/inventory_production")
            page.wait_for_selector("h2")
            page.click("#receive-tab") # Click tab
            time.sleep(0.5)
            page.screenshot(path="inventory_production.png")
            print("Captured inventory_production.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_inventory_ui()
