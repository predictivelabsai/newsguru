"""
Capture NewsGuru Product Demo Video

Playwright script that walks through the entire NewsGuru platform,
capturing frames for an animated GIF and MP4 video.

Usage:
    python main.py &
    python tests/capture_video.py

Output:
    docs/demo_video.mp4
    docs/demo_video.gif
    docs/frames/*.png
"""

import asyncio
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRAMES_DIR = ROOT / "docs" / "frames"
BASE_URL = "http://localhost:5020"

frame_num = 0


async def capture(page, label, pause=1.0):
    """Capture a frame with a pause for natural pacing."""
    global frame_num
    await asyncio.sleep(pause)
    path = FRAMES_DIR / f"{frame_num:03d}_{label}.png"
    await page.screenshot(path=str(path), type="png")
    print(f"  [{frame_num:03d}] {label}")
    frame_num += 1


async def run():
    from playwright.async_api import async_playwright

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== HOME PAGE =====
        await page.goto(BASE_URL)
        await asyncio.sleep(2)
        await capture(page, "homepage", 1.5)

        # ===== LOGIN PAGE =====
        await page.goto(f"{BASE_URL}/login")
        await asyncio.sleep(1)
        await capture(page, "login_page", 0.5)

        # ===== REGISTER PAGE =====
        await page.goto(f"{BASE_URL}/register")
        await asyncio.sleep(1)
        await capture(page, "register_page", 0.5)

        # ===== CHAT: News & Politics =====
        await page.goto(f"{BASE_URL}/chat/politics")
        await asyncio.sleep(2)
        await capture(page, "chat_politics_welcome", 1.0)

        # Send a message
        chat_input = page.locator('input[name="msg"]')
        await chat_input.fill("What are the top political headlines today?")
        await capture(page, "chat_politics_typed", 0.5)

        await page.click('button[type="submit"]')
        await asyncio.sleep(2)
        await capture(page, "chat_politics_thinking", 1.0)

        # Wait for response
        await asyncio.sleep(15)
        await capture(page, "chat_politics_response", 1.5)

        # ===== CHAT: Business & Tech =====
        await page.goto(f"{BASE_URL}/chat/technology")
        await asyncio.sleep(2)
        await capture(page, "chat_tech_welcome", 1.0)

        await chat_input.fill("Search for the latest AI news")
        await page.click('button[type="submit"]')
        await asyncio.sleep(2)
        await capture(page, "chat_tech_thinking", 1.0)

        await asyncio.sleep(15)
        await capture(page, "chat_tech_response", 1.5)

        # ===== HOME: Config Sources =====
        await page.goto(BASE_URL)
        await asyncio.sleep(2)

        # Open config
        config_toggle = page.locator("summary")
        await config_toggle.click()
        await asyncio.sleep(1)
        await capture(page, "config_sources", 1.0)

        # ===== MOBILE VIEW =====
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(BASE_URL)
        await asyncio.sleep(2)
        await capture(page, "mobile_homepage", 1.0)

        await page.goto(f"{BASE_URL}/chat/politics")
        await asyncio.sleep(2)
        await capture(page, "mobile_chat", 1.0)

        # ===== BACK TO DESKTOP =====
        await page.set_viewport_size({"width": 1440, "height": 900})
        await page.goto(BASE_URL)
        await asyncio.sleep(2)
        await capture(page, "final_homepage", 1.5)

        await browser.close()

    print(f"\n  Captured {frame_num} frames to docs/frames/")


def build_video():
    """Assemble frames into MP4 video and GIF."""
    from PIL import Image
    import av
    import numpy as np

    frames = sorted(FRAMES_DIR.glob("*.png"))
    if not frames:
        print("No frames found!")
        return

    images = [np.array(Image.open(f)) for f in frames]
    print(f"  Building video from {len(images)} frames...")

    # --- MP4 ---
    mp4_path = ROOT / "docs" / "demo_video.mp4"
    fps = 2
    hold_frames = 3  # each screenshot held for 1.5 seconds

    container = av.open(str(mp4_path), mode="w")
    h, w = images[0].shape[:2]
    w_enc = w if w % 2 == 0 else w - 1
    h_enc = h if h % 2 == 0 else h - 1
    stream = container.add_stream("libx264", rate=fps)
    stream.width = w_enc
    stream.height = h_enc
    stream.pix_fmt = "yuv420p"

    for img in images:
        img_cropped = img[:h_enc, :w_enc, :3]
        frame = av.VideoFrame.from_ndarray(img_cropped, format="rgb24")
        for _ in range(hold_frames):
            for packet in stream.encode(frame):
                container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)
    container.close()
    total_secs = len(images) * hold_frames / fps
    print(f"  Saved MP4: {mp4_path} ({total_secs:.0f}s)")

    # --- GIF ---
    gif_path = ROOT / "docs" / "demo_video.gif"
    pil_frames = []
    for img in images:
        pil_img = Image.fromarray(img[:, :, :3])
        pil_img = pil_img.resize((w // 2, h // 2), Image.LANCZOS)
        pil_frames.append(pil_img)

    pil_frames[0].save(
        str(gif_path), save_all=True, append_images=pil_frames[1:],
        duration=1500, loop=0, optimize=True,
    )
    print(f"  Saved GIF: {gif_path}")


def main():
    print(f"\n{'='*60}")
    print(f"  NewsGuru Product Demo -- Video Capture")
    print(f"{'='*60}\n")

    asyncio.run(run())

    print(f"\n{'='*60}")
    print(f"  Building video and GIF...")
    print(f"{'='*60}\n")

    build_video()

    print(f"\n  Done!")
    print(f"  MP4: docs/demo_video.mp4")
    print(f"  GIF: docs/demo_video.gif")
    print(f"  Frames: docs/frames/\n")


if __name__ == "__main__":
    main()
