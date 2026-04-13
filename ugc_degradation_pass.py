#!/usr/bin/env python3
"""
EmoGift Furin — UGC Degradation Pipeline
=========================================
Applies post-production degradation to AI-generated shots so they look like
real iPhone smartphone footage.  Seven stages, applied in strict order:

  1. Grain / ISO noise
  2. Camera shake (micro-tremblements)
  3. White-balance shift
  4. Lens softness + vignette
  5. Compression artifacts (H.264 Baseline, high CRF)
  6. Autofocus hunting (optional per shot)
  7. Frame-rate micro-variation

Usage
-----
Single shot:
    python ugc_degradation_pass.py --input shot1.mp4 --output shot1_ugc.mp4 --shot 1

Batch (all 6):
    python ugc_degradation_pass.py --batch --input-dir ./video/ --output-dir ./video_ugc/

Preview (first 3 s only):
    python ugc_degradation_pass.py --input shot1.mp4 --output shot1_ugc.mp4 --shot 1 --preview

Experts:
    4 — Lighting Saboteur
    6 — Camera Imperfection
    7 — Noise & Compression
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ugc_degradation")


# ---------------------------------------------------------------------------
# Shot preset configuration
# ---------------------------------------------------------------------------
@dataclass
class ShotPreset:
    """Per-shot degradation parameters."""

    name: str
    noise_strength: int  # alls= value for FFmpeg noise filter
    # White-balance: colorbalance r/g/b shifts
    wb_rs: float
    wb_gs: float
    wb_bs: float
    # Vignette angle (radians). PI/6 = medium, PI/5 = strong, PI/4 = light
    vignette_angle: str  # FFmpeg expression, e.g. "PI/6"
    # Lens softness (unsharp negative amount)
    lens_softness: float  # e.g. -0.3
    # Compression
    crf: int  # 32-35
    max_bitrate: str  # e.g. "2M"
    # Autofocus hunting: list of (start_frame, duration_frames) tuples
    af_hunting: List[Tuple[int, int]] = field(default_factory=list)
    # Lighting sabotage (eq filter)
    brightness: float = -0.02
    contrast: float = 1.05
    saturation: float = 0.95
    # Extra notes
    description: str = ""


SHOT_PRESETS: dict[int, ShotPreset] = {
    1: ShotPreset(
        name="shot1_kitchen_afternoon",
        noise_strength=10,
        wb_rs=0.05, wb_gs=-0.02, wb_bs=-0.04,  # warm
        vignette_angle="PI/6",
        lens_softness=-0.3,
        crf=33, max_bitrate="2M",
        af_hunting=[],
        brightness=-0.02, contrast=1.05, saturation=0.95,
        description="Kitchen, afternoon light — warm WB, medium vignette",
    ),
    2: ShotPreset(
        name="shot2_dining_morning",
        noise_strength=10,
        wb_rs=-0.02, wb_gs=0.01, wb_bs=0.06,  # cool
        vignette_angle="PI/6",
        lens_softness=-0.3,
        crf=33, max_bitrate="2M",
        af_hunting=[],
        brightness=-0.02, contrast=1.05, saturation=0.95,
        description="Dining table, morning light — cool WB, medium vignette",
    ),
    3: ShotPreset(
        name="shot3_garden_sunny",
        noise_strength=6,
        wb_rs=0.0, wb_gs=0.0, wb_bs=0.0,  # neutral
        vignette_angle="PI/4",  # light
        lens_softness=-0.2,
        crf=32, max_bitrate="2M",
        af_hunting=[(210, 15)],  # slight hunting near end (~7s mark at 30fps)
        brightness=-0.01, contrast=1.03, saturation=0.97,
        description="Garden, sunny — neutral WB, light vignette, slight AF hunt at end",
    ),
    4: ShotPreset(
        name="shot4_living_sidelight",
        noise_strength=12,
        wb_rs=0.05, wb_gs=-0.02, wb_bs=-0.04,  # warm
        vignette_angle="PI/5",  # strong
        lens_softness=-0.4,
        crf=33, max_bitrate="2M",
        af_hunting=[],  # emotion must stay sharp
        brightness=-0.03, contrast=1.06, saturation=0.93,
        description="Living room, side light — warm WB, strong vignette, NO AF hunt (emotion)",
    ),
    5: ShotPreset(
        name="shot5_kitchen_morning_zoom",
        noise_strength=14,  # digital zoom = more noise
        wb_rs=0.05, wb_gs=-0.02, wb_bs=-0.04,  # warm
        vignette_angle="PI/5",  # strong
        lens_softness=-0.5,
        crf=35, max_bitrate="1.5M",  # extra compression for digital zoom
        af_hunting=[(5, 15)],  # hunting at start
        brightness=-0.02, contrast=1.07, saturation=0.92,
        description="Kitchen, morning, zoomed — high noise, warm WB, strong vignette, AF hunt at start",
    ),
    6: ShotPreset(
        name="shot6_balcony_afternoon",
        noise_strength=8,
        wb_rs=0.05, wb_gs=-0.02, wb_bs=-0.04,  # warm
        vignette_angle="PI/6",  # medium
        lens_softness=-0.3,
        crf=33, max_bitrate="2M",
        af_hunting=[(45, 15), (150, 15)],  # twice, 0.5s each at 30fps
        brightness=-0.02, contrast=1.05, saturation=0.95,
        description="Balcony, afternoon — warm WB, medium vignette, AF hunt x2",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_ffmpeg(args: list[str], description: str) -> None:
    """Run an FFmpeg command, logging and raising on failure."""
    cmd = ["ffmpeg", "-y"] + args
    log.info("  CMD: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("FFmpeg failed during: %s", description)
        log.error("STDERR:\n%s", result.stderr[-2000:] if result.stderr else "(empty)")
        raise RuntimeError(f"FFmpeg failed: {description}")
    log.debug("  OK: %s", description)


def probe_video(path: str) -> dict:
    """Return basic video info via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}")
    data = json.loads(result.stdout)
    return data


def get_video_info(path: str) -> Tuple[int, int, float, int]:
    """Return (width, height, fps, total_frames) for a video."""
    data = probe_video(path)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            w = int(stream["width"])
            h = int(stream["height"])
            # Parse fps from r_frame_rate (e.g. "30/1")
            fps_parts = stream.get("r_frame_rate", "30/1").split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
            nb = int(stream.get("nb_frames", 0))
            if nb == 0:
                duration = float(data.get("format", {}).get("duration", "10"))
                nb = int(duration * fps)
            return w, h, fps, nb
    raise RuntimeError(f"No video stream found in {path}")


def generate_shake_offsets(num_frames: int, max_pixels: int = 3, seed: int = 42) -> List[Tuple[int, int]]:
    """
    Generate smooth random-walk camera shake offsets.
    Uses a random walk with momentum so the movement feels like a human hand
    rather than pure noise.
    """
    rng = random.Random(seed)
    offsets = []
    x, y = 0.0, 0.0
    vx, vy = 0.0, 0.0
    damping = 0.85
    impulse_scale = 0.6

    for _ in range(num_frames):
        # Random impulse
        vx = vx * damping + rng.gauss(0, impulse_scale)
        vy = vy * damping + rng.gauss(0, impulse_scale)
        x += vx
        y += vy
        # Clamp to max displacement
        x = max(-max_pixels, min(max_pixels, x))
        y = max(-max_pixels, min(max_pixels, y))
        offsets.append((round(x), round(y)))
    return offsets


def generate_af_hunting_curve(
    total_frames: int,
    hunting_ranges: List[Tuple[int, int]],
    max_blur: int = 5,
) -> List[int]:
    """
    Generate per-frame blur radius for autofocus hunting.
    Returns a list of blur values (0 = sharp, max_blur = blurriest).
    Each hunting range gets a smooth ease-in / ease-out bell curve.
    """
    blur = [0] * total_frames
    for start, duration in hunting_ranges:
        if start >= total_frames:
            continue
        end = min(start + duration, total_frames)
        actual_dur = end - start
        for i in range(actual_dur):
            # Sine bell: 0 -> max_blur -> 0
            t = i / max(actual_dur - 1, 1)
            val = math.sin(t * math.pi) * max_blur
            blur[start + i] = round(val)
    return blur


# ---------------------------------------------------------------------------
# Pipeline stages — each returns a path to an intermediate file
# ---------------------------------------------------------------------------

class UGCPipeline:
    """Applies the 7-stage degradation pipeline to a single shot."""

    def __init__(self, preset: ShotPreset, preview: bool = False, verbose: bool = True):
        self.preset = preset
        self.preview = preview
        self.tmpdir = tempfile.mkdtemp(prefix="ugc_")
        self.stage = 0
        if verbose:
            log.setLevel(logging.DEBUG)

    def _tmp(self, label: str) -> str:
        self.stage += 1
        return os.path.join(self.tmpdir, f"stage{self.stage}_{label}.mp4")

    def _duration_args(self) -> list[str]:
        """If preview mode, limit to 3 seconds."""
        if self.preview:
            return ["-t", "3"]
        return []

    # -- Stage 1: Grain / ISO noise -------------------------------------------
    def stage_grain(self, input_path: str) -> str:
        log.info("[Stage 1/7] Grain ISO noise  (alls=%d)", self.preset.noise_strength)
        out = self._tmp("grain")
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", f"noise=alls={self.preset.noise_strength}:allf=t+u",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "grain noise")
        return out

    # -- Stage 2: Camera shake ------------------------------------------------
    def stage_camera_shake(self, input_path: str) -> str:
        log.info("[Stage 2/7] Camera shake (micro-tremblements)")
        w, h, fps, nf = get_video_info(input_path)
        offsets = generate_shake_offsets(nf, max_pixels=3, seed=hash(self.preset.name) & 0xFFFFFFFF)

        # Strategy: pad the video by max_pixels on each side, then crop with
        # per-frame offsets using the sendcmd mechanism.
        pad = 4  # pixels padding on each side
        pw, ph = w + 2 * pad, h + 2 * pad

        # Build a sendcmd script: each frame sets crop x/y offset
        cmd_file = os.path.join(self.tmpdir, "shake_cmds.txt")
        frame_dur = 1.0 / fps
        with open(cmd_file, "w") as f:
            for i, (dx, dy) in enumerate(offsets):
                t = i * frame_dur
                cx = pad + dx
                cy = pad + dy
                # sendcmd format: time command
                f.write(f"{t:.6f} [crop] x {cx};\n")
                f.write(f"{t:.6f} [crop] y {cy};\n")

        out = self._tmp("shake")
        vf = (
            f"pad={pw}:{ph}:{pad}:{pad}:color=black,"
            f"sendcmd=f='{cmd_file}',"
            f"crop@crop={w}:{h}:{pad}:{pad}"
        )
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "camera shake")
        return out

    # -- Stage 3: White balance shift -----------------------------------------
    def stage_white_balance(self, input_path: str) -> str:
        p = self.preset
        log.info("[Stage 3/7] White balance shift  (rs=%.2f gs=%.2f bs=%.2f)", p.wb_rs, p.wb_gs, p.wb_bs)
        if p.wb_rs == 0 and p.wb_gs == 0 and p.wb_bs == 0:
            log.info("  -> Neutral WB, skipping")
            return input_path
        out = self._tmp("wb")
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", f"colorbalance=rs={p.wb_rs}:gs={p.wb_gs}:bs={p.wb_bs}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "white balance")
        return out

    # -- Stage 4: Lens softness + vignette ------------------------------------
    def stage_lens_vignette(self, input_path: str) -> str:
        p = self.preset
        log.info("[Stage 4/7] Lens softness (%.1f) + vignette (%s)", p.lens_softness, p.vignette_angle)
        out = self._tmp("lens")
        vf = f"vignette={p.vignette_angle},unsharp=3:3:{p.lens_softness}:3:3:{p.lens_softness}"
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "lens softness + vignette")
        return out

    # -- Stage 5: Compression artifacts ---------------------------------------
    def stage_compression(self, input_path: str) -> str:
        p = self.preset
        log.info("[Stage 5/7] Compression artifacts  (CRF %d, maxrate %s, Baseline)", p.crf, p.max_bitrate)
        out = self._tmp("compress")
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "3.1",
            "-crf", str(p.crf),
            "-maxrate", p.max_bitrate,
            "-bufsize", "4M",
            "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            out,
        ], "compression artifacts")
        return out

    # -- Stage 6: Autofocus hunting -------------------------------------------
    def stage_autofocus_hunting(self, input_path: str) -> str:
        p = self.preset
        if not p.af_hunting:
            log.info("[Stage 6/7] Autofocus hunting  -> SKIPPED (not configured for this shot)")
            return input_path

        log.info("[Stage 6/7] Autofocus hunting  (%d events)", len(p.af_hunting))
        w, h, fps, nf = get_video_info(input_path)
        blur_curve = generate_af_hunting_curve(nf, p.af_hunting, max_blur=5)

        # Build a sendcmd file that toggles boxblur per frame
        cmd_file = os.path.join(self.tmpdir, "af_cmds.txt")
        frame_dur = 1.0 / fps
        with open(cmd_file, "w") as f:
            prev_blur = 0
            for i, b in enumerate(blur_curve):
                if b != prev_blur:
                    t = i * frame_dur
                    # boxblur luma_radius:luma_power
                    # radius 0 means sharp, >0 means blur
                    radius = max(b, 0)
                    power = 1 if radius > 0 else 0
                    f.write(f"{t:.6f} [blur] luma_radius {radius};\n")
                    f.write(f"{t:.6f} [blur] luma_power {power};\n")
                    prev_blur = b

        out = self._tmp("af")
        vf = (
            f"sendcmd=f='{cmd_file}',"
            f"boxblur@blur=luma_radius=0:luma_power=0"
        )
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "autofocus hunting")
        return out

    # -- Stage 7: Frame-rate micro-variation ----------------------------------
    def stage_framerate_variation(self, input_path: str) -> str:
        log.info("[Stage 7/7] Frame-rate micro-variation (0.2%% random PTS jitter)")
        out = self._tmp("fps")
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", "setpts=PTS*(1+0.002*random(0))",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "frame-rate variation")
        return out

    # -- Lighting sabotage (applied together with another stage) ---------------
    def stage_lighting_sabotage(self, input_path: str) -> str:
        p = self.preset
        log.info("[Lighting] eq brightness=%.2f contrast=%.2f saturation=%.2f",
                 p.brightness, p.contrast, p.saturation)
        out = self._tmp("light")
        run_ffmpeg([
            "-i", input_path,
            *self._duration_args(),
            "-vf", f"eq=brightness={p.brightness}:contrast={p.contrast}:saturation={p.saturation}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            out,
        ], "lighting sabotage")
        return out

    # -- Full pipeline --------------------------------------------------------
    def run(self, input_path: str, output_path: str) -> str:
        """Execute all 7 stages + lighting sabotage in order."""
        log.info("=" * 60)
        log.info("UGC Degradation Pipeline — %s", self.preset.name)
        log.info("  Preset: %s", self.preset.description)
        log.info("  Input : %s", input_path)
        log.info("  Output: %s", output_path)
        if self.preview:
            log.info("  MODE  : PREVIEW (first 3 seconds only)")
        log.info("=" * 60)

        current = input_path

        # Stage 1: Grain
        current = self.stage_grain(current)

        # Stage 2: Camera shake
        current = self.stage_camera_shake(current)

        # Stage 3: White balance
        current = self.stage_white_balance(current)

        # Stage 4: Lens softness + vignette
        current = self.stage_lens_vignette(current)

        # Stage 5: Compression artifacts
        current = self.stage_compression(current)

        # Stage 6: Autofocus hunting
        current = self.stage_autofocus_hunting(current)

        # Stage 7: Frame-rate micro-variation
        current = self.stage_framerate_variation(current)

        # Lighting sabotage (Expert 4)
        current = self.stage_lighting_sabotage(current)

        # Copy final result to output
        log.info("-" * 60)
        log.info("Copying final result to %s", output_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        run_ffmpeg([
            "-i", current,
            "-c", "copy",
            output_path,
        ], "copy to output")

        # Clean up intermediates
        self._cleanup()

        log.info("DONE  %s", output_path)
        log.info("=" * 60)
        return output_path

    def _cleanup(self) -> None:
        """Remove temporary intermediate files."""
        import shutil
        try:
            shutil.rmtree(self.tmpdir)
            log.debug("Cleaned up temp dir: %s", self.tmpdir)
        except Exception as e:
            log.warning("Could not clean temp dir %s: %s", self.tmpdir, e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_single_shot(
    input_path: str,
    output_path: str,
    shot_number: int,
    preview: bool = False,
) -> str:
    """Process a single shot through the full UGC degradation pipeline."""
    if shot_number not in SHOT_PRESETS:
        raise ValueError(f"Unknown shot number {shot_number}. Valid: {sorted(SHOT_PRESETS.keys())}")

    preset = SHOT_PRESETS[shot_number]
    pipeline = UGCPipeline(preset, preview=preview)
    return pipeline.run(input_path, output_path)


def process_all_shots(
    input_dir: str,
    output_dir: str,
    preview: bool = False,
) -> List[str]:
    """
    Batch-process all 6 shots.
    Expects input files named shot1.mp4 .. shot6.mp4 in input_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for shot_num in sorted(SHOT_PRESETS.keys()):
        input_path = os.path.join(input_dir, f"shot{shot_num}.mp4")
        if not os.path.isfile(input_path):
            log.warning("Input not found, skipping: %s", input_path)
            continue

        output_path = os.path.join(output_dir, f"shot{shot_num}_ugc.mp4")
        log.info("\n")
        log.info("*" * 60)
        log.info("BATCH: Processing shot %d / %d", shot_num, len(SHOT_PRESETS))
        log.info("*" * 60)

        try:
            result = process_single_shot(input_path, output_path, shot_num, preview=preview)
            results.append(result)
        except Exception as e:
            log.error("FAILED shot %d: %s", shot_num, e)

    log.info("\n")
    log.info("=" * 60)
    log.info("BATCH COMPLETE — %d / %d shots processed", len(results), len(SHOT_PRESETS))
    log.info("=" * 60)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="EmoGift Furin — UGC Degradation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ugc_degradation_pass.py --input shot1.mp4 --output shot1_ugc.mp4 --shot 1
  python ugc_degradation_pass.py --input shot3.mp4 --output shot3_ugc.mp4 --shot 3 --preview
  python ugc_degradation_pass.py --batch --input-dir ./video/ --output-dir ./video_ugc/
        """,
    )

    parser.add_argument("--input", "-i", help="Input video file path")
    parser.add_argument("--output", "-o", help="Output video file path")
    parser.add_argument("--shot", "-s", type=int, choices=sorted(SHOT_PRESETS.keys()),
                        help="Shot number (1-6) for preset selection")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode: process all 6 shots")
    parser.add_argument("--input-dir", help="Input directory for batch mode")
    parser.add_argument("--output-dir", help="Output directory for batch mode")
    parser.add_argument("--preview", action="store_true",
                        help="Preview mode: process only first 3 seconds")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose (debug) logging")
    parser.add_argument("--list-presets", action="store_true",
                        help="List all shot presets and exit")

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    # List presets and exit
    if args.list_presets:
        print("\nShot presets:")
        print("-" * 60)
        for num, preset in sorted(SHOT_PRESETS.items()):
            print(f"  Shot {num}: {preset.description}")
            print(f"           noise={preset.noise_strength}  crf={preset.crf}  "
                  f"wb=({preset.wb_rs},{preset.wb_gs},{preset.wb_bs})  "
                  f"vignette={preset.vignette_angle}  "
                  f"af_hunting={'yes' if preset.af_hunting else 'no'}")
            print()
        return

    # Batch mode
    if args.batch:
        if not args.input_dir or not args.output_dir:
            parser.error("--batch requires --input-dir and --output-dir")
        process_all_shots(args.input_dir, args.output_dir, preview=args.preview)
        return

    # Single-shot mode
    if not args.input or not args.output or args.shot is None:
        parser.error("Single-shot mode requires --input, --output, and --shot")

    if not os.path.isfile(args.input):
        log.error("Input file not found: %s", args.input)
        sys.exit(1)

    process_single_shot(args.input, args.output, args.shot, preview=args.preview)


if __name__ == "__main__":
    main()
