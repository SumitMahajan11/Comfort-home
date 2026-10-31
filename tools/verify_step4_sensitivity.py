#!/usr/bin/env python3
"""
Verify sensitivity of each Wizard Step 4 question on Step 5 outputs.
Saves before/after values and screenshots to reports/evidence/ui/step4/.
"""

import os
import json
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/step4"
os.makedirs(OUT_DIR, exist_ok=True)

def run():
    evidence = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def set_and_read_step5(city="Jodhpur", feel="comfortable", hours=18, cooling="fan", priority="balanced", pkg=None):
            pkg_param = f"&pkg={pkg}" if pkg else ""
            url = f"http://localhost:3000/recommender?city={city}&step=5&feel={feel}&hours={hours}&cooling={cooling}&priority={priority}{pkg_param}"
            page.goto(url)
            page.wait_for_timeout(1000)

            # Extract fit score of first card
            fit_score = page.locator("span.text-xl.font-extrabold.text-teal-300").first.inner_text() if page.locator("span.text-xl.font-extrabold.text-teal-300").count() > 0 else "N/A"
            cooling_mode = page.locator("text=/Active cooling|Free-running/").first.inner_text() if page.locator("text=/Active cooling|Free-running/").count() > 0 else "N/A"
            
            # Active package badge
            active_badge = page.locator("div.glass-card span.bg-teal-500").first.inner_text() if page.locator("div.glass-card span.bg-teal-500").count() > 0 else "N/A"
            
            # Extract Annual Discomfort Hours text
            discomfort_text = page.locator("text=/\\d+\\.\\d+% \\(\\d+ h\\/yr/").first.inner_text() if page.locator("text=/\\d+\\.\\d+% \\(\\d+ h\\/yr/").count() > 0 else "N/A"

            return {
                "active_package": active_badge,
                "fit_score": fit_score,
                "cooling_mode": cooling_mode,
                "discomfort_hours": discomfort_text
            }

        # -------------------------------------------------------------
        # Question 1: Sensation Preference (feel)
        # -------------------------------------------------------------
        print("\n--- Testing Question 1: Sensation Preference (feel) ---")
        q1_before = set_and_read_step5(feel="comfortable")
        page.screenshot(path=f"{OUT_DIR}/q1_feel_comfortable.png")

        q1_after_hot = set_and_read_step5(feel="too_hot")
        page.screenshot(path=f"{OUT_DIR}/q1_feel_too_hot.png")

        q1_after_cold = set_and_read_step5(feel="too_cold")
        page.screenshot(path=f"{OUT_DIR}/q1_feel_too_cold.png")

        evidence["Q1_feel"] = {
            "question": "1. Indoor Thermal Sensation Preference",
            "base_comfortable": q1_before,
            "changed_too_hot": q1_after_hot,
            "changed_too_cold": q1_after_cold,
            "changed": (q1_before["fit_score"] != q1_after_hot["fit_score"]) and (q1_before["fit_score"] != q1_after_cold["fit_score"])
        }
        print(f"  Comfortable Fit Score: {q1_before['fit_score']}")
        print(f"  Too Hot Fit Score:     {q1_after_hot['fit_score']}")
        print(f"  Too Cold Fit Score:    {q1_after_cold['fit_score']}")
        print(f"  --> Changed: {evidence['Q1_feel']['changed']}")

        # -------------------------------------------------------------
        # Question 2: Daily Occupancy Duration (hours)
        # -------------------------------------------------------------
        print("\n--- Testing Question 2: Daily Occupancy Duration (hours) ---")
        q2_before = set_and_read_step5(hours=18)
        page.screenshot(path=f"{OUT_DIR}/q2_hours_18.png")

        q2_after = set_and_read_step5(hours=8)
        page.screenshot(path=f"{OUT_DIR}/q2_hours_8.png")

        evidence["Q2_hours"] = {
            "question": "2. Daily Occupancy Duration",
            "base_18h": q2_before,
            "changed_8h": q2_after,
            "changed": q2_before["discomfort_hours"] != q2_after["discomfort_hours"]
        }
        print(f"  18 h/day: {q2_before['discomfort_hours']}")
        print(f"  8 h/day:  {q2_after['discomfort_hours']}")
        print(f"  --> Changed: {evidence['Q2_hours']['changed']}")

        # -------------------------------------------------------------
        # Question 3: Existing Cooling Available (cooling)
        # -------------------------------------------------------------
        print("\n--- Testing Question 3: Existing Cooling Available (cooling) ---")
        q3_before = set_and_read_step5(cooling="fan")
        page.screenshot(path=f"{OUT_DIR}/q3_cooling_fan.png")

        q3_after = set_and_read_step5(cooling="none")
        page.screenshot(path=f"{OUT_DIR}/q3_cooling_none.png")

        evidence["Q3_cooling"] = {
            "question": "3. Existing Cooling Available",
            "base_fan": q3_before,
            "changed_none": q3_after,
            "changed": (q3_before["cooling_mode"] != q3_after["cooling_mode"]) or (q3_before["fit_score"] != q3_after["fit_score"])
        }
        print(f"  Fan cooling mode:  {q3_before['cooling_mode']} | Fit: {q3_before['fit_score']}")
        print(f"  None cooling mode: {q3_after['cooling_mode']} | Fit: {q3_after['fit_score']}")
        print(f"  --> Changed: {evidence['Q3_cooling']['changed']}")

        # -------------------------------------------------------------
        # Question 4: Design Optimization Priority (priority)
        # -------------------------------------------------------------
        print("\n--- Testing Question 4: Design Optimization Priority (priority) ---")
        # Step 4 interactive click to verify priority change updates selection
        page.goto("http://localhost:3000/recommender?city=Jodhpur&step=4&priority=balanced")
        page.wait_for_timeout(800)
        page.click("button:has-text('Next: View Recommended Plan')")
        page.wait_for_timeout(800)
        q4_before = {
            "active_package": page.locator("div.glass-card span.bg-teal-500").first.inner_text(),
            "fit_score": page.locator("span.text-xl.font-extrabold.text-teal-300").first.inner_text()
        }
        page.screenshot(path=f"{OUT_DIR}/q4_priority_balanced.png")

        # Now test low energy priority
        page.goto("http://localhost:3000/recommender?city=Jodhpur&step=4&priority=low energy")
        page.wait_for_timeout(800)
        page.click("button:has-text('Next: View Recommended Plan')")
        page.wait_for_timeout(800)
        q4_after_budget = {
            "active_package": page.locator("div.glass-card span.bg-teal-500").first.inner_text(),
            "fit_score": page.locator("span.text-xl.font-extrabold.text-teal-300").first.inner_text()
        }
        page.screenshot(path=f"{OUT_DIR}/q4_priority_lowest_energy.png")

        # Now test comfort priority
        page.goto("http://localhost:3000/recommender?city=Jodhpur&step=4&priority=comfort")
        page.wait_for_timeout(800)
        page.click("button:has-text('Next: View Recommended Plan')")
        page.wait_for_timeout(800)
        q4_after_comfort = {
            "active_package": page.locator("div.glass-card span.bg-teal-500").first.inner_text(),
            "fit_score": page.locator("span.text-xl.font-extrabold.text-teal-300").first.inner_text()
        }
        page.screenshot(path=f"{OUT_DIR}/q4_priority_comfort.png")

        evidence["Q4_priority"] = {
            "question": "4. Design Optimization Priority",
            "base_balanced": q4_before,
            "changed_lowest_energy": q4_after_budget,
            "changed_comfort": q4_after_comfort,
            "changed": (q4_before["active_package"] != q4_after_budget["active_package"]) and (q4_before["active_package"] != q4_after_comfort["active_package"])
        }
        print(f"  Balanced selected:      {q4_before['active_package']}")
        print(f"  Lowest energy selected: {q4_after_budget['active_package']}")
        print(f"  Comfort selected:       {q4_after_comfort['active_package']}")
        print(f"  --> Changed: {evidence['Q4_priority']['changed']}")

        with open(f"{OUT_DIR}/step4_sensitivity_evidence.json", "w") as f:
            json.dump(evidence, f, indent=2)

        context.close()
        browser.close()

    print(f"\nSaved all Step 4 sensitivity screenshots and evidence to {OUT_DIR}/")

if __name__ == "__main__":
    run()
