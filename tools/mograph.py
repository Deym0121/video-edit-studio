#!/usr/bin/env python3
"""mograph — BBD motion graphics (HyperFrames) synced to an edited video.

  scenes.json (work/<name>/scenes.json) describes each graphic with *phrases*
  from the script ("start": "every workflow"), never raw times. mograph resolves
  every phrase on the edited timeline, writes one HyperFrames composition per
  scene (motion/scenes/<id>.html), renders it, and registers it as an overlay in
  decisions.json so `vedit render` composites it.

Usage:  mograph.py VIDEO [--only id,id] [--no-render] [--snap]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vedit  # noqa: E402
import brandkit  # noqa: E402  (Studio look: colours + fonts)

LOOK_DEC: dict = {}  # the project's decisions.json, so text_w measures the chosen font

MOTION = ROOT / "motion"
NODE_BIN = ROOT / "tools" / "node" / "bin"
W, H = 1080, 1920

ICONS = {
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "bolt": '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "table": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15l3-3 3 3"/>',
    "form": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "task": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
    "send": '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 0 0 4 0"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "dollar": '<path d="M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 9.3-9.3M16 7l3 3M14 9l2 2"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    "node": '<rect x="3" y="7" width="8" height="10" rx="2"/><rect x="13" y="7" width="8" height="10" rx="2"/><path d="M11 12h2"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "spark": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
    "play": '<polygon points="7 4 20 12 7 20 7 4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "pin": '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    "tag": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
    "branch": '<circle cx="6" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 7.5v9M18 10.5c0 4-12 2-12 6"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "pen": '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "flag": '<path d="M4 22V4M4 4h13l-2 4 2 4H4"/>',
    "code": '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    "route": '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.8"/><path d="m21 15-5-5L5 21"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4M3 12h18"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    "upload": '<path d="M12 21V9M7 14l5-5 5 5M4 3h16"/>',
    "terminal": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3M12 15h5"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.9 1.6-1.7 0-1.2-1-1.6-1-2.6 0-.9.7-1.6 1.6-1.6H17a4 4 0 0 0 4-4C21 6.5 17 3 12 3z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7.5" r="1.2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 12 10 5 10-5M2 17l10 5 10-5"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "cursor": '<path d="m4 3 7 18 2.5-7.5L21 11z"/>',
    "folder": '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "wand": '<path d="m15 4 5 5L9 20l-5-5zM12 7l5 5M5 3v3M3.5 4.5h3M19 15v3M17.5 16.5h3"/>',
    "type": '<path d="M4 7V4h16v3M9 20h6M12 4v16"/>',
    "plug": '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
    "chart": '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-7"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2 21a7 7 0 0 1 14 0M16 4.5a3.5 3.5 0 0 1 0 7M18 21a7 7 0 0 0-3-5.7"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "rocket": '<path d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2M14 4c3-2 7-2 7-2s0 4-2 7l-7 7-5-5z"/><circle cx="15" cy="9" r="1.5"/>',
    "brain": '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
}

CSS = """
@font-face{font-family:"Inter Tight";font-weight:500;font-display:block;src:url("../fonts/InterTight-wght-500.ttf")}
@font-face{font-family:"Inter Tight";font-weight:600;font-display:block;src:url("../fonts/InterTight-wght-600.ttf")}
@font-face{font-family:"Inter Tight";font-weight:700;font-display:block;src:url("../fonts/InterTight-wght-700.ttf")}
@font-face{font-family:"Inter Tight";font-weight:800;font-display:block;src:url("../fonts/InterTight-wght-800.ttf")}
@font-face{font-family:"Inter Tight";font-weight:900;font-display:block;src:url("../fonts/InterTight-wght-900.ttf")}
@font-face{font-family:"Great Vibes";font-weight:400;font-display:block;src:url("../fonts/GreatVibes.ttf")}
:root{--o:#FF6A00;--o2:#FF9A4D;--o3:#C24700;--grad:linear-gradient(180deg,#FF9A4D 0%,#FF6A00 100%);--ink:#1A0B04;
  --t2:#D9D2CC;--dim:#8C837C;--mut:#A39A93;--line:rgba(255,255,255,.08);--edge:rgba(255,140,60,.30);--card:rgba(29,21,19,.94);
  --glow:rgba(255,106,0,.55);--red:#FF6A00;--navy:#0D1B2A}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:transparent}
body{font-family:"Inter Tight",Inter,"Helvetica Neue",Arial,sans-serif;color:#fff;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.scene{position:absolute;inset:0;overflow:hidden}
/* inspiration background: warm near-black, big orange-brown glow top-right, softer one bottom-left, faint dot grid */
.bg{position:absolute;inset:0;background:
  radial-gradient(1000px 1000px at 86% 7%,rgba(125,52,10,.80) 0%,rgba(92,38,8,.58) 24%,rgba(62,26,7,.30) 50%,transparent 75%),
  radial-gradient(1300px 1200px at 0% 100%,rgba(88,40,10,.62) 0%,rgba(62,28,8,.42) 34%,rgba(40,18,6,.22) 58%,transparent 80%),
  radial-gradient(900px 600px at 45% 16%,rgba(78,32,9,.34) 0%,transparent 72%),#0C0908}
.glow{position:absolute;right:-260px;top:-260px;width:900px;height:900px;border-radius:50%;
  background:radial-gradient(closest-side,rgba(140,58,12,.35),transparent 100%)}
.grain{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.09) 1.3px,transparent 1.8px);background-size:44px 44px;background-position:22px 22px}
.panel .bg{background:radial-gradient(90% 60% at 50% 48%,rgba(12,9,8,.30) 0%,rgba(12,9,8,.58) 70%,rgba(12,9,8,.78) 100%)}
.panel .glow{opacity:.5}
.content{position:absolute;left:48px;right:48px;top:400px;bottom:480px;display:flex;flex-direction:column;justify-content:center}
.content.center{align-items:center;text-align:center}
.lower .bg,.lower .glow{display:none}
.lower .content{top:1170px;bottom:260px;justify-content:flex-end}
.lower .kicker{text-shadow:0 2px 10px rgba(0,0,0,.8)}
/* v7 band (webinar split layout, Lloyd 2026-10-21): a compact explainer card over the lower part of the screen half
   (y 560–1030) — the top of the screen, his face and the seam captions stay visible */
.band .bg,.band .glow,.band .grain{display:none}
.band .content{top:560px;bottom:890px;left:36px;right:36px;padding:24px 34px;border-radius:30px;background:rgba(16,11,9,.92);
  border:2px solid rgba(255,106,0,.72);box-shadow:0 24px 60px rgba(0,0,0,.55),0 0 40px rgba(255,106,0,.18);justify-content:center;overflow:hidden}
.band .content>*{zoom:.92}
.band .kicker{margin-bottom:14px;font-size:30px}.band .title{margin-bottom:18px}
.kicker{font-size:36px;font-weight:800;letter-spacing:.2em;color:var(--o2);text-transform:uppercase;display:flex;align-items:center;gap:20px;margin-bottom:28px}
.kicker:before{content:"";width:15px;height:15px;transform:rotate(45deg);border-radius:3px;background:var(--o);box-shadow:0 0 16px var(--glow);margin-left:4px}
.title{font-size:84px;font-weight:900;line-height:1.0;letter-spacing:-.035em;margin-bottom:40px}
.title.sm{font-size:68px;margin-bottom:32px}
.title em,.hl{font-style:normal;color:var(--o)}
.script{font-family:"Great Vibes",cursive;font-weight:400;font-size:118px;line-height:1.05;color:#fff;letter-spacing:0}
.card{background:var(--card);border:1.5px solid var(--edge);border-radius:36px}
.stack{background:var(--card);border:1.5px solid var(--edge);border-radius:36px;overflow:hidden}
.stack>.row{margin:0;border:0;border-radius:0;background:transparent;border-bottom:1px solid var(--line)}
.stack>.row:last-child{border-bottom:0}
.row{display:flex;align-items:center;gap:28px;padding:30px 34px;margin-bottom:18px;position:relative}
.row.sm{padding:22px 30px;margin-bottom:14px;gap:22px}
.ico{width:76px;height:76px;border-radius:20px;background:var(--grad);display:grid;place-items:center;flex:none;box-shadow:0 0 26px rgba(255,106,0,.40)}
.row.sm .ico{width:62px;height:62px;border-radius:17px}
.ico svg{width:38px;height:38px;stroke:#fff;fill:none;stroke-width:2.3;stroke-linecap:round;stroke-linejoin:round}
.ico.ghost{background:rgba(255,255,255,.06);box-shadow:none;border:1.5px solid var(--line)}
.ico.ghost svg{stroke:var(--mut)}
.ico.bad{background:rgba(255,106,0,.12);box-shadow:none;border:1.5px solid rgba(255,106,0,.5)}
.ico.bad svg{stroke:var(--o)}
.num{width:76px;height:76px;border-radius:20px;display:grid;place-items:center;flex:none;font-size:32px;font-weight:900;color:var(--ink);background:var(--grad);box-shadow:0 0 22px rgba(255,106,0,.35)}
.num.off{background-color:rgba(255,255,255,.06);background-image:linear-gradient(180deg,rgba(255,154,77,0) 0%,rgba(255,106,0,0) 100%);color:var(--mut);box-shadow:none}
.t{font-size:48px;font-weight:800;letter-spacing:-.02em}
.row.sm .t{font-size:40px}
.s{font-size:32px;color:var(--mut);margin-top:6px;font-weight:600}
.arrow{color:var(--o);font-weight:900;margin:0 10px}
.chips{display:flex;flex-wrap:wrap;gap:16px}
.chip{display:inline-flex;align-items:center;gap:14px;padding:20px 32px;border-radius:999px;font-size:44px;font-weight:800;
  background-color:rgba(255,255,255,.06);background-image:linear-gradient(180deg,rgba(255,154,77,0) 0%,rgba(255,106,0,0) 100%);border:1.5px solid var(--line)}
.chip svg{width:36px;height:36px;stroke:var(--o);fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.chip.on,.on-now{background-image:var(--grad);border-color:transparent;color:var(--ink);box-shadow:0 0 34px rgba(255,106,0,.5)}
.chip.on svg{stroke:var(--ink)}
.chip.no{color:var(--dim);background:rgba(255,255,255,.03)}
.tag{display:inline-flex;align-items:center;padding:8px 22px;border-radius:999px;font-size:30px;font-weight:700;border:1.5px solid rgba(255,140,60,.6);color:var(--o2)}
.tag.on{background:var(--grad);color:var(--ink);border-color:transparent}
.pill{display:inline-flex;align-self:flex-start;align-items:center;gap:18px;margin-top:26px;padding:28px 50px;border-radius:999px;
  background:var(--grad);color:var(--ink);font-size:56px;font-weight:800;letter-spacing:-.01em;box-shadow:0 0 50px rgba(255,106,0,.5)}
.pill svg{width:42px;height:42px;stroke:var(--ink);fill:none;stroke-width:2.8;stroke-linecap:round;stroke-linejoin:round}
.pill.wide{align-self:stretch;justify-content:center}
.big{font-size:330px;font-weight:900;letter-spacing:-.05em;line-height:.86;color:var(--o);text-shadow:0 0 40px rgba(255,106,0,.55),0 0 110px rgba(255,106,0,.25)}
.sub{font-size:56px;font-weight:800;letter-spacing:-.02em;margin-top:18px;color:var(--t2)}
.strike{position:absolute;left:24px;right:24px;top:50%;height:6px;border-radius:3px;background:var(--o);box-shadow:0 0 14px var(--glow)}
.dimmed{opacity:.4}
.vline{position:absolute;left:111px;width:4px;border-radius:2px;background:linear-gradient(var(--o),rgba(255,106,0,.15))}
.toast{display:flex;align-items:center;gap:22px;padding:26px 32px;border-radius:28px;background:rgba(255,106,0,.10);border:1.5px solid var(--o);box-shadow:0 0 50px rgba(255,106,0,.25)}
.mono{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace}
.bubble{max-width:800px;padding:28px 36px;border-radius:36px;font-size:44px;font-weight:600;line-height:1.3;margin-bottom:20px}
.bubble.them{background:var(--card);border:1.5px solid var(--edge);border-bottom-left-radius:10px}
.bubble.me{margin-left:auto;background:var(--grad);color:var(--ink);border-bottom-right-radius:10px;box-shadow:0 0 40px rgba(255,106,0,.4)}
.bubble.me .hl{color:#fff;font-weight:800}
.meta{font-size:26px;color:var(--mut);font-weight:600;margin:-8px 0 20px 8px}
.bar{height:22px;border-radius:11px;background:rgba(255,255,255,.08);overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#FF9A4D,#FF6A00);border-radius:11px}
.bar.off i{background:rgba(255,255,255,.28)}
.spin{width:64px;height:64px;border-radius:50%;border:7px solid rgba(255,255,255,.12);border-top-color:var(--o)}
/* new inspiration blocks */
.meter{display:grid;grid-template-columns:270px 1fr 140px;align-items:center;gap:26px;padding:32px 34px;border-bottom:1px solid var(--line)}
.meter:last-child{border-bottom:0}
.meter .t{font-size:46px}.meter .pc{font-size:46px;font-weight:800;text-align:right;color:var(--t2)}
.meter.hot{margin:14px;padding:22px 20px;border:1.5px solid var(--o);border-radius:24px;background:rgba(255,106,0,.08)}
.meter.hot .pc{color:var(--o2)}
.opt{display:flex;align-items:center;gap:24px;padding:26px 30px;border-bottom:1px solid var(--line)}
.opt:last-child{border-bottom:0}
.opt .k{width:52px;height:52px;border-radius:14px;display:grid;place-items:center;font-size:28px;font-weight:800;background:rgba(255,255,255,.07);color:var(--mut)}
.opt .t{flex:1;font-size:44px}
.opt .rd{width:40px;height:40px;border-radius:50%;border:2.5px solid rgba(255,255,255,.25)}
.opt.sel{margin:10px;border:1.5px solid var(--o);border-radius:22px;background:rgba(255,106,0,.08)}
.opt.sel .rd{border-color:var(--o);background:radial-gradient(circle,var(--o) 0 42%,transparent 46%)}
.flow{display:flex;align-items:center}
.fnode{flex:1;display:flex;flex-direction:column;align-items:center;gap:14px;padding:30px 10px;border-radius:30px;background:var(--card);border:1.5px solid var(--edge);font-size:36px;font-weight:800}
.fnode svg{width:52px;height:52px;stroke:#fff;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.fnode.hot{background:var(--grad);color:var(--ink);border-color:transparent;box-shadow:0 0 50px rgba(255,106,0,.5)}
.fnode.hot svg{stroke:var(--ink)}
.wire{width:34px;height:4px;flex:none;background:var(--o);box-shadow:0 0 10px var(--glow)}
.chap{display:flex;flex-direction:column;align-items:center;text-align:center;width:100%}
.chap .step{font-size:38px;font-weight:800;letter-spacing:.3em;color:var(--t2);margin-bottom:6px}
.chap .mo{font-size:168px;font-weight:900;letter-spacing:-.045em;line-height:.88;color:var(--o);text-shadow:0 0 40px rgba(255,106,0,.55)}
.chap .what{font-family:"Great Vibes",cursive;font-size:120px;line-height:1.05;margin-top:-6px}
.stamp{position:absolute;right:30px;bottom:-30px;padding:10px 26px;border:5px solid var(--o);border-radius:14px;color:var(--o);
  font-size:52px;font-weight:900;letter-spacing:.04em;transform:rotate(-8deg);background:rgba(12,9,8,.6);text-transform:uppercase}
.mm{position:relative;width:984px;height:1000px}
.mm svg.lines{position:absolute;inset:0}
.mcore{position:absolute;left:50%;top:50%;width:300px;height:300px;margin:-150px 0 0 -150px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFB27A,#FF6A00 55%,#C24700);
  display:grid;place-items:center;text-align:center;color:var(--ink);font-size:46px;font-weight:900;line-height:1.0;letter-spacing:-.02em;box-shadow:0 0 90px rgba(255,106,0,.55);padding:30px}
.mnode{position:absolute;transform:translate(-50%,-50%);display:flex;align-items:center;gap:14px;padding:16px 22px;border-radius:22px;background:var(--card);border:1.5px solid var(--edge);font-size:32px;font-weight:800;width:max-content;max-width:330px;line-height:1.1}
.mnode .ico{width:48px;height:48px;border-radius:13px}.mnode .ico svg{width:26px;height:26px}
.lp{position:relative;width:860px;height:860px;margin:0 auto}
.lp svg{position:absolute;inset:0}
.lnode{position:absolute;transform:translate(-50%,-50%);padding:16px 30px;border-radius:999px;background:var(--card);border:1.5px solid var(--edge);font-size:38px;font-weight:800;white-space:nowrap}
.lcore{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:44px;font-weight:900;color:var(--t2);text-align:center}
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.tile{display:flex;align-items:center;gap:20px;padding:26px 28px;border-radius:28px;background:var(--card);border:1.5px solid var(--edge);font-size:42px;font-weight:800}
.tile .ico{width:60px;height:60px;border-radius:16px}.tile .ico svg{width:32px;height:32px;stroke:var(--ink)}
.appr .hd{display:flex;align-items:center;gap:20px;padding:28px 32px;border-bottom:1px solid var(--line)}
.appr .ln{display:flex;justify-content:space-between;align-items:center;padding:26px 32px;font-size:40px;font-weight:800}
.appr .btns{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:0 32px 30px}
.btn{padding:24px;border-radius:20px;text-align:center;font-size:40px;font-weight:800;background:rgba(255,255,255,.07)}
.btn.go{background-color:rgba(255,255,255,.07);background-image:linear-gradient(180deg,rgba(255,154,77,0) 0%,rgba(255,106,0,0) 100%)}
/* kinetic lockup (design system §5): words over the talking head, no box, shadow only */
.lockup .bg,.lockup .glow{display:none}
.lockup .content{top:1060px;bottom:460px;left:64px;right:144px;align-items:center;justify-content:center;gap:4px}
.lk-row{display:flex;align-items:center;justify-content:center;gap:22px;flex-wrap:nowrap}
.lk-row.l{justify-content:flex-start;align-self:stretch}
.lk{--sh:0 0 2px rgba(0,0,0,.85),0 2px 5px rgba(0,0,0,.6),0 6px 26px rgba(0,0,0,.55);text-shadow:var(--sh);color:#fff;white-space:nowrap}
.lk.md{font-size:70px;font-weight:800;line-height:1.05;letter-spacing:-.015em}
.lk.xl{font-size:150px;font-weight:900;line-height:.86;letter-spacing:-.045em;color:var(--o);
  text-shadow:0 0 2px rgba(0,0,0,.6),0 0 30px rgba(255,106,0,.55),0 6px 26px rgba(0,0,0,.45)}
.lk.sc{font-family:"Great Vibes",cursive;font-weight:400;font-size:118px;line-height:1;letter-spacing:0;padding:0 8px}
.lk-stack{display:flex;flex-direction:column;align-items:flex-end}
.lk-stack.l{align-items:flex-start}
.lk.sm{font-size:40px;font-weight:700;line-height:1.02}
.lk.tag{font-size:46px;font-weight:800;padding:10px 30px;border-radius:999px;background:var(--grad);color:var(--ink);text-shadow:none;box-shadow:0 0 30px rgba(255,106,0,.5)}
.lk.pl{font-size:30px;font-weight:700;padding:10px 24px;border-radius:999px;background:rgba(20,14,12,.82);border:1.5px solid rgba(255,255,255,.14);text-shadow:none}
/* ===== v4 GLASS (DESIGN_SYSTEM §13): the scene is see-through; vedit puts the footage, heavily blurred and
   warm-darkened, behind it — frosted glass over the live video. Cards are glass panes with a top highlight. */
.glass .bg{background:
  radial-gradient(1000px 900px at 90% 4%,rgba(255,106,0,.34) 0%,rgba(194,71,0,.16) 40%,transparent 72%),
  radial-gradient(1200px 1000px at -5% 104%,rgba(194,71,0,.30) 0%,rgba(120,44,6,.14) 45%,transparent 75%),
  linear-gradient(180deg,rgba(12,9,8,.42) 0%,rgba(12,9,8,.58) 100%)}
.glass .glow{background:radial-gradient(closest-side,rgba(255,120,30,.22),transparent 100%)}
.glass .grain{opacity:.5}
.glass .content{top:300px;bottom:400px}
.glass .content>*{zoom:1.13}  /* glass scenes read on a phone: everything ~13% bigger */
.glass .content>.phone,.glass .content>.ctl,.glass .content>.reel,.glass .content>.orb{zoom:1}
.glass .card,.glass .stack,.glass .fnode,.glass .tile,.glass .mnode,.glass .lnode,.glass .bubble.them,.glass .win,.glass .gpane{
  background-color:rgba(255,255,255,.035);
  background-image:linear-gradient(155deg,rgba(255,255,255,.17) 0%,rgba(255,255,255,.06) 42%,rgba(255,255,255,.025) 100%);
  border:1.5px solid rgba(255,255,255,.17);
  box-shadow:inset 0 1.5px 0 rgba(255,255,255,.30),inset 0 0 40px rgba(255,255,255,.03),0 34px 90px rgba(0,0,0,.50),0 0 0 1px rgba(255,140,60,.08);
  backdrop-filter:blur(28px) saturate(1.35);-webkit-backdrop-filter:blur(28px) saturate(1.35)}
.glass .chip,.glass .ico.ghost,.glass .num.off,.glass .btn{background-color:rgba(255,255,255,.08);border:1.5px solid rgba(255,255,255,.16);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.22);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
.glass .stack>.row{background:transparent;border-bottom:1px solid rgba(255,255,255,.10);box-shadow:none;backdrop-filter:none}
.glass .title,.glass .big,.glass .chap .mo{text-shadow:0 4px 30px rgba(0,0,0,.45)}
.sheen{position:absolute;top:-25%;left:0;width:34%;height:150%;pointer-events:none;transform:translateX(-160%) rotate(16deg);
  background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.0) 20%,rgba(255,226,200,.20) 50%,rgba(255,255,255,0) 80%,transparent 100%);mix-blend-mode:screen}
/* window chrome (terminal, app, player) */
.win{border-radius:34px;overflow:hidden}
.win .bar2{display:flex;align-items:center;gap:12px;padding:22px 28px;border-bottom:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04)}
.win .dot{width:18px;height:18px;border-radius:50%;background:rgba(255,255,255,.22)}
.win .dot:first-child{background:#FF6A00;box-shadow:0 0 10px rgba(255,106,0,.6)}
.win .wt{margin-left:14px;font-size:28px;font-weight:700;color:var(--mut);letter-spacing:.01em}
.win .wb{padding:30px 34px;display:flex;flex-direction:column;gap:20px}
.tl{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-size:33px;line-height:1.38;font-weight:600;color:var(--t2);white-space:pre-wrap}
.tl .p{color:var(--o);font-weight:800}
.tl.dim{color:var(--dim)}
.tl.ok{color:#fff}.tl.ok .p{color:var(--o)}
.tl .k{color:var(--o2)}
.caret{display:inline-block;width:16px;height:36px;margin-left:6px;vertical-align:-6px;background:var(--o);border-radius:3px}
.sw{display:flex;align-items:center;gap:18px;padding:16px 26px 16px 16px;border-radius:999px;font-size:38px;font-weight:800}
.sw i{width:58px;height:58px;border-radius:50%;border:2px solid rgba(255,255,255,.35);box-shadow:inset 0 2px 6px rgba(255,255,255,.25)}
/* phone mock (preview / storyboard) */
.phone{position:relative;width:520px;height:924px;border-radius:58px;padding:16px;margin:0 auto;
  background:linear-gradient(160deg,rgba(255,255,255,.22),rgba(255,255,255,.05));border:1.5px solid rgba(255,255,255,.22);
  box-shadow:inset 0 1.5px 0 rgba(255,255,255,.35),0 40px 100px rgba(0,0,0,.55)}
.phone .scr{position:relative;width:100%;height:100%;border-radius:44px;overflow:hidden;background:
  radial-gradient(420px 360px at 85% 8%,rgba(255,106,0,.40),transparent 70%),linear-gradient(180deg,#1A120E,#0C0908);
  padding:56px 28px 30px;display:flex;flex-direction:column;gap:16px}
.phone .notch{position:absolute;top:28px;left:50%;width:120px;height:30px;margin-left:-60px;border-radius:20px;background:#000;z-index:3}
.phone .hl2{font-size:56px;font-weight:900;letter-spacing:-.03em;line-height:1.0}
.phone .mini{display:flex;align-items:center;gap:16px;padding:18px 20px;border-radius:22px;font-size:34px;font-weight:800;
  background:linear-gradient(155deg,rgba(255,255,255,.16),rgba(255,255,255,.05));border:1px solid rgba(255,255,255,.16)}
.phone .mini .ico{width:56px;height:56px;border-radius:15px}.phone .mini .ico svg{width:28px;height:28px}
.phone .wire2{position:absolute;left:51px;width:4px;border-radius:2px;background:linear-gradient(var(--o),rgba(255,106,0,.3));box-shadow:0 0 10px var(--glow)}
.phone .cta2{margin-top:auto;align-self:center;padding:18px 40px;border-radius:999px;background:var(--grad);color:var(--ink);font-size:36px;font-weight:900;box-shadow:0 0 30px rgba(255,106,0,.5)}
.phone .nm{align-self:center;font-family:"Great Vibes",cursive;font-size:76px;line-height:1}
.ctl{display:flex;align-items:center;gap:20px;width:600px;margin:28px auto 0}
.ctl .pb{width:70px;height:70px;border-radius:50%;background:var(--grad);display:grid;place-items:center;box-shadow:0 0 26px rgba(255,106,0,.45);flex:none}
.ctl .pb svg{width:30px;height:30px;fill:var(--ink);stroke:none;margin-left:4px}
.ctl .bar{flex:1;height:12px}
.ctl .tc{font-family:"JetBrains Mono",monospace;font-size:26px;color:var(--mut);font-weight:600}
/* drop zone */
.drop{border:3px dashed rgba(255,154,77,.55);border-radius:36px;padding:40px 34px;display:flex;flex-direction:column;gap:18px;align-items:stretch}
.drop .dz{display:flex;align-items:center;justify-content:center;gap:18px;font-size:38px;font-weight:800;color:var(--o2);padding:10px 0 6px}
.drop .dz svg{width:44px;height:44px;stroke:var(--o2);fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
/* duo: two app tiles with a plus */
.duo{display:flex;align-items:stretch;gap:0}
.duo .card{flex:1;padding:44px 30px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:20px}
.duo .ico{width:120px;height:120px;border-radius:32px}.duo .ico svg{width:60px;height:60px}
.duo .t{font-size:50px}.duo .s{font-size:30px}
.duo .plus{align-self:center;width:84px;flex:none;text-align:center;font-size:84px;font-weight:900;color:var(--o);text-shadow:0 0 30px var(--glow)}
/* export */
.pct{font-size:150px;font-weight:900;letter-spacing:-.05em;line-height:.9;color:var(--o);text-shadow:0 0 40px rgba(255,106,0,.5)}
/* text behind the speaker (vedit cuts the person out on top of it) */
.behind .bg,.behind .glow,.behind .grain{display:none}
.behind .content{top:0;bottom:auto;left:0;right:0;height:1920px;display:block}
.bt{position:absolute;left:0;right:0;text-align:center;font-weight:900;letter-spacing:-.045em;line-height:.8;white-space:nowrap;text-transform:uppercase;
  filter:drop-shadow(0 10px 40px rgba(0,0,0,.35)) drop-shadow(0 0 50px rgba(255,106,0,.30))}
.bt span{display:inline-block;padding:0 .01em;background:linear-gradient(180deg,#FFB27A 0%,#FF6A00 55%,#E05500 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.bt.w span{background:linear-gradient(180deg,#FFFFFF 0%,#F1E2D6 100%);-webkit-background-clip:text;background-clip:text}
.bt.o span{background:none;-webkit-text-stroke:5px rgba(255,154,77,.95)}
.bk{position:absolute;left:0;right:0;text-align:center;font-size:44px;font-weight:800;letter-spacing:.24em;color:#fff;text-transform:uppercase;
  text-shadow:0 2px 14px rgba(0,0,0,.7)}
.bk.scr{font-family:"Great Vibes",cursive;font-weight:400;letter-spacing:0;text-transform:none;line-height:1;z-index:2;
  text-shadow:0 3px 10px rgba(0,0,0,.65),0 0 30px rgba(0,0,0,.35)}
.bk.big{font-weight:900;letter-spacing:-.025em;line-height:.95;text-shadow:0 4px 0 rgba(0,0,0,.25),0 8px 36px rgba(0,0,0,.6)}
/* pixel office (Pixel Agents) */
.office{position:relative;width:100%;height:560px;overflow:hidden;
  background:repeating-conic-gradient(rgba(255,170,110,.10) 0 25%,rgba(255,255,255,.035) 0 50%) 0 0/60px 60px,linear-gradient(180deg,rgba(60,32,18,.55),rgba(30,18,12,.65))}
.office .wall{position:absolute;left:0;right:0;top:0;height:120px;background:linear-gradient(180deg,rgba(255,255,255,.10),rgba(255,255,255,.04));border-bottom:4px solid rgba(255,154,77,.35)}
.office .win2{position:absolute;top:26px;width:120px;height:62px;border-radius:6px;background:linear-gradient(180deg,rgba(255,180,120,.35),rgba(255,106,0,.12));border:3px solid rgba(255,255,255,.18)}
.office .desk{position:absolute;width:200px;height:78px;border-radius:8px;background:#6B3E22;box-shadow:inset 0 -10px 0 #4E2C17,0 10px 0 rgba(0,0,0,.25)}
.office .mon{position:absolute;left:46px;top:-74px;width:108px;height:74px;border-radius:6px;background:#1A120E;border:4px solid #3A2A22;overflow:hidden}
.office .mon i{display:block;height:8px;margin:8px 8px 0;border-radius:3px;background:rgba(255,154,77,.85);transform-origin:left center;transform:scaleX(0)}
.office .glowm{position:absolute;left:30px;top:-110px;width:140px;height:140px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,106,0,.55),transparent);opacity:0}
.office .plant{position:absolute;width:44px;height:70px}
.office .plant:before{content:"";position:absolute;bottom:0;left:8px;width:28px;height:26px;background:#8C4A24;border-radius:4px}
.office .plant:after{content:"";position:absolute;top:0;left:0;width:44px;height:48px;background:#3E7A3A;border-radius:50% 50% 40% 40%}
.agent{position:absolute;left:0;top:0;width:96px;height:120px}
.agent .spr{position:absolute;left:0;top:0;width:12px;height:12px}
.agent .tagp{position:absolute;left:50%;top:-50px;transform:translateX(-50%);white-space:nowrap;padding:6px 16px;border-radius:999px;font-size:26px;font-weight:800;
  background:rgba(20,14,12,.85);border:1.5px solid rgba(255,154,77,.6);color:#fff}
.agent .bub{position:absolute;left:80px;top:-14px;padding:4px 12px;border-radius:14px 14px 14px 4px;background:var(--grad);color:var(--ink);font-family:"JetBrains Mono",monospace;font-size:22px;font-weight:800}
.live{display:inline-flex;align-items:center;gap:10px;margin-left:auto;padding:6px 16px;border-radius:999px;background:rgba(255,106,0,.16);border:1.5px solid rgba(255,106,0,.7);color:var(--o2);font-size:24px;font-weight:800;letter-spacing:.12em}
.live:before{content:"";width:12px;height:12px;border-radius:50%;background:var(--o);box-shadow:0 0 10px var(--o)}
/* ===== real media inside scenes (our own clips / screenshots, motion/clips/) */
.vclip,.mimg{width:100%;height:100%;object-fit:cover;display:block}
.phone.media .scr{padding:0;background:#000}
.reel{display:flex;justify-content:center;gap:22px;align-items:flex-start}
.reel .cell{display:flex;flex-direction:column;align-items:center;gap:22px}
.reel .phone{width:312px;height:555px;border-radius:44px;padding:10px}
.reel .phone .scr{border-radius:31px}
.reel .phone .notch{top:18px;width:80px;height:20px;margin-left:-40px}
.reel .chip{font-size:36px;padding:14px 28px}
.orb{position:relative;width:100%;height:860px;perspective:2400px}
.ring{position:absolute;left:50%;top:50%;width:0;height:0;transform-style:preserve-3d}
.orb .it{position:absolute;left:-165px;top:-293px;width:330px;height:586px;border-radius:30px;overflow:hidden;
  border:2px solid rgba(255,255,255,.22);box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,140,60,.15)}
.orb .it .lab{position:absolute;left:14px;bottom:14px;padding:6px 14px;border-radius:999px;font-size:22px;font-weight:800;background:rgba(20,14,12,.85);border:1.5px solid rgba(255,154,77,.6)}
/* orbit text cards (3 fonts: mono kicker · Inter Tight word · Great Vibes line); two faces so the back never shows mirrored text */
.orb .it.wk{overflow:visible;border:none;box-shadow:none;background:none;transform-style:preserve-3d}
.wk .f,.wk .b{position:absolute;inset:0;border-radius:30px;overflow:hidden;backface-visibility:hidden;-webkit-backface-visibility:hidden;
  border:2px solid rgba(255,154,77,.55);box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 46px rgba(255,106,0,.16)}
.wk .f{background:radial-gradient(120% 70% at 85% 0%,rgba(255,106,0,.30),transparent 60%),linear-gradient(165deg,#2A1B16,#130D0B 70%);
  display:flex;flex-direction:column;align-items:flex-start;padding:36px 32px 34px}
.wk .b{transform:rotateY(180deg);background:radial-gradient(90% 60% at 50% 45%,rgba(255,106,0,.22),transparent 70%),#140E0C;
  display:grid;place-items:center;font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-weight:600;font-size:150px;color:rgba(255,154,77,.28)}
.wk .wk-k{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-weight:600;font-size:30px;letter-spacing:.04em;color:#FF9A4D}
.wk .ico{margin-top:auto;width:100px;height:100px;border-radius:28px}.wk .ico svg{width:54px;height:54px;stroke:#1A0B04}
.wk .wk-t{margin-top:24px;font-weight:900;font-size:74px;letter-spacing:-.045em;line-height:.9;color:#fff;white-space:nowrap}
.wk .wk-s{font-family:"Great Vibes",cursive;font-size:58px;line-height:1.08;color:#FFB27A;margin-top:6px;white-space:nowrap}
.wk .wk-d{margin-top:20px;font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-weight:600;font-size:22px;letter-spacing:.1em;color:#8C837C}
/* demo screens (before → after) */
.demo{position:relative;height:640px;border-radius:34px;overflow:hidden}
.demo .st{position:absolute;left:26px;top:22px;padding:8px 20px;border-radius:999px;font-size:26px;font-weight:900;letter-spacing:.14em;
  background:rgba(255,255,255,.10);border:1.5px solid rgba(255,255,255,.2);color:var(--t2)}
.demo .st.af{background:var(--grad);color:var(--ink);border-color:transparent;opacity:0}
.demo .stage{position:absolute;inset:0;display:grid;place-items:center}
.demo .word{font-size:170px;font-weight:900;letter-spacing:-.05em;color:var(--o);text-shadow:0 0 40px rgba(255,106,0,.5)}
.demo .ringt{position:absolute;right:30px;top:20px;width:110px;height:110px}
.demo .ringt span{position:absolute;inset:0;display:grid;place-items:center;font-size:30px;font-weight:900;color:#fff}
.demo .bcard{width:520px;padding:34px 36px;display:flex;align-items:center;gap:24px}
.demo .floor{position:absolute;left:12%;right:12%;top:62%;height:3px;background:rgba(255,255,255,.18)}
.demo .mini{position:relative;width:330px;height:586px;border-radius:26px;background:linear-gradient(180deg,#1A120E,#0C0908);border:2px solid rgba(255,255,255,.2);overflow:hidden}
.demo .safe{position:absolute;inset:26px;border:3px dashed rgba(255,255,255,.28);border-radius:14px}
.demo .hl3{position:absolute;left:0;right:0;top:150px;text-align:center;font-weight:900;letter-spacing:-.04em;line-height:.92;color:#fff;white-space:nowrap}
.demo .hl3 em{font-style:normal;color:var(--o)}
/* ===== v5 · NEWSROOM (DESIGN_SYSTEM §14): charcoal editorial pages, serif headlines, orange highlighter,
   orange wipe slab transitions, face cam bubble (vedit) bottom-right, source pill on every news scene */
.news .sbody{position:absolute;inset:0;overflow:hidden}
.news .bg{background:
  radial-gradient(900px 700px at 0% 100%,rgba(255,106,0,.16),transparent 70%),
  radial-gradient(700px 500px at 100% 0%,rgba(255,106,0,.10),transparent 70%),
  repeating-linear-gradient(0deg,rgba(255,255,255,.022) 0 1px,transparent 1px 6px),#151311}
.news .glow,.news .grain{display:none}
.news .masthead{position:absolute;left:64px;right:144px;top:236px;display:flex;align-items:center;gap:18px;padding-bottom:16px;
  border-bottom:2px solid rgba(255,106,0,.85);font-family:"Inter Tight";font-size:26px;font-weight:700;color:var(--mut);letter-spacing:.14em;text-transform:uppercase}
.news .masthead b{color:#fff;font-family:"Inter Tight";font-weight:900;font-size:30px;letter-spacing:.14em}
.news .masthead b i{font-style:normal;color:var(--o)}
.news .masthead .dt{margin-left:auto}
.news .content{top:330px;bottom:760px;left:64px;right:144px;justify-content:center}
.news .content>*{zoom:1}
.news .phone{zoom:.82}.news .bubble{max-width:740px}
.news .brw .pg.img{height:640px}
.news .kicker{font-size:34px}

.news .title{font-size:84px}
.news .title.sm{font-size:68px}
.news .title em,.news .hl{font-style:normal;color:var(--o)}
.news .card,.news .stack{background:#1E1B19;border:1.5px solid rgba(255,255,255,.09);border-radius:20px;box-shadow:0 24px 60px rgba(0,0,0,.45)}
.news .row.card,.news .stack{border-left:6px solid var(--o)}
.news .stack>.row{border-left:0}
.news .chip{border-radius:12px;background:#24201D;border:1.5px solid rgba(255,255,255,.1)}
.news .ico{border-radius:14px}
.news .bubble.them{background:#24201D;border:1.5px solid rgba(255,255,255,.1)}
.src{position:absolute;left:64px;top:1214px;max-width:760px;display:flex;flex-direction:column;gap:6px;padding:16px 22px;border-radius:14px;
  background:rgba(20,18,16,.92);border:1.5px solid rgba(255,255,255,.12);font-family:"Inter Tight"}
.src .l{font-size:20px;font-weight:800;letter-spacing:.2em;color:var(--o)}
.src .d{font-size:28px;font-weight:800;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src .t{font-size:22px;font-weight:600;color:var(--mut);white-space:nowrap}
.cam{position:absolute;left:64px;top:1100px;width:250px;height:250px;border-radius:50%;border:7px solid var(--o);
  box-shadow:0 0 0 6px rgba(21,19,17,.9),0 0 40px rgba(255,106,0,.45)}
.cam:after{content:"● LIVE";position:absolute;left:50%;bottom:-22px;transform:translateX(-50%);padding:4px 14px;border-radius:8px;background:var(--o);
  color:var(--ink);font:900 20px "Inter Tight";letter-spacing:.12em}
.wipe{position:absolute;top:0;bottom:0;left:0;width:300px;background:linear-gradient(90deg,#FFB27A,#FF6A00 45%,#E05500);
  box-shadow:0 0 80px rgba(255,106,0,.55);transform:translateX(1200px)}
.wipe:after{content:"";position:absolute;top:0;bottom:0;left:46%;width:16px;background:#151311}
/* article / browser card */
.brw{border-radius:22px;overflow:hidden;background:#F4EFEA;color:#141210;box-shadow:0 30px 80px rgba(0,0,0,.55)}
.brw .ub{display:flex;align-items:center;gap:12px;padding:16px 20px;background:#2A2623}
.brw .ub i{width:14px;height:14px;border-radius:50%;background:rgba(255,255,255,.25)}
.brw .ub .url{flex:1;margin-left:10px;padding:10px 18px;border-radius:10px;background:#151311;color:#D9D2CC;font:600 24px "JetBrains Mono",monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brw .pg{position:relative;padding:36px 38px 40px;overflow:hidden}
.brw .pg.img{padding:0;height:760px}
.brw .pg.img img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:top;transform-origin:50% 0}
.brw .outlet{font:900 26px "Inter Tight";letter-spacing:.16em;text-transform:uppercase;color:#C24700;margin-bottom:16px}
.brw .hd{font:800 52px/1.08 "Playfair Display",Georgia,serif;color:#141210;margin-bottom:18px}
.brw .hd .hl{color:#141210;font-style:normal}
.brw .by{font:600 24px "Inter Tight";color:#6B625B;margin-bottom:24px}
.brw .ln{height:16px;border-radius:8px;background:rgba(20,18,16,.12);margin:14px 0}
.brw .box{position:absolute;border:5px solid #FF6A00;border-radius:12px;box-shadow:0 0 0 9999px rgba(0,0,0,.35)}
/* stat */
.stat .n{font:900 230px/0.88 "Inter Tight";letter-spacing:-.05em;color:var(--o);text-shadow:0 0 50px rgba(255,106,0,.35)}
.stat .u{font:800 54px "Inter Tight";color:#fff;margin-top:14px}
.stat .x{font:600 32px "Inter Tight";color:var(--mut);margin-top:10px}
/* thumbnail hook (first 3 s, doubles as the thumbnail) */
.thumb .bg,.thumb .glow,.thumb .grain{display:none}
.thumb .content{top:auto;bottom:470px;left:64px;right:144px;display:flex;flex-direction:column;align-items:center;gap:6px}
.th-tag{display:inline-flex;align-items:center;gap:12px;margin-bottom:14px;padding:10px 22px;border-radius:10px;background:#151311;border:2px solid var(--o);
  color:#fff;font:900 34px "Inter Tight";letter-spacing:.14em;text-transform:uppercase}
.th-tag:before{content:"";width:16px;height:16px;border-radius:50%;background:var(--o);box-shadow:0 0 14px var(--o)}
/* v6 · On-screen tags: small transparent callouts sitting on the A-roll (no blur, no page, footage stays visible) */
.otag .bg,.otag .glow,.otag .grain{display:none}
.otag .content{top:236px;bottom:auto;left:64px;right:144px;display:flex;flex-direction:column;align-items:flex-start;gap:14px}
.otag.tbot .content{top:auto;bottom:520px}
/* mini side callouts (Lloyd 2026-10-20: "sa gilid-gilid lang, may mag-a-appear lang"): small, at the edge, never over the face/demo */
.otag.mini .tg{gap:16px;padding:12px 26px 12px 12px;border-radius:22px;max-width:660px;border-width:1.5px}
.otag.mini .tg.np{padding:12px 26px}
.otag.mini .tg-ic{width:62px;height:62px;border-radius:16px}.otag.mini .tg-ic svg{width:32px;height:32px}
.otag.mini .tg-k{font-size:20px;letter-spacing:.16em}.otag.mini .tg-t{font-size:42px}.otag.mini .tg-s{font-size:25px}
.otag.mini .content{gap:10px}.otag.mini .tg-steps{max-width:760px;gap:8px}
.otag.mini .tg-steps .chip{padding:9px 18px;font-size:25px;border-width:1.5px}.otag.mini .tg-steps .ar{font-size:22px}
.otag.sr .content{left:144px;right:64px;align-items:flex-end}.otag.sr .tg-steps{justify-content:flex-end}
/* webinar clip header (tools/zoomclip.py layout, 2026-10-21): card right of the cam bubble, above the screen panel (y 248–518) */
.otag.hdr .content{top:248px;bottom:auto;left:350px;right:120px;height:270px;justify-content:center;align-items:stretch;gap:10px}
.otag.hdr .tg{max-width:none;padding:20px 26px 22px;border-radius:26px;align-items:flex-start;background:rgba(21,16,13,.92)}
.otag.hdr .tg-tx{gap:6px;width:100%}
.otag.hdr .tg-k{font:600 20px "JetBrains Mono",monospace;letter-spacing:.06em;white-space:normal}
.otag.hdr .tg-t{white-space:normal;line-height:1.02;letter-spacing:-.035em}
.otag.hdr .tg-s{font:400 50px/1.08 "Great Vibes",cursive;color:#FFB27A;white-space:normal;letter-spacing:0;margin-top:2px}
.otag.hdr .tg-s:before{content:none}
.otag.hdr .tg-steps{gap:6px;max-width:none}.otag.hdr .tg-steps .chip{padding:8px 14px;font-size:22px;border-width:1.5px}.otag.hdr .tg-steps .ar{font-size:20px}
.tg{display:flex;align-items:center;gap:24px;padding:20px 34px 20px 20px;border-radius:30px;background:rgba(12,9,8,.84);
  border:2px solid rgba(255,106,0,.75);box-shadow:0 18px 50px rgba(0,0,0,.45),0 0 0 1px rgba(0,0,0,.25);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);max-width:872px}
.tg.np{padding:18px 34px}
.tg-av{width:104px;height:104px;border-radius:22px;flex:none;position:relative;overflow:hidden;
  background:radial-gradient(circle at 50% 30%,rgba(255,154,77,.30),rgba(255,106,0,0) 72%),#2A1408;border:1.5px solid rgba(255,106,0,.6)}
.tg-av .spr{position:absolute;left:0;top:0;width:12px;height:12px;transform:translate(15px,6px) scale(.78);transform-origin:0 0}
.tg-ic{width:88px;height:88px;border-radius:22px;flex:none;background:var(--grad);display:grid;place-items:center;box-shadow:0 0 26px rgba(255,106,0,.40)}
.tg-ic svg{width:44px;height:44px;stroke:#fff;fill:none;stroke-width:2.3;stroke-linecap:round;stroke-linejoin:round}
.tg-tx{display:flex;flex-direction:column;gap:4px;min-width:0}
.tg-k{font-size:26px;font-weight:800;letter-spacing:.18em;color:var(--o);text-transform:uppercase;white-space:nowrap}
.tg-t{font-size:62px;font-weight:900;letter-spacing:-.03em;line-height:1.0;white-space:nowrap}
.tg-t em{font-style:normal;color:var(--o)}
.tg-s{font-size:34px;font-weight:700;color:var(--t2);white-space:nowrap;font-family:"JetBrains Mono",monospace;letter-spacing:-.01em}
.tg-s:before{content:"› ";color:var(--o)}
.tg-steps{display:flex;flex-wrap:wrap;gap:12px;max-width:872px}
.tg-steps .chip{padding:14px 24px;font-size:32px;background:rgba(12,9,8,.84);border:2px solid rgba(255,106,0,.75);color:#fff}
.tg-steps .ar{align-self:center;color:var(--o);font-size:30px;font-weight:900}
/* Studio hooks: comment bubble (white, like a real comment) · proof counter · typed headline */
.tg.cm{background:#FFFFFF;border:none;border-radius:36px 36px 36px 10px;padding:24px 38px 24px 24px;align-items:flex-start;
  box-shadow:0 22px 60px rgba(0,0,0,.42);-webkit-backdrop-filter:none;backdrop-filter:none}
.tg.cm .tg-ic{width:84px;height:84px;border-radius:50%}
.tg.cm .tg-k{color:#6B6560;letter-spacing:0;text-transform:none;font-size:30px;font-weight:700}
.tg.cm .tg-t{color:#15110F;font-size:52px;font-weight:800;letter-spacing:-.02em;white-space:normal;max-width:690px;line-height:1.08}
.tg-m{display:flex;gap:26px;margin-top:8px;font-size:26px;font-weight:700;color:#8C837C}
.tg-m b{color:var(--o)}
.tg.ct .tg-t{font-size:104px;line-height:.95;color:var(--o);letter-spacing:-.04em}
.tg.ty .tg-t{white-space:normal;max-width:800px}
/* money moment: counter + stacked "received" notifications (buyer names are drawn as blurred bars — never real names) */
.money{display:flex;flex-direction:column;align-items:center;gap:26px;width:100%}
.money .mk{font-size:38px;font-weight:800;letter-spacing:.2em;color:var(--o2);text-transform:uppercase}
.money .mt{font-size:200px;font-weight:900;letter-spacing:-.05em;line-height:.9;color:var(--o);text-shadow:0 0 60px rgba(255,106,0,.45)}
.money .mt .pf{font-size:150px;margin-right:6px}
.money .ms{font-size:46px;font-weight:700;color:var(--t2);margin-top:-6px}
.ntf{width:860px;display:flex;flex-direction:column;gap:14px;margin-top:18px}
.nr{display:flex;align-items:center;gap:22px;padding:20px 26px;border-radius:24px;background:rgba(29,21,19,.94);border:1.5px solid var(--edge)}
.nr .nd{width:58px;height:58px;border-radius:16px;background:var(--grad);display:grid;place-items:center;flex:none}
.nr .nd svg{width:30px;height:30px;stroke:#fff;fill:none;stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}
.nr .nx{flex:1;display:flex;flex-direction:column;gap:8px}
.nr .nl{font-size:24px;color:var(--mut);font-weight:600}
.nr .nb{height:24px;border-radius:8px;background:linear-gradient(90deg,rgba(255,255,255,.55),rgba(255,255,255,.25));filter:blur(5px)}
.nr .na{font-size:40px;font-weight:900;color:var(--o)}
.nr .nt{font-size:22px;color:var(--dim);font-weight:600;text-align:right}
.th-row{font-family:"Inter Tight";font-weight:900;text-transform:uppercase;line-height:.92;letter-spacing:-.045em;color:#fff;white-space:nowrap;
  text-shadow:0 5px 0 rgba(0,0,0,.35),0 10px 44px rgba(0,0,0,.65)}
.th-row .o{color:var(--o)}
.th-row .hb{display:inline-block;background:var(--grad);color:var(--ink);padding:.02em .16em .04em;border-radius:.08em;text-shadow:none;transform:rotate(-2deg);
  box-shadow:0 12px 40px rgba(0,0,0,.45)}
/* carousel (coverflow): one card per item slides in on its phrase and stops centred, lit in the accent */
.car{position:relative;width:100%;height:640px;perspective:2200px}
.glass .content>.car{zoom:1}.news .car{zoom:.78}
.car .trk{position:absolute;left:50%;top:50%;width:0;height:0;transform-style:preserve-3d}
.cc{position:absolute;left:-260px;top:-310px;width:520px;height:620px;border-radius:40px;padding:40px 38px 44px;display:flex;flex-direction:column;opacity:0;
  background:radial-gradient(120% 70% at 85% 0%,rgba(255,106,0,.20),transparent 62%),linear-gradient(165deg,#2A1B16,#130D0B 72%);
  border:2px solid rgba(255,255,255,.22);box-shadow:0 34px 90px rgba(0,0,0,.55)}
.cc .cl{position:absolute;inset:-2px;border-radius:40px;border:3px solid var(--o);background:rgba(255,106,0,.08);
  box-shadow:0 0 70px rgba(255,106,0,.42),inset 0 0 50px rgba(255,106,0,.10);opacity:0}
.cc .ch{position:relative;display:flex;align-items:center;justify-content:space-between}
.cc .cn{position:relative;width:84px;height:84px;font-size:34px;font-weight:900;letter-spacing:-.02em}
.cc .cn span,.cc .cn b{position:absolute;inset:0;display:grid;place-items:center;border-radius:22px}
.cc .cn span{background:rgba(255,255,255,.07);border:1.5px solid rgba(255,255,255,.16);color:var(--mut)}
.cc .cn b{background:var(--grad);color:var(--ink);box-shadow:0 0 30px rgba(255,106,0,.5);opacity:0}
.cc .ico{width:84px;height:84px;border-radius:22px}.cc .ico svg{width:44px;height:44px}
.cc .ct{position:relative;margin-top:auto;font-weight:900;line-height:.96;letter-spacing:-.04em;color:#fff}
.cc .cs{position:relative;margin-top:18px;font-size:34px;font-weight:600;line-height:1.22;color:var(--mut)}
.cc .ico,.cc .ct,.cc .cs{opacity:0}
.cc .cq{position:absolute;left:38px;right:38px;bottom:48px;display:flex;flex-direction:column;gap:18px}  /* skeleton: not said yet */
.cc .cq i{display:block;height:30px;border-radius:15px;background:rgba(255,255,255,.13)}.cc .cq i:first-child{width:82%;height:54px;border-radius:20px}.cc .cq i:last-child{width:56%}
.cdots{display:flex;justify-content:center;gap:14px;margin-top:24px}
.cdots i{display:block;width:18px;height:18px;border-radius:9px;background:rgba(255,255,255,.24);opacity:0}
/* shrink card: vedit scales the real footage into the card (the face is never drawn or covered here); this page only
   dims around the card and draws the accent ring, kicker, title and chips outside it */
.shrink .bg,.shrink .glow,.shrink .grain{display:none}
.shrink .content{top:0;bottom:0;left:0;right:0;display:block}
.sk-dim{position:absolute;box-shadow:0 0 0 2600px rgba(12,9,8,.44)}
.sk-ring{position:absolute;border:3px solid var(--o);box-shadow:0 0 0 1.5px rgba(0,0,0,.30),0 0 50px rgba(255,106,0,.40),0 36px 90px rgba(0,0,0,.55)}
.sk-k{position:absolute;left:64px;right:64px;justify-content:center;margin:0;text-shadow:0 2px 12px rgba(0,0,0,.6)}
.sk-t{position:absolute;left:64px;right:64px;text-align:center;font-weight:900;line-height:1.0;letter-spacing:-.035em;white-space:nowrap;
  text-shadow:0 4px 30px rgba(0,0,0,.5)}
.sk-items{position:absolute;left:144px;right:144px;display:flex;flex-wrap:wrap;justify-content:center;gap:14px}
.sk-items .chip{font-size:38px;padding:16px 28px;background-color:rgba(20,14,12,.78);border:1.5px solid rgba(255,255,255,.16);box-shadow:0 14px 40px rgba(0,0,0,.4)}
"""

RUNTIME = """
const D = %(dur).3f;
const tl = gsap.timeline({ paused: true });
gsap.set(".scene", { opacity: 1 });
tl.fromTo(".glow", { opacity: .7, scale: 1 }, { opacity: 1, scale: 1.08, duration: D, ease: "sine.inOut" }, 0);
const N = (el, k, d) => (el.dataset[k] !== undefined ? parseFloat(el.dataset[k]) : d);
const full = !document.querySelector(".panel,.lower,.band,.lockup,.behind,.thumb,.otag,.shrink,.scene.news");
if (document.querySelector(".scene.band")) {  // band card slides up out of blur, fades down at the end
  tl.from(".content", { y: 46, opacity: 0, filter: "blur(14px)", duration: .45, ease: "expo.out" }, 0);
  if (D > 1) tl.to(".content", { y: 24, opacity: 0, filter: "blur(10px)", duration: .25, ease: "power2.in" }, D - .25);
}
const glass = !!document.querySelector(".scene.glass");
if (full && glass) {  // v4 glass: content materialises out of the frosted footage, a light sheen sweeps the pane
  tl.from(".content", { scale: 1.07, y: 26, filter: "blur(22px)", opacity: 0, duration: .55, ease: "expo.out" }, 0);
  if (D > 1) tl.to(".content", { scale: .965, y: -14, filter: "blur(16px)", opacity: 0, duration: .3, ease: "power2.in" }, D - .3);
  gsap.set(".sheen", { rotation: 16, xPercent: -160 });
  tl.to(".sheen", { xPercent: 430, duration: 1.0, ease: "power2.inOut" }, .04);
} else {
  if (full) tl.from(".content", { scale: 1.14, filter: "blur(18px)", opacity: 0, duration: .34, ease: "expo.out" }, 0);  // scene in
  if (full && D > 1) tl.to(".content", { scale: .94, filter: "blur(14px)", opacity: 0, duration: .22, ease: "power2.in" }, D - .22);  // out
}
const newsScene = document.querySelector(".scene.news");
if (newsScene) {  // v5.1 newsroom: smooth blur-fade + gentle push (Lloyd: smooth transitions, no slab)
  const sb = newsScene.querySelector(".sbody"), ct = newsScene.querySelector(".content");
  if (newsScene.dataset.win === "1") tl.fromTo(sb, { opacity: 0, scale: 1.06, filter: "blur(26px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: .6, ease: "power2.out" }, 0);
  else tl.fromTo(sb, { opacity: 0 }, { opacity: 1, duration: .35, ease: "sine.out" }, 0);  // chained: soft crossfade over the previous page
  tl.from(ct, { y: 46, opacity: 0, filter: "blur(14px)", duration: .6, ease: "expo.out" }, newsScene.dataset.win === "1" ? .22 : .08);
  const src = newsScene.querySelector(".src"); if (src) tl.from(src, { y: 18, opacity: 0, duration: .4, ease: "power2.out" }, .45);
  if (newsScene.dataset.wout === "1" && D > 1.2) tl.to(sb, { opacity: 0, scale: 1.04, filter: "blur(22px)", duration: .5, ease: "power2.in" }, D - .5);
  else if (D > 1.2) tl.to(ct, { opacity: 0, y: -24, filter: "blur(10px)", duration: .3, ease: "power2.in" }, D - .3);
}
document.querySelectorAll("[data-mark]").forEach((el) => {  // highlighter sweep on a phrase
  tl.fromTo(el, { backgroundSize: "0%% 100%%" }, { backgroundSize: "100%% 100%%", duration: .45, ease: "power2.out" }, N(el, "mark", 0)); });
document.querySelectorAll("[data-kb]").forEach((el) => {  // screenshot: slow push + jump to a focus area
  const z = N(el, "kz", 1.6), fx = N(el, "kx", 0), fy = N(el, "ky", 0), t = N(el, "kb", 1);
  tl.fromTo(el, { scale: 1.02 }, { scale: 1.08, duration: Math.max(.5, t), ease: "none" }, 0);
  tl.to(el, { scale: z, x: fx, y: fy, duration: .7, ease: "power3.inOut" }, t); });
document.querySelectorAll(".th-row").forEach((el, i) => {  // thumbnail hook rows slam in
  const t = N(el, "tat", .05 + i * .12);
  tl.from(el, { scale: 1.45, opacity: 0, rotation: i %% 2 ? 3 : -3, duration: .32, ease: "power4.out" }, t);
  tl.to(el, { keyframes: { x: [0, -10, 8, -4, 0] }, duration: .25, ease: "none" }, t + .28); });
document.querySelectorAll("[data-bt]").forEach((el) => {  // text behind the speaker: letters rise out of blur, slow push, clear
  const t = N(el, "bt", 0), sp = el.querySelectorAll("span");
  tl.from(sp, { yPercent: 55, opacity: 0, scale: 1.25, filter: "blur(18px)", duration: .6, ease: "expo.out", stagger: Math.min(.06, .5 / sp.length) }, t);
  tl.fromTo(el, { scale: 1 }, { scale: 1.05, duration: Math.max(.5, D - t), ease: "none" }, t);
  tl.to(el, { opacity: 0, y: -30, filter: "blur(14px)", duration: .3, ease: "power2.in" }, Math.max(t + .4, D - .3));
});
document.querySelectorAll("[data-orbit]").forEach((el) => {  // orbit carousel: steady turn over the scene
  tl.fromTo(el, { rotationY: 0 }, { rotationY: -360 * N(el, "orbit", .6), duration: D, ease: "none" }, 0);
});
document.querySelectorAll("[data-car]").forEach((car) => {  // carousel: cards wait as numbered shells; on its phrase a card slides
  const cs = [...car.querySelectorAll(".cc")], SP = N(car, "car", 400), dots = [...document.querySelectorAll(".cdots i")];  // to the centre,
  const pose = (d) => ({ x: d * SP, z: -Math.abs(d) * 190, rotationY: d < 0 ? 34 : d > 0 ? -34 : 0, scale: d ? .86 : 1,  // fills in + lights;
    opacity: [1, .6, .22][Math.abs(d)] || 0 });  // said cards step left, turned away and dimmed
  cs.forEach((c, j) => gsap.set(c, pose(j)));
  gsap.set(dots, { opacity: 1 });
  cs.forEach((c, i) => {
    const t = N(c, "cat", 0), lit = (el) => [el.querySelector(".cl"), el.querySelector(".cn b")];
    if (i) cs.forEach((o, j) => tl.to(o, { ...pose(j - i), duration: .6, ease: "power3.inOut" }, t));
    tl.fromTo(c.querySelectorAll(".ico,.ct,.cs"), { opacity: 0, y: 24, filter: "blur(10px)" },
      { opacity: 1, y: 0, filter: "blur(0px)", duration: .45, ease: "expo.out", stagger: .06, immediateRender: false }, t + .08);
    tl.to(c.querySelector(".cq"), { opacity: 0, duration: .2 }, t);
    tl.to(lit(c), { opacity: 1, duration: .3 }, t + .12);
    if (i) tl.to(lit(cs[i - 1]), { opacity: 0, duration: .3 }, t);
    if (dots[i]) tl.to(dots[i], { width: 54, backgroundColor: "#FF6A00", duration: .35, ease: "power2.out" }, t);
    if (i && dots[i - 1]) tl.to(dots[i - 1], { width: 18, backgroundColor: "rgba(255,106,0,.45)", duration: .35 }, t);
  });
});
const skr = document.querySelector(".sk-ring");
if (skr) {  // shrink card: the page dims in while vedit shrinks the footage into the hole, the ring lands, all clears before it grows back
  const ti = N(skr, "tin", .5), to = N(skr, "tout", .45);
  tl.fromTo(".sk-dim", { opacity: 0 }, { opacity: 1, duration: .35, ease: "sine.out" }, 0);
  tl.fromTo(skr, { opacity: 0, scale: 1.05 }, { opacity: 1, scale: 1, duration: .4, ease: "expo.out" }, ti * .6);
  if (D > ti + to + .3) tl.to(".content", { opacity: 0, filter: "blur(8px)", duration: to * .8, ease: "power2.in" }, D - to);
}
document.querySelectorAll("[data-demo]").forEach((el) => {  // before → after revision demos (deterministic loops)
  const m = el.dataset.demo, f = N(el, "fix", 2), t0 = N(el, "t0", .4);
  const bef = el.querySelector(".st:not(.af)"), aft = el.querySelector(".st.af");
  tl.to(bef, { opacity: 0, duration: .15 }, f); tl.to(aft, { opacity: 1, duration: .2 }, f);
  if (m === "hold") {
    const w = el.querySelector(".word"), rg = el.querySelector(".rg"), rs = el.querySelector(".rs"), L = 2 * Math.PI * 46;
    gsap.set(w, { opacity: 0 }); gsap.set(rg, { strokeDasharray: L, strokeDashoffset: L });
    for (let t = t0; t + .45 < f; t += .6) {  // too fast: flashes in and straight out
      tl.fromTo(w, { opacity: 0, scale: .8 }, { opacity: 1, scale: 1, duration: .1 }, t);
      tl.to(w, { opacity: 0, scale: 1.1, duration: .1 }, t + .22); }
    tl.fromTo(w, { opacity: 0, scale: .8 }, { opacity: 1, scale: 1, duration: .3, ease: "expo.out" }, f + .05);  // holds 2 s
    tl.to(rg, { strokeDashoffset: 0, duration: 2, ease: "none" }, f + .05);
    const st = [];
    for (let i = 0; i <= 4; i++) tl.set(rs, { textContent: (i * .5).toFixed(1) + "s" }, f + .05 + i * .5);
  } else if (m === "bounce") {
    const c = el.querySelector(".bcard");
    for (let t = t0; t + 1.05 < f; t += 1.15)  // too bouncy
      tl.fromTo(c, { y: -330 }, { y: 0, duration: 1.0, ease: "elastic.out(1.3,0.22)" }, t);
    tl.fromTo(c, { y: -330, opacity: 1 }, { y: 0, duration: .55, ease: "power3.out" }, f + .05);  // calm: lands once
    gsap.set(c, { y: -330 });
  } else {
    const h = el.querySelector(".hl3"), sf = el.querySelector(".safe");
    gsap.set(h, { fontSize: 30 });
    tl.to(h, { fontSize: 70, duration: .6, ease: "power3.out" }, f + .05);  // bigger, but inside the safe margins
    tl.to(sf, { borderColor: "rgba(255,106,0,.95)", boxShadow: "0 0 24px rgba(255,106,0,.45)", duration: .3 }, f + .7);
  }
});
document.querySelectorAll(".agent[data-walk]").forEach((el) => {  // pixel office: walk in from the door, sit, type
  const t = N(el, "walk", 0), sx = N(el, "sx", 0), sy = N(el, "sy", 0), ty = N(el, "type", t + 1.4), d = el.dataset.desk;
  const walk = Math.max(.6, Math.min(1.3, ty - t - .2));
  gsap.set(el, { x: -110, y: 540, opacity: 0 });
  tl.to(el, { opacity: 1, duration: .15 }, t);
  tl.to(el, { x: sx, duration: walk, ease: "none" }, t);
  tl.to(el, { y: sy, duration: walk, ease: "power1.inOut" }, t);
  const bob = el.querySelector(".bob"), steps = Math.max(2, Math.round(walk / .14));
  for (let i = 0; i < steps; i++) tl.to(bob, { y: i %% 2 ? 0 : -7, duration: .07, ease: "none" }, t + i * walk / steps);
  tl.to(bob, { y: 0, duration: .05 }, t + walk);
  const tag = el.querySelector(".tagp"), bub = el.querySelector(".bub");
  tl.from(tag, { opacity: 0, y: 10, duration: .25 }, t + walk * .6);
  tl.from(bub, { opacity: 0, scale: .5, duration: .25, ease: "back.out(2)" }, ty);
  for (let i = 0; i < 6; i++) tl.to(bob, { y: i %% 2 ? 0 : -3, duration: .09, ease: "none" }, ty + .1 + i * .18);  // typing jiggle
  const gm = document.getElementById("gm" + d), mon = document.getElementById("mon" + d);
  if (gm) tl.to(gm, { opacity: 1, duration: .3 }, ty);
  if (mon) mon.querySelectorAll("i").forEach((b, i) => {
    tl.fromTo(b, { scaleX: 0 }, { scaleX: 1, duration: .22, ease: "power2.out", immediateRender: true }, ty + .1 + i * .22); });
});
const tagScene = document.querySelector(".scene.otag");
if (tagScene && D > 1) tl.to(".content", { opacity: 0, y: -18, filter: "blur(10px)", duration: .3, ease: "power2.in" }, D - .3);
document.querySelectorAll("[data-at],[data-on],[data-dim],[data-pulse]").forEach((el) => {
  const t = N(el, "at", 0), a = el.dataset.at === undefined ? "none" : (el.dataset.anim || "up");
  if (a === "none") {}
  else if (a === "up") tl.from(el, { opacity: 0, y: 40, filter: "blur(10px)", duration: .42, ease: "expo.out" }, t);
  else if (a === "pop") tl.from(el, { opacity: 0, scale: .6, duration: .35, ease: "back.out(2)" }, t);
  else if (a === "fade") tl.from(el, { opacity: 0, duration: .35 }, t);
  else if (a === "left") tl.from(el, { opacity: 0, x: -36, duration: .36, ease: "power3.out" }, t);
  else if (a === "right") tl.from(el, { opacity: 0, x: 36, duration: .36, ease: "power3.out" }, t);
  else if (a === "strike") tl.from(el, { scaleX: 0, transformOrigin: "left center", duration: .25, ease: "power2.out" }, t);
  else if (a === "stamp") tl.from(el, { opacity: 0, scale: 2.2, rotation: -16, duration: .28, ease: "power4.in" }, t);
  else if (a === "big") tl.from(el, { opacity: 0, scale: .72, filter: "blur(14px)", duration: .38, ease: "back.out(1.5)" }, t);
  else if (a === "grow") tl.from(el, { scaleY: 0, transformOrigin: "top center", duration: N(el, "dur", .45), ease: "power2.inOut" }, t);
  else if (a === "growx") tl.from(el, { scaleX: 0, transformOrigin: "left center", duration: N(el, "dur", .6), ease: "power3.out" }, t);
  else if (a === "type") tl.from(el, { clipPath: "inset(0 100%% 0 0)", duration: N(el, "dur", .9), ease: "steps(24)" }, t);
  else if (a === "shake") { tl.from(el, { opacity: 0, scale: .9, duration: .2 }, t);
    tl.to(el, { keyframes: { x: [0, -22, 18, -14, 10, -5, 0] }, duration: .5, ease: "none" }, t + .15); }
  else if (a === "draw") { const L = el.getTotalLength(); gsap.set(el, { strokeDasharray: L, strokeDashoffset: L });
    tl.to(el, { strokeDashoffset: 0, duration: N(el, "dur", 1), ease: "power1.inOut" }, t); }
  else if (a === "count") {  // stacked spans swapped with tl.set — onUpdate doesn't fire when the renderer seeks
    const end = N(el, "to", 0), suf = el.dataset.suffix || "", dur = N(el, "dur", 1.1), n = 16;
    el.textContent = ""; el.style.display = "inline-grid";
    const spans = [];
    for (let i = 0; i <= n; i++) { const p = 1 - Math.pow(1 - i / n, 2), sp = document.createElement("span");
      sp.textContent = Math.round(end * p).toLocaleString("en-US") + suf; sp.style.gridArea = "1/1";
      sp.style.opacity = i === 0 ? 1 : 0; el.appendChild(sp); spans.push(sp); }
    tl.from(el, { opacity: 0, scale: .72, filter: "blur(14px)", duration: .38, ease: "back.out(1.5)" }, t);
    for (let i = 1; i <= n; i++) { tl.set(spans[i - 1], { opacity: 0 }, t + dur * i / n); tl.set(spans[i], { opacity: 1 }, t + dur * i / n); } }
  else if (a === "drop") tl.from(el, { opacity: 0, y: -240, rotation: -7, scale: .9, duration: .6, ease: "power3.out" }, t);
  else if (a === "tagin") tl.from(el, { opacity: 0, x: -60, filter: "blur(14px)", duration: .5, ease: "expo.out" }, t);
  else if (a === "tagr") tl.from(el, { opacity: 0, x: 60, filter: "blur(14px)", duration: .5, ease: "expo.out" }, t);
  else if (a === "glass") tl.from(el, { opacity: 0, y: 34, scale: .96, filter: "blur(16px)", duration: .55, ease: "expo.out" }, t);
  else if (a === "spin") tl.to(el, { rotation: 360 * Math.max(1, Math.round(D - t)), duration: D - t, ease: "none" }, t);
  if (el.dataset.on !== undefined) { const ton = N(el, "on", 0);
    if (el.matches(".chip,.tag,.fnode,.num,.btn,.lnode,.tile,.mnode")) {  // fills with the orange gradient, dark ink text
      tl.to(el, { backgroundImage: "linear-gradient(180deg,rgba(255,154,77,1) 0%%,rgba(255,106,0,1) 100%%)", backgroundColor: "rgba(255,106,0,0)",
        borderColor: "rgba(255,106,0,0)", color: "#1A0B04", boxShadow: "0 0 34px rgba(255,106,0,.5)", duration: .3 }, ton);
      const sv = el.querySelectorAll("svg"); if (sv.length) tl.to(sv, { stroke: "#1A0B04", duration: .3 }, ton);
    } else {  // card or row becomes the "hot" card: orange edge + tint + glow
      tl.to(el, { borderColor: "#FF6A00", backgroundColor: "rgba(255,106,0,.10)", boxShadow: "0 0 50px rgba(255,106,0,.25)", duration: .3 }, ton);
      const ss = el.querySelectorAll(".s"); if (ss.length) tl.to(ss, { color: "#D9D2CC", duration: .3 }, ton);
      const nm = el.querySelectorAll(".num.off"); if (nm.length) tl.to(nm, { backgroundImage: "linear-gradient(180deg,rgba(255,154,77,1) 0%%,rgba(255,106,0,1) 100%%)",
        color: "#1A0B04", boxShadow: "0 0 22px rgba(255,106,0,.35)", duration: .3 }, ton);
    } }
  if (el.dataset.dim !== undefined) tl.to(el, { opacity: .38, duration: .3 }, N(el, "dim", 0));
  if (el.dataset.pulse !== undefined) tl.to(el, { scale: 1.06, duration: .18, yoyo: true, repeat: 1, ease: "power1.inOut" }, N(el, "pulse", 0));
});
const pk = document.querySelector("[data-pickat]"), pe = document.querySelector("[data-pick]");
if (pk && pe) { const t = N(pk, "pickat", 0);
  tl.to(pe, { borderColor: "#FF6A00", backgroundColor: "rgba(255,106,0,.10)", duration: .25 }, t);
  tl.to(pe.querySelector(".rd"), { borderColor: "#FF6A00", backgroundColor: "#FF6A00", boxShadow: "inset 0 0 0 7px #1D1513", duration: .25 }, t);
  document.querySelectorAll(".opt:not([data-pick])").forEach((o) => tl.to(o, { opacity: .4, duration: .25 }, t)); }
document.querySelectorAll("[data-lk]").forEach((el) => {
  const t = N(el, "lk", 0), k = el.dataset.kind;
  if (k === "xl" || k === "sc" || k === "tag" || k === "pl")  // keyword / script / tag pop in on their word
    tl.from(el, { opacity: 0, scale: .72, filter: "blur(14px)", duration: .38, ease: "back.out(1.5)" }, t);
  else {  // the rest of the lockup is there from the start, dim, and turns white on its word
    tl.from(el, { opacity: 0, duration: .16 }, 0);
    tl.fromTo(el, { color: "#8C837C" }, { color: "#ffffff", duration: .12 }, t);
  }
});
if (document.querySelector(".lockup")) tl.to(".content", { opacity: 0, y: -14, filter: "blur(6px)", duration: .18, ease: "power2.in" }, Math.max(0, D - .18));
%(more)s
window.__timelines = window.__timelines || {};
window.__timelines["%(sid)s"] = tl;
tl.seek(0);
"""


def esc(s):
    return html.escape(str(s), quote=True)


def rich(s):
    """*word* → orange highlight; everything else escaped."""
    return re.sub(r"\*(.+?)\*", r'<span class="hl">\1</span>', esc(s))


def icon(name, cls="ico"):
    return f'<div class="{cls}"><svg viewBox="0 0 24 24">{ICONS[name]}</svg></div>' if name else ""


# ----------------------------------------------------------------- timing
class Timeline:
    def __init__(self, wd, dec):
        words = json.loads((wd / "transcript.json").read_text())["words"]
        edl = json.loads((wd / "edl.json").read_text())
        fixes = dec.get("fixes", {})
        self.seq = []  # (norm word, out_start, out_end)
        for k, s, e in edl["words_out"]:
            for part in vedit.fixed_text(words, fixes, k).split():
                n = vedit.norm(part)
                if n:
                    self.seq.append((n, s, e))
        self.dur = edl["new_dur"]

    def find(self, phrase, after=0.0, end=False, soft=False):
        q = [vedit.norm(x) for x in phrase.split() if vedit.norm(x)]
        for i in range(len(self.seq) - len(q) + 1):
            if self.seq[i][1] + 1e-3 >= after and [x[0] for x in self.seq[i:i + len(q)]] == q:
                return self.seq[i + len(q) - 1][2] if end else self.seq[i][1]
        if soft:
            return None
        raise LookupError(f"phrase not found after {vedit.tc(after)}: “{phrase}”")


# ----------------------------------------------------------------- templates
def at(v):
    return f' data-at="{v:.2f}"' if v is not None else ""


def tpl_list(sc, T):
    small, sep = sc.get("small"), sc.get("separate")
    rows = []
    for it in sc["items"]:
        cls = ("row card sm" if small else "row card") if sep else ("row sm" if small else "row")
        extra = ""
        if it.get("on") is not None:
            extra += f' data-on="{T(it["on"]):.2f}"'
        state = it.get("state")
        ic = icon(it.get("icon"), "ico bad" if state == "x" else "ico ghost" if state == "ghost" else "ico") \
            if it.get("icon") else (f'<div class="num">{esc(it["num"])}</div>' if it.get("num") else "")
        strike = f'<div class="strike" data-anim="strike"{at(T(it["strike"]))}></div>' if it.get("strike") else ""
        sub = f'<div class="s">{rich(it["s"])}</div>' if it.get("s") else ""
        rows.append(f'<div class="{cls}"{at(T(it.get("at")))} data-anim="{it.get("anim", "up")}"{extra}>'
                    f'{ic}<div style="flex:1"><div class="t">{rich(it["t"])}</div>{sub}</div>{right(it)}{strike}</div>')
    body = "".join(rows) if sep else f'<div class="stack"{at(T(sc["items"][0].get("at")) - .05)} data-anim="fade">{"".join(rows)}</div>'
    return body + pill(sc, T) + script(sc, T)


def right(it):
    """optional right column: "r": "Done" text or "rtag": "Billing" tag"""
    if it.get("rtag"):
        return f'<div class="tag on">{esc(it["rtag"])}</div>'
    return f'<div class="s" style="margin:0;white-space:nowrap">{esc(it["r"])}</div>' if it.get("r") else ""


def tpl_chips(sc, T):
    chips = []
    for c in sc["chips"]:
        extra = f' data-on="{T(c["on"]):.2f}"' if c.get("on") is not None else ""
        ic = f'<svg viewBox="0 0 24 24">{ICONS[c["icon"]]}</svg>' if c.get("icon") else ""
        chips.append(f'<div class="chip"{at(T(c.get("at")))} data-anim="pop"{extra}>{ic}{rich(c["t"])}</div>')
    return f'<div class="chips">{"".join(chips)}</div>' + pill(sc, T) + script(sc, T)


def tpl_pipeline(sc, T):
    steps = sc["steps"]
    rows = []
    for n, st in enumerate(steps):
        extra = f' data-on="{T(st["on"]):.2f}"' if st.get("on") is not None else ""
        lead = (f'<div class="num{"" if st.get("on") is None and not sc.get("lit") else " off"}">{n + 1}</div>'
                if not st.get("icon") else icon(st["icon"]))
        sub = f'<div class="s">{rich(st["s"])}</div>' if st.get("s") else ""
        rows.append(f'<div class="row card sm"{at(T(st.get("at")))} data-anim="left"{extra}>{lead}'
                    f'<div><div class="t">{rich(st["t"])}</div>{sub}</div></div>')
    return "".join(rows) + pill(sc, T) + script(sc, T)


def tpl_big(sc, T):
    b = sc["big"]
    px = min(330, int(950 / max(1.0, text_w(b + sc.get("suffix", ""), 900, 330, -.05) / 330)))  # fit the frame width
    if re.fullmatch(r"[\d,]+", b):
        inner = (f'<div class="big" style="font-size:{px}px" data-anim="count" data-to="{b.replace(",", "")}"'
                 f'{at(T(sc.get("big_at")))} data-suffix="{esc(sc.get("suffix", ""))}">{esc(b)}</div>')
    else:
        inner = f'<div class="big" style="font-size:{px}px"{at(T(sc.get("big_at")))} data-anim="big">{esc(b)}</div>'
    sub = f'<div class="sub"{at(T(sc.get("sub_at")))} data-anim="up">{rich(sc["sub"])}</div>' if sc.get("sub") else ""
    chips = ""
    if sc.get("chips"):
        chips = '<div class="chips" style="margin-top:26px">' + "".join(
            f'<div class="chip" style="font-size:36px;padding:14px 26px"{at(T(c.get("at")))} data-anim="pop">{esc(c["t"])}</div>'
            for c in sc["chips"]) + "</div>"
    return inner + sub + chips + script(sc, T)


def tpl_versus(sc, T):
    bad, good = sc["bad"], sc["good"]
    return (f'<div class="row card"{at(T(bad.get("at")))} data-anim="up">{icon("x", "ico bad")}'
            f'<div><div class="t">{rich(bad["t"])}</div><div class="s">{rich(bad.get("s", ""))}</div></div>'
            f'<div class="strike" data-anim="strike"{at(T(bad.get("strike", bad.get("at"))))}></div></div>'
            f'<div style="height:26px"></div>'
            f'<div class="row card"{at(T(good.get("at")))} data-anim="up" data-on="{T(good.get("at")) + .35:.2f}">'
            f'{icon("check", "ico")}<div><div class="t">{rich(good["t"])}</div>'
            f'<div class="s" style="color:#fff">{rich(good.get("s", ""))}</div></div></div>' + script(sc, T))


def tpl_statement(sc, T):
    out = []
    for ln in sc["lines"]:
        style = ln.get("style", "")
        out.append(f'<div class="title" style="{style}"{at(T(ln.get("at")))} data-anim="up">{rich(ln["t"])}</div>')
    return "".join(out) + script(sc, T)


def tpl_loading(sc, T):
    a, b = sc["tutorial"], sc["mine"]
    for v in (a.get("at"), a.get("check"), b.get("at")):
        T(v)
    return (f'<div class="card" style="padding:34px"{at(T(a.get("at")))} data-anim="up">'
            f'<div style="display:flex;align-items:center;gap:24px;margin-bottom:26px">{icon("play")}'
            f'<div><div class="t">{rich(a["t"])}</div><div class="s">{rich(a["s"])}</div></div></div>'
            f'<div class="bar"><i data-anim="growx" data-dur="{max(1.0, T(b.get("at")) - T(a.get("at")) - .3):.2f}"'
            f'{at(T(a.get("at")) + .3)}></i></div>'
            f'<div class="s" style="margin-top:18px;color:#fff"{at(T(a.get("check")))} data-anim="fade">✓ {rich(a["check_t"])}</div></div>'
            f'<div style="height:30px"></div>'
            f'<div class="card" style="padding:34px;display:flex;align-items:center;gap:28px"{at(T(b.get("at")))} data-anim="up">'
            f'<div class="spin" data-anim="spin"{at(T(b.get("at")))}></div>'
            f'<div><div class="t">{rich(b["t"])}</div><div class="s">{rich(b["s"])}</div></div></div>' + script(sc, T))


def tpl_error(sc, T):
    body = tpl_chips(dict(sc, script=None, pill=None), T)
    t = sc["toast"]
    toast = (f'<div style="height:34px"></div><div class="toast"{at(T(t.get("at")))} data-anim="shake">'
             f'{icon("alert")}<div><div class="t" style="font-size:40px">{rich(t["t"])}</div>'
             f'<div class="s mono" style="color:var(--o2)">{esc(t["s"])}</div></div></div>')
    code = ""
    if sc.get("code"):
        c = sc["code"]
        code = (f'<div style="height:24px"></div><div class="card mono" style="padding:26px 32px;font-size:34px;color:var(--o2)"'
                f'{at(T(c.get("at")))} data-anim="type">{esc(c["t"])}</div>')
    return body + toast + code + script(sc, T)


def tpl_chat(sc, T):
    out = []
    for m in sc["messages"]:
        who = m.get("who", "them")
        if m.get("meta"):
            out.append(f'<div class="meta" style="{"text-align:right" if who == "me" else ""}"'
                       f'{at(T(m.get("at")))} data-anim="fade">{esc(m["meta"])}</div>')
        out.append(f'<div class="bubble {who}"{at(T(m.get("at")))} data-anim="{"right" if who == "me" else "left"}">'
                   f'{rich(m["t"])}</div>')
    if sc.get("verdict"):
        v = sc["verdict"]
        out.append(f'<div class="toast" style="margin-top:20px"{at(T(v.get("at")))} data-anim="shake">{icon("x")}'
                   f'<div class="t" style="font-size:40px">{rich(v["t"])}</div></div>')
    return "".join(out) + script(sc, T)


def tpl_email(sc, T):
    e = sc["email"]
    for v in [e.get("read"), sc.get("labels_at")] + [l.get("at") for l in sc["labels"]] + \
            [l.get("on") for l in sc["labels"]] + [sc["draft"].get("at"), sc["nosend"].get("at")]:
        T(v)
    labels = "".join(
        f'<div class="chip" style="font-size:34px;padding:18px 26px"{at(T(l.get("at")))} data-anim="pop"'
        f'{" data-on=%s" % chr(34) + format(T(l["on"]), ".2f") + chr(34) if l.get("on") is not None else ""}>'
        f'{esc(l["t"])}</div>' for l in sc["labels"])
    d = sc["draft"]
    return (f'<div class="card" style="padding:34px"{at(T(e.get("at")))} data-anim="up">'
            f'<div style="display:flex;align-items:center;gap:22px;margin-bottom:20px">{icon("mail")}'
            f'<div><div class="t" style="font-size:40px">{esc(e["from"])}</div><div class="s">{esc(e["addr"])}</div></div>'
            f'<div class="chip" style="margin-left:auto;font-size:26px;padding:10px 20px">New</div></div>'
            f'<div class="t" style="font-size:44px;margin-bottom:10px">{esc(e["subject"])}</div>'
            f'<div class="s" style="font-size:32px;line-height:1.35">{esc(e["body"])}</div>'
            f'<div class="bar" style="margin-top:24px"><i data-anim="growx" data-dur="1.4"{at(T(e.get("read")))}></i></div>'
            f'<div class="s" style="margin-top:12px;color:var(--o);font-weight:700"{at(T(e.get("read")))} data-anim="fade">'
            f'AI is reading…</div></div>'
            f'<div style="height:28px"></div><div class="kicker" style="font-size:24px"{at(T(sc.get("labels_at")))}'
            f' data-anim="fade">AI DECIDES</div><div class="chips">{labels}</div>'
            f'<div style="height:28px"></div><div class="card" style="padding:28px 32px;display:flex;align-items:center;gap:22px"'
            f'{at(T(d.get("at")))} data-anim="up">{icon("pen")}<div style="flex:1"><div class="t" style="font-size:38px">Draft reply</div>'
            f'<div class="s" data-anim="type" data-dur="1.4"{at(T(d.get("at")) + .3)}>{esc(d["t"])}</div></div></div>'
            f'<div class="toast" style="margin-top:22px"{at(T(sc["nosend"].get("at")))} data-anim="shake">{icon("x")}'
            f'<div class="t" style="font-size:38px">{rich(sc["nosend"]["t"])}</div></div>')


def tpl_map(sc, T):
    a, b, c, d = (T(sc[k]) for k in ("route_at", "dest_at", "change_at", "lost_at"))
    return (f'<svg viewBox="0 0 928 900" width="928" height="900" style="display:block">'
            f'<defs><pattern id="g" width="58" height="58" patternUnits="userSpaceOnUse">'
            f'<path d="M58 0H0V58" fill="none" stroke="rgba(255,255,255,.06)" stroke-width="2"/></pattern></defs>'
            f'<rect width="928" height="900" rx="34" fill="rgba(255,255,255,.035)" stroke="rgba(255,255,255,.1)" stroke-width="2"/>'
            f'<rect width="928" height="900" rx="34" fill="url(#g)"/>'
            f'<path d="M140 780 C 140 600, 420 640, 430 470 S 760 300, 780 140" fill="none" stroke="#FF6A00" '
            f'stroke-width="18" stroke-linecap="round" data-anim="draw" data-dur="1.4"{at(a)}/>'
            f'<path d="M430 470 C 300 380, 520 220, 780 140" fill="none" stroke="#8C837C" stroke-width="12" '
            f'stroke-dasharray="1 26" stroke-linecap="round" data-anim="fade"{at(c + .4)}/>'
            f'<g data-anim="pop"{at(a)}><circle cx="140" cy="780" r="30" fill="#fff"/><circle cx="140" cy="780" r="14" fill="#FF6A00"/></g>'
            f'<g data-anim="pop"{at(b)}><circle cx="780" cy="140" r="40" fill="#FF6A00"/>'
            f'<path d="M766 140l10 10 20-22" stroke="#fff" stroke-width="7" fill="none" stroke-linecap="round"/></g>'
            f'<g data-anim="shake"{at(c)}><circle cx="600" cy="390" r="52" fill="#C24700"/>'
            f'<path d="M580 370l40 40M620 370l-40 40" stroke="#fff" stroke-width="10" stroke-linecap="round"/></g>'
            f'</svg>'
            f'<div style="display:flex;gap:18px;margin-top:30px">'
            f'<div class="chip" style="font-size:38px;padding:20px 28px;white-space:nowrap"{at(b)} data-anim="pop"><svg viewBox="0 0 24 24">{ICONS["flag"]}</svg>Same destination ✓</div>'
            f'<div class="chip" style="font-size:38px;padding:20px 28px;white-space:nowrap;border-color:rgba(255,106,0,.6);background:rgba(255,106,0,.10)"{at(c)} data-anim="pop">'
            f'Nagbago ang daan</div></div>'
            f'<div class="script" style="margin-top:30px"{at(d)} data-anim="up">{esc(sc["lost_t"])}</div>')


def tpl_excel(sc, T):
    for v in [t["at"] for t in sc["tools"]] + [sc["excel_at"], sc["tabs_at"], sc["final_at"]]:
        T(v)
    tools = "".join(f'<div class="chip"{at(T(t["at"]))} data-anim="pop">{esc(t["t"])}</div>' for t in sc["tools"])
    tabs = ["Sheet1", "Leads", "OLD", "…"]
    tab_html = "".join(f'<div style="padding:16px 22px;border-radius:14px 14px 0 0;background:rgba(255,255,255,.06);'
                       f'font-size:28px;font-weight:600;color:var(--mut);white-space:nowrap">{t}</div>' for t in tabs)
    fin = (f'<div style="padding:16px 22px;border-radius:14px 14px 0 0;background:rgba(255,255,255,.06);font-size:28px;'
           f'font-weight:800;white-space:nowrap"{at(T(sc["final_at"]))} data-anim="pop" data-on="{T(sc["final_at"]) + .3:.2f}">'
           f'FINAL final (2)</div>')
    return (f'<div class="chips">{tools}</div><div style="height:46px"></div>'
            f'<div class="card" style="padding:34px"{at(T(sc["excel_at"]))} data-anim="up">'
            f'<div style="display:flex;align-items:center;gap:22px;margin-bottom:26px">{icon("table")}'
            f'<div class="t">Client_Data.xlsx</div></div>'
            f'<div style="height:300px;border-radius:16px;background:repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 2px,'
            f'transparent 2px 60px),repeating-linear-gradient(90deg,rgba(255,255,255,.05) 0 2px,transparent 2px 150px)"></div>'
            f'<div style="display:flex;gap:8px;margin-top:18px;overflow:hidden">{tab_html}{fin}</div></div>'
            f'<div style="display:flex;align-items:baseline;gap:20px;margin-top:34px"{at(T(sc["tabs_at"]))} data-anim="up">'
            f'<div class="big" style="font-size:200px" data-anim="count" data-to="47"{at(T(sc["tabs_at"]))}>47</div>'
            f'<div class="sub">tabs 😵</div></div>')


def tpl_notify(sc, T):
    out = []
    for n in sc["notes"]:
        out.append(f'<div class="card" style="padding:26px 30px;display:flex;align-items:center;gap:24px;margin-bottom:20px"'
                   f'{at(T(n["at"]))} data-anim="up">{icon(n.get("icon", "send"))}<div style="flex:1">'
                   f'<div class="s" style="margin:0 0 4px;font-weight:700">{esc(n.get("app", "AI Agent"))} · now</div>'
                   f'<div class="t" style="font-size:40px">{rich(n["t"])}</div></div></div>')
    return "".join(out) + script(sc, T)


def tpl_cta(sc, T):
    if sc.get("layout") == "lower":  # compact version that sits under the face
        return (f'<div style="display:flex;align-items:center;gap:22px;margin-bottom:22px">'
                f'<div class="title" style="font-size:72px;margin:0;text-shadow:0 3px 14px rgba(0,0,0,.8)"{at(T(sc.get("at")))} data-anim="up">Comment</div>'
                f'<div class="pill" style="font-size:66px;padding:18px 40px;margin:0"{at(T(sc.get("word_at")))} '
                f'data-anim="pop" data-pulse="{T(sc.get("word_at")) + .9:.2f}">{esc(sc["word"])}</div></div>'
                f'<div class="row card sm"{at(T(sc.get("part2_at")))} data-anim="up">{icon("play")}'
                f'<div><div class="t">{rich(sc["part2"])}</div><div class="s">{rich(sc["part2_s"])}</div></div></div>'
                f'<div class="row card sm"{at(T(sc.get("follow_at")))} data-anim="up">{icon("user")}'
                f'<div><div class="t">{rich(sc["follow"])}</div><div class="s">{rich(sc["follow_s"])}</div></div></div>')
    return (f'<div class="title" style="font-size:96px;margin-bottom:20px"{at(T(sc.get("at")))} data-anim="up">Comment</div>'
            f'<div class="pill" style="font-size:120px;padding:34px 70px;margin:0 0 50px"{at(T(sc.get("word_at")))} '
            f'data-anim="pop" data-pulse="{T(sc.get("word_at")) + .9:.2f}">{esc(sc["word"])}</div>'
            f'<div class="row card"{at(T(sc.get("part2_at")))} data-anim="up">{icon("play")}'
            f'<div><div class="t">{rich(sc["part2"])}</div><div class="s">{rich(sc["part2_s"])}</div></div></div>'
            f'<div class="row card"{at(T(sc.get("follow_at")))} data-anim="up">{icon("user")}'
            f'<div><div class="t">{rich(sc["follow"])}</div><div class="s">{rich(sc["follow_s"])}</div></div></div>')


def tpl_meter(sc, T):
    """Confidence bars: rows[{t, v (0-100), at, hot}], verdict{t, at} → orange pill under the card."""
    rows = []
    for r in sc["rows"]:
        hot = r.get("hot")
        rows.append(f'<div class="meter{" hot" if hot else ""}"{at(T(r.get("at")))} data-anim="left">'
                    f'<div class="t">{esc(r["t"])}</div><div class="bar{"" if hot else " off"}">'
                    f'<i style="width:{max(3, r["v"])}%%" data-anim="growx" data-dur=".7"{at(T(r.get("at")) + .1)}></i></div>'
                    f'<div class="pc">{r["v"]}%%</div></div>'.replace("%%", "%"))
    v = sc.get("verdict")
    verdict = (f'<div class="pill" style="align-self:center;margin-top:34px"{at(T(v.get("at")))} data-anim="pop">'
               f'<svg viewBox="0 0 24 24">{ICONS[v.get("icon", "check")]}</svg>{rich(v["t"])}</div>') if v else ""
    pre = ""
    if sc.get("before"):  # struck-out old way above the card ("Generate long text")
        b = sc["before"]
        pre = (f'<div class="chip no" style="align-self:flex-start;position:relative;margin-bottom:30px;font-size:40px"'
               f'{at(T(b.get("at")))} data-anim="pop">{esc(b["t"])}<div class="strike" data-anim="strike"'
               f'{at(T(b.get("strike", b.get("at"))) + .3)}></div></div>')
    return pre + f'<div class="stack">{"".join(rows)}</div>' + verdict + script(sc, T)


def tpl_choice(sc, T):
    """Multiple choice card: q, options[...], pick (index), pick_at."""
    opts = "".join(f'<div class="opt"{" data-pick=1" if n == sc.get("pick") else ""}{at(T(o.get("at")) if isinstance(o, dict) else None)}'
                   f'{" data-anim=left" if isinstance(o, dict) and o.get("at") else ""}>'
                   f'<div class="k">{chr(65 + n)}</div><div class="t">{esc(o["t"] if isinstance(o, dict) else o)}</div>'
                   f'<div class="rd"></div></div>' for n, o in enumerate(sc["options"]))
    q = f'<div class="t" style="padding:30px 34px 10px;font-size:46px">{rich(sc["q"])}</div>' if sc.get("q") else ""
    pick = f'<div data-pickat="{T(sc["pick_at"]):.2f}"></div>' if sc.get("pick_at") else ""
    return f'<div class="stack"{at(T(sc.get("at")))} data-anim="up">{q}{opts}</div>{pick}' + script(sc, T)


def tpl_flow(sc, T):
    """Horizontal nodes Inbox → Label → Action: nodes[{t, icon, at, on}]; below: optional list card."""
    out = []
    for n, nd in enumerate(sc["nodes"]):
        if n:
            out.append(f'<div class="wire"{at(T(nd.get("at")) - .1)} data-anim="growx" data-dur=".25"></div>')
        extra = f' data-on="{T(nd["on"]):.2f}"' if nd.get("on") is not None else ""
        out.append(f'<div class="fnode{" hot" if nd.get("hot") else ""}"{at(T(nd.get("at")))} data-anim="pop"{extra}>'
                   f'<svg viewBox="0 0 24 24">{ICONS[nd.get("icon", "node")]}</svg>{esc(nd["t"])}</div>')
    below = ""
    if sc.get("items"):
        below = '<div style="height:30px"></div>' + tpl_list(dict(sc, pill=None, script=None), T)
    return f'<div class="flow">{"".join(out)}</div>' + below + pill(sc, T) + script(sc, T)


def tpl_chapter(sc, T):
    """Chapter card: step ("MONTH 1 · PART 2"), mo ("OCTOBER"), what (script)."""
    return (f'<div class="chap"><div class="step"{at(.05)} data-anim="fade">{esc(sc.get("step", ""))}</div>'
            f'<div class="mo" style="font-size:{min(168, int(860 * 168 / max(1.0, text_w(sc["mo"], 900, 168, -.045))))}px"{at(.12)} data-anim="big">{esc(sc["mo"])}</div>'
            f'<div class="what"{at(T(sc.get("what_at")) if sc.get("what_at") else .4)} data-anim="up">{esc(sc.get("what", ""))}</div></div>')


def tpl_mindmap(sc, T):
    """Orange core + nodes around it with lines that draw in: core, core_at, nodes[{t, icon, at}] (≤6)."""
    import math
    W, H, RX, RY = 984, 1000, 320, 390
    nodes = sc["nodes"]
    pos = [(min(W - 170, max(170, W / 2 + RX * math.cos(math.radians(-90 + 360 * k / len(nodes))))),
            H / 2 + RY * math.sin(math.radians(-90 + 360 * k / len(nodes)))) for k in range(len(nodes))]
    lines = "".join(f'<path d="M{W / 2:.0f} {H / 2:.0f} L{x:.0f} {y:.0f}" stroke="rgba(255,140,60,.45)" stroke-width="3" '
                    f'fill="none" data-anim="draw" data-dur=".35"{at(T(n.get("at")))}/>' for (x, y), n in zip(pos, nodes))
    out = [f'<svg class="lines" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{lines}</svg>',
           f'<div class="mcore"{at(T(sc.get("core_at")))} data-anim="pop">{rich(sc["core"])}</div>']
    for (x, y), n in zip(pos, nodes):
        out.append(f'<div class="mnode" style="left:{x:.0f}px;top:{y:.0f}px"{at(T(n.get("at")) + .15)} data-anim="pop"'
                   f'{" data-on=%s%.2f%s" % (chr(34), T(n["on"]), chr(34)) if n.get("on") is not None else ""}>'
                   f'{icon(n.get("icon", "question"))}<span>{rich(n["t"])}</span></div>')
    return f'<div class="mm">{"".join(out)}</div>' + script(sc, T)


def tpl_loop(sc, T):
    """Agent loop: steps[{t, at, on}] around a circle whose arc fills; core label in the middle."""
    import math
    S, R = 860, 330
    steps = sc["steps"]
    circ = 2 * math.pi * R
    arc = (f'<circle cx="{S / 2}" cy="{S / 2}" r="{R}" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="10"/>'
           f'<circle cx="{S / 2}" cy="{S / 2}" r="{R}" fill="none" stroke="#FF6A00" stroke-width="10" stroke-linecap="round" '
           f'transform="rotate(-90 {S / 2} {S / 2})" style="filter:drop-shadow(0 0 10px rgba(255,106,0,.6))" '
           f'data-anim="draw" data-dur="{max(1.0, T(steps[-1].get("at")) - T(steps[0].get("at")) + .6):.2f}"{at(T(steps[0].get("at")))}/>')
    out = [f'<svg viewBox="0 0 {S} {S}" width="{S}" height="{S}">{arc}</svg>']
    for k, st in enumerate(steps):
        a = math.radians(-90 + 360 * k / len(steps))
        x, y = S / 2 + R * math.cos(a), S / 2 + R * math.sin(a)
        out.append(f'<div class="lnode" style="left:{x:.0f}px;top:{y:.0f}px"{at(T(st.get("at")))} data-anim="pop"'
                   f' data-on="{T(st.get("on", st.get("at"))) + .05:.2f}">{esc(st["t"])}</div>')
    if sc.get("core"):
        out.append(f'<div class="lcore"{at(T(sc.get("core_at")))} data-anim="fade">{rich(sc["core"])}</div>')
    return f'<div class="lp">{"".join(out)}</div>' + script(sc, T)


def tpl_tiles(sc, T):
    """2×2 label tiles: tiles[{t, icon, at, on}], optional button{t, at} (full-width orange)."""
    tiles = "".join(f'<div class="tile"{at(T(t.get("at")))} data-anim="pop"'
                    f'{" data-on=%s%.2f%s" % (chr(34), T(t["on"]), chr(34)) if t.get("on") is not None else ""}>'
                    f'{icon(t.get("icon", "question"))}{esc(t["t"])}</div>' for t in sc["tiles"])
    b = sc.get("button")
    btn = (f'<div class="pill wide" style="margin-top:22px"{at(T(b.get("at")))} data-anim="pop">'
           f'<svg viewBox="0 0 24 24">{ICONS[b.get("icon", "shield")]}</svg>{rich(b["t"])}</div>') if b else ""
    return f'<div class="tiles">{tiles}</div>' + btn + script(sc, T)


def tpl_approval(sc, T):
    """Approval card: head, tag, line, right, reject/approve buttons; approve_at lights Approve; note pill."""
    go = T(sc.get("approve_at")) if sc.get("approve_at") else None
    note = sc.get("note")
    return (f'<div class="stack appr"{at(T(sc.get("at")))} data-anim="up">'
            f'<div class="hd">{icon(sc.get("icon", "user"))}<div class="t" style="flex:1;font-size:42px">{esc(sc.get("head", "Needs your approval"))}</div>'
            f'<div class="tag">{esc(sc.get("tag", "sensitive"))}</div></div>'
            f'<div class="ln"{at(T(sc.get("line_at")) if sc.get("line_at") else None)} data-anim="fade"><span>{rich(sc["line"])}</span>'
            f'<span class="s" style="margin:0">{esc(sc.get("right", "AI drafted"))}</span></div>'
            f'<div class="btns"{at(T(sc.get("buttons_at")) if sc.get("buttons_at") else None)} data-anim="up">'
            f'<div class="btn">{esc(sc.get("reject", "Reject"))}</div>'
            f'<div class="btn go"{" data-on=%s%.2f%s" % (chr(34), go, chr(34)) if go is not None else ""}>{esc(sc.get("approve", "Approve"))}</div></div></div>'
            + (f'<div class="pill" style="align-self:center;font-size:40px;padding:18px 34px"{at(T(note.get("at")))} data-anim="pop">'
               f'{rich(note["t"])}</div>' if note else "") + script(sc, T))


LK = {"md": (800, 70, -.015), "xl": (900, 150, -.045), "sc": ("GreatVibes", 118, 0), "sm": (700, 40, 0),
      "tag": (800, 46, 0), "pl": (700, 30, 0)}  # kind → (font, px, tracking em)
_fonts = {}


def text_w(text, font, px, track=0.0):
    """Width in px of text set in one of the bundled fonts (so lockup rows can be fitted before render)."""
    font = brandkit.measure_file(LOOK_DEC, font) if LOOK_DEC.get("look") else font
    if font not in _fonts:
        from fontTools.ttLib import TTFont
        f = TTFont(MOTION / "fonts" / (f"{font}.ttf" if isinstance(font, str) else f"InterTight-wght-{font}.ttf"))
        _fonts[font] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    cmap, hm, upm = _fonts[font]
    return sum(hm.get(cmap.get(ord(c), ".notdef"), (upm // 2, 0))[0] for c in text) * px / upm + len(text) * track * px


def fit_row(items, width=860, gap=22):
    """items: [(kind, text, size_override)] → font sizes so the row fits the lockup width.
    Long keywords shrink first (down to 110px, as the design system says), then the whole row scales."""
    def w(kind, text, px):
        f, _, tr = LK[kind]
        if kind == "sm":
            return max(text_w(ln, f, px, tr) for ln in text.split("/"))
        return text_w(text, f, px, tr) + (60 if kind in ("tag", "pl") else 16 if kind == "sc" else 0)
    sizes = [sz or LK[k][1] for k, _, sz in items]
    total = lambda: sum(w(k, t, px) for (k, t, _), px in zip(items, sizes)) + gap * (len(items) - 1)
    while total() > width and any(k == "xl" and px > 110 for (k, _, _), px in zip(items, sizes)):
        sizes = [px - 4 if k == "xl" and px > 110 else px for (k, _, _), px in zip(items, sizes)]
    if total() > width:
        f = width / total()
        sizes = [px * f for px in sizes]
    return [round(px) for px in sizes]


def tpl_lockup(sc, T):
    """Kinetic lockup over the face (hook / key claim / CTA). rows: list of rows, each a list of tokens:
    "word" medium · "X:word" keyword (orange, 150px; "X120:word" sets the size) · "C:word" script ·
    "S:line one/line two" small stacked lines · "G:text" orange pill (+ Follow) · "P:text" small dark pill ·
    "<" first token = align row left.
    A row is a list of tokens, or a string split on spaces ("That X:confidence" / "S:score/is C:important").
    Each token appears on its own words; add "@phrase" to time it on other words ("X:AI@artificial")."""
    rows = []
    T0 = T  # "@0.2" = seconds into the scene (Studio hooks: the first word can sit before the scene's chaining floor)

    def T(v):  # noqa: F811
        return float(v) if isinstance(v, str) and re.fullmatch(r"\d+(\.\d+)?", v) else T0(v)
    for row in sc["rows"]:
        toks = row.split() if isinstance(row, str) else list(row)  # list form allows spaces inside a token
        left = bool(toks) and toks[0] == "<"
        items = []
        for tok in toks[1:] if left else toks:
            kind, _, text = tok.partition(":") if re.match(r"^(X\d*|C|S|G|P|M):", tok) else ("M", "", tok)
            text, _, when = text.partition("@")
            text = text.replace("_", " ")  # "M:sa_inyo" → one token in the string form
            size = int(kind[1:]) if kind.startswith("X") and kind[1:] else None
            kind = {"M": "md", "C": "sc", "S": "sm", "G": "tag", "P": "pl"}.get(kind, "xl" if kind.startswith("X") else kind)
            items.append((kind, text, size, when))
        sizes = fit_row([(k, t, sz) for k, t, sz, _ in items])
        out = []
        for (kind, text, _, when), px in zip(items, sizes):
            if kind == "sm":
                spans = "".join(f'<div class="lk sm" style="font-size:{px}px" data-lk="{T(when or ln):.2f}" '
                                f'data-kind="sm">{esc(ln)}</div>' for ln in text.split("/"))
                out.append(f'<div class="lk-stack{" l" if left else ""}">{spans}</div>')
            else:
                out.append(f'<div class="lk {kind}" style="font-size:{px}px" data-lk="{T(when or text):.2f}" '
                           f'data-kind="{kind}">{esc(text)}</div>')
        rows.append(f'<div class="lk-row{" l" if left else ""}">{"".join(out)}</div>')
    return "".join(rows)


def pill(sc, T):
    p = sc.get("pill")
    if not p:
        return ""
    return f'<div class="pill"{at(T(p.get("at")))} data-anim="pop">{icon(p.get("icon"), "") if False else ""}' \
           f'{"<svg viewBox=%s0 0 24 24%s>%s</svg>" % (chr(34), chr(34), ICONS[p["icon"]]) if p.get("icon") else ""}' \
           f'{rich(p["t"])}</div>'


def script(sc, T):
    s = sc.get("script")
    if not s:
        return ""
    return f'<div class="script" style="margin-top:34px"{at(T(s.get("at")))} data-anim="up">{esc(s["t"])}</div>'


def tpl_terminal(sc, T):
    """Claude Code-style terminal: lines[{k: prompt|out|ok|code|dim, t, at}], optional swatches[{c, t, at}]."""
    first = T(sc["lines"][0].get("at"))
    rows = []
    for ln in sc["lines"]:
        k, t, a = ln.get("k", "out"), ln["t"], T(ln.get("at"))
        if k == "prompt":
            dur = min(1.8, max(.5, len(t) * .032))
            rows.append(f'<div class="tl"{at(a)} data-anim="fade"><span class="p">› </span><span data-anim="type" data-dur="{dur:.2f}"'
                        f'{at(a)}>{rich(t)}</span><span class="caret" data-anim="fade"{at(a + dur)}></span></div>')
        elif k == "code":
            rows.append(f'<div class="tl dim"{at(a)} data-anim="type" data-dur="{min(1.4, max(.4, len(t) * .025)):.2f}">{rich(t)}</div>')
        else:
            mark = {"out": "⏺", "ok": "✓", "dim": " "}.get(k, "⏺")
            rows.append(f'<div class="tl {"ok" if k == "ok" else "dim" if k == "dim" else ""}"{at(a)} data-anim="left">'
                        f'<span class="p">{mark} </span>{rich(t)}</div>')
    tabs = ""
    if sc.get("tabs"):  # app tab bar ("Chat · Cowork · Code"), tab_on lights on tab_at
        ta = T(sc.get("tab_at")) if sc.get("tab_at") else None
        tabs = '<div style="display:flex;gap:12px;padding:18px 28px 0">' + "".join(
            f'<div class="chip" style="font-size:30px;padding:12px 26px"'
            f'{" data-on=%s%.2f%s" % (chr(34), ta, chr(34)) if n == sc.get("tab_on") and ta is not None else ""}>{esc(t)}</div>'
            for n, t in enumerate(sc["tabs"])) + "</div>"
    win = (f'<div class="win card"{at(first - .05)} data-anim="glass"><div class="bar2"><span class="dot"></span>'
           f'<span class="dot"></span><span class="dot"></span><span class="wt">{esc(sc.get("wtitle", "claude — ~/promo"))}</span></div>'
           f'{tabs}<div class="wb">{"".join(rows)}</div></div>')
    sw = ""
    if sc.get("swatches"):
        sw = '<div class="chips" style="margin-top:28px">' + "".join(
            f'<div class="sw gpane"{at(T(x.get("at")))} data-anim="pop"><i style="background:{x["c"]}"></i>{esc(x["t"])}</div>'
            for x in sc["swatches"]) + "</div>"
    return win + sw + pill(sc, T) + script(sc, T)


def tpl_phone(sc, T):
    """Phone preview/storyboard: headline, items[{t, icon, at}] joined by an orange wire, name (script), cta pill,
    controls (play + scrubber), button{t, icon, at} under the phone."""
    a0 = T(sc.get("at"))
    inner = '<div class="notch"></div>'
    if sc.get("video"):  # a real clip playing in the phone (our own videos)
        inner = media(sc["video"], 0, sc.get("_dur", 6), sc.get("offset", 0)) + inner
    if sc.get("headline"):
        inner += f'<div class="hl2"{at(T(sc.get("headline_at")))} data-anim="up">{rich(sc["headline"])}</div>'
    for n, it in enumerate(sc.get("items", [])):
        ta = T(it.get("at"))
        if n:
            inner += f'<div style="width:4px;height:20px;margin:-8px 0 -8px 74px;background:var(--o);box-shadow:0 0 10px var(--glow)" data-anim="grow" data-dur=".3"{at(ta - .05)}></div>'
        extra = f' data-on="{T(it["on"]):.2f}"' if it.get("on") is not None else ""
        inner += f'<div class="mini"{at(ta)} data-anim="left"{extra}>{icon(it.get("icon", "spark"))}{rich(it["t"])}</div>'
    if sc.get("name"):
        inner += f'<div class="nm" style="margin-top:auto"{at(T(sc.get("name_at")))} data-anim="up">{esc(sc["name"])}</div>'
    if sc.get("cta"):
        inner += (f'<div class="cta2"{" style=%smargin-top:10px%s" % (chr(34), chr(34)) if sc.get("name") else ""}'
                  f'{at(T(sc.get("cta_at")))} data-anim="pop">{esc(sc["cta"])}</div>')
    out = f'<div class="phone{" media" if sc.get("video") else ""}"{at(a0)} data-anim="glass"><div class="scr">{inner}</div></div>'
    if sc.get("controls"):
        c0 = T(sc.get("controls_at")) if sc.get("controls_at") else a0 + .3
        out += (f'<div class="ctl"{at(c0)} data-anim="up"><div class="pb"><svg viewBox="0 0 24 24"><polygon points="6 3 21 12 6 21"/></svg></div>'
                f'<div class="bar"><i data-anim="growx" data-dur="{max(1.0, sc.get("_dur", 6) - c0 - .4):.2f}"{at(c0 + .2)}></i></div>'
                f'<div class="tc">{esc(sc.get("tc", "0:15"))}</div></div>')
    if sc.get("button"):
        b = sc["button"]
        out += (f'<div style="display:flex;justify-content:center"><div class="pill"{at(T(b.get("at")))} data-anim="pop">'
                f'{"<svg viewBox=%s0 0 24 24%s>%s</svg>" % (chr(34), chr(34), ICONS[b["icon"]]) if b.get("icon") else ""}{rich(b["t"])}</div></div>')
    return out


def tpl_export(sc, T):
    """Render progress → file: file, s, done_at, file_at, (bar fills from at to done_at; % counts up)."""
    a, d, f = T(sc.get("at")), T(sc.get("done_at")), T(sc.get("file_at"))
    dur = max(.8, d - a - .2)
    return (f'<div class="card" style="padding:38px"{at(a)} data-anim="glass">'
            f'<div style="display:flex;align-items:center;gap:24px;margin-bottom:30px">{icon("film")}'
            f'<div><div class="t">{esc(sc.get("label", "Rendering…"))}</div><div class="s mono">{esc(sc["file"])}</div></div></div>'
            f'<div class="pct" data-anim="count" data-to="100" data-suffix="%" data-dur="{dur:.2f}"{at(a + .15)}>0%</div>'
            f'<div class="bar" style="margin-top:26px;height:26px;border-radius:13px"><i data-anim="growx" data-dur="{dur:.2f}"{at(a + .15)}></i></div></div>'
            f'<div style="height:30px"></div>'
            f'<div class="row card"{at(f)} data-anim="pop" data-on="{f + .3:.2f}">{icon("play")}'
            f'<div style="flex:1"><div class="t">{esc(sc["file"])}</div><div class="s">{esc(sc.get("s", "1080×1920 · MP4"))}</div></div>'
            f'<div class="tag on">✓ Ready</div></div>'
            + (f'<div style="display:flex;justify-content:center;margin-top:26px"><div class="phone media" style="width:300px;height:533px;border-radius:44px;padding:10px"'
               f'{at(f + .2)} data-anim="glass"><div class="scr" style="border-radius:35px">{media(sc["video"], f + .2, sc.get("_dur", 6), sc.get("offset", 0))}</div></div></div>'
               if sc.get("video") else "")
            + pill(sc, T) + script(sc, T))


def tpl_upload(sc, T):
    """Drop zone: label, files[{t, s, icon, at}] drop in and land as rows."""
    rows = "".join(f'<div class="row card sm" style="margin:0"{at(T(x.get("at")))} data-anim="drop">{icon(x.get("icon", "image"))}'
                   f'<div style="flex:1"><div class="t">{esc(x["t"])}</div>{"<div class=%ss%s>%s</div>" % (chr(34), chr(34), esc(x["s"])) if x.get("s") else ""}</div>'
                   f'<div class="tag on">✓</div></div>' for x in sc["files"])
    return (f'<div class="drop gpane"{at(T(sc.get("at")))} data-anim="glass"><div class="dz"><svg viewBox="0 0 24 24">{ICONS["upload"]}</svg>'
            f'{esc(sc.get("label", "I-drop dito"))}</div>{rows}</div>' + pill(sc, T) + script(sc, T))


def tpl_duo(sc, T):
    """Two app tiles joined by a plus: tiles[{t, s, icon, at, on}]."""
    a, b = sc["tiles"]
    def tile(x):
        extra = f' data-on="{T(x["on"]):.2f}"' if x.get("on") is not None else ""
        return (f'<div class="card"{at(T(x.get("at")))} data-anim="glass"{extra}>{icon(x.get("icon", "spark"))}'
                f'<div class="t">{rich(x["t"])}</div><div class="s">{rich(x.get("s", ""))}</div></div>')
    return (f'<div class="duo">{tile(a)}<div class="plus"{at(T(b.get("at")) - .1)} data-anim="pop">+</div>{tile(b)}</div>'
            + pill(sc, T) + script(sc, T))


def tpl_behind(sc, T):
    """Giant word(s) BEHIND the speaker (vedit cuts him out on top): text ("A/B" = two lines), style "" (orange) |
    "w" (white) | "o" (outline), y (top, 1920 px), size (max px), kicker (small line above)."""
    lines = sc["text"].split("/")
    y, gap = int(sc.get("y", 300)), sc.get("gap", .86)
    out, top = [], y
    a = T(sc.get("at"))
    if sc.get("kicker") and sc.get("kicker_script"):  # thumbnail hook: Great Vibes line riding on top of the big word
        kp = min(int(sc.get("kicker_size", 124)), int(900 * 124 / max(1.0, text_w(sc["kicker"], "GreatVibes", 124, 0))))
        out.append(f'<div class="bk scr" style="top:{y - round(kp * .5)}px;font-size:{kp}px" data-at="{a + .25:.2f}" data-anim="pop">{esc(sc["kicker"])}</div>')
    elif sc.get("kicker") and sc.get("kicker_big"):  # thumbnail hook: big white line above the head, word behind it
        kp = min(int(sc.get("kicker_size", 96)), int(940 * 96 / max(1.0, text_w(sc["kicker"].upper(), 900, 96, -.025))))
        out.append(f'<div class="bk big" style="top:{y - round(kp * 1.02)}px;font-size:{kp}px" data-at="{a:.2f}" data-anim="pop">{esc(sc["kicker"])}</div>')
    elif sc.get("kicker"):
        out.append(f'<div class="bk" style="top:{y - 74}px" data-at="{a:.2f}" data-anim="fade">{esc(sc["kicker"])}</div>')
    for n, ln in enumerate(lines):
        px = min(int(sc.get("size", 340)), int(960 * 340 / max(1.0, text_w(ln.upper(), 900, 340, -.045))))
        spans = "".join(f"<span>{esc(ch) if ch != ' ' else '&nbsp;'}</span>" for ch in ln)
        when = T(sc["lines_at"][n]) if sc.get("lines_at") else a + n * .25
        out.append(f'<div class="bt {sc.get("style", "")}" style="top:{top}px;font-size:{px}px" data-bt="{when:.2f}">{spans}</div>')
        top += round(px * gap)
    return "".join(out)

SPRITE = ["..hhhh..", ".hhhhhh.", ".hssssh.", ".ssesse.", "..ssss..", ".bbbbbb.", "bbbbbbbb", "s.bbbb.s", "..l..l..", "..l..l.."]


def sprite(body):
    cols = {"h": "#2B1A10", "s": "#E8B48A", "e": "#1A0B04", "b": body, "l": "#3A2A22"}
    sh = ",".join(f"{x * 12}px {y * 12}px 0 {cols[c]}" for y, row in enumerate(SPRITE) for x, c in enumerate(row) if c != ".")
    return f'<div class="spr" style="box-shadow:{sh}"></div>'


def tpl_office(sc, T):
    """Pixel Agents office: agents[{name, color, desk, at (walks in), type_at (starts typing), task (bubble)}],
    desks (count, ≤6), live (badge), wtitle. Agents walk from the door to their desk, sit, and type."""
    nd = int(sc.get("desks", 3))
    pos = [(36 + (k % 3) * 296, 230 if k < 3 else 470) for k in range(nd)]
    a0 = T(sc.get("at"))
    floor = '<div class="wall"></div>' + "".join(f'<div class="win2" style="left:{80 + k * 300}px"></div>' for k in range(3))
    floor += '<div class="plant" style="left:20px;top:150px"></div><div class="plant" style="right:24px;top:400px"></div>'
    agents_html, js = "", []
    for k, (x, y) in enumerate(pos):
        bars = "".join(f'<i style="width:{50 + (k * 13 + j * 17) % 40}px"></i>' for j in range(5))  # code lines (typed by the runtime)
        floor += (f'<div class="desk" style="left:{x}px;top:{y}px"><div class="glowm" id="gm{k}"></div>'
                  f'<div class="mon" id="mon{k}">{bars}</div></div>')
    for n, ag in enumerate(sc.get("agents", [])):
        d = ag.get("desk", n) % nd
        x, y = pos[d]
        ta = T(ag.get("at")) if ag.get("at") else a0 + .3 + n * .5
        ty = T(ag["type_at"]) if ag.get("type_at") else ta + 1.4
        sx, sy = x + 52, y + 84  # chair spot in front of the desk
        agents_html += (f'<div class="agent" id="ag{n}" data-walk="{ta:.2f}" data-sx="{sx}" data-sy="{sy}" data-type="{ty:.2f}" data-desk="{d}">'
                        f'<div class="bob">{sprite(ag.get("color", "#FF6A00"))}</div>'
                        f'<div class="tagp">{esc(ag.get("name", f"Agent {n + 1}"))}</div>'
                        f'<div class="bub">{esc(ag.get("task", "</>"))}</div></div>')
    head = (f'<div class="bar2"><span class="dot"></span><span class="dot"></span><span class="dot"></span>'
            f'<span class="wt">{esc(sc.get("wtitle", "Pixel Office"))}</span>'
            f'{"<span class=%slive%s>LIVE</span>" % (chr(34), chr(34)) if sc.get("live", True) else ""}</div>')
    return (f'<div class="win card"{at(a0)} data-anim="glass">{head}<div class="office">{floor}{agents_html}</div></div>'
            + pill(sc, T) + script(sc, T))


_DUR = {}


def clip_len(src):
    """seconds of motion/clips/<src> (videos only)."""
    if src not in _DUR:
        out = subprocess.run([vedit.binpath("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(MOTION / "clips" / src)], capture_output=True, text=True).stdout.strip()
        _DUR[src] = float(out or 0)
    return _DUR[src]


def media(src, start=0.0, dur=30.0, offset=0.0):
    """<video> (timed, muted) or <img> from motion/clips/."""
    if src.endswith((".mp4", ".mov", ".webm")):
        d = max(.5, min(dur, clip_len(src) - offset - .05))
        return (f'<video class="vclip" src="../clips/{src}" data-start="{start:.2f}" data-duration="{d:.2f}" '
                f'data-media-start="{offset:.2f}" muted playsinline></video>')
    return f'<img class="mimg" src="../clips/{src}" alt="">'


def tpl_reel(sc, T):
    """Real examples side by side: items[{src, label, at, offset}] in phones; each lights up on its word."""
    D = sc.get("_dur", 6)
    cells = []
    for it in sc["items"]:
        a = T(it.get("at"))
        cells.append(f'<div class="cell"><div class="phone media"{at(T(sc.get("at")))} data-anim="glass" data-on="{a:.2f}" data-pulse="{a:.2f}">'
                     f'<div class="scr">{media(it["src"], 0, D, it.get("offset", 0))}<div class="notch"></div></div></div>'
                     f'<div class="chip"{at(a)} data-anim="pop" data-on="{a + .05:.2f}">{esc(it["label"])}</div></div>')
    return f'<div class="reel">{"".join(cells)}</div>' + pill(sc, T) + script(sc, T)


def tpl_orbit(sc, T):
    """Orbiting carousel of our own clips/screenshots: items[{src, label, at, offset}], turns (default .6)."""
    D = sc.get("_dur", 6)
    n = len(sc["items"])
    R = int(sc.get("radius", 150 + 40 * n))

    def card(k, it):  # text card instead of a clip: card{k (mono kicker), t (word), s (script line), d (mono foot), icon, back}
        c, a = it["card"], T(it.get("at"))
        tf = int(min(74, 74 * 266 / max(1.0, text_w(c["t"], 900, 74, -.045))))
        sf = int(min(58, 58 * 266 / max(1.0, text_w(c.get("s", ""), "GreatVibes", 58, 0))))
        return (f'<div class="it wk" style="transform:rotateY({k * 360 / n:.1f}deg) translateZ({R}px)">'
                f'<div class="f"{at(a)} data-anim="pop"><div class="wk-k">{esc(c.get("k", ""))}</div>{icon(c.get("icon"))}'
                f'<div class="wk-t" style="font-size:{tf}px">{esc(c["t"])}</div><div class="wk-s" style="font-size:{sf}px">{esc(c.get("s", ""))}</div>'
                f'{"<div class=%swk-d%s>%s</div>" % (chr(34), chr(34), esc(c["d"])) if c.get("d") else ""}</div>'
                f'<div class="b"{at(a)} data-anim="pop">{esc(c.get("back", ""))}</div></div>')
    its = "".join(
        card(k, it) if it.get("card") else
        f'<div class="it" style="transform:rotateY({k * 360 / n:.1f}deg) translateZ({R}px)"{at(T(it.get("at")))} data-anim="pop">'
        f'{media(it["src"], 0, D, it.get("offset", 0))}{"<div class=%slab%s>%s</div>" % (chr(34), chr(34), esc(it["label"])) if it.get("label") else ""}</div>'
        for k, it in enumerate(sc["items"]))
    tall = ' style="height:720px"' if any(it.get("card") for it in sc["items"]) else ""  # text cards: keep a stamp clear of the low captions
    return (f'<div class="orb"{tall}><div class="ring" data-orbit="{float(sc.get("turns", .6)):.2f}">{its}</div></div>'
            + pill(sc, T) + script(sc, T))


def tpl_demo(sc, T):
    """Before → after demo of a revision: mode hold | bounce | headline; ask (chat bubble) + ask_at, fix_at, word."""
    mode, a, f = sc["mode"], T(sc.get("ask_at")), T(sc.get("fix_at"))
    bubble = f'<div class="bubble me" style="max-width:none;margin-bottom:26px"{at(a)} data-anim="right">{rich(sc["ask"])}</div>'
    word = esc(sc.get("word", "LEARN"))
    if mode == "hold":
        stage = (f'<div class="word">{word}</div>'
                 f'<svg class="ringt" viewBox="0 0 110 110"><circle cx="55" cy="55" r="46" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="9"/>'
                 f'<circle class="rg" cx="55" cy="55" r="46" fill="none" stroke="#FF6A00" stroke-width="9" stroke-linecap="round" transform="rotate(-90 55 55)"/></svg>'
                 f'<div class="ringt"><span class="rs">2s</span></div>')
    elif mode == "bounce":
        stage = (f'<div class="floor"></div><div class="card bcard">{icon(sc.get("icon", "layers"))}'
                 f'<div><div class="t">{esc(sc.get("card", "Week 1"))}</div><div class="s">{esc(sc.get("card_s", "Learn the fundamentals"))}</div></div></div>')
    else:
        stage = f'<div class="mini"><div class="safe"></div><div class="hl3">{"<br>".join(rich(x) for x in sc.get("headline", "Build/*faster*").split("/"))}</div></div>'
    return (bubble + f'<div class="demo card" data-demo="{mode}" data-fix="{f:.2f}" data-t0="{a + .3:.2f}"{at(a + .1)} data-anim="glass">'
            f'<div class="stage">{stage}</div><div class="st">BEFORE</div><div class="st af">AFTER ✓</div></div>' + pill(sc, T))


def tpl_thumb(sc, T):
    """Thumbnail hook (first ~3 s, doubles as the thumbnail): tag, rows of BIG words; tokens "H:word" orange box,
    "O:word" orange text, "_" = space, "@phrase" times the row. Rows auto-fit 1000 px."""
    out = [f'<div class="th-tag"{at(T(sc.get("tag_at")) if sc.get("tag_at") else .02)} data-anim="pop">{esc(sc["tag"])}</div>'] if sc.get("tag") else []
    for n, row in enumerate(sc["rows"]):
        row, _, when = row.partition("@")
        parts, plain = [], []
        for tok in row.split():
            kind, _, txt = tok.partition(":") if re.match(r"^[HO]:", tok) else ("", "", tok)
            txt = txt.replace("_", " ")
            plain.append(txt.upper())
            parts.append(f'<span class="{ {"H": "hb", "O": "o"}.get(kind, "")}">{esc(txt)}</span>' if kind else esc(txt))
        size = int(sc.get("sizes", [])[n]) if n < len(sc.get("sizes", [])) else 168
        w = text_w(" ".join(plain), 900, size, -.045) + (size * .4 if "H:" in row else 0)
        size = int(size * min(1.0, 860 / max(1.0, w)))  # safe zone: 64 left, 144 right
        t = T(when) if when else .08 + n * .14
        out.append(f'<div class="th-row" style="font-size:{size}px" data-tat="{t:.2f}">{" ".join(parts)}</div>')
    return "".join(out)


def tpl_article(sc, T):
    """News article in a browser card: url, outlet, headline (with *mark*), by (date/author), mark_at;
    or img (screenshot in motion/clips) + box [x, y, w, h] (px in the 916-wide card) + focus {at, z, x, y}."""
    a = T(sc.get("at"))
    if sc.get("img"):
        f = sc.get("focus") or {}
        kb = (f' data-kb="{T(f.get("at")):.2f}" data-kz="{f.get("z", 1.5)}" data-kx="{f.get("x", 0)}" data-ky="{f.get("y", 0)}"' if f else "")
        box = ""
        if sc.get("box"):
            x, y, w, h = sc["box"]
            box = f'<div class="box" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"{at(T(sc.get("box_at")))} data-anim="pop"></div>'
        pg = f'<div class="pg img"><img src="../clips/{sc["img"]}" alt=""{kb}>{box}</div>'
    else:
        hd = re.sub(r"\*(.+?)\*", lambda m: f'<span class="hl" data-mark="{T(sc.get("mark_at")):.2f}">{esc(m.group(1))}</span>', esc(sc["headline"]))
        lines = "".join(f'<div class="ln" style="width:{w}%"></div>' for w in (100, 94, 97, 70))
        pg = (f'<div class="pg"><div class="outlet">{esc(sc.get("outlet", ""))}</div><div class="hd">{hd}</div>'
              f'<div class="by">{esc(sc.get("by", ""))}</div>{lines}</div>')
    return (f'<div class="brw"{at(a)} data-anim="up"><div class="ub"><i></i><i></i><i></i><div class="url">{esc(sc.get("url", ""))}</div></div>{pg}</div>'
            + pill(sc, T) + script(sc, T))


def tpl_tag(sc, T):
    """v6 on-screen tag (transparent, sits on the A-roll at the top of the safe zone).
    k (small orange kicker) · name (big, *orange* via rich) · role (mono line, typed in on role_at) ·
    color (pixel-agent avatar in that shirt colour) or icon (orange tile) · steps[{t, at}] chips that light up · pos "bottom"."""
    a0 = T(sc.get("at"))
    out = ""
    if sc.get("name") or sc.get("k"):
        av = (f'<div class="tg-av">{sprite(sc["color"])}</div>' if sc.get("color") else
              f'<div class="tg-ic"><svg viewBox="0 0 24 24">{ICONS[sc["icon"]]}</svg></div>' if sc.get("icon") else "")
        style = {"comment": " cm", "counter": " ct", "typing": " ty"}.get(sc.get("style", ""), "")
        name = ""
        if sc.get("name"):
            m = re.match(r"^(\D*?)(\d[\d,]*)(.*)$", str(sc["name"])) if sc.get("style") == "counter" else None
            if m:  # proof counter: the number counts up (tick … ding in sfx.py via the scene's "sfx" cues)
                name = (f'<div class="tg-t">{esc(m.group(1))}<span data-at="{a0 + .3:.2f}" data-anim="count" data-to="{m.group(2).replace(",", "")}"'
                        f' data-dur="{float(sc.get("count_dur", 1.2)):.2f}"></span>{esc(m.group(3))}</div>')
            elif sc.get("style") == "typing":  # typed headline: letters appear like a keyboard
                name = (f'<div class="tg-t" data-at="{a0 + .3:.2f}" data-anim="type" '
                        f'data-dur="{min(1.4, max(.5, len(sc["name"]) * .06)):.2f}">{rich(sc["name"])}</div>')
            elif sc.get("slot") == "hdr":  # header card: wraps to ≤2 lines inside the 558 px card, largest size that fits
                words, fs = str(sc["name"]).replace("*", "").split(), 40
                for size in range(int(sc.get("max", 66)), 39, -2):
                    lines, cur = 1, ""
                    for wd in words:
                        cand = (cur + " " + wd).strip()
                        if cur and text_w(cand, 900, size, -.035) > 552:
                            lines, cur = lines + 1, wd
                        else:
                            cur = cand
                    if lines <= 2:
                        fs = size
                        break
                name = f'<div class="tg-t" style="font-size:{fs}px">{rich(sc["name"])}</div>'
            else:
                name = f'<div class="tg-t">{rich(sc["name"])}</div>'
        tx = (f'<div class="tg-k">{esc(sc["k"])}</div>' if sc.get("k") else "") + name
        if sc.get("role"):
            ra = T(sc.get("role_at")) if sc.get("role_at") else a0 + .35
            tx += f'<div class="tg-s"{at(ra)} data-anim="type" data-dur="{min(1.0, max(.4, len(sc["role"]) * .03)):.2f}">{esc(sc["role"])}</div>'
        if sc.get("style") == "comment":
            tx += f'<div class="tg-m"{at(a0 + .45)} data-anim="fade"><span>Reply</span><b>&#9829;</b></div>'
        anim = "pop" if sc.get("style") == "comment" else "tagr" if sc.get("side") == "right" else "tagin"
        out += f'<div class="tg{"" if av else " np"}{style}"{at(a0)} data-anim="{anim}">{av}<div class="tg-tx">{tx}</div></div>'
    if sc.get("steps"):
        chips = []
        for i, st in enumerate(sc["steps"]):
            t = T(st.get("at")) if st.get("at") else a0 + .2 + i * .25
            if i:
                chips.append(f'<span class="ar"{at(t)} data-anim="fade">→</span>')
            chips.append(f'<div class="chip"{at(t)} data-anim="pop" data-on="{t + .05:.2f}">{esc(st["t"])}</div>')
        out += f'<div class="tg-steps">{"".join(chips)}</div>'
    return out


def tpl_money(sc, T):
    """Money moment: kicker, total (counts up from 0 on total_at, prefix ₱), suffix ("K"), sub line, and a stack of
    `rows` received-payment cards (amount, time) dropping in one by one from rows_at. Names are blurred bars."""
    a = T(sc.get("total_at"))
    total = int(sc["total"])
    rows_at = T(sc.get("rows_at")) if sc.get("rows_at") else a
    gap = float(sc.get("gap", .22))
    rows = "".join(
        f'<div class="nr"{at(rows_at + i * gap)} data-anim="drop"><div class="nd"><svg viewBox="0 0 24 24">{ICONS["check"]}</svg></div>'
        f'<div class="nx"><div class="nl">Received money from</div><div class="nb" style="width:{48 + (i * 17) % 34}%"></div></div>'
        f'<div><div class="na">{esc(sc.get("amount", "₱4,500.00"))}</div><div class="nt">{esc(t)}</div></div></div>'
        for i, t in enumerate(sc.get("times", ["just now", "1 min ago", "3 mins ago", "5 mins ago", "8 mins ago"])))
    return (f'<div class="money">'
            + f'<div class="mt"{at(a)} data-anim="big"><span class="pf">{esc(sc.get("prefix", "₱"))}</span>'
              f'<span data-at="{a:.2f}" data-anim="count" data-to="{total}" data-dur="{float(sc.get("count_dur", 1.6)):.2f}"></span>{esc(sc.get("suffix", ""))}</div>'
            + (f'<div class="ms"{at(T(sc.get("sub_at")) if sc.get("sub_at") else a + .4)} data-anim="up">{rich(sc["sub"])}</div>' if sc.get("sub") else "")
            + f'<div class="ntf">{rows}</div></div>')


def tpl_stat(sc, T):
    """Big number: n (digits → counts up; else pops), u (unit line), x (small context), n_at."""
    n = str(sc["n"])
    a = T(sc.get("n_at"))
    shown = (f"{int(n.replace(',', '')):,}" if re.fullmatch(r"[\d,]+", n) else n) + sc.get("suffix", "")
    px = min(230, int(840 * 230 / max(1.0, text_w(shown, 900, 230, -.05))))
    num = (f'<div class="n" style="font-size:{px}px" data-anim="count" data-to="{n.replace(",", "")}" data-suffix="{esc(sc.get("suffix", ""))}"{at(a)}>{esc(n)}</div>'
           if re.fullmatch(r"[\d,]+", n) else f'<div class="n" style="font-size:{px}px"{at(a)} data-anim="big">{esc(n)}{esc(sc.get("suffix", ""))}</div>')
    return (f'<div class="stat">{num}<div class="u"{at(T(sc.get("u_at")) if sc.get("u_at") else a + .3)} data-anim="up">{rich(sc.get("u", ""))}</div>'
            f'{"<div class=%sx%s data-at=%s%.2f%s data-anim=%sfade%s>%s</div>" % (chr(34), chr(34), chr(34), T(sc.get("x_at")) if sc.get("x_at") else a + .6, chr(34), chr(34), chr(34), rich(sc["x"])) if sc.get("x") else ""}</div>'
            + pill(sc, T) + script(sc, T))


def tpl_carousel(sc, T):
    """Coverflow carousel: items[{t, s, icon, k, at}] (3–5 cards). The cards wait as numbered shells; on its phrase a card
    slides to the centre, fills in and lights up in the accent; cards already said step left, turned away and dimmed.
    k = small label (01, 02 …), spacing = px between card centres (400)."""
    cards = []
    for i, it in enumerate(sc["items"][:6]):
        a = T(it.get("at"))
        k = esc(it.get("k") or f"{i + 1:02d}")
        plain = it["t"].replace("*", "")
        longest = max(plain.split() or [plain], key=lambda w: text_w(w, 900, 84, -.04))
        px = 84 * min(1.0, 444 / max(1.0, text_w(longest, 900, 84, -.04)),  # longest word fits the card …
                      2 * 444 * .9 / max(1.0, text_w(plain, 900, 84, -.04)))  # … and the title stays within 2 lines
        sub = f'<div class="cs">{rich(it["s"])}</div>' if it.get("s") else ""
        cards.append(f'<div class="cc" data-cat="{a:.2f}"><div class="cl"></div><div class="ch"><div class="cn"><span>{k}</span><b>{k}</b></div>'
                     f'{icon(it.get("icon"))}</div><div class="cq"><i></i><i></i></div><div class="ct" style="font-size:{int(px)}px">{rich(it["t"])}</div>{sub}</div>')
    return (f'<div class="car" data-car="{int(sc.get("spacing", 400))}"><div class="trk">{"".join(cards)}</div></div>'
            f'<div class="cdots">{"<i></i>" * len(cards)}</div>' + pill(sc, T) + script(sc, T))


def shrink_geom(sc):
    """The card the footage shrinks into, in 1080×1920 px (also handed to vedit as the overlay's "card"):
    x, y, w, h on screen · s = footage scale · src_y = top of the footage window shown · r = corner radius ·
    tin / tout = shrink and grow-back seconds."""
    s = min(.8, max(.4, float(sc.get("scale", .6))))
    w = round(1080 * s)
    y = int(sc.get("y", 418 if sc.get("title") else 312 if sc.get("kicker") else 250))
    h = min(int(sc.get("h", 712 if sc.get("items") else 860)), round(1920 * s))
    win = h / s  # footage rows inside the card
    src_y = sc.get("src_y", float(sc.get("face_y", 720)) - win / 2)  # keep the face (default footage y 720) in the middle
    src_y = round(min(max(0.0, float(src_y)), 1920 - win), 1)
    return dict(x=(1080 - w) // 2, y=y, w=w, h=h, s=round(s, 4), src_y=src_y, r=44, tin=.5, tout=.45)


def tpl_shrink(sc, T):
    """Shrink card (transparent): vedit scales the real footage into a rounded card in the upper middle (≈60 %, the face
    stays whole and sharp), kicker + title appear above it and items[{t, icon, at, on}] chips below, then the footage
    grows back to full screen. Card: scale (.6), y / h (px), face_y (footage y kept in view, 720) or src_y.
    This page never draws inside the card, so nothing can cover the face."""
    g = shrink_geom(sc)
    x, y, w, h, r = g["x"], g["y"], g["w"], g["h"], g["r"]
    out = (f'<div class="sk-dim" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:{r}px"></div>'
           f'<div class="sk-ring" data-tin="{g["tin"]}" data-tout="{g["tout"]}" '
           f'style="left:{x - 6}px;top:{y - 6}px;width:{w + 12}px;height:{h + 12}px;border-radius:{r + 6}px"></div>')
    if sc.get("kicker"):
        out += f'<div class="kicker sk-k" style="top:236px" data-at="0.05" data-anim="fade">{esc(sc["kicker"])}</div>'
    if sc.get("title"):
        px = int(min(80, 80 * 940 / max(1.0, text_w(sc["title"].replace("*", ""), 900, 80, -.035))))
        out += (f'<div class="sk-t" style="top:{300 if sc.get("kicker") else 250}px;font-size:{px}px"'
                f'{at(T(sc.get("title_at")) if sc.get("title_at") else 0.12)} data-anim="up">{rich(sc["title"])}</div>')
    chips = []
    for c in sc.get("items", []):
        extra = f' data-on="{T(c["on"]):.2f}"' if c.get("on") is not None else ""
        ic = f'<svg viewBox="0 0 24 24">{ICONS[c["icon"]]}</svg>' if c.get("icon") else ""
        chips.append(f'<div class="chip"{at(T(c.get("at")))} data-anim="pop"{extra}>{ic}{rich(c["t"])}</div>')
    if chips:
        out += f'<div class="sk-items" style="top:{y + h + 40}px">{"".join(chips)}</div>'
    return out


TEMPLATES = dict(carousel=tpl_carousel, shrink=tpl_shrink, money=tpl_money, tag=tpl_tag, thumb=tpl_thumb, article=tpl_article, stat=tpl_stat, reel=tpl_reel, orbit=tpl_orbit, demo=tpl_demo, office=tpl_office, terminal=tpl_terminal, phone=tpl_phone, export=tpl_export, upload=tpl_upload, duo=tpl_duo, behind=tpl_behind,
                 list=tpl_list, chips=tpl_chips, pipeline=tpl_pipeline, big=tpl_big, versus=tpl_versus,
                 statement=tpl_statement, loading=tpl_loading, error=tpl_error, chat=tpl_chat, email=tpl_email,
                 map=tpl_map, excel=tpl_excel, notify=tpl_notify, cta=tpl_cta,
                 lockup=tpl_lockup, meter=tpl_meter, choice=tpl_choice, flow=tpl_flow, chapter=tpl_chapter,
                 mindmap=tpl_mindmap, loop=tpl_loop, tiles=tpl_tiles, approval=tpl_approval)
import mograph_more  # noqa: E402  v7: the 2026 short-form catalog (reference/motion_trends_2026.md)
MORE = mograph_more.register(sys.modules[__name__])
TEMPLATES.update(MORE["templates"])
MORE_TYPES = set(MORE["types"])
CSS = CSS + MORE["css"]


def build(sc, tl, prev_start, floor=0.0):
    if sc.get("start_after"):  # bridge card: begins right after a phrase ends (fills a breathing gap)
        start = tl.find(sc["start_after"], prev_start, end=True) + sc.get("offset", 0.08)
    else:
        start = tl.find(sc["start"], prev_start) - sc.get("lead", 0.15)
    start = max(0.0, floor, start)  # scenes chain: never overlap the previous one (design system §7)
    if sc.get("end"):
        end = tl.find(sc["end"], start + 0.5)
    elif sc.get("until"):
        end = tl.find(sc["until"], start, end=True) + 0.35
    elif sc.get("dur"):  # fixed on-screen time (short callouts)
        end = start + float(sc["dur"])
    else:
        end = tl.dur
    end = min(end, tl.dur)
    if end - start < 0.8:
        raise LookupError(f"scene became too short ({end - start:.1f}s) after edits")
    cursor, cache = [start], {}

    def T(v):
        """phrase → seconds from scene start (phrases resolved in order, cached)."""
        if v is None:
            return 0.12
        if isinstance(v, (int, float)):
            return float(v)
        if v not in cache:
            t = tl.find(v, max(start, cursor[0] - 2.0), soft=True)
            if t is None or t > end:  # written out of spoken order → search the whole scene again
                t2 = tl.find(v, max(0.0, start - 1.2), soft=True)  # (a chained scene can start just after its first cue word)
                t = t2 if t2 is not None and t2 <= end else t
            if t is None:  # phrase was edited out → show the item right after the previous one
                t = cursor[0] + 0.4
            cursor[0] = t
            cache[v] = max(0.05, min(t - start, max(0.05, end - start - 0.3)))
        return cache[v]

    # resolve every phrase in the order it is written, so templates may use them in any order
    TIME_KEYS = {"at", "on", "check", "strike", "read", "title_at", "press_at", "sug_at", "pick_at", "answer_at", "final_at",
                 "new_at", "reveal_at", "flip_at", "click_at", "labels_at", "big_at", "sub_at", "word_at",
                 "part2_at", "follow_at", "route_at", "dest_at", "change_at", "lost_at", "excel_at", "tabs_at",
                 "final_at", "pick_at", "what_at", "core_at", "approve_at", "line_at", "buttons_at",
                 "headline_at", "name_at", "cta_at", "controls_at", "done_at", "file_at", "tab_at", "ask_at", "fix_at"}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in TIME_KEYS and isinstance(v, str):
                    T(v)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk({k: v for k, v in sc.items() if k not in ("start", "end", "until")})

    head = ""
    if sc["type"] in MORE_TYPES:  # v7: placed by the template itself (top band / side / target / chest / full page)
        return start, end, TEMPLATES[sc["type"]](dict(sc, _dur=end - start), T)
    if sc["type"] in ("behind", "tag", "shrink"):  # own layout (shrink places its kicker/title around the card)
        style = "<style>.otag .content{top:%dpx}</style>" % int(sc["y"]) if sc["type"] == "tag" and sc.get("y") else ""
        return start, end, style + TEMPLATES[sc["type"]](sc, T)
    if sc.get("kicker"):
        head += f'<div class="kicker" data-at="0.05" data-anim="fade">{esc(sc["kicker"])}</div>'
    if sc.get("title"):
        head += (f'<div class="title{" sm" if sc.get("title_sm") else ""}"{at(T(sc.get("title_at")) if sc.get("title_at") else 0.12)}'
                 f' data-anim="up">{rich(sc["title"])}</div>')
    body = TEMPLATES[sc["type"]](dict(sc, _dur=end - start), T)
    if sc.get("stamp"):  # rotated outlined stamp slammed over the last element ("DENIED", "HINDI 'TO")
        st = sc["stamp"]
        lift = (f' style="bottom:{int(st["bottom"])}px;background:rgba(18,12,9,.94);box-shadow:0 12px 40px rgba(0,0,0,.6)"'
                if st.get("bottom") is not None else "")  # raised clear of the captions, solid so it reads over the cards
        body = (f'<div style="position:relative">{body}<div class="stamp"{lift}{at(T(st.get("at")))} data-anim="stamp">'
                f'{esc(st["t"])}</div></div>')
    style = ""
    if sc.get("center") or sc["type"] in ("chapter",) or (sc["type"] == "big" and not re.fullmatch(r"[\d,]+", sc["big"])):
        style += ".content{align-items:center;text-align:center}.kicker{justify-content:center}"
    if sc["type"] == "carousel":  # lift the block so the dots stay clear of the low captions (y ≈ 1420)
        style += ".content{padding-bottom:90px}"
    if sc["type"] == "thumb" and sc.get("y"):  # thumbnail title at the top (back-cam cold open) instead of over the chest
        style += f".thumb .content{{top:{int(sc['y'])}px;bottom:auto}}"
    if sc["type"] == "lockup" and sc.get("y"):
        style += f".lockup .content{{top:{int(sc['y'])}px;bottom:auto;justify-content:flex-start}}"
    if sc.get("mono"):  # third typeface: kicker + chapter step line in JetBrains Mono (Inter Tight + Great Vibes + Mono)
        style += '.kicker,.chap .step{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;font-weight:600;letter-spacing:.06em}'
    return start, end, (f"<style>{style}</style>" if style else "") + head + body


def page(sid, dur, inner, panel, glass=False, news=None):
    if news is not None and not panel:  # v5 newsroom page: masthead, clipped body, wipe slab, cam ring, source pill
        src = news.get("source")
        srch = (f'<div class="src"><div class="l">SOURCE</div><div class="d">{esc(src.get("name", ""))}</div>'
                f'<div class="t">{esc(src.get("date", ""))}</div></div>' if src else "")
        inner = (f'<div class="sbody"><div class="bg"></div>'
                 f'<div class="masthead"><b>AI <i>UPDATE</i></b><span>· {esc(news.get("section", "BBD NEWS"))}</span><span class="dt">{esc(news.get("date", ""))}</span></div>'
                 f'<div class="content">{inner}</div>{srch}{"<div class=%scam%s></div>" % (chr(34), chr(34)) if news.get("cam") else ""}</div>')
        cls, attrs = "news", f' data-win="{1 if news.get("win", True) else 0}" data-wout="{1 if news.get("wout", True) else 0}"'
    else:
        cls, attrs = "", ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1080, height=1920"/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@600&family=Playfair+Display:ital,wght@0,800;1,800&display=block" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style></head>
<body><div id="root" data-composition-id="{sid}" data-start="0" data-duration="{dur:.3f}" data-width="{W}" data-height="{H}">
<div class="clip scene{' ' + panel if panel else ''}{' glass' if glass and not panel else ''}{' ' + cls if cls else ''}" data-start="0" data-duration="{dur:.3f}" data-track-index="0"{attrs}>
{inner if cls else '<div class="bg"></div><div class="glow"></div>' + ('' if panel else '<div class="grain"></div>') + '<div class="content">' + inner + '</div>'}{'<div class="sheen"></div>' if glass and not panel else ''}
<div style="position:absolute;left:0;top:0;opacity:0;pointer-events:none"><span style="font-family:'Great Vibes'">Aa</span>
<span style="font-family:'Inter Tight';font-weight:500">Aa</span><span style="font-family:'Inter Tight';font-weight:600">Aa</span>
<span style="font-family:'Inter Tight';font-weight:700">Aa</span><span style="font-family:'Inter Tight';font-weight:800">Aa</span>
<span style="font-family:'Inter Tight';font-weight:900">Aa</span></div></div></div>
<script>{RUNTIME % dict(dur=dur, sid=sid, more=MORE["js"])}</script></body></html>
"""


def gallery(look_from=None):
    """Studio gallery: every v7 type as a live sample page (timed in seconds) in the creator's look
    → motion/scenes/gal_<id>.html. Usage: mograph.py --gallery [work/<name>/decisions.json]"""
    dec = vedit.jload(Path(look_from), {}) if look_from else {}
    LOOK_DEC.clear(); LOOK_DEC.update(dec)
    (MOTION / "scenes").mkdir(parents=True, exist_ok=True)
    n = 0
    for spec in mograph_more.GALLERY:
        sc, dur = dict(spec), float(spec["dur"])
        inner = TEMPLATES[sc["type"]](dict(sc, _dur=dur), lambda v: float(v) if isinstance(v, (int, float)) else 0.12)
        sid = f"gal_{sc['id']}"
        (MOTION / "scenes" / f"{sid}.html").write_text(brandkit.brandize_page(page(sid, dur, inner, mograph_more.panel_of(sc)), dec))
        n += 1
    print(f"✓ {n} gallery pages → motion/scenes/gal_*.html", flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--gallery":
        return gallery(sys.argv[2] if len(sys.argv) > 2 else None)
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--only", help="comma-separated scene ids")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--quality", default="looks")
    a = ap.parse_args()
    src, wd, meta = vedit.ctx(a.video)
    dec = vedit.jload(wd / "decisions.json", {})
    LOOK_DEC.clear(); LOOK_DEC.update(dec)
    scenes = json.loads((wd / "scenes.json").read_text())
    tl = Timeline(wd, dec)
    (MOTION / "scenes").mkdir(parents=True, exist_ok=True)
    (MOTION / "renders").mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    env = dict(os.environ, PATH=f"{NODE_BIN}:{Path(vedit.binpath('ffmpeg')).parent}:{os.environ['PATH']}",
               HYPERFRAMES_SKIP_SKILLS="1")
    overlays, prev, prev_end, prev_glass = [], 0.0, 0.0, False
    theme = dec.get("mograph_theme")
    built = []
    looks = []
    for sc in scenes:  # pass 1: resolve every scene's time on the edited timeline
        if sc.get("disabled"):  # rejected in the editor's review
            continue
        if sc["type"] == "look":  # footage filter flip (B&W / warm / cool …) on a phrase — applied by vedit, no render
            try:
                a0 = tl.find(sc["start"], 0.0) - sc.get("lead", 0.0)
                a1 = tl.find(sc["end"], a0 + 0.3) if sc.get("end") else a0 + float(sc.get("dur", 1.4))
            except LookupError as e:
                print(f"⚠ {sc['id']}: skipped — {e}", flush=True)
                continue
            looks.append(dict(id=sc["id"], at=round(a0, 3), dur=round(a1 - a0, 3), look=sc["look"]))
            print(f"• {sc['id']:<14} {vedit.tc(a0)} → {vedit.tc(a1)} look:{sc['look']}", flush=True)
            continue
        try:
            bt = sc["type"] == "behind"  # text-behind sits under the face layer, so it may share time with a lockup
            chained_theme = sc.get("glass", theme in ("glass", "news")) and prev_glass and sc["type"] not in ("lockup", "thumb")
            start, end, inner = build(sc, tl, prev, 0.0 if bt else prev_end + (0.0 if chained_theme else 0.04))
        except LookupError as e:
            print(f"⚠ {sc['id']}: skipped — {e}", flush=True)
            continue
        panel = ("lockup" if sc["type"] == "lockup" else "behind" if sc["type"] == "behind" else "thumb" if sc["type"] == "thumb"
                 else "shrink" if sc["type"] == "shrink"
                 else ("otag" + (" tbot" if sc.get("pos") == "bottom" else "") + (" mini" if sc.get("mini") else "")
                       + (" sr" if sc.get("side") == "right" else "") + (" hdr" if sc.get("slot") == "hdr" else "")) if sc["type"] == "tag"
                 else mograph_more.panel_of(sc) if sc["type"] in MORE_TYPES
                 else sc.get("layout") if sc.get("layout") in ("panel", "lower", "band") else None)
        if not bt:
            prev, prev_end = start, end
            prev_glass = not panel and sc.get("glass", theme in ("glass", "news"))
        built.append((sc, start, end, inner, panel))
    for i, (sc, start, end, inner, panel) in enumerate(built):  # pass 2: write + render
        dur = round(end - start, 3)
        glass = not panel and theme == "glass" and sc.get("glass", True)
        news = None
        if not panel and theme == "news":
            def themed(j):
                return 0 <= j < len(built) and not built[j][4]
            pv = next((j for j in range(i - 1, -1, -1) if built[j][4] != "behind"), None)
            nx = next((j for j in range(i + 1, len(built)) if built[j][4] != "behind"), None)
            win = not (pv is not None and themed(pv) and start - built[pv][2] < 0.5)
            wout = not (nx is not None and themed(nx) and built[nx][1] - end < 0.5)
            news = dict(source=sc.get("source"), section=dec.get("news_section", "BBD NEWS"), date=dec.get("news_date", ""),
                        win=win, wout=wout, cam=sc.get("cam", dec.get("cam_bubble", False)))
        sid = sc["id"]
        ext = "mov" if panel or glass or news is not None else "mp4"
        out = MOTION / "renders" / f"{sid}.{ext}"
        overlays.append(dict(id=sid, file=str(out.relative_to(ROOT)), at=round(start, 3), dur=dur,
                             kind=("tag" if panel and panel.startswith("otag") else panel) or ("glass" if glass else "news" if news is not None else "full"),
                             caption=sc.get("caption", mograph_more.caption_of(sc) if sc["type"] in MORE_TYPES else "normal" if panel and panel.startswith("otag") else {"panel": "panel", "lower": "top", "band": "normal", "lockup": "hide", "behind": "normal", "thumb": "hide", "otag": "normal", "otag tbot": "normal", "shrink": "panel"}.get(panel, "low")),
                             **({"card": shrink_geom(sc)} if sc["type"] == "shrink" else {}),  # vedit scales the footage into it
                             **({"sfx": [[(tl.find(off, start - 0.5) - start) if isinstance(off, str) else off, nm]
                                         for off, nm in sc["sfx"]]} if sc.get("sfx") else {}), **({"riser": True} if sc.get("riser") else {}),
                             **({"wout": news["wout"], "win": news["win"]} if news is not None else {})))
        if only and sid not in only:
            continue
        hp, doc = MOTION / "scenes" / f"{sid}.html", brandkit.brandize_page(page(sid, dur, inner, panel, glass, news), dec)
        made = hp.with_suffix(".rendered.html")  # the exact HTML the current render was made from
        unchanged = made.exists() and made.read_text() == doc and out.exists()
        overlays[-1]["stale"] = not unchanged
        hp.write_text(doc)
        print(f"• {sid:<14} {vedit.tc(start)} → {vedit.tc(end)} ({dur:.1f}s){' ' + panel if panel else ''}"
              f"{'  (unchanged, reused)' if unchanged else ''}", flush=True)
        if a.no_render or unchanged:
            continue
        cmd = ["npx", "-y", "hyperframes", "render", str(MOTION), "-c", f"scenes/{sid}.html", "-o", str(out),
               "--fps", "30", "--quiet", "--quality", a.quality]
        if ext == "mov":
            cmd += ["--format", "mov"]
        r = subprocess.run(cmd, cwd=MOTION, env=env, capture_output=True, text=True)
        if r.returncode or not out.exists():
            sys.stderr.write(r.stdout[-2000:] + r.stderr[-3000:])
            vedit.die(f"render failed: {sid}")
        made.write_text(doc)
        overlays[-1]["stale"] = False
    dec["overlays"] = overlays
    dec["looks"] = looks
    vedit.jsave(wd / "decisions.json", dec)
    print(f"✓ {len(overlays)} overlays registered in decisions.json")


if __name__ == "__main__":
    main()
