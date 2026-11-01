"""
tools/capture_audit_screenshots.py

Captures screenshots for the 5 screens required by ui-data-consistency audit:
1. Overview (/)
2. City Explorer (/cities?city=Jodhpur)
3. Wizard Step 5 (/recommender)
4. Pareto Inspector (/pareto?city=Jodhpur)
5. Explain (/explain?city=Jodhpur)

Supports mode: 'before' or 'after'.
Viewports: 1440x900 (desktop) and 390x844 (mobile).
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "evidence", "ui", "ui-data-consistency"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "mobile", "width": 390, "height": 844},
]

def capture_screens(prefix="before"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            v_name = vp["name"]
            w = vp["width"]
            h = vp["height"]
            print(f"--- Capturing {prefix} at {v_name} ({w}x{h}) ---")

            context = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = context.new_page()

            # 1. Overview
            print("1. Overview...")
            page.goto("http://localhost:3000/", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{prefix}_overview_{w}x{h}.png"), full_page=True)

            # 2. City Explorer
            print("2. City Explorer...")
            page.goto("http://localhost:3000/cities?city=Jodhpur", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{prefix}_city_explorer_{w}x{h}.png"), full_page=True)

            # 3. Wizard Step 5
            print("3. Wizard Step 5...")
            page.goto("http://localhost:3000/recommender?city=Jodhpur", wait_until="networkidle")
            page.wait_for_timeout(1500)
            # Step 1 -> 2
            btn2 = page.query_selector('button:has-text("Next: Choose Building Type")')
            if btn2:
                btn2.click()
                page.wait_for_timeout(1000)
            # Step 2 -> 3
            btn3 = page.query_selector('button:has-text("Next: Review Climate Data")')
            if btn3:
                btn3.click()
                page.wait_for_timeout(1000)
            # Step 3 -> 4
            btn4 = page.query_selector('button:has-text("Next: Comfort Questionnaire")')
            if btn4:
                btn4.click()
                page.wait_for_timeout(1000)
            # Step 4 -> 5
            btn5 = page.query_selector('button:has-text("Next: View Recommended Plan")')
            if btn5:
                btn5.click()
                page.wait_for_timeout(2000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{prefix}_wizard_step5_{w}x{h}.png"), full_page=True)

            # 4. Pareto Inspector
            print("4. Pareto Inspector...")
            page.goto("http://localhost:3000/pareto?city=Jodhpur", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{prefix}_pareto_{w}x{h}.png"), full_page=True)

            # 5. Explain
            print("5. Explain...")
            page.goto("http://localhost:3000/explain?city=Jodhpur", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{prefix}_explain_{w}x{h}.png"), full_page=True)

            context.close()

        browser.close()
        print(f"Captured all {prefix} screenshots into {OUTPUT_DIR}")

if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "before"
    capture_screens(prefix)
