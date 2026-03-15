"""Generate TikTok integration demo video using PIL + ffmpeg."""
import subprocess
import os
import shutil
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 30
OUT = "/tmp/demo_video"
FINAL = "/app/media/tiktok_demo.mp4"

# Colors
BG = "#f5f5f5"
DARK = "#111111"
WHITE = "#ffffff"
RED = "#fe2c55"
GREEN = "#4caf50"
GRAY = "#666666"
LIGHT_GRAY = "#e0e0e0"
CARD_BG = "#ffffff"

os.makedirs(OUT, exist_ok=True)


def get_font(size, bold=False):
    """Try to load a decent font."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_header(draw):
    """Draw AIZAVOD header bar."""
    draw.rectangle([0, 0, W, 56], fill=DARK)
    f = get_font(22, bold=True)
    draw.text((30, 14), "AIZAVOD", fill=WHITE, font=f)
    f2 = get_font(13)
    draw.text((W - 180, 20), "admin@aizavod.com", fill="#aaaaaa", font=f2)


def draw_nav(draw, active="TikTok"):
    """Draw navigation bar."""
    draw.rectangle([0, 56, W, 96], fill="#1a1a1a")
    tabs = ["Dashboard", "Content", "TikTok", "Instagram", "Telegram", "Settings"]
    x = 30
    f = get_font(13)
    for tab in tabs:
        color = WHITE if tab == active else "#888888"
        draw.text((x, 70), tab, fill=color, font=f)
        if tab == active:
            bbox = f.getbbox(tab)
            tw = bbox[2] - bbox[0]
            draw.rectangle([x, 92, x + tw, 96], fill=RED)
        bbox = f.getbbox(tab)
        x += bbox[2] - bbox[0] + 40


def draw_steps(draw, active_step=1):
    """Draw step indicator."""
    f = get_font(12, bold=True)
    fl = get_font(11)
    labels = ["1  Connect", "2  Upload", "3  Publish"]
    sw = 250
    gap = 15
    start_x = (W - (sw * 3 + gap * 2)) // 2
    for i, label in enumerate(labels):
        x = start_x + i * (sw + gap)
        if i + 1 < active_step:
            bg, fg = "#e8f5e9", "#2e7d32"
        elif i + 1 == active_step:
            bg, fg = RED, WHITE
        else:
            bg, fg = "#eeeeee", "#999999"
        draw.rounded_rectangle([x, 115, x + sw, 155], radius=8, fill=bg)
        bbox = f.getbbox(label)
        tw = bbox[2] - bbox[0]
        draw.text((x + (sw - tw) // 2, 127), label, fill=fg, font=f)


def draw_card(draw, x, y, w, h):
    """Draw a white card."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=CARD_BG)


def draw_button(draw, x, y, w, h, text, color=RED):
    """Draw a button."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=color)
    f = get_font(14, bold=True)
    bbox = f.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2 - 2), text, fill=WHITE, font=f)


# ─── Frame generators ────────────────────────────────

def frame_step1_connect():
    """Step 1: Connect TikTok page."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_header(draw)
    draw_nav(draw)
    draw_steps(draw, 1)

    # Card
    draw_card(draw, 60, 175, W - 120, 200)
    f_title = get_font(18, bold=True)
    draw.text((90, 195), "Connect TikTok Account", fill=DARK, font=f_title)
    f_desc = get_font(14)
    draw.text((90, 230), "Link your TikTok account to publish videos directly", fill=GRAY, font=f_desc)
    draw.text((90, 252), "from AIZAVOD using the Content Posting API.", fill=GRAY, font=f_desc)

    # Status
    draw.rounded_rectangle([90, 290, 240, 316], radius=13, fill="#fce4ec")
    f_s = get_font(12, bold=True)
    draw.ellipse([100, 298, 108, 306], fill="#f44336")
    draw.text((114, 295), "Not connected", fill="#c62828", font=f_s)

    # Button
    draw_button(draw, W - 320, 285, 250, 42, "Connect TikTok Account", RED)

    return img


def frame_step1_redirecting():
    """Overlay: redirecting to TikTok."""
    img = frame_step1_connect()
    draw = ImageDraw.Draw(img)

    # Overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 160))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Modal
    mx, my, mw, mh = W // 2 - 200, H // 2 - 60, 400, 120
    draw.rounded_rectangle([mx, my, mx + mw, my + mh], radius=16, fill=WHITE)
    f1 = get_font(16, bold=True)
    f2 = get_font(13)
    draw.text((mx + 80, my + 30), "Redirecting to TikTok...", fill=DARK, font=f1)
    draw.text((mx + 50, my + 60), "Authorize AIZAVOD to access your account", fill=GRAY, font=f2)

    return img.convert("RGB")


def frame_step2_upload(file_selected=False, caption=True):
    """Step 2: Upload video form."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_header(draw)
    draw_nav(draw)
    draw_steps(draw, 2)

    # Account card
    draw_card(draw, 60, 175, W - 120, 90)
    f_title = get_font(16, bold=True)
    draw.text((90, 187), "TikTok Account", fill=DARK, font=f_title)
    # Avatar
    draw.ellipse([90, 215, 120, 245], fill=RED)
    f_av = get_font(14, bold=True)
    draw.text((99, 220), "N", fill=WHITE, font=f_av)
    f_name = get_font(14, bold=True)
    f_handle = get_font(12)
    draw.text((130, 215), "Nika Flex", fill=DARK, font=f_name)
    draw.text((130, 235), "@nika_flex_official", fill="#888888", font=f_handle)
    # Connected badge
    draw.rounded_rectangle([W - 230, 222, W - 110, 244], radius=11, fill="#e8f5e9")
    draw.ellipse([W - 222, 229, W - 214, 237], fill=GREEN)
    f_s = get_font(11, bold=True)
    draw.text((W - 208, 226), "Connected", fill="#2e7d32", font=f_s)

    # Upload card
    draw_card(draw, 60, 280, W - 120, 380)
    draw.text((90, 298), "Publish New Video", fill=DARK, font=f_title)

    if not file_selected:
        # Upload area (dashed border simulation)
        draw.rounded_rectangle([90, 330, W - 90, 430], radius=12, outline=LIGHT_GRAY, width=2)
        f_up = get_font(28)
        draw.text((W // 2 - 15, 345), "🎬", fill=DARK, font=f_up)
        f14 = get_font(14, bold=True)
        draw.text((W // 2 - 80, 385), "Click to select video file", fill=DARK, font=f14)
        f12 = get_font(11)
        draw.text((W // 2 - 65, 408), "MP4, MOV — max 50MB", fill="#999999", font=f12)
    else:
        # File selected
        draw.rounded_rectangle([90, 330, W - 90, 430], radius=12, outline=GREEN, width=2, fill="#f1f8e9")
        f_up = get_font(28)
        draw.text((W // 2 - 10, 348), "✅", fill=DARK, font=f_up)
        f14 = get_font(14, bold=True)
        draw.text((W // 2 - 80, 388), "workout_morning.mp4", fill=DARK, font=f14)
        f12 = get_font(11)
        draw.text((W // 2 - 20, 408), "12.4 MB", fill=GRAY, font=f12)

    if caption:
        # Caption field
        f_label = get_font(13, bold=True)
        draw.text((90, 445), "Caption", fill=DARK, font=f_label)
        draw.rounded_rectangle([90, 465, W - 90, 530], radius=8, outline=LIGHT_GRAY, width=1, fill=WHITE)
        f_cap = get_font(12)
        draw.text((100, 475), "Morning workout vibes  Who else starts", fill=DARK, font=f_cap)
        draw.text((100, 495), "their day like this? #fitness #motivation #fyp", fill=DARK, font=f_cap)

        # Privacy
        draw.text((90, 545), "Privacy Level", fill=DARK, font=f_label)
        draw.rounded_rectangle([90, 565, 280, 590], radius=8, outline=LIGHT_GRAY, width=1, fill=WHITE)
        draw.text((100, 569), "Public", fill=DARK, font=f_cap)

        # Checkboxes
        f_cb = get_font(11)
        draw.rectangle([90, 605, 102, 617], outline=GRAY, width=1)
        draw.text((92, 604), "✓", fill=GREEN, font=f_cb)
        draw.text((108, 605), "Allow comments", fill=DARK, font=f_cb)
        draw.rectangle([230, 605, 242, 617], outline=GRAY, width=1)
        draw.text((232, 604), "✓", fill=GREEN, font=f_cb)
        draw.text((248, 605), "Allow duet", fill=DARK, font=f_cb)
        draw.rectangle([350, 605, 362, 617], outline=GRAY, width=1)
        draw.text((352, 604), "✓", fill=GREEN, font=f_cb)
        draw.text((368, 605), "Allow stitch", fill=DARK, font=f_cb)

    # Publish button
    draw_button(draw, W - 260, 630, 190, 40, "Publish to TikTok", DARK)

    return img


def frame_step2_publishing(progress_pct):
    """Step 2 with progress bar."""
    img = frame_step2_upload(file_selected=True)
    draw = ImageDraw.Draw(img)

    # Cover the button area
    draw.rounded_rectangle([W - 260, 630, W - 70, 670], radius=8, fill="#cccccc")
    f = get_font(14, bold=True)
    draw.text((W - 230, 639), "Publishing...", fill=WHITE, font=f)

    # Progress bar
    bar_x, bar_y = 90, 620
    bar_w = W - 180
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 6], radius=3, fill="#eeeeee")
    fill_w = int(bar_w * progress_pct / 100)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 6], radius=3, fill=RED)

    return img


def frame_step3_success():
    """Step 3: Published successfully."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_header(draw)
    draw_nav(draw)
    draw_steps(draw, 4)  # all done

    # Account card
    draw_card(draw, 60, 175, W - 120, 90)
    f_title = get_font(16, bold=True)
    draw.text((90, 187), "TikTok Account", fill=DARK, font=f_title)
    draw.ellipse([90, 215, 120, 245], fill=RED)
    f_av = get_font(14, bold=True)
    draw.text((99, 220), "N", fill=WHITE, font=f_av)
    f_name = get_font(14, bold=True)
    f_handle = get_font(12)
    draw.text((130, 215), "Nika Flex", fill=DARK, font=f_name)
    draw.text((130, 235), "@nika_flex_official", fill="#888888", font=f_handle)
    draw.rounded_rectangle([W - 230, 222, W - 110, 244], radius=11, fill="#e8f5e9")
    draw.ellipse([W - 222, 229, W - 214, 237], fill=GREEN)
    f_s = get_font(11, bold=True)
    draw.text((W - 208, 226), "Connected", fill="#2e7d32", font=f_s)

    # Success card
    draw_card(draw, 60, 280, W - 120, 200)
    draw.text((90, 300), "Publish New Video", fill=DARK, font=f_title)

    # Success message
    draw.rounded_rectangle([90, 340, W - 90, 400], radius=8, fill="#e8f5e9")
    f_suc = get_font(14, bold=True)
    draw.text((110, 355), "Video published successfully!", fill="#2e7d32", font=f_suc)
    f_id = get_font(12)
    draw.text((110, 378), "TikTok publish_id: v_pub_28fka93md", fill="#2e7d32", font=f_id)

    # Published button
    draw.rounded_rectangle([W - 230, 430, W - 90, 465], radius=8, fill="#cccccc")
    f_btn = get_font(13, bold=True)
    draw.text((W - 200, 440), "Published!", fill=WHITE, font=f_btn)

    return img


def save_frame(img, idx):
    """Save frame as PNG."""
    path = os.path.join(OUT, f"frame_{idx:05d}.png")
    img.save(path)
    return path


def generate_frames():
    """Generate all frames."""
    idx = 0

    # Scene 1: Connect page (2 seconds)
    img = frame_step1_connect()
    for _ in range(FPS * 2):
        save_frame(img, idx)
        idx += 1

    # Scene 2: Click animation — button highlight (0.5 sec)
    for _ in range(FPS // 2):
        save_frame(img, idx)
        idx += 1

    # Scene 3: Redirecting overlay (2 seconds)
    img = frame_step1_redirecting()
    for _ in range(FPS * 2):
        save_frame(img, idx)
        idx += 1

    # Scene 4: Connected — upload form (2 seconds)
    img = frame_step2_upload(file_selected=False)
    for _ in range(FPS * 2):
        save_frame(img, idx)
        idx += 1

    # Scene 5: File selected (2 seconds)
    img = frame_step2_upload(file_selected=True)
    for _ in range(FPS * 2):
        save_frame(img, idx)
        idx += 1

    # Scene 6: Publishing progress (3 seconds)
    total_pub_frames = FPS * 3
    for i in range(total_pub_frames):
        pct = int(100 * i / total_pub_frames)
        img = frame_step2_publishing(pct)
        save_frame(img, idx)
        idx += 1

    # Scene 7: Success (3 seconds)
    img = frame_step3_success()
    for _ in range(FPS * 3):
        save_frame(img, idx)
        idx += 1

    return idx


print("Generating frames...")
total = generate_frames()
print(f"Generated {total} frames")

print("Encoding video with ffmpeg...")
subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(OUT, "frame_%05d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-preset", "fast",
    "-crf", "23",
    FINAL,
], check=True)

print(f"Video saved to {FINAL}")
size_mb = os.path.getsize(FINAL) / 1024 / 1024
print(f"Size: {size_mb:.1f} MB")

# Cleanup frames
shutil.rmtree(OUT)
print("Done!")
