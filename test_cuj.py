from playwright.sync_api import sync_playwright

def run_cuj(page):
    # Go to SRN
    page.goto("http://localhost:5001/service_entry")
    page.wait_for_timeout(2000)
    page.screenshot(path="/home/jules/verification/screenshots/service_entry.png", full_page=True)

    # Go to Reversal
    page.goto("http://localhost:5001/service_entry_reversal")
    page.wait_for_timeout(2000)
    page.screenshot(path="/home/jules/verification/screenshots/service_entry_reversal.png", full_page=True)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        except Exception as e:
            print("Error:", e)
        finally:
            context.close()
            browser.close()
