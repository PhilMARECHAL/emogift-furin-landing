#!/usr/bin/env python3
"""
Expert 10 — Seamless Loop Engineer for TikTok
Creates a crossfade at the loop boundary so the video replays seamlessly.

Strategy:
  - The video starts with Shot 4 (emotional hook) and ends with Shot 6 (serene furin).
  - Last 0.5s of the video crossfades into the first 0.5s, so when TikTok loops
    the playback, viewers see a smooth transition from peaceful furin back to
    the emotional face — encouraging rewatches.

Technique:
  - Extract first 0.5s and last 0.5s as separate clips.
  - Create a blended crossfade segment (0.5s) from last->first.
  - Assemble: [crossfade 0.5s] + [middle portion] + [original last 0.5s kept for fade-out feel]
  - Actually: replace the last 0.5s with the crossfade so total duration stays the same.

Usage:
    python tiktok_loop.py --input tiktok_raw.mp4 --output tiktok_looped.mp4
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def get_video_info(video_path: str) -> dict:
    """Get video duration, fps, and codec info via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])

    # Find video stream for fps
    fps = 30.0
    for stream in info.get("streams", []):
        if stream["codec_type"] == "video":
            r_fps = stream.get("r_frame_rate", "30/1")
            num, den = r_fps.split("/")
            fps = float(num) / float(den)
            break

    return {"duration": duration, "fps": fps}


def run_ffmpeg(cmd: list, description: str = ""):
    """Run an ffmpeg command with error handling."""
    if description:
        print(f"  {description}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}")
        sys.exit(1)


def extract_frame_jpg(video_path: str, timestamp: float, output_path: str):
    """Extract a single frame as JPEG for visual comparison."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def create_looped_video(input_path: str, output_path: str, crossfade_dur: float = 0.5):
    """
    Create a seamlessly looping video using FFmpeg xfade filter.

    The approach:
    1. Split video into body (start to end-crossfade) and tail (last crossfade_dur).
    2. Also extract head (first crossfade_dur).
    3. Crossfade tail into head to create the transition segment.
    4. The final video = body + crossfaded_ending
       But since xfade shortens total by crossfade_dur, we duplicate the head
       at the end before applying xfade to maintain visual loop.

    Simpler FFmpeg approach:
    - Create two copies of the video offset, use xfade at the boundary.
    - Video A = original (plays full)
    - Video B = original (starts playing from beginning)
    - xfade at offset = duration - crossfade_dur
    - Then trim to original duration.
    """
    info = get_video_info(input_path)
    duration = info["duration"]
    fps = info["fps"]

    print(f"  Input duration: {duration:.3f}s, FPS: {fps:.2f}")
    print(f"  Crossfade duration: {crossfade_dur}s")

    output_dir = str(Path(output_path).parent) or "."
    temp_head = os.path.join(output_dir, "_loop_head.mp4")
    temp_body = os.path.join(output_dir, "_loop_body.mp4")
    temp_tail = os.path.join(output_dir, "_loop_tail.mp4")
    temp_xfade = os.path.join(output_dir, "_loop_xfade.mp4")
    temp_concat_list = os.path.join(output_dir, "_loop_concat.txt")

    xfade_offset = duration - crossfade_dur
    body_end = duration - crossfade_dur

    # Step 1: Extract head (first crossfade_dur seconds)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", f"{crossfade_dur:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",  # process video only for crossfade, re-add audio later
        temp_head
    ], f"Extracting head (0 to {crossfade_dur}s)")

    # Step 2: Extract body (from crossfade_dur to end-crossfade_dur)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", f"{crossfade_dur:.3f}",
        "-i", input_path,
        "-t", f"{body_end - crossfade_dur:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        temp_body
    ], f"Extracting body ({crossfade_dur}s to {body_end:.3f}s)")

    # Step 3: Extract tail (last crossfade_dur seconds)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", f"{xfade_offset:.3f}",
        "-i", input_path,
        "-t", f"{crossfade_dur:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        temp_tail
    ], f"Extracting tail ({xfade_offset:.3f}s to end)")

    # Step 4: Crossfade tail into head (tail plays, then fades into head)
    # xfade: transition at offset = tail_duration - crossfade_dur = 0
    # Since both clips are crossfade_dur long and we want full overlap,
    # we blend them frame-by-frame manually.
    # Using xfade with offset=0 and duration=crossfade_dur for full blend.
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", temp_tail,
        "-i", temp_head,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={crossfade_dur}:offset=0,format=yuv420p[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        temp_xfade
    ], "Creating crossfade segment (tail -> head)")

    # Step 5: Concatenate body + tail_original as the new video
    # Structure: [crossfade(tail->head)] + [body] + [tail]
    # But wait — the loop point is END->START. So the viewer sees:
    #   ... body ... tail --[TikTok loops]--> head ... body ... tail ...
    # We want tail->head to be smooth. So we replace the structure:
    #   [head] + [body] + [crossfade(tail->head)]
    # This way when it loops: ...crossfade_end(=head) -> head... seamless!
    # But the xfade segment ends on head's content, so:
    #   Final = [body] + [crossfade(tail->head)]
    # And xfade starts with tail content, ends with head content.
    # When TikTok loops: ...head_content -> body -> tail_fading_to_head -> head_content...
    # That's the seamless loop!

    # Actually simplest correct approach:
    # Final video = [crossfade_segment] + [body] + [tail]
    # - crossfade_segment starts as tail (end-of-video feel) and morphs into head
    # - body plays normally
    # - tail is the original ending
    # When loop: ...tail -> crossfade(tail->head) -> body -> tail -> crossfade...
    # No that doubles the tail.

    # Cleanest approach:
    # Final = [head] + [body] + [crossfade(tail->head)]
    # - Plays: head -> body -> crossfade(tail morphing to head)
    # - Loop: -> head -> body -> crossfade -> head -> ...
    # The crossfade ends looking like head, then head starts. Seamless!

    with open(temp_concat_list, "w") as f:
        f.write(f"file '{os.path.basename(temp_head)}'\n")
        f.write(f"file '{os.path.basename(temp_body)}'\n")
        f.write(f"file '{os.path.basename(temp_xfade)}'\n")

    # Concatenate video segments
    temp_video_only = os.path.join(output_dir, "_loop_video_only.mp4")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", temp_concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-movflags", "+faststart",
        temp_video_only
    ], "Concatenating: head + body + crossfade")

    # Step 6: Re-add original audio (trim to match new video duration)
    new_info = get_video_info(temp_video_only)
    new_duration = new_info["duration"]
    print(f"  New video duration: {new_duration:.3f}s (original: {duration:.3f}s)")

    # Check if original has audio
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-print_format", "json",
        input_path
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    has_audio = "audio" in probe_result.stdout

    if has_audio:
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", temp_video_only,
            "-i", input_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{new_duration:.3f}",
            "-movflags", "+faststart",
            "-shortest",
            output_path
        ], "Merging video with original audio")
    else:
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", temp_video_only,
            "-c:v", "copy",
            "-movflags", "+faststart",
            output_path
        ], "Finalizing (no audio track)")

    # Cleanup temp files
    for tmp in [temp_head, temp_body, temp_tail, temp_xfade,
                temp_concat_list, temp_video_only]:
        if os.path.exists(tmp):
            os.remove(tmp)

    print(f"  Output: {output_path}")
    return new_duration


def verify_loop(video_path: str, output_dir: str):
    """
    Extract the first and last frames for visual loop verification.
    If the loop is seamless, these two frames should look very similar.
    """
    info = get_video_info(video_path)
    duration = info["duration"]

    first_path = os.path.join(output_dir, "loop_check_first.jpg")
    last_path = os.path.join(output_dir, "loop_check_last.jpg")

    # First frame
    extract_frame_jpg(video_path, 0.0, first_path)
    print(f"  First frame -> {first_path}")

    # Last frame (slightly before end to avoid black)
    last_ts = max(0, duration - 0.05)
    extract_frame_jpg(video_path, last_ts, last_path)
    print(f"  Last frame  -> {last_path}")

    print(f"\n  Compare these two images visually.")
    print(f"  If the loop is seamless, the last frame should resemble the first frame")
    print(f"  (both showing the emotional face / hook shot content).")


def main():
    parser = argparse.ArgumentParser(description="TikTok Seamless Loop Engineer")
    parser.add_argument("--input", required=True, help="Path to assembled TikTok video")
    parser.add_argument("--output", required=True, help="Output path for looped video")
    parser.add_argument("--crossfade", type=float, default=0.5,
                        help="Crossfade duration in seconds (default: 0.5)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input video not found: {args.input}")
        sys.exit(1)

    output_dir = str(Path(args.output).parent) or "."
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("  TikTok Seamless Loop Engineer")
    print("=" * 60)

    # Step 1: Create the looped video
    print("\n--- Phase 1: Creating crossfade loop ---")
    create_looped_video(args.input, args.output, args.crossfade)

    # Step 2: Verify the loop
    print("\n--- Phase 2: Loop verification ---")
    verify_loop(args.output, output_dir)

    print("\n" + "=" * 60)
    print("  DONE - Seamless loop created")
    print("=" * 60)
    print(f"\n  Output: {args.output}")
    print(f"  Loop check images in: {output_dir}/")
    print(f"\n  Upload to TikTok and verify the loop plays smoothly.")
    print(f"  The transition should flow: serene furin -> emotional face (hook).")


if __name__ == "__main__":
    main()
