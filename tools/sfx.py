#!/usr/bin/env python3
"""sfx — sound design synced to the motion graphics (no library needed: every sound is synthesized here).

Usage: sfx.py VIDEO [--level 1.0] [--no-riser]

Reads the overlays in work/<name>/decisions.json and the scene HTML mograph wrote (motion/scenes/<id>.html),
places a cue on every visual event (page wipes, thumbnail slams, pops, counters, typing, stamps, highlighter)
plus a RISER that builds through the hook into the first reveal, renders one sfx track on the edited
timeline (work/<name>/sfx.wav) and registers it in decisions.json ("sfx_track"); `vedit render` mixes it
under the voice before loudness normalisation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
SCENES = ROOT / "motion" / "scenes"
RNG = np.random.default_rng(7)  # deterministic: same cues → same sounds


# ----------------------------------------------------------------- synthesis
def env(n, a, d, shape=3.0):
    """attack a (0..1 of n) then exponential-ish decay."""
    t = np.linspace(0, 1, n)
    e = np.where(t < a, (t / max(a, 1e-6)) ** 1.5, ((1 - t) / max(1 - a, 1e-6)) ** shape)
    return e * d


def noise(n, color="pink"):
    w = RNG.standard_normal(n)
    if color == "pink":
        b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
        w = signal.lfilter(b, a, w)
    return w / (np.abs(w).max() + 1e-9)


def sweep_band(x, f0, f1, q=1.2, block=512):
    """band-pass x with a centre frequency gliding f0 → f1 (log), overlap-added blocks."""
    out = np.zeros_like(x)
    n = len(x)
    win = np.hanning(block * 2)
    for i, s in enumerate(range(0, n, block)):
        fc = f0 * (f1 / f0) ** (s / max(1, n))
        lo, hi = fc / (1 + 1 / q), min(fc * (1 + 1 / q), SR / 2 - 100)
        sos = signal.butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        seg = x[max(0, s - block):s + block]
        y = signal.sosfiltfilt(sos, seg) if len(seg) > 20 else seg
        w = win[:len(y)] if len(y) == len(win) else np.hanning(len(y))
        a0 = max(0, s - block)
        out[a0:a0 + len(y)] += y * w
    return out / (np.abs(out).max() + 1e-9)


def tone(freqs, n):
    """sine with a per-sample frequency curve."""
    ph = 2 * np.pi * np.cumsum(freqs) / SR
    return np.sin(ph)


def reverb(x, secs=0.6, mix=0.25):
    ir = noise(int(SR * secs), "white") * np.exp(-np.linspace(0, 7, int(SR * secs)))
    ir = signal.sosfilt(signal.butter(2, 4000, fs=SR, output="sos"), ir)
    wet = signal.fftconvolve(x, ir)[:len(x) + int(SR * secs)]
    wet /= np.abs(wet).max() + 1e-9
    dry = np.pad(x, (0, len(wet) - len(x)))
    return (1 - mix) * dry + mix * wet


def norm(x, peak):
    return x / (np.abs(x).max() + 1e-9) * peak


def s_whoosh(dur=0.55, up=True):
    n = int(SR * dur)
    x = sweep_band(noise(n), 300 if up else 2600, 2600 if up else 300, q=1.6)
    x *= env(n, 0.45, 1.0, 2.2)
    air = signal.sosfilt(signal.butter(2, 5000, btype="high", fs=SR, output="sos"), noise(n, "white")) * env(n, 0.5, 0.25, 3)
    return norm(reverb(x + air, 0.35, 0.18), 1)


def s_riser(dur=3.6):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    grow = t ** 2.2
    band = sweep_band(noise(n), 250, 6000, q=2.2) * grow
    f = 140 * (9 ** t)  # 140 Hz → 1.26 kHz
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(4 + 18 * t ** 2) / SR)
    sw = (tone(f, n) + 0.35 * tone(f * 2.005, n)) * grow * trem * 0.55
    sub = tone(np.full(n, 55.0), n) * (t ** 1.5) * 0.35
    x = band + sw + sub
    x[-int(SR * 0.012):] *= np.linspace(1, 0, int(SR * 0.012))  # hard stop → the impact takes over
    return norm(x, 1)


def s_boom(dur=1.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = tone(38 + 80 * np.exp(-t * 9), n) * np.exp(-t * 2.6)
    k = int(SR * 0.05)
    crack = np.zeros(n)
    crack[:k] = signal.sosfilt(signal.butter(2, [800, 6000], btype="band", fs=SR, output="sos"), noise(k, "white")) * np.exp(-np.linspace(0, 6, k))
    return norm(reverb(body + 0.6 * crack, 1.0, 0.22), 1)


def s_hit(dur=0.45):
    n = int(SR * dur)
    t = np.arange(n) / SR
    thump = tone(70 + 60 * np.exp(-t * 25), n) * np.exp(-t * 14)
    snap = signal.sosfilt(signal.butter(2, [1500, 7000], btype="band", fs=SR, output="sos"), noise(n, "white")) * np.exp(-t * 40)
    return norm(reverb(thump + 0.7 * snap, 0.4, 0.2), 1)


def s_pop(dur=0.12):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = tone(520 + 700 * (1 - np.exp(-t * 60)), n) * np.exp(-t * 38)
    x[:int(SR * 0.003)] += noise(int(SR * 0.003), "white") * 0.3
    return norm(x, 1)


def s_tick(dur=0.03):
    n = int(SR * dur)
    x = signal.sosfilt(signal.butter(2, 2500, btype="high", fs=SR, output="sos"), noise(n, "white")) * np.exp(-np.linspace(0, 9, n))
    return norm(x, 1)


def s_type(dur=1.0):
    n = int(SR * dur)
    x = np.zeros(n + SR // 10)
    t = 0.0
    while t < dur:
        k = s_tick(0.025) * (0.5 + 0.5 * RNG.random())
        i = int(t * SR)
        x[i:i + len(k)] += k
        t += 0.055 + 0.05 * RNG.random()
    return norm(x, 1)


def s_ding(dur=1.4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * 1320 * r * t) * np.exp(-t * d) for r, a, d in ((1, 1, 3.5), (2.76, .45, 6), (5.4, .25, 9)))
    return norm(x, 1)


def s_swish(dur=0.28):
    n = int(SR * dur)
    x = sweep_band(noise(n, "white"), 2500, 7000, q=2.0) * env(n, 0.6, 1, 2)
    return norm(x, 1)


def s_shutter(dur=0.18):
    n = int(SR * dur)
    x = np.zeros(n)
    for o in (0, int(SR * 0.07)):
        k = s_tick(0.04)
        x[o:o + len(k)] += k
    return norm(x, 1)


def s_swoosh(dur=0.5, up=True, bright=1.0):
    """clean airy swoosh (Lloyd: minimal, clean) — wide soft band glide, smooth bell envelope, no clicks."""
    n = int(SR * dur)
    x = sweep_band(noise(n, "white"), 650 if up else 2000, 2000 if up else 650, q=0.8)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * np.clip(t / 0.55, 0, 1) / 2) ** 2 * np.where(t > 0.55, np.cos(np.pi * (t - 0.55) / 0.9) ** 2, 1)
    x = x * e
    x = signal.sosfilt(signal.butter(2, 6500 * bright, fs=SR, output="sos"), x)
    x = signal.sosfilt(signal.butter(1, 180, btype="high", fs=SR, output="sos"), x)
    return norm(reverb(x, 0.3, 0.1), 1)


def s_riser_clean(dur=2.2):
    """soft air swell that rises into the reveal (no tones, no tremolo, no hard stop)."""
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    x = sweep_band(noise(n), 300, 3200, q=0.7) * t ** 3
    x[-int(SR * 0.09):] *= np.linspace(1, 0.2, int(SR * 0.09))
    x = signal.sosfilt(signal.butter(2, 7000, fs=SR, output="sos"), x)
    return norm(x, 1)


def s_swoosh_v(kind, dur=None):
    """five clean swoosh characters so transitions never sound the same."""
    if kind == "deep":   # darker, slower body
        n = int(SR * (dur or 0.62)); x = sweep_band(noise(n), 220, 900, q=0.7)
        t = np.linspace(0, 1, n); x *= np.sin(np.pi * t) ** 1.6
        x = signal.sosfilt(signal.butter(2, 2600, fs=SR, output="sos"), x)
        return norm(reverb(x, 0.45, 0.16), 1)
    if kind == "whip":   # quick bright flick
        n = int(SR * (dur or 0.24)); x = sweep_band(noise(n, "white"), 3800, 900, q=1.1)
        t = np.linspace(0, 1, n); x *= (np.sin(np.pi * np.clip(t / 0.35, 0, 1) / 2) ** 2) * np.exp(-np.clip(t - 0.35, 0, 1) * 7)
        x = signal.sosfilt(signal.butter(2, 8000, fs=SR, output="sos"), x)
        return norm(reverb(x, 0.25, 0.1), 1)
    if kind == "shimmer":  # airy with a soft glassy top
        n = int(SR * (dur or 0.5)); base = s_swoosh(dur or 0.5, True, 0.9)[:n]
        t = np.arange(n) / SR; sh = sum(np.sin(2 * np.pi * f * t) for f in (2640, 3520, 4400)) / 3
        sh *= np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.18
        return norm(base + sh, 1)
    if kind == "reverse":  # swells up and stops — for pages leaving
        n = int(SR * (dur or 0.45)); x = sweep_band(noise(n), 500, 2400, q=0.8)
        t = np.linspace(0, 1, n); x *= t ** 2.4
        x[-int(SR * 0.03):] *= np.linspace(1, 0, int(SR * 0.03))
        x = signal.sosfilt(signal.butter(2, 6000, fs=SR, output="sos"), x)
        return norm(x, 1)
    return s_swoosh(dur or 0.42, True, 0.85)  # "air"


def s_riser_suspense(dur=3.0):
    """suspense build: slow heartbeat sub, rising dark air, faint dissonant pair creeping up; soft hand-off."""
    n = int(SR * dur)
    t = np.linspace(0, 1, n); ts = np.arange(n) / SR
    air = sweep_band(noise(n), 180, 2600, q=0.7) * t ** 2.6
    air = signal.sosfilt(signal.butter(2, 5000, fs=SR, output="sos"), air)
    beat = np.zeros(n)
    k, bt = 0.0, 0.0
    while bt < dur - 0.15:  # heartbeat speeds up 0.75 s → 0.32 s
        i = int(bt * SR); m = min(int(SR * 0.22), n - i)
        tt = np.arange(m) / SR
        beat[i:i + m] += np.sin(2 * np.pi * (52 + 18 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 16) * (0.35 + 0.65 * bt / dur)
        bt += 0.75 - 0.43 * (bt / dur)
    f1 = 196 * (1 + 0.35 * t ** 2); f2 = f1 * 1.06  # minor-second rub, rising
    pad = (tone(f1, n) + tone(f2, n)) * 0.5 * t ** 1.8
    pad = signal.sosfilt(signal.butter(2, 1800, fs=SR, output="sos"), pad)
    x = 0.9 * air + 0.8 * beat + 0.35 * pad
    x[-int(SR * 0.08):] *= np.linspace(1, 0.15, int(SR * 0.08))
    return norm(x, 1)


SOUNDS = dict(whoosh=lambda: s_swoosh(0.5, True), whoosh_out=lambda: s_swoosh(0.45, False), soft=lambda: s_swoosh(0.38, True, 0.8),
              sw_deep=lambda: s_swoosh_v("deep"), sw_air=lambda: s_swoosh_v("air"), sw_whip=lambda: s_swoosh_v("whip"),
              sw_shimmer=lambda: s_swoosh_v("shimmer"), sw_reverse=lambda: s_swoosh_v("reverse"),
              riser=s_riser_clean,
              boom=s_boom, hit=s_hit, pop=s_pop, tick=s_tick, type=s_type, ding=s_ding, swish=s_swish, shutter=s_shutter)
GAIN = dict(whoosh=.20, whoosh_out=.15, soft=.11, riser=.17, sw_deep=.24, sw_air=.17, sw_whip=.13, sw_shimmer=.15, sw_reverse=.15, boom=.42, hit=.34, pop=.16, tick=.10, type=.09, ding=.15,
            swish=.12, shutter=.14)


# ----------------------------------------------------------------- cues from the scene HTML
def scene_events_clean(o):
    """Lloyd 2026-10-15: minimal + clean — swooshes on transitions only (no pops/ticks/booms/hits)."""
    hp = SCENES / f"{o['id']}.html"
    if not hp.exists():
        return []
    h, at, dur, kind = hp.read_text(), o["at"], o["dur"], o.get("kind", "")
    ROT["n"] += 1
    swap = ("sw_whip", "sw_shimmer", "sw_air")[ROT["n"] % 3]
    slides = [(at + t, "sw_air") for t in map(float, re.findall(r'data-cat="([\d.]+)"', h)) if 0.35 <= t <= dur - 0.25]  # carousel cards
    if kind == "news":
        cues = [(at, ("sw_deep", "sw_air")[ROT["n"] % 2])] if 'data-win="1"' in h else [(at + 0.05, swap)]
        if 'data-wout="1"' in h and dur > 1.2:
            cues.append((at + dur - 0.5, "sw_reverse"))
        return cues + slides
    if kind in ("glass", "full"):
        return [(at, "sw_deep")] + slides
    if kind == "shrink":  # the footage shrinks into its card, then grows back
        return [(at + 0.02, "sw_air"), (at + dur - (o.get("card") or {}).get("tout", 0.45), "sw_reverse")] + slides
    if kind == "tag":  # v6 on-screen tags: one soft air swoosh as the tag slides in (alternating texture)
        return [(at + 0.02, ("sw_air", "sw_shimmer")[ROT["n"] % 2])]
    if kind in ("lockup", "thumb", "behind"):
        return [(at + 0.02, "sw_whip" if kind == "lockup" else "sw_shimmer")]
    return []


ROT = {"n": 0}


def scene_events(o):
    """(t, sound) cues inside one overlay, read from the composition mograph rendered."""
    hp = SCENES / f"{o['id']}.html"
    if not hp.exists():
        return []
    h = hp.read_text()
    at, dur, kind = o["at"], o["dur"], o.get("kind", "")
    cues = []
    if kind == "news":
        if 'data-win="1"' in h:
            cues.append((at + 0.0, "whoosh"))
        if 'data-wout="1"' in h and dur > 1.2:
            cues.append((at + dur - 0.5, "whoosh_out"))
    elif kind in ("glass", "full", "shrink"):
        cues.append((at + 0.0, "whoosh"))
    elif kind == "thumb":
        for k, t in enumerate(sorted(float(x) for x in re.findall(r'data-tat="([\d.]+)"', h))):
            cues.append((at + t, "hit" if k else "boom"))
        return cues
    elif kind == "lockup":
        cues.append((at + 0.02, "swish"))
        for m in re.finditer(r'data-lk="([\d.]+)" data-kind="(xl|tag)"', h):
            cues.append((at + float(m.group(1)), "pop"))
        return cues
    # element-level events (skip the first 0.35 s — the page entrance already has its whoosh)
    if kind == "news" and 'data-win="0"' in h:  # chained page: content swap gets a light swish
        cues.append((at + 0.05, "swish"))
    for m in re.finditer(r'<[^>]*data-at="([\d.]+)"[^>]*>', h):
        t, rest = float(m.group(1)), m.group(0)
        an = re.search(r'data-anim="([a-z]+)"', rest)
        an = an.group(1) if an else "up"
        if t < 0.35 or t > dur - 0.25:
            continue
        if an == "count":
            md = re.search(r'data-dur="([\d.]+)"', rest)
            d = float(md.group(1)) if md else 1.1
            k = 0.0
            while k < d:
                cues.append((at + t + k, "tick"))
                k += 0.075
            cues.append((at + t + d, "ding"))
        elif an == "type":
            cues.append((at + t, "type"))
        elif an == "stamp":
            cues.append((at + t + 0.2, "hit"))
        elif an in ("pop", "left", "right", "glass", "drop", "big", "shake"):
            cues.append((at + t, "pop"))
    for m in re.finditer(r'data-mark="([\d.]+)"', h):
        cues.append((at + float(m.group(1)), "swish"))
    for m in re.finditer(r'data-cat="([\d.]+)"', h):  # carousel card slides in
        cues.append((at + float(m.group(1)), "swish"))
    for m in re.finditer(r'data-kb="([\d.]+)"', h):  # screenshot jump-zoom
        cues.append((at + float(m.group(1)), "shutter"))
    return cues


def thin(cues, gap=0.28):
    """never two light cues closer than `gap` (keeps it musical, not clicky)."""
    light = {"pop", "tick", "swish", "shutter", "soft", "sw_whip", "sw_shimmer", "sw_air"}
    out, last = [], -9.0
    for t, s in sorted(cues):
        if s in light and s != "tick" and t - last < gap:
            continue
        out.append((t, s))
        if s in light and s != "tick":
            last = t
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--level", type=float, default=1.0)
    ap.add_argument("--no-riser", action="store_true")
    ap.add_argument("--style", default="clean", choices=["clean", "full"], help="clean = swooshes only (default)")
    a = ap.parse_args()
    src, wd, meta = vedit.ctx(a.video)
    dec = vedit.jload(wd / "decisions.json", {})
    edl = vedit.jload(wd / "edl.json") or vedit.die("run plan first")
    ovs = sorted(dec.get("overlays", []), key=lambda o: o["at"])
    cues = []
    for o in ovs:
        cues += scene_events(o) if a.style == "full" else scene_events_clean(o)
        cues += [(o["at"] + float(off), name) for off, name in o.get("sfx", [])]  # explicit cues from scenes.json
    # hook riser: builds through the hook and lands (boom) on the first page reveal after it
    first = (next((o for o in ovs if o.get("riser")), None)
             or next((o for o in ovs if o.get("kind") in ("news", "glass", "full") and o["at"] > 1.5), None))
    if first and not a.no_riser:
        land = first["at"] + 0.05
        if a.style == "full":
            cues.append((max(0.0, land - 3.6), f"riser:{min(3.6, land):.2f}"))
            cues.append((land, "boom"))
        else:  # suspense build that hands over to the page swoosh; the footage pushes in while it builds
            r0 = max(0.9, land - 3.2)
            cues.append((r0, f"riser:{land - r0:.2f}"))
            dec["hook_zoom"] = {"pop_out": [0.0, 0.6], "push_in": [round(r0, 3), round(land, 3)]}
    cues = thin(cues, 0.6)
    vedit.jsave(wd / "decisions.json", dec)
    n = int((edl["new_dur"] + 2) * SR)
    track = np.zeros(n)
    bank = {}
    for t, s in cues:
        name, _, arg = s.partition(":")
        if name == "riser":
            snd = s_riser_suspense(float(arg)) if a.style == "clean" else s_riser(float(arg))
        else:
            snd = bank.setdefault(name, SOUNDS[name]())
        i = int(t * SR)
        seg = snd[: max(0, n - i)] * GAIN[name] * a.level
        track[i:i + len(seg)] += seg
    peak = np.abs(track).max()
    if peak > 0.95:
        track *= 0.95 / peak
    out = wd / "sfx.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    dec["sfx_track"] = str(out.relative_to(ROOT))
    vedit.jsave(wd / "decisions.json", dec)
    kinds = {}
    for _, s in cues:
        kinds[s.split(":")[0]] = kinds.get(s.split(":")[0], 0) + 1
    print(f"✓ {len(cues)} sfx cues → {out.relative_to(ROOT)}  " + " ".join(f"{k}×{v}" for k, v in sorted(kinds.items())))


if __name__ == "__main__":
    main()
