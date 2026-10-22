/* Studio v2 — Auto-edit with Claude · Hook Lab · Edit Health · Talk-to-edit · Post Kit · Brand Kits · live / safe-zone toggles.
   Loaded after studio.html's main script: it adds panels to the Start, Hook and Watch steps (by wrapping render()),
   and talks to studio_pro.py through server.py. Everything it changes is written to the same decisions.json /
   scenes.json Claude edits by hand. */
(() => {
  Object.assign(I18N.en, {
    hint: "Live preview · graphics play as they will render", live_on: "Live graphics on — scene pages play in the phone", live_off: "Showing the last render's graphics",
    live_t: "Live graphics (no render needed)", safe_t: "Show TikTok / Reels / Shorts buttons", safe_names: ["", "TikTok", "Reels", "Shorts"],
    auto_h: "✨ Auto-edit with Claude", auto_s: "Claude does the editorial pass: retakes, repeats, dead air, the hook and the motion graphics, then the checks — and renders a preview.",
    auto_b: "✨ Auto-edit this video", auto_new: "Auto-edit every new upload", need_claude: "Needs Claude Code on this computer —", install: "how to install",
    c_run: "Claude is editing…", c_done: "Claude finished", c_err: "Claude stopped", c_cost: (x) => `cost ≈ $${x.toFixed(2)}`,
    hl_h: "🎯 Hook Lab", hl_s: "Your strongest 2–7 s lines to open with. The line is copied to the top — the video still runs through it.",
    hl_find: "Finding your strongest lines…", hl_none: "No strong line found yet — the edit may be too short.", hl_use: "Use as cold open", hl_on: "Cold open is on:", hl_off: "Turn off",
    hl_top: "Top line", hl_box: "Boxed words", hl_bot: "Bottom line (*word* = colour)", hl_tag: "Tag", hl_set: "✓ Cold open set — press Play to watch it",
    h_h: "🩺 Edit Health", h_s: "Checks what makes viewers swipe or you re-edit: doubles, clipped words, dead air, colour, face covered, app buttons, hook, loudness.",
    h_run: "Run check", h_running: "Checking… (about 2 min)", h_stale: "The edit changed since this check — run it again.", h_clean: "✓ Nothing to fix",
    fx_tighten: "Tighten", fx_sdr: "Natural colour", fx_scene_off: "Turn off graphic", fx_ask: "Add as note", fx_hooklab: "Open Hook Lab",
    n_h: "💬 Talk to edit", n_s: "Pause where something's wrong and say it. Claude fixes every note.", n_ph: "e.g. tanggalin ang dead air dito · end here · mas malaki ang hook",
    n_add: (x) => `Add @ ${x}`, n_apply: "✨ Apply notes with Claude", n_copy: "Copy notes for Claude", n_copied: "Notes copied — paste them to Claude", n_done: "done",
    n_mic: "Speak your note", n_nomic: "Voice input isn't available in this browser — type the note.",
    pk_h: "📦 Post Kit", pk_s: "Everything to post: 9:16, 1:1 and 16:9 videos, captions, cover and the caption text.", pk_b: "Build Post Kit", pk_run: "Building…", pk_zip: "Download all (.zip)", pk_copy: "Copy caption", pk_copied: "Caption copied",
    k_h: "🎨 Brand Kit", k_s: "Save this look — colours, fonts, hook, captions, extras — and use it on every video.", k_ph: "My brand", k_save: "Save kit", k_def: "Use for every new upload",
    k_apply: "Apply", k_default: "Default", k_import: "⇪ Import kit", k_saved: "✓ Kit saved", k_applied: "✓ Kit applied", k_none: "No kits yet.",
  });
  Object.assign(I18N.tl, {
    hint: "Live preview · nagpe-play ang graphics gaya ng sa render", live_on: "Live graphics — nagpe-play ang scene pages sa phone", live_off: "Graphics mula sa huling render",
    live_t: "Live graphics (hindi na kailangang mag-render)", safe_t: "Ipakita ang buttons ng TikTok / Reels / Shorts", safe_names: ["", "TikTok", "Reels", "Shorts"],
    auto_h: "✨ Auto-edit gamit si Claude", auto_s: "Si Claude ang gagawa ng editorial pass: retakes, ulit, dead air, hook at motion graphics, tapos checks — at magre-render ng preview.",
    auto_b: "✨ I-auto-edit ang video na ito", auto_new: "I-auto-edit ang bawat bagong upload", need_claude: "Kailangan ng Claude Code sa computer na ito —", install: "paano i-install",
    c_run: "Nag-e-edit si Claude…", c_done: "Tapos na si Claude", c_err: "Huminto si Claude", c_cost: (x) => `gastos ≈ $${x.toFixed(2)}`,
    hl_h: "🎯 Hook Lab", hl_s: "Ang pinakamalalakas mong linya (2–7 s) na pang-simula. Kinokopya lang sa unahan — dadaanan pa rin ito sa video.",
    hl_find: "Hinahanap ang pinakamalalakas mong linya…", hl_none: "Wala pang malakas na linya — baka masyadong maikli ang edit.", hl_use: "Gawing cold open", hl_on: "Naka-on ang cold open:", hl_off: "I-off",
    hl_top: "Itaas na linya", hl_box: "Nakabox na salita", hl_bot: "Ibabang linya (*salita* = kulay)", hl_tag: "Tag", hl_set: "✓ Naka-set ang cold open — pindutin ang Play",
    h_h: "🩺 Edit Health", h_s: "Sinusuri ang nagpapa-swipe sa viewers o nagpapa-re-edit sa'yo: doble, putol na salita, dead air, kulay, natakpang mukha, app buttons, hook, lakas ng tunog.",
    h_run: "I-check", h_running: "Sinusuri… (mga 2 min)", h_stale: "Nagbago ang edit mula sa check na ito — i-check ulit.", h_clean: "✓ Walang kailangang ayusin",
    fx_tighten: "Higpitan", fx_sdr: "Natural na kulay", fx_scene_off: "Patayin ang graphic", fx_ask: "Gawing note", fx_hooklab: "Buksan ang Hook Lab",
    n_h: "💬 Talk to edit", n_s: "I-pause kung saan may mali at sabihin. Aayusin ni Claude ang bawat note.", n_ph: "hal. tanggalin ang dead air dito · i-end dito · mas malaki ang hook",
    n_add: (x) => `Idagdag @ ${x}`, n_apply: "✨ Ipaayos kay Claude ang notes", n_copy: "Kopyahin ang notes para kay Claude", n_copied: "Nakopya — i-paste kay Claude", n_done: "tapos",
    n_mic: "Sabihin ang note", n_nomic: "Walang voice input sa browser na ito — i-type na lang.",
    pk_h: "📦 Post Kit", pk_s: "Lahat ng kailangan sa pag-post: 9:16, 1:1 at 16:9 na video, captions, cover at caption text.", pk_b: "Gawin ang Post Kit", pk_run: "Ginagawa…", pk_zip: "I-download lahat (.zip)", pk_copy: "Kopyahin ang caption", pk_copied: "Nakopya ang caption",
    k_h: "🎨 Brand Kit", k_s: "I-save ang look na ito — kulay, fonts, hook, captions, extras — at gamitin sa bawat video.", k_ph: "Brand ko", k_save: "I-save", k_def: "Gamitin sa bawat bagong upload",
    k_apply: "Gamitin", k_default: "Default", k_import: "⇪ Mag-import ng kit", k_saved: "✓ Na-save ang kit", k_applied: "✓ Nagamit ang kit", k_none: "Wala pang kit.",
  });


  /* ---------------------------------------------------------------- Brief + Style references: labels */
  Object.assign(I18N.en, {
    br_h: "🗣 Tell Claude what you want", br_s: "Don't just click: say the look you're after. Tap what fits, then say it in your own words (Taglish is fine). The Studio builds your look from it, and Auto-edit and your notes follow it.",
    br_q_platform: "Where will you post it?", br_q_vibe: "The vibe", br_q_captions: "Captions", br_q_graphics: "Graphics", br_q_text: "In your own words",
    brv: { tiktok: "TikTok", reels: "Reels", shorts: "Shorts", youtube: "YouTube", facebook: "Facebook", clean: "Clean & minimal", bold: "Bold & energetic", premium: "Premium",
      fun: "Fun & playful", teach: "Teach / explain", big: "Big & bold", subtle: "Subtle", none: "None", few: "Few", some: "Some", lots: "Lots" },
    br_ph: "e.g. clean, yellow keywords, big captions at the bottom, fast cuts, a hook with a big number, arrows on the screen demo",
    br_go: "✨ Build my look", br_render: "Render a preview after", br_claude_t: "Let Claude fit the edit too", br_need: "Tell Claude what you want first: tap a few chips or write a line.",
    br_done: "✓ Your look is set", br_claude: "Claude is fitting the edit to your brief, then the preview renders…", br_changed: "What changed", br_none: "Nothing to change yet: add a chip or a few words.",
    br_rendering: "Rendering a preview with your look…",
    brp: { Colours: "Colours", Fonts: "Fonts", Captions: "Captions", Graphics: "Graphics", "Motion graphics": "Motion graphics", Hook: "Hook", Pace: "Pace",
      colours: "Colours", captions: "Captions", fonts: "Fonts", graphics: "Graphics", hook: "Hook", pace: "Pace" },
    auto_gate: "Tell Claude what you want first (the brief above), so Auto-edit edits it your way.",
    rf_h: "🎬 Learn a style from videos you like", rf_s: "Add up to 3 videos from creators you like. The Studio studies their captions, colours, pacing and graphics (not their footage), and you mix them into your own style.",
    rf_add: "＋ Add a video you like", rf_add_s: ".mov or .mp4 · drop it here", rf_busy: "Studying its style…", rf_err: "Couldn't read this one", rf_cut: (s) => `a cut every ${s} s`,
    rf_nocap: "no captions", rf_mix: "Mix & match: take each part from the video you like best", rf_go: "✨ Make it my style", rf_kit: "Also save as a Brand Kit", rf_kit_ph: "My style",
    rf_done: "✓ Your style is set", rf_note: "Only the style is kept: the video you add is deleted after it's studied, and nothing from it ends up in your edit.",
  });
  Object.assign(I18N.tl, {
    br_h: "🗣 Sabihin kay Claude ang gusto mo", br_s: "Huwag lang mag-click: sabihin ang look na gusto mo. I-tap ang bagay, tapos sabihin sa sarili mong salita (puwede ang Taglish). Dito bubuuin ang look mo, at ito rin ang susundin ng Auto-edit at ng notes mo.",
    br_q_platform: "Saan mo ipo-post?", br_q_vibe: "Ang vibe", br_q_captions: "Captions", br_q_graphics: "Graphics", br_q_text: "Sa sarili mong salita",
    brv: { tiktok: "TikTok", reels: "Reels", shorts: "Shorts", youtube: "YouTube", facebook: "Facebook", clean: "Malinis at simple", bold: "Bold at masigla", premium: "Premium",
      fun: "Masaya", teach: "Pagtuturo", big: "Malaki at bold", subtle: "Simple lang", none: "Wala", few: "Konti", some: "Katamtaman", lots: "Marami" },
    br_ph: "hal. malinis, dilaw ang keywords, malaking captions sa baba, mabilis ang cuts, hook na may malaking number, may arrows sa screen demo",
    br_go: "✨ Buuin ang look ko", br_render: "Mag-render ng preview pagkatapos", br_claude_t: "Si Claude na rin ang mag-ayos ng edit", br_need: "Sabihin muna kay Claude ang gusto mo: mag-tap ng chips o magsulat ng isang linya.",
    br_done: "✓ Nakaayos na ang look mo", br_claude: "Inaayos ni Claude ang edit ayon sa brief mo, tapos magre-render ang preview…", br_changed: "Ang nagbago", br_none: "Wala pang babaguhin: magdagdag ng chip o ilang salita.",
    br_rendering: "Nagre-render ng preview gamit ang look mo…",
    brp: { Colours: "Kulay", Fonts: "Fonts", Captions: "Captions", Graphics: "Graphics", "Motion graphics": "Motion graphics", Hook: "Hook", Pace: "Bilis",
      colours: "Kulay", captions: "Captions", fonts: "Fonts", graphics: "Graphics", hook: "Hook", pace: "Bilis" },
    auto_gate: "Sabihin muna kay Claude ang gusto mo (ang brief sa itaas), para ayon sa gusto mo ang Auto-edit.",
    rf_h: "🎬 Gayahin ang style ng videos na gusto mo", rf_s: "Magdagdag ng hanggang 3 video ng creators na gusto mo. Pag-aaralan ng Studio ang captions, kulay, bilis at graphics nila (hindi ang footage), at pagsasamahin mo ang mga ito sa sarili mong style.",
    rf_add: "＋ Magdagdag ng video na gusto mo", rf_add_s: ".mov o .mp4 · i-drop dito", rf_busy: "Pinag-aaralan ang style…", rf_err: "Hindi ito mabasa", rf_cut: (s) => `may cut kada ${s} s`,
    rf_nocap: "walang captions", rf_mix: "Mix & match: kunin ang bawat bahagi sa video na pinakagusto mo", rf_go: "✨ Gawin itong style ko", rf_kit: "I-save din bilang Brand Kit", rf_kit_ph: "Style ko",
    rf_done: "✓ Nakaayos na ang style mo", rf_note: "Style lang ang itinatabi: dine-delete ang video pagkatapos pag-aralan, at walang bahagi nito na mapupunta sa edit mo.",
  });

  const css = document.createElement("style");
  css.textContent = `
  .pro .lead{font-size:13px;margin:0 0 12px}
  .bigbtn.sm{padding:9px 14px;font-size:14px;border-radius:11px}
  .chk{display:flex;align-items:center;gap:8px;color:var(--mut);font-size:13px;margin-top:12px;cursor:pointer}
  .chk input{accent-color:var(--o)}
  .nrow{display:flex;gap:8px;align-items:center}
  .nrow input{flex:1;min-width:0;background:var(--panel2);border:1px solid var(--line2);border-radius:11px;padding:10px 12px;color:var(--text);font:600 14px var(--ui)}
  .nrow input:focus{outline:none;border-color:var(--o)}
  .nrow button.ic{border:1px solid var(--line2);background:var(--panel2);border-radius:11px;padding:9px 11px}
  .nrow button.ic.rec{border-color:var(--bad);color:var(--bad);animation:pulse 1s infinite}
  .nl{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);color:var(--mut)}
  .nl .tm{font:700 12px ui-monospace,Menlo,monospace;color:var(--o2);cursor:pointer;padding-top:1px}
  .nl b{color:var(--text);font-weight:600;flex:1}
  .nl.done b{text-decoration:line-through;color:var(--dim)}
  .nl button{border:0;background:none;color:var(--dim)}
  .hs{font:900 22px var(--disp);margin-left:auto}
  .hs.g{color:var(--ok)} .hs.m{color:var(--o2)} .hs.b{color:var(--bad)}
  .box h4.hd{display:flex;align-items:center;gap:8px}
  .hi{display:flex;align-items:flex-start;gap:10px;padding:9px 0;border-bottom:1px solid var(--line);cursor:pointer}
  .hi:hover .hx b{color:var(--o2)}
  .hi i{width:9px;height:9px;border-radius:50%;margin-top:5px;flex:none;background:var(--dim)}
  .hi.s3 i{background:var(--bad)} .hi.s2 i{background:var(--o)} .hi.s1 i{background:var(--dim)}
  .hi .tm{font:700 12px ui-monospace,Menlo,monospace;color:var(--mut);min-width:34px;padding-top:1px}
  .hx{flex:1;display:flex;flex-direction:column;gap:2px;min-width:0}
  .hx b{font-weight:700;color:var(--text)} .hx small{color:var(--mut);font-size:12px}
  .hi .fx{border:1px solid var(--line2);background:var(--panel2);border-radius:8px;padding:5px 9px;font:700 12px var(--ui);color:var(--text);white-space:nowrap}
  .hi .fx:hover{border-color:var(--o)}
  .cev{font:12px/1.5 ui-monospace,Menlo,monospace;color:var(--mut);max-height:170px;overflow:auto;margin-top:10px}
  .cev div:last-child{color:var(--text)}
  .csay{margin-top:10px;padding:10px 12px;border-radius:12px;background:var(--panel2);white-space:pre-wrap;font-size:13px}
  .hlc{border:1.5px solid var(--line);background:var(--panel);border-radius:var(--r);padding:14px 16px;margin:0 0 12px}
  .hlc.on{border-color:var(--o);box-shadow:0 0 0 3px var(--osoft)}
  .hlc q{display:block;font:700 15px/1.35 var(--disp);margin:6px 0 10px;quotes:"“" "”"}
  .hlc .meta{display:flex;align-items:center;gap:10px;color:var(--mut);font-size:12px}
  .hlc .bar{flex:0 0 80px;height:5px;border-radius:3px;background:var(--panel3);overflow:hidden}.hlc .bar i{display:block;height:100%;background:var(--o)}
  .hlf{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0 10px}
  .hlf label{display:flex;flex-direction:column;gap:4px;font:700 11px var(--ui);color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
  .hlf input{background:var(--panel2);border:1px solid var(--line2);border-radius:9px;padding:8px 10px;color:var(--text);font:800 13px var(--disp);text-transform:uppercase}
  .hlf .wide{grid-column:1/-1}
  .hlprev{display:inline-flex;flex-direction:column;align-items:center;gap:2px;padding:10px 14px;border-radius:12px;background:#0b0a09;margin-bottom:10px}
  .hlprev .t1{font:900 15px/.95 var(--disp);color:#fff;text-transform:uppercase;letter-spacing:-.03em}
  .hlprev .t2{font:900 19px/.95 var(--disp);color:var(--ink);background:var(--o);padding:2px 6px;border-radius:3px;transform:rotate(-2deg);text-transform:uppercase}
  .hlprev .t3{font:900 10px var(--disp);color:#fff;text-transform:uppercase}.hlprev .t3 em{font-style:normal;color:var(--o)}
  .pkf{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
  #pktext{width:100%;min-height:96px;background:var(--panel2);border:1px solid var(--line2);border-radius:11px;color:var(--text);padding:10px 12px;font:13px/1.45 var(--ui);resize:vertical}
  .kl{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--line)}
  .kl .sw{width:18px;height:18px;border-radius:5px;flex:none}
  .kl b{flex:1} .kl small{color:var(--mut)}
  .kl button{border:1px solid var(--line2);background:var(--panel2);border-radius:8px;padding:4px 9px;font:700 12px var(--ui)}
  .kl button.on{border-color:var(--o);color:var(--o2)}
  .brq{margin:12px 0 0}.brq>b{display:block;font:800 12px var(--ui);letter-spacing:.04em;color:var(--mut);margin-bottom:7px;text-transform:uppercase}
  .brc{display:flex;flex-wrap:wrap;gap:7px}.brc button{border:1px solid var(--line2);background:var(--panel2);border-radius:99px;padding:7px 13px;font:700 13px var(--ui);color:var(--text)}
  .brc button.on{border-color:var(--o);background:var(--osoft);color:var(--o2)}
  #brText{flex:1;min-width:0;background:var(--panel2);border:1px solid var(--line2);border-radius:11px;padding:10px 12px;color:var(--text);font:600 14px var(--ui);resize:vertical}
  #brText:focus{outline:none;border-color:var(--o)}
  .brres{margin-top:12px;padding:12px 14px;border-radius:12px;background:var(--panel2);border:1px solid var(--line2)}.brres h5{margin:0 0 6px;font:800 13px var(--ui)}
  .brres small{color:var(--mut)}
  #brBox.flash{animation:brflash 1.2s 2}@keyframes brflash{50%{box-shadow:0 0 0 3px var(--o)}}
  .rfg{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
  .rfc{position:relative;display:flex;gap:10px;padding:10px;border-radius:12px;background:var(--panel2);border:1px solid var(--line2);min-height:96px}
  .rfc img{width:54px;height:96px;object-fit:cover;border-radius:8px;flex:none}.rfc.busy{align-items:center}
  .rfb{display:flex;flex-direction:column;gap:4px;min-width:0}.rfb b{font:800 13px var(--ui);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:18px}
  .rfb small{font-size:12px;color:var(--mut);line-height:1.35}
  .rfch{display:flex;flex-wrap:wrap;gap:5px;margin-top:2px}.rfch span{display:inline-flex;align-items:center;gap:5px;font:700 11px var(--ui);padding:3px 7px;border-radius:99px;background:var(--panel);border:1px solid var(--line2)}
  .rfch i,.rfm i{display:inline-block;width:10px;height:10px;border-radius:3px}
  .rfx{position:absolute;right:6px;top:6px;border:0;background:none;color:var(--mut);font:700 13px var(--ui)}
  .rfadd{display:flex;flex-direction:column;justify-content:center;gap:4px;padding:10px 14px;border-radius:12px;border:2px dashed var(--line2);cursor:pointer;min-height:96px}
  .rfadd b{font:800 14px var(--ui)}.rfadd small{color:var(--mut);font-size:12px}#rfBox.over .rfadd{border-color:var(--o);background:var(--osoft)}
  .rfm{width:100%;border-collapse:separate;border-spacing:6px 6px;font:600 12px var(--ui)}.rfm th{text-align:left;color:var(--mut);font:800 11px var(--ui);letter-spacing:.04em;text-transform:uppercase}
  .rfm button{width:100%;text-align:left;display:flex;align-items:center;gap:6px;border:1px solid var(--line2);background:var(--panel2);border-radius:9px;padding:7px 9px;font:700 12px var(--ui);color:var(--text)}
  .rfm button.on{border-color:var(--o);background:var(--osoft);color:var(--o2)}.rfm button:disabled{opacity:.35}
  .rfkn{background:var(--panel2);border:1px solid var(--line2);border-radius:9px;padding:7px 10px;color:var(--text);font:600 13px var(--ui);width:150px}`;
  document.head.appendChild(css);

  let CL = { available: false }, HL = null, CJ = null, cpoll = null, hpoll = null, kpoll = null;
  api("/api/claude").then((r) => { CL = r; if (P) render(); }).catch(() => {});
  const pane = () => $("main");
  const cur = () => { const o = $("outv"); return o ? o.currentTime || 0 : lastE; };

  /* ---------------------------------------------------------------- player toggles */
  $("liveBtn").title = t("live_t"); $("safeBtn").title = t("safe_t");
  $("liveBtn").onclick = () => { liveOn = !liveOn; $("liveBtn").classList.toggle("on", liveOn); toast(t(liveOn ? "live_on" : "live_off")); };
  const SAFE = {  // % of the phone: [left, top, width, height] — where each app draws its buttons and text
    tiktok: [[86, 46, 12, 40, "♥ 💬 ↗"], [3, 82, 76, 15, "@name · caption · ♫ sound"], [24, 2.5, 52, 4.5, "Following | For You"]],
    reels: [[87, 55, 11, 33, "♥ 💬 ➤"], [3, 84, 78, 13, "@name · caption · audio"], [3, 2.5, 34, 4.5, "Reels"]],
    shorts: [[86, 50, 12, 36, "👍 👎 💬 ↗"], [3, 80, 76, 16, "@channel · Subscribe · title"], [3, 2.5, 22, 4.5, "Shorts"]],
  };
  let safeI = 0;
  $("safeBtn").onclick = () => {
    safeI = (safeI + 1) % 4; const k = ["", "tiktok", "reels", "shorts"][safeI], el = $("safe");
    el.classList.toggle("on", !!k); $("safeBtn").classList.toggle("on", !!k);
    el.innerHTML = k ? SAFE[k].map(([l, tp, w, h, lab]) => `<i style="left:${l}%;top:${tp}%;width:${w}%;height:${h}%"><b>${esc(lab)}</b></i>`).join("") : "";
    if (k) toast(t("safe_names")[safeI]);
  };

  /* ---------------------------------------------------------------- Claude job view (Auto-edit + notes) */
  function claudeView() {
    if (!CJ || CJ.state === "idle") return "";
    const st = CJ.state === "running" ? `<span class="warn">● ${esc(t("c_run"))}</span>` : CJ.state === "done" ? `<span class="ok">✓ ${esc(t("c_done"))}</span>` : `<span style="color:var(--bad)">✕ ${esc(t("c_err"))}</span>`;
    const ev = (CJ.events || []).slice(-8).map((e) => `<div>› ${esc(e.tool)} · ${esc(e.what)}</div>`).join("");
    const say = CJ.result || CJ.say || (CJ.state === "error" ? CJ.log : "");
    return `<div style="margin-top:12px">${st}${CJ.cost ? ` <small class="warn">${esc(t("c_cost", CJ.cost))}</small>` : ""}</div>${ev ? `<div class="cev">${ev}</div>` : ""}${say ? `<div class="csay">${esc(say)}</div>` : ""}`;
  }
  async function pollClaude() {
    clearInterval(cpoll);
    const tick = async () => {
      CJ = await api(`/api/project/${P.name}/claude`);
      document.querySelectorAll(".cview").forEach((el) => (el.innerHTML = claudeView()));
      if (CJ.state !== "running") { clearInterval(cpoll); const q = await api(`/api/project/${P.name}`); P = q; L = await api(`/api/project/${P.name}/look`); setupPlayer(); if (P.job && P.job.state === "running") watch(); }
    };
    await tick(); cpoll = setInterval(tick, 2500);
  }

  /* ---------------------------------------------------------------- Start: Auto-edit */
  const installLink = `<a href="https://docs.claude.com/en/docs/claude-code/overview" target="_blank" rel="noopener">${esc(t("install"))}</a>`;
  function autoBox() {
    const running = CJ && CJ.state === "running";
    return `<div class="box pro" id="autoBox"><h4>${esc(t("auto_h"))}</h4><p class="lead">${esc(t("auto_s"))}</p>
      ${CL.available ? `<button class="bigbtn" data-pro="auto" ${running ? "disabled" : ""}>${esc(t("auto_b"))}</button>` : `<div class="li warn">${esc(t("need_claude"))} ${installLink}</div>`}
      <label class="chk"><input type="checkbox" data-pro="autoset" ${SET.auto_edit ? "checked" : ""} ${CL.available ? "" : "disabled"}> ${esc(t("auto_new"))}</label>
      <div class="cview">${claudeView()}</div></div>`;
  }


  /* ---------------------------------------------------------------- Brief: tell Claude what you want */
  const BRQ = [["platform", ["tiktok", "reels", "shorts", "youtube", "facebook"]], ["vibe", ["clean", "bold", "premium", "fun", "teach"]],
    ["captions", ["big", "subtle", "none"]], ["graphics", ["few", "some", "lots"]]];
  let BR = null, BRout = null;
  const hasBrief = () => !!BR && (BR.styled || !!(BR.text || "").trim() || Object.values(BR.answers || {}).some(Boolean));
  function briefBox() {
    const a = (BR && BR.answers) || {};
    const qs = BRQ.map(([q, opts]) => `<div class="brq"><b>${esc(t("br_q_" + q))}</b><div class="brc">${opts.map((o) =>
      `<button class="${a[q] === o ? "on" : ""}" data-pro="brchip" data-q="${q}" data-v="${o}">${esc(t("brv")[o])}</button>`).join("")}</div></div>`).join("");
    return `<div class="box pro" id="brBox"><h4>${esc(t("br_h"))}</h4><p class="lead">${esc(t("br_s"))}</p>${qs}
      <div class="brq"><b>${esc(t("br_q_text"))}</b><div class="nrow"><textarea id="brText" rows="2" placeholder="${esc(t("br_ph"))}">${esc((BR && BR.text) || "")}</textarea>
        <button class="ic" data-pro="brmic" title="${esc(t("n_mic"))}">🎤</button></div></div>
      <div class="row" style="margin:12px 0 0;align-items:center;gap:14px;flex-wrap:wrap"><button class="bigbtn" data-pro="brgo">${esc(t("br_go"))}</button>
        <label class="chk" style="margin:0"><input type="checkbox" id="brRender" checked> ${esc(t("br_render"))}</label>
        ${CL.available ? `<label class="chk" style="margin:0"><input type="checkbox" id="brClaude" checked> ${esc(t("br_claude_t"))}</label>` : ""}</div>
      <div id="brOut">${briefOut()}</div><div class="cview">${claudeView()}</div></div>`;
  }
  function briefOut() {
    if (!BRout) return "";
    const ch = (BRout.changes || []).map((c) => `<div class="li"><span class="ok">✓</span><span><b>${esc(t("brp")[c.part] || c.part)}</b> → ${esc(c.value)}${c.why ? ` <small>· ${esc(c.why)}</small>` : ""}</span></div>`).join("");
    return `<div class="brres"><h5>${esc(ch ? t("br_changed") : t("br_none"))}</h5>${ch}${BRout.claude && BRout.claude.state !== "error" ? `<div class="warn" style="margin-top:8px">● ${esc(t("br_claude"))}</div>` : ""}${BRout.render ? `<div class="warn" style="margin-top:8px">● ${esc(t("br_rendering"))}</div>` : ""}</div>`;
  }
  async function loadBrief() {
    if (BR && BR._for === P.name) return;
    BR = await api(`/api/project/${P.name}/brief`); BR.answers = BR.answers || {}; BR._for = P.name; BRout = null; RFout = null;
    const b = $("brBox"); if (b) b.outerHTML = briefBox();
  }

  /* ---------------------------------------------------------------- Style references: learn a style from videos you like */
  let RF = [], MIX = {}, RFout = null, rfpoll = null;
  const PARTS = ["colours", "captions", "fonts", "graphics", "hook", "pace"];
  const cname = (arr, id) => ((arr || []).find((x) => x.id === id) || {}).name || id;
  function partVal(r, p) {
    const lk = r.look || {};
    if (p === "colours") return lk.palette ? cname(CAT.palettes, lk.palette) : lk.accent || "—";
    if (p === "captions") return !lk.caption ? "—" : lk.caption.style === "none" ? cname(CAT.captions, "none") : `${cname(CAT.captions, lk.caption.style)} · ${cname(CAT.positions, lk.caption.pos)}`;
    if (p === "fonts") return lk.fonts ? cname(CAT.fonts, lk.fonts) : "—";
    if (p === "graphics") return lk.visuals ? cname(CAT.density, lk.visuals.density) : "—";
    if (p === "hook") return lk.hook ? cname(CAT.hooks, lk.hook) : "—";
    return lk.pace || "—";
  }
  const swatch = (r) => { const lk = r.look || {}; const c = lk.palette ? (CAT.palettes.find((x) => x.id === lk.palette) || {}).accent : lk.accent || r.accent; return c ? `<i style="background:${esc(c)}"></i>` : ""; };
  function refCards() {
    const cards = RF.map((r) => r.state === "ready"
      ? `<div class="rfc"><img src="${r.thumb}" alt=""><div class="rfb"><b>${esc(r.name)}</b><small>${esc(r.summary || "")}</small>
          <div class="rfch">${r.accent ? `<span>${swatch(r)}${esc(r.accent)}</span>` : ""}<span>${esc(t("rf_cut", (r.pace || {}).avg_shot))}</span><span>${esc(partVal(r, "captions"))}</span></div></div>
          <button class="rfx" data-pro="rfdel" data-id="${esc(r.id)}">✕</button></div>`
      : `<div class="rfc busy"><div class="rfb"><b>${esc(r.name)}</b><small class="${r.state === "error" ? "bad" : "warn"}">${esc(r.state === "error" ? `${t("rf_err")} · ${r.log || ""}` : t("rf_busy"))}</small></div>
          ${r.state === "error" ? `<button class="rfx" data-pro="rfdel" data-id="${esc(r.id)}">✕</button>` : ""}</div>`).join("");
    return cards + (RF.length < 3 ? `<label class="rfadd"><b>${esc(t("rf_add"))}</b><small>${esc(t("rf_add_s"))}</small><input type="file" id="rfFile" accept="video/*" hidden></label>` : "");
  }
  function mixTable() {
    const ready = RF.filter((r) => r.state === "ready"); if (!ready.length) return "";
    PARTS.forEach((p) => { if (!ready.some((r) => r.id === MIX[p] && partVal(r, p) !== "—")) MIX[p] = (ready.find((r) => partVal(r, p) !== "—") || ready[0]).id; });
    const rows = PARTS.map((p) => `<tr><th>${esc(t("brp")[p])}</th>${ready.map((r) => { const v = partVal(r, p);
      return `<td><button class="${MIX[p] === r.id ? "on" : ""}" ${v === "—" ? "disabled" : ""} data-pro="rfpick" data-p="${p}" data-id="${esc(r.id)}">${p === "colours" ? swatch(r) : ""}${esc(v)}</button></td>`; }).join("")}</tr>`).join("");
    return `<h5 style="margin:16px 0 4px">${esc(t("rf_mix"))}</h5><table class="rfm"><tr><th></th>${ready.map((r) => `<th>${esc(r.name)}</th>`).join("")}</tr>${rows}</table>
      <div class="row" style="margin:10px 0 0;align-items:center;gap:12px;flex-wrap:wrap"><button class="bigbtn" data-pro="rfgo">${esc(t("rf_go"))}</button>
        <label class="chk" style="margin:0"><input type="checkbox" id="rfKit"> ${esc(t("rf_kit"))}</label><input id="rfKitName" class="rfkn" placeholder="${esc(t("rf_kit_ph"))}"></div>
      <div id="rfOut">${RFout ? `<div class="brres"><h5>${esc(t("br_changed"))}</h5>${RFout.map((n) => `<div class="li"><span class="ok">✓</span><span><b>${esc(t("brp")[n.part] || n.part)}</b> ← ${esc(n.ref)} <small>· ${esc(n.why)}</small></span></div>`).join("")}</div>` : ""}</div>`;
  }
  function refsBox() {
    return `<div class="box pro" id="rfBox"><h4>${esc(t("rf_h"))}</h4><p class="lead">${esc(t("rf_s"))}</p>
      <div class="rfg" id="rfList">${refCards()}</div><div id="rfMix">${mixTable()}</div>
      <p class="lead" style="margin:12px 0 0;font-size:12px">${esc(t("rf_note"))}</p></div>`;
  }
  async function loadRefs() {
    const r = await api("/api/refs"); RF = r.refs || [];
    const l = $("rfList"); if (l) l.innerHTML = refCards();
    const m = $("rfMix"); if (m) m.innerHTML = mixTable();
    clearTimeout(rfpoll); if (RF.some((x) => x.state === "running")) rfpoll = setTimeout(loadRefs, 1500);
  }
  function upRef(file) {
    RF.push({ id: "", name: file.name, state: "running" }); const l = $("rfList"); if (l) l.innerHTML = refCards();
    const xhr = new XMLHttpRequest(); xhr.open("POST", `/api/refs/upload?name=${encodeURIComponent(file.name)}`);
    xhr.onload = () => loadRefs(); xhr.onerror = () => { toast(t("rf_err")); loadRefs(); }; xhr.send(file);
  }
  document.addEventListener("change", (e) => { if (e.target && e.target.id === "rfFile" && e.target.files[0]) upRef(e.target.files[0]); });
  document.addEventListener("dragover", (e) => { const z = e.target.closest && e.target.closest("#rfBox"); if (z) { e.preventDefault(); z.classList.add("over"); } });
  document.addEventListener("dragleave", (e) => { const z = e.target.closest && e.target.closest("#rfBox"); if (z && !z.contains(e.relatedTarget)) z.classList.remove("over"); });
  document.addEventListener("drop", (e) => {  // a video you like → a style reference (never the video you're editing)
    const z = e.target.closest && e.target.closest("#rfBox"); if (!z) return;
    e.preventDefault(); e.stopImmediatePropagation(); z.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f && RF.length < 3) upRef(f);
  }, true);

  /* ---------------------------------------------------------------- Hook Lab */
  const splitRows = (rows) => {
    const r = { top: "", box: "", bot: "" }; let seenBox = false;
    (rows || []).forEach((x) => { x = x.replace(/@.*$/, ""); if (x.startsWith("H:")) { r.box = x.slice(2).replace(/_/g, " "); seenBox = true; } else if (!seenBox) r.top = x; else r.bot = x.replace(/O:(\S+)/g, "*$1*").replace(/_/g, " "); });
    return r;
  };
  const joinRows = (r) => [r.top.trim().toUpperCase(), r.box.trim() ? "H:" + r.box.trim().toUpperCase().replace(/\s+/g, "_") : "", r.bot.trim().toUpperCase().replace(/\*([^*]+)\*/g, (m, w) => w.split(/\s+/).map((x) => "O:" + x).join(" "))].filter(Boolean);
  function hlPrev(r) {
    return `<div class="hlprev">${r.top ? `<div class="t1">${esc(r.top)}</div>` : ""}${r.box ? `<div class="t2">${esc(r.box)}</div>` : ""}${r.bot ? `<div class="t3">${esc(r.bot).replace(/\*([^*]+)\*/g, "<em>$1</em>")}</div>` : ""}</div>`;
  }
  function hookLab() {
    if (!HL) return `<div class="box pro" id="hlBox"><h4>${esc(t("hl_h"))}</h4><p class="lead">${esc(t("hl_find"))}</p></div>`;
    const curH = HL.current;
    const on = curH ? `<div class="li" style="margin-bottom:12px"><span class="ok">●</span><span>${esc(t("hl_on"))} “${esc((P.words || []).slice(curH.from, curH.to + 1).map((w) => (P.fixes[w.i] !== undefined ? P.fixes[w.i] : w.w)).join(" "))}”</span>
        <button class="fx tlink" data-pro="hloff" style="margin-left:auto">${esc(t("hl_off"))}</button></div>` : "";
    const cards = (HL.candidates || []).map((c, i) => {
      const r = splitRows(c.rows), isOn = curH && curH.from === c.from && curH.to === c.to, mx = Math.max(...HL.candidates.map((x) => x.score), 1);
      return `<div class="hlc ${isOn ? "on" : ""}" data-i="${i}"><div class="meta"><b style="color:var(--text)">#${i + 1}</b><span class="bar"><i style="width:${Math.max(8, c.score / mx * 100)}%"></i></span>
          <span>${tc(c.start)}–${tc(c.end)} · ${(c.end - c.start).toFixed(1)} s</span><button class="pbtn" style="position:static;margin-left:auto" data-pro="hlplay" data-i="${i}">${esc(t("playcard"))}</button></div>
        <q>${esc(c.text)}</q>${hlPrev(r)}
        <div class="hlf"><label>${esc(t("hl_top"))}<input data-hl="top" value="${esc(r.top)}"></label><label>${esc(t("hl_box"))}<input data-hl="box" value="${esc(r.box)}"></label>
          <label class="wide">${esc(t("hl_bot"))}<input data-hl="bot" value="${esc(r.bot)}"></label><label class="wide">${esc(t("hl_tag"))}<input data-hl="tag" value="${esc(c.tag || (L.hook.kicker || "Panoorin mo 'to"))}"></label></div>
        <button class="bigbtn sm" data-pro="hluse" data-i="${i}">${esc(t("hl_use"))}</button></div>`;
    }).join("") || `<p class="lead">${esc(t("hl_none"))}</p>`;
    return `<div class="box pro" id="hlBox"><h4>${esc(t("hl_h"))}</h4><p class="lead">${esc(t("hl_s"))}</p>${on}${cards}</div>`;
  }
  async function loadHookLab() { HL = await api(`/api/project/${P.name}/hooklab`); const b = $("hlBox"); if (b) b.outerHTML = hookLab(); }

  /* ---------------------------------------------------------------- Edit Health */
  function healthBox() { return `<div class="box pro" id="hBox"><h4 class="hd">${esc(t("h_h"))}<span class="hs" id="hScore"></span></h4><p class="lead">${esc(t("h_s"))}</p>
      <button class="bigbtn sec sm" data-pro="hrun">${esc(t("h_run"))}</button> <span id="hState" class="warn" style="font-size:13px"></span><div id="hList"></div></div>`; }
  function paintHealth(h) {
    const rep = h.report, running = h.job && h.job.state === "running";
    $("hState").textContent = running ? `${t("h_running")} ${h.job.step ? "· " + h.job.step : ""}` : h.stale ? t("h_stale") : "";
    if (!rep) { $("hScore").textContent = ""; $("hList").innerHTML = ""; return; }
    const sc = $("hScore"); sc.textContent = rep.score; sc.className = "hs " + (rep.score >= 90 ? "g" : rep.score >= 70 ? "m" : "b");
    const tx = (i, k) => i[(LANG === "tl" ? k.replace("en", "tl") : k)] || i[k];
    $("hList").innerHTML = rep.items.length ? rep.items.map((i, n) => `<div class="hi s${i.sev}" data-pro="hseek" data-at="${i.at ?? ""}"><i></i><span class="tm">${i.at !== null && i.at !== undefined ? tc(i.at) : "—"}</span>
        <span class="hx"><b>${esc(tx(i, "en"))}</b>${tx(i, "detail_en") ? `<small>${esc(tx(i, "detail_en"))}</small>` : ""}</span>
        ${i.fix ? `<button class="fx" data-pro="hfix" data-n="${n}">${esc(t("fx_" + i.fix.action))}</button>` : ""}</div>`).join("") : `<div class="li ok" style="margin-top:10px">${esc(t("h_clean"))}</div>`;
    $("hList")._items = rep.items;
  }
  async function loadHealth(poll) {
    const h = await api(`/api/project/${P.name}/health`); if (!$("hBox")) return; paintHealth(h);
    clearTimeout(hpoll); if (h.job && h.job.state === "running") hpoll = setTimeout(() => loadHealth(true), 3000); else if (poll) toast(`🩺 ${h.report ? h.report.score + "/100" : ""}`);
  }

  /* ---------------------------------------------------------------- Talk to edit */
  function notesBox() {
    return `<div class="box pro" id="nBox" style="margin-top:16px"><h4>${esc(t("n_h"))}</h4><p class="lead">${esc(t("n_s"))}</p>
      <div class="nrow"><input id="nText" placeholder="${esc(t("n_ph"))}"><button class="ic" data-pro="nmic" title="${esc(t("n_mic"))}">🎤</button><button class="bigbtn sm" data-pro="nadd" id="nAdd">${esc(t("n_add", tc(cur())))}</button></div>
      <div id="nList"></div><div class="row" style="margin:12px 0 0">${CL.available ? `<button class="bigbtn" data-pro="napply">${esc(t("n_apply"))}</button>` : `<button class="bigbtn sec sm" data-pro="ncopy">${esc(t("n_copy"))}</button> <small class="warn">${esc(t("need_claude"))} ${installLink}</small>`}</div>
      <div class="cview">${claudeView()}</div></div>`;
  }
  function paintNotes() {
    const el = $("nList"); if (!el) return;
    el.innerHTML = (P.comments || []).map((c) => `<div class="nl ${c.done ? "done" : ""}"><span class="tm" data-pro="nseek" data-at="${c.at}">${tc(c.at)}</span><b>${esc(c.text)}</b>${c.done ? `<small>${esc(t("n_done"))}</small>` : ""}<button data-pro="ndel" data-id="${c.id}">✕</button></div>`).join("");
  }
  let rec = null;
  function mic(btn, target = "nText") {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return toast(t("n_nomic"));
    if (rec) { rec.stop(); return; }
    rec = new SR(); rec.lang = LANG === "tl" ? "fil-PH" : "en-US"; rec.interimResults = true;
    rec.onresult = (e) => { $(target).value = [...e.results].map((r) => r[0].transcript).join(" "); };
    rec.onend = () => { rec = null; btn.classList.remove("rec"); };
    btn.classList.add("rec"); rec.start();
  }

  /* ---------------------------------------------------------------- Post Kit */
  function postKitBox() { return `<div class="box pro" id="pkBox"><h4>${esc(t("pk_h"))}</h4><p class="lead">${esc(t("pk_s"))}</p>
      <button class="bigbtn sec sm" data-pro="pkb">${esc(t("pk_b"))}</button> <span id="pkState" class="warn" style="font-size:13px"></span><div class="pkf" id="pkFiles"></div>
      <textarea id="pktext"></textarea><div class="row" style="margin:8px 0 0"><button class="tlink" data-pro="pkcopy">${esc(t("pk_copy"))}</button></div></div>`; }
  async function loadPostKit(poll) {
    const k = await api(`/api/project/${P.name}/postkit`); if (!$("pkBox")) return;
    const running = k.job && k.job.state === "running";
    $("pkState").textContent = running ? `${t("pk_run")} ${k.job.step || ""}` : k.job && k.job.state === "error" ? k.job.log : "";
    const kit = `${P.name}_postkit`;
    $("pkFiles").innerHTML = (k.zip ? `<a class="tlink" href="/out/${esc(k.zip)}" download>⇩ ${esc(t("pk_zip"))}</a>` : "") +
      k.files.filter((f) => f !== "post.txt").map((f) => `<a class="tlink" href="/out/${esc(kit)}/${esc(f)}" download>${esc(f)}</a>`).join("");
    if (!$("pktext").value || poll) $("pktext").value = k.text || "";
    clearTimeout(kpoll); if (running) kpoll = setTimeout(() => loadPostKit(true), 2500);
  }

  /* ---------------------------------------------------------------- Brand Kits */
  function kitsBox() { return `<div class="box pro" id="kBox"><h4>${esc(t("k_h"))}</h4><p class="lead">${esc(t("k_s"))}</p>
      <div class="nrow"><input id="kName" placeholder="${esc(t("k_ph"))}"><button class="bigbtn sm" data-pro="ksave">${esc(t("k_save"))}</button></div>
      <label class="chk"><input type="checkbox" id="kDef"> ${esc(t("k_def"))}</label><div id="kList" style="margin-top:10px"></div>
      <label class="tlink" style="display:inline-block;margin-top:12px;cursor:pointer">${esc(t("k_import"))}<input type="file" accept=".json,application/json" id="kImp" hidden></label></div>`; }
  async function loadKits() {
    const k = await api("/api/kits"); const el = $("kList"); if (!el) return;
    el.innerHTML = k.kits.length ? k.kits.map((x) => `<div class="kl"><span class="sw" style="background:${esc(x.accent || "#FF6A00")}"></span><b>${esc(x.name)}</b><small>${esc([x.fonts, x.hook, x.caption].filter(Boolean).join(" · "))}</small>
        <button data-pro="kapply" data-id="${esc(x.id)}">${esc(t("k_apply"))}</button><a class="tlink" style="padding:4px 9px" href="/api/kits/${esc(x.id)}.json" download>⇩</a>
        <button class="${k.default === x.id ? "on" : ""}" data-pro="kdef" data-id="${esc(x.id)}">★</button></div>`).join("") : `<div class="li">${esc(t("k_none"))}</div>`;
  }

  /* ---------------------------------------------------------------- 2026 motion library (live sample pages) */
  Object.assign(I18N.en, { trend: "✨ 2026 trends", trend_l: (n) => `${n} new motion graphics from what's trending on Reels, TikTok, Shorts and X. Hover to watch · click to pick it and play it on your video — Claude uses the ones you tick.` });
  Object.assign(I18N.tl, { trend: "✨ 2026 trends", trend_l: (n) => `${n} bagong motion graphics mula sa trending sa Reels, TikTok, Shorts at X. I-hover para makita · i-click para piliin at i-play sa video mo — gagamitin ni Claude ang mga naka-tick.` });
  const gdemo = document.createElement("iframe");
  gdemo.className = "gframe"; gdemo.id = "gdemo"; gdemo.setAttribute("scrolling", "no"); gdemo.style.zIndex = 7; $("phone").appendChild(gdemo);
  const galTL = (f) => { try { return (f.contentWindow.__timelines || {})[f.dataset.gal]; } catch (e) { return null; } };
  const galQ = []; let galBusy = false;
  function galNext() {  // load the card previews one after another (31 pages at once would stall the Studio)
    if (galBusy || !galQ.length) return; const f = galQ.shift(); if (!f.isConnected) return galNext();
    galBusy = true; f.onload = () => { galBusy = false; const go = (n) => { const tl = galTL(f); if (tl) tl.seek(+f.dataset.still); else if (n < 20) setTimeout(() => go(n + 1), 80); }; go(0); galNext(); };
    f.src = f.dataset.src;
  }
  function trendView() {
    const types = new Set(L.visuals.types || []), M = CAT.motion || [], img = frameUrl(midT());
    const v = Date.now() / 1e4 | 0;
    return (CAT.motion_groups || []).map((g) => {
      const its = M.filter((m) => m.group === g.id); if (!its.length) return "";
      return `<h2>${esc(g.name)} <small>${its.length}</small></h2><div class="grid">${its.map((m) => `<div class="card ${types.has(m.id) ? "picked" : ""}" role="button" tabindex="0" data-mv="${m.id}">
        <span class="no">${M.indexOf(m) + 1}</span><span class="pk">${esc(t("picked"))}</span>
        <div class="thumb"><img src="${img}" loading="lazy" alt=""><div class="ov"><iframe class="gframe gcard" scrolling="no" tabindex="-1" data-gal="gal_${m.id}" data-src="/motion/scenes/gal_${m.id}.html?v=${v}" data-still="${(m.dur * .62).toFixed(2)}"></iframe></div>
          <button class="pbtn" data-pro="mvplay" data-id="${m.id}">${esc(t("playcard"))}</button></div>
        <h3>${esc(m.name)}</h3><p>${esc(m.note)}</p></div>`).join("")}</div>`;
    }).join("");
  }
  function fitGal(root) { root.querySelectorAll(".gcard").forEach((f) => { const w = f.parentElement.clientWidth; if (w) { f.style.transform = `scale(${w / 1080})`; f.style.display = "block"; } }); }
  const SFX7 = { tier: [[1.0, "pop"], [1.7, "pop"], [2.3, "pop"], [2.9, "ding"]], score: [[2.2, "ding"]], price: [[0.8, "hit"]], island: [[0.2, "sw_air"]], search: [[0.65, "typing"]],
    post: [[1.6, "pop"]], call: [[0.3, "sw_air"]], keys: [[0.75, "tick"], [0.9, "tick"], [1.05, "tick"]], flap: [[0.2, "typing"]], glitch: [[0.2, "sw_whip"]], redact: [[1.6, "swish"]],
    flip: [[1.8, "sw_whip"]], polaroid: [[0.2, "shutter"], [0.55, "shutter"], [0.9, "shutter"]], achieve: [[0.3, "ding"]], sticker: [[0.3, "pop"]], burst: [[0.3, "pop"], [0.35, "sw_shimmer"]],
    rank: [[0.3, "pop"], [1.6, "sw_whip"], [2.9, "sw_whip"]], streak: [[0.4, "tick"], [0.9, "ding"]], chart: [[0.2, "riser"], [1.2, "ding"]], ring: [[1.0, "ding"]], timer: [[0.2, "tick"]] };
  function demoGal(id) {
    const m = (CAT.motion || []).find((x) => x.id === id); if (!m || !P) return;
    startDemo({ label: `${t("trend")} · ${m.name}`, main: true, from: talkTime(), dur: m.dur + .3, hideCaps: m.group !== "attention" && m.group !== "demo",
      sounds: SFX7[id] || [[0.15, "sw_air"]],
      fx: () => { gdemo.dataset.gal = `gal_${id}`; gdemo.style.display = "block"; gdemo.style.transform = `scale(${$("phone").clientHeight / 1920})`;
        gdemo.onload = () => { const go = (n) => { const tl = galTL(gdemo); if (tl) tl.restart(); else if (n < 20) setTimeout(() => go(n + 1), 60); }; go(0); };
        gdemo.src = `/motion/scenes/gal_${id}.html?v=${Date.now()}`;
        return () => { gdemo.style.display = "none"; gdemo.removeAttribute("src"); }; } });
  }
  const _vVisuals = vVisuals;
  vVisuals = function () {  // eslint-disable-line no-func-assign
    const isT = sub.visuals === "trend"; if (isT) sub.visuals = "library";
    let html = _vVisuals(); if (isT) sub.visuals = "trend";
    const btn = `<button data-sub="trend" class="${isT ? "on" : ""}">${esc(t("trend"))} · ${(CAT.motion || []).length}</button>`;
    html = html.replace(/(<div class="seg">[\s\S]*?)(<\/div>)/, (m0, a, b) => a + btn + b);
    if (isT) { html = html.replace('data-sub="library" class="on"', 'data-sub="library" class=""'); const k = html.lastIndexOf('<div class="grid">'); html = html.slice(0, k) + `<p class="lead">${esc(t("trend_l", (CAT.motion || []).length))}</p>` + trendView(); }
    return html;
  };
  pane().addEventListener("mouseover", (e) => {  // hover: the sample plays from the top; leave: back to its still
    const c = e.target.closest && e.target.closest("[data-mv]"); const f = c && c.querySelector(".gcard");
    if (f && f !== pane()._hov) { if (pane()._hov) { const tl0 = galTL(pane()._hov); if (tl0) tl0.pause().seek(+pane()._hov.dataset.still); } pane()._hov = f; const tl = galTL(f); if (tl) tl.restart(); }
  });
  pane().addEventListener("mouseleave", () => { const f = pane()._hov; if (f) { const tl = galTL(f); if (tl) tl.pause().seek(+f.dataset.still); pane()._hov = null; } });

  /* ---------------------------------------------------------------- 2026 trend hooks: previews are the real template pages */
  const V7H = new Set(["pov", "redact", "island", "search", "glitch", "flap", "price", "flip"]);
  const HKP = {};  // variant → {url, dur, sfx} for the current text
  let hkT = null;
  function loadHookFrames() {
    clearTimeout(hkT);
    hkT = setTimeout(async () => {
      if (!P) return;
      const want = new Set([...document.querySelectorAll("iframe.hkcard")].map((f) => f.dataset.hk));
      for (const v of want) {
        const key = [v, L.hook.text, L.hook.kicker, accent(), L.fonts].join("|");
        if (!HKP[v] || HKP[v].key !== key) { const r = await api(`/api/project/${P.name}/hookpage?v=${v}&text=${encodeURIComponent(L.hook.text || "")}&kicker=${encodeURIComponent(L.hook.kicker || "")}`); HKP[v] = { ...r, key }; }
        document.querySelectorAll(`iframe.hkcard[data-hk="${v}"]`).forEach((f) => {
          const w = f.parentElement.clientWidth || f.parentElement.parentElement.clientWidth; if (w) f.style.transform = `scale(${w / 1080})`; f.style.display = "block";
          if (f.dataset.u === HKP[v].url) return; f.dataset.u = HKP[v].url; f.dataset.gal = HKP[v].id;
          f.onload = () => { const go = (n) => { const tl = galTL(f); if (tl) tl.seek(Math.min(2.2, HKP[v].dur * .5)); else if (n < 20) setTimeout(() => go(n + 1), 80); }; go(0); };
          f.src = HKP[v].url;
        });
      }
    }, 250);
  }
  const _hookStill = hookStill;
  hookStill = function (v, text, kick) {  // eslint-disable-line no-func-assign
    if (!V7H.has(v)) return _hookStill(v, text, kick);
    loadHookFrames();
    return `<iframe class="gframe hkcard" scrolling="no" tabindex="-1" data-hk="${v}"></iframe>`;
  };
  const _demoHook = demoHook;
  demoHook = async function (v) {  // eslint-disable-line no-func-assign
    v = v || L.hook.type;
    if (!V7H.has(v)) return _demoHook(v);
    const r = await api(`/api/project/${P.name}/hookpage?v=${v}&text=${encodeURIComponent(L.hook.text || "")}&kicker=${encodeURIComponent(L.hook.kicker || "")}`);
    const ho = (P.overlays || []).find((o) => o.id === L.hook.id);  // the hook plays where it sits (after a cold open, if any)
    startDemo({ label: t("d_hook"), main: true, from: ho ? Math.max(0, ho.at - .05) : 0, dur: r.dur + .2, hideCaps: true, sounds: (r.sfx || []).map(([a, b]) => [a, b === "type" ? "typing" : b]),
      fx: () => { gdemo.dataset.gal = r.id; gdemo.style.display = "block"; gdemo.style.transform = `scale(${$("phone").clientHeight / 1920})`;
        gdemo.onload = () => { const go = (n) => { const tl = galTL(gdemo); if (tl) tl.restart(); else if (n < 20) setTimeout(() => go(n + 1), 60); }; go(0); };
        gdemo.src = r.url; return () => { gdemo.style.display = "none"; gdemo.removeAttribute("src"); }; } });
  };
  window.addEventListener("resize", () => { document.querySelectorAll("iframe.hkcard").forEach((f) => { const w = f.parentElement.clientWidth; if (w) f.style.transform = `scale(${w / 1080})`; }); fitGal(pane()); });

  /* ---------------------------------------------------------------- decorate the steps */
  // docs / screenshots: ?scroll=<px> scrolls the step, ?shot=1 shows a still frame where the video can't decode (headless Chrome)
  const QS = new URLSearchParams(location.search), SHOT = QS.get("shot") === "1", SCROLL = +(QS.get("scroll") || 0);
  const _render = render;
  render = function () {  // eslint-disable-line no-func-assign
    _render();
    if (!P) return;
    const s = STEPS[step], M = pane();
    if (SHOT) { const fr = `/media/${P.name}/frame.jpg?t=${((P.segments || [[0]])[0][0] + 2.2).toFixed(1)}&w=540`; $("vid").poster = fr; const o = $("outv"); if (o) o.poster = fr; }
    if (SCROLL) setTimeout(() => { M.scrollTop = SCROLL; }, 600);
    if (s === "start") { const g = M.querySelector(".grid"); if (g) g.insertAdjacentHTML("beforebegin", briefBox() + refsBox() + autoBox() + kitsBox()); loadKits(); loadBrief(); loadRefs(); }
    if (s === "visuals" && sub.visuals === "trend") { fitGal(M); galQ.length = 0; galQ.push(...M.querySelectorAll(".gcard")); galBusy = false; galNext(); }
    if (s === "hook") { const h = M.querySelector(".howto"); if (h) h.insertAdjacentHTML("afterend", hookLab()); if (!HL || HL._for !== P.name) { HL = null; loadHookLab().then(() => HL && (HL._for = P.name)); } }
    if (s === "watch") {
      const two = M.querySelector(".two"); if (!two) return;
      const [lc, rc] = two.children;
      lc.insertAdjacentHTML("beforeend", notesBox()); paintNotes();
      const r0 = rc.querySelector(".row"); (r0 || rc.firstChild).insertAdjacentHTML("afterend", healthBox() + postKitBox() + kitsBox());
      loadHealth(); loadPostKit(); loadKits();
      const o = $("outv"); if (o) o.addEventListener("timeupdate", () => { const b = $("nAdd"); if (b) b.textContent = t("n_add", tc(o.currentTime)); });
    }
  };

  /* ---------------------------------------------------------------- events */
  async function reloadP() { P = await api(`/api/project/${P.name}`); L = await api(`/api/project/${P.name}/look`); setupPlayer(); }
  pane().addEventListener("click", async (e) => {
    const mv = !e.target.closest("[data-pro]") && e.target.closest("[data-mv]");
    if (mv && P) {  // pick / unpick a 2026 motion type (Claude places the ticked ones) and play it on your video
      e.preventDefault(); e.stopPropagation(); ac();
      const ty = new Set(L.visuals.types || []), id = mv.dataset.mv, adding = !ty.has(id); adding ? ty.add(id) : ty.delete(id);
      await save({ visuals: { density: L.visuals.density, types: [...ty] } }); mv.classList.toggle("picked", adding);
      if (adding) demoGal(id); else stopDemo(); return;
    }
    const el = e.target.closest("[data-pro]"); if (!el || !P) return;
    const a = el.dataset.pro, d = el.dataset;
    if (a === "autoset") return;  // handled on change
    e.preventDefault(); e.stopPropagation();
    if (a === "mvplay") { ac(); return demoGal(d.id); }
    if (a === "auto") {
      if (!hasBrief()) { const b = $("brBox"); toast(t("auto_gate"), 6000); if (b) { b.scrollIntoView({ behavior: "smooth", block: "center" }); b.classList.remove("flash"); void b.offsetWidth; b.classList.add("flash"); } return; }
      CJ = await api(`/api/project/${P.name}/claude`, { kind: "auto" }); if (CJ.state === "error") return toast(CJ.log, 6000); return pollClaude();
    }
    if (a === "brchip") { BR.answers[d.q] = BR.answers[d.q] === d.v ? "" : d.v; el.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("on", BR.answers[d.q] === b.dataset.v)); return; }
    if (a === "brmic") return mic(el, "brText");
    if (a === "brgo") {
      BR.text = $("brText").value;
      if (!hasBrief()) { toast(t("br_need")); return $("brText").focus(); }
      el.disabled = true; busy(true);
      const cl = $("brClaude"), r = await api(`/api/project/${P.name}/brief`, { answers: BR.answers, text: BR.text, render: $("brRender").checked, claude: !!(cl && cl.checked) });
      busy(false); el.disabled = false; BRout = r;
      if (r.look) { L = r.look; paintChrome(); buildCaps(); render(); updatePreview(); }
      toast(t("br_done"));
      if (r.claude && r.claude.state !== "error") { CJ = r.claude; pollClaude(); } else if (r.render) watch();
      return;
    }
    if (a === "rfdel") { const r = await api("/api/refs", { delete: d.id }); RF = r.refs || []; const l = $("rfList"); if (l) l.innerHTML = refCards(); const m = $("rfMix"); if (m) m.innerHTML = mixTable(); return; }
    if (a === "rfpick") { MIX[d.p] = d.id; const m = $("rfMix"); if (m) m.innerHTML = mixTable(); return; }
    if (a === "rfgo") {
      const kit = $("rfKit").checked ? ($("rfKitName").value.trim() || t("rf_kit_ph")) : "";
      el.disabled = true; busy(true);
      const r = await api(`/api/project/${P.name}/style`, { picks: MIX, kit });
      busy(false); el.disabled = false;
      if (!r.ok) return toast(r.msg || t("rf_err"));
      RFout = r.notes || []; if (BR) BR.styled = true;
      L = r.look; paintChrome(); buildCaps(); render(); updatePreview(); toast(kit ? `${t("rf_done")} · ${t("k_saved")}` : t("rf_done"));
      return;
    }
    if (a === "napply") { CJ = await api(`/api/project/${P.name}/claude`, { kind: "notes" }); if (CJ.state === "error") return toast(CJ.log, 6000); return pollClaude(); }
    if (a === "ncopy") { const txt = (P.comments || []).filter((c) => !c.done).map((c) => `- ${tc(c.at)}: ${c.text}`).join("\n");
      try { await navigator.clipboard.writeText(`Edit notes for ${P.name}:\n${txt}`); toast(t("n_copied")); } catch (er) { toast(txt, 8000); } return; }
    if (a === "nadd") { const tx = $("nText").value.trim(); if (!tx) return $("nText").focus(); P.comments = await api(`/api/project/${P.name}/comments`, { at: cur(), text: tx }); $("nText").value = ""; return paintNotes(); }
    if (a === "ndel") { P.comments = await api(`/api/project/${P.name}/comments`, { delete: true, id: +d.id }); return paintNotes(); }
    if (a === "nmic") return mic(el);
    if (a === "nseek" || a === "hseek") { if (d.at === "") return; const x = +d.at, o = $("outv"); if (o) { o.currentTime = x; o.play().catch(() => {}); } seekE(x); return; }
    if (a === "hrun") { await api(`/api/project/${P.name}/health`, {}); return loadHealth(true); }
    if (a === "hfix") {
      const it = ($("hList")._items || [])[+d.n]; if (!it || !it.fix) return; const f = it.fix;
      if (f.action === "ask") { $("nText").value = f.text; const o = $("outv"); if (o && it.at !== null) o.currentTime = it.at; return $("nText").focus(); }
      if (f.action === "hooklab") return go(STEPS.indexOf("hook"));
      busy(true); const r = await api(`/api/project/${P.name}/fix`, f); busy(false);
      if (r.project) { P = r.project; setupPlayer(); } toast(r.msg || "✓"); return loadHealth();
    }
    if (a === "hlplay") { const c = HL.candidates[+d.i]; const r = await api(`/api/project/${P.name}/srcclip?s=${c.start}&e=${c.end}`); if (r.url) demoClip(r.url, `${t("hl_h")} #${+d.i + 1}`, c.end - c.start); return; }
    if (a === "hluse") {
      const c = HL.candidates[+d.i], box = el.closest(".hlc"), v = (k) => box.querySelector(`[data-hl="${k}"]`).value;
      busy(true); HL = await api(`/api/project/${P.name}/hooklab`, { from: c.from, to: c.to, probe: c.start, rows: joinRows({ top: v("top"), box: v("box"), bot: v("bot") }), tag: v("tag") });
      HL._for = P.name; await reloadP(); busy(false); render(); toast(t("hl_set"), 5000); seekE(0); return;
    }
    if (a === "hloff") { busy(true); HL = await api(`/api/project/${P.name}/hooklab`, { off: true }); HL._for = P.name; await reloadP(); busy(false); return render(); }
    if (a === "pkb") { await api(`/api/project/${P.name}/postkit`, {}); return loadPostKit(true); }
    if (a === "pkcopy") { try { await navigator.clipboard.writeText($("pktext").value); toast(t("pk_copied")); } catch (er) { $("pktext").select(); } return; }
    if (a === "ksave") { const nm = $("kName").value.trim() || t("k_ph"); await api(`/api/project/${P.name}/kit`, { kit: nm, default: $("kDef").checked }); toast(t("k_saved")); return loadKits(); }
    if (a === "kapply") { busy(true); const r = await api(`/api/project/${P.name}/kit`, { apply: d.id }); busy(false); if (r.ok) { L = r.look; toast(t("k_applied")); render(); } else toast(r.msg); return; }
    if (a === "kdef") { const k = await api("/api/kits"); SET = await api("/api/settings", { default_kit: k.default === d.id ? "" : d.id }); return loadKits(); }
  }, true);
  pane().addEventListener("change", async (e) => {
    if (e.target.dataset && e.target.dataset.pro === "autoset") { SET = await api("/api/settings", { auto_edit: e.target.checked }); return; }
    if (e.target.id === "kImp" && e.target.files[0]) {
      try { const kit = JSON.parse(await e.target.files[0].text()); const r = await api("/api/kits/import", { kit }); if (r.ok === false) toast(r.msg); else { toast(t("k_saved")); loadKits(); } } catch (er) { toast("Not a kit file"); }
      e.target.value = "";
    }
  });
  pane().addEventListener("input", (e) => {  // Hook Lab: the mini title preview follows the fields
    const box = e.target.closest && e.target.closest(".hlc"); if (!box || !e.target.dataset.hl) return;
    const v = (k) => box.querySelector(`[data-hl="${k}"]`).value; const pv = box.querySelector(".hlprev");
    if (pv) pv.outerHTML = hlPrev({ top: v("top").toUpperCase(), box: v("box").toUpperCase(), bot: v("bot").toUpperCase() });
  });
  document.addEventListener("keydown", (e) => { if (e.target && e.target.id === "nText" && e.key === "Enter") { e.preventDefault(); const b = document.querySelector('[data-pro="nadd"]'); if (b) b.click(); } });
  // after a look change, the scene pages are re-written in ~1 s: refresh the live URLs so the phone shows the new look
  const _save = save;
  save = function (partial, quiet) {  // eslint-disable-line no-func-assign
    const r = _save(partial, quiet);
    if (P && partial && ["palette", "accent", "fonts", "hook", "extras"].some((k) => k in partial)) {
      clearTimeout(save._t); save._t = setTimeout(async () => { const q = await api(`/api/project/${P.name}`); if (q && q.overlays) P.overlays = q.overlays; }, 2600);
    }
    return r;
  };
})();
