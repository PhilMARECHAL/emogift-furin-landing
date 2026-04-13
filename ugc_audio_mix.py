#!/usr/bin/env python3
"""
EmoGift Furin -- UGC Audio Mixing Pipeline
===========================================
Creates an authentic audio landscape for the 6 UGC shots. The philosophy is
strict: ZERO stock music, ZERO professional voiceover, ZERO cinematic sound
design. Only real, mundane, domestic sounds that make AI-generated video
sound like genuine smartphone home footage.

Three audio layers:
  1. Ambient sound (per shot) -- fridge hum, birds, wind, clock tick...
  2. Breathing of the camera holder -- calm female, barely perceptible
  3. Furin wind-chime -- selective tinkles on specific shots

Usage
-----
Single shot:
    python ugc_audio_mix.py --shot 1 --video shot1.mp4 \\
        --ambiance kitchen_ambiance.wav --output shot1_mixed.mp4

Batch (all 6):
    python ugc_audio_mix.py --batch --shots-dir ./video_ugc/ \\
        --audio-dir ./audio/ --output-dir ./video_final/

Audio sourcing checklist:
    python ugc_audio_mix.py --sourcing-list

Expert:
    8 -- Audio Authenticator
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ugc_audio_mix")


# ---------------------------------------------------------------------------
# Audio layer configuration per shot
# ---------------------------------------------------------------------------
@dataclass
class AudioLayer:
    """Configuration for a single audio layer within a shot."""
    file_key: str           # key to look up in the audio directory
    volume_db: float        # FFmpeg volume adjustment in dB
    delay_ms: int = 0       # delay before layer starts (milliseconds)
    fade_in_ms: int = 500   # fade-in duration
    fade_out_ms: int = 500  # fade-out duration


@dataclass
class ShotAudioPreset:
    """Complete audio preset for one shot."""
    name: str
    description: str
    ambiance_layers: List[AudioLayer]       # ambient sounds (Layer 1)
    breathing: Optional[AudioLayer] = None  # camera holder breathing (Layer 2)
    furin: Optional[AudioLayer] = None      # furin wind-chime (Layer 3)
    notes: str = ""


# ---------------------------------------------------------------------------
# Freesound.org search terms for each audio element
# ---------------------------------------------------------------------------
# These are embedded as documentation. The generate_audio_sourcing_list()
# function uses them to produce a complete download checklist.

AUDIO_SOURCES: Dict[str, dict] = {
    # -- AMBIANCE: KITCHEN / INDOOR --
    "kitchen_fridge_hum": {
        "description": "Steady refrigerator hum, low drone, domestic",
        "freesound_search": "refrigerator hum kitchen",
        "freesound_url": "https://freesound.org/search/?q=refrigerator+hum+kitchen&f=duration%3A%5B10+TO+120%5D",
        "pixabay_search": "fridge hum ambient",
        "target_file": "ambiance/kitchen_fridge_hum.wav",
        "shots": [1, 2, 4, 5],
    },
    "clock_tick": {
        "description": "Wall clock tick-tock, steady rhythm, domestic",
        "freesound_search": "wall clock tick tock room",
        "freesound_url": "https://freesound.org/search/?q=wall+clock+tick+tock+room&f=duration%3A%5B10+TO+60%5D",
        "pixabay_search": "clock ticking room",
        "target_file": "ambiance/clock_tick.wav",
        "shots": [1, 4],
    },
    "chair_creak": {
        "description": "Occasional wooden chair creak, single event",
        "freesound_search": "wooden chair creak",
        "freesound_url": "https://freesound.org/search/?q=wooden+chair+creak",
        "pixabay_search": "chair creak wood",
        "target_file": "ambiance/chair_creak.wav",
        "shots": [1],
    },
    "muffled_traffic": {
        "description": "Distant traffic through closed window, muffled low rumble",
        "freesound_search": "muffled traffic through window",
        "freesound_url": "https://freesound.org/search/?q=muffled+traffic+window&f=duration%3A%5B15+TO+120%5D",
        "pixabay_search": "distant traffic window",
        "target_file": "ambiance/muffled_traffic.wav",
        "shots": [1, 2, 5],
    },
    "morning_birds_window": {
        "description": "Birds singing outside window, morning, European species",
        "freesound_search": "morning birds window european",
        "freesound_url": "https://freesound.org/search/?q=morning+birds+window+european&f=duration%3A%5B15+TO+120%5D",
        "pixabay_search": "morning birds outside window",
        "target_file": "ambiance/morning_birds_window.wav",
        "shots": [2, 5],
    },
    "kettle_cooling": {
        "description": "Metal kettle cooling click, single ping/tick",
        "freesound_search": "kettle cooling click metal",
        "freesound_url": "https://freesound.org/search/?q=kettle+cooling+click+metal",
        "pixabay_search": "kettle click cooling",
        "target_file": "ambiance/kettle_cooling.wav",
        "shots": [2, 5],
    },
    # -- AMBIANCE: GARDEN / OUTDOOR --
    "garden_birdsong": {
        "description": "Varied European garden birdsong, NOT a short loop, natural variation",
        "freesound_search": "garden birds european varied",
        "freesound_url": "https://freesound.org/search/?q=garden+birds+european+varied&f=duration%3A%5B30+TO+300%5D",
        "pixabay_search": "garden birdsong nature varied",
        "target_file": "ambiance/garden_birdsong.wav",
        "shots": [3, 6],
    },
    "wind_leaves": {
        "description": "Gentle wind through tree leaves, garden, not stormy",
        "freesound_search": "wind leaves garden gentle",
        "freesound_url": "https://freesound.org/search/?q=wind+leaves+garden+gentle&f=duration%3A%5B15+TO+120%5D",
        "pixabay_search": "wind leaves tree gentle",
        "target_file": "ambiance/wind_leaves.wav",
        "shots": [3, 6],
    },
    "distant_car": {
        "description": "Single distant car pass-by, suburban, not highway",
        "freesound_search": "distant car pass suburban",
        "freesound_url": "https://freesound.org/search/?q=distant+car+pass+suburban",
        "pixabay_search": "distant car passing",
        "target_file": "ambiance/distant_car.wav",
        "shots": [3],
    },
    "distant_dog_bark": {
        "description": "Distant dog barking, single or double bark, suburban",
        "freesound_search": "distant dog bark suburban",
        "freesound_url": "https://freesound.org/search/?q=distant+dog+bark+suburban",
        "pixabay_search": "distant dog barking",
        "target_file": "ambiance/distant_dog_bark.wav",
        "shots": [3],
    },
    "garden_gate_creak": {
        "description": "Metal garden gate creak, single event",
        "freesound_search": "garden gate creak metal",
        "freesound_url": "https://freesound.org/search/?q=garden+gate+creak+metal",
        "pixabay_search": "gate creak metal",
        "target_file": "ambiance/garden_gate_creak.wav",
        "shots": [3],
    },
    # -- AMBIANCE: LIVING ROOM --
    "faint_tv": {
        "description": "Very faint distant TV from another room, unintelligible murmur",
        "freesound_search": "distant tv murmur room",
        "freesound_url": "https://freesound.org/search/?q=distant+tv+murmur+room&f=duration%3A%5B10+TO+60%5D",
        "pixabay_search": "faint tv background",
        "target_file": "ambiance/faint_tv.wav",
        "shots": [4],
    },
    # -- AMBIANCE: BALCONY --
    "balcony_wind": {
        "description": "Light wind on balcony, slightly more exposed than garden",
        "freesound_search": "balcony wind light urban",
        "freesound_url": "https://freesound.org/search/?q=balcony+wind+light+urban&f=duration%3A%5B15+TO+120%5D",
        "pixabay_search": "balcony wind ambient",
        "target_file": "ambiance/balcony_wind.wav",
        "shots": [6],
    },
    "distant_traffic_open": {
        "description": "Distant traffic heard from balcony/open window, French suburban",
        "freesound_search": "distant traffic balcony suburban france",
        "freesound_url": "https://freesound.org/search/?q=distant+traffic+balcony+suburban&f=duration%3A%5B15+TO+120%5D",
        "pixabay_search": "distant traffic urban balcony",
        "target_file": "ambiance/distant_traffic_open.wav",
        "shots": [6],
    },
    "church_bell_distant": {
        "description": "Distant church bell, single or few tolls, French suburban afternoon",
        "freesound_search": "distant church bell france",
        "freesound_url": "https://freesound.org/search/?q=distant+church+bell+france",
        "pixabay_search": "distant church bell",
        "target_file": "ambiance/church_bell_distant.wav",
        "shots": [6],
    },
    # -- BREATHING --
    "breathing_calm_female": {
        "description": "Calm female breathing, gentle, natural, barely perceptible",
        "freesound_search": "calm female breathing gentle quiet",
        "freesound_url": "https://freesound.org/search/?q=calm+female+breathing+gentle+quiet&f=duration%3A%5B10+TO+60%5D",
        "pixabay_search": "female breathing calm quiet",
        "target_file": "breathing/breathing_calm_female.wav",
        "shots": [1, 2, 4, 5],
    },
    # -- FURIN --
    "furin_tinkle": {
        "description": "Japanese furin wind-chime, gentle single or few tinkles",
        "freesound_search": "japanese wind chime furin glass",
        "freesound_url": "https://freesound.org/search/?q=japanese+wind+chime+furin+glass",
        "pixabay_search": "japanese wind chime glass",
        "target_file": "furin/furin.wav",
        "note": "Project already has furin.wav in audio/ directory",
        "shots": [3, 5, 6],
    },
}


# ---------------------------------------------------------------------------
# Shot presets
# ---------------------------------------------------------------------------
# Volume reference:
#   0 dB   = original level (unity)
#  -6 dB   = half perceived loudness
# -12 dB   = quarter perceived loudness
# -20 dB   = barely perceptible background

SHOT_PRESETS: Dict[int, ShotAudioPreset] = {
    1: ShotAudioPreset(
        name="shot1_kitchen_afternoon",
        description="Kitchen unboxing, afternoon. Fridge hum, clock tick, chair creak, muffled traffic.",
        ambiance_layers=[
            AudioLayer("kitchen_fridge_hum",   volume_db=-14, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("clock_tick",           volume_db=-18, fade_in_ms=300, fade_out_ms=300),
            AudioLayer("chair_creak",          volume_db=-16, delay_ms=3500, fade_in_ms=100, fade_out_ms=200),
            AudioLayer("muffled_traffic",      volume_db=-22, fade_in_ms=1000, fade_out_ms=800),
        ],
        breathing=AudioLayer("breathing_calm_female", volume_db=-20, fade_in_ms=500, fade_out_ms=500),
        furin=None,
        notes="Chair creak is a single event ~3.5s in. Keep fridge hum steady.",
    ),
    2: ShotAudioPreset(
        name="shot2_dining_morning",
        description="Dining table, morning. Same kitchen ambiance + morning birds + kettle cooling.",
        ambiance_layers=[
            AudioLayer("kitchen_fridge_hum",   volume_db=-16, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("morning_birds_window", volume_db=-15, fade_in_ms=1000, fade_out_ms=800),
            AudioLayer("muffled_traffic",      volume_db=-24, fade_in_ms=1000, fade_out_ms=800),
            AudioLayer("kettle_cooling",       volume_db=-18, delay_ms=5000, fade_in_ms=50, fade_out_ms=100),
        ],
        breathing=AudioLayer("breathing_calm_female", volume_db=-20, fade_in_ms=500, fade_out_ms=500),
        # Transition hint: very subtle single furin tinkle at the END of Shot 2
        # (foreshadowing for Shot 3 garden reveal)
        furin=AudioLayer("furin_tinkle", volume_db=-26, delay_ms=7000, fade_in_ms=100, fade_out_ms=800),
        notes="Furin tinkle near end = foreshadowing. Kettle click is single event ~5s in.",
    ),
    3: ShotAudioPreset(
        name="shot3_garden_sunny",
        description="Garden, sunny day. Varied birdsong, wind in leaves, distant car, dog bark, gate creak.",
        ambiance_layers=[
            AudioLayer("garden_birdsong",   volume_db=-10, fade_in_ms=1200, fade_out_ms=1000),
            AudioLayer("wind_leaves",       volume_db=-12, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("distant_car",       volume_db=-22, delay_ms=4000, fade_in_ms=500, fade_out_ms=1000),
            AudioLayer("distant_dog_bark",  volume_db=-24, delay_ms=6500, fade_in_ms=100, fade_out_ms=300),
            AudioLayer("garden_gate_creak", volume_db=-20, delay_ms=2000, fade_in_ms=50, fade_out_ms=200),
        ],
        breathing=None,  # outdoor shot, no one holding camera close
        furin=None,
        notes="Birdsong is the dominant layer. Events (car, dog, gate) are sparse and random-feeling.",
    ),
    4: ShotAudioPreset(
        name="shot4_living_sidelight",
        description="Living room, side angle. Clock tick-tock, faint TV, soft fridge hum from next room.",
        ambiance_layers=[
            AudioLayer("clock_tick",        volume_db=-14, fade_in_ms=300, fade_out_ms=300),
            AudioLayer("faint_tv",          volume_db=-26, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("kitchen_fridge_hum", volume_db=-24, fade_in_ms=600, fade_out_ms=500),
        ],
        # Breathing is slightly faster/emotional on this shot -- the filmer is moved
        breathing=AudioLayer("breathing_calm_female", volume_db=-18, fade_in_ms=400, fade_out_ms=400),
        furin=None,
        notes="Breathing at -18dB (louder than other shots) to convey subtle emotion. "
              "Clock tick is the anchor sound of this quiet room.",
    ),
    5: ShotAudioPreset(
        name="shot5_kitchen_morning_zoom",
        description="Kitchen, morning, close-up. Same ambiance as Shot 2 for continuity.",
        ambiance_layers=[
            AudioLayer("kitchen_fridge_hum",   volume_db=-16, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("morning_birds_window", volume_db=-15, fade_in_ms=1000, fade_out_ms=800),
            AudioLayer("muffled_traffic",      volume_db=-24, fade_in_ms=1000, fade_out_ms=800),
            AudioLayer("kettle_cooling",       volume_db=-20, delay_ms=3000, fade_in_ms=50, fade_out_ms=100),
        ],
        breathing=AudioLayer("breathing_calm_female", volume_db=-20, fade_in_ms=500, fade_out_ms=500),
        # Faint furin tinkle -- the furin is on the table, someone brushes it
        furin=AudioLayer("furin_tinkle", volume_db=-24, delay_ms=4500, fade_in_ms=100, fade_out_ms=600),
        notes="Continuity with Shot 2. Furin tinkle is accidental (brushed on table).",
    ),
    6: ShotAudioPreset(
        name="shot6_balcony_afternoon",
        description="Balcony, afternoon. Wind, traffic, birds, church bell. Primary furin scene.",
        ambiance_layers=[
            AudioLayer("balcony_wind",         volume_db=-10, fade_in_ms=1000, fade_out_ms=1000),
            AudioLayer("distant_traffic_open", volume_db=-16, fade_in_ms=800, fade_out_ms=600),
            AudioLayer("garden_birdsong",      volume_db=-14, fade_in_ms=1000, fade_out_ms=800),
            AudioLayer("church_bell_distant",  volume_db=-22, delay_ms=5000, fade_in_ms=300, fade_out_ms=1500),
        ],
        breathing=None,  # wide establishing shot or tripod
        # PRIMARY furin scene: 3-4 tinkles, wind-driven, gentle
        furin=AudioLayer("furin_tinkle", volume_db=-6, fade_in_ms=200, fade_out_ms=1200),
        notes="This is THE furin shot. Wind-chime at -6dB is prominent but natural. "
              "Church bell is a single distant toll around 5s. French suburban afternoon.",
    ),
}


# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def _check_ffmpeg() -> str:
    """Return path to ffmpeg binary or raise."""
    for candidate in ("ffmpeg", "ffmpeg.exe"):
        try:
            result = subprocess.run(
                [candidate, "-version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    log.error("FFmpeg not found. Install it: https://ffmpeg.org/download.html")
    sys.exit(1)


def _get_duration(ffmpeg: str, filepath: str) -> float:
    """Get duration of a media file in seconds using ffprobe."""
    cmd = [
        ffmpeg.replace("ffmpeg", "ffprobe"), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        return float(result.stdout.strip())
    except ValueError:
        log.warning("Could not determine duration for %s, defaulting to 10s", filepath)
        return 10.0


def _build_layer_filter(
    input_index: int,
    layer: AudioLayer,
    total_duration_s: float,
) -> str:
    """Build FFmpeg filter chain for one audio layer.

    Returns a filter string like:
        [1:a]adelay=3500|3500,volume=-16dB,afade=t=in:d=0.5,afade=t=out:st=9.0:d=0.5[a1]
    """
    parts = []

    # Delay
    if layer.delay_ms > 0:
        parts.append(f"adelay={layer.delay_ms}|{layer.delay_ms}")

    # Volume
    parts.append(f"volume={layer.volume_db}dB")

    # Fade in
    fade_in_s = layer.fade_in_ms / 1000.0
    if fade_in_s > 0:
        parts.append(f"afade=t=in:d={fade_in_s:.3f}")

    # Fade out
    fade_out_s = layer.fade_out_ms / 1000.0
    if fade_out_s > 0:
        fade_out_start = max(0, total_duration_s - fade_out_s)
        parts.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_out_s:.3f}")

    label_in = f"[{input_index}:a]"
    label_out = f"[a{input_index}]"

    return f"{label_in}{','.join(parts)}{label_out}"


# ---------------------------------------------------------------------------
# Core mixing functions
# ---------------------------------------------------------------------------

def mix_shot_audio(
    shot_number: int,
    video_path: str,
    ambiance_paths: Dict[str, str],
    breathing_path: Optional[str] = None,
    furin_path: Optional[str] = None,
    output_path: Optional[str] = None,
    ffmpeg: Optional[str] = None,
) -> str:
    """Mix all audio layers for a single shot and mux with video.

    Parameters
    ----------
    shot_number : int
        Shot number (1-6).
    video_path : str
        Path to the input video file.
    ambiance_paths : dict
        Mapping of audio_key -> file_path for ambiance layers.
    breathing_path : str, optional
        Path to breathing audio file.
    furin_path : str, optional
        Path to furin wind-chime audio file.
    output_path : str, optional
        Output video path. Defaults to <video_path>_mixed.mp4.

    Returns
    -------
    str
        Path to the output file.
    """
    if ffmpeg is None:
        ffmpeg = _check_ffmpeg()

    preset = SHOT_PRESETS.get(shot_number)
    if preset is None:
        raise ValueError(f"No preset for shot {shot_number}. Valid: 1-6.")

    if output_path is None:
        p = Path(video_path)
        output_path = str(p.parent / f"{p.stem}_mixed{p.suffix}")

    log.info("=== Mixing Shot %d: %s ===", shot_number, preset.name)
    log.info("Video: %s", video_path)
    log.info("Output: %s", output_path)

    # Get video duration for fade-out calculations
    duration = _get_duration(ffmpeg, video_path)
    log.info("Video duration: %.2fs", duration)

    # Build input list and filter chains
    inputs = ["-i", video_path]  # input 0 = video
    filter_parts = []
    mix_labels = []
    input_idx = 1  # start audio inputs at index 1

    # Layer 1: Ambiance
    for layer_cfg in preset.ambiance_layers:
        audio_file = ambiance_paths.get(layer_cfg.file_key)
        if audio_file is None or not Path(audio_file).exists():
            log.warning(
                "  Ambiance file missing for '%s' (expected: %s), skipping layer",
                layer_cfg.file_key,
                ambiance_paths.get(layer_cfg.file_key, "NOT PROVIDED"),
            )
            continue

        inputs.extend(["-i", audio_file])
        filt = _build_layer_filter(input_idx, layer_cfg, duration)
        filter_parts.append(filt)
        mix_labels.append(f"[a{input_idx}]")
        log.info("  + Ambiance: %s @ %sdB", layer_cfg.file_key, layer_cfg.volume_db)
        input_idx += 1

    # Layer 2: Breathing
    if preset.breathing and breathing_path and Path(breathing_path).exists():
        inputs.extend(["-i", breathing_path])
        filt = _build_layer_filter(input_idx, preset.breathing, duration)
        filter_parts.append(filt)
        mix_labels.append(f"[a{input_idx}]")
        log.info("  + Breathing @ %sdB", preset.breathing.volume_db)
        input_idx += 1
    elif preset.breathing:
        log.warning("  Breathing expected but file missing, skipping layer")

    # Layer 3: Furin
    if preset.furin and furin_path and Path(furin_path).exists():
        inputs.extend(["-i", furin_path])
        filt = _build_layer_filter(input_idx, preset.furin, duration)
        filter_parts.append(filt)
        mix_labels.append(f"[a{input_idx}]")
        log.info("  + Furin @ %sdB (delay: %dms)", preset.furin.volume_db, preset.furin.delay_ms)
        input_idx += 1
    elif preset.furin:
        log.warning("  Furin expected but file missing, skipping layer")

    if not mix_labels:
        log.error("No audio layers available for shot %d. Cannot mix.", shot_number)
        sys.exit(1)

    # Amix: merge all processed audio layers
    n_layers = len(mix_labels)
    amix_input = "".join(mix_labels)
    filter_parts.append(
        f"{amix_input}amix=inputs={n_layers}:duration=first:dropout_transition=2[amixed]"
    )

    # Trim mixed audio to video duration
    filter_parts.append(
        f"[amixed]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS[afinal]"
    )

    filter_complex = ";\n".join(filter_parts)

    # Build full FFmpeg command
    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v",          # video from input 0
        "-map", "[afinal]",     # mixed audio
        "-c:v", "copy",         # no re-encode video
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-ac", "2",             # stereo
        "-shortest",
        output_path,
    ]

    log.info("Running FFmpeg...")
    log.debug("Command: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log.error("FFmpeg failed:\n%s", result.stderr[-2000:] if result.stderr else "no output")
        sys.exit(1)

    log.info("Shot %d mixed successfully: %s", shot_number, output_path)
    return output_path


def _resolve_audio_paths(
    audio_dir: str,
    preset: ShotAudioPreset,
) -> tuple[Dict[str, str], Optional[str], Optional[str]]:
    """Resolve audio file paths from the audio directory structure.

    Expected directory layout inside audio_dir:
        ambiance/
            kitchen_fridge_hum.wav
            clock_tick.wav
            ...
        breathing/
            breathing_calm_female.wav
        furin/
            furin.wav
            (or) ../furin.wav   (fallback to root audio dir)

    Returns (ambiance_paths, breathing_path, furin_path)
    """
    audio_root = Path(audio_dir)
    ambiance_paths: Dict[str, str] = {}

    for layer in preset.ambiance_layers:
        key = layer.file_key
        # Try structured path first, then flat
        candidates = [
            audio_root / "ambiance" / f"{key}.wav",
            audio_root / "ambiance" / f"{key}.mp3",
            audio_root / f"{key}.wav",
            audio_root / f"{key}.mp3",
        ]
        for c in candidates:
            if c.exists():
                ambiance_paths[key] = str(c)
                break

    breathing_path = None
    if preset.breathing:
        for candidate in [
            audio_root / "breathing" / "breathing_calm_female.wav",
            audio_root / "breathing_calm_female.wav",
            audio_root / "breathing.wav",
        ]:
            if candidate.exists():
                breathing_path = str(candidate)
                break

    furin_path = None
    if preset.furin:
        for candidate in [
            audio_root / "furin" / "furin.wav",
            audio_root / "furin.wav",
        ]:
            if candidate.exists():
                furin_path = str(candidate)
                break

    return ambiance_paths, breathing_path, furin_path


def mix_all_audio(
    shots_dir: str,
    audio_dir: str,
    output_dir: str,
) -> List[str]:
    """Mix audio for all 6 shots in batch mode.

    Parameters
    ----------
    shots_dir : str
        Directory containing shot videos named shot1.mp4 .. shot6.mp4
        (also accepts shot1_ugc.mp4 variants).
    audio_dir : str
        Directory with audio assets (ambiance/, breathing/, furin/).
    output_dir : str
        Directory for output files.

    Returns
    -------
    list[str]
        Paths to all output files.
    """
    ffmpeg = _check_ffmpeg()
    shots_path = Path(shots_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    outputs = []

    for shot_num in range(1, 7):
        preset = SHOT_PRESETS[shot_num]

        # Find video file
        video_file = None
        for pattern in [f"shot{shot_num}.mp4", f"shot{shot_num}_ugc.mp4",
                        f"shot{shot_num}_degraded.mp4", f"shot{shot_num}*.mp4"]:
            matches = list(shots_path.glob(pattern))
            if matches:
                video_file = str(matches[0])
                break

        if video_file is None:
            log.warning("No video found for shot %d in %s, skipping.", shot_num, shots_dir)
            continue

        # Resolve audio paths
        ambiance_paths, breathing_path, furin_path = _resolve_audio_paths(audio_dir, preset)

        output_file = str(out_path / f"shot{shot_num}_final.mp4")

        result = mix_shot_audio(
            shot_number=shot_num,
            video_path=video_file,
            ambiance_paths=ambiance_paths,
            breathing_path=breathing_path,
            furin_path=furin_path,
            output_path=output_file,
            ffmpeg=ffmpeg,
        )
        outputs.append(result)
        log.info("")

    log.info("=== Batch complete: %d/%d shots mixed ===", len(outputs), 6)
    return outputs


# ---------------------------------------------------------------------------
# Audio sourcing checklist
# ---------------------------------------------------------------------------

def generate_audio_sourcing_list() -> None:
    """Print a complete checklist of all audio files needed with download links."""

    print("=" * 78)
    print("  EMOGIFT FURIN -- UGC AUDIO SOURCING CHECKLIST")
    print("  Expert 8 (Audio Authenticator)")
    print("=" * 78)
    print()
    print("PHILOSOPHY: ZERO stock music. ZERO cinematic SFX. Only REAL domestic sounds.")
    print("Sources: Freesound.org (CC0/CC-BY preferred), Pixabay Audio (royalty-free)")
    print()

    categories = {
        "AMBIANCE -- Kitchen / Indoor": [
            "kitchen_fridge_hum", "clock_tick", "chair_creak",
            "muffled_traffic", "morning_birds_window", "kettle_cooling",
        ],
        "AMBIANCE -- Garden / Outdoor": [
            "garden_birdsong", "wind_leaves", "distant_car",
            "distant_dog_bark", "garden_gate_creak",
        ],
        "AMBIANCE -- Living Room": ["faint_tv"],
        "AMBIANCE -- Balcony": [
            "balcony_wind", "distant_traffic_open", "church_bell_distant",
        ],
        "BREATHING": ["breathing_calm_female"],
        "FURIN": ["furin_tinkle"],
    }

    total = 0
    for cat_name, keys in categories.items():
        print(f"\n--- {cat_name} ---")
        for key in keys:
            src = AUDIO_SOURCES[key]
            total += 1
            shots_str = ", ".join(str(s) for s in src["shots"])
            note = src.get("note", "")
            note_str = f"  NOTE: {note}" if note else ""

            print(f"\n  [{total:2d}] {key}")
            print(f"       Description : {src['description']}")
            print(f"       Target file : {src['target_file']}")
            print(f"       Used in     : Shot(s) {shots_str}")
            print(f"       Freesound   : {src['freesound_url']}")
            print(f"       Pixabay     : https://pixabay.com/sound-effects/search/{src['pixabay_search'].replace(' ', '%20')}/")
            if note_str:
                print(f"      {note_str}")

    print(f"\n{'=' * 78}")
    print(f"  TOTAL FILES NEEDED: {total}")
    print()
    print("  EXPECTED DIRECTORY STRUCTURE:")
    print("    audio/")
    print("      ambiance/")
    print("        kitchen_fridge_hum.wav")
    print("        clock_tick.wav")
    print("        chair_creak.wav")
    print("        muffled_traffic.wav")
    print("        morning_birds_window.wav")
    print("        kettle_cooling.wav")
    print("        garden_birdsong.wav")
    print("        wind_leaves.wav")
    print("        distant_car.wav")
    print("        distant_dog_bark.wav")
    print("        garden_gate_creak.wav")
    print("        faint_tv.wav")
    print("        balcony_wind.wav")
    print("        distant_traffic_open.wav")
    print("        church_bell_distant.wav")
    print("      breathing/")
    print("        breathing_calm_female.wav")
    print("      furin/")
    print("        furin.wav")
    print(f"{'=' * 78}")
    print()
    print("  VOLUME GUIDELINES:")
    print("    Ambiance  : -10dB (outdoor dominant) to -26dB (faint background)")
    print("    Breathing : -20dB (calm) to -18dB (slightly emotional, Shot 4)")
    print("    Furin     : -26dB (foreshadow) to -6dB (hero shot, Shot 6)")
    print()
    print("  WHAT NOT TO SOURCE:")
    print("    x No stock emotional music (piano + strings = instant 'ad' feeling)")
    print("    x No cinematic SFX (whoosh, impact, rising tension)")
    print("    x No professional voiceover audio")
    print(f"{'=' * 78}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="EmoGift Furin -- UGC Audio Mixing Pipeline (Expert 8)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single shot:
    python ugc_audio_mix.py --shot 1 --video shot1.mp4 \\
        --ambiance kitchen_fridge_hum=audio/ambiance/kitchen_fridge_hum.wav \\
        --ambiance clock_tick=audio/ambiance/clock_tick.wav \\
        --breathing audio/breathing/breathing_calm_female.wav \\
        --output shot1_mixed.mp4

  Batch (all 6):
    python ugc_audio_mix.py --batch --shots-dir ./video_ugc/ \\
        --audio-dir ./audio/ --output-dir ./video_final/

  Audio sourcing checklist:
    python ugc_audio_mix.py --sourcing-list

  Show preset details:
    python ugc_audio_mix.py --show-preset 4
        """,
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--shot", type=int, choices=range(1, 7), metavar="N",
                      help="Mix a single shot (1-6)")
    mode.add_argument("--batch", action="store_true",
                      help="Mix all 6 shots in batch mode")
    mode.add_argument("--sourcing-list", action="store_true",
                      help="Print audio sourcing checklist with download links")
    mode.add_argument("--show-preset", type=int, choices=range(1, 7), metavar="N",
                      help="Display audio preset details for a shot")

    # Single-shot options
    single = parser.add_argument_group("Single-shot options")
    single.add_argument("--video", type=str, help="Input video file path")
    single.add_argument("--ambiance", action="append", default=[],
                        metavar="KEY=PATH",
                        help="Ambiance audio: key=filepath (repeat for each layer)")
    single.add_argument("--breathing", type=str, help="Breathing audio file path")
    single.add_argument("--furin", type=str, help="Furin audio file path")
    single.add_argument("--output", type=str, help="Output file path")

    # Batch options
    batch = parser.add_argument_group("Batch options")
    batch.add_argument("--shots-dir", type=str, default="./video_ugc/",
                       help="Directory with shot videos (default: ./video_ugc/)")
    batch.add_argument("--audio-dir", type=str, default="./audio/",
                       help="Directory with audio assets (default: ./audio/)")
    batch.add_argument("--output-dir", type=str, default="./video_final/",
                       help="Output directory (default: ./video_final/)")

    args = parser.parse_args()

    # --- Sourcing list ---
    if args.sourcing_list:
        generate_audio_sourcing_list()
        return

    # --- Show preset ---
    if args.show_preset:
        preset = SHOT_PRESETS[args.show_preset]
        print(f"\n=== Shot {args.show_preset}: {preset.name} ===")
        print(f"Description: {preset.description}")
        print(f"\nAmbiance layers ({len(preset.ambiance_layers)}):")
        for layer in preset.ambiance_layers:
            print(f"  - {layer.file_key:30s}  vol={layer.volume_db:+.0f}dB  "
                  f"delay={layer.delay_ms}ms  "
                  f"fade_in={layer.fade_in_ms}ms  fade_out={layer.fade_out_ms}ms")
        if preset.breathing:
            b = preset.breathing
            print(f"\nBreathing: vol={b.volume_db:+.0f}dB  "
                  f"fade_in={b.fade_in_ms}ms  fade_out={b.fade_out_ms}ms")
        else:
            print("\nBreathing: NONE (no close camera holder)")
        if preset.furin:
            f = preset.furin
            print(f"\nFurin: vol={f.volume_db:+.0f}dB  delay={f.delay_ms}ms  "
                  f"fade_in={f.fade_in_ms}ms  fade_out={f.fade_out_ms}ms")
        else:
            print("\nFurin: NONE")
        if preset.notes:
            print(f"\nNotes: {preset.notes}")
        print()
        return

    # --- Batch mode ---
    if args.batch:
        mix_all_audio(args.shots_dir, args.audio_dir, args.output_dir)
        return

    # --- Single shot mode ---
    if args.shot:
        if not args.video:
            parser.error("--video is required for single-shot mode")

        # Parse ambiance key=path pairs
        ambiance_paths: Dict[str, str] = {}
        for item in args.ambiance:
            if "=" in item:
                key, path = item.split("=", 1)
                ambiance_paths[key] = path
            else:
                # If no key given, try to infer from filename
                p = Path(item)
                ambiance_paths[p.stem] = item

        mix_shot_audio(
            shot_number=args.shot,
            video_path=args.video,
            ambiance_paths=ambiance_paths,
            breathing_path=args.breathing,
            furin_path=args.furin,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
