// Real Studio screens for the tutorial: 1440×900 at 2× + the rects the cursor clicks, → shots/*.png + shots/layout.json,
// plus a short frame sequence of one 2026 motion card playing (shots/play_<id>/).
// Needs the Studio running on :8765. Read-only: it never presses a control that saves anything. "After" states
// (a note added, a kit saved, Claude running) are drawn into the page the way the Studio draws them.
// The Studio is shown as it looks with Claude Code installed (the tutorial installs through it): /api/claude answers "available".
// usage:  NODE_PATH=<dir with puppeteer-core> ../../tools/node/bin/node capture.mjs
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const CHROME = `${process.env.HOME}/.cache/hyperframes/chrome/chrome-headless-shell/mac_arm-152.0.7977.30/chrome-headless-shell-mac-arm64/chrome-headless-shell`;
const BASE = "http://127.0.0.1:8765/?p=img_7779&shot=1&lang=en";
const PLAY = { id: process.env.PLAY || "wipe", from: 0.0, to: 3.2, fps: 30 };  // the card that plays on hover in the video

function pick(i, sel = "#main .grid .card") {  // move the "Picked" badge to card i, the way a click would look
  return `(() => { const cs = [...document.querySelectorAll('${sel}')]; cs.forEach((c) => c.classList.remove('picked')); cs[${i}] && cs[${i}].classList.add('picked'); })()`;
}
function running(box, events) {  // Claude's live job view, as claudeView() draws it while a job runs
  const ev = events.map((e) => `<div>› ${e}</div>`).join("");
  return `(() => { const v = document.querySelector('#${box} .cview'); if (v) v.innerHTML = '<div style="margin-top:12px"><span class="warn">● Claude is editing…</span></div><div class="cev">${ev}</div>'; })()`;
}
const NOTE = "cut the dead air";  // build.py types the same note
const typed = `(() => { document.getElementById('nText').value = '${NOTE}'; document.getElementById('nAdd').textContent = 'Add @ 0:42'; })()`;
const added = `(() => { document.getElementById('nText').value = ''; document.getElementById('nAdd').textContent = 'Add @ 0:42';
  document.getElementById('nList').innerHTML = '<div class="nl"><span class="tm">0:42</span><b>${NOTE}</b><button>✕</button></div>'; })()`;
const hookOn = `(() => { const c = document.querySelector('.hlc'); if (!c) return; c.classList.add('on'); const q = c.querySelector('q').textContent;
  c.insertAdjacentHTML('beforebegin', '<div class="li" style="margin-bottom:12px"><span class="ok">●</span><span>Cold open is on: “' + q + '”</span><button class="fx tlink" style="margin-left:auto">Turn off</button></div>'); })()`;
const postDone = `(() => { document.getElementById('pkFiles').innerHTML = '<a class="tlink">⇩ Download all (.zip)</a>' + ['cover.jpg', 'video_9x16.mp4', 'video_1x1.mp4', 'video_16x9.mp4', 'captions.srt'].map((f) => '<a class="tlink">' + f + '</a>').join(''); })()`;
const kitTyped = `(() => { document.getElementById('kName').value = 'My brand'; })()`;
const kitSaved = `(() => { document.getElementById('kName').value = ''; document.getElementById('kList').innerHTML = '<div class="kl"><span class="sw" style="background:#FF6A00"></span><b>My brand</b><small>Signature · Thumbnail · Pop</small><button>Apply</button><a class="tlink" style="padding:4px 9px">⇩</a><button>★</button></div>'; })()`;
const AUTO_EV = ["Read · transcript (158 s, 412 words)", "Edit · decisions.json — 15 cuts, hook 0:20–0:25", "Write · scenes.json — 6 motion graphics", "Bash · ./vedit render --preview"];
const NOTE_EV = ["Read · comments.json — 1 open note", "Edit · decisions.json — cut 0:42–0:45", "Bash · ./vedit render --preview"];


// Brief ("Tell Claude what you want") and Style references: the same steps a creator takes, drawn into the page
const BRIEF = "yellow keywords, big captions at the bottom, fast cuts";
const chip = (q, v) => `document.querySelector('.brc button[data-q="${q}"][data-v="${v}"]').classList.add('on');`;
const CHIPS = [chip("platform", "tiktok"), chip("vibe", "bold"), chip("captions", "big"), chip("graphics", "lots")];
const res = (rows, arrow) => `<div class="brres"><h5>What changed</h5>${rows.map(([p, v, w]) => `<div class="li"><span class="ok">✓</span><span><b>${p}</b> ${arrow} ${v} <small>· ${w}</small></span></div>`).join("")}</div>`;
const BRIEF_OUT = res([["Colours", "Sunshine", "you said “yellow”"], ["Fonts", "Punchy", "you picked bold"], ["Captions", "Highlight · Lower third · size 124", "you said “big captions”"],
  ["Graphics", "Full b-roll", "you picked lots graphics"], ["Hook", "Thumbnail · boxed", "you picked bold"], ["Pace", "fast", "you said “fast”"]], "→");
const STYLE_OUT = res([["Colours", "3-month roadmap", "its highlight colour is #D35C17"], ["Captions", "JEV classification reel", "mixed-case captions, about 2 words at a time, in the lower third"],
  ["Fonts", "3-month roadmap", "clean sans-serif text"], ["Graphics", "3-month roadmap", "graphics on 62% of its frames, a cut every 5.29 s"], ["Pace", "3-month roadmap", "10.7 cuts a minute"]], "←");
const briefText = `document.getElementById('brText').value = ${JSON.stringify(BRIEF)};`;
const briefDone = `document.getElementById('brOut').innerHTML = ${JSON.stringify(BRIEF_OUT)};`;
// one reference so far: hide the second card and its column in Mix & match
const oneRef = `(() => { const c = document.querySelectorAll('#rfList .rfc'); if (c[1]) c[1].remove(); document.querySelectorAll('.rfm tr').forEach((tr) => { if (tr.children[2]) tr.children[2].remove(); }); })();`;
const busyRef = `document.querySelector('#rfList .rfadd').insertAdjacentHTML('beforebegin', '<div class="rfc busy"><div class="rfb"><b>JEV classification reel</b><small class="warn">Studying its style…</small></div></div>');`;
const pickJev = `(() => { document.querySelectorAll('.rfm button[data-p="captions"]').forEach((b) => b.classList.toggle('on', b.dataset.id === 'jev-classification-reel')); })();`;
const styleDone = `document.getElementById('rfOut').innerHTML = ${JSON.stringify(STYLE_OUT)};`;

// rect finders: "#css" / ".css" → querySelector; "text:Label" → smallest visible element with that text; "nth:.css:2" → nth match
const STATES = [
  { id: "start", q: "step=start", rects: { name: "#sname", did: "text:What's already done", auto: "#autoBox", autoBtn: "text:Auto-edit this video", next: "#next" } },
  { id: "brief0", q: "step=start", into: "#brBox", rects: { box: "#brBox", tiktok: '.brc button[data-v="tiktok"]', bold: '.brc button[data-v="bold"]', big: '.brc button[data-v="big"]',
      lots: '.brc button[data-v="lots"]', text: "#brText", go: '[data-pro="brgo"]' } },
  { id: "brief1", q: "step=start", into: "#brBox", js: CHIPS.slice(0, 1).join(""), rects: {} },
  { id: "brief2", q: "step=start", into: "#brBox", js: CHIPS.slice(0, 2).join(""), rects: {} },
  { id: "brief3", q: "step=start", into: "#brBox", js: CHIPS.slice(0, 3).join(""), rects: {} },
  { id: "brief4", q: "step=start", into: "#brBox", js: CHIPS.join(""), rects: {} },
  { id: "brief5", q: "step=start", into: "#brBox", js: CHIPS.join("") + briefText, rects: {} },
  { id: "brief6", q: "step=start", into: '[data-pro="brgo"]', js: CHIPS.join("") + briefText + briefDone, rects: { out: "#brOut", go: '[data-pro="brgo"]' } },
  { id: "refs1", q: "step=start", into: "#rfBox", js: oneRef, rects: { box: "#rfBox", add: ".rfadd", card1: "nth:#rfList .rfc:0" } },
  { id: "refs2", q: "step=start", into: "#rfBox", js: oneRef + busyRef, rects: { busy: ".rfc.busy" } },
  { id: "refs3", q: "step=start", into: "#rfBox", rects: { card2: "nth:#rfList .rfc:1", mix: ".rfm" } },
  { id: "refs4", q: "step=start", into: ".rfm", rects: { mix: ".rfm", jev: '.rfm button[data-p="captions"][data-id="jev-classification-reel"]', go: '[data-pro="rfgo"]' } },
  { id: "refs5", q: "step=start", into: ".rfm", js: pickJev, rects: { go: '[data-pro="rfgo"]' } },
  { id: "refs6", q: "step=start", into: ".rfm", js: pickJev + styleDone, rects: { out: "#rfOut" } },
  { id: "autobox", q: "step=start", into: "#autoBox", rects: { auto: "#autoBox", autoBtn: "text:Auto-edit this video" } },
  { id: "auto_run", q: "step=start", into: "#autoBox", js: running("autoBox", AUTO_EV), rects: { auto: "#autoBox" } },
  { id: "drop", q: "step=start", into: "#drop", rects: { drop: "#drop", next: "#next" } },
  { id: "drop_on", q: "step=start", into: "#drop", js: `document.getElementById('drop').classList.add('hover')`, rects: { drop: "#drop" } },
  { id: "drop_busy", q: "step=start", into: "#drop", js: `document.getElementById('upst').textContent = 'Transcribing and cleaning the cuts… (a few minutes)'`, rects: { drop: "#drop" } },
  { id: "colours", q: "step=colours", rects: { c3: "nth:.card:2", next: "#next" } },
  { id: "colours_3", q: "step=colours", js: pick(2), rects: { c3: "nth:.card:2", next: "#next" } },
  { id: "fonts", q: "step=fonts", rects: { c2: "nth:.card:1", next: "#next" } },
  { id: "fonts_2", q: "step=fonts", js: pick(1), rects: { c2: "nth:.card:1", next: "#next" } },
  { id: "hook", q: "step=hook", into: "text:Hook Lab", rects: { lab: "#hlBox", cand: "nth:.hlc:0", use: "text:Use as cold open", fields: "nth:.hlf:0", next: "#next" } },
  { id: "hook_on", q: "step=hook", into: "text:Hook Lab", js: hookOn, rects: { on: "text:Cold open is on", next: "#next" } },
  { id: "captions", q: "step=captions", rects: { c2: "nth:.card:1", next: "#next" } },
  { id: "captions_2", q: "step=captions", js: pick(1), rects: { c2: "nth:.card:1", safe: "#safeBtn", phone: "#phone", next: "#next" } },
  { id: "captions_safe", q: "step=captions", js: pick(1), click: "#safeBtn", rects: { safe: "#safeBtn", phone: "#phone", next: "#next" } },
  { id: "visuals", q: "step=visuals", rects: { trend: "text:2026 trends", next: "#next" } },
  { id: "visuals_t", q: "step=visuals&sub=trend", wait: 5000, rects: { lead: "nth:#main p.lead:1", next: "#next" } },
  { id: "visuals_wipe", q: "step=visuals&sub=trend", into: '#main [data-mv="wipe"]', wait: 7000,
    rects: { wipe: '#main [data-mv="wipe"]', dock: '#main [data-mv="dock"]', loupe: '#main [data-mv="loupe"]', watchTab: '#steps button[data-i="7"]' } },
  { id: "visuals_wipe_pick", q: "step=visuals&sub=trend", into: '#main [data-mv="wipe"]', wait: 7000,
    js: `document.querySelector('#main [data-mv="wipe"]').classList.add('picked')`, rects: { wipe: '#main [data-mv="wipe"]', watchTab: '#steps button[data-i="7"]' } },
  { id: "watch", q: "step=watch", rects: { prev: "text:Render preview", fin: "text:Export final 1080p", run: "text:Run check", health: "#hBox", fix: "text:Natural colour" } },
  { id: "notes", q: "step=watch", into: "#nBox", js: `document.getElementById('nAdd').textContent = 'Add @ 0:42'`, rects: { nbox: "#nBox", ntext: "#nText", nadd: "#nAdd", apply: "text:Apply notes with Claude" } },
  { id: "notes_typed", q: "step=watch", into: "#nBox", js: typed, rects: { nadd: "#nAdd" } },
  { id: "notes_added", q: "step=watch", into: "#nBox", js: added, rects: { nlist: "#nList", apply: "text:Apply notes with Claude" } },
  { id: "notes_run", q: "step=watch", into: "#nBox", js: `${added};${running("nBox", NOTE_EV)}`, rects: { nbox: "#nBox" } },
  { id: "post", q: "step=watch", into: "#pkBox", rects: { post: "text:Build Post Kit", pkbox: "#pkBox" } },
  { id: "post_done", q: "step=watch", into: "#pkBox", js: postDone, rects: { files: "#pkFiles", pkbox: "#pkBox" } },
  { id: "kit", q: "step=watch", into: "#kBox", rects: { kbox: "#kBox", kname: "#kName", ksave: "text:Save kit" } },
  { id: "kit_typed", q: "step=watch", into: "#kBox", js: kitTyped, rects: { ksave: "text:Save kit" } },
  { id: "kit_saved", q: "step=watch", into: "#kBox", js: kitSaved, rects: { klist: "#kList", kbox: "#kBox" } },
];

const FIND = `window.__R = (spec) => {
  const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 ? r : null; };
  let el = null;
  if (spec.startsWith('text:')) {
    const want = spec.slice(5); let best = null;
    for (const e of document.querySelectorAll('button,a,label,h2,h3,h4,b,span,div')) {
      const tx = (e.innerText || '').trim(); if (!tx.includes(want)) continue;
      const r = vis(e); if (!r) continue; const a = r.width * r.height;
      if (!best || a < best.a) best = { e, a };
    }
    el = best && best.e;
  } else if (spec.startsWith('nth:')) { const [, sel, n] = spec.match(/^nth:(.+):(\\d+)$/); el = document.querySelectorAll(sel)[+n]; }
  else el = document.querySelector(spec);
  if (!el) return null;
  const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
};`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, protocolTimeout: 120000, args: ["--hide-scrollbars", "--mute-audio"] });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
await page.setRequestInterception(true);
page.on("request", (r) => (r.url().endsWith("/api/claude")
  ? r.respond({ status: 200, contentType: "application/json", body: JSON.stringify({ available: true, bin: "claude", job_keys: [] }) })
  : r.continue()));

async function open(s) {
  await page.goto(`${BASE}&${s.q}`, { waitUntil: "networkidle2", timeout: 60000 });
  await page.evaluate(FIND);
  await sleep(s.wait || 1800);  // fonts, lazy thumbs, hook lab, card previews
  if (s.into) {
    await page.evaluate((spec) => { const r = window.__R(spec), M = document.getElementById("main"); if (r && M) M.scrollTop += r[1] - 200; }, s.into);
    await sleep(900);
  }
}

const out = {};
const SH = path.join(HERE, "shots");
fs.mkdirSync(SH, { recursive: true });
for (const s of process.env.ONLY_PLAY ? [] : STATES.filter((x) => !process.env.ONLY || process.env.ONLY.split(',').includes(x.id))) {
  await open(s);
  if (s.click) { await page.click(s.click); await sleep(400); }  // UI-only toggles (safe zones)
  if (s.js) { await page.evaluate(s.js); await sleep(300); }
  const rects = {};
  for (const [k, spec] of Object.entries(s.rects)) rects[k] = await page.evaluate((x) => window.__R(x), spec);
  const scroll = await page.evaluate(() => (document.getElementById("main") || {}).scrollTop || 0);
  await page.screenshot({ path: path.join(SH, `${s.id}.png`) });
  out[s.id] = { q: s.q, scroll, rects };
  console.log(s.id.padEnd(18), JSON.stringify(rects));
}

// one 2026 card playing, the way it plays when you hover it: seek its own timeline frame by frame
if (!process.env.ONLY) {
await open({ q: "step=visuals&sub=trend", into: `#main [data-mv="${PLAY.id}"]`, wait: 7000 });
const card = await page.evaluate((id) => window.__R(`#main [data-mv="${id}"]`), PLAY.id);
const pd = path.join(SH, `play_${PLAY.id}`);
fs.rmSync(pd, { recursive: true, force: true });
fs.mkdirSync(pd);
const n = Math.round((PLAY.to - PLAY.from) * PLAY.fps);
for (let k = 0; k < n; k++) {
  await page.evaluate((id, t) => {
    const f = document.querySelector(`#main [data-mv="${id}"] iframe.gcard`);
    const tl = f && f.contentWindow.__timelines && f.contentWindow.__timelines[f.dataset.gal];
    if (tl) { tl.seek(t); }
  }, PLAY.id, PLAY.from + k / PLAY.fps);
  await sleep(40);
  await page.screenshot({ path: path.join(pd, `${String(k).padStart(3, "0")}.jpg`), type: "jpeg", quality: 86,
    clip: { x: card[0], y: card[1], width: card[2], height: card[3] } });
}
out.play = { id: PLAY.id, rect: card, frames: n, fps: PLAY.fps };
console.log("play", PLAY.id, card, n, "frames");
}
if (!process.env.ONLY_PLAY) { const old = process.env.ONLY && fs.existsSync(path.join(SH, "layout.json")) ? JSON.parse(fs.readFileSync(path.join(SH, "layout.json"))) : {}; fs.writeFileSync(path.join(SH, "layout.json"), JSON.stringify({ ...old, ...out }, null, 1)); }
await browser.close();
