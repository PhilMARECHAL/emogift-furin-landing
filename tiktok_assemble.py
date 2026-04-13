#!/usr/bin/env python3
"""
EmoGift Furin — TikTok "Emotional Payoff First" Assembly Script
================================================================
Assembles 6 UGC-style shots into a 30-second TikTok video with:
  - Reordered "hook first" timeline (Shot4 opener -> flashback -> climax)
  - Burned-in TikTok-style text overlays (drawtext with PIL fallback)
  - Audio mix: UGC ambient + furin tinkle bookends
  - White flash transitions at key moments
  - H.264 High / CRF 18 / 1080x1920 / 30fps final encode

Usage:
  python tiktok_assemble.py --output tiktok_final.mp4
  python tiktok_assemble.py --output tiktok_final.mp4 --no-text
  python tiktok_assemble.py --output tiktok_final.mp4 --shots-dir video_final --audio-dir audio
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("tiktok_assemble")

# ---------------------------------------------------------------------------
# Timeline definition
# ---------------------------------------------------------------------------
# Each segment: (shot_number, start_in_shot, end_in_shot, timeline_start, timeline_end, description)
TIMELINE = [
    (4, 0.0, 2.0, 0.0,  2.0,  "HOOK: mother's face, emotion peak — tight crop"),
    # 2.0-3.5 is flash + text overlay gap; filled by Shot1 start padded
    (1, 0.0, 3.0, 3.5,  6.5,  "Wrapping the furin, hands close-up"),
    (3, 0.0, 3.5, 6.5,  10.0, "Daughter selfie recording message"),
    # 10.0-11.5 is flash + text overlay gap; filled by Shot2 start padded
    (2, 0.0, 4.5, 11.5, 16.0, "Mother unwrapping, anticipation"),
    (4, 0.0, 5.0, 16.0, 22.0, "Mother's emotional reaction — FULL CLIMAX (6s)"),
    (5, 0.0, 4.0, 22.0, 26.0, "Mother watching video on phone, crying"),
    (6, 0.0, 4.0, 26.0, 30.0, "Furin on balcony + CTA"),
]

TOTAL_DURATION = 30.0

# Text overlays: (text, start_time, end_time, y_position_expr, fontsize)
TEXT_OVERLAYS = [
    ("POV: tu filmes ta mere quand elle decouvre ton cadeau", 0.0, 2.0, "h*0.12", 42),
    ("Retour en arriere...", 2.0, 3.5, "h*0.45", 52),
    ("Le jour de la fete des meres...", 10.0, 11.5, "h*0.45", 52),
    ("emogift.com - 49E | Lien dans la bio", 26.5, 30.0, "h*0.82", 44),
    ("Enregistre avant la fete des meres", 27.0, 30.0, "h*0.88", 38),
]

# Flash transitions: (time, duration_frames)
FLASH_TRANSITIONS = [
    (2.0, 3),   # After hook
    (10.0, 3),  # Before reveal
]


def run_ffmpeg(cmd, description=""):
    """Run an FFmpeg command with logging and error handling."""
    if description:
        log.info(description)
    log.debug("CMD: %s", " ".join(str(c) for c in cmd))
    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result
    except subprocess.CalledProcessError as e:
        log.error("FFmpeg failed: %s", e.stderr[-500:] if e.stderr else str(e))
        raise
    except subprocess.TimeoutExpired:
        log.error("FFmpeg timed out after 300s")
        raise


def probe_duration(filepath):
    """Get duration of a media file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(filepath)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# Step 1: Extract and trim segments from shots
# ---------------------------------------------------------------------------
def extract_segments(shots_dir, tmp_dir):
    """Extract each timeline segment from source shots, trimmed to length."""
    segments = []
    for i, (shot_num, ss, to_end, tl_start, tl_end, desc) in enumerate(TIMELINE):
        shot_path = shots_dir / f"shot{shot_num}_final.mp4"
        if not shot_path.exists():
            log.error("Missing shot: %s", shot_path)
            sys.exit(1)

        duration = tl_end - tl_start
        seg_path = Path(tmp_dir) / f"seg_{i:02d}.mp4"

        # For segment 0 (hook), crop tighter on face: zoom to 70% center
        if i == 0:
            run_ffmpeg([
                "ffmpeg", "-y", "-ss", str(ss), "-t", str(duration),
                "-i", str(shot_path),
                "-vf", "crop=iw*0.7:ih*0.7:(iw*0.15):(ih*0.10),scale=1080:1920:flags=lanczos",
                "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-r", "30", "-pix_fmt", "yuv420p",
                str(seg_path),
            ], f"Segment {i}: {desc} (shot{shot_num}, {duration:.1f}s, tight crop)")
        else:
            run_ffmpeg([
                "ffmpeg", "-y", "-ss", str(ss), "-t", str(duration),
                "-i", str(shot_path),
                "-vf", "scale=1080:1920:flags=lanczos",
                "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-r", "30", "-pix_fmt", "yuv420p",
                str(seg_path),
            ], f"Segment {i}: {desc} (shot{shot_num}, {duration:.1f}s)")

        segments.append(seg_path)
    return segments


# ---------------------------------------------------------------------------
# Step 2: Create flash transition frames
# ---------------------------------------------------------------------------
def create_flash_clip(tmp_dir, flash_idx, duration_frames=3, fps=30):
    """Create a short white flash clip (semi-transparent white frames)."""
    duration = duration_frames / fps
    flash_path = Path(tmp_dir) / f"flash_{flash_idx}.mp4"
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=white:s=1080x1920:d={duration}:r={fps}",
        "-f", "lavfi", "-i",
        f"anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(flash_path),
    ], f"Flash transition #{flash_idx} ({duration_frames} frames)")
    return flash_path


# ---------------------------------------------------------------------------
# Step 3: Concatenate all segments with flashes
# ---------------------------------------------------------------------------
def concatenate_segments(segments, flash_clips, tmp_dir):
    """Concatenate segments in order, inserting flash clips at transition points.

    Timeline:
      seg0 (0.0-2.0)  -> flash0 -> seg1 (3.5-6.5) -> seg2 (6.5-10.0) -> flash1
      -> seg3 (11.5-16.0) -> seg4 (16.0-22.0) -> seg5 (22.0-26.0) -> seg6 (26.0-30.0)

    The flashes fill the 2.0-3.5 and 10.0-11.5 gaps with:
      - flash (0.1s) + hold/padding from next segment's trim
    We handle the gap by creating a 1.5s bridging clip for each gap.
    """
    # Create bridge clips for the two gaps (2.0-3.5s and 10.0-11.5s)
    # Each bridge: short flash (0.1s) then a blank/black hold
    bridge0_path = Path(tmp_dir) / "bridge_0.mp4"
    bridge1_path = Path(tmp_dir) / "bridge_1.mp4"

    for idx, bridge_path in enumerate([(bridge0_path, 1.5), (bridge1_path, 1.5)]):
        path, dur = bridge_path
        flash_dur = 3 / 30  # 3 frames
        black_dur = dur - flash_dur

        # Create flash + black bridge
        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=white:s=1080x1920:d={flash_dur}:r=30",
            "-f", "lavfi", "-i",
            f"color=c=black:s=1080x1920:d={black_dur}:r=30",
            "-f", "lavfi", "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            f"[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-map", "2:a",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "16",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(path),
        ], f"Bridge clip {idx} ({dur}s: flash + black)")

    # Build concat list: seg0 -> bridge0 -> seg1 -> seg2 -> bridge1 -> seg3..seg6
    ordered = [
        segments[0],    # 0.0-2.0
        bridge0_path,   # 2.0-3.5 (flash + text gap)
        segments[1],    # 3.5-6.5
        segments[2],    # 6.5-10.0
        bridge1_path,   # 10.0-11.5 (flash + text gap)
        segments[3],    # 11.5-16.0
        segments[4],    # 16.0-22.0
        segments[5],    # 22.0-26.0
        segments[6],    # 26.0-30.0
    ]

    concat_list_path = Path(tmp_dir) / "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for seg in ordered:
            # FFmpeg concat demuxer needs forward slashes and escaped quotes
            safe_path = str(seg).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    concat_path = Path(tmp_dir) / "concat_raw.mp4"
    run_ffmpeg([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-r", "30", "-pix_fmt", "yuv420p",
        str(concat_path),
    ], "Concatenating all segments + bridges")

    return concat_path


# ---------------------------------------------------------------------------
# Step 4: Text overlays — drawtext with PIL fallback
# ---------------------------------------------------------------------------
def try_drawtext(input_path, output_path, overlays):
    """Try FFmpeg drawtext filter for all overlays at once."""
    vf_parts = []
    for text, start, end, y_expr, fontsize in overlays:
        # Escape special chars for drawtext
        escaped = text.replace("'", "\\'").replace(":", "\\:")
        vf_parts.append(
            f"drawtext=text='{escaped}'"
            f":fontfile='C\\:/Windows/Fonts/arialbd.ttf'"
            f":fontsize={fontsize}"
            f":fontcolor=white"
            f":borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y={y_expr}"
            f":enable='between(t,{start},{end})'"
        )
    vf_chain = ",".join(vf_parts)

    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", vf_chain,
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-c:a", "copy",
        "-r", "30", "-pix_fmt", "yuv420p",
        str(output_path),
    ], "Applying text overlays (drawtext)")


def pil_text_overlay_fallback(input_path, output_path, overlays, tmp_dir):
    """Fallback: render text overlays using PIL, then composite with FFmpeg."""
    from PIL import Image, ImageDraw, ImageFont
    log.info("Using PIL fallback for text overlays")

    WIDTH, HEIGHT = 1080, 1920

    # Try to load a bold font
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    def get_font(size):
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    overlay_inputs = []
    filter_parts = []

    for idx, (text, start, end, y_expr, fontsize) in enumerate(overlays):
        # Evaluate y position
        y_val = eval(y_expr, {"h": HEIGHT})
        y_pos = int(y_val)

        # Create transparent PNG with text
        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = get_font(fontsize)

        # Measure text
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x_pos = (WIDTH - tw) // 2

        # Draw shadow/outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    draw.text((x_pos + dx, y_pos + dy), text, fill=(0, 0, 0, 220), font=font)
        # Draw main text
        draw.text((x_pos, y_pos), text, fill=(255, 255, 255, 255), font=font)

        overlay_path = Path(tmp_dir) / f"text_overlay_{idx}.png"
        img.save(str(overlay_path))
        overlay_inputs.extend(["-i", str(overlay_path)])

        # Build filter: overlay this PNG with enable timing
        if idx == 0:
            prev = "[0:v]"
        else:
            prev = f"[tmp{idx}]"

        next_label = f"[tmp{idx + 1}]" if idx < len(overlays) - 1 else "[outv]"
        filter_parts.append(
            f"{prev}[{idx + 1}:v]overlay=0:0:enable='between(t,{start},{end})'{next_label}"
        )

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        *overlay_inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-c:a", "copy",
        "-r", "30", "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    run_ffmpeg(cmd, "Applying text overlays (PIL fallback)")


def apply_text_overlays(input_path, output_path, overlays, tmp_dir):
    """Apply text overlays with drawtext, falling back to PIL if it fails."""
    try:
        try_drawtext(input_path, output_path, overlays)
        log.info("drawtext succeeded")
    except Exception as e:
        log.warning("drawtext failed (%s), trying PIL fallback...", e)
        pil_text_overlay_fallback(input_path, output_path, overlays, tmp_dir)


# ---------------------------------------------------------------------------
# Step 5: Audio mix — UGC ambient + furin bookends
# ---------------------------------------------------------------------------
def mix_audio(video_path, audio_dir, output_path, tmp_dir):
    """Mix audio: keep UGC audio from video, add furin tinkle at 0s and 26s."""
    furin_path = audio_dir / "furin.wav"
    if not furin_path.exists():
        log.warning("furin.wav not found, skipping furin overlay")
        shutil.copy2(str(video_path), str(output_path))
        return

    furin_dur = probe_duration(furin_path)

    # Complex filter:
    # [0:a] = video's UGC audio (main)
    # [1:a] = furin at 0s (opening, moderate volume)
    # [2:a] = furin at 26s (closing, louder)
    #
    # Volume ducking during text overlay moments (0-2s, 2-3.5s, 10-11.5s)
    # by slightly reducing UGC audio at those points
    filter_complex = (
        # Delay furin for closing: 26 seconds = 26000ms
        f"[1:a]volume=0.6,apad=whole_dur={TOTAL_DURATION}[furin_open];"
        f"[2:a]volume=0.85,adelay=26000|26000,apad=whole_dur={TOTAL_DURATION}[furin_close];"
        # Main audio with subtle ducking during text overlays
        f"[0:a]volume='if(between(t,0,3.5),0.7,if(between(t,10,11.5),0.7,1.0))':eval=frame[main_ducked];"
        # Mix all three
        f"[main_ducked][furin_open][furin_close]amix=inputs=3:duration=first:dropout_transition=2,"
        # Normalize to -14 LUFS (TikTok standard)
        f"loudnorm=I=-14:TP=-1:LRA=11[aout]"
    )

    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(furin_path),
        "-i", str(furin_path),
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        str(output_path),
    ], "Mixing audio: UGC + furin bookends + loudnorm -14 LUFS")


# ---------------------------------------------------------------------------
# Step 6: Final encode — production quality
# ---------------------------------------------------------------------------
def final_encode(input_path, output_path):
    """Final encode pass: H.264 High, CRF 18, AAC 256k, faststart."""
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(input_path),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
        "-preset", "slow", "-crf", "18",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        "-t", str(TOTAL_DURATION),
        str(output_path),
    ], "Final encode: H.264 High / CRF 18 / AAC 256k / faststart")


# ---------------------------------------------------------------------------
# Main assembly pipeline
# ---------------------------------------------------------------------------
def assemble_tiktok(shots_dir, audio_dir, output_path, no_text=False):
    """Full assembly pipeline for the TikTok video."""
    shots_dir = Path(shots_dir)
    audio_dir = Path(audio_dir)
    output_path = Path(output_path)

    # Validate inputs
    for i in range(1, 7):
        p = shots_dir / f"shot{i}_final.mp4"
        if not p.exists():
            log.error("Missing: %s", p)
            sys.exit(1)
    log.info("All 6 shots found in %s", shots_dir)

    with tempfile.TemporaryDirectory(prefix="emogift_tiktok_") as tmp_dir:
        log.info("Temp dir: %s", tmp_dir)

        # Step 1: Extract and trim segments
        log.info("=" * 60)
        log.info("STEP 1: Extracting and trimming segments")
        log.info("=" * 60)
        segments = extract_segments(shots_dir, tmp_dir)

        # Step 2: Concatenate with flash transitions
        log.info("=" * 60)
        log.info("STEP 2: Concatenating segments with flash transitions")
        log.info("=" * 60)
        concat_path = concatenate_segments(segments, [], tmp_dir)

        # Step 3: Text overlays (unless --no-text)
        if no_text:
            log.info("Skipping text overlays (--no-text)")
            text_path = concat_path
        else:
            log.info("=" * 60)
            log.info("STEP 3: Applying text overlays")
            log.info("=" * 60)
            text_path = Path(tmp_dir) / "with_text.mp4"
            apply_text_overlays(concat_path, text_path, TEXT_OVERLAYS, tmp_dir)

        # Step 4: Audio mix
        log.info("=" * 60)
        log.info("STEP 4: Mixing audio (UGC + furin bookends)")
        log.info("=" * 60)
        audio_path = Path(tmp_dir) / "with_audio.mp4"
        mix_audio(text_path, audio_dir, audio_path, tmp_dir)

        # Step 5: Final encode
        log.info("=" * 60)
        log.info("STEP 5: Final encode")
        log.info("=" * 60)
        final_encode(audio_path, output_path)

    # Report
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        duration = probe_duration(output_path)
        log.info("=" * 60)
        log.info("SUCCESS: %s", output_path)
        log.info("  Size: %.1f MB", size_mb)
        log.info("  Duration: %.1f seconds", duration)
        log.info("  Target: 15-20 MB (TikTok upload quality)")
        if size_mb > 25:
            log.warning("  File is larger than expected. Consider raising CRF to 20.")
        log.info("=" * 60)
    else:
        log.error("Output file was not created!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="EmoGift Furin TikTok Assembly — Emotional Payoff First (30s)"
    )
    parser.add_argument(
        "--output", "-o",
        default="tiktok_final.mp4",
        help="Output filename (default: tiktok_final.mp4)",
    )
    parser.add_argument(
        "--shots-dir",
        default=None,
        help="Directory containing shot1_final.mp4..shot6_final.mp4",
    )
    parser.add_argument(
        "--audio-dir",
        default=None,
        help="Directory containing furin.wav and ambiance files",
    )
    parser.add_argument(
        "--no-text",
        action="store_true",
        help="Skip text overlays (clean version)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve directories relative to script location
    script_dir = Path(__file__).resolve().parent
    shots_dir = Path(args.shots_dir) if args.shots_dir else script_dir / "video_final"
    audio_dir = Path(args.audio_dir) if args.audio_dir else script_dir / "audio"
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = script_dir / output_path

    log.info("EmoGift Furin TikTok Assembly")
    log.info("  Shots:  %s", shots_dir)
    log.info("  Audio:  %s", audio_dir)
    log.info("  Output: %s", output_path)
    log.info("  Text:   %s", "OFF" if args.no_text else "ON")

    assemble_tiktok(shots_dir, audio_dir, output_path, no_text=args.no_text)


if __name__ == "__main__":
    main()
