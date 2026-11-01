#!/usr/bin/env python3
"""
Capture desktop (1440x900) and mobile (390x844) screenshots of Pareto Explorer
for all 5 cities (Jodhpur, Mumbai, New_Delhi, Bengaluru, Shimla) to satisfy
acceptance criteria.
"""

import os
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/pareto-fix"
os.makedirs(OUT_DIR, exist_ok=True)

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1440x900
        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        desktop_page = desktop_context.new_page()

        for city in CITIES:
            url = f"http://localhost:3000/pareto?city={city}"
            desktop_page.goto(url)
            desktop_page.wait_for_selector("svg.recharts-surface")
            desktop_page.wait_for_timeout(1000)

            # 1. Default frontier view (100 designs, inspector formatted, selected ring)
            desktop_path = f"{OUT_DIR}/pareto_{city}_desktop_1440x900.png"
            desktop_page.screenshot(path=desktop_path, full_page=True)
            print(f"Captured: {desktop_path}")

        # Capture Jodhpur with verified-only filter and table view open
        desktop_page.goto("http://localhost:3000/pareto?city=Jodhpur")
        desktop_page.wait_for_selector("svg.recharts-surface")
        desktop_page.wait_for_timeout(800)

        # Click "EnergyPlus verified only"
        desktop_page.locator("label:has-text('EnergyPlus verified only') input").click()
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{OUT_DIR}/pareto_Jodhpur_verified_only_desktop.png", full_page=True)
        print(f"Captured: {OUT_DIR}/pareto_Jodhpur_verified_only_desktop.png")

        # Click "Show as table"
        desktop_page.locator("button:has-text('Show as table')").click()
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{OUT_DIR}/pareto_Jodhpur_table_view_desktop.png", full_page=True)
        print(f"Captured: {OUT_DIR}/pareto_Jodhpur_table_view_desktop.png")

        desktop_context.close()

        # Mobile 390x844
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        )
        mobile_page = mobile_context.new_page()

        for city in CITIES:
            url = f"http://localhost:3000/pareto?city={city}"
            mobile_page.goto(url)
            mobile_page.wait_for_selector("svg.recharts-surface")
            mobile_page.wait_for_timeout(1000)

            mobile_path = f"{OUT_DIR}/pareto_{city}_mobile_390x844.png"
            mobile_page.screenshot(path=mobile_path, full_page=True)
            print(f"Captured: {mobile_path}")

        mobile_context.close()
        browser.close()

if __name__ == "__main__":
    run()
