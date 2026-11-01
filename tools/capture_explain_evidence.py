#!/usr/bin/env python3
"""
Capture desktop (1440x900) and mobile (390x844) screenshots of Explain page
before and after improvements into reports/evidence/ui/explain-fix/
"""

import os
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/explain-fix"
os.makedirs(OUT_DIR, exist_ok=True)

def capture(prefix="after"):
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1440x900
        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        desktop_page = desktop_context.new_page()
        desktop_page.goto("http://localhost:3000/explain")
        desktop_page.wait_for_timeout(1500)
        desktop_page.screenshot(path=f"{OUT_DIR}/explain_{prefix}_desktop_1440x900.png", full_page=True)

        # Assert zero '$' characters in rendered DOM text
        body_text = desktop_page.inner_text("body")
        dollar_count = body_text.count("$")
        assert dollar_count == 0, f"Found {dollar_count} literal '$' characters in rendered Explain DOM!"
        print(f" [PASS] Zero '$' characters verified in live DOM snapshot ({len(body_text)} chars scanned)")

        # Toggle table views on desktop
        while desktop_page.locator("button:has-text('Show as table')").count() > 0:
            desktop_page.locator("button:has-text('Show as table')").first.click()
            desktop_page.wait_for_timeout(300)

        desktop_page.screenshot(path=f"{OUT_DIR}/explain_table_view_desktop.png", full_page=True)

        # Mobile 390x844
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()
        mobile_page.goto("http://localhost:3000/explain")
        mobile_page.wait_for_timeout(1500)
        mobile_page.screenshot(path=f"{OUT_DIR}/explain_{prefix}_mobile_390x844.png", full_page=True)

        browser.close()
    print(f"Captured {prefix} and table view screenshots into {OUT_DIR}")

if __name__ == "__main__":
    import sys
    stage = sys.argv[1] if len(sys.argv) > 1 else "after"
    capture(stage)
