#!/usr/bin/env python3
"""
EmoGift Furin -- UGC Assembly & Montage Pipeline
=================================================
Assembles the 6 processed UGC shots into the final hero video for the website
AND 3 testimonial vignettes for a dedicated website section.

Hero video (emogift_hero_web.mp4):
    6 shots, 30s total, seamless loop, 1080x1920 vertical 9:16, 30fps.
    Hard cuts (default) or micro-crossfade (0.2s). Loop-point crossfade 0.5s.
    H.264 Baseline, yuv420p, CRF 30-33, AAC stereo 96kbps, ~5MB target.

Testimonial vignettes (3 separate videos):
    - Marie, 26 ans  -- Shot 3, 15-20s
    - Sophie, 31 ans -- Shots 1+2, 20-25s
    - Lea, 28 ans    -- Shots 4+5, 20-25s
    White burned-in subtitles (iPhone-native style), no animation, no box.

Usage
-----
Hero only:
    python ugc_assembly.py --hero --input-dir ./video_final/ --output hero.mp4

Vignettes only:
    python ugc_assembly.py --vignettes --input-dir ./video_final/ --output-dir ./vignettes/

Everything:
    python ugc_assembly.py --all --input-dir ./video_final/ --output-dir ./output/

Expert:
    9 -- Assembly & Montage Master
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
# Constants
# ---------------------------------------------------------------------------

RESOLUTION = (1080, 1920)  # width x height (vertical 9:16)
FPS = 30
SHOT_DURATION = 5.0  # seconds per shot
NUM_SHOTS = 6
HERO_DURATION = SHOT_DURATION * NUM_SHOTS  # 30s

# Encoding
CRF_DEFAULT = 31
CRF_MIN = 30
CRF_MAX = 33
AUDIO_BITRATE = "96k"
MAX_HERO_SIZE_MB = 5.0

# Transitions
CROSSFADE_DURATION = 0.2  # seconds for inter-shot crossfade
LOOP_CROSSFADE_DURATION = 0.5  # seconds for loop-point crossfade

# Subtitle styling (iPhone-native look)
SUBTITLE_FONT = "Inter"
SUBTITLE_FALLBACK_FONT = "Arial"
SUBTITLE_FONTSIZE = 42  # FFmpeg drawtext size (equiv ~24px at 1080w)
SUBTITLE_COLOR = "white"
SUBTITLE_SHADOW_COLOR = "black@0.6"
SUBTITLE_SHADOW_X = 2
SUBTITLE_SHADOW_Y = 2
SUBTITLE_BOTTOM_MARGIN = 120  # pixels from bottom

# Vignette definitions
VIGNETTES = [
    {
        "name": "Marie, 26 ans",
        "filename": "vignette_marie.mp4",
        "shots": [3],
        "duration": (15, 20),
        "subtitle": "C\u2019\u00e9tait la premi\u00e8re fois que je voyais "
                    "ma m\u00e8re pleurer de joie...",
    },
    {
        "name": "Sophie, 31 ans",
        "filename": "vignette_sophie.mp4",
        "shots": [1, 2],
        "duration": (20, 25),
        "subtitle": "J\u2019ai film\u00e9 le moment o\u00f9 elle a ouvert "
                    "le paquet... Magique.",
    },
    {
        "name": "L\u00e9a, 28 ans",
        "filename": "vignette_lea.mp4",
        "shots": [4, 5],
        "duration": (20, 25),
        "subtitle": "Ma m\u00e8re m\u2019a rappel\u00e9e en pleurant. "
                    "Elle a dit que c\u2019\u00e9tait le plus beau cadeau "
                    "de sa vie.",
    },
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ugc_assembly")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_ffmpeg() -> str:
    """Return ffmpeg path or raise."""
    path = shutil.which("ffmpeg")
    if not path:
        log.error("ffmpeg not found in PATH. Install it first.")
        sys.exit(1)
    return path


def _find_ffprobe() -> str:
    """Return ffprobe path or raise."""
    path = shutil.which("ffprobe")
    if not path:
        log.error("ffprobe not found in PATH. Install it first.")
        sys.exit(1)
    return path


FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe()


def _run(cmd: list[str], desc: str = "") -> subprocess.CompletedProcess:
    """Run a subprocess, log it, and raise on failure."""
    cmd_str = " ".join(cmd)
    if desc:
        log.info("%s", desc)
    log.debug("CMD: %s", cmd_str)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        log.error("Command failed (rc=%d): %s", result.returncode, cmd_str)
        log.error("STDERR: %s", result.stderr[-2000:] if result.stderr else "")
        raise RuntimeError(f"FFmpeg command failed: {desc or cmd_str}")
    return result


def _probe_duration(path: str) -> float:
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            FFPROBE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        log.warning("Could not probe duration for %s, assuming %.1fs", path, SHOT_DURATION)
        return SHOT_DURATION


def _file_size_mb(path: str) -> float:
    """Return file size in MB."""
    return os.path.getsize(path) / (1024 * 1024)


def _shot_path(shots_dir: str, shot_num: int) -> str:
    """
    Resolve shot file path. Tries common naming patterns:
      shot1.mp4, shot_1.mp4, shot01.mp4, shot_01.mp4
    """
    base = Path(shots_dir)
    candidates = [
        f"shot{shot_num}.mp4",
        f"shot_{shot_num}.mp4",
        f"shot0{shot_num}.mp4",
        f"shot_0{shot_num}.mp4",
        f"Shot{shot_num}.mp4",
        f"Shot_{shot_num}.mp4",
    ]
    for c in candidates:
        p = base / c
        if p.exists():
            return str(p)
    # Fallback: return first candidate (will fail validation later)
    return str(base / candidates[0])


def _validate_shots(shots_dir: str, required: list[int] | None = None) -> list[str]:
    """Verify that all required shot files exist. Return list of paths."""
    if required is None:
        required = list(range(1, NUM_SHOTS + 1))
    paths = []
    missing = []
    for n in required:
        p = _shot_path(shots_dir, n)
        if not os.path.isfile(p):
            missing.append(f"Shot {n}: {p}")
        else:
            paths.append(p)
    if missing:
        log.error("Missing shot files:")
        for m in missing:
            log.error("  - %s", m)
        raise FileNotFoundError(
            f"{len(missing)} shot(s) missing. Cannot proceed."
        )
    log.info("All %d required shots found.", len(required))
    return paths


def _escape_drawtext(text: str) -> str:
    """Escape text for FFmpeg drawtext filter."""
    # FFmpeg drawtext needs colons, backslashes, and single quotes escaped
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")  # replace straight quote with curly
    return text


# ---------------------------------------------------------------------------
# Hero video assembly
# ---------------------------------------------------------------------------


def assemble_hero(
    shots_dir: str,
    output_path: str,
    transition: str = "cut",
    crf: int = CRF_DEFAULT,
) -> str:
    """
    Assemble 6 shots into the hero video.

    Parameters
    ----------
    shots_dir : str
        Directory containing shot1.mp4 .. shot6.mp4
    output_path : str
        Output file path for the hero video.
    transition : str
        'cut' for hard cuts, 'crossfade' for 0.2s micro-crossfade.
    crf : int
        H.264 CRF value (30-33 range).

    Returns
    -------
    str
        Path to the assembled hero video.
    """
    log.info("=" * 60)
    log.info("HERO VIDEO ASSEMBLY")
    log.info("=" * 60)
    log.info("Transition mode: %s", transition)
    log.info("CRF: %d", crf)

    # Validate all 6 shots
    shot_paths = _validate_shots(shots_dir)

    # Log durations
    for i, sp in enumerate(shot_paths, 1):
        dur = _probe_duration(sp)
        log.info("  Shot %d: %.2fs -- %s", i, dur, sp)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if transition == "crossfade":
        return _assemble_hero_crossfade(shot_paths, output_path, crf)
    else:
        return _assemble_hero_hardcut(shot_paths, output_path, crf)


def _assemble_hero_hardcut(shot_paths: list[str], output_path: str, crf: int) -> str:
    """Assemble hero with hard cuts + loop-point crossfade."""
    log.info("Assembling with HARD CUTS + 0.5s loop-point crossfade...")

    tmpdir = tempfile.mkdtemp(prefix="ugc_hero_")
    try:
        # Step 1: Normalize all shots to same format
        normalized = []
        for i, sp in enumerate(shot_paths):
            norm_path = os.path.join(tmpdir, f"norm_{i}.ts")
            _run([
                FFMPEG, "-y", "-i", sp,
                "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}:force_original_aspect_ratio=decrease,"
                       f"pad={RESOLUTION[0]}:{RESOLUTION[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                "-r", str(FPS),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-bsf:v", "h264_mp4toannexb",
                "-f", "mpegts",
                norm_path,
            ], desc=f"Normalizing shot {i+1}")
            normalized.append(norm_path)

        # Step 2: Concatenate shots 1-6 using concat protocol
        concat_raw = os.path.join(tmpdir, "concat_raw.mp4")
        concat_input = "|".join(normalized)
        _run([
            FFMPEG, "-y",
            "-i", f"concat:{concat_input}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            concat_raw,
        ], desc="Concatenating all 6 shots")

        # Step 3: Create loop-point crossfade
        # Duplicate first 0.5s at the end and crossfade
        total_dur = _probe_duration(concat_raw)
        log.info("Raw concat duration: %.2fs", total_dur)

        # Extract the first 0.5s for the loop tail
        loop_head = os.path.join(tmpdir, "loop_head.mp4")
        _run([
            FFMPEG, "-y",
            "-i", concat_raw,
            "-t", str(LOOP_CROSSFADE_DURATION),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            loop_head,
        ], desc="Extracting loop head (first 0.5s)")

        # Apply xfade at the end: last 0.5s of main crossfades into first 0.5s
        xfade_offset = total_dur - LOOP_CROSSFADE_DURATION
        _run([
            FFMPEG, "-y",
            "-i", concat_raw,
            "-i", loop_head,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={LOOP_CROSSFADE_DURATION}"
            f":offset={xfade_offset:.3f},format=yuv420p[v];"
            f"[0:a][1:a]acrossfade=d={LOOP_CROSSFADE_DURATION}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
            "-preset", "slow", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            "-r", str(FPS),
            output_path,
        ], desc="Applying loop-point crossfade + final encode")

    finally:
        # Cleanup temp files
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.info("Cleaned up temp directory.")

    _report_hero(output_path)
    return output_path


def _assemble_hero_crossfade(shot_paths: list[str], output_path: str, crf: int) -> str:
    """Assemble hero with 0.2s micro-crossfades between shots + loop crossfade."""
    log.info("Assembling with 0.2s MICRO-CROSSFADE + 0.5s loop crossfade...")

    tmpdir = tempfile.mkdtemp(prefix="ugc_hero_xf_")
    try:
        # Normalize all shots
        normalized = []
        for i, sp in enumerate(shot_paths):
            norm_path = os.path.join(tmpdir, f"norm_{i}.mp4")
            _run([
                FFMPEG, "-y", "-i", sp,
                "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}:force_original_aspect_ratio=decrease,"
                       f"pad={RESOLUTION[0]}:{RESOLUTION[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                "-r", str(FPS),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                norm_path,
            ], desc=f"Normalizing shot {i+1}")
            normalized.append(norm_path)

        # Get durations
        durations = [_probe_duration(p) for p in normalized]

        # Build xfade chain for 6 inputs
        # Each xfade reduces total duration by CROSSFADE_DURATION
        inputs = []
        for p in normalized:
            inputs.extend(["-i", p])

        # Build complex filter graph
        # Chain: [0][1]xfade -> [v01], [v01][2]xfade -> [v012], ...
        filter_parts = []
        audio_parts = []

        # Video xfade chain
        xf_dur = CROSSFADE_DURATION
        running_offset = durations[0] - xf_dur
        prev_label = "0:v"

        for i in range(1, NUM_SHOTS):
            out_label = f"v{i}"
            filter_parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade"
                f":duration={xf_dur}:offset={running_offset:.3f}[{out_label}]"
            )
            if i < NUM_SHOTS - 1:
                running_offset += durations[i] - xf_dur
            prev_label = out_label

        # Final video label
        final_v = f"v{NUM_SHOTS - 1}"

        # Audio: amerge/amix all tracks sequentially with acrossfade
        prev_a = "0:a"
        for i in range(1, NUM_SHOTS):
            out_a = f"a{i}"
            filter_parts.append(
                f"[{prev_a}][{i}:a]acrossfade=d={xf_dur}[{out_a}]"
            )
            prev_a = out_a
        final_a = f"a{NUM_SHOTS - 1}"

        filter_graph = ";".join(filter_parts)

        # First pass: concatenate with crossfades
        concat_xf = os.path.join(tmpdir, "concat_xf.mp4")
        _run([
            FFMPEG, "-y",
            *inputs,
            "-filter_complex", filter_graph,
            "-map", f"[{final_v}]", "-map", f"[{final_a}]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            concat_xf,
        ], desc="Applying micro-crossfades between all shots")

        # Loop-point crossfade (same as hardcut method)
        total_dur = _probe_duration(concat_xf)
        log.info("Crossfaded concat duration: %.2fs", total_dur)

        loop_head = os.path.join(tmpdir, "loop_head.mp4")
        _run([
            FFMPEG, "-y",
            "-i", concat_xf,
            "-t", str(LOOP_CROSSFADE_DURATION),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            loop_head,
        ], desc="Extracting loop head for seamless loop")

        xfade_offset = total_dur - LOOP_CROSSFADE_DURATION
        _run([
            FFMPEG, "-y",
            "-i", concat_xf,
            "-i", loop_head,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={LOOP_CROSSFADE_DURATION}"
            f":offset={xfade_offset:.3f},format=yuv420p[v];"
            f"[0:a][1:a]acrossfade=d={LOOP_CROSSFADE_DURATION}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
            "-preset", "slow", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            "-r", str(FPS),
            output_path,
        ], desc="Final encode with loop crossfade")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.info("Cleaned up temp directory.")

    _report_hero(output_path)
    return output_path


def _report_hero(output_path: str) -> None:
    """Log hero video stats and warn if too large."""
    size_mb = _file_size_mb(output_path)
    duration = _probe_duration(output_path)
    log.info("-" * 40)
    log.info("HERO VIDEO COMPLETE")
    log.info("  Output:   %s", output_path)
    log.info("  Duration: %.2fs", duration)
    log.info("  Size:     %.2f MB", size_mb)
    if size_mb > MAX_HERO_SIZE_MB:
        log.warning(
            "File size %.2f MB exceeds target of %.1f MB! "
            "Consider increasing CRF (current max: %d) or reducing bitrate.",
            size_mb, MAX_HERO_SIZE_MB, CRF_MAX,
        )
    else:
        log.info("  Size OK (target: <%.1f MB)", MAX_HERO_SIZE_MB)
    log.info("-" * 40)


# ---------------------------------------------------------------------------
# Testimonial vignettes
# ---------------------------------------------------------------------------


def create_vignette(
    input_paths: list[str],
    output_path: str,
    subtitle_text: str,
    person_name: str,
    duration: tuple[int, int],
    crf: int = CRF_DEFAULT,
) -> str:
    """
    Create a single testimonial vignette from one or more shots.

    Parameters
    ----------
    input_paths : list[str]
        Paths to source shot(s).
    output_path : str
        Output file path.
    subtitle_text : str
        Subtitle text to burn in.
    person_name : str
        Person name for logging.
    duration : tuple[int, int]
        Target duration range (min_sec, max_sec).
    crf : int
        CRF value.

    Returns
    -------
    str
        Path to the created vignette.
    """
    log.info("--- Vignette: %s ---", person_name)
    log.info("  Source shots: %s", [os.path.basename(p) for p in input_paths])
    log.info("  Subtitle: %s", subtitle_text)
    log.info("  Target duration: %d-%ds", duration[0], duration[1])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="ugc_vignette_")
    try:
        # Step 1: If multiple shots, concatenate them first
        if len(input_paths) == 1:
            source = input_paths[0]
        else:
            # Normalize and concat
            ts_files = []
            for i, sp in enumerate(input_paths):
                ts_path = os.path.join(tmpdir, f"vig_norm_{i}.ts")
                _run([
                    FFMPEG, "-y", "-i", sp,
                    "-vf", f"scale={RESOLUTION[0]}:{RESOLUTION[1]}:force_original_aspect_ratio=decrease,"
                           f"pad={RESOLUTION[0]}:{RESOLUTION[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                    "-bsf:v", "h264_mp4toannexb",
                    "-f", "mpegts",
                    ts_path,
                ], desc=f"Normalizing source {i+1} for vignette")
                ts_files.append(ts_path)

            source = os.path.join(tmpdir, "vig_concat.mp4")
            concat_input = "|".join(ts_files)
            _run([
                FFMPEG, "-y",
                "-i", f"concat:{concat_input}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                source,
            ], desc="Concatenating shots for vignette")

        # Step 2: Determine actual duration and trim to target
        source_dur = _probe_duration(source)
        target_dur = min(source_dur, float(duration[1]))
        target_dur = max(target_dur, float(duration[0]))
        # If source is shorter than min, use what we have
        if source_dur < duration[0]:
            log.warning(
                "Source duration (%.1fs) is shorter than target min (%ds). "
                "Using full source.",
                source_dur, duration[0],
            )
            target_dur = source_dur

        log.info("  Source duration: %.2fs -> trimming to %.2fs", source_dur, target_dur)

        # Step 3: Build subtitle filter
        escaped_text = _escape_drawtext(subtitle_text)

        # Word-wrap: split subtitle into lines of ~35 chars for vertical video
        words = subtitle_text.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if len(test) > 35 and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        # Build multi-line drawtext filters (one per line, stacked from bottom)
        drawtext_filters = []
        num_lines = len(lines)
        line_height = SUBTITLE_FONTSIZE + 10  # fontsize + spacing

        for idx, line in enumerate(lines):
            escaped_line = _escape_drawtext(line)
            # Position from bottom: last line at margin, others above
            y_offset = SUBTITLE_BOTTOM_MARGIN + (num_lines - 1 - idx) * line_height
            y_expr = f"h-{y_offset}"

            drawtext_filters.append(
                f"drawtext=text='{escaped_line}'"
                f":fontfile=''"
                f":font={SUBTITLE_FONT}"
                f":fontsize={SUBTITLE_FONTSIZE}"
                f":fontcolor={SUBTITLE_COLOR}"
                f":shadowcolor={SUBTITLE_SHADOW_COLOR}"
                f":shadowx={SUBTITLE_SHADOW_X}"
                f":shadowy={SUBTITLE_SHADOW_Y}"
                f":x=(w-text_w)/2"
                f":y={y_expr}"
            )

        # Combine video filters
        vf_chain = (
            f"scale={RESOLUTION[0]}:{RESOLUTION[1]}:force_original_aspect_ratio=decrease,"
            f"pad={RESOLUTION[0]}:{RESOLUTION[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            + ",".join(drawtext_filters)
        )

        # Step 4: Final encode
        _run([
            FFMPEG, "-y",
            "-i", source,
            "-t", f"{target_dur:.2f}",
            "-vf", vf_chain,
            "-r", str(FPS),
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
            "-preset", "slow", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            output_path,
        ], desc=f"Encoding vignette: {person_name}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    size_mb = _file_size_mb(output_path)
    out_dur = _probe_duration(output_path)
    log.info("  Vignette complete: %.2fs, %.2f MB -> %s", out_dur, size_mb, output_path)
    return output_path


def create_all_vignettes(
    shots_dir: str,
    output_dir: str,
    crf: int = CRF_DEFAULT,
) -> list[str]:
    """
    Create all 3 testimonial vignettes.

    Returns list of output paths.
    """
    log.info("=" * 60)
    log.info("TESTIMONIAL VIGNETTES")
    log.info("=" * 60)

    os.makedirs(output_dir, exist_ok=True)
    outputs = []

    for vig in VIGNETTES:
        # Resolve shot paths
        input_paths = _validate_shots(shots_dir, vig["shots"])
        output_path = os.path.join(output_dir, vig["filename"])

        result = create_vignette(
            input_paths=input_paths,
            output_path=output_path,
            subtitle_text=vig["subtitle"],
            person_name=vig["name"],
            duration=vig["duration"],
            crf=crf,
        )
        outputs.append(result)

    log.info("=" * 60)
    log.info("All %d vignettes created.", len(outputs))
    for o in outputs:
        log.info("  -> %s", o)
    log.info("=" * 60)
    return outputs


def create_all(
    shots_dir: str,
    output_dir: str,
    transition: str = "cut",
    crf: int = CRF_DEFAULT,
) -> dict:
    """
    Create everything: hero video + 3 testimonial vignettes.

    Returns dict with 'hero' path and 'vignettes' list of paths.
    """
    log.info("*" * 60)
    log.info("FULL ASSEMBLY PIPELINE")
    log.info("*" * 60)

    # Validate all 6 shots upfront
    _validate_shots(shots_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Hero video
    hero_path = os.path.join(output_dir, "emogift_hero_web.mp4")
    assemble_hero(shots_dir, hero_path, transition=transition, crf=crf)

    # Vignettes
    vignettes_dir = os.path.join(output_dir, "vignettes")
    vignette_paths = create_all_vignettes(shots_dir, vignettes_dir, crf=crf)

    log.info("*" * 60)
    log.info("ALL DONE")
    log.info("  Hero:      %s", hero_path)
    log.info("  Vignettes: %s", vignettes_dir)
    log.info("*" * 60)

    return {"hero": hero_path, "vignettes": vignette_paths}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="EmoGift Furin -- UGC Assembly & Montage Pipeline (Expert 9)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --hero --input-dir ./video_final/ --output hero.mp4
  %(prog)s --vignettes --input-dir ./video_final/ --output-dir ./vignettes/
  %(prog)s --all --input-dir ./video_final/ --output-dir ./output/
  %(prog)s --hero --input-dir ./video_final/ --output hero.mp4 --transition crossfade
  %(prog)s --hero --input-dir ./video_final/ --output hero.mp4 --crf 33
        """,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--hero", action="store_true",
        help="Assemble the hero video only.",
    )
    mode.add_argument(
        "--vignettes", action="store_true",
        help="Create the 3 testimonial vignettes only.",
    )
    mode.add_argument(
        "--all", action="store_true",
        help="Create hero video + all 3 vignettes.",
    )

    parser.add_argument(
        "--input-dir", required=True,
        help="Directory containing processed shot files (shot1.mp4 .. shot6.mp4).",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output file path for hero video (used with --hero).",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for vignettes or full output (used with --vignettes/--all).",
    )
    parser.add_argument(
        "--transition", choices=["cut", "crossfade"], default="cut",
        help="Transition mode for hero video: 'cut' (hard cuts, default) "
             "or 'crossfade' (0.2s micro-crossfade).",
    )
    parser.add_argument(
        "--crf", type=int, default=CRF_DEFAULT,
        help=f"H.264 CRF value ({CRF_MIN}-{CRF_MAX}). Default: {CRF_DEFAULT}.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug-level logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate CRF range
    if not (CRF_MIN <= args.crf <= CRF_MAX):
        log.warning(
            "CRF %d is outside recommended range [%d-%d]. Proceeding anyway.",
            args.crf, CRF_MIN, CRF_MAX,
        )

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        log.error("Input directory does not exist: %s", args.input_dir)
        sys.exit(1)

    try:
        if args.hero:
            output = args.output or "emogift_hero_web.mp4"
            assemble_hero(args.input_dir, output, transition=args.transition, crf=args.crf)

        elif args.vignettes:
            output_dir = args.output_dir or "./vignettes/"
            create_all_vignettes(args.input_dir, output_dir, crf=args.crf)

        elif args.all:
            output_dir = args.output_dir or "./output/"
            create_all(args.input_dir, output_dir, transition=args.transition, crf=args.crf)

    except FileNotFoundError as e:
        log.error("Missing files: %s", e)
        sys.exit(1)
    except RuntimeError as e:
        log.error("FFmpeg error: %s", e)
        sys.exit(1)

    log.info("Pipeline finished successfully.")


if __name__ == "__main__":
    main()
