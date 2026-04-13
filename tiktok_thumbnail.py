#!/usr/bin/env python3
"""
Expert 9 — TikTok Thumbnail / Cover Frame Designer
Extracts emotionally compelling frames from Shot 4 and creates cover candidates
with text overlays optimized for TikTok profile grid and search results.

Usage:
    python tiktok_thumbnail.py --input video_final/shot4_final.mp4 --output-dir output/tiktok_covers/
"""

import argparse
import subprocess
import json
import os
from pathlib import Path


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def extract_frame(video_path: str, timestamp: float, output_path: str):
    """Extract a single frame at the given timestamp."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "1",  # highest JPEG quality from ffmpeg
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"  Extracted frame at {timestamp:.2f}s -> {output_path}")


def add_price_overlay(input_path: str, output_path: str):
    """
    Add a subtle price tag overlay in the bottom-right corner.
    Text: emoji + 49 euros, white with dark shadow for readability.
    Uses Pillow for precise text placement.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(input_path)
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Try to load a bold font, fall back to default
    text = "\U0001f97a 49\u20ac"  # 🥺 49€
    font_size = 72
    font = None
    for font_name in [
        "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold (Windows)
        "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold
        "C:/Windows/Fonts/segoeui.ttf",     # Segoe UI Regular
        "C:/Windows/Fonts/arial.ttf",       # Arial Regular
    ]:
        if os.path.exists(font_name):
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    # Position: bottom-right with padding
    # Use textbbox for accurate sizing
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    padding = 40
    x = w - text_w - padding
    y = h - text_h - padding - 80  # extra offset to stay above TikTok UI

    # Draw shadow for readability (offset by 3px)
    shadow_color = (0, 0, 0, 200)
    for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (0, 3), (3, 0)]:
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))

    # Draw main text in white
    draw.text((x, y), text, font=font, fill=(255, 255, 255))

    img.save(output_path, "JPEG", quality=95)
    print(f"  Added price overlay -> {output_path}")


def add_pov_overlay(input_path: str, output_path: str):
    """
    Add 'POV: son cadeau la fait pleurer' text overlay for profile grid version.
    Centered text with semi-transparent background band.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(input_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size

    # Load font
    font_size = 52
    font = None
    for font_name in [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        if os.path.exists(font_name):
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    text_line1 = "POV:"
    text_line2 = "son cadeau"
    text_line3 = "la fait pleurer"

    lines = [text_line1, text_line2, text_line3]
    line_bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [bb[3] - bb[1] for bb in line_bboxes]
    line_widths = [bb[2] - bb[0] for bb in line_bboxes]
    line_spacing = 12
    total_text_h = sum(line_heights) + line_spacing * (len(lines) - 1)
    max_text_w = max(line_widths)

    # Position: upper third of image (visible on profile grid which crops to square center)
    band_y = int(h * 0.30) - total_text_h // 2
    band_padding = 24

    # Semi-transparent dark band behind text
    draw.rectangle(
        [0, band_y - band_padding, w, band_y + total_text_h + band_padding],
        fill=(0, 0, 0, 140)
    )

    # Draw each line centered
    current_y = band_y
    for i, line in enumerate(lines):
        lw = line_widths[i]
        lx = (w - lw) // 2
        # Shadow
        for dx, dy in [(-2, 2), (2, 2), (2, -2), (-2, -2)]:
            draw.text((lx + dx, current_y + dy), line, font=font, fill=(0, 0, 0, 220))
        # Main text
        draw.text((lx, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += line_heights[i] + line_spacing

    # Composite and save as RGB JPEG
    composited = Image.alpha_composite(img, overlay).convert("RGB")
    composited.save(output_path, "JPEG", quality=95)
    print(f"  Added POV overlay -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="TikTok Thumbnail/Cover Frame Designer")
    parser.add_argument("--input", required=True, help="Path to Shot 4 video (mother's emotion)")
    parser.add_argument("--output-dir", required=True, help="Output directory for cover candidates")
    args = parser.parse_args()

    video_path = args.input
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(video_path):
        print(f"ERROR: Input video not found: {video_path}")
        return

    # Step 1: Get video duration
    duration = get_video_duration(video_path)
    print(f"Shot 4 duration: {duration:.2f}s")

    # Step 2: Extract frames at 5 timestamps (25%, 40%, 50%, 60%, 75%)
    percentages = [0.25, 0.40, 0.50, 0.60, 0.75]
    raw_frames = []

    print("\n--- Extracting candidate frames ---")
    for i, pct in enumerate(percentages, 1):
        ts = duration * pct
        raw_path = str(output_dir / f"_raw_frame_{i}.jpg")
        extract_frame(video_path, ts, raw_path)
        raw_frames.append(raw_path)

    # Step 3: Create cover candidates with price overlay
    print("\n--- Creating price overlay covers ---")
    for i, raw_path in enumerate(raw_frames, 1):
        cover_path = str(output_dir / f"tiktok_cover_{i}.jpg")
        add_price_overlay(raw_path, cover_path)

    # Step 4: Create POV overlay version (using the 50% frame as the best default)
    print("\n--- Creating POV overlay version ---")
    best_raw = raw_frames[2]  # 50% mark — typically peak emotion
    pov_path = str(output_dir / "tiktok_cover_pov.jpg")
    add_pov_overlay(best_raw, pov_path)

    # Also create POV versions for all candidates
    for i, raw_path in enumerate(raw_frames, 1):
        pov_variant = str(output_dir / f"tiktok_cover_pov_{i}.jpg")
        add_pov_overlay(raw_path, pov_variant)

    # Cleanup raw frames
    for raw_path in raw_frames:
        os.remove(raw_path)

    print(f"\n=== DONE ===")
    print(f"Output directory: {output_dir}")
    print(f"  tiktok_cover_1.jpg through tiktok_cover_5.jpg  (price overlay)")
    print(f"  tiktok_cover_pov.jpg                           (POV text, best frame)")
    print(f"  tiktok_cover_pov_1.jpg through pov_5.jpg       (POV text, all candidates)")
    print(f"\nReview all candidates and pick the one with the most visible emotion.")
    print(f"Look for: tears, open mouth, hand near face, strong lighting on face.")


if __name__ == "__main__":
    main()
