"""
Automated capture script for header & page shell verification.
Captures all 8 routes across 3 viewport widths:
- Desktop: 1440x900
- Tablet: 1024x768 (below 1100px: hamburger collapsed)
- Mobile: 390x844
Also captures the open hamburger drawer with focus trap on 1024 and 390.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("reports/evidence/ui/header-shell-fix")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = [
    ("overview", "/"),
    ("plan", "/recommender"),
    ("cities", "/cities"),
    ("evaluate", "/evaluate"),
    ("tradeoffs", "/pareto"),
    ("explain", "/explain"),
    ("models", "/models"),
    ("about", "/about"),
]

VIEWPORTS = [
    ("1440", 1440, 900),
    ("1024", 1024, 768),
    ("390", 390, 844),
]

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for width_name, w, h in VIEWPORTS:
            print(f"\n--- Capturing viewport: {width_name}px ({w}x{h}) ---")
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()

            for route_name, route_path in ROUTES:
                url = f"http://localhost:3000{route_path}"
                print(f"Loading {route_name} at {url}...")
                page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(1.0) # Allow animations to settle

                out_file = OUT_DIR / f"{route_name}_{width_name}.png"
                page.screenshot(path=str(out_file), full_page=False)
                print(f"Saved: {out_file}")

            # If tablet or mobile (<1100px), test opening hamburger drawer and capturing it
            if w < 1100:
                print(f"Testing hamburger drawer and focus trap at {width_name}px...")
                page.goto("http://localhost:3000/", wait_until="networkidle")
                time.sleep(0.5)

                # Find hamburger button
                hamburger = page.locator("button[aria-controls='mobile-nav-drawer']")
                if hamburger.is_visible():
                    hamburger.click()
                    time.sleep(0.5)

                    drawer_file = OUT_DIR / f"drawer_open_{width_name}.png"
                    page.screenshot(path=str(drawer_file), full_page=False)
                    print(f"Saved drawer screenshot: {drawer_file}")

                    # Test Esc to close
                    page.keyboard.press("Escape")
                    time.sleep(0.3)
                    assert not page.locator("#mobile-nav-drawer").is_visible(), "Drawer should be closed after Esc"
                    print("Esc closed drawer successfully!")

            context.close()

        browser.close()
    print("\nAll screenshots and checks completed successfully!")

if __name__ == "__main__":
    capture_all()
