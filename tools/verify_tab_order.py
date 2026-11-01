from playwright.sync_api import sync_playwright

def test_tab_order():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://localhost:3000/")
        page.wait_for_load_state("networkidle")

        # Focus body and press tab
        page.keyboard.press("Tab")
        active = page.evaluate("() => document.activeElement ? (document.activeElement.tagName + ' ' + (document.activeElement.getAttribute('aria-label') || document.activeElement.innerText || document.activeElement.id || document.activeElement.className)) : 'none'")
        print(f"Desktop 1st Tab: {active}")

        # Check subsequent tabs
        for i in range(5):
            page.keyboard.press("Tab")
            active = page.evaluate("() => document.activeElement ? (document.activeElement.tagName + ' ' + (document.activeElement.getAttribute('aria-label') || document.activeElement.innerText || document.activeElement.id || document.activeElement.className)) : 'none'")
            print(f"Desktop Tab {i+2}: {active[:60]}")

        # Tablet / Mobile Drawer focus trap test
        page_mobile = browser.new_page(viewport={"width": 1024, "height": 768})
        page_mobile.goto("http://localhost:3000/")
        page_mobile.wait_for_load_state("networkidle")

        # Open drawer
        hamburger = page_mobile.locator("button[aria-controls='mobile-nav-drawer']")
        hamburger.click()
        page_mobile.wait_for_timeout(200)

        # Tab through drawer items and verify it stays inside drawer
        focused_tags = []
        for i in range(12):
            page_mobile.keyboard.press("Tab")
            is_inside = page_mobile.evaluate("() => { const d = document.querySelector('#mobile-nav-drawer'); return d && d.contains(document.activeElement); }")
            assert is_inside, f"Tab escaped drawer at index {i}!"
            active = page_mobile.evaluate("() => document.activeElement ? document.activeElement.innerText.trim() : ''")
            focused_tags.append(active)
        print("Drawer focus trap verified! Focus stayed inside drawer for 12 consecutive tabs:", focused_tags[:4], "...")

        # Test Escape
        page_mobile.keyboard.press("Escape")
        page_mobile.wait_for_timeout(200)
        assert not page_mobile.locator("#mobile-nav-drawer").is_visible(), "Drawer should be closed after Escape"
        print("Escape successfully closed drawer!")

        browser.close()

if __name__ == "__main__":
    test_tab_order()
