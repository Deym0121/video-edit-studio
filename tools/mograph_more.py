"""mograph v7 templates — the 2026 short-form catalog (reference/motion_trends_2026.md), built as transparent pages.

Every type here sits ON the footage without touching it (no blur, dim or grade — Lloyd's rule) and is placed in a free
zone: the top band (y 236+), a side, the chest band, around a target on a screen demo, or as an opaque full-screen
page ("bg": true) on B-roll moments. Timing keys ("at", "on", "*_at") are phrases like everywhere else in scenes.json,
or seconds (numbers) — the Studio gallery uses seconds.

register(M) is called by mograph.py with itself as M (esc, rich, at, ICONS, text_w), and returns the templates,
their CSS and the runtime JS that animates them on the page timeline.
"""
from __future__ import annotations

import base64
import json
import math
import random
import re
import struct
import zlib

TYPES = ("scribble", "target", "ping", "keys", "island", "search", "post", "call", "tier", "score", "price", "timer",
         "ring", "chart", "timeline", "streak", "flap", "glitch", "redact", "define", "pov", "rank", "ransom", "flip",
         "polaroid", "achieve", "sticker", "burst", "rail", "ff",
         # next wave (2026-10-21)
         "wipe", "loupe", "thread", "voicenote", "feed", "receipt", "venn", "cloud", "slot", "tear", "board", "dock", "frame3d")
FS_ONLY = ("board", "frame3d")  # always an opaque full-screen page (B-roll moments)
CB_TYPES = ("venn", "cloud", "thread")  # on the footage these sit in the chest band (y 1150) unless moved

CSS = r"""
/* ===== v7 catalog: transparent, placed pages (never over the face / the demo) ===== */
.mx .bg,.mx .glow,.mx .grain{display:none}
.mx .content{position:absolute;inset:0;padding:0;display:block}
.mx.fs .bg{display:block}
.mx.fs .glow{display:block}
.mxw{position:absolute;left:64px;right:64px;display:flex;flex-direction:column;align-items:center;gap:16px}
.mxw.l{align-items:flex-start}.mxw.r{align-items:flex-end}
.mxsvg{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:visible}
.mxsvg .st{fill:none;stroke-linecap:round;stroke-linejoin:round}
.mx-chip{display:inline-flex;align-items:center;gap:12px;padding:12px 22px;border-radius:999px;background:rgba(12,9,8,.88);border:2px solid rgba(255,106,0,.8);
  color:#fff;font:800 32px "Inter Tight";white-space:nowrap;box-shadow:0 12px 34px rgba(0,0,0,.45)}
.mx-chip.o{background:var(--grad);color:var(--ink);border:0}
.mx-card{background:rgba(22,16,13,.94);border:2px solid rgba(255,140,60,.32);border-radius:34px;box-shadow:0 24px 70px rgba(0,0,0,.5)}
/* keys */
.kcs{display:flex;gap:18px;align-items:flex-end}
.kc{min-width:118px;height:118px;padding:0 26px;border-radius:24px;background:linear-gradient(180deg,#2B231F,#1A1412);border:2px solid rgba(255,255,255,.14);
  box-shadow:0 10px 0 #0C0908,0 22px 40px rgba(0,0,0,.5);display:grid;place-items:center;font:800 54px "Inter Tight";color:#fff}
.kc.o{border-color:var(--o);box-shadow:0 10px 0 #7A3300,0 0 40px rgba(255,106,0,.45)}
.kplus{font:800 44px "Inter Tight";color:var(--o2);padding-bottom:34px}
/* island */
.isl{position:absolute;left:50%;top:222px;width:960px;height:210px;margin-left:-480px;border-radius:58px;background:#000;display:flex;align-items:center;gap:28px;padding:0 40px;
  box-shadow:0 18px 50px rgba(0,0,0,.5);transform-origin:50% 0;overflow:hidden}
.isl .ic{width:118px;height:118px;border-radius:30px;background:var(--grad);display:grid;place-items:center;flex:none}
.isl .ic svg{width:60px;height:60px;stroke:#fff;fill:none;stroke-width:2.3;stroke-linecap:round;stroke-linejoin:round}
.isl .tx{display:flex;flex-direction:column;gap:6px;min-width:0}
.isl .t{font:800 46px "Inter Tight";color:#fff;white-space:nowrap;letter-spacing:-.02em}
.isl .s{font:600 34px "Inter Tight";color:#A39A93;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:700px}
.isl .tm{margin-left:auto;font:600 30px "JetBrains Mono",monospace;color:#8C837C;align-self:flex-start;padding-top:44px}
/* search */
.srch{width:952px;display:flex;flex-direction:column;align-items:stretch}
.sbar{height:124px;border-radius:62px;background:#fff;display:flex;align-items:center;gap:22px;padding:0 40px;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.sbar svg{width:52px;height:52px;stroke:#5B524C;fill:none;stroke-width:2.6;stroke-linecap:round;flex:none}
.sbar .q{font:700 46px "Inter Tight";color:#15110F;white-space:nowrap;overflow:hidden}
.sbar .car{width:4px;height:54px;background:var(--o);border-radius:2px}
.sug{margin:14px 24px 0;border-radius:30px;background:#fff;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.sug div{display:flex;align-items:center;gap:20px;padding:24px 34px;font:600 38px "Inter Tight";color:#3A332E;border-left:8px solid transparent}
.sug div svg{width:36px;height:36px;stroke:#8C837C;fill:none;stroke-width:2.4;flex:none}
/* post */
.post{width:952px;padding:40px 44px;display:flex;flex-direction:column;gap:22px}
.post .hd{display:flex;align-items:center;gap:22px}
.post .av{width:100px;height:100px;border-radius:50%;background:var(--grad);display:grid;place-items:center;font:900 46px "Inter Tight";color:var(--ink);flex:none}
.post .nm{font:800 42px "Inter Tight";color:#fff;display:flex;align-items:center;gap:10px}
.post .vf{width:38px;height:38px;border-radius:50%;background:var(--o);display:grid;place-items:center}
.post .vf svg{width:24px;height:24px;stroke:#fff;fill:none;stroke-width:3.4}
.post .hn{font:600 32px "Inter Tight";color:#8C837C}
.post .bd{font:600 46px/1.28 "Inter Tight";color:#F4EFEA}
.post .bd span{display:inline-block}
.post .mt{display:flex;gap:46px;font:700 32px "JetBrains Mono",monospace;color:#A39A93;padding-top:6px}
.post .mt b{display:flex;align-items:center;gap:12px;font-weight:700}
.post .mt svg{width:38px;height:38px;stroke:#A39A93;fill:none;stroke-width:2.2}
.post .mt .lk svg{fill:transparent}
/* call */
.call{width:952px;height:200px;border-radius:52px;background:rgba(18,14,12,.96);display:flex;align-items:center;gap:26px;padding:0 34px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.call .av{position:relative;width:120px;height:120px;border-radius:50%;background:var(--grad);display:grid;place-items:center;font:900 52px "Inter Tight";color:var(--ink);flex:none}
.call .av i{position:absolute;inset:-6px;border-radius:50%;border:5px solid var(--o)}
.call .tx{flex:1;min-width:0}.call .t{font:800 46px "Inter Tight";color:#fff}.call .s{font:600 32px "Inter Tight";color:#A39A93}
.call .b{width:104px;height:104px;border-radius:50%;display:grid;place-items:center;flex:none}
.call .b svg{width:52px;height:52px;stroke:#fff;fill:none;stroke-width:2.6;stroke-linecap:round}
.call .no{background:#E5484D}.call .yes{background:#30A46C}
/* tier */
.tier{width:952px;padding:22px;display:flex;flex-direction:column;gap:12px}
.trow{display:flex;align-items:stretch;gap:12px;min-height:132px}
.trow .lt{width:132px;border-radius:20px;display:grid;place-items:center;font:900 72px "Inter Tight";color:var(--ink);flex:none}
.trow .its{flex:1;border-radius:20px;background:rgba(255,255,255,.04);display:flex;gap:12px;padding:12px;align-items:center;flex-wrap:wrap}
.tit{height:108px;padding:0 24px;border-radius:18px;background:#241C18;border:2px solid rgba(255,255,255,.12);display:flex;align-items:center;gap:12px;font:800 36px "Inter Tight";color:#fff}
.tit svg{width:40px;height:40px;stroke:var(--o2);fill:none;stroke-width:2.3}
/* score */
.score{width:952px;padding:38px 44px;display:flex;flex-direction:column;gap:20px}
.score .k{font:800 26px "Inter Tight";letter-spacing:.18em;color:var(--o);text-transform:uppercase}
.srow{display:flex;align-items:center;gap:24px}.srow .n{flex:1;font:800 44px "Inter Tight";color:#fff}
.stars{display:flex;gap:10px}.stars i{width:54px;height:54px;display:block}
.stars i svg{width:54px;height:54px;fill:#3A332E}
.stars i.f svg{fill:var(--o)}
.sfin{display:flex;align-items:center;gap:26px;padding-top:12px;border-top:1px solid rgba(255,255,255,.1)}
.sfin .big{font:900 120px "Inter Tight";color:var(--o);letter-spacing:-.04em;line-height:1}
.sfin .of{font:700 40px "JetBrains Mono",monospace;color:#8C837C}
/* price */
.price{display:flex;align-items:center;gap:26px;flex-wrap:wrap;justify-content:center;max-width:952px}
.price .old{position:relative;font:800 80px "Inter Tight";color:#A39A93;letter-spacing:-.03em}
.price .old svg{position:absolute;left:-14px;top:-10px;width:calc(100% + 28px);height:calc(100% + 20px);overflow:visible}
.price .new{padding:14px 36px;border-radius:999px;background:var(--grad);color:var(--ink);font:900 92px "Inter Tight";letter-spacing:-.04em;box-shadow:0 0 60px rgba(255,106,0,.45)}
.price .bdg{padding:10px 22px;border-radius:14px;background:#fff;color:#15110F;font:900 44px "Inter Tight";transform:rotate(-8deg)}
/* timer + ring */
.dial{position:relative;display:grid;place-items:center}
.dial svg{position:absolute;inset:0;width:100%;height:100%;transform:rotate(-90deg)}
.dial .v{position:relative;font:700 88px "JetBrains Mono",monospace;color:#fff;font-variant-numeric:tabular-nums;display:inline-grid}
.dial .v span{grid-area:1/1}
.dial .lb{position:relative;font:700 26px "Inter Tight";color:#A39A93;letter-spacing:.12em;text-transform:uppercase;margin-top:6px;max-width:72%;text-align:center;line-height:1.15}
.dlb{font:800 38px "Inter Tight";color:#fff;text-align:center;text-shadow:0 0 2px rgba(0,0,0,.85),0 4px 18px rgba(0,0,0,.6);max-width:700px}
.dial .in{display:flex;flex-direction:column;align-items:center}
/* chart */
.chart{width:952px;height:520px;padding:34px 40px;position:relative}
.chart .k{font:800 26px "Inter Tight";letter-spacing:.18em;color:var(--o);text-transform:uppercase}
.chart svg{position:absolute;left:40px;top:96px;width:872px;height:380px;overflow:visible}
.chart .pl{position:absolute;padding:12px 24px;border-radius:999px;background:var(--grad);color:var(--ink);font:900 46px "Inter Tight"}
/* timeline */
.tln{width:952px;padding:46px 40px 40px;position:relative}
.tln .ln{position:absolute;left:70px;right:70px;top:150px;height:8px;border-radius:4px;background:rgba(255,255,255,.14);overflow:hidden}
.tln .ln i{display:block;height:100%;background:var(--o)}
.tln .nodes{display:flex;justify-content:space-between;position:relative}
.tnd{display:flex;flex-direction:column;align-items:center;gap:14px;width:200px;text-align:center}
.tnd .d{font:700 30px "JetBrains Mono",monospace;color:var(--o2)}
.tnd .dot{width:40px;height:40px;border-radius:50%;background:var(--o);box-shadow:0 0 0 8px rgba(255,106,0,.25)}
.tnd .t{font:800 32px/1.15 "Inter Tight";color:#fff}
/* streak */
.strk{padding:34px 40px;display:flex;flex-direction:column;gap:22px;align-items:flex-start}
.strk .hd{display:flex;align-items:baseline;gap:18px}.strk .hd b{font:900 74px "Inter Tight";color:#fff;letter-spacing:-.03em}.strk .hd span{font:700 34px "JetBrains Mono",monospace;color:var(--o2)}
.grd{display:grid;grid-template-columns:repeat(7,96px);gap:12px}
.grd i{width:96px;height:96px;border-radius:20px;background:rgba(255,255,255,.07);display:block}
.grd i.on{background:var(--o)}
.grd i.today{box-shadow:0 0 0 6px #fff}
/* flap */
.flap{display:flex;gap:10px}
.fc{position:relative;width:84px;height:124px;border-radius:12px;background:#1B1513;box-shadow:0 10px 26px rgba(0,0,0,.5);overflow:hidden;perspective:400px}
.fc:after{content:"";position:absolute;left:0;right:0;top:61px;height:2px;background:rgba(0,0,0,.65)}
.fc span{position:absolute;inset:0;display:grid;place-items:center;font:700 82px "JetBrains Mono",monospace;color:#fff}
.fc.sp{background:transparent;box-shadow:none}
/* glitch */
.glt{position:relative;font:900 150px/1 "Inter Tight";letter-spacing:-.04em;text-transform:uppercase;white-space:nowrap}
.glt span{position:absolute;left:0;top:0}
.glt .base{position:relative;color:#fff;text-shadow:0 8px 40px rgba(0,0,0,.5)}
.glt .r{color:#FF2D55;mix-blend-mode:screen}.glt .c{color:#00E5FF;mix-blend-mode:screen}
/* redact */
.rdx{width:952px;padding:40px 46px;display:flex;flex-direction:column;gap:18px}
.rdx .k{font:700 26px "JetBrains Mono",monospace;letter-spacing:.14em;color:#8C837C}
.rdx .ln{font:800 58px/1.25 "Inter Tight";color:#fff}
.rdx .h{position:relative;display:inline-block;color:var(--o)}
.rdx .h i{position:absolute;left:-6px;right:-6px;top:6px;bottom:2px;background:#0B0807;border-radius:6px;transform-origin:100% 50%;display:grid;place-items:center;
  font:700 18px "JetBrains Mono",monospace;color:#5B524C;letter-spacing:.2em;font-style:normal}
/* define */
.dfn{width:952px;padding:40px 46px;display:flex;flex-direction:column;gap:10px}
.dfn .w{font:900 104px "Inter Tight";color:#fff;letter-spacing:-.04em;line-height:1;position:relative;display:inline-block}
.dfn .w i{position:absolute;left:0;right:0;bottom:-10px;height:8px;border-radius:4px;background:var(--o);transform-origin:0 50%}
.dfn .ph{font:600 32px "JetBrains Mono",monospace;color:#8C837C;margin-top:16px}
.dfn .pos{font:400 56px "Great Vibes";color:var(--o2)}
.dfn .df{font:600 40px/1.3 "Inter Tight";color:#E8E1DB}
/* pov */
.pov{display:flex;align-items:center;gap:20px;max-width:952px}
.pov b{padding:10px 22px;border-radius:14px;background:var(--grad);color:var(--ink);font:900 46px "Inter Tight";letter-spacing:.02em;flex:none}
.pov span{font:800 56px/1.12 "Inter Tight";color:#fff;text-shadow:0 0 2px rgba(0,0,0,.85),0 4px 18px rgba(0,0,0,.6)}
/* rank */
.rank{display:flex;align-items:center;gap:22px}
.rank .bd{position:relative;width:170px;height:170px;border-radius:50%;background:var(--grad);display:grid;place-items:center;box-shadow:0 0 50px rgba(255,106,0,.45)}
.rank .bd .v{display:inline-grid;font:900 92px "Inter Tight";color:var(--ink);letter-spacing:-.05em}.rank .bd .v span{grid-area:1/1}
.rank .of{display:flex;flex-direction:column;gap:12px}.rank .of b{font:700 30px "JetBrains Mono",monospace;color:#fff;letter-spacing:.12em}
.rank .dots{display:flex;gap:10px}.rank .dots i{width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,.2)}.rank .dots i.on{background:var(--o)}
/* ransom */
.rns{display:flex;flex-wrap:wrap;gap:14px;max-width:952px;justify-content:center}
.rns span{padding:8px 18px;border-radius:6px;font-size:80px;line-height:1.05;box-shadow:0 10px 24px rgba(0,0,0,.45)}
.rns .s0{background:#F4F1EA;color:#15110F;font-family:"Inter Tight";font-weight:900}
.rns .s1{background:var(--o);color:var(--ink);font-family:"Inter Tight";font-weight:900;text-transform:uppercase}
.rns .s2{background:#C9A27E;color:#2A1A10;font-family:"Playfair Display";font-weight:800;font-style:italic}
.rns .s3{background:#1B1513;color:#fff;font-family:"JetBrains Mono";font-weight:600}
.rns .s4{background:#fff;color:var(--o3);font-family:"Great Vibes";font-size:96px}
/* flip */
.flipw{perspective:1600px;width:860px;height:460px}
.flipc{position:relative;width:100%;height:100%;transform-style:preserve-3d}
.flipc .fa{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;border-radius:38px;padding:44px 50px;display:flex;flex-direction:column;gap:18px;justify-content:center}
.flipc .front{background:#1E1714;border:2px solid rgba(255,255,255,.12)}
.flipc .back{background:#1E1714;border:3px solid var(--o);transform:rotateY(180deg);box-shadow:0 0 60px rgba(255,106,0,.3)}
.flipc .lb{align-self:flex-start;padding:10px 22px;border-radius:12px;font:900 34px "Inter Tight";letter-spacing:.14em}
.flipc .front .lb{background:#3A332E;color:#D9D2CC}.flipc .back .lb{background:var(--grad);color:var(--ink)}
.flipc .tx{font:800 54px/1.2 "Inter Tight";color:#fff}
/* polaroid */
.pols{position:relative;width:952px;height:560px}
.pol{position:absolute;top:0;width:340px;padding:20px 20px 74px;background:#F6F3EE;border-radius:6px;box-shadow:0 18px 40px rgba(0,0,0,.45)}
.pol .ph{width:300px;height:300px;background:#2A221E center/cover no-repeat;display:grid;place-items:center;font:900 44px "Inter Tight";color:var(--o)}
.pol .cp{position:absolute;left:0;right:0;bottom:16px;text-align:center;font:400 46px "Great Vibes";color:#3A2A20}
.pol .tp{position:absolute;left:50%;top:-18px;width:120px;height:38px;margin-left:-60px;background:rgba(255,236,190,.75);transform:rotate(-3deg)}
/* achieve */
.ach{width:900px;height:200px;padding:0 34px;display:flex;align-items:center;gap:28px}
.ach .ic{position:relative;width:132px;height:132px;border-radius:50%;display:grid;place-items:center;flex:none;background:#241C18}
.ach .ic svg.rg{position:absolute;inset:0;width:132px;height:132px;transform:rotate(-90deg)}
.ach .ic svg.st{width:62px;height:62px;stroke:var(--o);fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.ach .tx{flex:1;display:flex;flex-direction:column;gap:10px}
.ach .k{font:700 26px "JetBrains Mono",monospace;color:var(--o2);letter-spacing:.16em}
.ach .t{font:900 50px "Inter Tight";color:#fff;letter-spacing:-.02em}
.ach .xp{height:14px;border-radius:7px;background:rgba(255,255,255,.12);overflow:hidden}.ach .xp i{display:block;height:100%;background:var(--grad);transform-origin:0 50%}
/* sticker */
.stk{position:absolute;padding:14px 30px;border-radius:22px;background:var(--o);color:var(--ink);font:900 72px "Inter Tight";letter-spacing:-.02em;text-transform:uppercase;
  box-shadow:0 0 0 12px #fff,10px 14px 0 12px rgba(0,0,0,.35);white-space:nowrap}
.stk.w{background:#fff;color:#15110F;box-shadow:0 0 0 12px var(--o),10px 14px 0 12px rgba(0,0,0,.35)}
/* burst */
.bst i{position:absolute;display:block;border-radius:3px}
/* rail */
.rail{display:flex;flex-direction:column;gap:20px}
.rail .st{display:flex;align-items:center;gap:20px;padding:14px 26px 14px 14px;border-radius:999px;background:rgba(12,9,8,.86);border:2px solid rgba(255,255,255,.12);color:#A39A93;font:800 34px "Inter Tight"}
.rail .st b{width:62px;height:62px;border-radius:50%;background:#2B231F;display:grid;place-items:center;font:900 32px "Inter Tight";color:#fff}
/* ff */
.ffb{display:flex;align-items:center;gap:18px;padding:16px 30px;border-radius:999px;background:rgba(12,9,8,.88);border:2px solid var(--o)}
.ffb svg{width:60px;height:60px;fill:var(--o)}
.ffb b{font:900 56px "Inter Tight";color:#fff}.ffb span{font:700 30px "JetBrains Mono",monospace;color:#A39A93;letter-spacing:.1em}
/* ===== next wave (2026-10-21) ===== */
.mxh{font:900 64px/1.08 "Inter Tight";letter-spacing:-.03em;word-spacing:.08em;color:#fff;text-align:center;max-width:872px;text-shadow:0 4px 18px rgba(0,0,0,.5)}
.mx .tx{position:absolute;inset:0;display:block;background-size:48px 48px;pointer-events:none}
.shimg{background:#141010 center/cover no-repeat}
/* generic app mock-up: stands in for a screenshot when no src is given (gallery samples) */
.mku{position:absolute;left:0;top:0;width:860px;height:560px;background:#141010;transform-origin:0 0;color:#E8E1DB;overflow:hidden;text-align:left;font-family:"Inter Tight"}
.mku-top{height:64px;display:flex;align-items:center;gap:26px;padding:0 26px;border-bottom:1px solid rgba(255,255,255,.08);background:#1B1513;font:700 22px "Inter Tight";color:#8C837C}
.mku-top i{width:30px;height:30px;border-radius:9px;background:var(--grad)}
.mku-top b{font:900 26px "Inter Tight";color:#fff;margin-right:14px}
.mku-top .on{color:#fff;padding:8px 16px;border-radius:999px;background:rgba(255,106,0,.16)}
.mku-top em{margin-left:auto;width:40px;height:40px;border-radius:50%;background:#3A332E}
.mku-side{position:absolute;left:0;top:64px;bottom:0;width:200px;padding:22px 16px;display:flex;flex-direction:column;gap:8px;border-right:1px solid rgba(255,255,255,.06)}
.mku-side div{padding:12px 16px;border-radius:12px;font:700 22px "Inter Tight";color:#8C837C}
.mku-side .on{background:rgba(255,255,255,.07);color:#fff}
.mku-main{position:absolute;left:236px;top:90px;right:34px;height:440px}
.mku-h{height:48px;margin-bottom:18px;font:900 40px "Inter Tight";color:#fff;letter-spacing:-.02em}
.mku-row{display:flex;justify-content:space-between;align-items:center;height:62px;border-bottom:1px solid rgba(255,255,255,.07);font:600 24px "Inter Tight";color:#A39A93}
.mku-row b{font:700 24px "JetBrains Mono",monospace;color:#fff}
.mku-tg{width:64px;height:36px;border-radius:18px;background:var(--o);position:relative}
.mku-tg:after{content:"";position:absolute;right:4px;top:4px;width:28px;height:28px;border-radius:50%;background:#fff}
.mku-btn{position:absolute;left:0;top:326px;width:300px;height:62px;border-radius:16px;background:var(--grad);display:grid;place-items:center;font:900 26px "Inter Tight";color:var(--ink)}
.mku-fine{position:absolute;left:0;top:450px;font:600 15px "JetBrains Mono",monospace;color:#6F6660;white-space:nowrap}
/* wipe */
.wp{position:absolute;border-radius:30px;overflow:hidden;background:#141010;box-shadow:0 0 0 2px rgba(255,255,255,.1),0 30px 80px rgba(0,0,0,.55)}
.wpl{position:absolute;inset:0;overflow:hidden}
.wpd{position:absolute;top:0;bottom:0;width:6px;margin-left:-3px;background:#fff;box-shadow:0 0 18px rgba(0,0,0,.45)}
.wpk{position:absolute;left:50%;top:50%;width:96px;height:96px;margin:-48px 0 0 -48px;border-radius:50%;background:#15110F;border:6px solid var(--o);display:grid;place-items:center;
  box-shadow:0 10px 30px rgba(0,0,0,.5)}
.wpk svg{width:54px;height:54px;fill:#fff}
.wpc{position:absolute;top:24px;padding:10px 20px;border-radius:12px;font:700 26px "JetBrains Mono",monospace;letter-spacing:.14em;background:rgba(12,9,8,.86);color:#fff}
.wpc.l{left:24px}.wpc.r{right:24px;background:var(--grad);color:var(--ink)}
.tmk{position:absolute;left:0;top:0;width:872px;height:872px;transform-origin:0 0;overflow:hidden}
.tmk i{position:absolute;display:block}
.tmk .hd{left:331px;top:430px;width:210px;height:210px;border-radius:50%}
.tmk .bd{left:186px;top:620px;width:500px;height:320px;border-radius:250px 250px 40px 40px}
.tmk .tt{position:absolute;left:0;right:0;text-align:center;white-space:nowrap}
.tmk.b{background:linear-gradient(180deg,#8E8882,#615C57)}
.tmk.b .hd,.tmk.b .bd{background:#4D4844}
.tmk.b .tt{top:190px;font:500 54px "Inter Tight";color:#E6E1DC}
.tmk.a{background:radial-gradient(560px 560px at 50% 62%,rgba(255,106,0,.55),transparent 72%),#0C0908}
.tmk.a .hd,.tmk.a .bd{background:#1B1513;box-shadow:0 0 0 6px var(--o),0 0 70px rgba(255,106,0,.55)}
.tmk.a .tt{top:130px;font:900 136px/1 "Inter Tight";color:#fff;letter-spacing:-.04em}
.tmk.a .tt b{color:var(--o)}
.tmk.a .st{position:absolute;right:70px;top:440px;padding:14px 28px;border-radius:18px;background:#fff;color:#15110F;font:900 60px "Inter Tight";transform:rotate(8deg);
  box-shadow:8px 10px 0 rgba(0,0,0,.35)}
/* loupe */
.lp-shot{position:absolute;border-radius:22px;overflow:hidden;box-shadow:0 0 0 2px rgba(255,255,255,.1),0 30px 80px rgba(0,0,0,.55)}
.lp-lens{position:absolute}
.lp-in{position:absolute;inset:0;border-radius:50%;overflow:hidden;background:#141010}
.lp-ring{position:absolute;inset:-6px;border-radius:50%;border:10px solid var(--o);box-shadow:0 24px 60px rgba(0,0,0,.6),0 0 40px rgba(255,106,0,.35)}
/* thread */
.thr{width:100%;display:flex;flex-direction:column}
.th-p{display:flex;gap:22px;padding:28px 30px 26px}
.th-v{width:70px;display:flex;flex-direction:column;align-items:center;gap:6px;flex:none;padding-top:4px}
.th-v svg{width:46px;height:46px;stroke:#8C837C;fill:none;stroke-width:2;stroke-linejoin:round}
.th-v .dn{transform:rotate(180deg)}
.th-v b{font:700 28px "JetBrains Mono",monospace;color:#fff;display:inline-grid}
.th-m{flex:1;min-width:0;display:flex;flex-direction:column;gap:12px}
.th-k{display:flex;align-items:center;gap:12px;font:600 26px "Inter Tight";color:#8C837C;white-space:nowrap}
.th-k i{width:38px;height:38px;border-radius:50%;background:var(--grad);flex:none}
.th-k b{color:#D9D2CC;font-weight:800}
.th-t{font:800 44px/1.18 "Inter Tight";color:#fff;letter-spacing:-.01em}
.th-b{font:500 34px/1.35 "Inter Tight";color:#D9D2CC}
.th-f{display:flex;gap:30px;font:700 26px "Inter Tight";color:#8C837C;padding-top:4px}
.th-f b{display:flex;align-items:center;gap:10px}.th-f svg{width:32px;height:32px;stroke:#8C837C;fill:none;stroke-width:2.2}
.th-rs{margin-left:100px;display:flex;flex-direction:column}
.th-r{position:relative;margin-top:18px}
.th-r .cn{position:absolute;left:-40px;top:-18px;width:34px;height:64px;border-left:4px solid rgba(255,255,255,.3);border-bottom:4px solid rgba(255,255,255,.3);border-bottom-left-radius:24px}
.th-r .cv{position:absolute;left:-40px;top:42px;bottom:-18px;width:4px;background:rgba(255,255,255,.3)}
.th-rc{padding:20px 28px;border-radius:26px;background:rgba(22,16,13,.94);border:2px solid rgba(255,140,60,.2);border-left:8px solid rgba(255,255,255,.14);
  box-shadow:0 18px 50px rgba(0,0,0,.45);display:flex;flex-direction:column;gap:8px}
.th-rc .th-k i{width:32px;height:32px;background:#5B524C}
.th-x{font:600 34px/1.3 "Inter Tight";color:#F4EFEA}
.th-rv{display:flex;align-items:center;gap:8px;font:700 24px "JetBrains Mono",monospace;color:#8C837C}
.th-rv svg{width:28px;height:28px;stroke:#8C837C;fill:none;stroke-width:2}
/* voicenote */
.vn-w{display:flex;flex-direction:column;gap:8px;align-items:flex-start}
.vn-s{font:700 24px "Inter Tight";color:#fff;text-shadow:0 0 2px rgba(0,0,0,.85),0 3px 14px rgba(0,0,0,.6);padding-left:18px}
.vn{position:relative;width:760px;height:132px;border-radius:44px 44px 44px 12px;background:rgba(31,24,21,.96);border:2px solid rgba(255,140,60,.3);
  box-shadow:0 20px 60px rgba(0,0,0,.5);display:flex;align-items:center;gap:20px;padding:0 28px 0 22px}
.vn-b{position:relative;width:84px;height:84px;border-radius:50%;background:var(--grad);flex:none;box-shadow:0 0 30px rgba(255,106,0,.45)}
.vn-b svg{position:absolute;left:50%;top:50%;width:38px;height:38px;margin:-19px 0 0 -19px;fill:var(--ink)}
.vn-wv{position:relative;flex:1;height:72px}
.vn-wv .ly{position:absolute;inset:0;display:flex;align-items:center;justify-content:space-between}
.vn-wv i{display:block;width:5px;border-radius:3px;background:#5B524C}
.vn-wv .ly.o i{background:var(--o)}
.vn-d{font:700 28px "JetBrains Mono",monospace;color:#D9D2CC;display:inline-grid;flex:none;min-width:80px;justify-items:end}
.vn-d span{grid-area:1/1}
/* feed */
.fdw{position:absolute;width:500px;height:1010px;transform-origin:0 0}
.fdp{position:absolute;inset:0;border-radius:72px;background:#0A0807;border:3px solid #3A332E;box-shadow:0 0 0 2px #15110F,0 40px 90px rgba(0,0,0,.6);padding:14px}
.fds{position:relative;width:100%;height:100%;border-radius:58px;background:#120E0C;overflow:hidden}
.fdst{position:absolute;left:0;right:0;top:0;height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 42px;font:800 22px "Inter Tight";color:#fff;z-index:2;
  background:linear-gradient(180deg,#120E0C 70%,rgba(18,14,12,0))}
.fdst i{position:absolute;left:50%;top:12px;width:130px;height:36px;margin-left:-65px;border-radius:18px;background:#000}
.fdst u{width:36px;height:17px;border-radius:5px;border:2px solid #fff;position:relative}
.fdst u:after{content:"";position:absolute;left:2px;top:2px;bottom:2px;width:60%;border-radius:2px;background:#fff}
.fdv{position:absolute;left:0;right:0;top:56px;bottom:0;overflow:hidden}
.fdl{position:absolute;left:16px;right:16px;top:16px;display:flex;flex-direction:column;gap:20px}
.fd-c{height:400px;border-radius:30px;background:#1E1714;border:2px solid rgba(255,255,255,.08);overflow:hidden;display:flex;flex-direction:column;flex:none}
.fd-h{height:78px;display:flex;align-items:center;gap:14px;padding:0 20px;flex:none}
.fd-h i{width:48px;height:48px;border-radius:50%;flex:none}
.fd-h b{display:block;font:800 22px "Inter Tight";color:#fff}.fd-h span{display:block;font:600 18px "Inter Tight";color:#8C837C}
.fd-m{flex:1;margin:0 14px;border-radius:20px;display:flex;align-items:flex-end;padding:22px;font:900 40px/1.05 "Inter Tight";color:#fff;letter-spacing:-.02em;text-shadow:0 3px 16px rgba(0,0,0,.35)}
.fd-m.lt{color:#15110F;text-shadow:none}
.fd-f{height:64px;display:flex;align-items:center;gap:26px;padding:0 22px;font:700 20px "JetBrains Mono",monospace;color:#A39A93;flex:none}
.fd-f b{display:flex;align-items:center;gap:8px}.fd-f svg{width:26px;height:26px;stroke:#A39A93;fill:none;stroke-width:2.2}
/* receipt */
.rcw{position:absolute}
.rc-slot{position:relative;height:26px;margin:0 -24px;border-radius:13px;background:linear-gradient(180deg,#3A332E,#15110F);box-shadow:0 10px 24px rgba(0,0,0,.5);z-index:2}
.rc{position:relative;margin-top:-10px}
.rc-p{position:relative;background:#F4F1EA;color:#2A211C;padding:26px 30px 14px;font:600 26px "JetBrains Mono",monospace}
.rc-p .tx{opacity:.12;mix-blend-mode:multiply}
.rc-h{position:relative;height:52px;text-align:center;font:800 34px "JetBrains Mono",monospace;letter-spacing:.06em;color:#15110F;white-space:nowrap}
.rc-m{position:relative;height:36px;text-align:center;font:600 20px "JetBrains Mono",monospace;color:#6F6660;white-space:nowrap}
.rc-ds{height:28px;display:flex;align-items:center}.rc-ds i{flex:1;border-top:3px dashed #B8AEA4}
.rc-l{position:relative;height:48px;display:flex;justify-content:space-between;align-items:center;white-space:nowrap;gap:16px}
.rc-l b{font-weight:800;color:#15110F}
.rc-t{position:relative;height:74px;display:flex;justify-content:space-between;align-items:center;font:800 40px "JetBrains Mono",monospace;color:var(--o)}
.rc-f{position:relative;height:86px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.rc-bc{display:flex;gap:3px;height:40px}.rc-bc i{display:block;background:#2A211C}
.rc-f span{font:600 17px "JetBrains Mono",monospace;color:#6F6660;letter-spacing:.12em}
.rc-zz{display:block}
.rc-pd{position:absolute;right:26px;bottom:8px;padding:4px 22px;border:7px solid var(--o);border-radius:14px;color:var(--o);font:900 62px "Inter Tight";letter-spacing:.06em;
  transform:rotate(-8deg);background:rgba(244,241,234,.5)}
/* venn */
.vl{position:absolute;width:0;height:0}
.vl span{position:absolute;left:0;top:0;transform:translate(-50%,-50%);white-space:nowrap;font-weight:800;color:#fff;text-align:center;text-shadow:0 2px 10px rgba(0,0,0,.6)}
.vl.c span{padding:12px 26px;border-radius:999px;background:var(--grad);color:var(--ink);font:900 36px "Inter Tight";text-shadow:none;box-shadow:0 0 40px rgba(255,106,0,.5)}
/* cloud */
.cld span{position:absolute;white-space:nowrap;line-height:1.08;color:#fff;letter-spacing:-.01em;text-shadow:0 0 2px rgba(0,0,0,.85),0 4px 18px rgba(0,0,0,.55)}
.cld span.d2{color:#D9D2CC}.cld span.pk{z-index:2}
/* slot */
.slt{display:flex;flex-direction:column;gap:6px;padding:10px 20px 8px;border-radius:32px;background:linear-gradient(180deg,#2B231F,#15110F);border:3px solid rgba(255,106,0,.55);
  box-shadow:0 0 30px rgba(255,106,0,.25),0 20px 50px rgba(0,0,0,.5)}
.slt .k{font:800 22px/1.2 "Inter Tight";letter-spacing:.16em;color:var(--o2);text-transform:uppercase;text-align:center}
.slr{display:flex;gap:16px}
.slc{display:flex;flex-direction:column;gap:4px}
.slw{position:relative;height:96px;border-radius:18px;background:#0C0908;overflow:hidden;box-shadow:inset 0 0 0 2px rgba(255,255,255,.08)}
.slw:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(12,9,8,.92) 0%,rgba(12,9,8,0) 32%,rgba(12,9,8,0) 68%,rgba(12,9,8,.92) 100%)}
.slw b{position:absolute;top:50%;width:10px;height:28px;margin-top:-14px;background:var(--o);z-index:2}
.slw b.l{left:0;border-radius:0 6px 6px 0}.slw b.r{right:0;border-radius:6px 0 0 6px}
.sls{position:absolute;left:0;right:0;top:0}
.sls div{height:96px;display:grid;place-items:center;font-family:"Inter Tight";font-weight:900;color:#fff;white-space:nowrap;letter-spacing:-.02em}
.slc .lb{font:700 16px/1.2 "JetBrains Mono",monospace;color:#8C837C;letter-spacing:.14em;text-align:center}
/* tear */
.tr{position:relative;overflow:hidden;border-radius:8px}
.tr-h{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:0 40px;border-radius:26px;background:rgba(22,16,13,.95);border:2px solid rgba(255,140,60,.32);
  font:900 72px/1.05 "Inter Tight";letter-spacing:-.03em;color:#fff;text-align:center}
.tr-hw{position:absolute;inset:0;filter:drop-shadow(0 8px 12px rgba(0,0,0,.4))}
.tr-pp{position:absolute;inset:0;background:#EFE6D8}
.tr-pp .tx,.tr-st .tx{opacity:.14;mix-blend-mode:multiply}
.tr-pp svg{position:absolute;left:0;top:0;overflow:visible}
.tr-cv{position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);text-align:center;font:400 86px/1.2 "Great Vibes";color:#3A2A20}
.tr-sw{filter:drop-shadow(0 10px 14px rgba(0,0,0,.4))}
.tr-st{position:relative;display:flex;align-items:center;justify-content:center;background:#EFE6D8;font:900 64px/1.05 "Inter Tight";color:#15110F;letter-spacing:-.02em;white-space:nowrap}
.tr-st span{position:relative}
/* board */
.bd-cam{position:absolute;left:0;top:0;width:1080px;height:1920px}
.bd-dr{position:absolute;inset:0}
.bd-bg{position:absolute;inset:-40px;background:radial-gradient(900px 760px at 50% 45%,#2A211C 0%,#1A1412 70%,#120E0C 100%)}
.bd-bg .tx{opacity:.22;mix-blend-mode:overlay}
.bd-it{position:absolute}
.bdc{width:100%;height:100%;padding:24px 26px;border-radius:14px;background:#241C18;border:2px solid rgba(255,255,255,.1);box-shadow:0 18px 34px rgba(0,0,0,.55);display:flex;flex-direction:column;gap:10px}
.bdc .ic{width:64px;height:64px;border-radius:16px;background:var(--grad);display:grid;place-items:center}
.bdc .ic svg{width:36px;height:36px;stroke:var(--ink);fill:none;stroke-width:2.3;stroke-linecap:round;stroke-linejoin:round}
.bdc b{font:900 40px "Inter Tight";color:#fff;letter-spacing:-.02em;white-space:nowrap}
.bdc span{font:600 24px "Inter Tight";color:#A39A93}
.bdn{width:100%;height:100%;padding:30px 24px;background:#F4F1EA;box-shadow:0 18px 30px rgba(0,0,0,.5);font:800 40px/1.12 "Inter Tight";color:#15110F;display:flex;align-items:center;justify-content:center;text-align:center}
.bdp{width:100%;height:100%;padding:18px 18px 0;background:#F6F3EE;box-shadow:0 18px 30px rgba(0,0,0,.5)}
.bdp .ph{width:234px;height:234px;background:#2A221E center/cover no-repeat;display:grid;place-items:center}
.bdp .ph svg{width:96px;height:96px;stroke:var(--o);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bdp .cp{text-align:center;font:400 50px/78px "Great Vibes";color:#3A2A20}
.bd-pin{position:absolute;display:block;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFB27A 0%,#FF6A00 45%,#9A3D00 100%);
  box-shadow:0 6px 10px rgba(0,0,0,.55)}
/* dock (glass = the graphic's own gradient fill; never a backdrop blur over the footage) */
.dk{position:relative;display:flex;align-items:flex-end;gap:16px;padding:16px 20px;border-radius:32px;background:linear-gradient(180deg,rgba(255,255,255,.30),rgba(255,255,255,.10));
  border:1.5px solid rgba(255,255,255,.5);box-shadow:inset 0 1px 0 rgba(255,255,255,.7),inset 0 -1px 0 rgba(255,255,255,.15),0 22px 50px rgba(0,0,0,.35)}
.dk:before{content:"";position:absolute;left:24px;right:24px;top:4px;height:42%;border-radius:30px 30px 60px 60px;background:linear-gradient(180deg,rgba(255,255,255,.32),rgba(255,255,255,0))}
.dk-t{position:relative;width:76px;height:76px;transform-origin:50% 100%}
.dk-i{width:76px;height:76px;border-radius:20px;display:grid;place-items:center;box-shadow:0 8px 18px rgba(0,0,0,.35)}
.dk-i svg{width:42px;height:42px;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.dk-dot{position:absolute;left:50%;bottom:-10px;width:8px;height:8px;margin-left:-4px;border-radius:50%;background:#fff;opacity:0}
.dk-lb{position:absolute;top:100%;margin-top:10px;width:0;height:0}
.dk-lb span{position:absolute;left:0;top:0;transform:translateX(-50%);white-space:nowrap;padding:8px 20px;border-radius:999px;background:var(--grad);color:var(--ink);font:800 24px "Inter Tight";
  box-shadow:0 12px 34px rgba(0,0,0,.45)}
/* frame3d */
.f3-grid{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.10) 1.5px,transparent 2px);background-size:40px 40px}
.f3w{position:absolute;perspective:2200px}
.f3{position:absolute;inset:0;border-radius:24px;overflow:hidden;background:#1B1513;box-shadow:0 0 0 1.5px rgba(255,106,0,.6),0 0 60px rgba(255,106,0,.25),0 70px 120px rgba(0,0,0,.7)}
.f3-bar{height:48px;display:flex;align-items:center;gap:10px;padding:0 20px;background:#221A17;border-bottom:1px solid rgba(255,255,255,.07)}
.f3-bar i{width:15px;height:15px;border-radius:50%;background:#5B524C;flex:none}
.f3-bar i:nth-child(1){background:#E5484D}.f3-bar i:nth-child(2){background:#F5A524}.f3-bar i:nth-child(3){background:#30A46C}
.f3-url{margin:0 auto;padding:6px 26px;border-radius:999px;background:#120E0C;font:600 18px "JetBrains Mono",monospace;color:#A39A93;display:flex;align-items:center;gap:8px}
.f3-url svg{width:16px;height:16px;stroke:#A39A93;fill:none;stroke-width:2.4}
.f3.ph{border-radius:64px;padding:14px;background:#0A0807;border:3px solid #3A332E}
.f3.ph .f3-scr{border-radius:52px;overflow:hidden;height:100%}
"""

JS = r"""
// ===== v7 catalog runtime (deterministic: fixed seeds, finite repeats, stepped where it should feel handmade)
const S7 = (q, f) => document.querySelectorAll(q).forEach(f);
S7("[data-draw7]", (el) => { const L = el.getTotalLength(), t = N(el, "draw7", 0), d = N(el, "dd", .45);
  gsap.set(el, { strokeDasharray: L, strokeDashoffset: L }); tl.to(el, { strokeDashoffset: 0, duration: d, ease: "power2.out" }, t);
  if (D > 1) tl.to(el, { opacity: 0, duration: .18, ease: "power2.in" }, D - .22); });
S7("[data-boil]", (g) => {  // marker boil: swap 3 jittered copies every 2 frames while it is held
  const v = g.querySelectorAll(".bv"), t0 = N(g, "boil", 0) + .5; if (v.length < 2) return;
  for (let k = 0, t = t0; t < D - .3 && k < 400; k++, t += 2 / 30) v.forEach((p, i) => tl.set(p, { opacity: i === k % v.length ? 1 : 0 }, t)); });
S7("[data-ring7]", (el) => { const t = N(el, "ring7", 0); gsap.set(el, { opacity: 0, transformOrigin: "50% 50%" });  // ping rings: 2 cycles, staggered (SVG: GSAP origin = the ring's own centre)
  for (let c = 0; c < 2; c++) tl.fromTo(el, { scale: .15, opacity: 1 }, { scale: 1, opacity: 0, duration: .6, ease: "expo.out", immediateRender: false }, t + c * .75 + N(el, "rd", 0)); });
S7("[data-press]", (el) => { const t = N(el, "press", 0);
  tl.to(el, { y: 8, scale: .94, boxShadow: "0 2px 0 #0C0908,0 8px 18px rgba(0,0,0,.5)", duration: .08, ease: "power2.out" }, t);
  tl.to(el, { y: 0, scale: 1, duration: .16, ease: "power2.out", clearProps: "boxShadow" }, t + .12); });
S7(".isl", (el) => { const t = N(el, "isl", 0), sub = el.querySelectorAll(".ic,.tx,.tm");
  tl.fromTo(el, { width: 300, height: 88, marginLeft: -150, borderRadius: 44, scale: .6, opacity: 0 }, { scale: 1, opacity: 1, duration: .2, ease: "back.out(1.8)" }, t);
  tl.to(el, { width: 960, height: 210, marginLeft: -480, borderRadius: 58, duration: .5, ease: "expo.out" }, t + .2);
  tl.from(sub, { y: 12, opacity: 0, duration: .3, stagger: .05, ease: "power3.out" }, t + .35);
  if (D > 2) { tl.to(sub, { opacity: 0, duration: .15 }, D - .55); tl.to(el, { width: 300, height: 88, marginLeft: -150, borderRadius: 44, duration: .35, ease: "power3.in" }, D - .5);
    tl.to(el, { opacity: 0, scale: .8, duration: .15 }, D - .15); } });
S7("[data-typeq]", (el) => { const t = N(el, "typeq", 0), sp = el.querySelectorAll("span");  // typed query, one char at a time
  sp.forEach((s, i) => tl.from(s, { opacity: 0, duration: .01 }, t + i * .045)); });
S7("[data-blink]", (el) => { const t = N(el, "blink", 0); for (let k = 0; k < 4; k++) tl.set(el, { opacity: k % 2 ? 1 : 0 }, t + k * .25); });
S7("[data-sug]", (el) => { const t = N(el, "sug", 0);
  tl.from(el, { height: 0, opacity: 0, duration: .3, ease: "power3.out" }, t);
  tl.from(el.children, { x: -20, opacity: 0, duration: .25, stagger: .06, ease: "power3.out" }, t + .08); });
S7("[data-pick7]", (el) => { tl.to(el, { borderLeftColor: "#FF6A00", backgroundColor: "rgba(255,106,0,.10)", color: "#15110F", duration: .2 }, N(el, "pick7", 0)); });
S7("[data-words]", (el) => { const t = N(el, "words", 0), sp = el.querySelectorAll("span");
  tl.from(sp, { opacity: 0, y: 10, duration: .25, stagger: .04, ease: "power2.out" }, t); });
S7("[data-heart]", (el) => { const t = N(el, "heart", 0), p = el.querySelector("svg");
  tl.to(p, { fill: "#FF6A00", stroke: "#FF6A00", duration: .1 }, t);
  tl.fromTo(p, { scale: .6 }, { scale: 1, duration: .35, ease: "back.out(2.4)" }, t); });
S7("[data-pulse7]", (el) => { const t = N(el, "pulse7", 0);
  for (let c = 0; c < 3; c++) tl.fromTo(el, { scale: 1, opacity: .9 }, { scale: 1.35, opacity: 0, duration: .6, ease: "power2.out", immediateRender: false }, t + c * .7); });
S7("[data-tile]", (el) => { tl.from(el, { y: 300, rotation: 6, opacity: 0, duration: .45, ease: "back.out(1.6)" }, N(el, "tile", 0)); });
S7("[data-star]", (el) => { const t = N(el, "star", 0); tl.set(el, { className: "f" }, t); tl.fromTo(el, { scale: .6 }, { scale: 1, duration: .2, ease: "back.out(2)" }, t); });
S7("[data-strike7]", (el) => { const L = el.getTotalLength(); gsap.set(el, { strokeDasharray: L, strokeDashoffset: L });
  tl.to(el, { strokeDashoffset: 0, duration: .25, ease: "power2.out" }, N(el, "strike7", 0)); });
S7("[data-slam]", (el) => { tl.from(el, { scale: 1.3, opacity: 0, duration: .3, ease: "power4.out" }, N(el, "slam", 0)); });
S7("[data-badge]", (el) => { tl.from(el, { rotation: -30, scale: .6, opacity: 0, duration: .3, ease: "back.out(2)" }, N(el, "badge", 0)); });
S7("[data-arc]", (el) => {  // ring / timer arc: draw to its share
  const L = el.getTotalLength(), t = N(el, "arc", 0), p = N(el, "p", 1), mode = el.dataset.mode;
  gsap.set(el, { strokeDasharray: L, strokeDashoffset: L });
  if (mode === "deplete") { tl.to(el, { strokeDashoffset: 0, duration: .5, ease: "power2.out" }, t); tl.to(el, { strokeDashoffset: L, duration: Math.max(.5, D - t - .9), ease: "none" }, t + .5); }
  else tl.to(el, { strokeDashoffset: L * (1 - p), duration: N(el, "ad", .8), ease: "power3.out" }, t); });
S7("[data-steps7]", (el) => {  // stacked values (timer digits / rank numerals): swap at fixed times
  const sp = el.querySelectorAll("span"), ts = el.dataset.steps7.split(",").map(parseFloat);
  sp.forEach((s, i) => gsap.set(s, { opacity: i ? 0 : 1 }));
  ts.forEach((t, i) => { if (i + 1 < sp.length) { tl.set(sp[i], { opacity: 0 }, t); tl.set(sp[i + 1], { opacity: 1 }, t);
    if (el.dataset.flipnum !== undefined) tl.fromTo(sp[i + 1], { rotationX: 90 }, { rotationX: 0, duration: .2, ease: "power2.out" }, t); } }); });
S7("[data-area]", (el) => { tl.from(el, { opacity: 0, duration: .4 }, N(el, "area", 0)); });
S7("[data-popin]", (el) => { tl.from(el, { scale: 0, opacity: 0, duration: .3, ease: "back.out(2)" }, N(el, "popin", 0)); });
S7("[data-grow7]", (el) => { tl.from(el, { scaleX: 0, transformOrigin: "0 50%", duration: N(el, "gd", .6), ease: "power2.inOut" }, N(el, "grow7", 0)); });
S7("[data-cell]", (el) => { const t = N(el, "cell", 0); tl.set(el, { className: el.className + " on" }, t); tl.fromTo(el, { scale: .8 }, { scale: 1, duration: .2, ease: "power2.out" }, t); });
S7("[data-flapcell]", (el) => {  // split-flap: letters flip through, settle on the target
  const sp = el.querySelectorAll("span"), t = N(el, "flapcell", 0);
  sp.forEach((s, i) => { gsap.set(s, { opacity: 0 }); tl.set(s, { opacity: 1 }, t + i * .04); if (i + 1 < sp.length) tl.set(s, { opacity: 0 }, t + (i + 1) * .04);
    tl.fromTo(s, { rotationX: -80 }, { rotationX: 0, duration: .035, ease: "none", immediateRender: false }, t + i * .04); });
  tl.to(el, { keyframes: { y: [0, -2, 2, 0] }, duration: .07, ease: "none" }, t + sp.length * .04); });
S7("[data-glitch]", (el) => {  // RGB split + slices, stepped, settles clean; micro-glitch at fixed times
  const t = N(el, "glitch", 0), r = el.querySelector(".r"), c = el.querySelector(".c"), b = el.querySelector(".base");
  gsap.set([r, c], { clipPath: "inset(0 0 100% 0)" });
  const off = [[-12, 9, "inset(8% 0 62% 0)"], [10, -7, "inset(40% 0 30% 0)"], [-6, 11, "inset(66% 0 6% 0)"], [8, -5, "inset(20% 0 52% 0)"], [-4, 4, "inset(52% 0 22% 0)"], [3, -2, "inset(0 0 0 0)"]];
  tl.from(el, { opacity: 0, duration: .01 }, t);
  off.forEach(([x1, x2, cp], i) => { const tt = t + i * 2 / 30; tl.set(r, { x: x1, clipPath: cp }, tt); tl.set(c, { x: x2, clipPath: cp }, tt); tl.set(b, { x: i % 2 ? -3 : 3 }, tt); });
  const tc0 = t + off.length * 2 / 30; tl.set([r, c], { x: 0, clipPath: "inset(0 0 100% 0)" }, tc0); tl.set(b, { x: 0 }, tc0);
  for (let m = tc0 + 1.6; m < D - .5; m += 1.8) { tl.set(r, { x: -8, clipPath: "inset(30% 0 45% 0)" }, m); tl.set(c, { x: 7, clipPath: "inset(30% 0 45% 0)" }, m);
    tl.set([r, c], { x: 0, clipPath: "inset(0 0 100% 0)" }, m + 2 / 30); } });
S7("[data-unbar]", (el) => { tl.to(el, { scaleX: 0, duration: .3, ease: "power3.inOut" }, N(el, "unbar", 0)); });
S7("[data-drop7]", (el) => { tl.from(el, { scale: 1.3, rotation: N(el, "rot", 0) + 14, opacity: 0, duration: .22, ease: "expo.out" }, N(el, "drop7", 0)); });
S7("[data-flip7]", (el) => { const t = N(el, "flip7", 0);
  tl.to(el, { rotationY: 180, duration: .7, ease: "power2.inOut" }, t);
  tl.to(el, { keyframes: { scale: [1, 1.05, 1] }, duration: .7, ease: "power2.inOut" }, t); });
S7("[data-pol]", (el) => { tl.from(el, { scale: 1.25, y: -60, rotation: 0, opacity: 0, duration: .45, ease: "power3.out" }, N(el, "pol", 0)); });
S7("[data-slide7]", (el) => { const t = N(el, "slide7", 0); tl.from(el, { xPercent: -120, opacity: 0, duration: .4, ease: "expo.out" }, t);
  if (D > 1.2) tl.to(el, { x: -40, opacity: 0, duration: .25, ease: "power2.in" }, D - .3); });
S7("[data-sweep]", (el) => { const L = el.getTotalLength(); gsap.set(el, { strokeDasharray: L, strokeDashoffset: L });
  tl.to(el, { strokeDashoffset: 0, duration: .6, ease: "power2.out" }, N(el, "sweep", 0)); });
S7("[data-slap]", (el) => { const t = N(el, "slap", 0), r = N(el, "rot", -6);
  tl.fromTo(el, { scale: 1.4, rotation: r + (r < 0 ? -18 : 18), opacity: 0 }, { scale: 1, rotation: r, opacity: 1, duration: .32, ease: "back.out(2.2)" }, t);
  if (D > 1) tl.to(el, { scale: .8, opacity: 0, duration: .15 }, D - .18); });
S7("[data-conf]", (el) => {  // confetti: precomputed ballistic keyframes (seeded in Python)
  const t = N(el, "conf", 0), k = JSON.parse(el.dataset.k);
  tl.fromTo(el, { x: 0, y: 0, rotation: 0, opacity: 1 }, { keyframes: k, duration: 1.2, ease: "none", immediateRender: false }, t); gsap.set(el, { opacity: 0 }); });
S7("[data-railon]", (el) => { tl.to(el, { color: "#FFFFFF", borderColor: "#FF6A00", backgroundColor: "rgba(255,106,0,.14)", duration: .25 }, N(el, "railon", 0));
  tl.to(el.querySelector("b"), { backgroundColor: "#FF6A00", color: "#1A0B04", duration: .25 }, N(el, "railon", 0)); });
S7("[data-railoff]", (el) => { tl.to(el, { color: "#5B524C", borderColor: "rgba(255,255,255,.08)", backgroundColor: "rgba(12,9,8,.6)", duration: .25 }, N(el, "railoff", 0)); });
// ----- next wave (2026-10-21)
S7("[data-wipe]", (el) => {  // before/after: the AFTER side wipes across, overshoots back to the middle, the knob pulses once
  const t = N(el, "wipe", 0), a = el.querySelector(".wpa"), d = el.querySelector(".wpd"), k = el.querySelector(".wpk");
  tl.to(a, { clipPath: "inset(0% 0% 0% 0%)", duration: 1.1, ease: "power2.inOut" }, t); tl.to(d, { left: "0%", duration: 1.1, ease: "power2.inOut" }, t);
  tl.to(a, { clipPath: "inset(0% 0% 0% 50%)", duration: .5, ease: "power3.out" }, t + 1.1); tl.to(d, { left: "50%", duration: .5, ease: "power3.out" }, t + 1.1);
  tl.to(k, { keyframes: { scale: [1, 1.18, 1] }, duration: .35, ease: "power2.inOut" }, t + 1.65); });
S7("[data-lens]", (el) => {  // loupe: grows out of the target while it travels to its free spot, shrinks back at the end
  const t = N(el, "lens", 0), dx = N(el, "dx", 0), dy = N(el, "dy", 0);
  tl.fromTo(el, { x: dx, y: dy }, { x: 0, y: 0, duration: .45, ease: "expo.out" }, t);
  tl.fromTo(el, { scale: .2, opacity: 0 }, { scale: 1, opacity: 1, duration: .4, ease: "back.out(1.6)" }, t);
  if (D > t + 1.2) tl.to(el, { x: dx, y: dy, scale: .2, opacity: 0, duration: .3, ease: "power3.in" }, D - .42); });
S7("[data-down7]", (el) => { tl.fromTo(el, { clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: .3, ease: "power2.out" }, N(el, "down7", 0)); });
S7("[data-edge7]", (el) => { tl.to(el, { borderLeftColor: "#FF6A00", boxShadow: "0 18px 50px rgba(0,0,0,.45),0 0 40px rgba(255,106,0,.22)", duration: .2 }, N(el, "edge7", 0)); });
S7("[data-upv]", (el) => { tl.to(el, { stroke: "#FF6A00", fill: "#FF6A00", duration: .15 }, N(el, "upv", 0)); });
S7("[data-vbar]", (el) => { const t = N(el, "vbar", 0);  // voice note: bars grow from the middle line, both layers in step
  el.querySelectorAll(".ly").forEach((ly) => tl.from(ly.children, { scaleY: 0, duration: .3, ease: "power3.out", stagger: .012 }, t)); });
S7("[data-vprog]", (el) => { tl.to(el, { clipPath: "inset(0% 0% 0% 0%)", duration: N(el, "len", 1), ease: "none" }, N(el, "vprog", 0)); });
S7("[data-vplay]", (el) => { const t = N(el, "vplay", 0), p = el.querySelector(".pl"), q = el.querySelector(".pa");
  tl.to(el, { keyframes: { scale: [1, .9, 1] }, duration: .18, ease: "power2.out" }, t);
  tl.to(p, { opacity: 0, scale: .6, duration: .2 }, t); tl.fromTo(q, { opacity: 0, scale: .6 }, { opacity: 1, scale: 1, duration: .2, immediateRender: false }, t); });
S7("[data-phone7]", (el) => { const t = N(el, "phone7", 0);  // feed phone: rises in, drops out
  tl.from(el, { y: 120, opacity: 0, duration: .5, ease: "expo.out" }, t);
  if (D > 1.5) tl.to(el, { y: 60, opacity: 0, duration: .3, ease: "power2.in" }, D - .32); });
S7("[data-flicks]", (el) => { JSON.parse(el.dataset.flicks).forEach(([t, y]) => tl.to(el, { y, duration: .45, ease: "power4.out" }, t)); });
S7("[data-hl7]", (el) => { tl.to(el, { scale: 1.04, borderColor: "#FF6A00", boxShadow: "0 0 0 5px #FF6A00,0 0 50px rgba(255,106,0,.45)", duration: .25, ease: "power2.out" }, N(el, "hl7", 0)); });
S7("[data-print]", (el) => {  // receipt: the paper extends one line at a time (stepped), jittering on twos while it prints
  const st = JSON.parse(el.dataset.print), t0 = st[0][0], t1 = st[st.length - 1][0] + .1;
  st.forEach(([t, b]) => tl.set(el, { clipPath: `inset(0px 0px ${b}px 0px)` }, t));
  for (let k = 0, t = t0; t < t1 && k < 200; k++, t += 2 / 30) tl.set(el, { y: [0, 1.5, -1, 1, -1.5, .5][k % 6] }, t);
  tl.set(el, { y: 0 }, t1 + 2 / 30); });
S7("[data-tot7]", (el) => { tl.fromTo(el, { scale: 1.15 }, { scale: 1, duration: .25, ease: "power2.out", immediateRender: false }, N(el, "tot7", 0)); });
S7("[data-vin]", (el) => { tl.from(el, { x: N(el, "dx", 0), y: N(el, "dy", 0), opacity: 0, duration: .6, ease: "power3.inOut" }, N(el, "vin", 0)); });
S7("[data-ov]", (el) => { const t = N(el, "ov", 0); gsap.set(el, { svgOrigin: el.dataset.o });  // venn overlap fills in
  tl.from(el, { opacity: 0, scale: .7, duration: .3, ease: "power2.out" }, t); });
S7("[data-cw]", (el) => { tl.from(el, { x: N(el, "dx", 0), y: N(el, "dy", 0), opacity: 0, filter: "blur(12px)", duration: .5, ease: "expo.out" }, N(el, "cw", 0)); });
S7("[data-cpick]", (el) => { tl.to(el, { scale: 1.2, color: "#FF6A00", duration: .3, ease: "power2.out" }, N(el, "cpick", 0)); });
S7("[data-cdim]", (el) => { tl.to(el, { opacity: .38, duration: .3 }, N(el, "cdim", 0)); });
S7("[data-reel]", (el) => {  // slot reel: precomputed strip, power4.out so it slows onto the pick; the window bumps on landing
  const t = N(el, "reel", 0), d = N(el, "rdur", 1.4), y = N(el, "ry", 0), w = el.parentElement;
  tl.fromTo(el, { y: 0 }, { y, duration: d, ease: "power4.out" }, t);
  tl.fromTo(el, { filter: "blur(3px)" }, { filter: "blur(0px)", duration: d * .7, ease: "power2.in" }, t);
  tl.fromTo(w, { scale: 1.06 }, { scale: 1, duration: .2, ease: "power2.out", immediateRender: false }, t + d);
  tl.to(el.lastElementChild, { color: "#FF6A00", duration: .15 }, t + d); });
S7("[data-flash7]", (el) => { const t = N(el, "flash7", 0);
  tl.to(el, { borderColor: "#FF6A00", boxShadow: "0 0 0 3px #FF6A00,0 0 60px rgba(255,106,0,.55),0 20px 50px rgba(0,0,0,.5)", duration: .08 }, t);
  tl.to(el, { borderColor: "rgba(255,106,0,.55)", boxShadow: "0 0 30px rgba(255,106,0,.25),0 20px 50px rgba(0,0,0,.5)", duration: .3 }, t + .15); });
S7("[data-tear]", (el) => {  // torn halves pull apart, stepped on twos (power3.out envelope), and leave the window
  const t = N(el, "tear", 0), dy = N(el, "dy", 140), r = N(el, "rot", 3);
  for (let k = 1; k <= 8; k++) { const p = 1 - Math.pow(1 - k / 8, 3);
    tl.set(el, { y: dy * p, rotation: r * p, opacity: k > 5 ? 1 - (k - 5) / 3 : 1 }, t + k * 2 / 30); } });
S7("[data-strip7]", (el) => { const t = N(el, "strip7", 0);  // torn strip slides in, 2° overshoot, settles
  tl.fromTo(el, { xPercent: -115, rotation: -3 }, { xPercent: 0, rotation: 1.5, duration: .4, ease: "power3.out" }, t);
  tl.to(el, { rotation: 0, duration: .22, ease: "power2.out" }, t + .4); });
S7("[data-pin7]", (el) => { tl.fromTo(el, { scale: 1.15, rotation: 0, opacity: 0 }, { scale: 1, rotation: N(el, "rot", 0), opacity: 1, duration: .35, ease: "power3.out" }, N(el, "pin7", 0)); });
S7("[data-cam]", (el) => {  // board camera: pans / zooms between clusters; the slow drift lives on the inner layer
  const k = JSON.parse(el.dataset.cam); gsap.set(el, { x: k[0][1], y: k[0][2], scale: k[0][3], transformOrigin: "0 0" });
  k.slice(1).forEach(([t, x, y, s]) => tl.to(el, { x, y, scale: s, duration: .8, ease: "power2.inOut" }, t)); });
S7("[data-drift]", (el) => { tl.fromTo(el, { scale: 1 }, { scale: 1.03, duration: D, ease: "none" }, 0); });
S7("[data-mag]", (el) => { tl.to(el, { keyframes: { scale: [1, 1.3, 1] }, duration: .36, ease: "power2.inOut" }, N(el, "mag", 0)); });
S7("[data-dpick]", (el) => { const t = N(el, "dpick", 0);  // dock: the chosen tool grows, rings orange, its dot lights
  tl.to(el, { scale: 1.25, duration: .25, ease: "power2.out" }, t);
  tl.to(el.querySelector(".dk-i"), { boxShadow: "0 0 0 5px #FF6A00,0 0 18px rgba(255,106,0,.55)", duration: .25 }, t);
  tl.to(el.querySelector(".dk-dot"), { opacity: 1, duration: .2 }, t); });
S7("[data-f3d]", (el) => { const t = N(el, "f3d", 0);  // device frame: floats in tilted, drifts flatter while held, lifts out
  tl.fromTo(el, { scale: .9, y: 80, rotationX: 12, rotationY: -10, opacity: 0 }, { scale: 1, y: 0, rotationX: 6, rotationY: -10, opacity: 1, duration: .6, ease: "expo.out" }, t);
  if (D > t + 1.6) tl.fromTo(el, { rotationX: 6, rotationY: -10 }, { rotationX: 3, rotationY: -4, duration: D - t - 1.0, ease: "sine.inOut", immediateRender: false }, t + .6);
  if (D > 1.5) tl.to(el, { y: -40, opacity: 0, duration: .3, ease: "power2.in" }, D - .32); });
S7(".mx [data-in7]", (el) => { const t = N(el, "in7", 0);  // default entrance for v7 cards + exit at the end
  tl.from(el, { y: 40, opacity: 0, filter: "blur(12px)", duration: .45, ease: "expo.out" }, t);
  if (D > 1.2 && el.dataset.keep === undefined) tl.to(el, { y: -20, opacity: 0, filter: "blur(8px)", duration: .25, ease: "power2.in" }, D - .28); });
"""


def register(M):
    esc, rich, at, ICONS, text_w = M.esc, M.rich, M.at, M.ICONS, M.text_w

    def ic(name, cls=""):
        return f'<svg{f" class={chr(34)}{cls}{chr(34)}" if cls else ""} viewBox="0 0 24 24">{ICONS.get(name, ICONS["spark"])}</svg>'

    def wrap(sc, inner, y=236, align="c", anim=True, h=0):
        y = int(sc.get("y", y))
        right = 144 if y <= 1480 and y + h >= 700 else 64  # keep clear of the app button column (h: the graphic's height)
        cls = {"l": " l", "r": " r"}.get(sc.get("align", align), "")
        return (f'<div class="mxw{cls}" style="top:{y}px;right:{right}px"{" data-in7=" + chr(34) + f"{T0(sc):.2f}" + chr(34) if anim else ""}>'
                f'{inner}</div>')

    def T0(sc):
        return sc.get("_t0", 0.08)

    def wobble(pts, rnd, amp=3.0):
        return [(x + rnd.uniform(-amp, amp), y + rnd.uniform(-amp, amp)) for x, y in pts]

    def path(pts):
        if not pts:
            return ""
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d += f" Q{x0:.1f},{y0:.1f} {(x0 + x1) / 2:.1f},{(y0 + y1) / 2:.1f}"
        return d + f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"

    def shape_pts(shape, box, rnd, frm=None):
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        if shape == "circle":
            rx, ry = w / 2 + 26, h / 2 + 22
            a0 = math.radians(-110)
            return [[(cx + rx * math.cos(a0 + a) * (1 + 0.04 * math.sin(3 * a)), cy + ry * math.sin(a0 + a)) for a in
                     [i / 40 * math.radians(385) for i in range(41)]]]
        if shape == "box":
            p = 18
            return [[(x - p, y - p), (x + w + p, y - p), (x + w + p, y + h + p), (x - p, y + h + p), (x - p, y - p + 6)]]
        if shape == "underline":
            return [[(x - 12 + i * (w + 24) / 12, y + h + 14 + 5 * math.sin(i / 2)) for i in range(13)]]
        if shape == "x":
            return [[(x, y), (x + w, y + h)], [(x + w, y), (x, y + h)]]
        if shape == "check":
            return [[(x + w * .1, y + h * .55), (x + w * .38, y + h * .85), (x + w * .95, y + h * .1)]]
        # arrow: curved shaft from `frm` to the box edge, then the head
        fx, fy = frm or (cx - 260 if cx > 540 else cx + 260, cy - 220 if cy > 700 else cy + 220)
        tx, ty = cx + (fx - cx) * (w / 2 + 30) / max(1, math.hypot(fx - cx, fy - cy)), cy + (fy - cy) * (h / 2 + 30) / max(1, math.hypot(fx - cx, fy - cy))
        mx, my = (fx + tx) / 2 + (ty - fy) * .25, (fy + ty) / 2 - (tx - fx) * .25
        shaft = [((1 - u) ** 2 * fx + 2 * (1 - u) * u * mx + u * u * tx, (1 - u) ** 2 * fy + 2 * (1 - u) * u * my + u * u * ty) for u in [i / 16 for i in range(17)]]
        ang = math.atan2(ty - shaft[-3][1], tx - shaft[-3][0])
        head = [(tx - 46 * math.cos(ang - .5), ty - 46 * math.sin(ang - .5)), (tx, ty), (tx - 46 * math.cos(ang + .5), ty - 46 * math.sin(ang + .5))]
        return [shaft, head]

    # ------------------------------------------------------------ attention / annotation
    def tpl_scribble(sc, T):
        """Marker annotation drawn ON (screen demos / objects, never the face): shape circle|box|underline|arrow|x|check
        around box [x, y, w, h]; color o|w; optional label chip; boils while held."""
        t = T(sc.get("at"))
        box = sc.get("box", [380, 760, 320, 120])
        col = "#FFFFFF" if sc.get("color") == "w" else "#FF6A00"
        strokes = shape_pts(sc.get("shape", "circle"), box, random.Random(7), sc.get("from"))
        variants = []
        for v in range(3):
            rnd = random.Random(11 + v)
            ps = "".join(f'<path class="st"{" data-draw7=" + chr(34) + f"{t + k * .3:.2f}" + chr(34) + " data-dd=" + chr(34) + (".12" if k else ".42") + chr(34) if v == 0 else ""} '
                         f'd="{path(wobble(s, rnd, 2.6 if v else 0))}" stroke="{col}" stroke-width="12"/>' for k, s in enumerate(strokes))
            variants.append(f'<g class="bv" style="opacity:{1 if v == 0 else 0}">{ps}</g>')
        svg = (f'<svg class="mxsvg" viewBox="0 0 1080 1920" style="filter:drop-shadow(0 4px 10px rgba(0,0,0,.45))">'
               f'<g data-boil="{t:.2f}">{"".join(variants)}</g></svg>')
        lab = ""
        if sc.get("label"):
            x, y, w, h = box
            ly = y - 110 if y > 420 else y + h + 46
            lab = (f'<div class="mx-chip o" style="position:absolute;left:{max(64, min(780, x + w / 2 - 120)):.0f}px;top:{ly:.0f}px"'
                   f'{at(t + .35)} data-anim="pop">{esc(sc["label"])}</div>')
        return svg + lab

    def tpl_target(sc, T):
        """UI target ring + leader line + label (screen demos): box [x, y, w, h], label, side top|bottom|left|right,
        click [x, y] (+ click_at) adds a click ripple."""
        t = T(sc.get("at"))
        x, y, w, h = sc.get("box", [300, 700, 480, 140])
        side = sc.get("side", "top" if y > 500 else "bottom")
        r = 22
        ring = (f'<rect class="st" x="{x - 10}" y="{y - 10}" width="{w + 20}" height="{h + 20}" rx="{r}" stroke="#FF6A00" stroke-width="7" '
                f'data-draw7="{t:.2f}" data-dd=".45"/>')
        cx = x + w / 2
        if side == "top":
            ly, lx = y - 170, cx
            line = f'<path class="st" d="M{cx:.0f},{y - 12} L{cx:.0f},{y - 90}" stroke="#FF6A00" stroke-width="5" data-draw7="{t + .35:.2f}" data-dd=".2"/>'
        elif side == "bottom":
            ly, lx = y + h + 100, cx
            line = f'<path class="st" d="M{cx:.0f},{y + h + 12} L{cx:.0f},{y + h + 90}" stroke="#FF6A00" stroke-width="5" data-draw7="{t + .35:.2f}" data-dd=".2"/>'
        else:
            ly, lx = y + h / 2 - 34, (x - 300 if side == "left" else x + w + 300)
            ex = x - 12 if side == "left" else x + w + 12
            line = f'<path class="st" d="M{ex:.0f},{y + h / 2:.0f} L{(ex - 80 if side == "left" else ex + 80):.0f},{y + h / 2:.0f}" stroke="#FF6A00" stroke-width="5" data-draw7="{t + .35:.2f}" data-dd=".2"/>'
        rip = ""
        if sc.get("click"):
            px, py = sc["click"]
            ct = T(sc.get("click_at")) if sc.get("click_at") else t + .7
            rip = "".join(f'<circle cx="{px}" cy="{py}" r="70" fill="none" stroke="#FFFFFF" stroke-width="6" style="transform-origin:{px}px {py}px" '
                          f'data-ring7="{ct:.2f}" data-rd="{k * .15:.2f}"/>' for k in range(2))
            rip += f'<circle cx="{px}" cy="{py}" r="16" fill="#FF6A00" data-popin="{ct:.2f}"/>'
        svg = f'<svg class="mxsvg" viewBox="0 0 1080 1920" style="filter:drop-shadow(0 4px 12px rgba(0,0,0,.5))">{ring}{line}{rip}</svg>'
        lab = (f'<div class="mx-chip" style="position:absolute;left:{max(64, min(900, lx) - 160):.0f}px;top:{ly:.0f}px"{at(t + .5)} data-anim="pop">'
               f'{esc(sc.get("label", "Dito"))}</div>') if sc.get("label", "Dito") else ""
        return svg + lab

    def tpl_ping(sc, T):
        """'Dito' locator: rings radiate from point [x, y] (2 cycles) + a chip."""
        t = T(sc.get("at"))
        px, py = sc.get("point", [540, 900])
        rings = "".join(f'<circle cx="{px}" cy="{py}" r="80" fill="none" stroke="#FF6A00" stroke-width="7" style="transform-origin:{px}px {py}px" '
                        f'data-ring7="{t:.2f}" data-rd="{k * .15:.2f}"/>' for k in range(3))
        svg = f'<svg class="mxsvg" viewBox="0 0 1080 1920">{rings}<circle cx="{px}" cy="{py}" r="14" fill="#FF6A00" data-popin="{t:.2f}"/></svg>'
        chip = (f'<div class="mx-chip" style="position:absolute;left:{min(820, px + 40)}px;top:{py - 110}px"{at(t + .25)} data-anim="right">'
                f'{esc(sc.get("label", "Dito"))}</div>')
        return svg + chip

    def tpl_keys(sc, T):
        """Keycap shortcut: keys ["⌘", "Shift", "K"] pressed one after another (press_at), optional label."""
        t = T(sc.get("at"))
        pt = T(sc.get("press_at")) if sc.get("press_at") else t + .55
        ks = sc.get("keys", ["⌘", "K"])
        caps = []
        for i, k in enumerate(ks):
            if i:
                caps.append('<span class="kplus">+</span>')
            caps.append(f'<div class="kc{" o" if i == len(ks) - 1 else ""}" data-press="{pt + i * .16:.2f}">{esc(k)}</div>')
        lab = f'<div class="mx-chip"{at(pt + .4)} data-anim="pop">{esc(sc["label"])}</div>' if sc.get("label") else ""
        return wrap(sc, f'<div class="kcs">{"".join(caps)}</div>{lab}')

    # ------------------------------------------------------------ phone / app UI
    def tpl_island(sc, T):
        """Dynamic-Island alert: pill → banner (icon, title, body, time) → pill. Sits at the very top (y 222)."""
        t = T(sc.get("at"))
        return (f'<div class="isl" data-isl="{t:.2f}" style="top:{int(sc.get("y", 222))}px"><div class="ic">{ic(sc.get("icon", "bell"))}</div>'
                f'<div class="tx"><div class="t">{esc(sc.get("title", "Bagong message"))}</div><div class="s">{esc(sc.get("body", ""))}</div></div>'
                f'<div class="tm">{esc(sc.get("time", "now"))}</div></div>')

    def tpl_search(sc, T):
        """Search bar: the query types in, suggestions open, one lights up (pick = index, pick_at)."""
        t = T(sc.get("at"))
        q = sc.get("query", "paano mag-edit gamit si Claude")
        chars = "".join(f"<span>{esc(c) if c != ' ' else '&nbsp;'}</span>" for c in q)
        tq = t + .45
        t_sug = T(sc.get("sug_at")) if sc.get("sug_at") else tq + len(q) * .045 + .2
        sug = sc.get("suggestions", [])
        pick = sc.get("pick", 0)
        pt = T(sc.get("pick_at")) if sc.get("pick_at") else t_sug + .6
        rows = "".join(f'<div{" data-pick7=" + chr(34) + f"{pt:.2f}" + chr(34) if i == pick else ""}>{ic("search")}{esc(s)}</div>' for i, s in enumerate(sug))
        mag = '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>'
        return wrap(sc, f'<div class="srch"><div class="sbar">{mag}<div class="q" data-typeq="{tq:.2f}">{chars}</div>'
                        f'<i class="car" data-blink="{t + .1:.2f}"></i></div>{f"<div class={chr(34)}sug{chr(34)} data-sug={chr(34)}{t_sug:.2f}{chr(34)}>{rows}</div>" if sug else ""}</div>')

    def tpl_post(sc, T):
        """Social post card (generic, unbranded): name, handle, text word by word, metrics count up, heart fills."""
        t = T(sc.get("at"))
        name = sc.get("name", "Creator")
        words = "".join(f"<span>{esc(w)}&nbsp;</span>" for w in str(sc.get("text", "")).split())
        mt = sc.get("metrics", {"replies": 128, "reposts": 412, "likes": 2487, "views": "48K"})
        ct = t + .6 + .04 * len(str(sc.get("text", "")).split())

        def num(v):
            return (f'<span data-at="{ct:.2f}" data-anim="count" data-to="{int(v)}" data-dur=".8"></span>' if isinstance(v, (int, float)) or str(v).isdigit()
                    else esc(v))
        icons = {"replies": "message", "reposts": "loop" if "loop" in ICONS else "route", "likes": "heart" if "heart" in ICONS else "spark", "views": "chart"}
        heart = '<svg viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6C19 16.5 12 21 12 21z"/></svg>'
        cells = "".join(f'<b{" class=" + chr(34) + "lk" + chr(34) + " data-heart=" + chr(34) + f"{ct + .9:.2f}" + chr(34) if k == "likes" else ""}>'
                        f'{heart if k == "likes" else ic(icons.get(k, "spark"))}{num(v)}</b>' for k, v in mt.items())
        vf = f'<span class="vf">{ic("check")}</span>' if sc.get("verified", True) else ""
        return wrap(sc, f'<div class="mx-card post"><div class="hd"><div class="av">{esc(name[:1].upper())}</div><div><div class="nm">{esc(name)}{vf}</div>'
                        f'<div class="hn">{esc(sc.get("handle", "@" + re.sub(r"[^a-z0-9]", "", name.lower())))}</div></div></div>'
                        f'<div class="bd" data-words="{t + .4:.2f}">{words}</div><div class="mt">{cells}</div></div>', y=300)

    def tpl_call(sc, T):
        """Incoming-call banner: avatar ring pulses, then accept/decline presses on answer_at."""
        t = T(sc.get("at"))
        name = sc.get("caller", "Client")
        at_ = T(sc.get("answer_at")) if sc.get("answer_at") else t + 1.6
        btn = "yes" if sc.get("answer", "decline") == "accept" else "no"
        phone = '<svg viewBox="0 0 24 24"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>'
        return wrap(sc, f'<div class="call"><div class="av">{esc(name[:1].upper())}<i data-pulse7="{t + .2:.2f}"></i></div>'
                        f'<div class="tx"><div class="t">{esc(name)}</div><div class="s">{esc(sc.get("sub", "incoming call…"))}</div></div>'
                        f'<div class="b no"{" data-press=" + chr(34) + f"{at_:.2f}" + chr(34) if btn == "no" else ""}>{phone}</div>'
                        f'<div class="b yes"{" data-press=" + chr(34) + f"{at_:.2f}" + chr(34) if btn == "yes" else ""}>{phone}</div></div>', y=222)

    # ------------------------------------------------------------ rankings / data
    TIER_C = {"S": "#FF6A00", "A": "#FF8A33", "B": "#FF9A4D", "C": "#8C837C", "D": "#4A433F"}

    def tpl_tier(sc, T):
        """Tier list: rows [{tier, items:[{t, icon, at}]}]; tiles fly into their row on their cue."""
        rows = []
        for r in sc.get("rows", [{"tier": "S", "items": []}, {"tier": "A", "items": []}, {"tier": "B", "items": []}]):
            its = "".join(f'<div class="tit" data-tile="{T(it.get("at")):.2f}">{ic(it["icon"]) if it.get("icon") else ""}{esc(it["t"])}</div>'
                          for it in r.get("items", []))
            rows.append(f'<div class="trow"><div class="lt" style="background:{TIER_C.get(r["tier"], "#8C837C")}">{esc(r["tier"])}</div><div class="its">{its}</div></div>')
        return wrap(sc, f'<div class="mx-card tier">{"".join(rows)}</div>', y=420)

    STAR = '<svg viewBox="0 0 24 24"><path d="M12 2l3 6.9 7.5.6-5.7 4.9 1.7 7.4L12 17.9 5.5 21.8l1.7-7.4L1.5 9.5 9 8.9z"/></svg>'

    def tpl_score(sc, T):
        """Rating scorecard: rows [{t, v (0–5), at}], final score counts up, verdict pill."""
        t = T(sc.get("at"))
        rows, k = [], 0
        for r in sc.get("rows", []):
            rt = T(r.get("at")) if r.get("at") else t + .4 + k * .5
            stars = "".join(f'<i{" data-star=" + chr(34) + f"{rt + s * .06:.2f}" + chr(34) if s < round(float(r.get("v", 0))) else ""}>{STAR}</i>' for s in range(5))
            rows.append(f'<div class="srow"{at(rt - .1)} data-anim="left"><div class="n">{esc(r["t"])}</div><div class="stars">{stars}</div></div>')
            k += 1
        ft = T(sc.get("final_at")) if sc.get("final_at") else t + .5 + k * .5
        fin = sc.get("final", 8.5)
        whole = int(float(fin) * 10)
        verdict = f'<div class="mx-chip o"{at(ft + .7)} data-anim="pop">{esc(sc["verdict"])}</div>' if sc.get("verdict") else ""
        return wrap(sc, f'<div class="mx-card score"><div class="k">{esc(sc.get("kicker", "Rating"))}</div>{"".join(rows)}'
                        f'<div class="sfin"><div class="big"><span data-at="{ft:.2f}" data-anim="count" data-to="{whole}" data-dur=".7"></span></div>'
                        f'<div class="of">/100</div>{verdict}</div></div>', y=400)

    def tpl_price(sc, T):
        """Price slash: old price struck by hand, new price slams in a pill, a tilted badge."""
        t = T(sc.get("at"))
        nt = T(sc.get("new_at")) if sc.get("new_at") else t + .6
        strike = (f'<svg viewBox="0 0 100 40" preserveAspectRatio="none"><path class="st" d="M2,30 Q30,22 50,20 T98,8" stroke="#FF6A00" stroke-width="5" '
                  f'fill="none" vector-effect="non-scaling-stroke" data-strike7="{t + .35:.2f}"/></svg>')
        badge = f'<div class="bdg" data-badge="{nt + .3:.2f}">{esc(sc["badge"])}</div>' if sc.get("badge") else ""
        return wrap(sc, f'<div class="price"><div class="old"{at(t)} data-anim="up">{esc(sc.get("old", "₱1,100"))}{strike}</div>'
                        f'<div class="new" data-slam="{nt:.2f}">{esc(sc.get("new", "LIBRE"))}</div>{badge}</div>')

    def dial(size, inner, arc_attr, stroke=22):
        r = size / 2 - stroke
        c = size / 2
        return (f'<div class="dial" style="width:{size}px;height:{size}px"><svg viewBox="0 0 {size} {size}"><circle cx="{c}" cy="{c}" r="{r}" fill="rgba(12,9,8,.86)" '
                f'stroke="rgba(255,255,255,.12)" stroke-width="{stroke}"/><circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#FF6A00" stroke-width="{stroke}" '
                f'stroke-linecap="round" {arc_attr}/></svg><div class="in">{inner}</div></div>')

    def tpl_timer(sc, T):
        """Countdown: mm:ss from `from` seconds down to `to`, compressed over the scene; the ring depletes."""
        t = T(sc.get("at"))
        a, b = int(sc.get("from", 600)), int(sc.get("to", 0))
        n = 16
        vals = [round(a + (b - a) * i / n) for i in range(n + 1)]
        span = max(1.0, float(sc.get("_dur", 6)) - t - 1.0)
        times = ",".join(f"{t + .5 + span * i / n:.2f}" for i in range(1, n + 1))
        digits = "".join(f"<span>{v // 60:02d}:{v % 60:02d}</span>" for v in vals)
        return wrap(sc, dial(360, f'<div class="v" data-steps7="{times}">{digits}</div><div class="lb">{esc(sc.get("label", "timer"))}</div>',
                             f'data-arc="{t:.2f}" data-mode="deplete"'), align=sc.get("align", "l"))

    def tpl_ring(sc, T):
        """Progress ring: arc to pct with the number counting up in the middle, label under it."""
        t = T(sc.get("at"))
        p = float(sc.get("pct", 87))
        lab = f'<div class="dlb"{at(t + .5)} data-anim="up">{rich(sc["label"])}</div>' if sc.get("label") else ""  # under the dial: never clipped
        return wrap(sc, dial(int(sc.get("size", 420)), f'<div class="v" style="font-family:Inter Tight;font-weight:900;font-size:120px"><span data-at="{t:.2f}" data-anim="count" '
                             f'data-to="{int(p)}" data-dur=".8" data-suffix="%"></span></div>',
                             f'data-arc="{t:.2f}" data-p="{p / 100:.3f}" data-ad=".8"', stroke=30) + lab)

    def tpl_chart(sc, T):
        """Growth chart draw-on: points (values), area fill, end dot + rings, a pill at the peak."""
        t = T(sc.get("at"))
        pts = [float(v) for v in sc.get("points", [2, 3, 2.6, 4, 5.2, 7.8, 9.6])]
        lo, hi = min(pts), max(pts)
        W_, H_ = 872, 380
        xy = [(i * W_ / (len(pts) - 1), H_ - (v - lo) / max(1e-6, hi - lo) * (H_ - 40) - 20) for i, v in enumerate(pts)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        area = d + f" L{W_},{H_} L0,{H_} Z"
        ex, ey = xy[-1]
        pill = (f'<div class="pl" style="left:{min(680, 40 + ex - 120):.0f}px;top:{max(20, 96 + ey - 110):.0f}px"{at(t + 1.0)} data-anim="up">'
                f'{esc(sc.get("pill", "↑ 3.4×"))}</div>')
        return wrap(sc, f'<div class="mx-card chart"><div class="k">{esc(sc.get("kicker", "Growth"))}</div><svg viewBox="0 0 {W_} {H_}">'
                        f'<path d="{area}" fill="rgba(255,106,0,.18)" data-area="{t + .35:.2f}"/>'
                        f'<path class="st" d="{d}" stroke="#FF6A00" stroke-width="8" fill="none" data-draw7="{t:.2f}" data-dd=".9"/>'
                        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="16" fill="#FF6A00" data-popin="{t + .9:.2f}"/>'
                        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="46" fill="none" stroke="#FF6A00" stroke-width="5" style="transform-origin:{ex:.1f}px {ey:.1f}px" data-ring7="{t + .95:.2f}"/>'
                        f'</svg>{pill}</div>', y=420)

    def tpl_timeline(sc, T):
        """Horizontal timeline: nodes [{d (date), t, at}]; the line draws, nodes pop on their cue."""
        t = T(sc.get("at"))
        nodes = sc.get("nodes", [])
        nd = "".join(f'<div class="tnd"{at(T(n.get("at")) if n.get("at") else t + .5 + i * .4)} data-anim="up"><div class="d">{esc(n.get("d", ""))}</div>'
                     f'<div class="dot"></div><div class="t">{esc(n.get("t", ""))}</div></div>' for i, n in enumerate(nodes))
        return wrap(sc, f'<div class="mx-card tln"><div class="ln"><i data-grow7="{t:.2f}" data-gd=".6"></i></div><div class="nodes">{nd}</div></div>', y=400)

    def tpl_streak(sc, T):
        """Streak grid: `days` cells fill in sequence up to `upto` (today gets a ring) + 'DAY n / days'."""
        t = T(sc.get("at"))
        days, upto = int(sc.get("days", 30)), int(sc.get("upto", 14))
        cells = "".join(f'<i class="{"today" if i == upto - 1 else ""}"{" data-cell=" + chr(34) + f"{t + .3 + i * .025:.2f}" + chr(34) if i < upto else ""}></i>' for i in range(min(35, days)))
        return wrap(sc, f'<div class="mx-card strk"><div class="hd"><b>DAY {upto}</b><span>/ {days}</span></div><div class="grd">{cells}</div></div>',
                    y=380, align=sc.get("align", "c"))

    # ------------------------------------------------------------ type-driven / editorial
    FLAPS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def tpl_flap(sc, T):
        """Split-flap board: each letter flips through a few characters and settles (≤ 12 cells)."""
        t = T(sc.get("at"))
        txt = str(sc.get("text", "NEW TOOL")).upper()[:12]
        rnd = random.Random(5)
        cells = []
        for i, ch in enumerate(txt):
            if ch == " ":
                cells.append('<div class="fc sp"></div>')
                continue
            seq = [rnd.choice(FLAPS) for _ in range(6 + i % 5)] + [ch]
            cells.append(f'<div class="fc" data-flapcell="{t + i * .03:.2f}">{"".join(f"<span>{esc(c)}</span>" for c in seq)}</div>')
        return wrap(sc, f'<div class="flap">{"".join(cells)}</div>')

    def tpl_glitch(sc, T):
        """Glitch / RGB-split title (text only — the footage is never glitched)."""
        t = T(sc.get("at"))
        txt = esc(sc.get("text", "BREAKING"))
        px = int(min(150, 150 * 900 / max(1.0, text_w(sc.get("text", "BREAKING").upper(), 900, 150, -.04))))
        k = f'<div class="mx-chip o"{at(t + .5)} data-anim="pop">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
        return wrap(sc, f'{k}<div class="glt" style="font-size:{px}px" data-glitch="{t:.2f}"><span class="base">{txt}</span><span class="r">{txt}</span>'
                        f'<span class="c">{txt}</span></div>')

    def tpl_redact(sc, T):
        """Redaction reveal: lines with [[hidden words]] under black bars that wipe away on reveal_at (in order)."""
        t = T(sc.get("at"))
        rt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + 1.2
        k = [0]

        def hide(m):
            k[0] += 1
            return f'<span class="h">{esc(m.group(1))}<i data-unbar="{rt + (k[0] - 1) * .12:.2f}">REDACTED</i></span>'
        lines = "".join('<div class="ln">' + re.sub(r"\[\[(.+?)\]\]", hide, esc(ln)) + "</div>" for ln in sc.get("lines", ["Ang tool na 'to ay [[libre]]"]))
        return wrap(sc, f'<div class="mx-card rdx"><div class="k">{esc(sc.get("kicker", "CLASSIFIED"))}</div>{lines}</div>')

    def tpl_define(sc, T):
        """Definition card: word, phonetics (types in), part of speech (script), the definition."""
        t = T(sc.get("at"))
        return wrap(sc, f'<div class="mx-card dfn"><div><span class="w"{at(t + .1)} data-anim="left">{esc(sc.get("word", "agentic"))}<i data-grow7="{t + .4:.2f}" data-gd=".3"></i></span></div>'
                        f'<div class="ph"{at(t + .35)} data-anim="type" data-dur=".5">{esc(sc.get("phon", "/eɪˈdʒɛn.tɪk/"))}</div>'
                        f'<div class="pos"{at(t + .5)} data-anim="fade">{esc(sc.get("pos", "adjective"))}</div>'
                        f'<div class="df"{at(t + .65)} data-anim="up">{rich(sc.get("def", ""))}</div></div>', y=300)

    def tpl_pov(sc, T):
        """POV label: chip + one-line scenario typed in; up on frame 0 for POV hooks."""
        t = T(sc.get("at")) if sc.get("at") is not None else 0.0
        line = sc.get("text", "unang araw mo gamit si Claude")
        return wrap(sc, f'<div class="pov"><b{at(t)} data-anim="pop">POV</b><span{at(t + .15)} data-anim="type" data-dur="{min(1.4, max(.4, len(line) * .035)):.2f}">'
                        f'{esc(line)}</span></div>', align=sc.get("align", "l"), anim=False)

    def tpl_rank(sc, T):
        """Listicle rank badge: '#n OF m' with progress dots; steps [{n, at}] flip the numeral and light its dot."""
        t = T(sc.get("at"))
        of = int(sc.get("of", 5))
        steps = sc.get("steps") or [{"n": int(sc.get("n", 1))}]
        ts = [T(st["at"]) if st.get("at") is not None else t + 1.2 * i for i, st in enumerate(steps)]
        ns = [int(st["n"]) for st in steps]
        times = ",".join(f"{x:.2f}" for x in ts[1:])
        lit = {n - 1: ts[k] for k, n in enumerate(ns)}
        dots = "".join(f'<i class="{"on" if i < ns[0] - 1 else ""}"' + (f' data-cell="{lit[i]:.2f}"' if i in lit else "") + "></i>" for i in range(of))
        return wrap(sc, f'<div class="rank"><div class="bd"{at(t)} data-anim="pop"><div class="v" data-flipnum data-steps7="{times}">'
                        f'{"".join(f"<span>#{n}</span>" for n in ns)}</div></div><div class="of"><b>OF {of}</b><div class="dots">{dots}</div></div></div>',
                    align=sc.get("align", "l"))

    def tpl_ransom(sc, T):
        """Ransom-note headline: each word on a different cut-out swatch, dropped in one by one."""
        t = T(sc.get("at"))
        rnd = random.Random(3)
        words = str(sc.get("text", "ang sikreto ng mga editor")).split()
        out = []
        for i, w in enumerate(words):
            rot = rnd.choice([-6, -3, 2, 4, 7, -5])
            out.append(f'<span class="s{(i * 2 + rnd.randint(0, 1)) % 5}" style="transform:rotate({rot}deg)" data-drop7="{t + i * .09:.2f}" data-rot="{rot}">{esc(w)}</span>')
        return wrap(sc, f'<div class="rns">{"".join(out)}</div>')

    # ------------------------------------------------------------ photo / 3D / game
    def tpl_flip(sc, T):
        """Myth / Fact 3D flip card (flip_at): the back never shows mirrored text."""
        t = T(sc.get("at"))
        ft = T(sc.get("flip_at")) if sc.get("flip_at") else t + 1.6
        return wrap(sc, f'<div class="flipw"><div class="flipc" data-flip7="{ft:.2f}"><div class="fa front"><div class="lb">{esc(sc.get("front_label", "MYTH"))}</div>'
                        f'<div class="tx">{rich(sc.get("myth", "Kailangan mong marunong mag-code"))}</div></div>'
                        f'<div class="fa back"><div class="lb">{esc(sc.get("back_label", "FACT"))}</div><div class="tx">{rich(sc.get("fact", "Sasabihin mo lang kay Claude"))}</div></div></div></div>', y=400)

    def tpl_polaroid(sc, T):
        """Polaroid stack: items [{src (motion/clips path) | t, cap, at}] drop onto a pile with tape."""
        t = T(sc.get("at"))
        items = sc.get("items", [{"t": "1"}, {"t": "2"}, {"t": "3"}])
        angs = [-9, 6, -3, 8, -5]
        out = []
        for i, it in enumerate(items[:5]):
            x = 40 + i * (952 - 380) / max(1, len(items) - 1) if len(items) > 1 else 300
            img = f' style="background-image:url(../clips/{esc(it["src"])})"' if it.get("src") else ""
            out.append(f'<div class="pol" style="left:{x:.0f}px;transform:rotate({angs[i]}deg)" data-pol="{T(it.get("at")) if it.get("at") else t + i * .35:.2f}">'
                       f'<div class="tp"></div><div class="ph"{img}>{"" if it.get("src") else esc(it.get("t", ""))}</div><div class="cp">{esc(it.get("cap", ""))}</div></div>')
        return wrap(sc, f'<div class="pols">{"".join(out)}</div>', y=420)

    def tpl_achieve(sc, T):
        """Achievement toast: icon ring sweeps, kicker, title, XP bar fills."""
        t = T(sc.get("at"))
        rg = (f'<svg class="rg" viewBox="0 0 132 132"><circle cx="66" cy="66" r="60" fill="none" stroke="#FF6A00" stroke-width="6" stroke-linecap="round" '
              f'data-sweep="{t + .2:.2f}"/></svg>')
        return wrap(sc, f'<div class="mx-card ach" data-slide7="{t:.2f}"><div class="ic">{rg}{ic(sc.get("icon", "flag"), "st")}</div><div class="tx">'
                        f'<div class="k">{esc(sc.get("kicker", "ACHIEVEMENT UNLOCKED"))}</div><div class="t">{esc(sc.get("title", "Unang automation mo"))}</div>'
                        f'<div class="xp"><i data-grow7="{t + .45:.2f}" data-gd=".5"></i></div></div></div>', anim=False)

    def tpl_sticker(sc, T):
        """Die-cut sticker slapped on at [x, y] (outside the face), tilted (rot), white outline."""
        t = T(sc.get("at"))
        x, y = sc.get("pos", [120, 300])
        rot = float(sc.get("rot", -6))
        return f'<div class="stk{" w" if sc.get("style") == "white" else ""}" style="left:{x}px;top:{y}px" data-slap="{t:.2f}" data-rot="{rot}">{esc(sc.get("text", "LEGIT"))}</div>'

    def tpl_burst(sc, T):
        """Confetti burst from origin [x, y] (a graphic, never the face): seeded ballistic paths, 1.2 s."""
        t = T(sc.get("at"))
        ox, oy = sc.get("origin", [540, 420])
        rnd = random.Random(int(sc.get("seed", 9)))
        cols = ["#FF6A00", "#FF9A4D", "#F4EFEA", "#FFFFFF", "#FFC08A"]
        out = []
        for i in range(int(sc.get("n", 34))):
            ang = rnd.uniform(-math.pi * .95, -math.pi * .05)
            v = rnd.uniform(500, 950)
            vx, vy = v * math.cos(ang), v * math.sin(ang)
            ks = []
            for s in range(1, 7):
                tt = 1.2 * s / 6
                ks.append({"x": round(vx * tt), "y": round(vy * tt + 0.5 * 1800 * tt * tt), "rotation": round(rnd.uniform(-1, 1) * 360 * tt),
                           "opacity": 1 if tt < .8 else round(max(0, 1 - (tt - .8) / .4), 2)})
            w, h = rnd.choice([(16, 16), (10, 26), (22, 10)])
            import json as _j
            out.append(f'<i style="left:{ox - w / 2:.0f}px;top:{oy - h / 2:.0f}px;width:{w}px;height:{h}px;background:{rnd.choice(cols)}" '
                       f"data-conf=\"{t:.2f}\" data-k='{_j.dumps(ks)}'></i>")
        return f'<div class="bst">{"".join(out)}</div>'

    # ------------------------------------------------------------ screen-demo helpers
    def tpl_rail(sc, T):
        """Step-counter rail: items [{t, at}]; the current step lights up, the done ones fade back."""
        t = T(sc.get("at"))
        items = sc.get("items", [{"t": "Upload"}, {"t": "Style"}, {"t": "Render"}])
        times = [T(it.get("at")) if it.get("at") else t + .3 + i * 1.2 for i, it in enumerate(items)]
        out = []
        for i, it in enumerate(items):
            off = f' data-railoff="{times[i + 1]:.2f}"' if i + 1 < len(items) else ""
            out.append(f'<div class="st" data-railon="{times[i]:.2f}"{off}><b>{i + 1}</b>{esc(it["t"])}</div>')
        return wrap(sc, f'<div class="rail">{"".join(out)}</div>', align=sc.get("align", "l"))

    def tpl_ff(sc, T):
        """Speed-up badge for a sped-up demo: ▶▶ 4× + label."""
        t = T(sc.get("at"))
        return wrap(sc, f'<div class="ffb"{at(t)} data-anim="pop"><svg viewBox="0 0 24 24"><path d="M2 5l9 7-9 7zM12 5l9 7-9 7z"/></svg>'
                        f'<b>{esc(sc.get("speed", "4×"))}</b><span>{esc(sc.get("label", "FAST-FORWARD"))}</span></div>', align=sc.get("align", "r"))

    # ------------------------------------------------------------ next wave (2026-10-21)
    def noise_png(w=48, h=48, seed=4):
        """Tiny seeded grey-noise PNG (paper / cork texture — on the graphic only, never the footage), as a data URI."""
        rnd = random.Random(seed)
        raw = b"".join(b"\x00" + bytes(rnd.randint(70, 255) for _ in range(w)) for _ in range(h))

        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9))
               + chunk(b"IEND", b""))
        return "data:image/png;base64," + base64.b64encode(png).decode()
    NOISE = noise_png()

    def tex():
        return f'<i class="tx" style="background-image:url({NOISE})"></i>'

    MOCK = ('<div class="mku-top"><i></i><b>Studio</b><span>Projects</span><span class="on">Export</span><span>Settings</span><em></em></div>'
            '<div class="mku-side"><div class="on">Video</div><div>Captions</div><div>Audio</div><div>Brand</div><div>Billing</div></div>'
            '<div class="mku-main"><div class="mku-h">Export final</div><div class="mku-row"><span>Resolution</span><b>1080 × 1920</b></div>'
            '<div class="mku-row"><span>Captions</span><b>Pop · 110</b></div><div class="mku-row"><span>Music</span><b>−18 dB</b></div>'
            '<div class="mku-row"><span>Auto-zoom</span><i class="mku-tg"></i></div><div class="mku-btn">Export 1080p</div>'
            '<div class="mku-fine">Plan: Free · ₱0/mo · no watermark</div></div>')

    def shot_html(sc, w, h):
        """A screenshot filling w×h: `src` (a file in motion/clips) or, without one, a generic app mock-up."""
        if sc.get("src"):
            return f'<div class="shimg" style="width:{w:.0f}px;height:{h:.0f}px;background-image:url(../clips/{esc(sc["src"])})"></div>'
        return (f'<div style="position:relative;width:{w:.0f}px;height:{h:.0f}px;overflow:hidden;background:#141010">'
                f'<div class="mku" style="transform:scale({w / 860:.4f})">{MOCK}</div></div>')

    def fhead(sc, y, t=.1):
        """Kicker chip + title for a full-screen page (or above a placed graphic)."""
        k = f'<div class="mx-chip o"{at(t)} data-anim="pop">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
        h = f'<div class="mxh"{at(t + .08)} data-anim="up">{rich(sc["title"])}</div>' if sc.get("title") else ""
        return f'<div class="mxw" style="top:{int(y)}px">{k}{h}</div>' if k or h else ""

    HEART = '<svg viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6C19 16.5 12 21 12 21z"/></svg>'
    TMK = {"before": '<i class="hd"></i><i class="bd"></i><div class="tt">my video ep. 3</div>',
           "after": '<i class="hd"></i><i class="bd"></i><div class="tt"><b>₱0</b> EDITOR</div><div class="st">LIBRE</div>'}

    def tpl_wipe(sc, T):
        """Before / after slider (images): `before` / `after` are screenshots in motion/clips (none → thumbnail mock-ups).
        The AFTER side wipes across on reveal_at, overshoots back to the middle and holds; a knob rides the divider.
        box [x, y, w, h]; "bg": true = full-screen B-roll page, else it sits ON a screen region. labels [left, right]; kicker / title."""
        t = T(sc.get("at"))
        rt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + .5
        bg = sc.get("bg")
        x, y, w, h = sc.get("box", [64, 440, 872, 872] if bg else [64, 300, 872, 560])

        def side(k):
            if sc.get(k):
                return f'<div class="shimg" style="position:absolute;inset:0;background-image:url(../clips/{esc(sc[k])})"></div>'
            s = max(w, h) / 872  # mock-ups cover the box like a photo would
            return f'<div class="tmk {k[0]}" style="transform:translate({(w - 872 * s) / 2:.0f}px,{(h - 872 * s) / 2:.0f}px) scale({s:.4f})">{TMK[k]}</div>'
        lb = sc.get("labels", ["BEFORE", "AFTER"])
        arrows = '<svg viewBox="0 0 24 24"><path d="M9 6l-6 6 6 6zM15 6l6 6-6 6z"/></svg>'
        return (fhead(sc, sc.get("head_y", max(236, y - 150))) +
                f'<div class="wp" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px" data-in7="{T0(sc):.2f}" data-wipe="{rt:.2f}">'
                f'<div class="wpl">{side("before")}</div><div class="wpl wpa" style="clip-path:inset(0% 0% 0% 100%)">{side("after")}</div>'
                f'<div class="wpd" style="left:100%"><i class="wpk">{arrows}</i></div>'
                f'<div class="wpc l"{at(rt + .2)} data-anim="fade">{esc(lb[0])}</div><div class="wpc r"{at(rt + .2)} data-anim="fade">{esc(lb[1])}</div></div>')

    def tpl_loupe(sc, T):
        """Magnifier loupe on a screenshot: the shot (`src` in motion/clips, else a mock-up) sits at shot [x, y, w, h]; a ping
        marks point [x, y] (tiny text / a toggle / a price), then a lens (r, zoom 2–2.5×) grows out of it and travels to
        lens [x, y] — a free zone, never over the target or the face — with a leader line. label = a chip beside the lens."""
        t = T(sc.get("at"))
        lt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + .35
        sx, sy, sw, sh = sc.get("shot", [64, 300, 872, 568])
        px, py = sc.get("point", [440, 857])
        lx, ly = sc.get("lens", [330, 1120])
        r, z = int(sc.get("r", 190)), float(sc.get("zoom", 2.4))
        inner = shot_html(sc, sw, sh)
        dist = max(1.0, math.hypot(px - lx, py - ly))
        ex, ey = lx + (px - lx) / dist * (r + 4), ly + (py - ly) / dist * (r + 4)
        svg = (f'<svg class="mxsvg" viewBox="0 0 1080 1920" style="filter:drop-shadow(0 3px 8px rgba(0,0,0,.5))">'
               f'<path class="st" d="M{px},{py} L{ex:.0f},{ey:.0f}" stroke="#FF6A00" stroke-width="5" data-draw7="{lt + .4:.2f}" data-dd=".2"/>'
               + "".join(f'<circle cx="{px}" cy="{py}" r="40" fill="none" stroke="#FF6A00" stroke-width="6" style="transform-origin:{px}px {py}px" '
                         f'data-ring7="{t:.2f}" data-rd="{k * .15:.2f}"/>' for k in range(2))
               + f'<circle cx="{px}" cy="{py}" r="10" fill="#FF6A00" data-popin="{t:.2f}"/></svg>')
        lens = (f'<div class="lp-lens" style="left:{lx - r}px;top:{ly - r}px;width:{2 * r}px;height:{2 * r}px" data-lens="{lt:.2f}" data-dx="{px - lx}" data-dy="{py - ly}">'
                f'<div class="lp-in"><div style="position:absolute;left:{r - (px - sx) * z:.1f}px;top:{r - (py - sy) * z:.1f}px;transform:scale({z});transform-origin:0 0">'
                f'{inner}</div></div><i class="lp-ring"></i></div>')
        lab = ""
        if sc.get("label"):
            cw = text_w(sc["label"], 800, 32) + 70
            if lx + r + 24 + cw <= 936:
                lpos = f"left:{lx + r + 24:.0f}px;top:{ly - 34:.0f}px"
            elif lx - r - 24 - cw >= 64:
                lpos = f"left:{lx - r - 24 - cw:.0f}px;top:{ly - 34:.0f}px"
            else:
                lpos = f"left:{max(64, lx - cw / 2):.0f}px;top:{ly + r + 22:.0f}px"
            lab = f'<div class="mx-chip o" style="position:absolute;{lpos}"{at(lt + .5)} data-anim="pop">{esc(sc["label"])}</div>'
        return (fhead(sc, sc.get("head_y", 236)) + f'<div class="lp-shot" style="left:{sx}px;top:{sy}px;width:{sw}px;height:{sh}px" data-in7="{T0(sc):.2f}" data-keep>'
                f'{inner}</div>{svg}{lens}{lab}')

    def up_svg(attr="", cls="up"):
        return f'<svg class="{cls}"{attr} viewBox="0 0 24 24"><path d="M12 4l7 8h-4.5v8h-5v-8H5z"/></svg>'

    def tpl_thread(sc, T):
        """Forum thread card (generic, unbranded): vote column ▲ n ▼ (votes count up), community · user · time, title, body;
        replies [{user, text, votes, at, top}] indent under it on connector lines that draw down; the `top` reply gets an
        orange edge. Full-screen ("bg": true) for a long thread; on the footage it sits in the chest band (y 1150, shown at 72 %)
        — keep that one to a short title (no body) + one reply."""
        t = T(sc.get("at"))
        reps = sc.get("replies", [])
        rows = []
        for i, r in enumerate(reps):
            rt = T(r.get("at")) if r.get("at") else t + .9 + i * .5
            cv = "" if i == len(reps) - 1 else f'<i class="cv" data-down7="{rt + .1:.2f}"></i>'
            edge = f' data-edge7="{rt + .3:.2f}"' if r.get("top") else ""
            rows.append(f'<div class="th-r"><i class="cn" data-down7="{rt - .3:.2f}"></i>{cv}<div class="th-rc"{at(rt)} data-anim="right"{edge}>'
                        f'<div class="th-k"><i></i><b>{esc(r.get("user", "@member"))}</b>· {esc(r.get("time", "2h"))}</div>'
                        f'<div class="th-x">{rich(r.get("text", ""))}</div><div class="th-rv">{up_svg()}{esc(str(r.get("votes", 42)))}</div></div></div>')
        vt = t + .35
        par = (f'<div class="mx-card th-p"><div class="th-v">{up_svg(f" data-upv={chr(34)}{vt:.2f}{chr(34)}")}'
               f'<b><span data-at="{vt:.2f}" data-anim="count" data-to="{int(sc.get("votes", 1248))}" data-dur=".6"></span></b>{up_svg(cls="dn")}</div>'
               f'<div class="th-m"><div class="th-k"><i></i><b>{esc(sc.get("community", "Video Editing PH"))}</b>· {esc(sc.get("user", "@member"))} · '
               f'{esc(sc.get("time", "5h"))}</div><div class="th-t">{rich(sc.get("title", ""))}</div>'
               + (f'<div class="th-b">{rich(sc["body"])}</div>' if sc.get("body") else "")
               + f'<div class="th-f"><b>{ic("message")}{len(reps) or int(sc.get("comments", 12))} replies</b><b>{ic("link")}Share</b></div></div></div>')
        if sc.get("bg"):
            return wrap(sc, f'<div class="thr">{par}<div class="th-rs">{"".join(rows)}</div></div>', y=420, h=360 + 170 * len(reps))
        return wrap(sc, f'<div class="thr" style="width:1211px;transform:scale(.72);transform-origin:0 0">{par}<div class="th-rs">{"".join(rows)}</div></div>',
                    y=1150, align="l", h=310)  # chest band: laid out 1211 wide, shown 872 (keep it to a short title + one reply)

    def wav_bars(path, n):
        """RMS per bar from a .wav (mono mix), perceptual (sqrt) and normalised → [0.12..1], plus the clip length."""
        import wave
        import numpy as np
        with wave.open(str(path), "rb") as wf:
            ch, sw, sr, nf = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
            a = np.frombuffer(wf.readframes(nf), dtype={1: np.uint8, 2: np.int16, 4: np.int32}[sw]).astype(np.float64)
        if sw == 1:
            a -= 128
        a = a.reshape(-1, ch).mean(axis=1) if ch > 1 else a
        rms = np.array([np.sqrt(np.mean(c ** 2)) if len(c) else 0.0 for c in np.array_split(a, n)])
        rms = np.sqrt(rms / max(1e-9, float(rms.max())))
        return [max(.12, float(v)) for v in rms], nf / float(sr)

    def tpl_voicenote(sc, T):
        """Voice-note bubble: orange play button, 24–64 waveform bars (from `audio` — a .wav in the project, so the
        waveform is the real one — else seeded), mono duration. Bars grow in; on press_at play turns to pause, the bars
        fill orange over `length` s (the audio's length when given) and the counter runs. sender = small line above."""
        t = T(sc.get("at"))
        pt = T(sc.get("press_at")) if sc.get("press_at") else t + .8
        n = max(24, min(64, int(sc.get("bars", 48))))
        hs, alen = None, None
        if sc.get("audio"):
            try:
                hs, alen = wav_bars(M.ROOT / sc["audio"], n)
            except Exception:  # missing / not a plain PCM .wav → seeded bars
                hs = None
        if hs is None:
            rnd = random.Random(int(sc.get("seed", 21)))
            hs = [max(.14, min(1.0, (.3 + .7 * abs(math.sin(i * .41) * math.cos(i * .13 + 1.1))) * rnd.uniform(.55, 1.0)
                                * (1 - .55 * abs(i / (n - 1) * 2 - 1) ** 3))) for i in range(n)]
        length = float(alen or sc.get("length") or max(1.0, float(sc.get("_dur", 6)) - pt - .6))
        span = max(.5, min(length, float(sc.get("_dur", 6)) - pt - .3))
        bars = "".join(f'<i style="height:{max(6.0, v * 72):.0f}px"></i>' for v in hs)

        def mmss(s):
            s = int(round(s))
            return f"{s // 60}:{s % 60:02d}"
        secs = list(range(int(span) + 1))
        digits = "".join(f"<span>{v}</span>" for v in [mmss(length)] + [mmss(s) for s in secs])
        play = '<svg class="pl" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
        pause = '<svg class="pa" style="opacity:0" viewBox="0 0 24 24"><path d="M7 5h4v14H7zM13 5h4v14h-4z"/></svg>'
        sender = f'<div class="vn-s">{esc(sc["sender"])}</div>' if sc.get("sender") else ""
        return wrap(sc, f'<div class="vn-w">{sender}<div class="vn"><div class="vn-b" data-vplay="{pt:.2f}">{play}{pause}</div>'
                        f'<div class="vn-wv" data-vbar="{t + .3:.2f}"><div class="ly">{bars}</div>'
                        f'<div class="ly o" style="clip-path:inset(0% 100% 0% 0%)" data-vprog="{pt:.2f}" data-len="{span:.2f}">{bars}</div></div>'
                        f'<div class="vn-d" data-steps7="{",".join(f"{pt + s:.2f}" for s in secs)}">{digits}</div></div></div>',
                    y=240, align=sc.get("align", "l"), h=170)

    FEED_WHO = [("Mika Edits", "@mikaedits"), ("Kape & Code", "@kapecode"), ("AI Daily PH", "@aidailyph"), ("Creator Lab", "@creatorlab"),
                ("Studio Notes", "@studionotes"), ("Edit Tips", "@edittips"), ("Pixel Pinoy", "@pixelpinoy"), ("Joshua", "@joshua")]
    FEED_BG = ["linear-gradient(160deg,#FF9A4D,#C24700)", "linear-gradient(160deg,#3A332E,#15110F)", "linear-gradient(160deg,#F4F1EA,#CFC5BA)",
               "linear-gradient(160deg,#6B4429,#24160F)", "linear-gradient(160deg,#2B231F,#0C0908)"]
    FEED_AV = ["#FF9A4D", "#D9D2CC", "#FF6A00", "#A39A93", "#C24700"]

    def tpl_feed(sc, T):
        """Feed-scroll phone (generic): a phone of posts (items: [text, …]) flick-scrolls 3× and stops on `pick`, which
        rings orange (pick_at); the phone rises in and drops out. "bg": true = centred full-screen page; on the footage
        it is a small side-rail phone at x 64 (side "left", the default there) for when the face sits right of centre."""
        t = T(sc.get("at"))
        items = sc.get("items") or ["5 AI tools na libre", "POV: unang client mo", "Paano mag-caption", "CapCut vs Premiere",
                                    "Day 14 / 30", "Bakit ako tumigil", "Gumawa ako ng sariling editor", "Behind the scenes"]
        pick = max(0, min(len(items) - 1, int(sc.get("pick", len(items) - 2))))
        yf = -max(0, pick * 420 - 244)  # card stride 420; the picked post ends centred in the screen
        nfl = 3 if pick >= 3 else max(1, pick)
        t0 = t + .75
        fl = [[round(t0 + k * .6, 2), round(yf * (k + 1) / nfl)] for k in range(nfl)]
        pk = T(sc.get("pick_at")) if sc.get("pick_at") else fl[-1][0] + .55
        rnd = random.Random(int(sc.get("seed", 12)))
        cards = []
        for i, txt in enumerate(items):
            nm, hd = FEED_WHO[(i * 3 + 1) % len(FEED_WHO)]
            bgc = FEED_BG[i % len(FEED_BG)]
            cards.append(f'<div class="fd-c"{" data-hl7=" + chr(34) + f"{pk:.2f}" + chr(34) if i == pick else ""}><div class="fd-h">'
                         f'<i style="background:{FEED_AV[(i + 2) % len(FEED_AV)]}"></i><div><b>{esc(nm)}</b><span>{esc(hd)}</span></div></div>'
                         f'<div class="fd-m{" lt" if "F4F1EA" in bgc else ""}" style="background:{bgc}">{esc(txt)}</div>'
                         f'<div class="fd-f"><b>{HEART}{rnd.randint(12, 98) / 10:.1f}K</b><b>{ic("message")}{rnd.randint(20, 400)}</b></div></div>')
        left = sc.get("side", "center" if sc.get("bg") else "left") == "left"
        s = .68 if left else float(sc.get("scale", 1))
        x = 64 if left else int(sc.get("x", 540 - 250 * s))
        y = int(sc.get("y", 480 if left else 330))
        return (fhead(sc, sc.get("head_y", 236)) +
                f'<div class="fdw" style="left:{x}px;top:{y}px;transform:scale({s:.3f})" data-phone7="{t:.2f}"><div class="fdp"><div class="fds">'
                f'<div class="fdst"><span>9:41</span><i></i><u></u></div><div class="fdv"><div class="fdl" data-flicks=\'{json.dumps(fl)}\'>{"".join(cards)}'
                f'</div></div></div></div></div>')

    def tpl_receipt(sc, T):
        """Receipt print: an off-white thermal receipt prints out of a slot one line at a time — title, meta, items
        [[label, value]], then TOTAL in orange (final_at) and an optional stamp ("PAID" / "LIBRE" or {t, at}).
        Left side rail by default (x 64, y 480, shown w 316 = x 64–380); move / size it with x / y / w."""
        t = T(sc.get("at"))
        w, x, y = 420, int(sc.get("x", 64)), int(sc.get("y", 480))  # laid out 420 wide, shown at w (scaled)
        s = float(sc.get("w", 316)) / w
        items = sc.get("items", [["Auto-captions", "₱0"], ["Motion graphics", "₱0"], ["Oras na natipid", "6 hrs"]])
        tot = sc.get("total", ["TOTAL", "₱0.00"])
        PT, HT, HM, HD, HL, HTO, HF, PB, ZZ = 26, 52, 36, 28, 48, 74, 86, 14, 18  # fixed row heights → exact print steps
        n = len(items)
        Ht = PT + HT + HM + HD + n * HL + HD + HTO + HF + PB + ZZ
        t0 = t + .3
        tl0 = t0 + .54 + n * .18
        ft = max(tl0 + .1, T(sc.get("final_at")) if sc.get("final_at") else tl0 + .2)
        seq = [(PT + HT, t0), (HM, t0 + .18), (HD, t0 + .36)] + [(HL, t0 + .54 + i * .18) for i in range(n)] + [(HD, tl0), (HTO, ft), (HF + PB + ZZ, ft + .3)]
        steps, b = [], 0
        for hh, tt in seq:
            b += hh
            steps.append([round(tt, 2), Ht - b])
        lines = "".join(f'<div class="rc-l"{at(t0 + .54 + i * .18)} data-anim="type" data-dur="{max(.12, len(str(a) + str(v)) * .02):.2f}">'
                        f'<span>{esc(a)}</span><b>{esc(v)}</b></div>' for i, (a, v) in enumerate(items))
        rnd = random.Random(int(sc.get("seed", 3)))
        code = "".join(f'<i style="width:{rnd.choice([2, 2, 3, 4, 6])}px"></i>' for _ in range(int((w - 120) / 6)))
        st = sc.get("stamp")
        stamp = ""
        if st:
            st = st if isinstance(st, dict) else {"t": st}
            stamp = f'<div class="rc-pd"{at(T(st["at"]) if st.get("at") else ft + .55)} data-anim="stamp">{esc(st["t"])}</div>'
        zz = " ".join(f"{w - k * 12:.0f},{16 if k % 2 == 0 else 2}" for k in range(int(w / 12) + 1))
        return (f'<div class="rcw" style="left:{x}px;top:{y}px;width:{w}px;transform:scale({s:.4f});transform-origin:0 0" data-in7="{T0(sc):.2f}"><div class="rc-slot"></div>'
                f'<div class="rc" style="clip-path:inset(0px 0px {Ht}px 0px)" data-print=\'{json.dumps(steps)}\'><div class="rc-p">{tex()}'
                f'<div class="rc-h">{esc(sc.get("title", "RECEIPT"))}</div><div class="rc-m">{esc(sc.get("meta", ""))}</div><div class="rc-ds"><i></i></div>{lines}'
                f'<div class="rc-ds"><i></i></div><div class="rc-t" data-tot7="{ft:.2f}"><span>{esc(tot[0])}</span><span>{esc(tot[1])}</span></div>'
                f'<div class="rc-f"><div class="rc-bc">{code}</div><span>{esc(sc.get("thanks", "SALAMAT · THANK YOU"))}</span></div>{stamp}</div>'
                f'<svg class="rc-zz" width="{w}" height="{ZZ}"><polygon points="0,0 {w},0 {zz} 0,2" fill="#F4F1EA"/></svg></div></div>')

    def tpl_venn(sc, T):
        """Venn diagram: 2–3 sets [{t}] slide together, the overlap fills orange (reveal_at) and the `center` label pops.
        Full-screen ("bg": true, r ≈ 220) or the chest band (y 1150–1460: r 130 for two sets, 105 for three)."""
        t = T(sc.get("at"))
        rt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + .85
        sets = sc.get("sets", [{"t": "Mabilis"}, {"t": "Libre"}, {"t": "Pro ang dating"}])[:3]
        n = len(sets)
        bg = sc.get("bg")
        r = float(sc.get("r", (220 if n == 3 else 230) if bg else (105 if n == 3 else 130)))
        cx = 540
        d = (.57 if n == 3 else .52) * r
        cy = float(sc.get("cy", 860 if bg else int(sc.get("y", 1150)) + 8 + r + (.5 * d if n == 3 else 0)))
        dirs = [(-.866, -.5), (.866, -.5), (0.0, 1.0)] if n == 3 else [(-1.0, 0.0), (1.0, 0.0)]
        cs = [(cx + dx * d, cy + dy * d) for dx, dy in dirs]
        fills = ["rgba(44,34,29,.84)", "rgba(62,43,31,.84)", "rgba(34,26,22,.84)"]
        strokes = ["rgba(255,255,255,.55)", "rgba(255,154,77,.9)", "rgba(255,255,255,.35)"]

        def circ(i, fill, extra=""):
            return f'<circle cx="{cs[i][0]:.1f}" cy="{cs[i][1]:.1f}" r="{r:.1f}" fill="{fill}"{extra}/>'
        defs = "".join(f'<clipPath id="vc{i}">{circ(i, "#000")}</clipPath>' for i in range(n))
        rings = "".join(f'<g data-vin="{t + i * .08:.2f}" data-dx="{dirs[i][0] * 180:.0f}" data-dy="{dirs[i][1] * 180:.0f}">'
                        f'{circ(i, fills[i], f" stroke={chr(34)}{strokes[i]}{chr(34)} stroke-width={chr(34)}4{chr(34)}")}</g>' for i in range(n))
        if n == 3:
            ov = ("".join(f'<g clip-path="url(#vc{a})">{circ(b_, "rgba(255,106,0,.26)")}</g>' for a, b_ in ((0, 1), (0, 2), (1, 2)))
                  + f'<g clip-path="url(#vc0)"><g clip-path="url(#vc1)">{circ(2, "#FF6A00")}</g></g>')
        else:
            ov = f'<g clip-path="url(#vc0)">{circ(1, "#FF6A00")}</g>'
        svg = (f'<svg class="mxsvg" viewBox="0 0 1080 1920" style="filter:drop-shadow(0 18px 40px rgba(0,0,0,.45))"><defs>{defs}</defs>{rings}'
               f'<g data-ov="{rt:.2f}" data-o="{cx} {cy:.0f}">{ov}</g></svg>')
        fs = max(26, min(42, r * .19))
        labs = "".join(f'<div class="vl" style="left:{cs[i][0] + dirs[i][0] * r * .48:.0f}px;top:{cs[i][1] + dirs[i][1] * r * .48:.0f}px" '
                       f'data-vin="{t + i * .08 + .1:.2f}" data-dx="{dirs[i][0] * 180:.0f}" data-dy="{dirs[i][1] * 180:.0f}">'
                       f'<span style="font-size:{fs:.0f}px">{rich(s_.get("t", ""))}</span></div>' for i, s_ in enumerate(sets))
        mid = (f'<div class="vl c" style="left:{cx}px;top:{cy:.0f}px"{at(rt + .2)} data-anim="pop"><span>{esc(sc["center"])}</span></div>'
               if sc.get("center") else "")
        return fhead(sc, sc.get("head_y", 300 if bg else max(236, cy - r - d - 150))) + svg + labs + mid

    CLOUD_PX = {1: 34, 2: 42, 3: 52, 4: 64, 5: 80}

    def tpl_cloud(sc, T):
        """Word cloud: words [text | [text, weight 1–5]] (12–24) fly in from seeded offsets and lock into a packed cloud
        inside box [x, y, w, h]; `pick` (one of the words) turns orange and grows while the rest step back (pick_at).
        Full-screen ("bg": true) or the chest band (default box y 1150–1450)."""
        t = T(sc.get("at"))
        words = [(w, 3) if isinstance(w, str) else (str(w[0]), int(w[1])) for w in sc.get("words", ["libre ba?", "Mac lang?", "presyo?"])][:24]
        pick = sc.get("pick", words[0][0])
        bx, by, bw, bh = sc.get("box", [64, 470, 872, 800] if sc.get("bg") else [64, 1150, 872, 300])
        rnd = random.Random(int(sc.get("seed", 6)))
        asp = max(1.0, min(3.2, bw / bh))
        placed = []  # (index, x, y, w, h, px, weight, pad) — spiral packing, the pick in the middle with room to grow 1.2×
        for i in sorted(range(len(words)), key=lambda i: (words[i][0] != pick, -words[i][1], i)):
            txt, wt = words[i]
            px = 96 if txt == pick else CLOUD_PX[max(1, min(5, wt))]
            fw = 900 if txt == pick else rnd.choice([900, 800, 700, 600])
            g = 1.22 if txt == pick else 1.0
            ww, hh = (text_w(txt, fw, px, -.01) + 20) * g, (px * 1.08 + 10) * g
            x0 = y0 = 0.0
            for k in range(8000):
                a = k * .14
                x0, y0 = 2.2 * a * math.cos(a) * asp - ww / 2, 2.2 * a * math.sin(a) - hh / 2
                if all(x0 + ww <= x or x + w <= x0 or y0 + hh <= y or y + h <= y0 for _, x, y, w, h, *_ in placed):
                    break
            placed.append((i, x0, y0, ww, hh, px, fw, ((ww - ww / g) / 2, (hh - hh / g) / 2)))
        mnx, mny = min(p[1] for p in placed), min(p[2] for p in placed)
        cw_, ch_ = max(p[1] + p[3] for p in placed) - mnx, max(p[2] + p[4] for p in placed) - mny
        s = min(1.7, bw / cw_, bh / ch_)  # fill the box (up to 1.7×)
        ox, oy = bx + (bw - cw_ * s) / 2, by + (bh - ch_ * s) / 2
        order = list(range(len(placed)))
        rnd.shuffle(order)
        pt = T(sc.get("pick_at")) if sc.get("pick_at") else t + .15 + len(placed) * .03 + .75
        out = []
        for j, k in enumerate(order):
            i, x, y, w, h, px, fw, (padx, pady) = placed[k]
            txt = words[i][0]
            cue = f'data-cpick="{pt:.2f}"' if txt == pick else f'data-cdim="{pt:.2f}"'
            cls = "pk" if txt == pick else "d2" if j % 3 == 1 else ""
            out.append(f'<span class="{cls}" style="left:{ox + (x - mnx + padx + 10) * s:.0f}px;top:{oy + (y - mny + pady + 5) * s:.0f}px;font-size:{px * s:.0f}px;font-weight:{fw}" '
                       f'data-cw="{t + .15 + j * .03:.2f}" data-dx="{rnd.uniform(-400, 400):.0f}" data-dy="{rnd.uniform(-400, 400):.0f}" {cue}>{esc(txt)}</span>')
        return fhead(sc, sc.get("head_y", 300 if sc.get("bg") else 236)) + f'<div class="cld">{"".join(out)}</div>'

    def tpl_slot(sc, T):
        """Slot-reel picker: 1–3 reels [{items, pick, label}] (or items + pick for one reel) spin through ~24 entries and
        land on their pick — the first at pick_at (default at + 1.9), the rest 0.25 s apart; each window bumps, the
        frame flashes orange (the graphic only). title = the line on top. Top band by default (y 240–416), 760 wide."""
        t = T(sc.get("at"))
        reels = (sc.get("reels") or [{"items": sc.get("items", ["CapCut", "Premiere", "Canva", "Claude"]), "pick": sc.get("pick")}])[:3]
        n = len(reels)
        rw = (716 - 16 * (n - 1)) / n
        ts = t + .45  # the spin starts once the machine is in
        spin = max(.9, (T(sc.get("pick_at")) if sc.get("pick_at") else t + 1.9) - ts)
        cols = []
        for i, rl in enumerate(reels):
            its = [str(v) for v in rl.get("items", [])] or ["?"]
            pk = str(rl.get("pick") or its[-1])
            if pk not in its:
                its.append(pk)
            K = 20 + 4 * i
            j0 = (its.index(pk) - (K - 1)) % len(its)
            strip = "".join(f"<div>{esc(its[(j0 + k) % len(its)])}</div>" for k in range(K))
            px = min({1: 56, 2: 46}.get(n, 40), (rw - 36) / max(text_w(v, 900, 100, -.02) / 100 for v in its))
            lb = f'<div class="lb">{esc(rl["label"])}</div>' if rl.get("label") else ""
            cols.append(f'<div class="slc" style="width:{rw:.0f}px"><div class="slw"><b class="l"></b><b class="r"></b>'
                        f'<div class="sls" style="font-size:{px:.0f}px" data-reel="{ts:.2f}" data-rdur="{spin + .25 * i:.2f}" data-ry="{-(K - 1) * 96}">{strip}</div>'
                        f'</div>{lb}</div>')
        k = f'<div class="k">{esc(sc["title"])}</div>' if sc.get("title") else ""
        return wrap(sc, f'<div class="slt" data-flash7="{ts + spin + .25 * (n - 1):.2f}">{k}<div class="slr">{"".join(cols)}</div></div>', y=240, h=190)

    def tpl_tear(sc, T):
        """Torn paper. style "reveal" (default): a paper sheet with a `cover` line tears in two along a jagged edge and the
        halves pull apart, stepped on twos, revealing the headline `text` (reveal_at). style "strip": a torn paper strip
        carrying `text` slides in. *word* = orange. Top band (y 250–420); the paper texture is on the graphic only."""
        t = T(sc.get("at"))
        rnd = random.Random(int(sc.get("seed", 8)))
        txt = sc.get("text", "Ang *totoong* dahilan")
        plain = re.sub(r"\*", "", txt)

        def poly(pts):
            return "polygon(" + ",".join(f"{x:.1f}px {y:.1f}px" for x, y in pts) + ")"
        if sc.get("style") == "strip":
            rt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + .1
            px = min(64.0, 64 * 760 / max(1.0, text_w(plain, 900, 64, -.02)))
            w, h = min(900, text_w(plain, 900, px, -.02) + 150), 150
            pts = ([(x, rnd.uniform(0, 7)) for x in range(0, int(w), 36)] + [(w - rnd.uniform(0, 16), y) for y in range(0, h + 1, 12)]
                   + [(x, h - rnd.uniform(0, 7)) for x in range(int(w), 0, -36)] + [(rnd.uniform(0, 16), y) for y in range(h, -1, -12)])
            return wrap(sc, f'<div class="tr-sw"><div class="tr-st" style="width:{w:.0f}px;height:{h}px;font-size:{px:.0f}px;clip-path:{poly(pts)}" '
                            f'data-strip7="{rt:.2f}">{tex()}<span>{rich(txt)}</span></div></div>', y=250, h=h)
        rt = T(sc.get("reveal_at")) if sc.get("reveal_at") else t + .9
        W, H = int(sc.get("w", 872)), int(sc.get("h", 170))
        xs = [0.0] + sorted(rnd.uniform(14, W - 14) for _ in range(W // 20)) + [float(W)]
        edge = [(x, H / 2 + rnd.uniform(-12, 12) + rnd.choice([0, 0, 0, -16, 14])) for x in xs]
        fib = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in edge)
        hp = min(66.0, 66 * (W - 90) / max(1.0, text_w(plain, 900, 66, -.03)))

        def half(pts, dy, rot):
            return (f'<div class="tr-hw" data-tear="{rt:.2f}" data-dy="{dy}" data-rot="{rot}"><div class="tr-pp" style="clip-path:{poly(pts)}">{tex()}'
                    f'<div class="tr-cv">{esc(sc.get("cover", "Akala mo…"))}</div><svg width="{W}" height="{H}"><path d="{fib}" fill="none" stroke="#FFFCF5" '
                    f'stroke-width="8" stroke-linejoin="round"/></svg></div></div>')
        return wrap(sc, f'<div class="tr" style="width:{W}px;height:{H}px"><div class="tr-h" style="font-size:{max(40.0, hp):.0f}px"><span>{rich(txt)}</span></div>'
                        f'{half([(0, 0), (W, 0)] + edge[::-1], -(H // 2 + 40), -3)}{half(edge + [(W, H), (0, H)], H // 2 + 40, 3)}</div>', y=250, h=H)

    BD_SLOTS = [(300, 520), (720, 600), (330, 900), (700, 1010), (420, 1250), (740, 1290)]
    BD_SIZE = {"card": (300, 210), "note": (270, 220), "photo": (270, 330)}

    def tpl_board(sc, T):
        """Investigation board (full-screen only): cards [{t, sub, icon, kind card|note|photo, src, pos [x, y], at}] (≤ 6)
        drop and pin onto a charcoal cork board, orange string draws between pins (links [[i, j]] or [{a, b, at}]),
        the camera pans to each new cluster and pulls back to the whole board on final_at. title = a chip on top."""
        t = T(sc.get("at"))
        rnd = random.Random(int(sc.get("seed", 5)))
        items, pins, info = [], [], []
        for i, c in enumerate(sc.get("cards", [])[:6]):
            kind = c.get("kind", "card")
            w, h = BD_SIZE.get(kind, BD_SIZE["card"])
            cx, cy = c.get("pos") or BD_SLOTS[i]
            rot = float(c.get("rot", rnd.choice([-5, -3.5, -2, 2.5, 4, 5])))
            ct = T(c.get("at")) if c.get("at") else t + .3 + i * .6
            if kind == "note":
                inner = f'<div class="bdn"><span>{rich(c.get("t", ""))}</span></div>'
            elif kind == "photo":
                ph = f' style="background-image:url(../clips/{esc(c["src"])})"' if c.get("src") else ""
                inner = f'<div class="bdp"><div class="ph"{ph}>{"" if c.get("src") else ic(c.get("icon", "image"))}</div><div class="cp">{esc(c.get("t", ""))}</div></div>'
            else:
                inner = f'<div class="bdc"><div class="ic">{ic(c.get("icon", "spark"))}</div><b>{esc(c.get("t", ""))}</b><span>{esc(c.get("sub", ""))}</span></div>'
            items.append(f'<div class="bd-it" style="left:{cx - w / 2:.0f}px;top:{cy - h / 2:.0f}px;width:{w}px;height:{h}px" data-pin7="{ct:.2f}" data-rot="{rot}">{inner}</div>')
            a = math.radians(rot)
            pxy = (cx + (h / 2 - 18) * math.sin(a), cy - (h / 2 - 18) * math.cos(a))  # the pin rides the rotated card's top edge
            pins.append(f'<i class="bd-pin" style="left:{pxy[0]:.0f}px;top:{pxy[1]:.0f}px" data-popin="{ct + .28:.2f}"></i>')
            info.append((pxy, ct, (cx, cy), (cx - w / 2 - 24, cx + w / 2 + 24)))
        strings = ""
        for l in sc.get("links", []):
            a_, b_ = (l["a"], l["b"]) if isinstance(l, dict) else l[:2]
            if max(a_, b_) >= len(info):
                continue
            (x1, y1), (x2, y2) = info[a_][0], info[b_][0]
            lt = T(l["at"]) if isinstance(l, dict) and l.get("at") else max(info[a_][1], info[b_][1]) + .45
            d = f"M{x1:.0f},{y1:.0f} Q{(x1 + x2) / 2:.0f},{(y1 + y2) / 2 + .12 * math.hypot(x2 - x1, y2 - y1):.0f} {x2:.0f},{y2:.0f}"  # string sags
            strings += (f'<path class="st" d="{d}" stroke="rgba(0,0,0,.4)" stroke-width="6" style="stroke-linecap:butt" transform="translate(3,7)" data-draw7="{lt:.2f}" data-dd=".4"/>'
                        f'<path class="st" d="{d}" stroke="#FF6A00" stroke-width="5" style="stroke-linecap:butt" data-draw7="{lt:.2f}" data-dd=".4"/>')
        Z = float(sc.get("zoom", 1.12))
        lo, hi = min([i[3][0] for i in info] + [540]), max([i[3][1] for i in info] + [540])

        def cam(c, z):
            x, y = 540 - c[0] * z, 880 - c[1] * z
            xa, xb = 64 - lo * z, 936 - hi * z  # x range that keeps every card inside x 64–936 (margins + button column)
            x = min(xb, max(xa, x)) if xa <= xb else 500 - (lo + hi) / 2 * z
            return [round(min(0.0, max(1080 - 1080 * z, x)), 1), round(min(0.0, max(1920 - 1920 * z, y)), 1), round(z, 3)]
        ks = [[0] + cam(info[0][2], Z)] if info else [[0, 0, 0, 1]]
        last = 0.0
        for _, ct, c, _ in info[1:]:
            if ct - .25 - last >= .9:
                ks.append([round(ct - .25, 2)] + cam(c, Z))
                last = ct - .25
        fin = T(sc.get("final_at")) if sc.get("final_at") else max([i[1] for i in info] + [0]) + .9
        ks.append([round(max(fin, last + .9), 2), 0, 0, 1])
        head = (f'<div class="mxw" style="top:{int(sc.get("y", 250))}px"><div class="mx-chip o"{at(t)} data-anim="pop">{esc(sc["title"])}</div></div>'
                if sc.get("title") else "")  # pinned on the board, so it moves with the camera instead of covering zoomed cards
        return (f'<div class="bd-cam" data-cam=\'{json.dumps(ks)}\'><div class="bd-dr" data-drift><div class="bd-bg">{tex()}</div>{head}{"".join(items)}'
                f'<svg class="mxsvg" viewBox="0 0 1080 1920">{strings}</svg>{"".join(pins)}</div></div>')

    DOCK_BG = [("linear-gradient(160deg,#4A3F39,#1E1714)", "#FFFFFF"), ("linear-gradient(160deg,#FFFFFF,#DCD3CA)", "#1A0B04"),
               ("linear-gradient(180deg,#FF9A4D,#FF6A00)", "#1A0B04"), ("linear-gradient(160deg,#7A4A2A,#2A1A10)", "#FFFFFF"),
               ("linear-gradient(160deg,#F4F1EA,#C9BFB4)", "#1A0B04"), ("linear-gradient(160deg,#2B231F,#0C0908)", "#FFFFFF")]

    def tpl_dock(sc, T):
        """Glass tool dock: a glass pill (its own gradient fill + edge + highlight — never a backdrop blur over the footage)
        with 4–6 app tiles [{t, icon}]; tiles pop in, a magnify wave runs across, then `pick` grows with an orange ring and
        its label (label, pick_at) rises under it. Top band by default (y 244–410), or the chest band."""
        t = T(sc.get("at"))
        tiles = sc.get("tiles", [{"t": "Claude", "icon": "spark"}, {"t": "Studio", "icon": "wand"}, {"t": "Captions", "icon": "type"}])[:6]
        n = len(tiles)
        pick = max(0, min(n - 1, int(sc.get("pick", 0))))
        tw = t + .35 + n * .07 + .25  # magnify wave start
        pt = T(sc.get("pick_at")) if sc.get("pick_at") else tw + n * .12 + .35
        out = []
        for i, it in enumerate(tiles):
            bgi, ink = DOCK_BG[i % len(DOCK_BG)]
            out.append(f'<div class="dk-t" data-popin="{t + .35 + i * .07:.2f}" data-mag="{tw + i * .12:.2f}"{" data-dpick=" + chr(34) + f"{pt:.2f}" + chr(34) if i == pick else ""}>'
                       f'<div class="dk-i" style="background:{it.get("bg", bgi)}"><svg viewBox="0 0 24 24" style="stroke:{ink}">{ICONS.get(it.get("icon", "spark"), ICONS["spark"])}</svg></div>'
                       f'<i class="dk-dot"></i></div>')
        label = sc.get("label") or tiles[pick].get("t", "")
        lab = f'<div class="dk-lb" style="left:{20 + pick * 92 + 38}px"{at(pt + .15)} data-anim="up"><span>{esc(label)}</span></div>' if label else ""
        return wrap(sc, f'<div class="dk">{"".join(out)}{lab}</div>', y=244, h=170)

    def tpl_frame3d(sc, T):
        """Floating device frame (full-screen B-roll page): a screenshot (`src` in motion/clips, else a mock-up) in a generic
        browser window (url) or a phone (device "phone"), tilted in 3D over the brand background and a dot grid; it floats
        in, drifts flatter while held and lifts out. kicker / title sit above it."""
        t = T(sc.get("at"))
        if sc.get("device") == "phone":
            w, h = int(sc.get("w", 420)), int(sc.get("h", 860))
            y = int(sc.get("y", 520))
            inner = f'<div class="f3 ph" data-f3d="{t:.2f}"><div class="f3-scr">{shot_html(sc, w - 34, h - 34)}</div></div>'
        else:
            w = int(sc.get("w", 760))
            sh = round(w * 560 / 860)
            h, y = 48 + sh, int(sc.get("y", 660))
            inner = (f'<div class="f3" data-f3d="{t:.2f}"><div class="f3-bar"><i></i><i></i><i></i><div class="f3-url">{ic("lock")}{esc(sc.get("url", "localhost:8765"))}</div></div>'
                     f'<div class="f3-scr">{shot_html(sc, w, sh)}</div></div>')
        return (f'<div class="f3-grid"></div>{fhead(sc, sc.get("head_y", y - 250 if sc.get("device") != "phone" else 300))}'
                f'<div class="f3w" style="left:{540 - w // 2}px;top:{y}px;width:{w}px;height:{h}px">{inner}</div>')

    templates = dict(scribble=tpl_scribble, target=tpl_target, ping=tpl_ping, keys=tpl_keys, island=tpl_island, search=tpl_search,
                     post=tpl_post, call=tpl_call, tier=tpl_tier, score=tpl_score, price=tpl_price, timer=tpl_timer, ring=tpl_ring,
                     chart=tpl_chart, timeline=tpl_timeline, streak=tpl_streak, flap=tpl_flap, glitch=tpl_glitch, redact=tpl_redact,
                     define=tpl_define, pov=tpl_pov, rank=tpl_rank, ransom=tpl_ransom, flip=tpl_flip, polaroid=tpl_polaroid,
                     achieve=tpl_achieve, sticker=tpl_sticker, burst=tpl_burst, rail=tpl_rail, ff=tpl_ff,
                     wipe=tpl_wipe, loupe=tpl_loupe, thread=tpl_thread, voicenote=tpl_voicenote, feed=tpl_feed, receipt=tpl_receipt,
                     venn=tpl_venn, cloud=tpl_cloud, slot=tpl_slot, tear=tpl_tear, board=tpl_board, dock=tpl_dock, frame3d=tpl_frame3d)
    assert set(templates) == set(TYPES)
    return dict(templates=templates, css=CSS, js=JS, types=TYPES)


def is_fs(sc):
    return bool(sc.get("bg")) or sc.get("type") in FS_ONLY


def panel_of(sc):
    return "mx" + (" fs" if is_fs(sc) else "")


def caption_of(sc):
    """Captions under a v7 graphic: chest-band / full-screen cards push them away, top-band ones leave them be."""
    dflt = 236
    if sc.get("type") in CB_TYPES:
        dflt = (sc.get("box") or [0, 1150])[1] if sc.get("type") == "cloud" else 1150
    y = int(sc.get("y", dflt))
    if is_fs(sc):
        return "low"
    return "top" if 1000 <= y <= 1500 else "normal"


# ---------------------------------------------------------------- the Studio gallery (live samples, seconds-timed)
GALLERY = [
    dict(id="scribble", type="scribble", dur=4.5, shape="circle", box=[330, 840, 420, 150], label="Ito yung button", at=0.3),
    dict(id="arrow", type="scribble", dur=4.5, shape="arrow", box=[560, 980, 300, 120], label="I-click mo 'to", at=0.3),
    dict(id="target", type="target", dur=4.5, box=[250, 820, 580, 160], label="Export final 1080p", click=[540, 900], at=0.3),
    dict(id="ping", type="ping", dur=4.0, point=[640, 960], label="Dito", at=0.3),
    dict(id="keys", type="keys", dur=4.0, keys=["⌘", "Shift", "K"], label="Command palette", at=0.2),
    dict(id="island", type="island", dur=4.5, icon="bell", title="Na-approve na!", body="Bayad na ang client — ₱45,000", time="now", at=0.2),
    dict(id="search", type="search", dur=6.0, query="paano mag-edit gamit si Claude", suggestions=["paano mag-edit gamit si Claude AI", "claude video editor libre", "claude vs capcut"], pick=1, at=0.2),
    dict(id="post", type="post", dur=6.0, name="Joshua", handle="@joshualadero", text="Gumawa ako ng sarili kong video editor gamit si Claude — at hindi na ako babalik sa CapCut.", at=0.2),
    dict(id="call", type="call", dur=4.5, caller="Client", sub="incoming call… 2:14 AM", answer="decline", at=0.2),
    dict(id="tier", type="tier", dur=6.0, rows=[{"tier": "S", "items": [{"t": "Claude", "icon": "spark", "at": 1.0}]}, {"tier": "A", "items": [{"t": "CapCut", "at": 1.7}, {"t": "Premiere", "at": 2.3}]},
                                                 {"tier": "B", "items": [{"t": "Canva", "at": 2.9}]}], at=0.2),
    dict(id="score", type="score", dur=6.0, kicker="Rating · Studio", rows=[{"t": "Bilis", "v": 5}, {"t": "Presyo", "v": 5}, {"t": "Output", "v": 4}], final=9.2, verdict="WORTH IT", at=0.2),
    dict(id="price", type="price", dur=4.5, old="₱1,100/mo", new="LIBRE", badge="−100%", at=0.2),
    dict(id="timer", type="timer", dur=6.0, **{"from": 600, "to": 0}, label="edit time", at=0.2),
    dict(id="ring", type="ring", dur=4.5, pct=87, label="ng oras, editing", at=0.2),
    dict(id="chart", type="chart", dur=5.0, kicker="Views · 30 days", points=[1, 1.4, 1.2, 2.2, 3.1, 4.6, 6.8], pill="↑ 6.8×", at=0.2),
    dict(id="timeline", type="timeline", dur=5.5, nodes=[{"d": "OKT 17", "t": "Unang edit"}, {"d": "OKT 19", "t": "Brand toolkit"}, {"d": "OKT 21", "t": "Studio v2"}], at=0.2),
    dict(id="streak", type="streak", dur=5.0, days=30, upto=14, at=0.2),
    dict(id="flap", type="flap", dur=4.0, text="NEW TOOL", at=0.2),
    dict(id="glitch", type="glitch", dur=4.5, text="LEAKED", kicker="AI UPDATE", at=0.2),
    dict(id="redact", type="redact", dur=5.0, kicker="CLASSIFIED", lines=["Ang editor ko ay", "[[libre]] at [[open source]]"], reveal_at=1.6, at=0.2),
    dict(id="define", type="define", dur=5.0, word="agentic", phon="/eɪˈdʒɛn.tɪk/", pos="adjective", **{"def": "AI na *kumikilos* para sa'yo — hindi lang sumasagot."}, at=0.2),
    dict(id="pov", type="pov", dur=4.0, text="unang araw mo gamit si Claude", at=0.0),
    dict(id="rank", type="rank", dur=5.0, of=5, steps=[{"n": 1, "at": 0.3}, {"n": 2, "at": 1.6}, {"n": 3, "at": 2.9}], at=0.2),
    dict(id="ransom", type="ransom", dur=4.5, text="ang sikreto ng mga editor", at=0.2),
    dict(id="flip", type="flip", dur=5.5, myth="Kailangan mong marunong mag-*code*", fact="Sasabihin mo lang kay *Claude*", flip_at=1.8, at=0.2),
    dict(id="polaroid", type="polaroid", dur=5.0, items=[{"t": "Day 1", "cap": "unang edit"}, {"t": "Day 3", "cap": "studio"}, {"t": "Day 5", "cap": "v2!"}], at=0.2),
    dict(id="achieve", type="achieve", dur=4.5, title="Unang auto-edit mo", at=0.2),
    dict(id="sticker", type="sticker", dur=3.5, text="LEGIT", pos=[110, 300], rot=-7, at=0.3),
    dict(id="burst", type="burst", dur=3.0, origin=[540, 520], at=0.3),
    dict(id="rail", type="rail", dur=5.5, items=[{"t": "Upload"}, {"t": "Pick a look"}, {"t": "Render"}], y=300, at=0.2),
    dict(id="ff", type="ff", dur=3.5, speed="4×", label="FAST-FORWARD", at=0.2),
    # next wave (2026-10-21)
    dict(id="wipe", type="wipe", dur=5.0, bg=True, kicker="THUMBNAIL", title="v1 vs *v2*", reveal_at=0.6, at=0.1),
    dict(id="loupe", type="loupe", dur=5.0, bg=True, shot=[64, 300, 872, 568], point=[440, 857], lens=[330, 1120], r=190, zoom=2.4,
         label="₱0/mo — libre talaga", at=0.3),
    dict(id="thread", type="thread", dur=6.0, bg=True, community="Video Editing PH", user="@newbie_editor", time="5h", votes=1248,
         title="May libreng editor ba na may auto-captions at motion graphics?", body="Pagod na ako sa subscription. Kahit simple lang, basta mabilis.",
         replies=[{"user": "@joshua", "time": "4h", "text": "Ginawa ko 'to gamit si *Claude* — libre at nasa Mac mo lang.", "votes": 342, "top": True},
                  {"user": "@kreator.ph", "time": "3h", "text": "Legit. Dalawang linggo ko nang gamit.", "votes": 87}], at=0.1),
    dict(id="voicenote", type="voicenote", dur=6.0, sender="Client · voice message", press_at=1.0, at=0.2),
    dict(id="feed", type="feed", dur=6.0, bg=True, items=["5 AI tools na libre", "POV: unang client mo", "Paano mag-caption sa phone", "CapCut vs Premiere",
                                                       "Day 14 ng 30", "Bakit ako tumigil sa CapCut", "Gumawa ako ng sariling editor", "Behind the scenes"],
         pick=6, at=0.1),
    dict(id="receipt", type="receipt", dur=6.0, title="EDIT RECEIPT", meta="OKT 21 2026 · 09:41",
         items=[["Auto-captions", "₱0"], ["Motion graphics", "₱0"], ["Color + audio", "₱0"], ["Oras na natipid", "6 hrs"]],
         total=["TOTAL", "₱0.00"], stamp="LIBRE", at=0.2),
    dict(id="venn", type="venn", dur=5.0, bg=True, kicker="ANG SWEET SPOT", sets=[{"t": "Mabilis"}, {"t": "Libre"}, {"t": "Pro ang dating"}],
         center="Studio", at=0.3),
    dict(id="cloud", type="cloud", dur=5.5, bg=True, kicker="MGA TANONG NIYO SA COMMENTS",
         words=[["libre ba?", 5], ["Mac lang?", 4], ["Windows?", 3], ["paano i-install?", 4], ["presyo?", 3], ["captions?", 2], ["Taglish?", 3],
                ["gaano kabilis?", 3], ["may tutorial?", 2], ["safe ba?", 2], ["4K?", 2], ["templates?", 2], ["CapCut?", 3], ["AI voice?", 1],
                ["offline?", 2], ["magkano?", 4]], pick="libre ba?", at=0.2),
    dict(id="slot", type="slot", dur=5.0, title="Anong gagamitin today?",
         reels=[{"items": ["CapCut", "Premiere", "Canva", "DaVinci", "Claude"], "pick": "Claude", "label": "TOOL"},
                {"items": ["YouTube", "TikTok", "Shorts", "Reels"], "pick": "Reels", "label": "FORMAT"},
                {"items": ["₱1,100", "₱499", "₱2,500", "₱0"], "pick": "₱0", "label": "PRESYO"}], at=0.2),
    dict(id="tear", type="tear", dur=4.5, cover="Akala mo…", text="Ang *totoong* dahilan", reveal_at=1.0, at=0.2),
    dict(id="board", type="board", dur=8.0, title="PAANO KONEKTADO?",
         cards=[{"t": "Claude", "sub": "ang utak", "icon": "spark"}, {"t": "HyperFrames", "sub": "motion graphics", "icon": "film"},
                {"t": "Studio", "kind": "photo", "icon": "wand"}, {"t": "₱0 / buwan", "kind": "note"}, {"t": "Reels · TikTok · Shorts", "kind": "note"}],
         links=[[0, 1], [0, 2], [1, 3], [2, 3], [2, 4]], at=0.2),
    dict(id="dock", type="dock", dur=5.0, tiles=[{"t": "Whisper", "icon": "message"}, {"t": "FFmpeg", "icon": "terminal"}, {"t": "Claude", "icon": "spark"},
                                                 {"t": "HyperFrames", "icon": "film"}, {"t": "Studio", "icon": "wand"}], pick=2, label="Claude — ang utak", at=0.2),
    dict(id="frame3d", type="frame3d", dur=5.0, kicker="ITO YUNG APP", title="*Studio* — libre, sa Mac mo", url="localhost:8765", at=0.2),
]

# catalog for the Studio (brandkit.VISUALS-style): id, name, note, group, gallery page
CATALOG = [
    ("scribble", "Marker circle", "Hand-drawn circle around a button or word on screen", "attention"),
    ("arrow", "Marker arrow", "A drawn arrow points at what you're talking about", "attention"),
    ("target", "Target ring", "Ring + label on a UI element, with a click", "attention"),
    ("ping", "“Dito” ping", "Rings radiate from one spot", "attention"),
    ("loupe", "Magnifier loupe", "A lens zooms into tiny text on a screenshot", "attention"),
    ("keys", "Keyboard shortcut", "Keycaps press one after another", "demo"),
    ("rail", "Step rail", "Step 1 → 2 → 3 lights up as you go", "demo"),
    ("ff", "Fast-forward badge", "4× badge on a sped-up part", "demo"),
    ("wipe", "Before / after", "A divider wipes from before to after", "demo"),
    ("dock", "Tool dock", "A glass dock of your tools — one gets picked", "demo"),
    ("frame3d", "3D device frame", "Your screenshot floats in a tilted browser", "demo"),
    ("island", "Island alert", "Phone alert pops open at the top", "phone"),
    ("search", "Search bar", "A question types in, suggestions open", "phone"),
    ("post", "Social post", "A post card with likes counting up", "phone"),
    ("call", "Incoming call", "A call banner rings — comedic interrupt", "phone"),
    ("thread", "Forum thread", "A question with replies on connector lines", "phone"),
    ("voicenote", "Voice note", "A voice message plays its waveform", "phone"),
    ("feed", "Feed scroll", "A phone flicks through posts, stops on one", "phone"),
    ("tier", "Tier list", "Tools drop into S / A / B rows", "data"),
    ("score", "Scorecard", "Stars fill, a final score counts up", "data"),
    ("price", "Price slash", "Old price struck, new price slams in", "data"),
    ("timer", "Countdown", "A timer ring ticks down", "data"),
    ("ring", "Progress ring", "A ring fills to a percentage", "data"),
    ("chart", "Growth chart", "A line draws up, a ×N pill pops", "data"),
    ("timeline", "Timeline", "Dates pop along a line", "data"),
    ("streak", "Streak grid", "Day N of 30 fills up", "data"),
    ("receipt", "Receipt print", "A receipt prints the costs line by line", "data"),
    ("venn", "Venn diagram", "Circles slide together, the overlap lights up", "data"),
    ("flap", "Split-flap board", "Airport-board letters flip into a word", "type"),
    ("glitch", "Glitch title", "RGB-split headline (text only)", "type"),
    ("redact", "Redacted reveal", "Black bars wipe away the secret", "type"),
    ("define", "Definition card", "Dictionary entry for a jargon word", "type"),
    ("pov", "POV label", "POV chip + your scenario, on frame 0", "type"),
    ("rank", "Rank badge", "#1 of 5 badge for list videos", "type"),
    ("ransom", "Ransom note", "Cut-out words, collage style", "type"),
    ("cloud", "Word cloud", "Words fly into a cloud, one lights up", "type"),
    ("tear", "Torn paper", "Paper tears open on the real headline", "type"),
    ("flip", "Myth / Fact flip", "A card flips from myth to fact", "card"),
    ("polaroid", "Polaroid stack", "Photos drop onto a pile", "card"),
    ("achieve", "Achievement", "“Achievement unlocked” toast", "card"),
    ("sticker", "Sticker", "A die-cut sticker slaps on", "card"),
    ("burst", "Confetti", "A burst for a win moment", "card"),
    ("slot", "Slot reels", "Reels spin and land on the pick", "card"),
    ("board", "Investigation board", "Pinned cards tied with orange string", "card"),
]
GROUPS = [("attention", "Point at it"), ("demo", "Screen demo"), ("phone", "Phone & apps"), ("data", "Numbers & rankings"),
          ("type", "Type & text"), ("card", "Cards & fun")]
