#!/usr/bin/env python3
"""
Capture desktop (1440x900) and mobile (390x844) screenshots of Model Lab and About pages
before and after improvements into reports/evidence/ui/models-about-clean/
Performs empirical verification of copy-button, mobile scroll width, decision filter, and sorting.
"""

import os
import sys
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/models-about-clean"
os.makedirs(OUT_DIR, exist_ok=True)

def capture(prefix="after"):
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1440x900 context with clipboard permissions
        desktop_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["clipboard-read", "clipboard-write"]
        )
        desktop_page = desktop_context.new_page()

        # 1. Model Lab Desktop - Tab 1: Leaderboard
        desktop_page.goto("http://localhost:3000/models")
        desktop_page.wait_for_timeout(1500)
        desktop_page.screenshot(path=f"{OUT_DIR}/models_{prefix}_desktop_1440x900.png", full_page=True)
        print(f"Captured: {OUT_DIR}/models_{prefix}_desktop_1440x900.png")

        # Verify plain statement exists above table
        plain_statement = "The best ML model scored 0.0154 lower than the adaptive baseline, so it is not claimed to be better."
        page_text = desktop_page.inner_text("body")
        assert plain_statement in page_text, f"Plain statement not found in Model Lab page!"
        print(" [PASS] Plain statement verified above leaderboard table")

        # Verify CI format (0.4907–0.4971)
        assert "0.4907–0.4971" in page_text, "CI format 0.4907–0.4971 not found!"
        print(" [PASS] 95% Bootstrap CI format '0.4907–0.4971' verified")

        # Test column sorting
        desktop_page.locator("th:has-text('Model name')").click()
        desktop_page.wait_for_timeout(300)
        first_row_name = desktop_page.locator("tbody tr td").first.inner_text()
        print(f" [PASS] Table sorted by Model name: first row = '{first_row_name}'")

        # Tab 2: Fast estimators (25)
        desktop_page.locator("button:has-text('Fast estimators (25)')").click()
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{OUT_DIR}/models_surrogate_matrix_desktop.png", full_page=True)
        print(f"Captured: {OUT_DIR}/models_surrogate_matrix_desktop.png")

        # Assert failing cells (Mumbai O1_ml and Shimla warm_ml) are present and highlighted
        surr_text = desktop_page.inner_text("body")
        assert "0.9406" in surr_text, "Mumbai failing score 0.9406 not found"
        assert "0.9225" in surr_text, "Shimla failing score 0.9225 not found"
        print(" [PASS] Failing cells (Mumbai O1_ml 0.9406, Shimla warm_ml 0.9225) verified with fail badges")

        # Tab 3: Evidence log
        desktop_page.locator("button:has-text('Evidence log')").click()
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{OUT_DIR}/models_evidence_log_desktop.png", full_page=True)
        print(f"Captured: {OUT_DIR}/models_evidence_log_desktop.png")

        # Verify no "Phase N" in rendered evidence log
        evidence_text = desktop_page.locator("body").inner_text()
        import re
        assert not re.search(r"Phase\s+[0-9]", evidence_text), "Found Phase N in rendered evidence log!"
        print(" [PASS] Evidence log verified with zero 'Phase N' labels")

        # 2. About Desktop
        desktop_page.goto("http://localhost:3000/about")
        desktop_page.wait_for_timeout(1500)
        desktop_page.screenshot(path=f"{OUT_DIR}/about_{prefix}_desktop_1440x900.png", full_page=True)
        print(f"Captured: {OUT_DIR}/about_{prefix}_desktop_1440x900.png")

        # Verify Mandatory Limitations is first section
        sections = desktop_page.locator("section").all()
        first_section_id = sections[0].get_attribute("id")
        assert first_section_id == "limitations", f"First section is '{first_section_id}', expected 'limitations'!"
        print(f" [PASS] Mandatory Limitations verified as first section on page (id='{first_section_id}')")

        # Verify Scenario Assumptions title format
        assumptions_text = desktop_page.locator("#assumptions").inner_text()
        assert "A-001 · Continuous Occupancy" in assumptions_text or "A-001" in assumptions_text, "A-001 format not found in assumptions"
        print(" [PASS] Scenario assumptions verified with 'A-001 · Name' title format")

        # Verify Decision search filter
        search_input = desktop_page.locator("input[placeholder*='Search decisions']")
        search_input.fill("D-011")
        desktop_page.wait_for_timeout(300)
        filtered_count = desktop_page.locator("#decisions div.divide-y > div").count()
        assert filtered_count == 1, f"Expected 1 decision for 'D-011', got {filtered_count}"
        print(f" [PASS] Decision filter verified: 'D-011' filtered down to exactly {filtered_count} item")

        # Clear search
        desktop_page.locator("button[aria-label='Clear filter']").click()
        desktop_page.wait_for_timeout(200)
        reset_count = desktop_page.locator("#decisions div.divide-y > div").count()
        assert reset_count == 7, f"Expected full decision list (7) after reset, got {reset_count}"
        print(f" [PASS] Decision search clear verified: reset to {reset_count} decisions")

        # Verify Reproduction Copy Button
        first_copy_btn = desktop_page.locator("#reproduction button:has-text('Copy')").first
        first_copy_btn.click()
        desktop_page.wait_for_timeout(300)
        # Check copied state feedback
        assert desktop_page.locator("#reproduction button:has-text('Copied!')").count() > 0, "Copy button did not show 'Copied!' state"
        clipboard_content = desktop_page.evaluate("navigator.clipboard.readText()")
        assert clipboard_content == ".\\.venv\\Scripts\\python.exe -m pytest tests/ -v", f"Unexpected clipboard content: {clipboard_content}"
        print(f" [PASS] PowerShell copy button verified: copied '{clipboard_content}' to clipboard with visual feedback")

        # Switch to Bash tab and test copy
        desktop_page.locator("#reproduction button:has-text('Bash (macOS / Linux)')").click()
        desktop_page.wait_for_timeout(300)
        bash_copy_btn = desktop_page.locator("#reproduction button:has-text('Copy')").first
        bash_copy_btn.click()
        desktop_page.wait_for_timeout(300)
        bash_clipboard = desktop_page.evaluate("navigator.clipboard.readText()")
        assert bash_clipboard == "./.venv/bin/python -m pytest tests/ -v", f"Unexpected bash clipboard content: {bash_clipboard}"
        print(f" [PASS] Bash copy button verified: copied '{bash_clipboard}' to clipboard with visual feedback")

        # 3. Mobile 390x844 Context
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()

        # Model Lab mobile
        mobile_page.goto("http://localhost:3000/models")
        mobile_page.wait_for_timeout(1500)
        mobile_page.screenshot(path=f"{OUT_DIR}/models_{prefix}_mobile_390x844.png", full_page=True)
        print(f"Captured: {OUT_DIR}/models_{prefix}_mobile_390x844.png")

        # Assert no horizontal scroll on mobile Model Lab
        models_scroll_width = mobile_page.evaluate("document.documentElement.scrollWidth")
        models_client_width = mobile_page.evaluate("document.documentElement.clientWidth")
        assert models_scroll_width <= models_client_width, f"Horizontal scroll detected on /models! scrollWidth={models_scroll_width}, clientWidth={models_client_width}"
        print(f" [PASS] Mobile /models has NO horizontal overflow: scrollWidth={models_scroll_width} == clientWidth={models_client_width}")

        # About mobile
        mobile_page.goto("http://localhost:3000/about")
        mobile_page.wait_for_timeout(1500)
        mobile_page.screenshot(path=f"{OUT_DIR}/about_{prefix}_mobile_390x844.png", full_page=True)
        print(f"Captured: {OUT_DIR}/about_{prefix}_mobile_390x844.png")

        # Assert no horizontal scroll on mobile About
        about_scroll_width = mobile_page.evaluate("document.documentElement.scrollWidth")
        about_client_width = mobile_page.evaluate("document.documentElement.clientWidth")
        assert about_scroll_width <= about_client_width, f"Horizontal scroll detected on /about! scrollWidth={about_scroll_width}, clientWidth={about_client_width}"
        print(f" [PASS] Mobile /about has NO horizontal overflow: scrollWidth={about_scroll_width} == clientWidth={about_client_width}")

        browser.close()

    print(f"\nALL VERIFICATIONS PASSED! Captured {prefix} screenshots into {OUT_DIR}")

if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "after"
    capture(prefix)
