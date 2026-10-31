"""
tools/capture_wizard_honest.py

Automated browser snapshot tool using Playwright for the honest wizard verification.
Captures:
- Step-by-step screenshots for Jodhpur and Shimla from Step 1 to Step 5 (and PDF output)
- Viewports: 1440x900 (desktop) and 390x844 (mobile)
- Saved to reports/evidence/ui/wizard-honest/
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("reports/evidence/ui/wizard-honest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]

CITIES = ["Jodhpur", "Shimla"]

def capture_wizard():
    print(f"Starting wizard honest verification capture to {OUT_DIR}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for city in CITIES:
            for vp_name, width, height in VIEWPORTS:
                print(f"\n--- Capturing {city} on {vp_name} ({width}x{height}) ---")
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2)
                page = context.new_page()

                # Step 1: Location
                page.goto(f"http://localhost:3000/recommender?step=1&city={city}", wait_until="networkidle")
                page.wait_for_timeout(1000)
                s1_file = OUT_DIR / f"{city.lower()}_step1_location_{vp_name}.png"
                page.screenshot(path=str(s1_file), full_page=True)
                print(f"Saved: {s1_file}")

                # Step 2: Typology & Assumptions
                page.goto(f"http://localhost:3000/recommender?step=2&city={city}", wait_until="networkidle")
                page.wait_for_timeout(1000)
                s2_file = OUT_DIR / f"{city.lower()}_step2_typology_{vp_name}.png"
                page.screenshot(path=str(s2_file), full_page=True)
                print(f"Saved: {s2_file}")

                # Step 3: Climate Profile & Confidence
                page.goto(f"http://localhost:3000/recommender?step=3&city={city}", wait_until="networkidle")
                page.wait_for_timeout(1000)
                s3_file = OUT_DIR / f"{city.lower()}_step3_climate_{vp_name}.png"
                page.screenshot(path=str(s3_file), full_page=True)
                print(f"Saved: {s3_file}")

                # Step 4: Occupant Profile & Questions
                page.goto(f"http://localhost:3000/recommender?step=4&city={city}&feel=too+hot&hours=18&cooling=fan&priority=balanced", wait_until="networkidle")
                page.wait_for_timeout(1000)
                s4_file = OUT_DIR / f"{city.lower()}_step4_occupant_{vp_name}.png"
                page.screenshot(path=str(s4_file), full_page=True)
                print(f"Saved: {s4_file}")

                # Step 5: Recommended Packages & Materials List
                page.goto(f"http://localhost:3000/recommender?step=5&city={city}&feel=too+hot&hours=18&cooling=fan&priority=balanced&pkg=pkg_balanced", wait_until="networkidle")
                page.wait_for_timeout(1500)
                s5_file = OUT_DIR / f"{city.lower()}_step5_packages_{vp_name}.png"
                page.screenshot(path=str(s5_file), full_page=True)
                print(f"Saved: {s5_file}")

                # If desktop, also test modal and PDF generation
                if vp_name == "desktop":
                    # Open comparison modal
                    cmp_btn = page.query_selector('button:has-text("Compare 3 Packages")')
                    if cmp_btn:
                        cmp_btn.click()
                        page.wait_for_timeout(600)
                        modal_file = OUT_DIR / f"{city.lower()}_compare_modal_desktop.png"
                        page.screenshot(path=str(modal_file), full_page=False)
                        print(f"Saved modal: {modal_file}")
                        close_btn = page.query_selector('button:has-text("Close Comparison")')
                        if close_btn:
                            close_btn.click()
                            page.wait_for_timeout(400)

                    # Capture Print / PDF sheet view
                    page.emulate_media(media="print")
                    page.wait_for_timeout(500)
                    pdf_preview_file = OUT_DIR / f"{city.lower()}_pdf_spec_sheet.png"
                    page.screenshot(path=str(pdf_preview_file), full_page=True)
                    print(f"Saved PDF preview: {pdf_preview_file}")

                    # Generate literal PDF artifact
                    pdf_doc_file = OUT_DIR / f"{city.lower()}_shelter_plan.pdf"
                    page.pdf(path=str(pdf_doc_file), format="A4")
                    print(f"Generated PDF doc: {pdf_doc_file}")

                context.close()

        # Additionally test non-station proxy match in Step 1 (e.g., Pune -> Mumbai proxy with >100km distance warning)
        print("\n--- Testing Nearest Station Proxy Match ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto("http://localhost:3000/recommender?step=1", wait_until="networkidle")
        search_input = page.query_selector('input[type="text"]')
        if search_input:
            search_input.fill("Pune")
            page.wait_for_timeout(500)
            proxy_file = OUT_DIR / "proxy_station_pune_match.png"
            page.screenshot(path=str(proxy_file), full_page=False)
            print(f"Saved proxy test: {proxy_file}")
        context.close()

        browser.close()
    print("Screenshot capture completed successfully.")

if __name__ == "__main__":
    capture_wizard()
