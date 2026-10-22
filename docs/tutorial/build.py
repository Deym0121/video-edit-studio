#!/usr/bin/env python3
"""Studio tutorial — a screen-share walkthrough from the GitHub page to the first export (16:9, about 2 min, no voice).

It plays like a screen recording of a Mac: a browser, Terminal and Finder, a cursor that moves, clicks, types and
drags, auto-zoom on whatever it touches, arrows with short labels, and keystroke pills. The Studio screens are real
captures (capture.mjs → shots/). The only sound is clicks and keys, so your voiceover sits on top cleanly.

The voiceover script drives the pacing: each line gets the time it needs at a calm speaking pace (WPS), and the
actions it describes happen while it is said. The same lines are written out with their start times.

  hf/index.html            HyperFrames page (1920×1080, one GSAP timeline)
  VOICEOVER.md             the script with the time each line starts (English + Taglish)
  voiceover_en.srt / _tl   the same lines as cues: a teleprompter, or subtitles once you've recorded
  audio.wav                clicks, keys and soft whooshes

usage:  ../../.venv/bin/python build.py            page + script + audio (runs measure.mjs with the bundled node)
        ../../.venv/bin/python build.py --render   … and render → Studio_Tutorial.mp4
"""
import collections
import html
import json
import math
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import signal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sfx as S  # noqa: E402

OWNER = "Deym0121"
REPO = f"github.com/{OWNER}/video-edit-studio"
SHOTS = json.loads((HERE / "shots" / "layout.json").read_text())
NODE = ROOT / "tools/node/bin/node"
WPS = 2.6  # voiceover pace, words per second
# the recorded voiceover (vo/NNN.mp3, one clip per line, trimmed to the speech in vo/lines.json) and the music bed
VOICE = {o["en"]: o for o in json.loads((HERE / "vo" / "lines.json").read_text())} if (HERE / "vo" / "lines.json").exists() else {}
MUSIC = ROOT / "assets/music/pixabay_solvik_emotional_uplifting_611149.mp3"  # Pixabay licence: fine inside a published video
FFMPEG = ROOT / ".venv/lib/python3.12/site-packages/static_ffmpeg/bin/darwin_arm64/ffmpeg"
NSTEPS = 9

# ---------------------------------------------------------------- desktop geometry (desktop px = frame px at zoom 1)
W, H = 1920, 1080
BX, BY = 240, 44             # browser window; its page is 1440×900 under an 86 px chrome
PX, PY = BX, BY + 86         # page origin, so Studio screenshot px map 1:1
TX, TY, TW, TH = 330, 96, 1260, 800  # Terminal
FX, FY, FW, FH = 40, 580, 600, 390   # Finder
LH, VR, CW = 32, 23, 12.64   # terminal line height, visible rows, Menlo 21 px character width
TOP = TY + 48                # first terminal row
BRIEF = "yellow keywords, big captions at the bottom, fast cuts"  # the brief typed in the video (capture.mjs draws the same one)
NOTE = "cut the dead air"   # the Talk-to-edit note typed in the video (capture.mjs draws the same one)
PROMPT0 = '<span class="pu">you@Mac</span> <span class="pd">~</span> % '
PROMPT1 = '<span class="pu">you@Mac</span> <span class="pd">video-edit-studio</span> % '


def SR(shot, key):
    x, y, w, h = SHOTS[shot]["rects"][key]
    return [PX + x, PY + y, w, h]


def C(r):
    return r[0] + r[2] / 2, r[1] + r[3] / 2


def esc(s):
    return html.escape(s, quote=False)


def qlen(p0, p1, p2, k=24):
    pts = [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])
           for u in (i / k for i in range(k + 1))]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(k))


# ---------------------------------------------------------------- timeline builder
class Tl:
    def __init__(s, tg):
        s.tg = tg  # measured targets of the mock windows
        s.t = 0.0
        s.js, s.desk, s.over, s.term, s.snd, s.page = [], [], [], [], [], []
        s.cams = [(0.0, 1.0)]
        s.cur = [1180.0, 720.0]
        s.n = 0
        s.drag = False
        s.row = s.scroll = 0
        s.vo, s.chapters = [], []

    def uid(s, p="e"):
        s.n += 1
        return f"{p}{s.n}"

    def j(s, x):
        s.js.append(x)

    def wait(s, d):
        s.t += d

    def z(s, t=None):
        t = s.t if t is None else t
        return [k[1] for k in sorted(s.cams) if k[0] <= t + 1e-6][-1]

    # -- voiceover lines + chapters
    @staticmethod
    def need(en):
        """Seconds a voiceover line needs: its recorded length (+ a breath) once it's recorded, else a calm reading pace."""
        v = VOICE.get(en)
        base = len(en.split()) / WPS + .45
        return max(base, v["end"] - v["start"] + .7) if v else base

    def pad(s):
        if s.vo:
            s.t = max(s.t, s.vo[-1][0] + s.need(s.vo[-1][2]))

    def until(s, frac):
        """Wait until this share of the current voiceover line has been said."""
        if s.vo:
            s.t = max(s.t, s.vo[-1][0] + s.need(s.vo[-1][2]) * frac)

    def B(s, en, tl_):
        """A voiceover line starts here. The line before it gets the time it needs first."""
        s.pad()
        s.vo.append([round(s.t, 2), len(s.chapters), en, tl_])

    def chapter(s, n, en, tl_, cam=None):
        """A new step: a full-screen title card wipes across (the camera resets behind it), then the step chip stays bottom-left."""
        s.pad()
        prev = [c for c in s.chapters if c[1]]
        if prev:
            s.j(f"tl.to(Q('chip{prev[-1][1]}'), {{autoAlpha: 0, y: -14, duration: .25}}, {s.t - .05:.3f});")
        s.chapters.append((round(s.t, 2), n, en, tl_))
        if n:
            k = f"stc{n}"
            s.over.append(f'<div class="stc hid" id="{k}"><div class="sk">STEP {n} OF {NSTEPS}</div><h2 id="{k}h">{esc(en)}</h2><div class="sb"></div>'
                          f'<div class="sn">{n}</div></div>')
            s.j(f"tl.fromTo(Q('{k}'), {{autoAlpha: 1, clipPath: 'inset(0% 100% 0% 0%)'}}, {{clipPath: 'inset(0% 0% 0% 0%)', duration: .38, ease: 'power3.inOut'}}, {s.t:.3f});"
                f"tl.from(Q('{k}h'), {{x: -70, opacity: 0, duration: .5, ease: 'expo.out'}}, {s.t + .18:.3f});"
                f"tl.to(Q('{k}'), {{clipPath: 'inset(0% 0% 0% 100%)', duration: .38, ease: 'power3.inOut'}}, {s.t + 1.05:.3f});"
                f"tl.set(Q('{k}'), {{autoAlpha: 0}}, {s.t + 1.45:.3f});")
            s.snd.append((s.t, "whoosh", .6))
            if cam:
                s.cam(*cam, d=.05, t=s.t + .45)
            s.t += 1.3
            cid = f"chip{n}"
            s.over.append(f'<div class="chip hid" id="{cid}"><i>{n}</i><div><em>STEP {n} OF {NSTEPS}</em><span>{esc(en)}</span></div></div>')
            s.j(f"tl.fromTo(Q('{cid}'), {{autoAlpha: 0, y: 20}}, {{autoAlpha: 1, y: 0, duration: .4, ease: 'back.out(1.6)'}}, {s.t:.3f});")

    # -- camera
    def cam(s, sc, cx, cy, d=.9, t=None):
        t = s.t if t is None else t
        x = min(0, max(W - W * sc, W / 2 - cx * sc))
        y = min(0, max(H - H * sc, H / 2 - cy * sc))
        s.j(f"tl.to(D, {{scale: {sc}, x: {x:.1f}, y: {y:.1f}, duration: {d}, ease: 'power3.inOut'}}, {t:.3f});")
        s.cams.append((t + d * .6, sc))

    # -- cursor
    def move(s, x, y, d=None):
        x0, y0 = s.cur
        d = d or min(1.0, max(.4, .32 + math.hypot(x - x0, y - y0) / 1600))
        for el, ox, oy in [("CU", 0, 0)] + ([("GH", -40, -30)] if s.drag else []):
            s.j(f"tl.to({el}, {{x: {x + ox:.1f}, duration: {d:.2f}, ease: 'power2.inOut'}}, {s.t:.3f});"
                f"tl.to({el}, {{y: {y + oy:.1f}, duration: {d:.2f}, ease: 'sine.inOut'}}, {s.t:.3f});")
        s.cur = [x, y]
        s.t += d

    def click(s, quiet=False):
        x, y = s.cur
        r = s.uid("rp")
        s.desk.append(f'<b class="rip" id="{r}" style="left:{x:.0f}px;top:{y:.0f}px"></b>')
        s.j(f"tl.to(CU, {{scale: .8, duration: .07, yoyo: true, repeat: 1}}, {s.t:.3f});"
            f"tl.set(Q('{r}'), {{scale: .25, opacity: .95}}, {s.t:.3f}); tl.to(Q('{r}'), {{scale: 1, opacity: 0, duration: .5, ease: 'power2.out'}}, {s.t:.3f});")
        s.snd.append((s.t, "click", .6 if quiet else 1))
        s.t += .18

    def go(s, r, dx=0, dy=0, pause=.12):
        x, y = C(r)
        s.move(x + dx, y + dy)
        s.wait(pause)
        s.click()

    # -- showing things
    def show(s, el, t=None, d=.25, frm="{autoAlpha: 0}", to="{autoAlpha: 1}"):
        t = s.t if t is None else t
        s.j(f"tl.fromTo(Q('{el}'), {frm}, {{...{to}, duration: {d}, ease: 'power2.out'}}, {t:.3f});")

    def hide(s, el, t=None, d=.2):
        t = s.t if t is None else t
        s.j(f"tl.to(Q('{el}'), {{autoAlpha: 0, duration: {d}}}, {t:.3f});")

    def set(s, el, props, t=None):
        t = s.t if t is None else t
        s.j(f"tl.set(Q('{el}'), {props}, {t:.3f});")

    def shot(s, new, old=None, mode="cut", t=None):
        t = s.t if t is None else t
        if mode == "scroll" and old:  # same page, further down: the new view slides up into place over the old one
            s.j(f"tl.fromTo(Q('sh_{new}'), {{autoAlpha: 0, y: 36}}, {{autoAlpha: 1, y: 0, duration: .28, ease: 'power2.out'}}, {t:.3f});"
                f"tl.to(Q('sh_{old}'), {{autoAlpha: 0, duration: .2}}, {t + .12:.3f});")
        else:
            s.j(f"tl.fromTo(Q('sh_{new}'), {{autoAlpha: 0, y: 0}}, {{autoAlpha: 1, duration: .14}}, {t:.3f});")
            if old:
                s.j(f"tl.to(Q('sh_{old}'), {{autoAlpha: 0, duration: .14}}, {t + .1:.3f});")

    # -- typing: one hidden <i> per character, revealed in turn (seek-safe, no callbacks)
    def chars(s, text):
        i = s.uid("ty")
        return i, f'<span id="{i}">' + "".join(f"<i>{esc(c)}</i>" for c in text) + "</span>"

    def type_in(s, span, n, cps=15, t=None):
        t = s.t if t is None else t
        for k in range(n):
            s.j(f"tl.set(Q('{span}').children[{k}], {{display: 'inline'}}, {t + k / cps:.3f});")
        s.snd.append((t, "type", n / cps))
        s.t = t + n / cps

    def paste(s, span, t=None):
        s.j(f"tl.set(Q('{span}').children, {{display: 'inline'}}, {s.t if t is None else t:.3f});")

    def keys(s, *ks, t=None, hold=1.0):
        t = s.t if t is None else t
        k = s.uid("kp")
        s.over.append(f'<div class="kp hid" id="{k}">' + "".join(f"<kbd>{esc(x)}</kbd>" for x in ks) + "</div>")
        s.j(f"tl.fromTo(Q('{k}'), {{autoAlpha: 0, y: 24, scale: .9}}, {{autoAlpha: 1, y: 0, scale: 1, duration: .22, ease: 'back.out(2)'}}, {t:.3f});"
            f"tl.to(Q('{k}'), {{autoAlpha: 0, y: 10, duration: .25}}, {t + hold:.3f});")
        s.snd.append((t, "key", 1))
        s.t = t + .3

    # -- annotations: they live on the desktop so they ride the camera, sized for the zoom they're seen at
    def note(s, text, target, dx, dy, t=None, hold=2.8, bend=1):
        t = s.t if t is None else t
        z = s.z(t + .4)
        tx, ty = target
        fs, pdx, pdy = 29 / z, 19 / z, 10 / z
        lw, lh = len(text) * fs * .53 + 2 * pdx, fs * 1.2 + 2 * pdy
        lx, ly = tx + dx / z, ty + dy / z
        vx, vy = tx - lx, ty - ly
        if abs(vx) * lh > abs(vy) * lw:
            sx, sy = lx + math.copysign(lw / 2 + 8 / z, vx), ly
        else:
            sx, sy = lx, ly + math.copysign(lh / 2 + 8 / z, vy)
        L = math.hypot(tx - sx, ty - sy) or 1
        ex, ey = tx - (tx - sx) / L * 10 / z, ty - (ty - sy) / L * 10 / z
        nx, ny = -(ey - sy) / L, (ex - sx) / L
        cx, cy = (sx + ex) / 2 + nx * .22 * L * bend, (sy + ey) / 2 + ny * .22 * L * bend
        ux, uy = ex - cx, ey - cy
        ul = math.hypot(ux, uy) or 1
        ux, uy = ux / ul, uy / ul
        hl, a = 20 / z, math.radians(30)
        h1 = (ex - hl * (ux * math.cos(a) - uy * math.sin(a)), ey - hl * (uy * math.cos(a) + ux * math.sin(a)))
        h2 = (ex - hl * (ux * math.cos(a) + uy * math.sin(a)), ey - hl * (uy * math.cos(a) - ux * math.sin(a)))
        plen = qlen((sx, sy), (cx, cy), (ex, ey))
        i = s.uid("nt")
        sw = 4.5 / z
        d = f"M{sx:.1f} {sy:.1f} Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}"
        hd = f"M{h1[0]:.1f} {h1[1]:.1f} L{ex:.1f} {ey:.1f} L{h2[0]:.1f} {h2[1]:.1f}"
        s.desk.append(
            f'<svg class="ar" id="{i}a" viewBox="0 0 {W} {H}"><path d="{d}" class="sh" style="stroke-width:{sw * 2.4:.2f}px;stroke-dasharray:{plen:.1f};stroke-dashoffset:{plen:.1f}" id="{i}ps"/>'
            f'<path d="{d}" id="{i}p" style="stroke-width:{sw:.2f}px;stroke-dasharray:{plen:.1f};stroke-dashoffset:{plen:.1f}"/>'
            f'<path d="{hd}" class="sh hd" id="{i}hs" style="stroke-width:{sw * 2.4:.2f}px"/><path d="{hd}" class="hd" id="{i}h" style="stroke-width:{sw:.2f}px"/></svg>'
            f'<div class="nl hid" id="{i}" style="left:{lx:.1f}px;top:{ly:.1f}px;font-size:{fs:.2f}px;padding:{pdy:.2f}px {pdx:.2f}px;'
            f'border-radius:{lh:.1f}px;box-shadow:0 {8 / z:.1f}px {24 / z:.1f}px rgba(0,0,0,.45)">{esc(text)}</div>')
        s.j(f"tl.fromTo(Q('{i}'), {{autoAlpha: 0, scale: .6, xPercent: -50, yPercent: -50}}, {{autoAlpha: 1, scale: 1, xPercent: -50, yPercent: -50, duration: .3, ease: 'back.out(2)'}}, {t:.3f});"
            f"tl.set(Q('{i}a'), {{autoAlpha: 1}}, {t + .1:.3f});"
            f"tl.to([Q('{i}p'), Q('{i}ps')], {{strokeDashoffset: 0, duration: .35, ease: 'power2.out'}}, {t + .12:.3f});"
            f"tl.fromTo([Q('{i}h'), Q('{i}hs')], {{opacity: 0}}, {{opacity: 1, duration: .1}}, {t + .42:.3f});"
            f"tl.to([Q('{i}'), Q('{i}a')], {{autoAlpha: 0, duration: .25}}, {t + hold:.3f});")
        s.snd.append((t, "pop", 1))

    def ring(s, r, t=None, hold=2.4, pad=8):
        t = s.t if t is None else t
        z = s.z(t + .4)
        p, b = pad / z, 4 / z
        i = s.uid("rg")
        s.desk.append(f'<b class="rg hid" id="{i}" style="left:{r[0] - p - b:.1f}px;top:{r[1] - p - b:.1f}px;width:{r[2] + 2 * (p + b):.1f}px;'
                      f'height:{r[3] + 2 * (p + b):.1f}px;border-width:{b:.2f}px;border-radius:{12 / z:.1f}px"></b>')
        s.j(f"tl.fromTo(Q('{i}'), {{autoAlpha: 0, scale: 1.12}}, {{autoAlpha: 1, scale: 1, duration: .3, ease: 'back.out(2)'}}, {t:.3f});"
            f"tl.to(Q('{i}'), {{autoAlpha: 0, duration: .25}}, {t + hold:.3f});")

    def flip(s):
        """The hovered 2026 card plays: its captured frames, one per video frame; the last one holds until it's hidden."""
        P = SHOTS["play"]
        s.set("flip", "{autoAlpha: 1}")
        for k in range(P["frames"]):
            s.set(f"fp{k}", "{visibility: 'visible'}", s.t + k / P["fps"])
            if k:
                s.set(f"fp{k - 1}", "{visibility: 'hidden'}", s.t + k / P["fps"])

    def typebox(s, shot, key, text, cps=14, top=False):
        """Type into a Studio text field: a focused field drawn over the screenshot. Returns its id (hide it when the real shot takes over)."""
        x, y, w, h = SHOTS[shot]["rects"][key]
        sp, ch = s.chars(text)
        i = s.uid("tb")
        tops = ";align-items:flex-start;padding-top:9px" if top else ""
        s.page.append(f'<div class="tbx hid" id="{i}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px{tops}">{ch}<b class="tcar"></b></div>')
        s.show(i, d=.05)
        s.wait(.15)
        s.type_in(sp, len(text), cps)
        s.wait(.2)
        return i

    def drag_to(s, ghost, tx, ty, d=1.2):
        x0, y0 = s.cur
        s.snd.append((s.t, "click", .5))
        s.j(f"tl.set(Q('{ghost}'), {{x: {x0 - 40:.1f}, y: {y0 - 30:.1f}}}, {s.t:.3f});")
        s.show(ghost, d=.1)
        s.wait(.1)
        for el, ox, oy in (("CU", 0, 0), (f"Q('{ghost}')", -40, -30)):
            s.j(f"tl.to({el}, {{x: {tx + ox:.1f}, duration: {d}, ease: 'power2.inOut'}}, {s.t:.3f}); tl.to({el}, {{y: {ty + oy:.1f}, duration: {d}, ease: 'sine.inOut'}}, {s.t:.3f});")
        s.cur = [tx, ty]
        s.t += d
        s.click(quiet=True)
        s.hide(ghost, d=.1)

    def badge(s, text, t, hold):
        i = s.uid("ff")
        s.over.append(f'<div class="ff hid" id="{i}"><b>⏩ SPED UP</b><span>{esc(text)}</span></div>')
        s.j(f"tl.fromTo(Q('{i}'), {{autoAlpha: 0, y: 20}}, {{autoAlpha: 1, y: 0, duration: .3, ease: 'back.out(1.6)'}}, {t:.3f});"
            f"tl.to(Q('{i}'), {{autoAlpha: 0, duration: .25}}, {t + hold:.3f});")

    # -- terminal: absolute rows; the view scrolls once the text reaches the bottom
    def tline(s, inner, t=None, rows=1, cls=""):
        t = s.t if t is None else t
        i = s.uid("tl")
        s.term.append(f'<div class="tl {cls}" id="{i}" style="top:{s.row * LH}px">{inner}</div>')
        s.set(i, "{visibility: 'visible'}", t)
        s.row += rows
        need = max(0, s.row - VR)
        if need > s.scroll:
            s.scroll = need
            s.j(f"tl.to(Q('tsc'), {{y: {-need * LH}, duration: .16, ease: 'power2.out'}}, {t:.3f});")
        return i

    def row_y(s, row, frac=.5):
        """Desktop y of a terminal row, with the scroll as it is now."""
        return TOP + (row - s.scroll + frac) * LH

    def tcmd(s, prompt, text, paste_text="", cps=15):
        """A prompt, typed text (+ an optional ⌘V paste), then Return."""
        a, ah = s.chars(text)
        b, bh = s.chars(paste_text) if paste_text else ("", "")
        ca = s.uid("ca")
        s.tline(f'{prompt}{ah}{bh}<i class="caret" id="{ca}"></i>')
        s.wait(.35)
        s.type_in(a, len(text), cps)
        if paste_text:
            s.wait(.2)
            s.keys("⌘", "V")
            s.paste(b, t=s.t - .25)
            s.wait(.35)
        s.wait(.25)
        s.keys("Return")
        s.set(ca, "{display: 'none'}")


# ---------------------------------------------------------------- the mock apps
def gh_page():
    folder = '<svg viewBox="0 0 16 16" class="ic dir"><path d="M1.5 3h4l1.4 1.6h7.6v8.4h-13z"/></svg>'
    file = '<svg viewBox="0 0 16 16" class="ic fil"><path d="M3.5 1.5h6l3 3v10h-9z" fill="none" stroke-width="1.3"/></svg>'
    rows = [("d", ".claude", "Studio v2: Edit Health, Hook Lab, Post Kit", "2 hours ago"), ("d", "docs", "Tutorial + English and Taglish guides", "1 hour ago"),
            ("d", "reference", "2026 motion research", "2 hours ago"), ("d", "tools", "Studio v2: Edit Health, Hook Lab, Post Kit", "2 hours ago"),
            ("f", ".gitignore", "Keep videos and renders out of git", "2 hours ago"), ("f", "CLAUDE.md", "Install steps for Claude", "2 hours ago"),
            ("f", "DESIGN_SYSTEM.md", "Natural colour rule", "3 hours ago"), ("f", "README.md", "Link the guides", "1 hour ago"),
            ("f", "STUDIO_GUIDE.md", "Studio v2 table", "2 hours ago"), ("f", "vedit", "Editor CLI", "3 days ago")]
    fr = "".join(f'<div class="fr">{folder if k == "d" else file}<span class="fn">{n}</span><span class="fm">{m}</span><span class="ft">{a}</span></div>' for k, n, m, a in rows)
    copy = '<svg viewBox="0 0 16 16" id="cp1"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M11 3.5V2.8c0-.7-.5-1.3-1.2-1.3H3c-.8 0-1.5.6-1.5 1.4v6.8c0 .7.6 1.3 1.3 1.3h.7"/></svg>'
    check = '<svg viewBox="0 0 16 16" id="cp2" class="hid"><path d="M2.5 8.5l3.5 3.5 7.5-8"/></svg>'
    return f'''<div class="pg gh hid" id="pg_gh">
  <div class="gt"><span class="gm">☰</span><span class="glogo"></span><span class="gc">{OWNER} <i>/</i> <b>video-edit-studio</b></span><span class="grow"></span>
    <span class="gs">Type <kbd>/</kbd> to search</span><span class="gme">J</span></div>
  <div class="gtabs"><span class="on">&lt;&gt; Code</span><span>Issues</span><span>Pull requests</span><span>Actions</span><span>Projects</span><span>Security</span><span>Insights</span></div>
  <div class="gw">
    <div class="gti"><span class="gav">J</span><b>video-edit-studio</b><em>Public</em><span class="grow"></span><span class="btn">Watch <s>1</s></span><span class="btn">Fork <s>0</s></span><span class="btn">☆ Star <s>0</s></span></div>
    <div class="gcols"><div class="gmain">
      <div class="gbar"><span class="btn">main ▾</span><span class="mut">1 Branch</span><span class="mut">0 Tags</span><span class="grow"></span><span class="ggo">Go to file</span><span class="btn">Add file ▾</span>
        <span class="codew"><span class="btn green" id="gh_code" data-t="gh_code">&lt;&gt;&nbsp; Code ▾</span>
          <div class="pop hid" id="gh_pop">
            <div class="ptab"><span class="on">Local</span><span>Codespaces</span></div>
            <div class="pbody"><div class="phd">Clone</div><div class="psub"><span class="on">HTTPS</span><span>SSH</span><span>GitHub CLI</span></div>
              <div class="purl"><span>https://{REPO}.git</span><span class="cp" data-t="gh_copy">{copy}{check}</span></div><div class="pmut">Clone using the web URL.</div></div>
            <div class="prow">Open with GitHub Desktop</div><div class="prow" data-t="gh_zip">Download ZIP</div>
            <div class="tip hid" id="gh_tip">Copied!</div>
          </div></span></div>
      <div class="gfiles"><div class="fh"><span class="gav s">J</span><b>{OWNER}</b><span class="fm">Tutorial + English and Taglish guides</span><span class="ft">1 hour ago · 24 commits</span></div>{fr}</div>
      <div class="grd"><div class="grh">README</div><h1>Video Edit with Claude — Studio</h1>
        <p><b>Your own AI video editor, on your Mac.</b> Drop in a talking-head or screen-demo video. Claude cuts the retakes, repeats and dead air,
        writes the captions, places motion graphics that never cover your face, and adds sound effects.</p></div>
    </div><div class="gside"><h3>About</h3><p>Your own AI video editor, on your Mac: a step-by-step Studio + Claude.</p>
      <div class="topics"><span>video-editing</span><span>claude</span><span>macos</span><span>ai</span></div>
      <div class="sl">Readme</div><div class="sl">Activity</div><div class="sl">1 star · 1 watching · 0 forks</div></div></div>
  </div></div>'''


def browser(om_html, page_extra="", gq_html=""):
    shots = "".join(f'<img class="sh hid" id="sh_{k}" src="assets/{k}.jpg" alt="">' for k in SHOTS if k != "play")
    x, y, w, h = SHOTS["play"]["rect"]
    shots += (f'<div class="hid" id="flip" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
              + "".join(f'<img id="fp{k}" src="assets/play/{k:03d}.jpg" alt="" style="position:absolute;inset:0;width:100%;height:100%;visibility:hidden">'
                        for k in range(SHOTS["play"]["frames"])) + "</div>" + page_extra)
    return f'''<div class="win br" id="wB" style="left:{BX}px;top:{BY}px;width:1440px;height:986px;z-index:10">
  <div class="btabs"><span class="lights"><i></i><i></i><i></i></span>
    <span class="tab on" id="tab1"><s class="fav gh"></s><span><b id="t1a">New Tab</b><b id="t1b" class="dn">GitHub</b><b id="t1c" class="dn">Search · video edit studio</b><b id="t1d" class="dn">{OWNER}/video-edit-studio</b></span><em>×</em></span>
    <span class="tab" id="tab2"><s class="fav st">J</s><span id="tab2a">New Tab</span><span id="tab2b" class="dn">Studio</span><em>×</em></span>
    <span class="plus" data-t="br_plus">+</span></div>
  <div class="bbar"><span class="nav">‹&nbsp;&nbsp;›&nbsp;&nbsp;↻</span><div class="omni" data-t="br_omni"><s class="lock"></s>
    <span id="om2" class="mut">Search or type a URL</span>{om_html}<b class="ocaret" id="omc"></b><span id="o_gh" class="dn">github.com</span>
    <span id="o_srch" class="dn">github.com/search?q=video+edit+studio&amp;type=repositories</span><span id="o_repo" class="dn">{REPO}</span>
    <span id="o_st" class="dn">localhost:8765</span></div>
    <span class="dlb hid" id="dlb" data-t="dl_btn"><svg viewBox="0 0 24 24"><path d="M12 4v11M7 10l5 5 5-5M5 19h14"/></svg></span><span class="dots">⋮</span>
    <div class="dlpop hid" id="dlpop"><div class="dlh">Recent downloads</div><div class="dlr" data-t="dl_item"><s class="zipi"></s><div><b>video-edit-studio-main.zip</b><small>9.8 MB · Done</small></div></div></div></div>
  <div class="bpage">{gh_page()}{gh_home(gq_html)}{gh_results()}<div class="pg np" id="pg_new"><div class="npl">Search or type a URL</div></div>
    <div class="pg st" id="pg_st">{shots}</div></div></div>'''


GH_HEAD = """<div class="gt"><span class="gm">☰</span><span class="glogo"></span><b class="gdash">Dashboard</b><span class="grow"></span>
    <span class="gs" %s>Type <kbd>/</kbd> to search</span><span class="gme">J</span></div>"""


def gh_home(gq_html=""):
    feed = "".join(f'<div class="gfc"><span class="gav s">{a}</span><div><b>{t}</b><small>{d}</small></div></div>'
                   for a, t, d in [("J", "You starred 3 repositories", "2 days ago"), ("J", "New release of a tool you follow", "4 days ago"), ("J", "Your weekly digest", "1 week ago")])
    return f'''<div class="pg gh hid" id="pg_home">{GH_HEAD % 'data-t="gh_search"'}
  <div class="ghome"><div class="gleft"><h4>Top repositories</h4><div class="gli"></div><div class="gli s"></div><div class="gli"></div></div>
    <div class="gfeed"><h2>Home</h2>{feed}</div></div>
  <div class="gsq hid" id="gh_sq"><svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6.5"/><path d="M15 15l5.5 5.5"/></svg>{gq_html}<b class="qcar"></b></div></div>'''


def gh_results():
    return f'''<div class="pg gh hid" id="pg_srch">{GH_HEAD % ""}
  <div class="gres"><div class="gfil"><h4>Filter by</h4><div class="on">Repositories <s>1</s></div><div>Code</div><div>Issues</div><div>Users</div></div>
    <div class="glist"><h3>1 result</h3><div class="grc"><div class="grt" data-t="sr_repo"><span class="gav s">J</span><a>{OWNER}/<b>video-edit-studio</b></a></div>
      <p>Your own AI video editor, on your Mac: a step-by-step Studio + Claude. Cuts, captions, motion graphics.</p>
      <div class="gtg"><span>video-editing</span><span>claude</span><span>macos</span></div><div class="gmeta">● Python · ☆ 1 · Updated today</div></div></div></div></div>'''


def downloads():
    return f'''<div class="win fnd hid" id="wD" style="left:60px;top:560px;width:640px;height:400px;z-index:35">
  <div class="fbar"><span class="lights"><i></i><i></i><i></i></span><b>Downloads</b></div>
  <div class="fside"><em>Favourites</em><span>Recents</span><span>Applications</span><span>Desktop</span><span>Documents</span><span class="on">Downloads</span></div>
  <div class="fgrid"><div class="fi" data-t="d_zip"><s class="zipi big"></s><span>video-edit-studio-main.zip</span></div>
    <div class="fi hid" id="d_fold" data-t="d_fold"><s class="fold"></s><span>video-edit-studio-main</span></div></div></div>
  <div class="dico hid" id="dsk_f" data-t="dsk_f" style="left:1752px;top:56px"><s class="fold"></s><span>video-edit-studio-main</span></div>
  <div class="ghost hid" id="ghost2" style="width:80px"><s class="fold" style="opacity:.85"></s></div>'''


CX0, CY0 = 290, 70  # Claude app window


def claude_app(ci_html):
    prog = ["Python env (.venv, 3.12)", "ffmpeg", "Voice cleanup (DeepFilterNet3)", "Node (motion-graphics renderer)", "Apple tools: cut-out · natural colour · face finder",
            "AI models (Whisper, MMS)", "Studio graphics library"]
    lines = "".join(f'<div class="cpl hid" id="cpl{k}"><span class="ok">✓</span> {esc(x)}</div>' for k, x in enumerate(prog))
    return f'''<div class="win capp hid" id="wC" style="left:{CX0}px;top:{CY0}px;width:1340px;height:900px;z-index:25">
  <div class="cbar"><span class="lights"><i></i><i></i><i></i></span><div class="cseg"><span id="cs_chat" class="on">Chat</span><span id="cs_code" data-t="c_code">Code</span></div></div>
  <div class="cside"><div class="clogo"><b>✻</b> Claude</div><div class="cnew">＋ New session</div><em>Recents</em><div class="crec"></div><div class="crec s"></div><div class="crec"></div></div>
  <div class="cmain">
    <div class="cv" id="c_chat"><h1 class="cgreet"><b>✻</b> Good morning</h1><div class="ccomp"><span class="mut">How can I help you today?</span></div></div>
    <div class="cv hid" id="c_home"><h1 class="cgreet"><b>✻</b> What should we work on?</h1>
      <div class="ccomp big"><div class="cin" data-t="c_input"><span class="mut" id="c_ph">Describe a task…</span>{ci_html}<b class="ccar hid" id="c_car"></b></div>
        <div class="crow"><span class="cfold" data-t="c_folder"><s class="fold sm"></s><b id="c_f1">Choose a folder</b><b id="c_f2" class="dn">video-edit-studio-main</b> ▾</span>
          <span class="grow"></span><span class="csend" data-t="c_send">↑</span></div></div></div>
    <div class="cv hid" id="c_conv"><div class="ctop"><s class="fold sm"></s> Desktop / video-edit-studio-main</div>
      <div class="cmsgs"><div class="cu hid" id="cm_u">install this</div>
        <div class="ca hid" id="cm_a">I'll install the Studio: run the installer, check that everything works, then start it.</div>
        <div class="ctool hid" id="cm_t1"><div class="cth"><b>Run command</b><code>./tools/setup.sh</code><span class="cst hid" id="cm_t1r">Running…</span><span class="cst ok hid" id="cm_t1d">✓ Done</span></div>
          <div class="cperm" id="cm_perm"><span>Installs Python, ffmpeg, the Apple tools and the AI models, inside this folder.</span><span class="grow"></span><b class="cbtn">Deny</b><b class="cbtn al" data-t="c_allow">Allow</b></div>
          <div class="cprog">{lines}</div></div>
        <div class="ctool hid" id="cm_t2"><div class="cth"><b>Run command</b><code>./vedit doctor</code><span class="cst ok">✓ ready</span></div></div>
        <div class="ctool hid" id="cm_t3"><div class="cth"><b>Run command</b><code>.venv/bin/python tools/editor/server.py</code><span class="cst ok">✓ running</span></div></div>
        <div class="ca hid" id="cm_done">All set! Your Studio is running: <a data-t="c_link">http://localhost:8765</a></div></div>
      <div class="ccomp low"><span class="mut">Reply to Claude…</span></div></div>
    <div class="dlg hid" id="dlg"><div class="dlgs"><em>Favourites</em><span>Recents</span><span>Applications</span><span class="on">Desktop</span><span>Documents</span><span>Downloads</span></div>
      <div class="dlgm"><div class="dlgp">Desktop</div><div class="dlgr" id="dlg_row" data-t="dlg_row"><s class="fold sm"></s>video-edit-studio-main</div>
        <div class="dlgr"><s class="fold sm"></s>Screenshots</div><div class="dlgr"><s class="docs"></s>notes.txt</div>
        <div class="dlgb"><span class="grow"></span><b class="cbtn">Cancel</b><b class="cbtn al" data-t="dlg_open">Open</b></div></div></div>
  </div></div>'''


INTRO_ICONS = {
    "cut": '<circle cx="6" cy="7" r="3"/><circle cx="6" cy="17" r="3"/><path d="M8.6 8.6 20 20M8.6 15.4 20 4"/>',
    "cc": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 10.2a2.2 2.2 0 1 0 0 3.6M16.5 10.2a2.2 2.2 0 1 0 0 3.6"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    "pulse": '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
    "box": '<path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z"/><path d="M3 7.5 12 12l9-4.5M12 12v9"/>',
}
INTRO_CHIPS = [("cut", "Cuts retakes & dead air"), ("cc", "Writes the captions"), ("spark", "Adds motion graphics"),
               ("target", "Hook Lab"), ("pulse", "Edit Health"), ("box", "Post Kit")]


def intro():
    chips = "".join(f'<div class="ich" id="ich{k}"><i><svg viewBox="0 0 24 24">{INTRO_ICONS[ic]}</svg></i>{esc(t)}</div>' for k, (ic, t) in enumerate(INTRO_CHIPS))
    return f'''<div id="intro"><div class="igrid"></div>
  <div id="i_t"><div class="ik" id="i_k">OPEN SOURCE · FOR MAC</div>
    <div class="il"><span id="i_l1">Your own</span></div><div class="il"><span id="i_l2" class="o">AI video editor</span></div>
    <div class="iby" id="i_by"><b>✻</b> built with Claude</div></div>
  <div class="ichips">{chips}</div>
  <div id="i_rl"><div class="ik">INTRODUCING</div><h2>Video Edit Studio</h2></div>
  <div id="i_rev"><div class="bar"><span class="lights"><i></i><i></i><i></i></span><span class="u">localhost:8765</span></div><img src="assets/start.jpg" alt=""></div>
  <div class="ireq" id="i_q0"><i><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></i><div><b>A Mac with Apple Silicon</b><small>M1, M2, M3 or M4</small></div></div>
  <div class="ireq" id="i_q1"><i><b class="cl">✻</b></i><div><b>The Claude app</b><small>claude.ai/download</small></div></div></div>'''


def finder():
    return f'''<div class="win fnd hid" id="wF" style="left:{FX}px;top:{FY}px;width:{FW}px;height:{FH}px;z-index:35">
  <div class="fbar"><span class="lights"><i></i><i></i><i></i></span><b>Movies</b></div>
  <div class="fside"><em>Favourites</em><span>Recents</span><span>Applications</span><span>Desktop</span><span>Documents</span><span>Downloads</span><span class="on">Movies</span></div>
  <div class="fgrid"><div class="fi" data-t="f_vid"><img src="assets/file_a.jpg" alt=""><span>my-video.mov</span></div>
    <div class="fi"><img src="assets/file_b.jpg" alt=""><span>b-roll.mp4</span></div><div class="fi" data-t="f_ref"><img src="assets/file_c.jpg" alt=""><span>JEV classification reel.mov</span></div></div></div>
  <div class="ghost hid" id="ghost3"><img src="assets/file_c.jpg" alt=""></div>'''


def spotlight(sp_html):
    return f'''<div class="spot hid" id="spot"><div class="spin"><svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6.5"/><path d="M15 15l5.5 5.5"/></svg>{sp_html}<b class="scaret"></b></div>
  <div class="spres hid" id="spres"><div class="on"><s class="tic cl">✻</s><b>Claude</b><em>Application</em></div><div><s class="tic g"></s>Claude — Help</div></div></div>'''


def terminal(rows):
    return f'''<div class="win term hid" id="wT" style="left:{TX}px;top:{TY}px;width:{TW}px;height:{TH}px;z-index:20">
  <div class="tbar"><span class="lights"><i></i><i></i><i></i></span><span class="tt"><span id="tt1">you — -zsh — 120×30</span><span id="tt2" class="dn">video-edit-studio — claude — 120×30</span></span></div>
  <div class="tbody"><div class="tsc" id="tsc">{"".join(rows)}</div></div></div>'''


MENUBAR = '''<div class="mb"><s class="mlogo"></s><b><span id="app1">Browser</span><span id="app2" class="dn">Terminal</span><span id="app3" class="dn">Finder</span><span id="app4" class="dn">Claude</span></b>
  <span>File</span><span>Edit</span><span>View</span><span>Window</span><span>Help</span>
  <span class="r"><svg viewBox="0 0 24 24"><path d="M2 9a15 15 0 0 1 20 0M5.5 12.5a10 10 0 0 1 13 0M9 16a5 5 0 0 1 6 0"/><circle cx="12" cy="19" r="1.2"/></svg>
  <s class="bat"><i></i></s><span>Wed 21 Oct&nbsp;&nbsp;9:41 AM</span></span></div>'''

CURSOR = '<div id="cu"><svg width="30" height="44" viewBox="0 0 30 44"><path d="M3 2 L3 33 L10.4 26.2 L15.4 38 L20.6 35.8 L15.6 24.4 L25.6 24.4 Z"/></svg></div>'


def app(T, on, t=None):
    for k in (1, 2, 3, 4):
        T.set(f"app{k}", "{display: '%s'}" % ("inline" if k == on else "none"), t)


# ---------------------------------------------------------------- the walkthrough
def walkthrough(tg):
    T = Tl(tg)
    J = T.j
    sp_span, sp_html = T.chars("Claude")
    om_span, om_html = T.chars("github.com")
    gq_span, gq_html = T.chars("video edit studio")
    ci_span, ci_html = T.chars("install this")
    T.html = dict(sp=sp_html, om=om_html, gq=gq_html, ci=ci_html)
    T.set("cu", "{x: %.0f, y: %.0f, autoAlpha: 0}" % tuple(T.cur), 0)

    # 0 · intro: what it is → the Studio reveal → what you need ----------
    T.chapter(0, "Intro", "Intro")
    l1 = "Meet Video Edit Studio: your own AI video editor, on your Mac."
    T.B(l1, "Ito ang Video Edit Studio: sarili mong AI video editor, sa Mac mo.")
    J("tl.from(Q('i_k'), {opacity: 0, y: 20, duration: .5, ease: 'power3.out'}, .2);"
      "tl.from(Q('i_l1'), {yPercent: 110, duration: .7, ease: 'expo.out'}, .35);"
      "tl.from(Q('i_l2'), {yPercent: 110, duration: .7, ease: 'expo.out'}, .6);"
      "tl.from(Q('i_by'), {opacity: 0, y: 20, scale: .9, duration: .5, ease: 'back.out(2)'}, 1.3);")
    T.wait(T.need(l1))
    l2 = "Claude cuts the retakes, writes the captions and adds motion graphics. You pick the look."
    T.B(l2, "Si Claude ang nagtatanggal ng retakes, gumagawa ng captions at naglalagay ng motion graphics. Ikaw ang pipili ng look.")
    J(f"tl.to(Q('i_t'), {{y: -190, scale: .74, duration: .8, ease: 'power3.inOut'}}, {T.t:.3f});")
    for k in range(len(INTRO_CHIPS)):
        J(f"tl.fromTo(Q('ich{k}'), {{opacity: 0, y: 40, scale: .85}}, {{opacity: 1, y: 0, scale: 1, duration: .45, ease: 'back.out(1.8)'}}, {T.t + .45 + k * .42:.3f});")
        T.snd.append((T.t + .45 + k * .42, "pop", 1))
    T.wait(T.need(l2))
    l3 = "And this is the Studio, where every choice plays on your own video."
    T.B(l3, "At ito ang Studio, kung saan makikita mo agad ang bawat pili sa sarili mong video.")
    J(f"tl.to([Q('i_t'), ...document.querySelectorAll('.ich')], {{opacity: 0, y: -40, duration: .4, stagger: .03, ease: 'power2.in'}}, {T.t:.3f});"
      f"tl.fromTo(Q('i_rev'), {{opacity: 0, y: 420, rotationX: 38, scale: .72, transformPerspective: 1800}}, {{opacity: 1, y: 0, rotationX: 0, scale: 1, transformPerspective: 1800, duration: 1.3, ease: 'expo.out'}}, {T.t + .35:.3f});"
      f"tl.from(Q('i_rl'), {{opacity: 0, y: 30, duration: .6, ease: 'expo.out'}}, {T.t + .9:.3f});"
      f"tl.to(Q('i_rev'), {{scale: 1.035, duration: 4, ease: 'none'}}, {T.t + 1.65:.3f});")
    T.snd.append((T.t + .35, "whoosh", 1))
    T.wait(T.need(l3))
    l4 = "You need a Mac with Apple Silicon, and the Claude app."
    T.B(l4, "Kailangan mo ng Mac na Apple Silicon, at ng Claude app.")
    J(f"tl.to(Q('i_rev'), {{x: -330, scale: .64, duration: .9, ease: 'power3.inOut'}}, {T.t:.3f});"
      f"tl.to(Q('i_rl'), {{x: -330, duration: .9, ease: 'power3.inOut'}}, {T.t:.3f});"
      f"tl.fromTo(Q('i_q0'), {{opacity: 0, x: 80}}, {{opacity: 1, x: 0, duration: .5, ease: 'expo.out'}}, {T.t + .6:.3f});"
      f"tl.fromTo(Q('i_q1'), {{opacity: 0, x: 80}}, {{opacity: 1, x: 0, duration: .5, ease: 'expo.out'}}, {T.t + 1.1:.3f});")
    T.pad()
    T.hide("intro", t=T.t - .1, d=.4)

    # 1 · find it on GitHub ------------------------------------------------
    omni = tg["br_omni"]
    T.chapter(1, "Find it on GitHub", "Hanapin sa GitHub", cam=(1.6, omni[0] + 420, omni[1] + 250))
    T.B("Open your browser, and go to github.com.", "Buksan ang browser, at pumunta sa github.com.")
    T.show("cu", d=.3)
    T.go(omni, -omni[2] / 2 + 160, 0)
    T.set("om2", "{display: 'none'}")
    T.set("omc", "{display: 'inline-block'}")
    T.type_in(om_span, 10, 12)
    T.wait(.2)
    T.keys("Return")
    T.set("omc", "{display: 'none'}")
    T.set(om_span, "{display: 'none'}", T.t + .2)
    T.set("o_gh", "{display: 'inline'}", T.t + .2)
    T.set("pg_new", "{autoAlpha: 0}", T.t + .2)
    T.set("pg_home", "{autoAlpha: 1}", T.t + .2)
    T.set("t1a", "{display: 'none'}", T.t + .2)
    T.set("t1b", "{display: 'inline'}", T.t + .2)
    T.wait(.8)
    T.B("Search for video edit studio, and open the repository.", "I-search ang video edit studio, at buksan ang repository.")
    gs = tg["gh_search"]
    T.cam(1.55, PX + 640 + 330, gs[1] + 260, .8)
    T.wait(.4)
    T.go(gs)
    T.show("gh_sq", d=.15)
    T.wait(.2)
    T.type_in(gq_span, 17, 14)
    T.wait(.2)
    T.keys("Return")
    T.hide("gh_sq", d=.1)
    for a_, b_ in (("pg_home", "pg_srch"),):
        T.set(a_, "{autoAlpha: 0}", T.t + .2)
        T.set(b_, "{autoAlpha: 1}", T.t + .2)
    for a_, b_ in (("o_gh", "o_srch"), ("t1b", "t1c")):
        T.set(a_, "{display: 'none'}", T.t + .2)
        T.set(b_, "{display: 'inline'}", T.t + .2)
    sr = tg["sr_repo"]
    T.cam(1.5, sr[0] + 330, sr[1] + 110, .8)
    T.wait(.7)
    T.note("Open it", (sr[0] + 200, sr[1] + sr[3] / 2), 230, -60, hold=1.8)
    T.wait(.5)
    T.go(sr, -sr[2] / 2 + 150, 0)
    T.set("pg_srch", "{autoAlpha: 0}", T.t + .2)
    T.set("pg_gh", "{autoAlpha: 1}", T.t + .2)
    for a_, b_ in (("o_srch", "o_repo"), ("t1c", "t1d")):
        T.set(a_, "{display: 'none'}", T.t + .2)
        T.set(b_, "{display: 'inline'}", T.t + .2)
    T.wait(.6)
    T.B("Click the green Code button, then Download ZIP.", "I-click ang berdeng Code button, tapos Download ZIP.")
    code, zip_ = tg["gh_code"], tg["gh_zip"]
    cx, cy = C(code)
    T.cam(1.7, cx - 170, cy + 150, .9)
    T.wait(.6)
    T.note("Code", (cx - 10, code[1] - 2), -120, -80, hold=1.5)
    T.go(code)
    T.show("gh_pop", d=.18, frm="{autoAlpha: 0, y: -8}", to="{autoAlpha: 1, y: 0}")
    T.wait(.5)
    T.note("Download ZIP", (zip_[0] - 6, zip_[1] + zip_[3] / 2), -230, 40, hold=2.0)
    T.wait(.3)
    T.go(zip_, -zip_[2] / 2 + 70, 0)
    T.hide("gh_pop", t=T.t + .2, d=.15)
    dlb = tg["dl_btn"]
    T.show("dlb", t=T.t + .3, d=.2, frm="{autoAlpha: 0, scale: .5}", to="{autoAlpha: 1, scale: 1}")
    T.show("dlpop", t=T.t + .5, d=.2, frm="{autoAlpha: 0, y: -8}", to="{autoAlpha: 1, y: 0}")
    T.snd.append((T.t + .6, "ding", .5))
    T.cam(1.6, dlb[0] - 220, dlb[1] + 140, .8, t=T.t + .3)
    T.wait(1.4)

    # 2 · put it on your Desktop -------------------------------------------
    T.chapter(2, "Put it on your Desktop", "Ilagay sa Desktop", cam=(1.6, dlb[0] - 220, dlb[1] + 140))
    T.B("Open the download. It unzips into a folder.", "Buksan ang download. Magiging folder ito.")
    T.go(tg["dl_item"])
    T.hide("dlpop", t=T.t + .1, d=.15)
    T.cam(1.0, W / 2, H / 2, .8)
    T.show("wD", t=T.t + .2, d=.3, frm="{autoAlpha: 0, y: 40}", to="{autoAlpha: 1, y: 0}")
    T.snd.append((T.t + .2, "whoosh", .4))
    app(T, 3, T.t + .2)
    T.wait(1.0)
    dz = tg["d_zip"]
    T.go(dz, 0, -10, pause=.05)
    T.click()
    df = tg["d_fold"]
    T.show("d_fold", t=T.t + .4, d=.3, frm="{autoAlpha: 0, scale: .6}", to="{autoAlpha: 1, scale: 1}")
    T.snd.append((T.t + .45, "pop", 1))
    T.wait(1.2)
    T.B("Drag the folder onto your Desktop.", "I-drag ang folder papunta sa Desktop.")
    T.move(df[0] + df[2] / 2, df[1] + 40)
    T.wait(.2)
    T.snd.append((T.t, "click", .5))
    J(f"tl.set(Q('ghost2'), {{x: {T.cur[0] - 40:.1f}, y: {T.cur[1] - 30:.1f}}}, {T.t:.3f});")
    T.show("ghost2", d=.1)
    J("const GH2 = Q('ghost2');")
    ds = tg["dsk_f"]
    tgt = (ds[0] + ds[2] / 2, ds[1] + 44)
    x0, y0 = T.cur
    d = 1.3
    J(f"tl.to([CU], {{x: {tgt[0]:.1f}, duration: {d}, ease: 'power2.inOut'}}, {T.t:.3f}); tl.to([CU], {{y: {tgt[1]:.1f}, duration: {d}, ease: 'sine.inOut'}}, {T.t:.3f});"
      f"tl.to(GH2, {{x: {tgt[0] - 40:.1f}, duration: {d}, ease: 'power2.inOut'}}, {T.t:.3f}); tl.to(GH2, {{y: {tgt[1] - 30:.1f}, duration: {d}, ease: 'sine.inOut'}}, {T.t:.3f});")
    T.cur = list(tgt)
    T.t += d
    T.click(quiet=True)
    T.hide("ghost2", d=.1)
    T.show("dsk_f", d=.25, frm="{autoAlpha: 0, scale: .6}", to="{autoAlpha: 1, scale: 1}")
    T.note("On your Desktop", (ds[0] + 4, ds[1] + ds[3] / 2), -260, 90, hold=2.4)
    T.wait(1.6)
    T.B("Using git? Clone it into your Desktop folder instead.", "Gumagamit ng git? I-clone na lang ito sa Desktop folder.")
    T.show("gitc", d=.35, frm="{autoAlpha: 0, x: 40}", to="{autoAlpha: 1, x: 0}")
    T.pad()
    T.hide("gitc", t=T.t - .3, d=.3)

    # 3 · install with the Claude app --------------------------------------
    T.chapter(3, "Install with Claude", "I-install gamit si Claude", cam=(1.0, W / 2, H / 2))
    T.B("Open the Claude app, and go to the Code tab.", "Buksan ang Claude app, at pumunta sa Code tab.")
    T.hide("wD", d=.2)
    T.move(1300, 760)
    T.keys("⌘", "Space")
    T.show("spot", d=.2, frm="{autoAlpha: 0, scale: .96}", to="{autoAlpha: 1, scale: 1}")
    T.wait(.25)
    T.type_in(sp_span, 6, 11)
    T.show("spres", t=T.t - .3, d=.15)
    T.wait(.3)
    T.keys("Return")
    T.hide("spot", d=.15)
    T.wait(.1)
    T.show("wC", d=.3, frm="{autoAlpha: 0, scale: .95, transformOrigin: '50% 50%'}", to="{autoAlpha: 1, scale: 1}")
    T.snd.append((T.t, "whoosh", .5))
    app(T, 4)
    T.cam(1.25, CX0 + 670, CY0 + 400, .9)
    T.wait(.9)
    T.go(tg["c_code"])
    T.set("c_chat", "{autoAlpha: 0}")
    T.set("c_home", "{autoAlpha: 1}")
    J(f"tl.set(Q('cs_chat'), {{backgroundColor: 'rgba(0,0,0,0)', color: '#a8a39c'}}, {T.t:.3f}); tl.set(Q('cs_code'), {{backgroundColor: '#3a3835', color: '#ffffff'}}, {T.t:.3f});")
    T.wait(.8)
    T.B("Choose the folder on your Desktop.", "Piliin ang folder sa Desktop.")
    cf = tg["c_folder"]
    T.go(cf)
    T.show("dlg", t=T.t + .1, d=.2, frm="{autoAlpha: 0, y: -20}", to="{autoAlpha: 1, y: 0}")
    T.wait(.7)
    T.go(tg["dlg_row"])
    T.set("dlg_row", "{backgroundColor: '#3b6fe0', color: '#ffffff'}")
    T.wait(.3)
    T.go(tg["dlg_open"])
    T.hide("dlg", d=.15)
    T.set("c_f1", "{display: 'none'}")
    T.set("c_f2", "{display: 'inline'}")
    T.note("Your Desktop folder", (cf[0] + cf[2] / 2, cf[1] + cf[3] + 4), 120, 80, hold=1.8)
    T.wait(.8)
    T.B("Then type: install this, and send it.", "Tapos i-type: install this, at i-send.")
    T.go(tg["c_input"], -tg["c_input"][2] / 2 + 120, 0)
    T.set("c_ph", "{display: 'none'}")
    T.set("c_car", "{autoAlpha: 1}")
    T.type_in(ci_span, 12, 12)
    T.wait(.3)
    T.go(tg["c_send"])
    T.set("c_home", "{autoAlpha: 0}", T.t + .1)
    T.set("c_conv", "{autoAlpha: 1}", T.t + .1)
    T.show("cm_u", t=T.t + .15, d=.2)
    T.show("cm_a", t=T.t + .9, d=.3)
    T.wait(1.4)
    T.B("Claude asks before it runs anything. Click Allow.", "Nagtatanong muna si Claude bago mag-run ng kahit ano. I-click ang Allow.")
    T.show("cm_t1", d=.3, frm="{autoAlpha: 0, y: 14}", to="{autoAlpha: 1, y: 0}")
    al = tg["c_allow"]
    T.cam(1.5, al[0] - 260, al[1] + 60, .8)
    T.wait(.8)
    T.note("Click Allow", (al[0] + al[2] / 2, al[1] + al[3] + 4), -60, 90, hold=1.8)
    T.until(.75)
    T.go(al)
    T.hide("cm_perm", d=.1)
    T.show("cm_t1r", d=.1)
    T.B("The first install takes ten to twenty minutes. Then Claude checks everything, and starts the Studio.",
        "Mga sampu hanggang dalawampung minuto ang unang install. Tapos iche-check ni Claude ang lahat, at bubuksan ang Studio.")
    t0 = T.t
    T.badge("The first install takes 10–20 minutes", t0, 4.2)
    for k in range(7):
        T.set(f"cpl{k}", "{autoAlpha: 1}", t0 + .3 + k * .45)
    T.t = t0 + .3 + 7 * .45
    T.hide("cm_t1r", d=.05)
    T.show("cm_t1d", d=.1)
    T.show("cm_t2", t=T.t + .3, d=.25, frm="{autoAlpha: 0, y: 14}", to="{autoAlpha: 1, y: 0}")
    T.show("cm_t3", t=T.t + .8, d=.25, frm="{autoAlpha: 0, y: 14}", to="{autoAlpha: 1, y: 0}")
    lk = tg["c_link"]
    T.cam(1.4, lk[0] + 40, lk[1] - 120, .9, t=T.t + .6)
    T.show("cm_done", t=T.t + 1.4, d=.3)
    T.snd.append((T.t + 1.4, "ding", .6))
    T.wait(2.2)
    T.B("Prefer Terminal? These three commands do the same.", "Mas gusto mo ang Terminal? Pareho lang ang ginagawa ng tatlong command na ito.")
    T.show("noc", d=.35, frm="{autoAlpha: 0, x: 40}", to="{autoAlpha: 1, x: 0}")
    T.pad()
    T.hide("noc", t=T.t - .3, d=.3)

    # 4 · open the Studio ---------------------------------------------------
    T.chapter(4, "Open the Studio", "Buksan ang Studio", cam=(1.4, lk[0] + 40, lk[1] - 120))
    T.B("Click the link, and your Studio opens in the browser.", "I-click ang link, at bubukas ang Studio sa browser.")
    T.go(lk, -lk[2] / 2 + 60, 0)
    T.set("wB", "{zIndex: 40}", T.t + .1)
    app(T, 1, T.t + .1)
    J(f"tl.to(Q('tab2'), {{width: 250, paddingLeft: 12, paddingRight: 12, duration: .2, ease: 'power2.out'}}, {T.t + .1:.3f});")
    T.set("tab1", "{backgroundColor: 'rgba(0,0,0,0)', color: '#bfc2c7'}", T.t + .1)
    T.set("tab2", "{backgroundColor: '#35363a', color: '#ffffff'}", T.t + .1)
    T.set("tab2a", "{display: 'none'}", T.t + .1)
    T.set("tab2b", "{display: 'inline'}", T.t + .1)
    T.set("o_repo", "{display: 'none'}", T.t + .1)
    T.set("o_st", "{display: 'inline'}", T.t + .1)
    T.set("dlb", "{autoAlpha: 0}", T.t + .1)
    T.shot("start", t=T.t + .3)
    T.set("pg_gh", "{autoAlpha: 0}", T.t + .4)
    T.set("pg_st", "{backgroundColor: '#100d0c'}", T.t + .4)
    T.cam(1.0, W / 2, H / 2, .8, t=T.t + .2)
    T.wait(1.6)
    T.B("Click the name at the top to make it your own brand.", "I-click ang pangalan sa itaas para gawing sarili mong brand.")
    name = SR("start", "name")
    T.cam(1.55, name[0] + 330, name[1] + 260, .8)
    T.wait(.6)
    T.move(*C(name))
    T.ring(name, hold=2.4)
    T.note("Click to rename it", (name[0] + name[2] + 8, name[1] + name[3] / 2), 250, 70, hold=2.4)
    T.wait(2.2)

    # 4 · upload (+ Auto-edit) ----------------------------------------------
    T.chapter(5, "Upload a video", "Mag-upload ng video", cam=(1.22, 760, 650))
    T.B("Drag your video onto Upload a video.", "I-drag ang video mo sa Upload a video.")
    T.cam(1.22, 760, 650, .9)
    T.shot("drop", "start", "scroll")
    T.show("wF", d=.3, frm="{autoAlpha: 0, y: 40}", to="{autoAlpha: 1, y: 0}")
    T.snd.append((T.t, "whoosh", .4))
    app(T, 3, T.t + .2)
    drop = SR("drop", "drop")
    T.wait(.5)
    T.note("Drop it here", (drop[0] + drop[2] / 2, drop[1] + 40), 150, -110, hold=3.2)
    vid = tg["f_vid"]
    T.move(vid[0] + vid[2] / 2, vid[1] + vid[3] * .4)
    T.wait(.2)
    T.snd.append((T.t, "click", .5))
    J(f"tl.set(GH, {{x: {T.cur[0] - 40:.1f}, y: {T.cur[1] - 30:.1f}}}, {T.t:.3f});")
    T.show("ghost", d=.12)
    T.drag = True
    T.wait(.1)
    T.move(drop[0] + drop[2] / 2, drop[1] + drop[3] / 2, 1.1)
    T.shot("drop_on", "drop", t=T.t - .35)
    T.wait(.25)
    T.drag = False
    T.click(quiet=True)
    T.hide("ghost", d=.1)
    T.shot("drop_busy", "drop_on")
    T.hide("wF", t=T.t + .3, d=.3)
    app(T, 1, T.t + .3)
    T.B("It transcribes it, and removes the retakes, repeats and dead air by itself.",
        "Kusa nitong ita-transcribe, at tatanggalin ang retakes, ulit at dead air.")
    T.badge("Transcribing takes a few minutes", T.t, 2.6)
    T.ring(drop, hold=2.2)
    T.wait(2.6)
    did = SR("start", "did")
    did = [did[0], did[1], did[2], 92]
    T.shot("start", "drop_busy", "scroll")
    T.cam(1.6, did[0] + did[2] / 2, did[1] + 130, .8)
    T.wait(.6)
    T.ring(did, hold=2.6)
    T.B("iPhone HDR is turned into natural colour, too.", "Ginagawa ring natural na kulay ang iPhone HDR.")
    T.wait(2.0)

    # 6 · tell Claude what you want: brief → style references → Auto-edit ----
    T.chapter(6, "Tell Claude what you want", "Sabihin kay Claude ang gusto mo", cam=(1.35, 1150, 600))
    T.B("Now tell Claude what you want. Tap where you'll post it, the vibe, the captions and the graphics.",
        "Ngayon, sabihin kay Claude ang gusto mo. I-tap kung saan mo ipo-post, ang vibe, ang captions at ang graphics.")
    T.shot("brief0", "start", "scroll")
    T.wait(.6)
    bx = SR("brief0", "box")
    T.ring([bx[0], bx[1], bx[2], 60], hold=1.8, pad=4)
    T.note("Don't just click: say what you want", (bx[0] + 330, bx[1] + 28), 330, -60, hold=2.2)
    T.wait(.6)
    for k, key in enumerate(("tiktok", "bold", "big", "lots")):
        T.go(SR("brief0", key), pause=.08)
        T.shot(f"brief{k + 1}", f"brief{k}")
        T.wait(.3)
    T.B("Then say it in your own words, like: yellow keywords, big captions at the bottom, fast cuts.",
        "Tapos sabihin sa sarili mong salita, gaya ng: dilaw ang keywords, malaking captions sa baba, mabilis ang cuts.")
    tx = SR("brief0", "text")
    T.go(tx, -tx[2] / 2 + 90, 0)
    tb = T.typebox("brief0", "text", BRIEF, cps=18, top=True)
    T.shot("brief5", "brief4")
    T.hide(tb, t=T.t + .1, d=.05)
    T.note("Taglish is fine", (tx[0] + 470, tx[1] + tx[3]), 140, 70, hold=1.8)
    T.wait(.4)
    T.B("Click Build my look. Every change shows up, with the reason why.", "I-click ang Build my look. Lalabas ang bawat pagbabago, kasama ang dahilan.")
    T.go(SR("brief0", "go"))
    T.shot("brief6", "brief5", "scroll")
    out = SR("brief6", "out")
    T.cam(1.45, out[0] + out[2] / 2, out[1] + out[3] / 2 - 30, .7)
    T.ring(out, hold=3.0, pad=6)
    T.note("What changed, and why", (out[0] + out[2] - 80, out[1] - 6), 90, -70, hold=2.8)
    T.wait(2.8)
    T.B("Or learn a style from videos you like. Drag in a creator's video, and the Studio studies its captions, colours and pacing.",
        "O gayahin ang style ng videos na gusto mo. I-drag ang video ng isang creator, at pag-aaralan ng Studio ang captions, kulay at bilis nito.")
    T.shot("refs1", "brief6", "scroll")
    T.cam(1.15, 780, 640, .8)
    T.show("wF", t=T.t + .2, d=.3, frm="{autoAlpha: 0, y: 40}", to="{autoAlpha: 1, y: 0}")
    app(T, 3, T.t + .2)
    T.wait(.7)
    add = SR("refs1", "add")
    T.note("Drop a video you like", (add[0] + add[2] / 2, add[1] + 8), 120, -90, hold=2.6)
    fr = tg["f_ref"]
    T.move(fr[0] + fr[2] / 2, fr[1] + fr[3] * .4)
    T.wait(.15)
    T.drag_to("ghost3", add[0] + add[2] / 2, add[1] + add[3] / 2)
    T.shot("refs2", "refs1")
    T.hide("wF", t=T.t + .3, d=.3)
    app(T, 1, T.t + .3)
    T.badge("Studying a video takes a few seconds", T.t, 1.8)
    T.wait(1.6)
    T.shot("refs3", "refs2")
    T.ring(SR("refs3", "card2"), hold=2.0, pad=4)
    T.wait(.6)
    T.B("Mix and match: take each part from the video you like best, then click Make it my style.",
        "Mix and match: kunin ang bawat bahagi sa video na pinakagusto mo, tapos i-click ang Make it my style.")
    T.shot("refs4", "refs3", "scroll")
    T.cam(1.4, 1150, 520, .8)
    T.wait(.6)
    jv = SR("refs4", "jev")
    T.note("Captions from this one", (jv[0] + jv[2] / 2, jv[1] + jv[3]), 60, 80, hold=1.8)
    T.go(jv)
    T.shot("refs5", "refs4")
    T.wait(.5)
    T.go(SR("refs4", "go"))
    T.shot("refs6", "refs5")
    ro = SR("refs6", "out")
    T.ring(ro, hold=2.8, pad=6)
    T.wait(.4)
    T.B("Only the style is kept. The video is deleted once it's studied, and none of it goes in your edit.",
        "Style lang ang itinatabi. Dine-delete ang video pagkatapos pag-aralan, at walang bahagi nito na mapupunta sa edit mo.")
    T.note("Your style, part by part", (ro[0] + ro[2] - 120, ro[1] + ro[3]), 60, 70, hold=2.6)
    T.wait(2.4)
    T.B("Have Claude Code? Click Auto-edit, and Claude edits the whole video the way you asked.",
        "May Claude Code ka? I-click ang Auto-edit, at ie-edit ni Claude ang buong video ayon sa gusto mo.")
    T.shot("autobox", "refs6", "scroll")
    auto, ab = SR("autobox", "auto"), SR("autobox", "autoBtn")
    T.cam(1.45, auto[0] + auto[2] / 2, auto[1] + 170, .8)
    T.wait(.5)
    T.note("Follows your brief", (ab[0] + ab[2] + 8, ab[1] + ab[3] / 2), 300, 10, hold=2.6)
    T.wait(.8)
    T.go(ab)
    T.shot("auto_run", "autobox")
    T.ring(SR("auto_run", "auto"), hold=3.4, pad=4)
    T.wait(3.0)

    # 5 · pick your look (+ Hook Lab, safe zones, 2026 trends) -------------
    T.chapter(7, "Fine-tune your look", "Ayusin pa ang look", cam=(1.3, 1150, 640))
    T.B("Fine-tune anything in the steps: your colours, and your fonts.", "Puwede mo pang ayusin ang bawat step: ang kulay, at ang fonts.")
    T.cam(1.3, 1150, 640, .9)
    nxt = SR("start", "next")
    T.go(nxt)
    T.shot("colours", "auto_run")
    T.wait(.4)
    c3 = SR("colours", "c3")
    T.go(c3, 0, -40)
    T.shot("colours_3", "colours")
    T.note("Colours", (c3[0] + c3[2] / 2, c3[1] + 4), 0, -60, hold=1.4)
    T.wait(.9)
    T.go(nxt)
    T.shot("fonts", "colours_3")
    T.wait(.4)
    c2 = SR("fonts", "c2")
    T.go(c2, 0, -40)
    T.shot("fonts_2", "fonts")
    T.note("Fonts", (c2[0] + c2[2] / 2, c2[1] + 4), 0, -60, hold=1.4)
    T.wait(.9)
    T.B("In Hook, Hook Lab finds your strongest line. Click Use as cold open.",
        "Sa Hook, hinahanap ng Hook Lab ang pinakamalakas mong linya. I-click ang Use as cold open.")
    T.go(nxt)
    T.shot("hook", "fonts_2")
    T.wait(.6)
    use = SR("hook", "use")
    T.note("Your best line becomes the hook", (use[0] + use[2] + 6, use[1] + use[3] / 2), 330, 30, hold=2.4)
    T.wait(.8)
    T.go(use)
    T.shot("hook_on", "hook")
    on = SR("hook_on", "on")
    T.ring(on, hold=2.2, pad=6)
    T.note("Cold open is on", (on[0] + on[2] + 10, on[1] + on[3] / 2), 230, 70, hold=2.2)
    T.wait(1.6)
    T.B("Pick a caption style. Safe zones shows what TikTok and Reels will cover.",
        "Pumili ng caption style. Ipinapakita ng Safe zones kung ano ang matatakpan ng TikTok at Reels.")
    T.go(nxt)
    T.shot("captions", "hook_on")
    T.wait(.4)
    k2 = SR("captions", "c2")
    T.go(k2, 0, -40)
    T.shot("captions_2", "captions")
    T.note("Captions", (k2[0] + k2[2] / 2, k2[1] + 4), 0, -60, hold=1.4)
    T.wait(.6)
    T.cam(1.3, 800, 640, .7)
    T.wait(.3)
    T.go(SR("captions_2", "safe"))
    T.shot("captions_safe", "captions_2")
    ph = SR("captions_safe", "phone")
    T.ring(ph, hold=2.4, pad=4)
    T.note("Safe zones: what the apps cover", (ph[0] + ph[2] + 8, ph[1] + ph[3] * .3), 270, -30, hold=2.4)
    T.wait(2.2)
    T.B("Then in Visuals, open 2026 trends: 44 motion graphics, like this new before and after wipe.",
        "Tapos sa Visuals, buksan ang 2026 trends: 44 na motion graphics, gaya nitong bagong before and after wipe.")
    T.cam(1.3, 1150, 640, .7)
    T.go(nxt)
    T.shot("visuals", "captions_safe")
    T.wait(.4)
    T.go(SR("visuals", "trend"))
    T.shot("visuals_t", "visuals")
    T.wait(.4)
    T.ring(SR("visuals_t", "lead"), hold=1.6, pad=6)
    T.wait(1.4)
    T.shot("visuals_wipe", "visuals_t", "scroll")
    wp = SR("visuals_wipe", "wipe")
    T.cam(1.75, wp[0] + wp[2] / 2 - 140, wp[1] + wp[3] / 2, .8)
    T.wait(.6)
    T.move(wp[0] + wp[2] * .55, wp[1] + wp[3] * .42)
    T.wait(.1)
    T.note("Hover a card: it plays", (wp[0] - 8, wp[1] + 70), -230, -30, hold=2.8)
    T.flip()
    T.wait(SHOTS["play"]["frames"] / SHOTS["play"]["fps"] + .2)
    T.B("Tick the ones you like, and Claude places them on the right lines.",
        "I-tick ang gusto mo, at si Claude ang maglalagay sa tamang linya.")
    T.wait(.5)
    T.click()
    T.shot("visuals_wipe_pick", "visuals_wipe")
    T.set("flip", "{autoAlpha: 0}", T.t + .1)
    T.note("Picked", (wp[0] + wp[2] - 30, wp[1] + 4), 90, -60, hold=1.6)
    T.wait(1.6)

    # 6 · check & fix (render preview, Edit Health, Talk to edit) ----------
    T.chapter(8, "Check & fix", "I-check at ayusin", cam=(1.3, 1100, 560))
    T.B("Next, Watch. Click Render preview.", "Sunod, Watch. I-click ang Render preview.")
    T.cam(1.3, 1100, 560, .8)
    T.wait(.3)
    T.go(SR("visuals_wipe_pick", "watchTab"))
    T.shot("watch", "visuals_wipe_pick")
    T.wait(.4)
    prev = SR("watch", "prev")
    T.go(prev)
    T.ring(prev, hold=1.8, pad=5)
    T.badge("A preview renders in a few minutes", T.t, 2.0)
    T.wait(1.0)
    T.B("Run Edit Health. It finds repeated words, dead air and colour problems.",
        "I-run ang Edit Health. Hinahanap nito ang dobleng salita, dead air at problema sa kulay.")
    T.go(SR("watch", "run"))
    hb = SR("watch", "health")
    T.ring(hb, hold=3.0, pad=4)
    T.note("Edit Health", (hb[0] + hb[2] - 60, hb[1] - 8), 120, -60, hold=2.6)
    T.wait(2.4)
    T.B("Each item has a fix. One click, and it's done.", "May fix ang bawat isa. Isang click lang, ayos na.")
    fx = SR("watch", "fix")
    T.note("One-click fix", (fx[0] - 8, fx[1] + fx[3] / 2), -230, 60, hold=2.4)
    T.wait(.5)
    T.go(fx)
    T.ring(fx, hold=1.6, pad=4)
    T.wait(1.4)
    T.B("To change anything, pause there and leave a note, like: cut the dead air.",
        "Para may baguhin, i-pause doon at mag-iwan ng note, gaya ng: cut the dead air.")
    T.shot("notes", "watch", "scroll")
    nb = SR("notes", "nbox")
    T.cam(1.7, nb[0] + nb[2] / 2 + 80, nb[1] + nb[3] / 2 + 30, .8)
    T.wait(.6)
    T.go(SR("notes", "ntext"))
    tb = T.typebox("notes", "ntext", NOTE)
    T.shot("notes_typed", "notes")
    T.hide(tb, t=T.t + .1, d=.05)
    T.wait(.3)
    T.go(SR("notes", "nadd"))
    T.shot("notes_added", "notes_typed")
    nl = SR("notes_added", "nlist")
    T.ring(nl, hold=2.0, pad=4)
    T.note("Your note, at 0:42", (nl[0] + nl[2] + 8, nl[1] + nl[3] / 2), 230, 20, hold=2.0)
    T.wait(1.6)
    T.B("Then click Apply notes with Claude, and Claude fixes them all.", "Tapos i-click ang Apply notes with Claude, at aayusin ni Claude lahat.")
    T.go(SR("notes_added", "apply"))
    T.shot("notes_run", "notes_added")
    T.ring(SR("notes_run", "nbox"), hold=2.8, pad=4)
    T.wait(2.6)

    # 7 · export + post (+ Post Kit, Brand Kit) -----------------------------
    T.chapter(9, "Export & post", "I-export at i-post", cam=(1.3, 1100, 560))
    T.B("When it looks right, export the final 1080p.", "Kapag ayos na, i-export ang final 1080p.")
    T.shot("watch", "notes_run", "scroll")
    T.cam(1.3, 1100, 560, .8)
    T.wait(.4)
    fin = SR("watch", "fin")
    T.go(fin)
    T.ring(fin, hold=1.6, pad=5)
    T.wait(1.2)
    T.B("Build the Post Kit: vertical, square and wide videos, captions and a cover, ready to post.",
        "Gawin ang Post Kit: vertical, square at wide na video, captions at cover, handa nang i-post.")
    T.shot("post", "watch", "scroll")
    T.wait(.5)
    T.go(SR("post", "post"))
    T.shot("post_done", "post", t=T.t + .6)
    files = SR("post_done", "files")
    T.ring(files, t=T.t + .7, hold=2.6, pad=4)
    T.note("9:16 · 1:1 · 16:9 + captions + cover", (files[0] + files[2] * .45, files[1] + files[3] + 6), 60, 90, t=T.t + .7, hold=2.6)
    T.wait(3.0)
    T.B("And save your look as a Brand Kit, to use on every video.", "At i-save ang look mo bilang Brand Kit, para magamit sa bawat video.")
    T.shot("kit", "post_done", "scroll")
    T.wait(.5)
    T.go(SR("kit", "kname"))
    tb = T.typebox("kit", "kname", "My brand")
    T.shot("kit_typed", "kit")
    T.hide(tb, t=T.t + .1, d=.05)
    T.go(SR("kit_typed", "ksave"))
    T.shot("kit_saved", "kit_typed")
    kl = SR("kit_saved", "klist")
    T.ring(kl, hold=2.2, pad=4)
    T.note("Use it on every video", (kl[0] + kl[2] * .4, kl[1] + kl[3] + 6), 40, 80, hold=2.2)
    T.wait(2.0)

    # outro -----------------------------------------------------------------
    T.chapter(0, "Outro", "Outro")
    T.B("That's it! Grab it on GitHub, and happy editing.",
        "Ayan na! Kunin ito sa GitHub, at happy editing.")
    T.cam(1.0, W / 2, H / 2, .9)
    T.hide("cu", d=.3)
    T.show("end", t=T.t + .3, d=.5)
    for k, el in enumerate(("end_h", "end_u")):
        J(f"tl.from(Q('{el}'), {{y: 30, opacity: 0, duration: .6, ease: 'expo.out'}}, {T.t + .5 + k * .25:.2f});")
    T.pad()
    T.wait(1.2)
    return T


# ---------------------------------------------------------------- page
CSS = """
@font-face{font-family:"Inter Tight";font-weight:600;src:url("fonts/InterTight-wght-600.ttf")}
@font-face{font-family:"Inter Tight";font-weight:700;src:url("fonts/InterTight-wght-700.ttf")}
@font-face{font-family:"Inter Tight";font-weight:800;src:url("fonts/InterTight-wght-800.ttf")}
@font-face{font-family:"Inter Tight";font-weight:900;src:url("fonts/InterTight-wght-900.ttf")}
:root{--o:#FF6A00;--o2:#FF9A4D;--ink:#160A03;--ui:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Helvetica,Arial,sans-serif;--mono:Menlo,Monaco,monospace}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:#000}
body{font-family:var(--ui);-webkit-font-smoothing:antialiased;color:#e8e6ea}
#root{position:absolute;inset:0;overflow:hidden;background:#000}
.hid{visibility:hidden;opacity:0}.dn{display:none}.mut{color:#8b8792}.grow{flex:1}
#desk{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;overflow:hidden;
  background:radial-gradient(900px 700px at 10% 12%,rgba(255,122,26,.42),transparent 62%),radial-gradient(1000px 800px at 92% 92%,rgba(122,60,255,.32),transparent 62%),
  radial-gradient(1100px 800px at 62% 30%,rgba(255,61,107,.20),transparent 66%),linear-gradient(135deg,#1d1220,#0e0c15 58%,#170d0a)}
.mb{position:absolute;left:0;top:0;right:0;height:30px;background:rgba(18,14,20,.62);display:flex;align-items:center;gap:20px;padding:0 18px;font:500 14px var(--ui);color:#f1eff3;z-index:5}
.mb b{font-weight:700}.mlogo{width:15px;height:15px;border-radius:50%;background:var(--o)}
.mb .r{margin-left:auto;display:flex;gap:16px;align-items:center}.mb svg{width:18px;height:18px;fill:none;stroke:#f1eff3;stroke-width:2}
.bat{width:26px;height:12px;border:1.5px solid #f1eff3;border-radius:3px;padding:1.5px}.bat i{display:block;width:70%;height:100%;background:#f1eff3;border-radius:1px}
.win{position:absolute;border-radius:12px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 0 1px rgba(255,255,255,.13)}
.lights{display:flex;gap:8px}.lights i{width:12px;height:12px;border-radius:50%;background:#ff5f57}.lights i:nth-child(2){background:#febc2e}.lights i:nth-child(3){background:#28c840}
/* browser */
.br{background:#202124}
.btabs{height:40px;display:flex;align-items:flex-end;padding:0 12px 0 16px;background:#1a1b1e}
.btabs .lights{align-self:center;margin-right:20px}
.tab{height:32px;width:250px;display:flex;align-items:center;gap:9px;padding:0 12px;border-radius:9px 9px 0 0;font:500 13px var(--ui);color:#bfc2c7;overflow:hidden;white-space:nowrap;flex:none}
.tab span{flex:1;overflow:hidden;text-overflow:ellipsis}.tab em{font-style:normal;color:#8e9196}
.tab.on{background:#35363a;color:#fff}
#tab2{width:0;padding:0}
.fav{width:16px;height:16px;border-radius:50%;flex:none}.fav.gh{background:#e6edf3}.fav.st{background:var(--o);color:var(--ink);font:900 10px var(--ui);display:grid;place-items:center;text-decoration:none;border-radius:4px}
.plus{width:32px;height:32px;display:grid;place-items:center;color:#c8cbd0;font:300 24px var(--ui);margin:0 0 1px 6px;flex:none}
.bbar{height:46px;background:#35363a;display:flex;align-items:center;gap:16px;padding:0 16px}
.nav{color:#9aa0a6;font:500 18px var(--ui)}.dots{color:#9aa0a6;font:700 18px var(--ui)}
.omni{flex:1;height:32px;border-radius:16px;background:#202124;display:flex;align-items:center;padding:0 16px;gap:10px;font:400 15px var(--ui);color:#e8eaed;white-space:pre}
.omni span i,.tl span i,.spin span i{font-style:normal;display:none}
.ocaret{display:none;width:2px;height:18px;background:#e8eaed;margin-left:-9px}
.lock{width:11px;height:13px;border:2px solid #9aa0a6;border-radius:3px}
.bpage{position:absolute;left:0;top:86px;width:1440px;height:900px;overflow:hidden;background:#0d1117}
.pg{position:absolute;inset:0}
.np{background:#202124}.npl{position:absolute;left:470px;top:330px;width:500px;height:46px;border-radius:23px;background:#303134;color:#9aa0a6;font:400 16px var(--ui);display:flex;align-items:center;padding:0 22px}
.st .sh{position:absolute;left:0;top:0;width:1440px;height:900px}
.tbx{position:absolute;z-index:3;background:#1E1B19;border:1px solid #FF6A00;border-radius:11px;padding:0 12px;display:flex;align-items:center;font:600 14px var(--ui);color:#F4EFEA;white-space:pre;overflow:hidden}
.tbx span i{font-style:normal;display:none}.tcar{display:inline-block;width:1.5px;height:17px;background:#F4EFEA;margin-left:1px}
/* github */
.gh{background:#0d1117;color:#e6edf3;font:400 14px var(--ui)}
.gt{height:64px;background:#010409;display:flex;align-items:center;gap:16px;padding:0 20px;border-bottom:1px solid #30363d}
.gm{color:#9198a1;font-size:18px}.glogo{width:32px;height:32px;border-radius:50%;background:#e6edf3}
.gc{font:400 15px var(--ui)}.gc i{font-style:normal;color:#9198a1;margin:0 2px}.gc b{font-weight:600}
.gs{width:300px;height:32px;border:1px solid #3d444d;border-radius:6px;color:#9198a1;display:flex;align-items:center;padding:0 12px;gap:6px}
.gs kbd{font:500 11px var(--ui);border:1px solid #3d444d;border-radius:4px;padding:0 5px}
.gme{width:32px;height:32px;border-radius:50%;background:var(--o);color:var(--ink);display:grid;place-items:center;font:800 14px var(--ui)}
.gtabs{height:48px;display:flex;align-items:flex-end;gap:6px;padding:0 24px;border-bottom:1px solid #30363d;background:#010409}
.gtabs span{padding:0 10px 12px;color:#e6edf3;font:400 14px var(--ui)}.gtabs .on{border-bottom:2px solid #f78166;font-weight:600}
.gw{padding:22px 40px}
.gti{display:flex;align-items:center;gap:10px;margin-bottom:20px}.gti b{font:600 20px var(--ui)}
.gti em{font-style:normal;font:500 12px var(--ui);color:#9198a1;border:1px solid #3d444d;border-radius:99px;padding:1px 8px}
.gav{width:26px;height:26px;border-radius:50%;background:var(--o);color:var(--ink);display:grid;place-items:center;font:800 12px var(--ui)}.gav.s{width:22px;height:22px;font-size:10px}
.btn{height:30px;display:inline-flex;align-items:center;gap:6px;padding:0 12px;border-radius:6px;background:#212830;border:1px solid #3d444d;font:500 13px var(--ui);color:#e6edf3;white-space:nowrap}
.btn s{text-decoration:none;background:#2f3742;border-radius:99px;padding:0 6px;font-size:12px}
.btn.green{background:#238636;border-color:rgba(240,246,252,.1);color:#fff;font-weight:600}
.gcols{display:flex;gap:28px}.gmain{flex:1;min-width:0}.gside{width:290px}
.gbar{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.ggo{width:200px;height:30px;border:1px solid #3d444d;border-radius:6px;color:#9198a1;display:flex;align-items:center;padding:0 10px;font-size:13px}
.codew{position:relative}
.pop{position:absolute;right:0;top:38px;width:420px;background:#151b23;border:1px solid #3d444d;border-radius:12px;box-shadow:0 16px 40px rgba(0,0,0,.6);z-index:5}
.ptab{display:flex;border-bottom:1px solid #3d444d}.ptab span{flex:1;text-align:center;padding:12px 0;font:500 14px var(--ui);color:#9198a1}.ptab .on{color:#e6edf3;font-weight:600;border-bottom:2px solid #f78166}
.pbody{padding:16px}.phd{font:600 14px var(--ui);margin-bottom:12px}
.psub{display:flex;gap:16px;margin-bottom:10px;border-bottom:1px solid #3d444d}.psub span{padding-bottom:8px;font:500 13px var(--ui);color:#9198a1}.psub .on{color:#e6edf3;font-weight:600;border-bottom:2px solid #f78166}
.purl{display:flex;align-items:center;height:32px;border:1px solid #3d444d;border-radius:6px;background:#0d1117;font:400 13px var(--mono);overflow:hidden}
.purl>span:first-child{flex:1;padding:0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cp{width:34px;height:30px;display:grid;place-items:center;border-left:1px solid #3d444d;position:relative}
.cp svg{width:16px;height:16px;fill:none;stroke:#e6edf3;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round;position:absolute;left:9px;top:7px}
#cp2{stroke:#3fb950;stroke-width:2}
.pmut{margin-top:8px;font:400 12px var(--ui);color:#9198a1}
.prow{padding:12px 16px;border-top:1px solid #3d444d;font:500 14px var(--ui)}
.tip{position:absolute;right:-6px;top:72px;background:#3d444d;color:#fff;font:600 12px var(--ui);padding:5px 9px;border-radius:6px}
.gfiles{border:1px solid #3d444d;border-radius:6px;overflow:hidden}
.fh{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#151b23;border-bottom:1px solid #3d444d;font-size:14px}
.fr{display:flex;align-items:center;gap:12px;padding:9px 16px;border-top:1px solid #21262d;font-size:14px}.fh+.fr{border-top:0}
.ic{width:16px;height:16px;flex:none}.ic.dir{fill:#7d8590}.ic.fil{stroke:#7d8590}
.fn{width:240px}.fm{flex:1;color:#9198a1}.ft{color:#9198a1;white-space:nowrap}.fh .fm{margin-left:6px}
.grd{margin-top:20px;border:1px solid #3d444d;border-radius:6px;padding:0 24px 24px}
.grh{margin:0 -24px 16px;padding:12px 16px;border-bottom:1px solid #3d444d;font:600 14px var(--ui)}
.grd h1{font:600 30px var(--ui);padding-bottom:8px;border-bottom:1px solid #30363d;margin-bottom:14px}.grd p{font:400 16px/1.5 var(--ui);color:#d1d7e0}
.gside h3{font:600 16px var(--ui);margin-bottom:12px}.gside p{font:400 15px/1.45 var(--ui);margin-bottom:14px}
.topics{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}.topics span{background:#121d2f;color:#4493f8;border-radius:99px;padding:2px 10px;font:500 12px var(--ui)}
.sl{color:#9198a1;margin:8px 0;font-size:14px}
/* terminal */
.term{background:#1d1c21}
.tbar{height:34px;background:#2b2a31;display:flex;align-items:center;padding:0 14px;position:relative;border-bottom:1px solid #111}
.tt{position:absolute;left:0;right:0;text-align:center;font:600 13px var(--ui);color:#b9b7bf}
.tbody{position:absolute;left:22px;top:48px;right:22px;bottom:14px;overflow:hidden}
.tsc{position:relative}
.tl{position:absolute;left:0;right:0;white-space:pre;font:400 21px/32px var(--mono);color:#ebe9f0;visibility:hidden}
.pu{color:#7ee787}.pd{color:#79c0ff}.ok{color:#7ee787;font-weight:700}.lnk{color:#79c0ff;text-decoration:underline}
.caret{display:inline-block;width:12px;height:25px;background:#ebe9f0;vertical-align:-6px;font-style:normal}
.cco{color:#d97757}.ccb{color:#ebe9f0}.ccg{color:#7ee787}
.tl.ccw{right:auto;width:720px;height:184px;border:2px solid #d97757;border-radius:10px;padding:10px 18px}
.ccw div{height:32px}
.tl.ccin{height:56px;border:1.5px solid #6c6874;border-radius:8px;padding:10px 14px;line-height:34px}
.hist{color:#a9a5b0;background:#2c2a33;padding:2px 8px;border-radius:4px}
.tl.ccp{right:auto;width:760px;height:280px;border:2px solid #d97757;border-radius:10px;padding:8px 18px;line-height:29px;font-size:20px}
.ccp .pt b{color:#d97757}.ccp .sel{color:#d97757;font-weight:700}
/* spotlight */
.spot{position:absolute;left:610px;top:240px;width:700px;border-radius:16px;background:rgba(44,42,49,.97);box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 0 1px rgba(255,255,255,.14);z-index:38;overflow:hidden}
.spin{height:64px;display:flex;align-items:center;gap:14px;padding:0 20px;font:400 26px var(--ui);color:#f3f1f6;white-space:pre}
.spin svg{width:26px;height:26px;fill:none;stroke:#a7a3ad;stroke-width:2.2;flex:none}
.scaret{display:inline-block;width:2px;height:30px;background:#f3f1f6;margin-left:-12px}
.spres{border-top:1px solid rgba(255,255,255,.1);padding:8px}
.spres div{display:flex;align-items:center;gap:12px;padding:9px 12px;border-radius:9px;font:400 17px var(--ui);color:#d9d6de}
.spres .on{background:#3b6fe0;color:#fff}.spres b{font-weight:600}.spres em{margin-left:auto;font-style:normal;font-size:14px;opacity:.75}
.tic{width:30px;height:30px;border-radius:7px;background:#111;color:#e8e8e8;font:700 12px var(--mono);display:grid;place-items:center;text-decoration:none;border:1px solid #555}
.tic.g{background:#666;border:0}
/* finder */
.fnd{background:#1f1e23}
.fbar{height:44px;display:flex;align-items:center;gap:22px;padding:0 16px;background:#2a2930;border-bottom:1px solid #111;font:700 14px var(--ui)}
.fside{position:absolute;left:0;top:44px;bottom:0;width:160px;background:#26252b;padding:14px 10px;display:flex;flex-direction:column;gap:2px;font:500 13px var(--ui);color:#d2cfd6}
.fside em{font-style:normal;font-size:11px;font-weight:700;color:#8b8792;margin:0 0 6px 8px}.fside span{padding:6px 8px;border-radius:6px}.fside .on{background:#3d3b44}
.fgrid{position:absolute;left:184px;top:70px;right:20px;display:flex;gap:26px}
.fi{width:118px;display:flex;flex-direction:column;align-items:center;gap:10px;font:500 13px var(--ui);color:#e3e0e7}
.fi img{width:96px;height:96px;object-fit:cover;border-radius:6px;box-shadow:0 0 0 1px rgba(255,255,255,.2)}
.fi.doc s{width:76px;height:96px;background:#f2f2f2;border-radius:4px}
.ghost{position:absolute;left:0;top:0;width:96px;z-index:45}.ghost img{width:96px;height:96px;object-fit:cover;border-radius:6px;box-shadow:0 12px 30px rgba(0,0,0,.5);opacity:.85}
/* cursor + marks */
#cu{position:absolute;left:-3px;top:-2px;z-index:60;transform-origin:3px 2px}
#cu svg{display:block;filter:drop-shadow(0 2px 3px rgba(0,0,0,.5))}#cu path{fill:#111;stroke:#fff;stroke-width:2.2;stroke-linejoin:round}
.rip{position:absolute;width:60px;height:60px;margin:-30px 0 0 -30px;border-radius:50%;border:3px solid var(--o);background:rgba(255,106,0,.2);opacity:0;z-index:59}
.ar{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:visible;z-index:55;visibility:hidden;fill:none}
.ar path{stroke:var(--o);stroke-linecap:round;stroke-linejoin:round;fill:none}.ar path.sh{stroke:rgba(0,0,0,.45)}.ar path.hd{opacity:0}
.nl{position:absolute;white-space:nowrap;background:var(--o);color:var(--ink);font-family:"Inter Tight";font-weight:800;z-index:56;line-height:1.2}
.rg{position:absolute;border-style:solid;border-color:var(--o);box-shadow:0 0 0 3px rgba(255,106,0,.25),0 0 24px rgba(255,106,0,.55);z-index:54}

.tab span b{font-weight:500}
/* github home + search */
.gdash{font:600 15px var(--ui)}
.gs{cursor:text}
.ghome{display:flex;gap:40px;padding:28px 40px}.gleft{width:300px}.gleft h4{font:600 14px var(--ui);margin-bottom:14px}
.gli{height:14px;width:220px;border-radius:7px;background:#21262d;margin:12px 0}.gli.s{width:160px}
.gfeed{flex:1}.gfeed h2{font:600 20px var(--ui);margin-bottom:16px}
.gfc{display:flex;gap:12px;align-items:center;padding:16px;border:1px solid #30363d;border-radius:8px;margin-bottom:12px;background:#0d1117}
.gfc b{display:block;font:500 14px var(--ui)}.gfc small{color:#9198a1;font-size:12px}
.gsq{position:absolute;left:640px;top:12px;width:740px;height:40px;border:2px solid #1f6feb;border-radius:8px;background:#0d1117;display:flex;align-items:center;gap:10px;padding:0 14px;font:400 16px var(--ui);color:#e6edf3;white-space:pre;box-shadow:0 12px 40px rgba(0,0,0,.6)}
.gsq svg{width:18px;height:18px;fill:none;stroke:#9198a1;stroke-width:2.2;flex:none}.gsq span i{font-style:normal;display:none}.qcar{width:1.5px;height:20px;background:#e6edf3;margin-left:-9px}
.gres{display:flex;gap:28px;padding:24px 40px}.gfil{width:250px}.gfil h4{font:600 14px var(--ui);margin-bottom:10px}
.gfil div{padding:8px 10px;border-radius:6px;font-size:14px;color:#e6edf3;display:flex;justify-content:space-between}.gfil .on{background:#1f2630;font-weight:600}.gfil s{text-decoration:none;background:#2f3742;border-radius:99px;padding:0 7px;font-size:12px}
.glist{flex:1}.glist h3{font:600 16px var(--ui);margin-bottom:14px}
.grc{border:1px solid #30363d;border-radius:8px;padding:18px 20px}.grt{display:flex;align-items:center;gap:10px}.grt a{color:#4493f8;font:400 18px var(--ui)}.grt a b{font-weight:600}
.grc p{color:#d1d7e0;margin:10px 0;font-size:14px}.gtg{display:flex;gap:6px}.gtg span{background:#121d2f;color:#4493f8;border-radius:99px;padding:2px 10px;font:500 12px var(--ui)}
.gmeta{margin-top:12px;color:#9198a1;font-size:12px}
/* download bubble */
.dlb{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:rgba(138,180,248,.18)}
.dlb svg{width:18px;height:18px;fill:none;stroke:#8ab4f8;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.dlpop{position:absolute;right:56px;top:90px;width:360px;background:#2b2c30;border-radius:12px;box-shadow:0 16px 40px rgba(0,0,0,.6);padding:12px;z-index:9}
.dlh{font:600 13px var(--ui);color:#e8eaed;padding:4px 6px 10px}.dlr{display:flex;gap:12px;align-items:center;padding:8px;border-radius:8px;background:#35363a}
.dlr b{display:block;font:500 13px var(--ui);color:#e8eaed}.dlr small{font-size:12px;color:#9aa0a6}
/* file icons */
.zipi{display:block;width:30px;height:38px;border-radius:4px;background:linear-gradient(90deg,transparent 44%,#9aa0a6 44% 56%,transparent 56%) 0 6px/100% 50% no-repeat,#e9e9ec}
.zipi.big{width:76px;height:96px}
.fold{display:block;width:96px;height:76px;border-radius:8px;background:linear-gradient(#7cc4ff,#4ea4f2);position:relative;margin-top:14px}
.fold::before{content:"";position:absolute;left:0;top:-10px;width:42%;height:14px;border-radius:6px 6px 0 0;background:#5fb0f7}
.fold.sm{width:20px;height:15px;border-radius:3px;margin:0}.fold.sm::before{top:-3px;height:4px;border-radius:2px 2px 0 0}
.docs{display:block;width:14px;height:18px;border-radius:2px;background:#e9e9ec}
.dico{position:absolute;width:130px;display:flex;flex-direction:column;align-items:center;gap:8px;font:600 13px var(--ui);color:#fff;text-align:center;text-shadow:0 1px 3px rgba(0,0,0,.7);z-index:3}
/* Claude app */
.capp{background:#262624;color:#f5f4ef}
.cbar{height:46px;display:flex;align-items:center;padding:0 16px;background:#1f1e1d;border-bottom:1px solid #34322f;position:relative}
.cseg{position:absolute;left:50%;transform:translateX(-50%);display:flex;gap:4px;background:#2b2a27;border-radius:10px;padding:3px}
.cseg span{padding:6px 18px;border-radius:8px;font:600 14px var(--ui);color:#a8a39c}.cseg .on{background:#3a3835;color:#fff}
.cside{position:absolute;left:0;top:46px;bottom:0;width:250px;background:#1f1e1d;padding:18px 14px;display:flex;flex-direction:column;gap:8px}
.clogo{font:600 20px Georgia,serif;margin-bottom:10px}.clogo b,.cgreet b,.tic.cl,.ireq .cl{color:#d97757}
.cnew{padding:9px 12px;border-radius:9px;background:#2b2a27;font:600 14px var(--ui)}.cside em{font-style:normal;font:600 12px var(--ui);color:#8d877f;margin:14px 4px 4px}
.crec{height:12px;width:190px;border-radius:6px;background:#2f2d2a;margin:8px 4px}.crec.s{width:140px}
.cmain{position:absolute;left:250px;top:46px;right:0;bottom:0}
.cv{position:absolute;inset:0}
.cgreet{position:absolute;left:0;right:0;top:250px;text-align:center;font:400 40px Georgia,serif;color:#f5f4ef}
.ccomp{position:absolute;left:160px;right:160px;top:340px;min-height:64px;border-radius:18px;background:#30302e;border:1px solid #45423e;padding:20px 22px;font:400 17px var(--ui)}
.ccomp.big{height:140px}.ccomp.low{top:auto;bottom:24px}
.cin{font:400 18px var(--ui);color:#f5f4ef;white-space:pre}.cin span i{font-style:normal;display:none}.ccar{display:inline-block;width:1.5px;height:20px;background:#f5f4ef;vertical-align:-4px}
.crow{position:absolute;left:18px;right:18px;bottom:14px;display:flex;align-items:center}
.cfold{display:flex;align-items:center;gap:8px;padding:7px 12px;border-radius:9px;border:1px solid #4a4743;font:600 14px var(--ui);color:#e5e1da}
.csend{width:36px;height:36px;border-radius:10px;background:#d97757;color:#1f1e1d;display:grid;place-items:center;font:800 18px var(--ui)}
.ctop{position:absolute;left:24px;top:16px;display:flex;align-items:center;gap:8px;font:600 14px var(--ui);color:#a8a39c}
.cmsgs{position:absolute;left:120px;right:120px;top:64px;display:flex;flex-direction:column;gap:16px}
.cu{align-self:flex-end;background:#3a3835;border-radius:16px;padding:12px 18px;font:500 17px var(--ui)}
.ca{font:400 18px/1.5 Georgia,serif;color:#f5f4ef}.ca a{color:#e8a184;text-decoration:underline}
.ctool{border:1px solid #45423e;border-radius:14px;background:#2b2a27;overflow:hidden}
.cth{display:flex;align-items:center;gap:12px;padding:12px 16px;font:600 14px var(--ui)}.cth code{font:500 14px var(--mono);color:#e5e1da;background:#1f1e1d;border-radius:6px;padding:3px 8px}
.cst{margin-left:auto;font:600 13px var(--ui);color:#d9a066}.cst.ok{color:#7ee787}
.cperm{display:flex;align-items:center;gap:10px;padding:12px 16px;border-top:1px solid #3a3835;font:400 14px var(--ui);color:#cfc9c0}
.cbtn{padding:8px 16px;border-radius:9px;border:1px solid #55514c;font:600 14px var(--ui);color:#f5f4ef}.cbtn.al{background:#d97757;border-color:#d97757;color:#1f1e1d}
.cprog{padding:0 16px 8px}.cpl{font:400 14px var(--mono);color:#cfc9c0;padding:3px 0}.cpl .ok{color:#7ee787}
.dlg{position:absolute;left:150px;top:0;width:780px;height:420px;background:#2b2a27;border:1px solid #45423e;border-top:0;border-radius:0 0 14px 14px;box-shadow:0 30px 70px rgba(0,0,0,.6);display:flex;overflow:hidden;z-index:5}
.dlgs{width:180px;background:#24231f;padding:16px 10px;display:flex;flex-direction:column;gap:2px;font:500 13px var(--ui);color:#d2cfd6}
.dlgs em{font-style:normal;font-size:11px;font-weight:700;color:#8b8792;margin:0 0 6px 8px}.dlgs span{padding:6px 8px;border-radius:6px}.dlgs .on{background:#3d3b44}
.dlgm{flex:1;position:relative;padding:14px 18px}.dlgp{font:700 14px var(--ui);margin-bottom:10px}
.dlgr{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;font:500 14px var(--ui);color:#e5e1da}
.dlgb{position:absolute;left:18px;right:18px;bottom:16px;display:flex;gap:10px}
/* intro */
#intro{position:absolute;inset:0;z-index:90;overflow:hidden;background:radial-gradient(900px 620px at 16% 18%,rgba(255,106,0,.34),transparent 62%),radial-gradient(900px 700px at 86% 88%,rgba(255,61,107,.22),transparent 62%),#0c0908}
.igrid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:80px 80px}
#i_t{position:absolute;left:0;right:0;top:250px;text-align:center;transform-origin:50% 0}
.ik{font:800 22px "Inter Tight";letter-spacing:.24em;color:var(--o2)}
.il{overflow:hidden;font:900 136px/1.02 "Inter Tight";letter-spacing:-.045em;color:#fff}.il span{display:inline-block}.il .o{color:var(--o)}
.iby{display:inline-flex;align-items:center;gap:10px;margin-top:28px;padding:10px 20px;border-radius:99px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);font:700 24px "Inter Tight";color:#e8e2dc}.iby b{color:#d97757}
.ichips{position:absolute;left:250px;right:250px;top:610px;display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.ich{display:flex;align-items:center;gap:18px;padding:22px 26px;border-radius:22px;background:rgba(26,20,17,.94);border:1px solid rgba(255,255,255,.11);font:800 29px "Inter Tight";color:#fff;opacity:0}
.ich i{width:58px;height:58px;border-radius:16px;background:rgba(255,106,0,.16);display:grid;place-items:center;flex:none}
.ich svg,.ireq svg{width:32px;height:32px;fill:none;stroke:var(--o);stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
#i_rl{position:absolute;left:0;right:0;top:46px;text-align:center}#i_rl h2{font:900 64px "Inter Tight";letter-spacing:-.03em;color:#fff;margin-top:6px}
#i_rev{position:absolute;left:340px;top:172px;width:1240px;border-radius:18px;overflow:hidden;opacity:0;background:#111;
  box-shadow:0 60px 140px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.14),0 0 140px rgba(255,106,0,.28)}
#i_rev .bar{height:40px;background:#1e1b19;display:flex;align-items:center;gap:16px;padding:0 16px}#i_rev .u{font:600 15px var(--mono);color:#a39a93}
#i_rev img{display:block;width:1240px;height:775px}
.ireq{position:absolute;left:1180px;width:620px;display:flex;align-items:center;gap:22px;padding:26px 30px;border-radius:24px;background:rgba(26,20,17,.96);border:1px solid rgba(255,140,60,.4);opacity:0}
#i_q0{top:400px}#i_q1{top:580px}
.ireq i{width:72px;height:72px;border-radius:18px;background:rgba(255,106,0,.16);display:grid;place-items:center;flex:none;font:900 40px "Inter Tight";font-style:normal}
.ireq b{display:block;font:900 34px "Inter Tight";color:#fff}.ireq small{font:600 22px var(--mono);color:#bdb4ad}
/* step cards */
.stc{position:absolute;inset:0;z-index:95;background:linear-gradient(118deg,#110c0a 0%,#1a110c 58%,#2b1609 100%);display:flex;flex-direction:column;justify-content:center;padding-left:190px;overflow:hidden}
.stc .sk{font:800 24px "Inter Tight";letter-spacing:.22em;color:var(--o2)}
.stc h2{font:900 118px/1.02 "Inter Tight";letter-spacing:-.045em;color:#fff;margin-top:14px;max-width:1250px}
.stc .sb{width:140px;height:9px;border-radius:5px;background:var(--o);margin-top:36px}
.stc .sn{position:absolute;right:120px;top:50%;transform:translateY(-52%);font:900 520px/1 "Inter Tight";color:rgba(255,106,0,.11)}
/* overlays (screen space) */
#ov{position:absolute;inset:0;z-index:100;font-family:"Inter Tight"}
.chip{position:absolute;left:36px;bottom:36px;display:flex;align-items:center;gap:14px;padding:12px 24px 12px 12px;border-radius:18px;background:rgba(16,12,10,.94);
  border:1px solid rgba(255,255,255,.14);box-shadow:0 12px 34px rgba(0,0,0,.45)}
.chip i{width:46px;height:46px;border-radius:13px;background:var(--o);color:var(--ink);display:grid;place-items:center;font:900 26px "Inter Tight";font-style:normal}
.chip em{display:block;font:700 13px "Inter Tight";letter-spacing:.16em;color:var(--o2);font-style:normal}.chip span{display:block;font:800 26px "Inter Tight";color:#fff;margin-top:1px}
.kp{position:absolute;left:810px;width:300px;bottom:40px;display:flex;justify-content:center;gap:10px}
.kp kbd{min-width:62px;height:62px;padding:0 18px;border-radius:13px;background:linear-gradient(#3b3633,#272321);border:1px solid rgba(255,255,255,.2);border-bottom-width:4px;
  display:grid;place-items:center;font:800 26px "Inter Tight";color:#fff;box-shadow:0 10px 26px rgba(0,0,0,.5)}
.ff{position:absolute;right:36px;bottom:36px;display:flex;align-items:center;gap:14px;padding:14px 22px;border-radius:18px;background:rgba(16,12,10,.94);border:1px solid rgba(255,140,60,.45)}
.ff b{font:900 18px "Inter Tight";letter-spacing:.1em;color:var(--o)}.ff span{font:700 22px "Inter Tight";color:#fff}
.noc{position:absolute;right:36px;top:36px;width:640px;padding:26px 30px;border-radius:22px;background:rgba(16,12,10,.96);border:1px solid rgba(255,140,60,.45);box-shadow:0 20px 50px rgba(0,0,0,.5)}
.noc em{font:800 16px "Inter Tight";letter-spacing:.14em;color:var(--o2);font-style:normal}.noc h3{font:900 34px "Inter Tight";color:#fff;margin:6px 0 16px}
.noc code{display:block;font:500 22px var(--mono);color:#fff;background:#221c19;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:10px 14px;margin-top:10px}
.noc code b{color:var(--o2);font-weight:700;margin-right:12px}
.card{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;background:rgba(10,8,8,.84)}
.card .k{font:800 22px "Inter Tight";letter-spacing:.2em;color:var(--o2)}
.card h1{font:900 104px/1 "Inter Tight";letter-spacing:-.04em;color:#fff;margin:18px 0 24px}.card h1 span{color:var(--o)}
.card p{font:700 30px "Inter Tight";color:#bdb4ad}
.card .u{display:flex;align-items:center;gap:14px;margin:4px 0 28px;padding:20px 32px;border-radius:20px;background:#181412;border:2px solid var(--o);font:600 36px var(--mono);color:#fff}
"""


def page(T, timeline=True):
    desk = (MENUBAR + browser(T.html["om"], "".join(T.page), T.html["gq"]) + downloads() + claude_app(T.html["ci"]) + finder() + spotlight(T.html["sp"])
            + '<div class="ghost hid" id="ghost"><img src="assets/file_a.jpg" alt=""></div>' + "".join(T.desk) + CURSOR)
    over = ("".join(T.over)
            + '''<div class="noc hid" id="noc"><em>PREFER TERMINAL?</em><h3>These three do the same</h3>
                 <code><b>1</b>./tools/setup.sh</code><code><b>2</b>./vedit doctor</code><code><b>3</b>.venv/bin/python tools/editor/server.py</code></div>'''
            + f'''<div class="noc hid" id="gitc"><em>USING GIT?</em><h3>Clone it into your Desktop</h3>
                 <code><b>1</b>cd ~/Desktop</code><code><b>2</b>git clone https://{REPO}.git</code></div>'''
            + intro()
            + f'''<div class="card hid" id="end"><h1 id="end_h">You're <span>ready.</span></h1><div class="u" id="end_u">{REPO}</div></div>''')
    D = round(T.t, 2)
    js = ""
    if timeline:
        js = "\n".join(["const D = Q('desk'), CU = Q('cu'), GH = Q('ghost');", "const tl = gsap.timeline({ paused: true });"] + T.js
                       + [f"tl.set({{}}, {{}}, {D});", "window.__timelines = window.__timelines || {}; window.__timelines['studio_tutorial'] = tl; tl.seek(0);"])
    return D, f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/>
<!-- Studio tutorial (screen-share walkthrough). Generated by docs/tutorial/build.py — edit walkthrough() there, not here. -->
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style></head>
<body><div id="root" data-composition-id="studio_tutorial" data-start="0" data-duration="{D}" data-width="1920" data-height="1080">
<div id="desk">{desk}</div><div id="ov">{over}</div></div>
<script>const Q = (s) => document.getElementById(s);
{js}</script></body></html>
"""


# ---------------------------------------------------------------- the script, written out
def ts(x, sep=","):
    m, s = divmod(max(0, x), 60)
    return f"00:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def mmss(x):
    return f"{int(x // 60)}:{int(x % 60):02d}"


def srt(T, lang):
    out = []
    for n, (t, _, en, tl_) in enumerate(T.vo):
        end = T.vo[n + 1][0] - .1 if n + 1 < len(T.vo) else T.t - .3
        out.append(f"{n + 1}\n{ts(t)} --> {ts(end)}\n{en if lang == 'en' else tl_}\n")
    return "\n".join(out)


def script_md(T, D):
    rows = [f"# Tutorial voiceover script\n\n`Studio_Tutorial.mp4` ({mmss(D)}) is narrated with these lines (AI voice: ElevenLabs “Nathaniel Hartley”), over a "
            "music bed. To use your own voice instead, record over `Studio_Tutorial_music_only.mp4` (the same video with music and clicks only): "
            "each line starts at the time shown, and the screen does what the line says while you say it.\n\n"
            "Teleprompter / subtitle files: `voiceover_en.srt` (English) and `voiceover_tl.srt` (Taglish). After you change a line, re-record it "
            "(`vo/`), then rebuild with `../../.venv/bin/python build.py --render`; the timing follows the recorded lines.\n"]
    for ci, (ct, n, en, _) in enumerate(T.chapters):
        rows.append(f"\n## {'Step ' + str(n) + ' · ' if n else ''}{en} ({mmss(ct)})\n\n| Time | English | Taglish |\n|---|---|---|")
        rows += [f"| {mmss(t)} | {e} | {l_} |" for t, c, e, l_ in T.vo if c - 1 == ci]
    return "\n".join(rows) + "\n"


# ---------------------------------------------------------------- sound: clicks, keys, whooshes only
def place(buf, x, t, g):
    i = int(t * S.SR)
    if 0 <= i < len(buf):
        x = x[: len(buf) - i]
        buf[i:i + len(x)] += x * g


def s_click():
    n = int(.1 * S.SR)
    x = np.zeros(n)
    for off, g, f in ((0, 1.0, 3400), (int(.06 * S.SR), .55, 2600)):  # press + release
        m = int(.007 * S.SR)
        b = S.noise(m, "white") * np.exp(-np.linspace(0, 9, m))
        x[off:off + m] += signal.sosfilt(signal.butter(2, [f * .55, f * 1.6], btype="band", fs=S.SR, output="sos"), b) * g
    return x / np.abs(x).max()


def s_key():
    m = int(.03 * S.SR)
    b = S.noise(m, "white") * np.exp(-np.linspace(0, 7, m))
    x = signal.sosfilt(signal.butter(2, [900, 4200], btype="band", fs=S.SR, output="sos"), b)
    return x / np.abs(x).max()


def decode(path):
    r = subprocess.run([str(FFMPEG), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(S.SR), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).astype(float)


def smooth(x, secs):
    """Moving average (fast, via cumulative sums)."""
    k = max(1, int(secs * S.SR))
    c = np.cumsum(np.concatenate([[0.0], x]))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k // 2, y[0]), y, np.full(len(x) - len(y) - k // 2, y[-1])])


def voice_track(T, N):
    """Each recorded line at its start (+.15 s), with a mask of where someone is talking."""
    v, mask = np.zeros(N), np.zeros(N)
    for t, _, en, _ in T.vo:
        o = VOICE.get(en)
        if not o:
            continue
        x = decode(HERE / "vo" / o["file"])[int(o["start"] * S.SR):int(o["end"] * S.SR)].copy()
        a, b = int(.02 * S.SR), int(.06 * S.SR)
        x[:a] *= np.linspace(0, 1, a)
        x[-b:] *= np.linspace(1, 0, b)
        place(v, x, t + .15, 1.0)
        mask[max(0, int((t - .1) * S.SR)):int((t + .15 + len(x) / S.SR + .3) * S.SR)] = 1
    return v, smooth(mask, .35)


def music_track(N, under, voice):
    """The music bed, looped with crossfades, ducked under the voice (−20 dB vs the voice) and fuller in the gaps (−10 dB)."""
    if not MUSIC.exists():
        return np.zeros(N)
    m = decode(MUSIC)
    xf = int(2 * S.SR)
    out = m.copy()
    while len(out) < N:
        ramp = np.linspace(0, 1, xf)
        out = np.concatenate([out[:-xf], out[-xf:] * (1 - ramp) + m[:xf] * ramp, m[xf:]])
    out = out[:N]
    vr = np.sqrt(np.mean(voice[np.abs(voice) > 1e-4] ** 2)) if np.any(np.abs(voice) > 1e-4) else .1
    mr = np.sqrt(np.mean(out ** 2)) or 1
    hi, lo = vr * 10 ** (-10 / 20) / mr, vr * 10 ** (-20 / 20) / mr
    out *= hi * (1 - under) + lo * under
    fi, fo = int(1.5 * S.SR), int(3 * S.SR)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-fo:] *= np.linspace(1, 0, fo)
    return out


def audio(T, D, with_voice=True):
    N = int(D * S.SR)
    v, under = voice_track(T, N)
    mix = music_track(N, under, v) + sfx_track(T, D) * .6
    if with_voice:
        mix = mix + v
    return mix / max(1.0, np.abs(mix).max() / .9)


def sfx_track(T, D):
    out = np.zeros(int(D * S.SR) + S.SR * 2)
    click, key = s_click(), s_key()
    for t, kind, g in T.snd:
        if kind == "click":
            place(out, click, t, .42 * g)
        elif kind == "key":
            place(out, key, t, .34)
        elif kind == "type":
            place(out, S.s_type(max(.2, g)), t, .22)
        elif kind == "pop":
            place(out, S.s_pop(), t, .05)
        elif kind == "whoosh":
            place(out, S.s_swoosh(.4, True, .7), t, .12 * g)
        elif kind == "ding":
            place(out, S.s_ding(), t, .1 * g)
    return out[:int(D * S.SR)] * .5


def write_wav(p, x):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(S.SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    ad = HERE / "hf" / "assets"
    ad.mkdir(parents=True, exist_ok=True)
    pa = ad / "play"
    pa.mkdir(exist_ok=True)
    for f in (HERE / "shots" / f"play_{SHOTS['play']['id']}").glob("*.jpg"):  # the hovered card, frame by frame
        if not (pa / f.name).exists() or (pa / f.name).stat().st_mtime < f.stat().st_mtime:
            (pa / f.name).write_bytes(f.read_bytes())
    for k in [k for k in SHOTS if k != "play"]:  # real Studio captures at 2×, so zooms stay sharp
        src, dst = HERE / "shots" / f"{k}.png", ad / f"{k}.jpg"
        if not src.exists():  # the raw captures stay local (git ignores them); the JPGs here are what renders
            continue
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            Image.open(src).convert("RGB").save(dst, quality=90)
    # pass 1: lay out the mock windows without a timeline, and measure where their buttons landed
    T = walkthrough(collections.defaultdict(lambda: [0, 0, 10, 10]))
    (HERE / "hf" / "index.html").write_text(page(T, timeline=False)[1])
    pptr = next(Path.home().glob(".npm/_npx/*/node_modules/puppeteer-core")).parent
    subprocess.run([str(NODE), str(HERE / "measure.mjs")], env=dict(os.environ, NODE_PATH=str(pptr)), check=True)
    tg = json.loads((HERE / "hf" / "targets.json").read_text())
    # pass 2: the real timeline
    T = walkthrough(tg)
    D, doc = page(T)
    (HERE / "hf" / "index.html").write_text(doc)
    (HERE / "voiceover_en.srt").write_text(srt(T, "en"))
    (HERE / "voiceover_tl.srt").write_text(srt(T, "tl"))
    (HERE / "VOICEOVER.md").write_text(script_md(T, D))
    write_wav(HERE / "audio.wav", audio(T, D))
    write_wav(HERE / "audio_music.wav", audio(T, D, with_voice=False))  # music + clicks only, to record your own voice over
    for i, (ct, n, en, _) in enumerate(T.chapters):
        nt = T.chapters[i + 1][0] if i + 1 < len(T.chapters) else D
        print(f"  {mmss(ct)}  {nt - ct:5.1f} s  {en}")
    print(f"✓ {D:.1f} s ({mmss(D)}) · {len(T.vo)} voiceover lines → hf/index.html, VOICEOVER.md, voiceover_*.srt, audio.wav")
    if "--render" in sys.argv:
        ffdir = ROOT / ".venv/lib/python3.12/site-packages/static_ffmpeg/bin/darwin_arm64"
        env = dict(os.environ, PATH=f"{ROOT / 'tools/node/bin'}:{ffdir}:" + os.environ["PATH"], HYPERFRAMES_SKIP_SKILLS="1")
        vid = HERE / "video.mp4"
        subprocess.run(["npx", "-y", "hyperframes", "render", str(HERE / "hf"), "-o", str(vid), "--fps", "30", "--quiet", "--quality", "looks"],
                       cwd=HERE / "hf", env=env, check=True)
        # one fixed gain that brings the voiced mix to −16 LUFS, used on both versions (so the music sits at the same level in each)
        r = subprocess.run([str(FFMPEG), "-v", "info", "-i", str(HERE / "audio.wav"), "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True)
        gain = -16 - float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])
        for wav, out in ((HERE / "audio.wav", HERE / "Studio_Tutorial.mp4"), (HERE / "audio_music.wav", HERE / "Studio_Tutorial_music_only.mp4")):
            subprocess.run([str(ffdir / "ffmpeg"), "-y", "-v", "error", "-i", str(vid), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest",
                            "-movflags", "+faststart", str(out)], check=True)
            print(f"✓ {out}")


if __name__ == "__main__":
    main()
