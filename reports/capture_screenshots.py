import time
import os
from playwright.sync_api import sync_playwright

os.makedirs("reports/figures", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 1800})
    
    # 1. Jodhpur
    page.goto("http://localhost:8501", wait_until="networkidle")
    time.sleep(3)
    page.screenshot(path="reports/figures/app_get_shelter_jodhpur.png", full_page=True)
    print("Saved complete Jodhpur screenshot.")
    
    # 2. Shimla
    input_elem = page.locator('input[type="text"]').first
    input_elem.click()
    input_elem.fill("")
    input_elem.type("Shimla, Himachal Pradesh", delay=40)
    input_elem.press("Enter")
    time.sleep(3)
    
    submit_btn = page.locator('button:has-text("Generate Recommended Shelter Design")')
    if submit_btn.count() > 0:
        submit_btn.first.click()
    time.sleep(3)
    
    page.screenshot(path="reports/figures/app_get_shelter_shimla.png", full_page=True)
    print("Saved complete Shimla screenshot.")
    browser.close()
