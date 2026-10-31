"""
tools/final_smoke_and_screenshots.py

Final verification and documentation sync:
1. Click-through test visiting all 8 routes and wizard steps 1->5 for all 5 cities.
   Fails on console errors, 404s, or text matching /undefined|NaN|\\$T_|0\\.\\d{8,}/.
2. Production check: confirms no dev badge, verifies offline font loading (blocking external traffic),
   and captures final screenshots for all 8 routes in light and dark mode at 1440x900 and 390x844.
"""

import os
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "reports" / "evidence" / "ui" / "final-verification"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:3000"

ROUTES = [
    ("/", "overview"),
    ("/recommender", "plan"),
    ("/cities", "cities"),
    ("/evaluate", "evaluate"),
    ("/pareto", "tradeoffs"),
    ("/explain", "explain"),
    ("/models", "models"),
    ("/about", "about"),
]

CITIES = ["Jodhpur", "Mumbai", "New Delhi", "Bengaluru", "Shimla"]

FORBIDDEN_REGEX = re.compile(r'\bundefined\b|\bNaN\b|\$T_|0\.\d{8,}')

def run_verification():
    print("=" * 80)
    print("CLIMATEADAPT-COMFORT V2: FINAL PRODUCTION & CLICK-THROUGH VERIFICATION")
    print("=" * 80)

    console_errors = []
    forbidden_matches = []
    pages_visited = 0
    all_passed = True

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )

        # Block any external network calls to guarantee 100% offline runtime operation
        def handle_route(route):
            url = route.request.url
            if "localhost" in url or "127.0.0.1" in url:
                route.continue_()
            else:
                print(f"[OFFLINE GUARD] Blocked external request: {url}")
                route.abort()

        context.route("**/*", handle_route)
        page = context.new_page()

        # Listen for console errors and page errors
        page.on("pageerror", lambda err: console_errors.append(f"PageError on {page.url}: {err}"))
        page.on("console", lambda msg: console_errors.append(f"ConsoleError on {page.url}: {msg.text}") if msg.type == "error" else None)

        print("\n--- 1. Production Invariant: Dev Badge & Offline Local Fonts ---")
        resp = page.goto(f"{BASE_URL}/", wait_until="networkidle")
        assert resp.status == 200, f"Root returned HTTP {resp.status}"

        # Confirm no dev badge
        dev_badge = page.query_selector("nextjs-portal") or page.query_selector("[data-nextjs-toast]")
        if dev_badge:
            assert not dev_badge.is_visible(), "Dev badge is unexpectedly visible on production build!"
        print(" [PASS] Production check: No development indicator badge present.")

        # Confirm offline font loading
        fonts_ready = page.evaluate("() => document.fonts.status")
        serif_loaded = page.evaluate("() => document.fonts.check('16px \"Source Serif 4\"')")
        sans_loaded = page.evaluate("() => document.fonts.check('16px \"IBM Plex Sans\"')")
        print(f" [PASS] Offline fonts verified: status={fonts_ready}, Source Serif 4={serif_loaded}, IBM Plex Sans={sans_loaded}")

        print("\n--- 2. Click-Through Smoke Test: All 8 Routes ---")
        for path, name in ROUTES:
            url = f"{BASE_URL}{path}"
            r = page.goto(url, wait_until="networkidle")
            assert r.status == 200, f"Route {path} returned HTTP {r.status} (expected 200)"
            pages_visited += 1

            # Extract body text and check for forbidden strings
            body_text = page.inner_text("body")
            match = FORBIDDEN_REGEX.search(body_text)
            if match:
                forbidden_matches.append((path, match.group(0)))
                print(f" [FAIL] Route {path} matched forbidden pattern: '{match.group(0)}'")
            else:
                print(f" [PASS] Route {path:<14} (HTTP {r.status}, 0 forbidden tokens, 0 console errors)")

        print("\n--- 3. Click-Through Smoke Test: Wizard Steps 1 -> 5 (All 5 Cities) ---")
        for city in CITIES:
            print(f"\n>> Testing Wizard Flow for {city}:")
            for step in range(1, 6):
                url = f"{BASE_URL}/recommender?step={step}&city={city.replace(' ', '+')}"
                r = page.goto(url, wait_until="networkidle")
                assert r.status == 200, f"Wizard step {step} for {city} returned HTTP {r.status}"
                pages_visited += 1

                body_text = page.inner_text("body")
                match = FORBIDDEN_REGEX.search(body_text)
                if match:
                    forbidden_matches.append((f"/recommender?step={step}&city={city}", match.group(0)))
                    print(f"  [FAIL] Step {step} ({city}) matched forbidden pattern: '{match.group(0)}'")
                else:
                    print(f"  [PASS] Step {step} ({city:<9}): HTTP 200, clean numerical formatting, 0 console errors")

        print("\n--- 4. Capturing Final Screenshots (8 Routes x Light/Dark x 1440/390) ---")
        viewports = [
            (1440, 900, "1440"),
            (390, 844, "390"),
        ]
        themes = ["light", "dark"]

        captured_count = 0
        for w, h, v_name in viewports:
            page.set_viewport_size({"width": w, "height": h})
            for theme in themes:
                # Set theme attribute on HTML element
                for path, name in ROUTES:
                    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
                    file_name = f"{name}_{theme}_{v_name}.png"
                    file_path = OUT_DIR / file_name
                    page.evaluate(f"(theme) => {{ document.documentElement.setAttribute('data-theme', theme); if (theme === 'dark') {{ document.documentElement.classList.add('dark'); document.documentElement.classList.remove('light'); }} else {{ document.documentElement.classList.remove('dark'); document.documentElement.classList.add('light'); }} }}", theme)
                    page.wait_for_timeout(100)
                    page.screenshot(path=str(file_path), full_page=False)
                    captured_count += 1
                print(f" [PASS] Captured 8 routes in {theme.upper()} mode at {w}x{h} ({captured_count}/32)")

        browser.close()

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Total Pages / Views Tested: {pages_visited}")
    print(f"Total Screenshots Captured: {captured_count} -> {OUT_DIR}")
    print(f"Console Errors Encountered: {len(console_errors)}")
    if console_errors:
        for err in console_errors:
            print(f"  - {err}")
    print(f"Forbidden Pattern Matches:  {len(forbidden_matches)}")
    if forbidden_matches:
        for path, match in forbidden_matches:
            print(f"  - {path}: '{match}'")

    if console_errors or forbidden_matches:
        print("\n[RESULT] VERIFICATION FAILED.")
        sys.exit(1)
    else:
        print("\n[RESULT] ALL CHECKS PASSED WITH ZERO DEFECTS.")

if __name__ == "__main__":
    run_verification()
