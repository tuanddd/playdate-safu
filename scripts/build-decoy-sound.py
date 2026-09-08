#!/usr/bin/env python3
"""Bake Safu's fake latch with a falling buzz, using only Python's standard library.

Run from any directory:
    python3 scripts/build-decoy-sound.py
    python3 scripts/build-decoy-sound.py --comparison /tmp/safu-decoy-comparison.wav

The curated source WAVs are read only. The buzz is part of the resulting sample,
so the game's existing latch mute, volume, stop, and audition behavior all apply.
These measurements describe the file; audible distinction needs device listening.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import wave


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "sound-fxs" / "fake-obvious.wav"
REAL = ROOT / "source" / "sounds" / "sweet.wav"
OUTPUT = ROOT / "source" / "sounds" / "sweet-fake.wav"
SAMPLE_RATE = 44100
BUZZ_START_SECONDS = 0.165
BUZZ_DURATION_SECONDS = 0.140
BUZZ_ATTACK_SECONDS = 0.008
BUZZ_RELEASE_SECONDS = 0.032
BUZZ_START_HZ = 550.0
BUZZ_END_HZ = 350.0
BUZZ_PEAK = 0.18
HARMONICS = ((1, 1.0), (3, 0.45), (5, 0.20))
COMPARISON_GAP_SECONDS = 0.7


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (
            1, 2, SAMPLE_RATE, "NONE"
        ):
            raise ValueError(f"Expected mono 16-bit PCM at {SAMPLE_RATE} Hz: {path}")
        raw = wav.readframes(wav.getnframes())
    return list(struct.unpack(f"<{len(raw) // 2}h", raw))


def write_pcm(path, samples):
    raw = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(raw)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_buzz():
    count = round(BUZZ_DURATION_SECONDS * SAMPLE_RATE)
    buzz = []
    # The sweep's fundamental falls linearly; all harmonics follow that phase.
    slope = (BUZZ_END_HZ - BUZZ_START_HZ) / BUZZ_DURATION_SECONDS
    for index in range(count):
        seconds = index / SAMPLE_RATE
        phase = 2 * math.pi * (BUZZ_START_HZ * seconds + 0.5 * slope * seconds**2)
        # Half-cosine edges avoid introducing a second sharp click.
        attack = min(1.0, seconds / BUZZ_ATTACK_SECONDS)
        release = min(1.0, (count - 1 - index) / SAMPLE_RATE / BUZZ_RELEASE_SECONDS)
        envelope = (0.5 - 0.5 * math.cos(math.pi * attack)) * (
            0.5 - 0.5 * math.cos(math.pi * release)
        )
        tone = sum(level * math.sin(harmonic * phase) for harmonic, level in HARMONICS)
        buzz.append(tone * envelope)
    scale = BUZZ_PEAK / max(abs(sample) for sample in buzz)
    return [sample * scale for sample in buzz]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, help="Optional real, silence, fake comparison WAV")
    args = parser.parse_args()

    original = read_pcm(BASE)
    mixed = [sample / 32768 for sample in original]
    buzz = build_buzz()
    start = round(BUZZ_START_SECONDS * SAMPLE_RATE)
    if start + len(buzz) > len(mixed):
        raise ValueError("Buzz extends beyond curated sample")
    for offset, sample in enumerate(buzz):
        mixed[start + offset] += sample
    if min(mixed) < -1.0 or max(mixed) > 32767 / 32768:
        raise ValueError("Mixed sample would clip; lower BUZZ_PEAK")
    output = [round(sample * 32768) for sample in mixed]
    write_pcm(OUTPUT, output)

    if args.comparison:
        real = read_pcm(REAL)
        gap = [0] * round(COMPARISON_GAP_SECONDS * SAMPLE_RATE)
        write_pcm(args.comparison, real + gap + output)

    peak = max(abs(sample) for sample in output) / 32768
    rms = math.sqrt(sum((sample / 32768) ** 2 for sample in output) / len(output))
    report = {
        "base": str(BASE),
        "base_sha256": sha256(BASE),
        "output": str(OUTPUT),
        "output_sha256": sha256(OUTPUT),
        "format": "mono 16-bit PCM WAV",
        "sample_rate": SAMPLE_RATE,
        "frames": len(output),
        "duration_seconds": len(output) / SAMPLE_RATE,
        "peak": peak,
        "peak_dbfs": 20 * math.log10(peak),
        "rms_dbfs": 20 * math.log10(rms),
        "clipped_samples": sum(sample in (-32768, 32767) for sample in output),
        "buzz_start_seconds": start / SAMPLE_RATE,
        "buzz_end_seconds": (start + len(buzz)) / SAMPLE_RATE,
        "buzz_peak_before_pcm_quantization": max(abs(sample) for sample in buzz),
        "buzz_sweep_hz": [BUZZ_START_HZ, BUZZ_END_HZ],
        "buzz_harmonics": HARMONICS,
        "buzz_attack_seconds": BUZZ_ATTACK_SECONDS,
        "buzz_release_seconds": BUZZ_RELEASE_SECONDS,
    }
    if args.comparison:
        report["comparison"] = str(args.comparison)
        report["comparison_sha256"] = sha256(args.comparison)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
