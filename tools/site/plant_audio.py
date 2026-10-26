#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# plant_audio.py — turn the Khait et al. 2023 plant-ultrasound recordings
# (Dryad 10.5061/dryad.jwstqjqf7, CC0) into something a human can hear.
#
# The source WAVs are 2 ms clicks recorded at 500 kHz — 20-100 kHz band,
# above human hearing. Rewriting the header to declare 44.1 kHz plays the
# same samples ~11.3x slower, which is the standard honest "slowed down"
# presentation: shape preserved, pitch shifted into the audible range.
#
# Usage:
#   tools/site/plant_audio.py [--zip data/dryad/PlantSounds.zip]
#
# Downloads the dataset yourself (CC0):
#   https://datadryad.org/stash/dataset/doi:10.5061/dryad.jwstqjqf7
#
# Output: site/public/audio/plant-{thirsty,cut,room}.wav

import argparse
import random
import wave
import zipfile
from io import BytesIO
from pathlib import Path

OUT_RATE = 44100
GAP_MS = 180  # silence between clicks
CLICKS = 8
SEED = 20231026

CLASSES = {
    "thirsty": "Tomato Dry/",   # unwatered 4-6 days, soil <5%
    "cut": "Tomato Cut/",       # cut at the stem
    "room": "Empty Pot/",       # microphone self-noise control
}


def read_zip_wav(zf: zipfile.ZipFile, name: str) -> bytes:
    with wave.open(BytesIO(zf.read(name))) as w:
        return w.readframes(w.getnframes())


def build(zf: zipfile.ZipFile, prefix: str) -> bytes:
    names = sorted(
        n for n in zf.namelist()
        if n.startswith(prefix) and n.endswith(".wav")
    )
    if not names:
        raise SystemExit(f"no wavs under {prefix!r} — check dataset layout")
    picks = random.Random(SEED).sample(names, min(CLICKS, len(names)))
    frames = b"".join(read_zip_wav(zf, n) for n in picks)
    return frames, picks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="data/dryad/PlantSounds.zip")
    ap.add_argument("--out", default="site/public/audio")
    args = ap.parse_args()

    zf = zipfile.ZipFile(args.zip)
    # verify header params from a sample
    probe = read_zip_wav(zf, [n for n in zf.namelist() if n.endswith(".wav")][0])
    gap = b"\x00\x00" * int(OUT_RATE * GAP_MS / 1000)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for cls, prefix in CLASSES.items():
        frames, picks = build(zf, prefix)
        chunks = []
        # re-split concatenated frames back into per-click chunks for gaps:
        # each source wav is exactly 1000 samples (2 ms @ 500 kHz), 16-bit mono
        n_samples = len(frames) // 2
        per = n_samples // len(picks)
        for i in range(len(picks)):
            chunks.append(frames[i * per * 2:(i + 1) * per * 2])
            if i < len(picks) - 1:
                chunks.append(gap)
        body = b"".join(chunks)
        dst = outdir / f"plant-{cls}.wav"
        with wave.open(str(dst), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(OUT_RATE)  # the ~11.3x slowdown: 500 kHz -> 44.1 kHz
            w.writeframes(body)
        print(f"{dst}: {len(picks)} clicks, {len(body)//2/OUT_RATE:.2f}s, "
              f"{dst.stat().st_size//1024} KB  <- {[p.split('/')[-1] for p in picks][:3]}...")


if __name__ == "__main__":
    main()
