"""
Capture script for Overview Rework verification.
Captures before and after states for:
- Overview (/) at 1440x900 (desktop) and 390x844 (mobile)
- Model Lab (/models) at 1440x900 (desktop) and 390x844 (mobile)
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("reports/evidence/ui/overview-rework")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("1440x900", 1440, 900),
    ("390x844", 390, 844),
]

ROUTES = [
    ("overview", "/"),
    ("models", "/models"),
]

def capture(stage="before"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp_name, w, h in VIEWPORTS:
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()
            for route_name, route_path in ROUTES:
                url = f"http://localhost:3000{route_path}"
                page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(1.0)
                # First screen view
                out_file = OUT_DIR / f"{stage}_{route_name}_{vp_name}.png"
                page.screenshot(path=str(out_file), full_page=False)
                print(f"Saved: {out_file}")

                # Also capture full page for Overview to verify footer and below the fold
                if route_name == "overview":
                    full_file = OUT_DIR / f"{stage}_{route_name}_full_{vp_name}.png"
                    page.screenshot(path=str(full_file), full_page=True)
                    print(f"Saved: {full_file}")

            # Capture Recommender Step 5 to verify StatusPairing
            print(f"Capturing recommender step 5 at {vp_name}...")
            page.goto("http://localhost:3000/recommender?city=Jodhpur", wait_until="networkidle")
            page.wait_for_timeout(1000)
            # Step 1 -> 2
            b2 = page.query_selector('button:has-text("Next: Choose Building Type")')
            if b2: b2.click(); page.wait_for_timeout(600)
            # Step 2 -> 3
            b3 = page.query_selector('button:has-text("Next: Set Priority")')
            if b3: b3.click(); page.wait_for_timeout(600)
            # Step 3 -> 4
            b4 = page.query_selector('button:has-text("Next: Occupant Habits")')
            if b4: b4.click(); page.wait_for_timeout(600)
            # Step 4 -> 5
            b5 = page.query_selector('button:has-text("Generate Recommended Packages")')
            if b5: b5.click(); page.wait_for_timeout(1500)
            step5_file = OUT_DIR / f"{stage}_status_pairing_{vp_name}.png"
            page.screenshot(path=str(step5_file), full_page=False)
            print(f"Saved: {step5_file}")

            context.close()
        browser.close()

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "before"
    capture(stage)
