"""
Remote smoke tests for newsguru.chat production deployment.

Tests the live site to verify deployment is working.

Usage:
    python tests/remote_tests.py
    python tests/remote_tests.py https://custom-url.com
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

PROD_URL = sys.argv[1] if len(sys.argv) > 1 else "https://newsguru.chat"
SCREENSHOTS = Path(__file__).parent.parent / "screenshots" / "remote"

results = []


def log(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"name": name, "passed": passed, "detail": detail})
    icon = "+" if passed else "X"
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))


async def run():
    from playwright.async_api import async_playwright

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    print(f"\nTesting: {PROD_URL}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== 1. Homepage =====
        print("--- Homepage ---")
        try:
            resp = await page.goto(PROD_URL, timeout=30000)
            log("Homepage loads", resp.status == 200, f"status={resp.status}")
        except Exception as e:
            log("Homepage loads", False, str(e)[:80])
            await browser.close()
            _print_summary()
            return

        await asyncio.sleep(3)
        body = await page.evaluate('() => document.body.innerText')
        log("Has NewsGuru branding", "NewsGuru" in body or "ewsGuru" in body)
        log("Has topic cards", "News & Politics" in body or "Business & Tech" in body or "TOPICS" in body)
        log("Has live feed", "Live Feed" in body)
        log("Has starter cards", await page.evaluate('() => document.querySelectorAll(".starter-card").length') > 0)
        log("Has chat input", await page.evaluate('() => !!document.getElementById("chat-input")'))
        log("Has version number", "v0." in body or "v1." in body)

        left = await page.evaluate('() => document.getElementById("left-pane")?.offsetWidth > 50')
        right = await page.evaluate('() => document.getElementById("right-pane")?.offsetWidth > 50')
        log("3-pane: left pane visible", left)
        log("3-pane: right pane visible", right)
        await page.screenshot(path=str(SCREENSHOTS / "01-homepage.png"))

        # ===== 2. Static pages =====
        print("\n--- Static Pages ---")
        try:
            resp = await page.goto(f"{PROD_URL}/methodology", timeout=15000)
            log("Methodology page loads", resp.status == 200)
            meth = await page.evaluate('() => document.body.innerText')
            log("Methodology: has scoring factors", "Scale" in meth and "Impact" in meth)
        except Exception as e:
            log("Methodology page loads", False, str(e)[:60])

        try:
            resp = await page.goto(f"{PROD_URL}/about", timeout=15000)
            log("About page loads", resp.status == 200)
            about = await page.evaluate('() => document.body.innerText')
            log("About: has Predictive Labs", "Predictive Labs" in about or "predictivelabs" in about)
        except Exception as e:
            log("About page loads", False, str(e)[:60])

        try:
            resp = await page.goto(f"{PROD_URL}/login", timeout=15000)
            log("Login page loads", resp.status == 200)
        except Exception as e:
            log("Login page loads", False, str(e)[:60])

        try:
            resp = await page.goto(f"{PROD_URL}/register", timeout=15000)
            log("Register page loads", resp.status == 200)
        except Exception as e:
            log("Register page loads", False, str(e)[:60])

        # ===== 3. Treemap =====
        print("\n--- Treemap ---")
        try:
            resp = await page.goto(f"{PROD_URL}/treemap-chart", timeout=15000)
            log("Treemap chart page loads", resp.status == 200)
            await asyncio.sleep(4)
            has_plotly = await page.evaluate('() => !!document.querySelector(".js-plotly-plot")')
            log("Treemap: Plotly renders", has_plotly)
        except Exception as e:
            log("Treemap chart page loads", False, str(e)[:60])

        # ===== 4. Journalist chart =====
        try:
            resp = await page.goto(f"{PROD_URL}/journalist-chart", timeout=15000)
            log("Journalist chart page loads", resp.status == 200)
            await asyncio.sleep(4)
            has_j_plotly = await page.evaluate('() => !!document.querySelector(".js-plotly-plot")')
            log("Journalist chart: Plotly renders", has_j_plotly)
        except Exception as e:
            log("Journalist chart page loads", False, str(e)[:60])

        # ===== 5. API endpoints =====
        print("\n--- API ---")
        for endpoint in ["/api/trending", "/api/journalists", "/api/sources"]:
            try:
                resp = await page.goto(f"{PROD_URL}{endpoint}", timeout=10000)
                log(f"API {endpoint}", resp.status == 200)
            except Exception as e:
                log(f"API {endpoint}", False, str(e)[:60])

        # ===== 6. SSE feed =====
        print("\n--- SSE ---")
        await page.goto(PROD_URL)
        await asyncio.sleep(2)
        sse_ok = await page.evaluate("""() => {
            return fetch('/sse/feed').then(r => r.status === 200).catch(() => false);
        }""")
        log("SSE /sse/feed responds", sse_ok)

        # ===== 7. Chat interaction =====
        print("\n--- Chat ---")
        await page.goto(PROD_URL)
        await asyncio.sleep(3)
        try:
            await page.evaluate("""() => {
                var inp = document.getElementById('chat-input');
                if (inp) { inp.value = 'heatmap'; inp.disabled = false; inp.form.requestSubmit(); }
            }""")
            await asyncio.sleep(8)
            has_iframe = await page.evaluate('() => !!document.querySelector("iframe[src=\\"/treemap-chart\\"]")')
            log("Chat: heatmap trigger works", has_iframe)
            body3 = await page.evaluate('() => document.body.innerText')
            no_err = "couldn't generate" not in body3
            log("Chat: no error in response", no_err)
            await page.screenshot(path=str(SCREENSHOTS / "02-chat-heatmap.png"))
        except Exception as e:
            log("Chat interaction", False, str(e)[:60])

        # ===== 8. Mobile =====
        print("\n--- Mobile ---")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(PROD_URL)
        await asyncio.sleep(2)
        mobile_tabs = await page.evaluate('() => document.querySelector(".mobile-tabs")?.offsetHeight > 0')
        log("Mobile: tab bar visible", mobile_tabs)
        await page.screenshot(path=str(SCREENSHOTS / "03-mobile.png"))

        await browser.close()

    _print_summary()


def _print_summary():
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"\n{'='*50}")
    print(f"  {PROD_URL}")
    print(f"  {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")
    if failed:
        print("\n  FAILURES:")
        for r in results:
            if not r["passed"]:
                print(f"    X {r['name']}: {r['detail']}")
    print()


if __name__ == "__main__":
    asyncio.run(run())
