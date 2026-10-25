"""
tools/capture_wizard_screenshots.py

Automated browser snapshot tool using Playwright.
Navigates the 5-step guided wizard on http://localhost:3000/recommender
and captures pixel-accurate screenshots to reports/evidence/.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "evidence"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run():
    print(f"Starting screenshot capture to {OUTPUT_DIR}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = context.new_page()

        # -------------------------------------------------------------
        # STEP 1: WHERE
        # -------------------------------------------------------------
        print("Navigating to http://localhost:3000/recommender (Step 1: Where)...")
        page.goto("http://localhost:3000/recommender", wait_until="networkidle")
        page.wait_for_timeout(2000)

        s1_path = os.path.join(OUTPUT_DIR, "wizard_step_1_where.png")
        page.screenshot(path=s1_path, full_page=True)
        print(f"Captured Step 1: {s1_path}")

        # Capture Hindi localized view
        lang_btn = page.query_selector('button[title*="हिंदी"], button:has-text("हिंदी")')
        if lang_btn:
            lang_btn.click()
            page.wait_for_timeout(1000)
            s1_hi_path = os.path.join(OUTPUT_DIR, "wizard_step_1_where_hindi.png")
            page.screenshot(path=s1_hi_path, full_page=True)
            print(f"Captured Step 1 Hindi: {s1_hi_path}")
            # Switch back to English
            en_btn = page.query_selector('button:has-text("English")')
            if en_btn:
                en_btn.click()
                page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # STEP 2: WHAT
        # -------------------------------------------------------------
        print("Advancing to Step 2: What (Typology & Budget)...")
        page.click('button:has-text("Next: Choose Building Type")')
        page.wait_for_timeout(1500)

        s2_path = os.path.join(OUTPUT_DIR, "wizard_step_2_what.png")
        page.screenshot(path=s2_path, full_page=True)
        print(f"Captured Step 2: {s2_path}")

        # -------------------------------------------------------------
        # STEP 3: YOUR CLIMATE
        # -------------------------------------------------------------
        print("Advancing to Step 3: Your Climate...")
        page.click('button:has-text("Next: Review Climate Data")')
        page.wait_for_timeout(1500)

        s3_path = os.path.join(OUTPUT_DIR, "wizard_step_3_climate.png")
        page.screenshot(path=s3_path, full_page=True)
        print(f"Captured Step 3: {s3_path}")

        # -------------------------------------------------------------
        # STEP 4: YOUR COMFORT
        # -------------------------------------------------------------
        print("Advancing to Step 4: Your Comfort (Questionnaire)...")
        page.click('button:has-text("Next: Comfort Questionnaire")')
        page.wait_for_timeout(1500)

        s4_path = os.path.join(OUTPUT_DIR, "wizard_step_4_comfort.png")
        page.screenshot(path=s4_path, full_page=True)
        print(f"Captured Step 4: {s4_path}")

        # -------------------------------------------------------------
        # STEP 5: YOUR PLAN
        # -------------------------------------------------------------
        print("Advancing to Step 5: Your Plan (3 Packages & Monthly Chart)...")
        page.click('button:has-text("Next: View Recommended Plan")')
        page.wait_for_timeout(2500)

        s5_path = os.path.join(OUTPUT_DIR, "wizard_step_5_plan.png")
        page.screenshot(path=s5_path, full_page=True)
        print(f"Captured Step 5: {s5_path}")

        # Open Compare Packages Modal
        compare_btn = page.query_selector('button:has-text("Compare 3 Packages")')
        if compare_btn:
            compare_btn.click()
            page.wait_for_timeout(1000)
            compare_path = os.path.join(OUTPUT_DIR, "wizard_step_5_compare_modal.png")
            page.screenshot(path=compare_path, full_page=True)
            print(f"Captured Compare Modal: {compare_path}")
            close_btn = page.query_selector('button:has-text("Close Comparison")')
            if close_btn:
                close_btn.click()
                page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # EXPERT MODE PAGES
        # -------------------------------------------------------------
        print("Navigating to Expert Design Studio (/evaluate)...")
        page.goto("http://localhost:3000/evaluate", wait_until="networkidle")
        page.wait_for_timeout(2000)
        exp_studio_path = os.path.join(OUTPUT_DIR, "expert_design_studio.png")
        page.screenshot(path=exp_studio_path, full_page=True)
        print(f"Captured Expert Studio: {exp_studio_path}")

        print("Navigating to Expert Pareto Explorer (/pareto)...")
        page.goto("http://localhost:3000/pareto", wait_until="networkidle")
        page.wait_for_timeout(2000)
        exp_pareto_path = os.path.join(OUTPUT_DIR, "expert_pareto_explorer.png")
        page.screenshot(path=exp_pareto_path, full_page=True)
        print(f"Captured Expert Pareto: {exp_pareto_path}")

        print("Navigating to Model Lab (/models)...")
        page.goto("http://localhost:3000/models", wait_until="networkidle")
        page.wait_for_timeout(2000)
        exp_models_path = os.path.join(OUTPUT_DIR, "expert_model_lab.png")
        page.screenshot(path=exp_models_path, full_page=True)
        print(f"Captured Expert Model Lab: {exp_models_path}")

        browser.close()
        print("All screenshot captures completed successfully!")

if __name__ == "__main__":
    run()
