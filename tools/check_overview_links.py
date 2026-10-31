"""
Link checker script for Overview and Footer.
Verifies all <a> links and anchor targets on the Overview page (http://localhost:3000/):
- Internal routes return HTTP 200 (no 404s)
- Anchors (#...) resolve to existing DOM elements (no dead anchors)
- External links are valid well-formed URLs
"""

import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"

def check_overview_and_footer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading Overview page at {BASE_URL}/ ...")
        response = page.goto(f"{BASE_URL}/", wait_until="networkidle")
        if not response or response.status != 200:
            print(f"FAILED to load root page! Status: {response.status if response else 'None'}")
            sys.exit(1)

        # Extract all links on the Overview page
        links = page.eval_on_selector_all(
            "a[href]",
            """elements => elements.map(el => ({
                href: el.getAttribute('href'),
                text: el.innerText.trim() || el.getAttribute('aria-label') || '[icon/image]',
                location: el.closest('footer') ? 'Footer' : (el.closest('header') ? 'Header' : 'Overview Main')
            }))"""
        )

        print(f"Discovered {len(links)} links on Overview page and shell.\n")
        print(f"{'Location':<15} | {'Status':<16} | {'Target':<35} | {'Text'}")
        print("-" * 90)

        dead_links = []
        checked_urls = {}

        for item in links:
            href = item['href']
            text = item['text']
            location = item['location']

            # Ignore Next.js development server overlay links
            if "nextjs.org" in href:
                continue

            if not href or href == "#":
                dead_links.append((location, href, text, "Empty or stub '#' href"))
                print(f"{location:<15} | {'DEAD ANCHOR':<16} | {href:<35} | {text}")
                continue

            # Case 1: Pure in-page anchor (e.g. /#research-results or #research-results)
            if href.startswith("/#") or href.startswith("#"):
                anchor_id = href.split("#")[-1]
                target_el = page.query_selector(f"#{anchor_id}")
                if target_el:
                    status_str = f"OK (#{anchor_id})"
                    print(f"{location:<15} | {status_str:<16} | {href:<35} | {text}")
                else:
                    dead_links.append((location, href, text, f"Element #{anchor_id} not found on page"))
                    print(f"{location:<15} | {'DEAD ANCHOR':<16} | {href:<35} | {text}")
                continue

            # Case 2: External URL
            if href.startswith("http://") or href.startswith("https://"):
                parsed = urlparse(href)
                if parsed.netloc:
                    print(f"{location:<15} | {'OK (external)':<16} | {href:<35} | {text}")
                else:
                    dead_links.append((location, href, text, "Invalid external URL"))
                    print(f"{location:<15} | {'INVALID URL':<16} | {href:<35} | {text}")
                continue

            # Case 3: Internal route (with or without anchor)
            route_part = href.split("#")[0]
            anchor_part = href.split("#")[1] if "#" in href else None

            # Check route HTTP status
            full_url = f"{BASE_URL}{route_part}"
            if full_url not in checked_urls:
                sub_res = page.request.get(full_url)
                checked_urls[full_url] = sub_res.status

            code = checked_urls[full_url]
            if code != 200:
                dead_links.append((location, href, text, f"HTTP {code}"))
                print(f"{location:<15} | {f'HTTP {code}':<16} | {href:<35} | {text}")
                continue

            # If anchor part exists, verify DOM element on that target page
            if anchor_part:
                sub_page = browser.new_page()
                sub_page.goto(full_url, wait_until="domcontentloaded")
                target_el = sub_page.query_selector(f"#{anchor_part}")
                sub_page.close()
                if target_el:
                    status_str = f"OK (200 + #{anchor_part})"
                    print(f"{location:<15} | {status_str:<16} | {href:<35} | {text}")
                else:
                    dead_links.append((location, href, text, f"Element #{anchor_part} not found on {route_part}"))
                    print(f"{location:<15} | {'DEAD ANCHOR':<16} | {href:<35} | {text}")
                continue

            print(f"{location:<15} | {'OK (HTTP 200)':<16} | {href:<35} | {text}")

        print("-" * 90)
        print(f"\nAudit complete: Total links checked: {len(links)}")
        print(f"Total dead links or dead anchors: {len(dead_links)}")

        browser.close()

        if dead_links:
            print("\nFAIL: Found broken links/anchors:")
            for loc, h, t, err in dead_links:
                print(f" - [{loc}] {h} ({t}): {err}")
            sys.exit(1)
        else:
            print("\nPASS: Zero 404s and zero dead anchors found on Overview and footer.")

if __name__ == "__main__":
    check_overview_and_footer()
