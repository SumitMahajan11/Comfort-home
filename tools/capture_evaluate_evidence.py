#!/usr/bin/env python3
"""
Capture desktop (1440x900) and mobile (390x844) screenshots of Evaluate page
at three slider extremes (Low, Mid/Baseline, High) and nearest-Pareto comparison modal.
"""

import os
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/evaluate-improve"
os.makedirs(OUT_DIR, exist_ok=True)

EXTREMES = [
    {
        "name": "low_extreme",
        "params": "city=Jodhpur&roof_ins=0&wall_ins=0&mass=light&absorp=0.30&wwr=5&orient=0&shading=0.0&vent=1.0",
        "desc": "Low Extreme (0mm insulation, light mass, 0.30 absorp, 5% WWR, 0 deg N, 0m shading, 1.0 ACH)"
    },
    {
        "name": "mid_baseline",
        "params": "city=Jodhpur&roof_ins=75&wall_ins=50&mass=medium&absorp=0.40&wwr=15&orient=180&shading=0.50&vent=6.0",
        "desc": "Mid Baseline (75mm roof, 50mm wall, medium brick, 0.40 absorp, 15% WWR, 180 deg S, 0.5m shading, 6.0 ACH)"
    },
    {
        "name": "high_extreme",
        "params": "city=Jodhpur&roof_ins=150&wall_ins=150&mass=heavy&absorp=0.90&wwr=40&orient=270&shading=1.0&vent=15.0",
        "desc": "High Extreme (150mm insulation, heavy mass, 0.90 absorp, 40% WWR, 270 deg W, 1.0m shading, 15.0 ACH)"
    }
]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1440x900
        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        desktop_page = desktop_context.new_page()

        for ext in EXTREMES:
            url = f"http://localhost:3000/evaluate?{ext['params']}"
            desktop_page.goto(url)
            desktop_page.wait_for_selector("canvas")
            desktop_page.wait_for_timeout(1000)

            out_path = f"{OUT_DIR}/evaluate_{ext['name']}_desktop_1440x900.png"
            desktop_page.screenshot(path=out_path, full_page=True)
            print(f"Captured: {out_path} ({ext['desc']})")

        # Capture Nearest Pareto Comparison Modal
        desktop_page.goto("http://localhost:3000/evaluate?city=Jodhpur&roof_ins=75&wall_ins=50&mass=medium&absorp=0.40&wwr=15&orient=180&shading=0.50&vent=6.0")
        desktop_page.wait_for_selector("canvas")
        desktop_page.wait_for_timeout(800)
        desktop_page.locator("button:has-text('Compare with nearest Pareto design')").click()
        desktop_page.wait_for_timeout(600)
        modal_path = f"{OUT_DIR}/evaluate_compare_modal_desktop.png"
        desktop_page.screenshot(path=modal_path, full_page=True)
        print(f"Captured: {modal_path} (Nearest Pareto Comparison Modal)")

        desktop_context.close()

        # Mobile 390x844
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        )
        mobile_page = mobile_context.new_page()

        for ext in EXTREMES:
            url = f"http://localhost:3000/evaluate?{ext['params']}"
            mobile_page.goto(url)
            mobile_page.wait_for_selector("canvas")
            mobile_page.wait_for_timeout(1000)

            out_path = f"{OUT_DIR}/evaluate_{ext['name']}_mobile_390x844.png"
            mobile_page.screenshot(path=out_path, full_page=True)
            print(f"Captured: {out_path}")

        mobile_context.close()
        browser.close()

if __name__ == "__main__":
    run()
