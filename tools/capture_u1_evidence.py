"""
tools/capture_u1_evidence.py

Captures Task U1 visual evidence:
- Copies baseline 'before' screenshots from reports/evidence/ui/final-verification/
- Captures new 'after' screenshots for all 8 routes in light and dark modes at 1440x900 and 390x844
- Saves everything into reports/evidence/ui/u1/
"""

import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
BEFORE_DIR = REPO_ROOT / "reports" / "evidence" / "ui" / "final-verification"
U1_DIR = REPO_ROOT / "reports" / "evidence" / "ui" / "u1"
U1_BEFORE = U1_DIR / "before"
U1_AFTER = U1_DIR / "after"

U1_DIR.mkdir(parents=True, exist_ok=True)
U1_BEFORE.mkdir(parents=True, exist_ok=True)
U1_AFTER.mkdir(parents=True, exist_ok=True)

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

VIEWPORTS = [
    (1440, 900, "1440"),
    (390, 844, "390"),
]

THEMES = ["light", "dark"]

def copy_before_evidence():
    print("--- 1. Copying Baseline 'Before' Screenshots ---")
    copied = 0
    for path, name in ROUTES:
        for theme in THEMES:
            for w, h, v_name in VIEWPORTS:
                src_file = BEFORE_DIR / f"{name}_{theme}_{v_name}.png"
                if src_file.exists():
                    shutil.copy2(src_file, U1_BEFORE / f"{name}_{theme}_{v_name}.png")
                    shutil.copy2(src_file, U1_DIR / f"before_{name}_{theme}_{v_name}.png")
                    copied += 1
    print(f" [PASS] Copied {copied} before screenshots to {U1_DIR}")

def capture_after_evidence():
    print("\n--- 2. Capturing 'After' Screenshots with New Color Tokens & Text Alignment ---")
    captured = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        for w, h, v_name in VIEWPORTS:
            page.set_viewport_size({"width": w, "height": h})
            for theme in THEMES:
                for path, name in ROUTES:
                    page.goto(f"http://localhost:3000{path}", wait_until="networkidle")
                    page.evaluate(
                        f"""(theme) => {{
                            document.documentElement.setAttribute('data-theme', theme);
                            if (theme === 'dark') {{
                                document.documentElement.classList.add('dark');
                                document.documentElement.classList.remove('light');
                            }} else {{
                                document.documentElement.classList.remove('dark');
                                document.documentElement.classList.add('light');
                            }}
                        }}""",
                        theme,
                    )
                    page.wait_for_timeout(150)
                    
                    target_after = U1_AFTER / f"{name}_{theme}_{v_name}.png"
                    target_flat = U1_DIR / f"after_{name}_{theme}_{v_name}.png"
                    target_standard = U1_DIR / f"{name}_{theme}_{v_name}.png"

                    page.screenshot(path=str(target_after), full_page=False)
                    shutil.copy2(target_after, target_flat)
                    shutil.copy2(target_after, target_standard)
                    captured += 1

                print(f" [PASS] Captured 8 routes in {theme.upper()} mode at {w}x{h}")

        browser.close()
    print(f" [PASS] Captured {captured} after screenshots to {U1_AFTER} and {U1_DIR}")

if __name__ == "__main__":
    copy_before_evidence()
    capture_after_evidence()
    print("\n[COMPLETE] All U1 evidence screenshots generated successfully.")
