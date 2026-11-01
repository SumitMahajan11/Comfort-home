#!/usr/bin/env python3
"""
Audit accessibility using axe-core across core routes and capture 1440px screenshot of the SOI map.
"""

import os
import json
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui"
os.makedirs(OUT_DIR, exist_ok=True)

PAGES = [
    ("/", "Overview"),
    ("/recommender", "Plan (Recommender)"),
    ("/pareto", "Trade-offs (Pareto)")
]

def main():
    with open("web/node_modules/axe-core/axe.min.js", "r") as f:
        axe_script = f.read()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("=== AXE ACCESSIBILITY AUDIT ===")
        for route, name in PAGES:
            page.goto(f"http://localhost:3000{route}")
            page.wait_for_timeout(1000)
            page.evaluate(axe_script)
            results = page.evaluate("axe.run()")
            violations = results.get("violations", [])
            passes = results.get("passes", [])

            print(f"\nRoute {route} ({name}):")
            print(f"  Passes: {len(passes)}")
            print(f"  Violations: {len(violations)}")
            for v in violations:
                print(f"    - Violation [{v['id']}] ({v.get('impact')}): {v['help']}")
                for node in v.get("nodes", []):
                    print(f"        target: {node.get('target')}")
                    print(f"        failureSummary: {node.get('failureSummary', '').splitlines()[0] if node.get('failureSummary') else ''}")

        # Capture 1440px screenshot of India Climate Map on Overview page
        print("\n=== CAPTURING 1440px MAP SCREENSHOT ===")
        page.goto("http://localhost:3000/")
        page.wait_for_timeout(1000)
        
        # Locate the map container
        map_el = page.locator("svg[viewBox='0 0 600 680']")
        map_el.wait_for()
        
        # Ensure all stations are visible
        for station in ["Shimla", "New Delhi", "Jodhpur", "Mumbai", "Bengaluru"]:
            count = page.locator(f"text={station}").count()
            print(f"  Station label visible: {station} (count={count})")

        # Scroll map into view and capture screenshot
        map_section = page.locator("section:has(svg[viewBox='0 0 600 680'])").first
        map_section.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        screenshot_path = os.path.join(OUT_DIR, "map_soi_1440.png")
        map_section.screenshot(path=screenshot_path)
        print(f"Saved map screenshot to: {screenshot_path}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
