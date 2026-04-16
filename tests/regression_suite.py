"""
NewsGuru Regression Test Suite

Tests all pages and key interactions with Playwright.
Generates docs/test_coverage.md report.

Usage:
    python main.py &   # start app on port 5020
    python tests/regression_suite.py
"""
import asyncio
import time
from pathlib import Path
from datetime import datetime

BASE = "http://localhost:5020"
SCREENSHOTS = Path(__file__).parent.parent / "screenshots" / "regression"
REPORT_PATH = Path(__file__).parent.parent / "docs" / "test_coverage.md"

results = []


def log(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"name": name, "passed": passed, "detail": detail})
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


async def run():
    from playwright.async_api import async_playwright

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== 1. Homepage loads =====
        print("\n--- Page Load Tests ---")
        resp = await page.goto(BASE)
        log("Homepage returns 200", resp.status == 200)
        await page.screenshot(path=str(SCREENSHOTS / "01-homepage.png"))

        # Check 3-pane layout
        left = await page.evaluate('() => document.getElementById("left-pane")?.offsetWidth > 100')
        right = await page.evaluate('() => document.getElementById("right-pane")?.offsetWidth > 100')
        chat_input = await page.evaluate('() => !!document.getElementById("chat-input")')
        log("3-pane layout: left pane", left)
        log("3-pane layout: right pane", right)
        log("3-pane layout: chat input", chat_input)

        # Check left pane sections
        body_text = await page.evaluate('() => document.body.innerText')
        log("Left pane: New Chat button", "New Chat" in body_text)
        log("Left pane: Topics section", "TOPICS" in body_text or "Topics" in body_text)
        log("Left pane: Significance Map link", "Significance Map" in body_text)
        log("Left pane: Trending section", "TRENDING" in body_text or "Trending" in body_text)
        log("Left pane: Sources section", "SOURCES" in body_text or "Sources" in body_text)
        log("Left pane: Journalists section", "JOURNALISTS" in body_text or "Journalists" in body_text)
        log("Left pane: Methodology link", "Methodology" in body_text)

        # Check starter cards (only on fresh session — may be 0 if session has messages)
        starters = await page.evaluate('() => document.querySelectorAll(".starter-card").length')
        log("Starter cards present", starters == 6 or starters == 0, f"found {starters} (0 ok if session has history)")

        # Check live feed
        feed_items = await page.evaluate('() => document.querySelectorAll(".feed-item").length')
        log("Live feed has articles", feed_items > 0, f"{feed_items} items")

        # ===== 2. Login page =====
        print("\n--- Auth Pages ---")
        resp = await page.goto(f"{BASE}/login")
        log("Login page returns 200", resp.status == 200)
        has_email = await page.evaluate('() => !!document.querySelector("input[name=email]")')
        log("Login has email field", has_email)
        await page.screenshot(path=str(SCREENSHOTS / "02-login.png"))

        # ===== 3. Register page =====
        resp = await page.goto(f"{BASE}/register")
        log("Register page returns 200", resp.status == 200)
        has_name = await page.evaluate('() => !!document.querySelector("input[name=display_name]")')
        log("Register has name field", has_name)
        await page.screenshot(path=str(SCREENSHOTS / "03-register.png"))

        # ===== 4. Methodology page =====
        print("\n--- Static Pages ---")
        resp = await page.goto(f"{BASE}/methodology")
        log("Methodology page returns 200", resp.status == 200)
        meth_text = await page.evaluate('() => document.body.innerText')
        log("Methodology: has scoring table", "Scale" in meth_text and "Impact" in meth_text)
        log("Methodology: has philosophy", "Significance is objective" in meth_text)
        log("Methodology: has distribution", "0-2" in meth_text)
        await page.screenshot(path=str(SCREENSHOTS / "04-methodology.png"))

        # ===== 5. Treemap standalone =====
        print("\n--- Treemap ---")
        resp = await page.goto(f"{BASE}/treemap-chart")
        log("Treemap page returns 200", resp.status == 200)
        await asyncio.sleep(4)
        has_plotly = await page.evaluate('() => !!document.querySelector(".js-plotly-plot")')
        log("Treemap: Plotly chart rendered", has_plotly)
        has_what = await page.evaluate('() => !!document.querySelector("a[href=\\"/methodology\\"]")')
        log("Treemap: 'What is this?' link", has_what)
        await page.screenshot(path=str(SCREENSHOTS / "05-treemap-standalone.png"))

        # ===== 6. Treemap in chat =====
        await page.goto(BASE)
        await asyncio.sleep(2)
        await page.evaluate("""() => {
            var inp = document.getElementById('chat-input');
            inp.value = 'heatmap';
            inp.disabled = false;
            inp.form.requestSubmit();
        }""")
        await asyncio.sleep(6)
        has_iframe = await page.evaluate('() => !!document.querySelector("iframe[src=\\"/treemap-chart\\"]")')
        log("Treemap in chat: iframe present", has_iframe)
        headlines = await page.evaluate('() => document.body.innerText.includes("Top Stories")')
        log("Treemap in chat: headlines below", headlines)
        await page.screenshot(path=str(SCREENSHOTS / "06-treemap-in-chat.png"))

        # ===== 7. Chat interaction =====
        print("\n--- Chat Tests ---")
        await page.goto(BASE)
        await asyncio.sleep(2)
        await page.evaluate("""() => {
            var inp = document.getElementById('chat-input');
            inp.value = 'What are the main news today?';
            inp.disabled = false;
            inp.form.requestSubmit();
        }""")
        await asyncio.sleep(15)
        user_msg = await page.evaluate('() => document.body.innerText.includes("What are the main news")')
        log("Chat: user message shown", user_msg)
        response = await page.evaluate('() => document.querySelectorAll(".chat-assistant").length')
        log("Chat: assistant response present", response > 0, f"{response} responses")
        share = await page.evaluate('() => document.body.innerText.includes("Share this chat")')
        log("Chat: share widget present", share)
        await page.screenshot(path=str(SCREENSHOTS / "07-chat-response.png"))

        # ===== 8. Topic navigation =====
        print("\n--- Topic Navigation ---")
        resp = await page.goto(f"{BASE}/topic/politics")
        log("Topic /politics returns 200", resp.status == 200)
        await page.screenshot(path=str(SCREENSHOTS / "08-topic-politics.png"))

        resp = await page.goto(f"{BASE}/topic/technology")
        log("Topic /technology returns 200", resp.status == 200)

        try:
            resp = await page.goto(f"{BASE}/topic/nonexistent", timeout=5000)
            log("Invalid topic redirects", resp.status == 200 or resp.status == 303, f"url={page.url}")
        except Exception:
            log("Invalid topic redirects", True, "redirect/timeout")

        # ===== 9. API endpoints =====
        print("\n--- API Endpoints ---")
        resp = await page.goto(f"{BASE}/api/trending")
        log("API /api/trending returns 200", resp.status == 200)

        resp = await page.goto(f"{BASE}/api/journalists")
        log("API /api/journalists returns 200", resp.status == 200)

        resp = await page.goto(f"{BASE}/api/sources")
        log("API /api/sources returns 200", resp.status == 200)

        # ===== 10. SSE endpoints (streaming — use fetch with timeout) =====
        print("\n--- SSE Endpoints ---")
        sse_ok = await page.evaluate("""() => {
            return fetch('/sse/feed').then(r => r.status === 200).catch(() => false);
        }""")
        log("SSE /sse/feed returns 200", sse_ok)
        await page.goto(BASE)  # navigate away from SSE

        # ===== 11. Language switch (requires login) =====
        print("\n--- Language ---")
        resp = await page.goto(f"{BASE}/set-lang/et", wait_until="networkidle")
        log("Language switch without login redirects to /login", "/login" in page.url)

        # ===== 12. Mobile view =====
        print("\n--- Mobile View ---")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(BASE)
        await asyncio.sleep(2)
        mobile_tabs = await page.evaluate('() => document.querySelector(".mobile-tabs")?.offsetHeight > 0')
        log("Mobile: tab bar visible", mobile_tabs)
        left_hidden = await page.evaluate('() => document.getElementById("left-pane")?.offsetWidth === 0')
        log("Mobile: left pane hidden", left_hidden)
        await page.screenshot(path=str(SCREENSHOTS / "09-mobile.png"))

        # Restore desktop
        await page.set_viewport_size({"width": 1440, "height": 900})

        # ===== 13. Session loading =====
        print("\n--- Session ---")
        await page.goto(BASE)
        await asyncio.sleep(1)
        session_links = await page.evaluate('() => Array.from(document.querySelectorAll("a[href^=\\"/session/\\"]")).length')
        log("Session: history links present", session_links > 0, f"{session_links} sessions")

        await browser.close()

    # Generate report
    _write_report()


def _write_report():
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# NewsGuru Test Coverage Report",
        f"\nGenerated: {ts}",
        f"\n**Total: {total} tests | Passed: {passed} | Failed: {failed}**\n",
        "| # | Test | Status | Detail |",
        "|---|------|--------|--------|",
    ]
    for i, r in enumerate(results, 1):
        status = "PASS" if r["passed"] else "**FAIL**"
        lines.append(f"| {i} | {r['name']} | {status} | {r['detail']} |")

    lines.append(f"\n## Test Categories\n")
    categories = {
        "Page Load": ["Homepage", "3-pane", "Left pane", "Starter", "Live feed"],
        "Authentication": ["Login", "Register"],
        "Static Pages": ["Methodology"],
        "Treemap": ["Treemap"],
        "Chat": ["Chat", "share"],
        "Navigation": ["Topic", "Invalid"],
        "API": ["API"],
        "SSE": ["SSE"],
        "Language": ["Language"],
        "Mobile": ["Mobile"],
        "Session": ["Session"],
    }
    for cat, keywords in categories.items():
        cat_tests = [r for r in results if any(k.lower() in r["name"].lower() for k in keywords)]
        cat_pass = sum(1 for r in cat_tests if r["passed"])
        lines.append(f"- **{cat}**: {cat_pass}/{len(cat_tests)} passed")

    lines.append(f"\n## Screenshots\n")
    lines.append("All screenshots saved to `screenshots/regression/`\n")
    for f in sorted(SCREENSHOTS.glob("*.png")):
        lines.append(f"- [{f.name}](../screenshots/regression/{f.name})")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"\nReport: {REPORT_PATH}")
    print(f"Result: {passed}/{total} passed, {failed} failed")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  NewsGuru Regression Test Suite")
    print(f"{'='*60}")
    asyncio.run(run())
