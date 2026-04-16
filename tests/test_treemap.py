"""Test treemap rendering with Playwright — 5 iterations."""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:5020"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== Iteration 1: Standalone treemap page =====
        print("Iter 1: Standalone /treemap-chart page...")
        await page.goto(f"{BASE}/treemap-chart")
        await asyncio.sleep(4)
        has_plotly = await page.evaluate('() => !!document.querySelector(".js-plotly-plot")')
        await page.screenshot(path="screenshots/iter1-treemap-standalone.png")
        print(f"  Plotly rendered: {has_plotly}")

        # ===== Iteration 2: Trigger heatmap from chat =====
        print("Iter 2: Trigger heatmap in chat...")
        await page.goto(BASE)
        await asyncio.sleep(2)
        await page.evaluate("""() => {
            document.getElementById('chat-input').value='heatmap';
            document.getElementById('chat-input').form.requestSubmit();
        }""")
        await asyncio.sleep(6)
        has_iframe = await page.evaluate('() => !!document.querySelector("iframe[src=\\"/treemap-chart\\"]")')
        await page.screenshot(path="screenshots/iter2-heatmap-in-chat.png")
        print(f"  Iframe present: {has_iframe}")

        # ===== Iteration 3: Check iframe content =====
        print("Iter 3: Check iframe loaded...")
        if has_iframe:
            frame = page.frame(url="**/treemap-chart")
            if frame:
                await asyncio.sleep(3)
                has_chart = await frame.evaluate('() => !!document.querySelector(".js-plotly-plot")')
                print(f"  Chart inside iframe: {has_chart}")
            else:
                print("  Frame not accessible")
        await page.evaluate('() => { var c=document.getElementById("chat-messages"); if(c) c.scrollTop=c.scrollHeight; }')
        await asyncio.sleep(1)
        await page.screenshot(path="screenshots/iter3-heatmap-scrolled.png")

        # ===== Iteration 4: Full page with headlines =====
        print("Iter 4: Check headlines below chart...")
        headlines_text = await page.evaluate('() => document.body.innerText.includes("Top Stories")')
        await page.screenshot(path="screenshots/iter4-headlines.png")
        print(f"  Has 'Top Stories': {headlines_text}")

        # ===== Iteration 5: Verify 3-pane layout intact =====
        print("Iter 5: Verify 3-pane layout...")
        left = await page.evaluate('() => document.getElementById("left-pane")?.offsetWidth > 0')
        right = await page.evaluate('() => document.getElementById("right-pane")?.offsetWidth > 0')
        chat_input = await page.evaluate('() => !!document.getElementById("chat-input")')
        await page.screenshot(path="screenshots/iter5-layout-check.png")
        print(f"  Left pane: {left}, Right pane: {right}, Chat input: {chat_input}")

        await browser.close()
        print("\nDone! Check screenshots/iter*.png")

asyncio.run(run())
