#!/usr/bin/env python3
"""Synthesise every sound of the game (stdlib only, deterministic) into assets/sounds/*.wav.

    python3 tools/gen_sounds.py
"""
import math
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sounds")
RATE = 22050


def env(i, n, a=0.01, r=0.3):
    t = i / RATE
    dur = n / RATE
    att = min(1.0, t / a) if a > 0 else 1.0
    rel = min(1.0, (dur - t) / (r * dur)) if r > 0 else 1.0
    return max(0.0, att * rel)


def tone(freqs, dur, vol=0.5, a=0.01, r=0.4, kind="sine", glide=None):
    n = int(dur * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        s = 0.0
        for f in freqs:
            if glide:
                f = f * (1 + (glide - 1) * t / dur)
            ph = 2 * math.pi * f * t
            if kind == "sine":
                s += math.sin(ph)
            elif kind == "tri":
                s += 2 / math.pi * math.asin(math.sin(ph))
            elif kind == "bell":
                s += math.sin(ph) * math.exp(-3 * t) + 0.4 * math.sin(2.76 * ph) * math.exp(-5 * t)
        out.append(vol * s / len(freqs) * env(i, n, a, r))
    return out


def noise(dur, vol=0.4, seed=1, lp=0.15, a=0.02, r=0.5):
    rng = random.Random(seed)
    n = int(dur * RATE)
    out, y = [], 0.0
    for i in range(n):
        y += lp * (rng.uniform(-1, 1) - y)
        out.append(vol * y * 3 * env(i, n, a, r))
    return out


def seq(*parts):
    out = []
    for p in parts:
        out += p
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def silence(dur):
    return [0.0] * int(dur * RATE)


def write(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))
    return path


def music():
    # slow night pad: pentatonic chords + soft bell melody, 16 s loop
    chords = [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 329.63)]
    pad = []
    for c in chords:
        pad += tone(c, 4.0, vol=0.18, a=1.0, r=0.4, kind="tri")
    rng = random.Random(7)
    notes = [440.0, 493.88, 587.33, 659.25, 783.99]
    mel = []
    for _ in range(16):
        mel += tone([rng.choice(notes)], 0.5, vol=0.12, a=0.005, r=0.9, kind="bell") + silence(0.5)
    return mix(pad, mel)


SOUNDS = {
    "pickup": lambda: tone([1318.5, 1760.0], 0.18, vol=0.35, r=0.6, glide=1.15),
    "lantern_lit": lambda: seq(tone([523.25, 659.25], 0.15, 0.4), tone([659.25, 783.99, 1046.5], 0.6, 0.4, kind="bell")),
    "pulse": lambda: mix(tone([300.0], 0.5, 0.4, glide=2.5, r=0.7), noise(0.5, 0.15, seed=3, lp=0.3)),
    "hit": lambda: mix(tone([140.0, 95.0], 0.4, 0.5, kind="tri", glide=0.6), noise(0.3, 0.3, seed=4, lp=0.5)),
    "jump": lambda: tone([392.0], 0.15, 0.3, glide=1.6, r=0.5),
    "dash": lambda: noise(0.22, 0.35, seed=5, lp=0.6, a=0.005, r=0.8),
    "win": lambda: seq(tone([523.25], 0.15, 0.35), tone([659.25], 0.15, 0.35), tone([783.99], 0.15, 0.35),
                       tone([1046.5, 783.99, 659.25], 0.9, 0.35, kind="bell")),
    "lose": lambda: seq(tone([392.0], 0.3, 0.35, kind="tri"), tone([329.63], 0.3, 0.35, kind="tri"),
                        tone([261.63, 196.0], 0.9, 0.35, kind="tri", glide=0.9)),
    "shade_spawn": lambda: mix(tone([110.0, 116.5], 0.9, 0.4, a=0.2, kind="tri"), noise(0.9, 0.15, seed=6, lp=0.05)),
    "countdown": lambda: tone([880.0], 0.08, 0.35, r=0.5),
    "wind": lambda: noise(1.8, 0.35, seed=8, lp=0.04, a=0.4, r=0.4),
    "music": music,
}


def main():
    for name, fn in SOUNDS.items():
        print("wrote", os.path.relpath(write(name, fn()), ROOT))


if __name__ == "__main__":
    main()
