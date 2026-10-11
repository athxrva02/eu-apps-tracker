"""Optional browser smoke test against an already running local demo server."""

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--browser", help="Optional installed Chrome/Chromium executable")
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("Use a local demo server")
    token = os.environ.get("ADMIN_TOKEN", "")
    headers = {"Authorization": "Bearer " + token} if token else {}
    response = httpx.get(args.url + "/api/v1/overview", headers=headers)
    response.raise_for_status()
    if not response.json()["demo"]:
        parser.error("Browser smoke test requires a synthetic demo workspace")
    output = Path("test-results")
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        if token:
            import json

            page.add_init_script('sessionStorage.setItem("agent-token", ' + json.dumps(token) + ")")
        page.goto(args.url)
        expect(page.get_by_text("Demo workspace", exact=True).first).to_be_visible()
        expect(page.locator(".job-card").first).to_be_visible()
        page.screenshot(path=str(output / "jobs-desktop.png"), full_page=True)
        page.locator(".job-title").first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.screenshot(path=str(output / "job-detail.png"), full_page=True)
        page.keyboard.press("Escape")
        for name in ["Profile", "Sources", "Activity", "Settings"]:
            page.get_by_role("navigation").get_by_role("button", name=name, exact=True).click()
            expect(page.locator("main")).to_be_visible()
            assert page.locator("main h1").count() == 1
            page.screenshot(path=str(output / (name.lower() + ".png")), full_page=True)
        page.get_by_role("navigation").get_by_role("button", name="Opportunities").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(output / "jobs-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()
    print(
        "Five screens, job dialog, mobile overflow and browser errors checked; screenshots in test-results/."
    )


if __name__ == "__main__":
    main()
