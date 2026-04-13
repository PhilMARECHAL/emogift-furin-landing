#!/usr/bin/env python3
"""
EmoGift Furin — UGC Quality Gate (Expert 10)
=============================================
10-point realism scoring tool with automated technical checks and interactive
manual review.  Has VETO POWER over any shot that looks AI-generated.

Criteria mix:
  - 5 automated / semi-automated (light asymmetry, ISO noise, camera shake,
    ambient audio, compression artifacts)
  - 5 manual (skin imperfections, life clutter, hand realism, facial emotion
    asymmetry, overall "phone look")

Minimum passing score: 8 / 10

Usage
-----
Single shot (interactive):
    python ugc_quality_gate.py --shot shot1_final.mp4 --shot-number 1

Batch (all 6):
    python ugc_quality_gate.py --batch --input-dir ./video_final/

Auto checks only (no manual input):
    python ugc_quality_gate.py --auto-only --shot shot1.mp4

View saved report:
    python ugc_quality_gate.py --report ugc_quality_report.json

Expert:
    10 — UGC Quality Gate
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PASS_THRESHOLD = 8
CONDITIONAL_THRESHOLD = 6

CRITERIA = [
    {
        "id": 1,
        "name": "Skin imperfections",
        "description": "Skin shows visible imperfections (pores, wrinkles, spots)",
        "auto": False,
    },
    {
        "id": 2,
        "name": "Light asymmetry",
        "description": "Light is asymmetric (one side brighter than the other)",
        "auto": True,
    },
    {
        "id": 3,
        "name": "ISO video noise",
        "description": "ISO video noise is visible (especially in dark areas)",
        "auto": True,
    },
    {
        "id": 4,
        "name": "Camera micro-shake",
        "description": "Image trembles slightly (human micro-shake)",
        "auto": True,
    },
    {
        "id": 5,
        "name": "Life clutter",
        "description": "Decor contains 'life clutter' (everyday objects)",
        "auto": False,
    },
    {
        "id": 6,
        "name": "Hand realism",
        "description": "Hands are realistic (veins, imperfections, natural movement)",
        "auto": False,
    },
    {
        "id": 7,
        "name": "Facial emotion asymmetry",
        "description": "Facial emotion is asymmetric and uncontrolled",
        "auto": False,
    },
    {
        "id": 8,
        "name": "Ambient audio",
        "description": "Ambient sound is present and credible (no total silence)",
        "auto": True,
    },
    {
        "id": 9,
        "name": "Compression artifacts",
        "description": "Video compression is visible (slight H.264 artifacts)",
        "auto": True,
    },
    {
        "id": 10,
        "name": "Phone-filmed look",
        "description": "A non-expert friend would say 'filmed with a phone'",
        "auto": False,
    },
]

REMEDIATION = {
    1: "Increase grain in ugc_degradation_pass.py, or re-prompt with 'visible pores, acne scars, sun damage'",
    2: "Add stronger vignette, or re-prompt with 'harsh side window light'",
    3: "Increase noise level in ugc_degradation_pass.py (alls=12+)",
    4: "Enable/increase camera shake in ugc_degradation_pass.py",
    5: "Re-prompt with more environmental clutter details",
    6: "Re-generate shot, add 'visible veins, dry skin' to prompt",
    7: "Generate 10+ more variations, pick most asymmetric expression",
    8: "Run ugc_audio_mix.py to add ambiance layers",
    9: "Re-encode at CRF 33+ via ugc_degradation_pass.py",
    10: "Full pipeline redo — shot is fundamentally too 'AI-looking'",
}

# ---------------------------------------------------------------------------
# Helpers — FFmpeg / FFprobe wrappers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess, return result.  Raises on failure."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False,
    )


def _ffprobe_json(path: str) -> dict:
    """Return ffprobe JSON output for *path*."""
    r = _run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ])
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {r.stderr}")
    return json.loads(r.stdout)


def _get_duration(path: str) -> float:
    """Return video duration in seconds."""
    info = _ffprobe_json(path)
    return float(info["format"]["duration"])


def _extract_frame(video: str, timestamp: float, output: str) -> str:
    """Extract a single frame at *timestamp* seconds, save as JPEG."""
    _run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", video,
        "-frames:v", "1", "-q:v", "2", output,
    ])
    return output


def _extract_review_frames(video: str, out_dir: str) -> list[str]:
    """Extract 3 representative frames at 25%, 50%, 75% of duration."""
    duration = _get_duration(video)
    timestamps = [duration * p for p in (0.25, 0.50, 0.75)]
    paths: list[str] = []
    for i, ts in enumerate(timestamps, 1):
        out = os.path.join(out_dir, f"review_frame_{i}.jpg")
        _extract_frame(video, ts, out)
        paths.append(out)
    return paths


# ---------------------------------------------------------------------------
# Automated checks
# ---------------------------------------------------------------------------

def check_light_asymmetry(video: str) -> tuple[bool, str]:
    """Criterion 2: Extract mid frame, split left/right, compare luminance.

    PASS if left-right luminance difference > 10%.
    """
    duration = _get_duration(video)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        frame_path = tmp.name
    _extract_frame(video, duration / 2, frame_path)

    # Use ffmpeg to get average brightness of left and right halves
    # Left half
    r_left = _run([
        "ffmpeg", "-i", frame_path,
        "-vf", "crop=iw/2:ih:0:0,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ])
    # Right half
    r_right = _run([
        "ffmpeg", "-i", frame_path,
        "-vf", "crop=iw/2:ih:iw/2:0,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ])

    try:
        os.unlink(frame_path)
    except OSError:
        pass

    if r_left.returncode != 0 or r_right.returncode != 0:
        # Fallback: use signalstats for average brightness
        return _check_light_asymmetry_signalstats(video)

    # Calculate mean pixel value from raw bytes
    left_bytes = r_left.stdout.encode("latin-1") if isinstance(r_left.stdout, str) else r_left.stdout
    right_bytes = r_right.stdout.encode("latin-1") if isinstance(r_right.stdout, str) else r_right.stdout

    if not left_bytes or not right_bytes:
        return _check_light_asymmetry_signalstats(video)

    left_mean = sum(left_bytes) / len(left_bytes)
    right_mean = sum(right_bytes) / len(right_bytes)
    max_val = max(left_mean, right_mean, 1)
    diff_pct = abs(left_mean - right_mean) / max_val * 100

    passed = diff_pct > 10
    detail = f"L/R luminance: {left_mean:.1f} vs {right_mean:.1f} (diff {diff_pct:.1f}%)"
    return passed, detail


def _check_light_asymmetry_signalstats(video: str) -> tuple[bool, str]:
    """Fallback using signalstats filter on a single frame."""
    duration = _get_duration(video)
    mid = duration / 2

    def _avg_brightness(crop_filter: str) -> float | None:
        r = _run([
            "ffmpeg", "-ss", str(mid), "-i", video,
            "-frames:v", "1",
            "-vf", f"{crop_filter},signalstats",
            "-f", "null", "-",
        ])
        output = r.stderr or ""
        for line in output.splitlines():
            if "YAVG" in line:
                parts = line.split("YAVG:")
                if len(parts) >= 2:
                    try:
                        return float(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
        return None

    left_avg = _avg_brightness("crop=iw/2:ih:0:0")
    right_avg = _avg_brightness("crop=iw/2:ih:iw/2:0")

    if left_avg is None or right_avg is None:
        return False, "Could not measure luminance (ffmpeg signalstats unavailable)"

    max_val = max(left_avg, right_avg, 1)
    diff_pct = abs(left_avg - right_avg) / max_val * 100
    passed = diff_pct > 10
    detail = f"L/R luminance (signalstats): {left_avg:.1f} vs {right_avg:.1f} (diff {diff_pct:.1f}%)"
    return passed, detail


def check_iso_noise(video: str) -> tuple[bool, str]:
    """Criterion 3: Measure noise variance in dark regions.

    Uses consecutive-frame temporal difference in dark areas.
    PASS if noise variance is above threshold.
    """
    duration = _get_duration(video)
    mid = duration / 2

    # Extract two consecutive frames and measure difference
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp1:
        f1 = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp2:
        f2 = tmp2.name

    # Use signalstats to measure noise (YDIF = temporal difference)
    r = _run([
        "ffmpeg", "-ss", str(mid), "-i", video,
        "-frames:v", "10",
        "-vf", "signalstats=stat=tout+vrep+brng",
        "-f", "null", "-",
    ])

    try:
        os.unlink(f1)
        os.unlink(f2)
    except OSError:
        pass

    output = r.stderr or ""

    # Parse YDIF (temporal difference) values as noise proxy
    ydif_values: list[float] = []
    for line in output.splitlines():
        if "YDIF" in line:
            parts = line.split("YDIF:")
            if len(parts) >= 2:
                try:
                    val = float(parts[1].strip().split()[0])
                    ydif_values.append(val)
                except (ValueError, IndexError):
                    pass

    if not ydif_values:
        # Fallback: check for noise using YLOW (dark pixel percentage)
        ylow_values: list[float] = []
        for line in output.splitlines():
            if "YLOW" in line:
                parts = line.split("YLOW:")
                if len(parts) >= 2:
                    try:
                        val = float(parts[1].strip().split()[0])
                        ylow_values.append(val)
                    except (ValueError, IndexError):
                        pass
        if ylow_values:
            avg_ylow = sum(ylow_values) / len(ylow_values)
            # If there are many dark pixels with variation, likely noisy
            passed = avg_ylow > 2.0
            return passed, f"Dark pixel % (YLOW avg): {avg_ylow:.2f} (threshold 2.0)"
        return False, "Could not measure noise (signalstats YDIF unavailable)"

    avg_ydif = sum(ydif_values) / len(ydif_values)
    # Threshold: temporal difference > 1.5 suggests visible noise
    passed = avg_ydif > 1.5
    detail = f"Temporal noise (YDIF avg): {avg_ydif:.2f} (threshold 1.5)"
    return passed, detail


def check_camera_shake(video: str) -> tuple[bool, str]:
    """Criterion 4: Analyze motion vectors between consecutive frames.

    PASS if average displacement > 0.5 px.
    """
    duration = _get_duration(video)
    mid = duration / 2

    # Use vidstabdetect to measure global motion
    with tempfile.NamedTemporaryFile(suffix=".trf", delete=False) as tmp:
        trf_path = tmp.name

    r = _run([
        "ffmpeg", "-ss", str(mid), "-t", "2", "-i", video,
        "-vf", f"vidstabdetect=shakiness=10:accuracy=15:result={trf_path}",
        "-f", "null", "-",
    ])

    # Parse transform file for motion data
    displacements: list[float] = []
    try:
        if os.path.exists(trf_path):
            with open(trf_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    # Format: frame_idx dx dy ...
                    parts = line.split()
                    for part in parts:
                        if part.startswith("dx="):
                            try:
                                dx = float(part.split("=")[1].rstrip(","))
                            except ValueError:
                                dx = 0.0
                        elif part.startswith("dy="):
                            try:
                                dy = float(part.split("=")[1].rstrip(","))
                            except ValueError:
                                dy = 0.0
                    try:
                        displacement = (dx**2 + dy**2) ** 0.5
                        displacements.append(displacement)
                    except NameError:
                        pass
    except (OSError, ValueError):
        pass
    finally:
        try:
            os.unlink(trf_path)
        except OSError:
            pass

    if not displacements:
        # Fallback: use scene detection variance
        return False, "Could not measure camera shake (vidstabdetect unavailable)"

    avg_disp = sum(displacements) / len(displacements)
    passed = avg_disp > 0.5
    detail = f"Avg frame displacement: {avg_disp:.2f} px (threshold 0.5 px)"
    return passed, detail


def check_ambient_audio(video: str) -> tuple[bool, str]:
    """Criterion 8: Check audio RMS level is not silent.

    PASS if RMS > -40 dB (audio is present and non-silent).
    """
    # Check if video has an audio stream at all
    info = _ffprobe_json(video)
    has_audio = any(
        s.get("codec_type") == "audio" for s in info.get("streams", [])
    )
    if not has_audio:
        return False, "No audio stream found"

    # Measure RMS using astats
    r = _run([
        "ffmpeg", "-i", video,
        "-af", "astats=metadata=1:reset=0,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ])

    output = r.stderr or ""
    rms_values: list[float] = []
    for line in output.splitlines():
        if "RMS_level" in line:
            parts = line.split("=")
            if len(parts) >= 2:
                try:
                    val = float(parts[-1].strip())
                    if val > -100:  # Filter out -inf
                        rms_values.append(val)
                except ValueError:
                    pass

    if not rms_values:
        # Fallback: use volumedetect
        r2 = _run([
            "ffmpeg", "-i", video,
            "-af", "volumedetect", "-f", "null", "-",
        ])
        output2 = r2.stderr or ""
        for line in output2.splitlines():
            if "mean_volume" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        val = float(parts[-1].strip().replace(" dB", ""))
                        rms_values.append(val)
                    except ValueError:
                        pass

    if not rms_values:
        return False, "Could not measure audio level"

    avg_rms = sum(rms_values) / len(rms_values)
    passed = avg_rms > -40
    detail = f"Audio RMS: {avg_rms:.1f} dB (threshold -40 dB)"
    return passed, detail


def check_compression(video: str) -> tuple[bool, str]:
    """Criterion 9: Check bitrate and infer compression level.

    PASS if average bitrate < 3 Mbps (indicating visible H.264 artifacts).
    """
    info = _ffprobe_json(video)

    # Get video stream bitrate
    video_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        return False, "No video stream found"

    # Try stream-level bit_rate, then format-level
    bitrate_str = video_stream.get("bit_rate")
    if not bitrate_str:
        bitrate_str = info.get("format", {}).get("bit_rate")
    if not bitrate_str:
        # Calculate from file size and duration
        size_bytes = int(info["format"].get("size", 0))
        duration = float(info["format"].get("duration", 1))
        bitrate = (size_bytes * 8) / duration if duration > 0 else 0
    else:
        bitrate = float(bitrate_str)

    bitrate_mbps = bitrate / 1_000_000

    # Also check codec
    codec = video_stream.get("codec_name", "unknown")

    # For CRF we cannot directly read it from the file, but low bitrate
    # combined with H.264 is a strong indicator of high CRF
    passed = bitrate_mbps < 3.0
    detail = (
        f"Bitrate: {bitrate_mbps:.2f} Mbps, codec: {codec} "
        f"({'< 3 Mbps = visible artifacts' if passed else '>= 3 Mbps = too clean'})"
    )
    return passed, detail


# Dispatch table for automated checks
AUTO_CHECKS: dict[int, Any] = {
    2: check_light_asymmetry,
    3: check_iso_noise,
    4: check_camera_shake,
    8: check_ambient_audio,
    9: check_compression,
}


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

def evaluate_shot(
    video_path: str,
    shot_number: int | None = None,
    auto_only: bool = False,
    frame_dir: str | None = None,
) -> dict[str, Any]:
    """Run all 10 criteria against a video file.

    Returns a result dict with scores, details, verdict.
    """
    video_path = os.path.abspath(video_path)
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    basename = os.path.basename(video_path)
    print(f"\n{'='*70}")
    print(f"  UGC QUALITY GATE — Expert 10")
    print(f"  Shot: {basename}" + (f" (#{shot_number})" if shot_number else ""))
    print(f"{'='*70}\n")

    # Extract review frames for manual inspection
    if frame_dir is None:
        frame_dir = os.path.join(os.path.dirname(video_path), "review_frames")
    os.makedirs(frame_dir, exist_ok=True)

    review_frames: list[str] = []
    if not auto_only:
        try:
            review_frames = _extract_review_frames(video_path, frame_dir)
            print(f"  Review frames extracted to: {frame_dir}/")
            for fp in review_frames:
                print(f"    -> {os.path.basename(fp)}")
            print()
        except Exception as e:
            print(f"  [WARN] Could not extract review frames: {e}\n")

    scores: dict[int, dict[str, Any]] = {}

    for criterion in CRITERIA:
        cid = criterion["id"]
        is_auto = criterion["auto"]

        print(f"  [{cid:2d}/10] {criterion['name']}")
        print(f"         {criterion['description']}")

        if is_auto and cid in AUTO_CHECKS:
            # Run automated check
            try:
                passed, detail = AUTO_CHECKS[cid](video_path)
                score = 1 if passed else 0
                method = "AUTO"
                print(f"         -> {method}: {'PASS' if passed else 'FAIL'} — {detail}")
            except Exception as e:
                score = 0
                detail = f"Auto-check error: {e}"
                method = "AUTO-ERROR"
                print(f"         -> {method}: {detail}")
        elif auto_only:
            # Skip manual checks in auto-only mode
            score = -1  # Not evaluated
            detail = "Skipped (auto-only mode)"
            method = "SKIPPED"
            print(f"         -> {method}")
        else:
            # Manual input
            while True:
                try:
                    user_input = input(f"         Score (1=pass, 0=fail): ").strip()
                    if user_input in ("0", "1"):
                        score = int(user_input)
                        break
                    print("         Please enter 0 or 1.")
                except (EOFError, KeyboardInterrupt):
                    score = 0
                    break
            detail = "Manual assessment"
            method = "MANUAL"

        scores[cid] = {
            "criterion": criterion["name"],
            "description": criterion["description"],
            "score": score,
            "detail": detail,
            "method": method,
        }
        print()

    # Calculate totals
    evaluated = {k: v for k, v in scores.items() if v["score"] >= 0}
    total = sum(v["score"] for v in evaluated.values())
    max_possible = len(evaluated)
    failed = [cid for cid, v in evaluated.items() if v["score"] == 0]

    # Determine verdict
    if auto_only:
        auto_total = sum(v["score"] for v in evaluated.values())
        auto_max = len(evaluated)
        if auto_total == auto_max:
            verdict = "AUTO-PASS"
            verdict_text = f"All {auto_max} automated checks passed"
        else:
            verdict = "AUTO-ISSUES"
            verdict_text = f"{auto_total}/{auto_max} automated checks passed — manual review needed"
    elif total >= PASS_THRESHOLD:
        verdict = "PASS"
        verdict_text = "Shot approved for production"
    elif total >= CONDITIONAL_THRESHOLD:
        verdict = "CONDITIONAL"
        verdict_text = "Shot needs targeted fixes"
    else:
        verdict = "REJECT"
        verdict_text = "Shot must be regenerated"

    # Display verdict
    icons = {
        "PASS": "[PASS]",
        "CONDITIONAL": "[CONDITIONAL]",
        "REJECT": "[REJECT]",
        "AUTO-PASS": "[AUTO-PASS]",
        "AUTO-ISSUES": "[AUTO-ISSUES]",
    }
    print(f"\n{'='*70}")
    print(f"  VERDICT: {icons.get(verdict, verdict)}  {total}/{max_possible} — {verdict_text}")
    print(f"{'='*70}")

    if failed:
        print(f"\n  Failed criteria with remediation:")
        for cid in failed:
            print(f"    [{cid:2d}] {scores[cid]['criterion']}")
            print(f"        FIX: {REMEDIATION.get(cid, 'N/A')}")

    print()

    result = {
        "file": basename,
        "path": video_path,
        "shot_number": shot_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scores": {str(k): v for k, v in scores.items()},
        "total": total,
        "max_possible": max_possible,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "failed_criteria": failed,
        "remediation": {str(cid): REMEDIATION.get(cid, "N/A") for cid in failed},
        "review_frames": review_frames,
    }
    return result


def batch_evaluate(
    input_dir: str,
    auto_only: bool = False,
) -> list[dict[str, Any]]:
    """Evaluate all video files in *input_dir*."""
    input_dir = os.path.abspath(input_dir)
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"Directory not found: {input_dir}")

    videos = sorted(
        p for p in Path(input_dir).iterdir()
        if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm")
    )
    if not videos:
        print(f"No video files found in {input_dir}")
        return []

    print(f"\n  BATCH MODE — {len(videos)} video(s) in {input_dir}\n")

    results: list[dict[str, Any]] = []
    for i, vp in enumerate(videos, 1):
        frame_dir = os.path.join(input_dir, f"review_frames_shot{i}")
        result = evaluate_shot(
            str(vp),
            shot_number=i,
            auto_only=auto_only,
            frame_dir=frame_dir,
        )
        results.append(result)

    # Print summary table
    print(f"\n{'='*70}")
    print(f"  BATCH SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Shot':<30} {'Score':>8} {'Verdict':>15}")
    print(f"  {'-'*55}")
    for r in results:
        print(f"  {r['file']:<30} {r['total']:>3}/{r['max_possible']:<4} {r['verdict']:>15}")

    passed = sum(1 for r in results if r["verdict"] in ("PASS", "AUTO-PASS"))
    print(f"\n  {passed}/{len(results)} shots passed the quality gate.\n")

    return results


def save_report(results: list[dict[str, Any]], output_path: str) -> None:
    """Save evaluation results to JSON."""
    report = {
        "ugc_quality_gate_version": "1.0.0",
        "expert": "10 — UGC Quality Gate",
        "generated": datetime.now(timezone.utc).isoformat(),
        "pass_threshold": PASS_THRESHOLD,
        "conditional_threshold": CONDITIONAL_THRESHOLD,
        "total_shots": len(results),
        "passed": sum(1 for r in results if r["verdict"] in ("PASS", "AUTO-PASS")),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Report saved to: {output_path}")


def view_report(report_path: str) -> None:
    """Display a previously saved quality report."""
    report_path = os.path.abspath(report_path)
    if not os.path.isfile(report_path):
        print(f"Report not found: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    print(f"\n{'='*70}")
    print(f"  UGC QUALITY GATE REPORT")
    print(f"  Generated: {report.get('generated', 'N/A')}")
    print(f"  Expert: {report.get('expert', 'N/A')}")
    print(f"{'='*70}\n")

    results = report.get("results", [])
    print(f"  {'Shot':<30} {'Score':>8} {'Verdict':>15}")
    print(f"  {'-'*55}")
    for r in results:
        print(f"  {r['file']:<30} {r['total']:>3}/{r['max_possible']:<4} {r['verdict']:>15}")

    print(f"\n  Total: {report.get('passed', 0)}/{report.get('total_shots', 0)} passed")
    print()

    # Show failed criteria details
    for r in results:
        if r.get("failed_criteria"):
            print(f"  {r['file']} — Failed criteria:")
            for cid in r["failed_criteria"]:
                cid_str = str(cid)
                scores = r.get("scores", {})
                crit_info = scores.get(cid_str, {})
                print(f"    [{cid:>2}] {crit_info.get('criterion', 'N/A')}")
                remediation = r.get("remediation", {})
                print(f"        FIX: {remediation.get(cid_str, 'N/A')}")
            print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="EmoGift Furin — UGC Quality Gate (Expert 10)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ugc_quality_gate.py --shot shot1_final.mp4 --shot-number 1
  python ugc_quality_gate.py --batch --input-dir ./video_final/
  python ugc_quality_gate.py --auto-only --shot shot1.mp4
  python ugc_quality_gate.py --report ugc_quality_report.json
        """,
    )

    parser.add_argument(
        "--shot", type=str, help="Path to a single video file to evaluate"
    )
    parser.add_argument(
        "--shot-number", type=int, default=None, help="Shot number (for labeling)"
    )
    parser.add_argument(
        "--batch", action="store_true", help="Batch mode: evaluate all videos in --input-dir"
    )
    parser.add_argument(
        "--input-dir", type=str, default="./video_final/",
        help="Directory containing videos for batch mode (default: ./video_final/)",
    )
    parser.add_argument(
        "--auto-only", action="store_true",
        help="Run only automated checks (no manual input required)",
    )
    parser.add_argument(
        "--report", type=str, help="View a previously saved quality report JSON"
    )
    parser.add_argument(
        "--output-report", type=str, default="ugc_quality_report.json",
        help="Path to save the quality report (default: ugc_quality_report.json)",
    )

    args = parser.parse_args()

    # View report mode
    if args.report:
        view_report(args.report)
        return

    # Batch mode
    if args.batch:
        results = batch_evaluate(args.input_dir, auto_only=args.auto_only)
        if results:
            save_report(results, args.output_report)
        return

    # Single shot mode
    if args.shot:
        result = evaluate_shot(
            args.shot,
            shot_number=args.shot_number,
            auto_only=args.auto_only,
        )
        save_report([result], args.output_report)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
