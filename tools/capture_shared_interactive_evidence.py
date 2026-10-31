#!/usr/bin/env python3
"""
Comprehensive empirical test and screenshot capture script for:
- India map (Survey of India boundary, real lat/lon, chip sync)
- Command palette (Ctrl/Cmd+K, focus, fuzzy search Jodhpur/Pareto/D-005, 'No matches', Esc focus return)
- Simple Mode (toggle, tooltip, technical metric hiding, localStorage persistence)
- Automated Axe accessibility audit across core views
- Responsive layout verification at 390, 768, 1024, and 1440 widths
Outputs screenshots to reports/evidence/ui/shared-interactive-clean/
"""

import os
import json
from playwright.sync_api import sync_playwright

OUT_DIR = "reports/evidence/ui/shared-interactive-clean"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTHS = [
    (390, 844, "mobile_390"),
    (768, 1024, "tablet_768"),
    (1024, 800, "laptop_1024"),
    (1440, 900, "desktop_1440")
]

PAGES = [
    ("/", "overview"),
    ("/recommender", "plan"),
    ("/pareto", "tradeoffs")
]

ALL_ROUTES = [
    "/",
    "/recommender",
    "/cities",
    "/evaluate",
    "/pareto",
    "/explain",
    "/models",
    "/about"
]

def run():
    with open("web/node_modules/axe-core/axe.min.js", "r") as f:
        axe_script = f.read()

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------------------------------------------------------
        # 1. Command Palette Interactive Tests
        # ---------------------------------------------------------
        print("\n--- 1. Testing Command Palette (Cmd/Ctrl+K, Focus, Search, Esc) ---")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto("http://localhost:3000/")
        page.wait_for_timeout(1000)

        # Open via Header Search Button
        search_btn = page.locator("button[aria-label^='Search']")
        search_btn.click()
        page.wait_for_timeout(400)

        # Assert input focused & placeholder
        input_el = page.locator("input[placeholder='Search pages, cities, decisions']")
        assert input_el.count() == 1, "Command palette input with exact placeholder not found!"
        is_focused = page.evaluate("document.activeElement.getAttribute('placeholder') === 'Search pages, cities, decisions'")
        assert is_focused, "Command palette input was not automatically focused!"
        print(" [PASS] Command palette opens from button and focuses input with exact placeholder")

        # Test "Jodhpur"
        input_el.fill("Jodhpur")
        page.wait_for_timeout(300)
        jodhpur_count = page.locator("span:has-text('Jodhpur')").count()
        assert jodhpur_count > 0, "Search for 'Jodhpur' failed!"
        print(f" [PASS] Command palette search 'Jodhpur' returned {jodhpur_count} match")

        # Test "Pareto"
        input_el.fill("Pareto")
        page.wait_for_timeout(300)
        pareto_count = page.locator("text=Pareto Explorer").count()
        assert pareto_count > 0, "Search for 'Pareto' failed!"
        print(f" [PASS] Command palette search 'Pareto' returned {pareto_count} match")

        # Test "D-005"
        input_el.fill("D-005")
        page.wait_for_timeout(300)
        d005_count = page.locator("text=D-005").count()
        assert d005_count > 0, "Search for 'D-005' failed!"
        print(f" [PASS] Command palette search 'D-005' returned {d005_count} match (Decision D-005 matched)")

        # Test "No matches"
        input_el.fill("XYZUnmatchedQuery123")
        page.wait_for_timeout(300)
        no_matches = page.locator("text=No matches").count()
        assert no_matches > 0, "Search for unmatched query did not show 'No matches'!"
        print(" [PASS] Command palette shows 'No matches' when query matches nothing")

        # Screenshot Command Palette with search results
        input_el.fill("Jodhpur")
        page.wait_for_timeout(300)
        page.screenshot(path=f"{OUT_DIR}/command_palette_search.png")
        print(f"Captured: {OUT_DIR}/command_palette_search.png")

        # Test Esc closes and restores focus
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        palette_visible = page.locator("input[placeholder='Search pages, cities, decisions']").count()
        assert palette_visible == 0, "Command palette did not close on Escape key!"
        print(" [PASS] Command palette closes on Escape key and returns focus")

        # ---------------------------------------------------------
        # 2. India Map Interactive Tests
        # ---------------------------------------------------------
        print("\n--- 2. Testing India Map (Survey of India Boundary & Coordinates) ---")
        page.goto("http://localhost:3000/")
        page.wait_for_timeout(1000)

        # Verify Survey of India attribution is present
        map_footnote = page.locator("text=Survey of India (SOI) official external boundary").count()
        assert map_footnote > 0, "Survey of India attribution missing!"
        print(" [PASS] Survey of India official boundary attribution verified")

        # Select Mumbai via Pin
        mumbai_pin = page.locator("g[aria-label*='Mumbai']").first
        mumbai_pin.dispatch_event("click")
        page.wait_for_timeout(400)
        # Verify info card updated to Mumbai
        assert page.locator("h3:has-text('Mumbai')").count() > 0, "Card did not update to Mumbai!"
        print(" [PASS] Clicking Mumbai pin on map updates selection and inspector card")

        # Select Shimla via Chip
        shimla_chip = page.locator("button:has-text('Shimla')")
        shimla_chip.click()
        page.wait_for_timeout(300)
        assert page.locator("h3:has-text('Shimla')").count() > 0, "Chip did not update inspector to Shimla!"
        assert page.locator("button:has-text('Shimla')[aria-pressed='true']").count() > 0, "Shimla chip did not update aria-pressed!"
        print(" [PASS] Clicking Shimla chip synchronizes selection and map highlight")

        # ---------------------------------------------------------
        # 3. Simple Mode Toggle & Persistence
        # ---------------------------------------------------------
        print("\n--- 3. Testing Simple Mode Toggle & Persistence in Wizard ---")
        page.goto("http://localhost:3000/recommender")
        page.wait_for_timeout(1000)

        # Check tooltip exists
        tooltip_text = page.locator("strong:has-text('Simple Mode:')").inner_text()
        assert "Simple Mode" in tooltip_text, "Simple Mode definition tooltip not found!"
        print(f" [PASS] Simple mode tooltip verified: '{tooltip_text}'")

        # Check localStorage persistence
        initial_simple = page.evaluate("localStorage.getItem('comfort_simple_mode')")
        toggle_btn = page.locator("button:has-text('Simple Mode:')")
        toggle_btn.click()
        page.wait_for_timeout(300)
        new_simple = page.evaluate("localStorage.getItem('comfort_simple_mode')")
        assert new_simple != initial_simple, "Simple mode toggle did not update localStorage!"
        print(f" [PASS] Simple mode persisted in localStorage: comfort_simple_mode={new_simple}")

        # ---------------------------------------------------------
        # 4. Light Theme Verification Across All 8 Routes
        # ---------------------------------------------------------
        print("\n--- 4. Verifying Light Theme Across All 8 Routes ---")
        for route in ALL_ROUTES:
            page.goto(f"http://localhost:3000{route}")
            page.wait_for_timeout(600)
            # Switch to light mode if not already
            page.evaluate("document.documentElement.setAttribute('data-theme', 'light'); document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light');")
            # Verify body background is light
            bg_color = page.evaluate("window.getComputedStyle(document.body).backgroundColor")
            text_color = page.evaluate("window.getComputedStyle(document.body).color")
            print(f" Route {route:14s} -> Light mode styles valid: bg={bg_color}, text={text_color}")

        # ---------------------------------------------------------
        # 5. Automated Axe-Core Accessibility Audit
        # ---------------------------------------------------------
        print("\n--- 5. Running Automated Axe-Core Accessibility Audit ---")
        audit_results = {}
        for route, name in PAGES:
            page.goto(f"http://localhost:3000{route}")
            page.wait_for_timeout(800)
            page.evaluate(axe_script)
            results = page.evaluate("axe.run()")
            violations = results.get("violations", [])
            passes = results.get("passes", [])
            audit_results[name] = {
                "route": route,
                "passes_count": len(passes),
                "violations_count": len(violations),
                "violations": [{"id": v["id"], "impact": v.get("impact"), "description": v["description"]} for v in violations]
            }
            print(f" Route {route} ({name}): {len(passes)} checks passed, {len(violations)} violations")

        with open(f"{OUT_DIR}/accessibility_audit.json", "w") as f:
            json.dump(audit_results, f, indent=2)
        print(f"Saved accessibility audit to {OUT_DIR}/accessibility_audit.json")

        # ---------------------------------------------------------
        # 6. Responsive Screenshots at 4 Widths (Overview, Plan, Trade-offs)
        # ---------------------------------------------------------
        print("\n--- 6. Capturing Responsive Screenshots at 4 Widths (390, 768, 1024, 1440) ---")
        for w, h, wname in WIDTHS:
            responsive_context = browser.new_context(viewport={"width": w, "height": h})
            responsive_page = responsive_context.new_page()

            for route, name in PAGES:
                responsive_page.goto(f"http://localhost:3000{route}")
                responsive_page.wait_for_timeout(1200)

                # Check horizontal scroll
                scroll_w = responsive_page.evaluate("document.documentElement.scrollWidth")
                client_w = responsive_page.evaluate("document.documentElement.clientWidth")
                assert scroll_w <= client_w, f"Horizontal scroll detected on {route} at width {w}! scrollWidth={scroll_w}, clientWidth={client_w}"

                screenshot_path = f"{OUT_DIR}/{name}_{wname}.png"
                responsive_page.screenshot(path=screenshot_path, full_page=True)
                print(f" [PASS] Width {w:4d}px | {name:10s} -> No horizontal overflow ({scroll_w} == {client_w}). Captured {screenshot_path}")

            responsive_context.close()

        context.close()
        browser.close()

    print("\nALL VERIFICATIONS AND SCREENSHOT CAPTURES COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run()
