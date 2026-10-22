# Motion-graphic, hook, B-roll and caption trends: short-form 2025–2026

Reference catalog for extending the vedit / HyperFrames pipeline (1080 × 1920, 30 fps, GSAP scenes rendered with alpha, composited with ffmpeg).
Researched 2026-10-21 from public articles, template marketplaces, tool docs and platform blogs (sources at the end). Everything is summarised in our own words. Most sources are vendor or marketplace pages, so each item carries an **evidence** note: **strong** means several independent sources or a platform's own data; **medium** means clear marketplace supply or tutorial demand; **weak** means inferred or a single source.

> **Scope check against the toolkit.** The brief's "existing" list was cross-checked with `DESIGN_SYSTEM.md`. The design system already has `chat` (bubbles plus typing dots), `choice` (A–D quiz), `map`, `stamp`, `terminal`, `phone`, `email`, `error`, `loading`, `meter`, `mindmap`, `loop`, `tiles`, `approval`, `cta`, `chips`, `pipeline`, the cam bubble, the split `zoomclip` layout and the news highlighter. Ideas that only upgrade one of these are listed separately in **§1b** and are **not** counted in the 39 new types.

---

## 0. Conventions used below

### Placement zones (1080 × 1920)
The hard limits come from DESIGN_SYSTEM §2 and §15: nothing above y 220, nothing below y 1480, and nothing right of x 936 between y 700 and 1480 (that is the platform button column). Side margins are 64 px.

| Code | Zone | Use |
|---|---|---|
| **TB** | **Top band**, x 64–936. On talking-head footage use **y 236–420**: Lloyd's head top sits at about y 380–450, so check each video. On screen-demo or back-cam footage, where the top is browser chrome or wall, use **y 236–600**. | Small cards, pills, badges, one-line headers |
| **SR** | **Side rail**. Left: x 64–380, y 480–1150. Right: x 600–936, **y 236–690 only**. Use it only when the face box leaves room, and check per video. | Mini cards, stickers, small phones, polaroids |
| **CB** | **Chest band**, y 1150–1460, x 64–936. Use it only when the chin is above y 1120. While it is up, captions move to TB (`caption_zones` y 240) or hide. | Compact charts, cards, tier rows |
| **FS** | **Full-screen opaque page.** B-roll moments only, when the face is not needed. Content sits at y 300–1460, captions low at y ≈ 1420. The page is **opaque**: the footage cuts away, so it is never blurred or dimmed underneath. | Boards, timelines, device frames, big charts |
| **ON** | **On-screen anchored** (screen-demo footage). Sits **beside** the UI target with a leader line and never fills over it. | Rings, loupes, keycaps, labels |

**Never:** a graphic over the face; blur, dim, vignette, grain, LUT or colour wash on footage; text in the right button column; content below y 1480.

### Motion rules inherited from DESIGN_SYSTEM §6
- Animate only transform, opacity, filter (on graphics), colour and clip-path.
- Everything is deterministic: no `Math.random()` (use a seeded PRNG such as mulberry32 with a fixed seed) and no `repeat:-1` (use finite repeats).
- No bouncy easing on text and no spinning text. `back.out` and `bounce.out` are for small objects only: pills, icons, stickers.
- Default entrance is 0.42–0.5 s expo.out or power3.out. Default exit is 0.18–0.3 s power2.in.
- At 30 fps, 1 frame = 0.033 s, 0.1 s = 3 frames and 0.2 s = 6 frames. Work in 2-frame steps when you want the **"on-twos" handmade feel** (12–15 fps stepped motion, a 2026 trend).
- GSAP 3.13+ ships **SplitText, DrawSVG and MorphSVG free** (they used to be paid Club plugins). DrawSVG and MorphSVG make most of the stroke and morph items below trivial.

### SFX vocabulary
The existing synthesized set in `tools/sfx.py` is `sw_deep`, `sw_air`, `sw_whip`, `sw_shimmer`, `sw_reverse`, `swish`, `pop`, `tick`, `ding`, `typing`, `shutter`, `riser`, `boom` and `hit`. Sounds marked **NEW** would need a new synth patch. Lloyd's **clean** style uses swooshes only, so every item also lists a `clean:` fallback. Keep SFX under the voice, at 0.5 or less.

---

## Trend signals in one screen

1. **Word-by-word captions are the baseline. The full Hormozi package (yellow keyword, a whoosh per word, emoji) reads as saturated.** The successor is "dynamic minimalism": the same timing, fewer colours, no per-word SFX. Coloured **pill** backgrounds are rising. *(strong: Blitzcut 2026, Shotstack, Submagic docs)*
2. **The platforms differ.** TikTok rewards a raw look and punishes graphics that look like ads. Shorts rewards speed, where heavy graphics hurt completion. Reels rewards polish. Kinetic captions are native everywhere. *(medium: Mirra 2026)*
3. **Handmade and imperfect motion** is in: wobbly strokes, scribbles, paper and collage, torn edges, stepped "on-twos" motion. It reads as a reaction to AI-polished sameness. *(strong: Videobolt, GraphicDesignJunction, AutoAE, Tangence, 2026)*
4. **Phone and app UI mockups are the biggest template category:** Dynamic-Island alerts, search bars, AI prompt bars, chat, notification packs, glass docks. *(strong: Envato, Videohive, AutoAE and Uppbeat supply)*
5. **Liquid glass** (the iOS 26 look) is emerging for tech and AI content, but still more vendor push than proven adoption. *(medium)*
6. **Tier lists** drew more than 1B views on YouTube in H1 2025 (YouTube's own blog). Ranking formats are hot for Shorts. *(strong)*
7. **The split or stacked screen** and **green-screen commentary** (speaker over a screenshot of an article or post) remain default formats. *(strong)*
8. **Screen-Studio-style demos** (click-driven auto-zoom, smoothed and enlarged cursor, framed window on a background, vertical re-framing) are the reference look for software tutorials. Competitors such as FocuSee add 3D tilt and spotlight. *(strong)*
9. **Hooks** now stack three layers that must agree: the spoken line, the frame-1 visual and the frame-1 caption (no fade-in). The spoken hook is about 8–15 words and lands by 2–2.5 s. **Re-hooks** around 10–12 s and **seamless loops** at the end help retention. *(strong, practitioner consensus)*
10. **Editorial type mixes:** a serif revival, script accents and a mono for data. Bold sans (700–900) still owns the primary captions. *(medium)*

---

## 1. Motion graphics: 39 new types

Format for each entry: **Look**, **Use when**, **Motion** (in → hold → out), **SFX**, **Place**, **Build**, **Evidence**.

### A. Phone and app UI mockups (generic, unbranded: never copy a real brand's logo or trade dress)

#### 1. Dynamic-Island alert · `island`
- **Look:** a black pill at top centre that stretches into a rounded banner (icon tile, bold title, one-line body), then shrinks back to a pill.
- **Use when:** a "something just happened" beat ("Na-approve na yung payment", "Build failed", "New message from client"). It works well as a **hook interrupt**.
- **Motion:** the pill (300 × 88, r 44) scales in from 0.6 in 0.2 s back.out(1.8). It **morphs** to the banner (960 × 210, r 56) via width, height and radius in 0.5 s expo.out. Icon and text rise y +12 → 0 with a 0.05 s stagger, starting 0.15 s into the morph. Hold 1.5–2.5 s. It collapses back to the pill in 0.35 s power3.in, then the pill fades out in 0.15 s.
- **SFX:** NEW two-tone "notif" chime (soft sine at 880 → 1320 Hz, 0.18 s). `clean: sw_air`.
- **Place:** TB, centred at y 236. The top edge may sit at y 222, never higher.
- **Build:** a single div with border-radius, or MorphSVG. Icon is an SVG on an orange tile.
- **Evidence:** strong (multiple Envato, Gumroad and Uppbeat Dynamic-Island packs, plus vertical notification packs).

#### 2. Search bar with autocomplete · `search`
- **Look:** a rounded white or glass search pill with a magnifier icon. The query types in, a dropdown of 3–5 suggestions slides open, and one suggestion lights orange.
- **Use when:** "Lahat nag-se-search ng…", showing what people ask, or setting up a question hook. It also suits "top searches" stats.
- **Motion:** the bar rises y +30 and blurs 10 → 0 in 0.45 s expo.out. The caret blinks twice (stepped, finite). Typing runs at 0.045 s per character, stepped with clip-path or char spans. The dropdown height animates 0 → auto in 0.3 s power3.out and rows stagger 0.06 s from x −20. The selected row gets an orange left rule and tint in 0.2 s. Out: the dropdown collapses in 0.2 s, then the bar fades in 0.2 s.
- **SFX:** `typing` (0.22), then a NEW soft click on the selection. `clean: sw_air` on entry only.
- **Place:** the bar alone at TB, y 236–330. With the dropdown, use the screen-demo top band (y 236–600) or CB.
- **Build:** HTML only. Never show the Google logo; use a neutral wordmark-free bar.
- **Evidence:** strong (Videohive vertical search-bar template, several Envato search-bar items, AutoAE "animated Google search" product).

#### 3. Social post card (X-style) · `post`
- **Look:** an avatar, display name, handle and generic orange check, then the post text, then a metrics row (replies, reposts, likes, views) that counts up. The heart fills orange.
- **Use when:** quoting what someone posted (AI news, a hot take, a founder announcement) in Newsroom-style videos.
- **Motion:** the card rises and blurs in (y +40, blur 12 → 0, 0.45 s expo.out). Text reveals **word by word** (0.04 s stagger) or as a typewriter. Metrics count up over 0.8 s power2.out (tabular, stepped spans). The heart pops at the end (scale 0.6 → 1.25 → 1, back.out(2.4), 0.35 s) with 6 small burst dots. Out: y −20 and fade in 0.25 s.
- **SFX:** `pop` on the heart, light `tick` × 3 on counters. `clean: sw_air`.
- **Place:** CB (compact, 900 px wide) or FS. Real posts use a **screenshot plus source pill**; rebuilt ones are labelled "Rebuilt" (follow the Newsroom source rules).
- **Evidence:** strong (TwitterShots video export with a 9:16 rise-in and count-up, Jitter and Envato tweet templates, Premiere typewriter-tweet MOGRT).

#### 4. Forum thread card (Reddit-style) · `thread`
- **Look:** a vote column (▲ count ▼) beside the title and body. Reply cards indent underneath, joined by connector lines. The top reply gets an orange edge.
- **Use when:** "Ito ang tanong ng isang user…", community pain points, story-time setups.
- **Motion:** the parent card enters (0.45 s expo.out). The vote count ticks up over 0.6 s. Connector lines draw down (DrawSVG, 0.3 s power2.out), then replies slide in x +40 with a 0.25 s stagger. The highlight edge fades in over 0.2 s.
- **SFX:** `tick` on votes, `swish` per reply. `clean: sw_air`.
- **Place:** FS for long threads, CB for 1 post plus 1 reply.
- **Evidence:** strong (Reddit-story formats: 19.6M #reddit TikTok posts per TechCrunch 2026; Kapwing guide).

#### 5. Voice-note bubble · `voicenote`
- **Look:** a chat bubble with an orange play button, 40–60 waveform bars and a mono duration. A progress fill sweeps across the bars.
- **Use when:** "Nag-voice message sa'kin yung client…", quoting audio, a podcast clip, or AI voice output.
- **Motion:** the bubble pops in (scale 0.85 → 1, 0.35 s back.out(1.6), small object). The bars grow from the baseline (scaleY 0 → 1, stagger 0.012 s, 0.3 s power3.out). The play icon morphs to pause (MorphSVG, 0.2 s). The progress tints bars orange in sync with the actual audio over its real duration (linear).
- **SFX:** the real audio clip, or NEW "blip" on play. `clean: none`.
- **Place:** TB (bubble 700 × 140) or CB.
- **Build:** bar heights are precomputed from the clip's RMS (numpy), so the waveform is truthful and deterministic.
- **Evidence:** medium (Envato vertical chat kits list voice-waveform bubbles).

#### 6. Incoming-call banner · `call`
- **Look:** a full-width rounded banner with an avatar circle, a caller name ("Boss", "Client", "Future mo"), the line "incoming call…", and accept and decline buttons.
- **Use when:** comedic interrupts or story cold-opens ("Tapos tumawag yung client ng 2 AM…").
- **Motion:** the banner slides down from y 40 to y 236 in 0.45 s expo.out. The avatar ring pulses 3× (scale 1 → 1.25, fading, 0.6 s each, finite). Accept or decline presses on cue: the button scales to 0.9 and back in 0.15 s, then the banner collapses up in 0.3 s power3.in.
- **SFX:** NEW two-note marimba ring, 2 cycles at 0.25. `clean: sw_air`.
- **Place:** TB.
- **Evidence:** weak/medium (phone-UI packs carry call alerts, e.g. the Dynamic-Island packs listing calls).

#### 7. Feed-scroll phone · `feed`
- **Look:** a generic phone frame with a vertical feed of cards that flick-scrolls and stops on one post, which highlights.
- **Use when:** "Habang nag-i-scroll ka…", doom-scroll commentary, showing many examples fast.
- **Motion:** the phone rises in 0.5 s expo.out. Run 3–4 flicks: feed y keyframes, each 0.45 s power4.out, with 0.15 s rests. The final card scales to 1.04 and gains an orange ring (0.25 s). Out: the phone drops y +60 and fades in 0.3 s.
- **SFX:** `swish` per flick. `clean: sw_air` on the first flick only.
- **Place:** FS, or SR left (phone 340 × 700 at x 64–404) when the face sits right of centre.
- **Evidence:** medium (Envato 3D phone-with-bubbles loops, phone UI packs).

### B. Annotation and attention

#### 8. Hand-drawn annotation kit · `scribble`
- **Look:** marker-style **circle, underline, arrow, curved arrow, scribble-out, X and check**. Strokes are 10–14 px with round caps, in orange #FF6A00 or white, with slight wobble.
- **Use when:** pointing at a keyword in a caption, a number on screen, a UI button, or an object he holds up. It is the most-taught "simple" motion graphic for Shorts.
- **Motion:** draw-on with DrawSVG (or a dashoffset tween) for 0.35–0.5 s power2.out. Arrows draw the shaft, then the head (the head takes 0.12 s). While held, **boil**: swap between 3 pre-jittered path variants every 2 frames (deterministic). Out: reverse-draw in 0.2 s power2.in or fade in 0.15 s.
- **SFX:** NEW marker squeak (band-passed noise sweep, 0.25 s). `clean: swish`.
- **Place:** ON (around the target, never filling it) or next to captions and keywords. On talking-head footage, only around objects or text, **never on the face**.
- **Evidence:** strong (Motion Array scribble-arrow and hand-drawn packs, FlexClip, Shorts editing guides recommending drawn-on arrows over popped ones).

#### 9. Magnifier loupe · `loupe`
- **Look:** a round lens (Ø 360–420) with a 10 px orange ring and soft shadow, showing a 2–2.5× zoom of a small detail. A thin leader line connects the lens to the spot it magnifies.
- **Use when:** tiny UI text, a price, a setting toggle or a line of code, in screen demos or screenshots.
- **Motion:** a small orange dot pings on the target (ring Ø 20 → 80, 0.35 s). The lens grows from that point (scale 0.2 → 1, 0.4 s back.out(1.6)) while **travelling to a free zone** (0.45 s expo.out), so it never covers the target or the face. The leader draws in 0.2 s. Hold 1.5–3 s. Out: the lens shrinks back to the point in 0.3 s power3.in.
- **SFX:** `sw_air` (rising) on open, `sw_reverse` on close.
- **Place:** ON (lens in TB or an empty screen region).
- **Build:** for **screenshots**, HTML only (two img layers, one scaled, with `clip-path: circle()`). For **live footage**, ffmpeg: `crop` the target box → `scale` 2.2× → circular alpha via `geq` (alpha 255 inside radius r, else 0) → `overlay` at the lens position with `enable='between(t,T0,T1)'` and a 0.2 s alpha fade. The HTML layer supplies the ring, leader and ping on the same timeline.
- **Evidence:** medium (CapCut ships a magnifying-glass zoom effect; tutorial guides stress zooming tiny UI for vertical feeds).

#### 10. Before / after slider · `wipe`
- **Look:** two states split by a white 6 px divider with a round orange-ring knob (◀ ▶). BEFORE and AFTER mono chips sit in the top corners.
- **Use when:** thumbnail v1 vs v2, raw vs edited, old prompt output vs new, manual vs automated result.
- **Motion:** the divider starts at the left edge. It sweeps to 100% in 1.1 s power2.inOut, overshoots back to 50% in 0.5 s power3.out, and holds. The knob pulses once. Chips fade in 0.2 s after the sweep starts.
- **SFX:** long `swish` (1.1 s) on the sweep. `clean: sw_air`.
- **Place:** FS (B-roll), or ON over a screen region when both states are the same UI.
- **Build:** for images, HTML `clip-path: inset(0 X% 0 0)` on the after layer. For footage, render a **matte** (white/black) from the same GSAP timeline, `alphamerge` it with the "after" clip, overlay it on "before", then overlay the handle (ffmpeg crop width cannot animate, so use the matte).
- **Evidence:** strong (Jitter before-after templates, Videohive vertical before/after pack, phone apps exporting 1080 × 1920 wipes).

#### 11. Die-cut sticker pop · `sticker`
- **Look:** an icon or 1–2-word label with a **thick white outline** (10–14 px) and a small hard drop shadow, tilted ±6–10°, like a vinyl sticker. Use SVG or PNG art only; the design system bans emoji glyphs.
- **Use when:** "LEGIT", "FREE", "NEW", "TRY THIS", tool logos as stickers, reactions next to the head.
- **Motion:** slap-on: scale 1.4 → 0.96 → 1 with rotation from ±18° to the final tilt, 0.32 s back.out(2.2) (small object, so allowed). Optional corner-peel highlight sweep (0.4 s). Out: scale 0.8 and fade in 0.15 s, or "peel off" with rotateX 60° and a 0.25 s fade.
- **SFX:** `pop`, or NEW sticker "thwp" (low thud plus paper). `clean: none`.
- **Place:** SR or TB, around the head but **outside the face box**. On B-roll pages, anywhere.
- **Evidence:** medium (sticker effects listed as core vertical-motion devices; 41-piece hand-drawn social element packs).

#### 12. Spotlight ping / "dito" locator · `ping`
- **Look:** 2–3 concentric orange rings radiating from one point, with a small label chip ("Dito", "Click this").
- **Use when:** quickly pointing at a spot without a full annotation, such as a menu item or an icon.
- **Motion:** rings expand Ø 24 → 160 with stroke 6 → 0 and opacity 1 → 0, 0.6 s expo.out each, staggered 0.15 s, 2 cycles (finite). The chip slides from the side in 0.25 s power3.out.
- **SFX:** NEW soft "blip". `clean: none`.
- **Place:** ON.
- **Evidence:** medium (click highlights and pulses recommended in screen-recording guides).

### C. Rankings, prices, data

#### 13. Tier list · `tier`
- **Look:** rows S / A / B / C / D, each with a coloured letter block on the left and logo or icon tiles dropping into the rows. Brand ramp: S #FF6A00, A #FF8A33, B #FF9A4D, C #8C837C, D #4A433F.
- **Use when:** "Ni-rank ko lahat ng AI tools…", reviews, "worth it or not" verdicts.
- **Motion:** rows slide in x −60 with a 0.08 s stagger (0.4 s power3.out). Each tile, on its spoken cue, flies from below (y +300, rotate 6° → 0, 0.45 s back.out(1.6)) into its row slot. The row flashes a tint (0.25 s). The final S-tier tile gets a glow ring.
- **SFX:** `pop` per placement, `ding` on S. `clean: sw_whip` per placement, thinned to 0.28 s spacing or more.
- **Place:** FS for the full list. **CB mini**: only the row being filled (3 rows max, 900 × 300) while he talks.
- **Evidence:** **strong** (YouTube blog: more than 1B views on "tier list" titles in H1 2025, with Shorts used for quick takes).

#### 14. Rating scorecard · `score`
- **Look:** 3–5 criteria rows ("Bilis", "Presyo", "Output") with 5-star or 10-segment bars, then a big final score and a verdict pill.
- **Use when:** tool reviews, "I tried X" videos, comparisons.
- **Motion:** rows enter with a 0.12 s stagger. Stars fill left to right (each 0.06 s, scale 0.6 → 1, back.out(2)). The final number counts up (reuse the counter span-swap) over 0.7 s, and the verdict pill pops (0.35 s back.out(2)).
- **SFX:** `tick` per star (thinned), `ding` on the verdict. `clean: sw_air` on the verdict.
- **Place:** CB or FS.
- **Evidence:** medium (review and "proof" hook formats; Mosaic "bold infographic" preset).

#### 15. Price slash · `price`
- **Look:** the old price (₱ in Inter Tight 800, `--text-2`) gets a hand-drawn orange strike. The new price pops in an orange pill, with a "−60%" badge tilted −8°.
- **Use when:** "₱1,100 a month → libre", deal, savings or ROI moments.
- **Motion:** the old price fades up (0.3 s). The strike draws in 0.25 s power2.out (wobble path). The new pill slams (scale 1.3 → 1, 0.3 s power4.out). The badge rotates in from −30° in 0.3 s back.out(2).
- **SFX:** NEW cash-register "cha-ching" (bell plus noise burst). `clean: sw_whip`.
- **Place:** TB or SR (compact), or CB.
- **Evidence:** medium (urgency and money hooks; deal overlays common in UGC).

#### 16. Receipt print · `receipt`
- **Look:** an off-white thermal receipt (#F4F1EA, JetBrains Mono, zigzag bottom edge) that "prints" down line by line: items, time saved, cost, then a bold orange TOTAL. Optionally a PAID stamp (reuse `stamp`).
- **Use when:** "Magkano talaga ang nagastos ko", time or cost breakdowns, "the receipts" (proof).
- **Motion:** the paper extends via clip-path from the top, **stepped** (each line 0.18 s, small y jitter on twos). Each line types at 0.02 s per character. TOTAL scales 1.15 → 1 (0.25 s). The stamp slams per the design system (0.28 s power4.in).
- **SFX:** NEW printer whirr (filtered noise bursts per line) plus `tick`. `clean: sw_air` plus stamp `hit` off.
- **Place:** SR (receipt 380 px wide), CB, or FS.
- **Evidence:** weak/medium (inferred from analog and handmade trends; common meme format).

#### 17. Timeline · `timeline`
- **Look:** a horizontal (CB) or vertical (FS) line with dated nodes (year or date in JetBrains Mono, event in Inter Tight 700). A playhead dot travels to "NOW".
- **Use when:** "Paano nangyari 'to": AI news history, career story, product versions.
- **Motion:** the line draws in 0.6 s power2.inOut. Nodes pop on cue (scale 0 → 1, 0.3 s back.out(2)) and labels rise (0.3 s). The playhead slides between nodes (0.5 s power3.inOut). The "now" node gets a pulsing ring (2 cycles).
- **SFX:** `tick` per node, `sw_air` on the line. `clean: sw_air`.
- **Place:** CB (horizontal, 3–5 nodes) or FS (vertical, up to 8).
- **Evidence:** medium (Vox-style explainers with charts or maps every 8–10 s; vintage evidence-timeline templates).

#### 18. Calendar / streak grid · `streak`
- **Look:** (a) a tear-off calendar page "DAY 14 / 30", or (b) a 7 × 5 month grid where days fill orange in sequence up to today (a contribution-heatmap feel).
- **Use when:** challenges ("Day 1 of 30"), consistency claims, schedules, deadlines.
- **Motion:** (a) pages tear off with rotateX −100° and fall y +80, 0.25 s each, stepped through N pages fast (0.06 s each at the end). (b) Cells fill with a 0.025 s stagger (tint plus scale 0.8 → 1). Today gets a ring and a label pill.
- **SFX:** (a) NEW paper flip per page (thinned), (b) fast `tick` roll plus `ding`. `clean: sw_air`.
- **Place:** TB (tear-off, 260 × 260, top-left) or CB (grid).
- **Evidence:** medium (challenge and "I did X for 30 days" hooks are widely listed).

#### 19. Countdown / stopwatch · `timer`
- **Look:** JetBrains Mono 140 px tabular "09:59" inside a circular sweep ring, orange on dark glass.
- **Use when:** "Gagawin ko 'to in 10 minutes", speed builds, "60-second" promises.
- **Motion:** the ring draws its full sweep in 0.5 s, then depletes in real or compressed time. Digits update per second (stepped). The last 3 seconds scale 1.08 → 1 each. At zero the ring flashes orange (0.15 s) and a "DONE" pill pops.
- **SFX:** soft `tick` per second (thinned to 0.28 s or more), `ding` at zero. `clean: ding` only.
- **Place:** TB top-left (260 px) for the whole build segment.
- **Evidence:** medium (time-promise hooks, urgency countdowns in hook guides).

#### 20. Growth chart draw-on · `chart`
- **Look:** a minimal line or area chart with a mono axis. The line draws, the end dot pulses, and an "↑ 3.4×" pill pops at the peak.
- **Use when:** views, revenue or time-saved growth; "noong una vs ngayon".
- **Motion:** axes fade in (0.2 s). The line draws in 0.9 s power2.inOut. The area fill fades to 18% (0.4 s, 0.3 s after the line starts). The end dot pops (0.3 s back.out(2)) with 2 rings. The pill slides up (0.3 s). Optional bars variant: bars grow with a 0.08 s stagger.
- **SFX:** `riser` (short, 0.9 s) under the draw, `ding` on the pill. `clean: sw_air`.
- **Place:** CB (900 × 420) or FS.
- **Evidence:** strong (animated charts with pop-ups called out in YouTube motion-design roundups; Vox-style stats overlays).

#### 21. Progress ring / donut · `ring`
- **Look:** a thick orange arc to N% with a big tabular number in the centre and a label under it.
- **Use when:** "87% ng oras ko, napunta sa editing", completion, accuracy and share stats.
- **Motion:** the track fades in (0.2 s). The arc draws to N% in 0.8 s power3.out while the centre number counts up on the same tween. The label rises (0.25 s).
- **SFX:** `tick` roll plus `ding`. `clean: sw_air`.
- **Place:** TB (Ø 200 mini) or CB (Ø 420).
- **Evidence:** medium (loading and progress listed as a UI-animation subcategory on AutoAE).

#### 22. Venn diagram · `venn`
- **Look:** 2–3 translucent circles with labels that slide together. The overlap fills orange with a "sweet spot" label.
- **Use when:** "Skills na kailangan mo: A + B", positioning, "where AI fits".
- **Motion:** circles enter from the sides (x ±300 → ±120, 0.6 s power3.inOut). The overlap clip-path fills (0.3 s). The label pops (0.3 s back.out(2)).
- **SFX:** `sw_air`, `pop` on the overlap. `clean: sw_air`.
- **Place:** CB or FS.
- **Evidence:** weak/medium (Mosaic explainer and diagram presets; general infographic overlays).

#### 23. Word cloud assemble · `cloud`
- **Look:** 12–24 words or phrases of varying size and weight fly in and lock into a tight cloud. One word highlights orange and the rest step back to `--text-dim`.
- **Use when:** "Lahat ng tanong niyo sa comments…", the noise vs the one thing that matters.
- **Motion:** words come from seeded random offsets (±400 px, blur 12 → 0) to their slots, 0.5 s expo.out with a 0.03 s stagger. The highlight word scales 1 → 1.2 while the others dim (0.3 s).
- **SFX:** `swish` (one, covering the stagger), `pop` on the highlight. `clean: sw_air`.
- **Place:** FS or CB.
- **Evidence:** weak (kinetic typography as the main visual is a strong 2026 trend; the cloud layout is our application).

#### 24. Slot-reel picker · `slot`
- **Look:** a 1–3-reel slot window cycling tool names or icons that decelerates and lands on the answer. The window frame flashes orange (the graphic only, never the footage).
- **Use when:** "Anong tool ang gagamitin natin today?", random-pick bits, A/B choice reveals.
- **Motion:** the reel strip translates y through 20–30 items over 1.4 s power4.out (precomputed so it lands exactly). Reels stagger their stops by 0.25 s. On landing: scale 1.06 → 1 (0.2 s) and a frame flash (0.15 s).
- **SFX:** NEW ratchet ticks that slow with the reel, then `ding`. `clean: ding`.
- **Place:** TB (compact 760 × 180) or CB.
- **Evidence:** weak (template-marketplace "selector or scrolling list highlight" UI animations).

#### 25. Win burst (confetti or sparkle) · `burst`
- **Look:** 24–40 small shapes (orange, cream, white: squares, strips, stars) bursting from a graphic element and falling with gravity.
- **Use when:** a success beat: "Gumana!", a milestone number, a quiz answer reveal (Instagram's own quiz sticker does a confetti shower).
- **Motion:** seeded velocities. x/y follow a physics curve precomputed per frame (v0 400–900 px/s, gravity 1800 px/s²) with rotation drift. 1.2 s total, opacity fading after 0.8 s. **Origin must be a graphic** (a stat or pill), and particles stay out of the face box.
- **SFX:** `pop` plus `sw_shimmer`. `clean: sw_shimmer`.
- **Place:** around TB or CB graphics.
- **Evidence:** medium (quiz-sticker confetti; celebratory overlays in vertical promo kits).

### D. Type-driven and editorial

#### 26. Split-flap board · `flap`
- **Look:** an airport departure-board headline. Each character cell (JetBrains Mono 700 on charcoal tiles, with a hairline split across the middle) flips through letters to settle.
- **Use when:** big reveals: "NEW TOOL", tool names, dates, "DAY 07", chapter-like headlines with mechanical drama.
- **Motion:** each cell runs 6–12 flips at 0.04 s each (the top half folds rotateX 0 → −90°, then the next char's bottom half unfolds). Cells stagger 0.03 s left to right. Settle with a 2-frame shake (y ±2 px).
- **SFX:** NEW flap clatter: rapid `tick` grains, density following the active cells. `clean: sw_air` plus one `tick` at settle.
- **Place:** TB (one line, ≤ 12 cells, cell 64 × 92) or FS.
- **Evidence:** weak/medium (a classic motion trope; fits the mono/typography-as-hero trend).

#### 27. Glitch / RGB-split title · `glitch`
- **Look:** a headline that tears into horizontal slices with red/cyan channel offsets for a few frames, then snaps clean. Orange and white versions only.
- **Use when:** tech or AI news hooks ("BREAKING", "LEAKED"), "error" beats, chapter transitions.
- **Motion:** in: 0.4 s of 6–8 **stepped** frames. Each frame shows 3 copies (R/G/B, `mix-blend-mode: screen`) offset x ±4–12 px plus 2–4 `clip-path: inset()` slices shifted ±20 px (seeded). Then everything settles to 0 by 0.5 s. While held, one 2-frame micro-glitch every 1.5–2 s (at fixed timestamps). Out: glitch-out over 0.25 s, then gone.
- **SFX:** NEW digital zap (bit-crushed blip, 0.12 s). `clean: sw_whip`.
- **Place:** TB or FS. **Text only**: the footage is never glitched (that would be a filter).
- **Evidence:** medium (glitch and high-energy transitions in CapCut's 2026 trends; Y2K/glitch/chrome in AutoAE's 2026 list).

#### 28. Torn-paper reveal · `tear`
- **Look:** a paper sheet (cream or kraft, subtle fibre texture) tears along a jagged edge to reveal the headline underneath, or a torn strip carries the text.
- **Use when:** "the real reason", the truth behind a myth, chapter titles with a handmade feel.
- **Motion:** two paper halves pull apart (y ±140, rotate ±3°) over 0.5 s power3.out, **stepped on twos**. The headline underneath is static (or rises 0.3 s). Torn strip variant: the strip slides in x −100% → 0 (0.4 s) with a slight 2° overshoot settle.
- **SFX:** NEW paper tear (crackly noise burst, 0.35 s). `clean: sw_air`.
- **Place:** TB (strip 900 × 160) or FS.
- **Build:** the torn edge is an SVG polygon (seeded jagged points). The texture is a small inline PNG at 8–12% opacity, on the **paper only**.
- **Evidence:** strong (torn paper, cutout craft and mixed-media collage across all 2026 motion-trend roundups).

#### 29. Ransom-note headline · `ransom`
- **Look:** each letter or word cut from a different "magazine" swatch (white, orange, kraft, charcoal), with mixed weights and cases across Inter Tight 900, Great Vibes and JetBrains Mono, each slightly rotated.
- **Use when:** secret and insider hooks, "confession" beats, collage-style thumbnails.
- **Motion:** each piece drops in with scale 1.3 → 1 and rotate settle, 0.22 s expo.out, staggered 0.045 s, stepped on twos. Once assembled, the whole line holds (no wobble on text).
- **SFX:** NEW paper snip (short scissor click per 2–3 pieces). `clean: sw_air`.
- **Place:** TB (fit within 860 px) or FS.
- **Evidence:** medium (collage and cutout trends; magazine-clipping materials named in craft-motion trend pieces).

#### 30. Investigation board · `board`
- **Look:** a dark cork or charcoal board with pinned cards and polaroids (screenshots, tool logos, notes), connected by **orange string**. The camera pans across it.
- **Use when:** "Paano konektado lahat ng 'to", explaining a system or ecosystem, AI-news "conspiracy-style" fun.
- **Motion:** cards drop and pin (scale 1.15 → 1, rotate to ±5°, 0.35 s power3.out). The pin pops (0.2 s back.out(2.5)). The string draws from pin to pin (DrawSVG, 0.4 s power2.inOut, with a slight sag curve). The whole board translates or zooms between clusters (0.8 s power2.inOut), with slow drift while held.
- **SFX:** `tick` per pin, `swish` per string, `sw_air` per pan. `clean: sw_air` per pan.
- **Place:** FS only.
- **Evidence:** strong (many vertical and horizontal detective-board templates: Envato vertical, AEJuice "Connection", VideoBolt, AutoAE evidence timeline).

#### 31. Redaction reveal · `redact`
- **Look:** text lines with solid charcoal bars and tiny "REDACTED" mono labels. On cue the bars wipe away to reveal the hidden phrase, the key word in orange.
- **Use when:** curiosity and secret hooks ("Ang tool na 'to ay [■■■■■]…"), hiding the answer until the payoff, and also re-hooks.
- **Motion:** the text card fades in with the bars already on (0.3 s). Reveal: each bar runs `scaleX 1 → 0` from its right edge in 0.3 s power3.inOut, staggered 0.12 s. The revealed keyword glows (0.25 s).
- **SFX:** `swish` per bar, or NEW tape peel. `clean: sw_air`.
- **Place:** TB or CB. The bars sit on graphic text only, **never on footage** (no blurring or redacting his screen this way; see B-roll 12 for privacy).
- **Evidence:** medium (secret-angle hooks; "top secret file" opener templates).

#### 32. Definition card · `define`
- **Look:** a dictionary entry: the word in Inter Tight 900 96 px, phonetics in JetBrains Mono 30 px (`--text-dim`), the part of speech in Great Vibes, then a 1–2-line Taglish definition in body text.
- **Use when:** introducing jargon: "agentic", "token", "context window", "prompt injection".
- **Motion:** the card rises in (0.45 s expo.out). The word slides in (x −30), phonetics type in (0.03 s per character), an underline draws under the word (0.3 s), and the definition reveals by line (0.08 s stagger).
- **SFX:** `sw_air` plus NEW soft page sound. `clean: sw_air`.
- **Place:** TB (compact, word plus one line) or CB.
- **Evidence:** weak (common edu-creator device; fits the editorial type trend).

#### 33. "POV" label · `pov`
- **Look:** a small orange "POV" chip followed by a one-line scenario in Inter Tight 800, 60–64 px, white.
- **Use when:** POV hooks and skits ("POV: unang araw mo sa bagong AI tool").
- **Motion:** the chip pops (0.3 s back.out(2)). The line types in (0.035 s per character) or reveals word by word. It holds through the hook (2–4 s), then clears with y −14, blur 6, 0.18 s.
- **SFX:** short `typing` (0.22). `clean: none`.
- **Place:** TB, y 236. It must be up on **frame 0**.
- **Evidence:** strong (a long-running TikTok format; POV-scenario aesthetic in Opus 2026).

#### 34. Listicle rank badge · `rank`
- **Look:** a circular orange-gradient badge with a big "#3" (Inter Tight 900), "OF 5" in mono, and a row of 5 progress dots.
- **Use when:** numbered-list videos, to keep a persistent "finish line" visible (retention).
- **Motion:** it pops in (0.35 s back.out(2)). On each item change, the numeral flips (rotateX 90° out, 0.15 s, then in, 0.2 s) and the next dot fills (0.2 s). Out: scale 0.8 and fade (0.2 s).
- **SFX:** `sw_whip` per change. `clean: sw_whip`.
- **Place:** TB, left (x 64, y 236, Ø 150) for the whole video.
- **Evidence:** strong (list hooks with an on-screen number plus ding).

### E. Photo, 3D and "game" layers

#### 35. Polaroid stack · `polaroid`
- **Look:** 3–5 photos or screenshots in white polaroid frames (24 px border, 80 px bottom), with tape strips. They drop onto a pile at varied angles (−9°, 6°, −3°). An optional Great Vibes caption sits on the bottom strip.
- **Use when:** "photo dump" recaps, behind-the-scenes, client results, event recaps.
- **Motion:** each frame drops (scale 1.25 → 1, y −60 → 0, rotate to its angle, 0.45 s power3.out), staggered 0.35 s, with the shadow growing with "landing". A **moving** variant plays a short clip inside the frame. Out: the stack slides off x −120% in 0.4 s power3.in.
- **SFX:** `shutter` per photo, plus NEW paper flick. `clean: shutter` only.
- **Place:** SR (frames 320 px wide), CB, or FS.
- **Evidence:** strong (moving-polaroid carousel trend on Picsart, plus TikTok polaroid frame templates).

#### 36. Parallax 2.5D photo · `parallax`
- **Look:** a still photo split into a foreground subject and a background, moving at different speeds for a slow pseudo-3D push.
- **Use when:** B-roll stills (event photos, a person being discussed, a product shot) that would otherwise sit flat.
- **Motion:** 3–4 s. The background scales 1.0 → 1.06 and moves x −20. The foreground scales 1.0 → 1.12 and moves x +10, both sine.inOut. Keep moves at 3% or less so no inpainting is needed. Entry: crossfade 0.25 s.
- **SFX:** low `sw_deep` at the start. `clean: sw_deep`.
- **Place:** FS (B-roll).
- **Build:** cut the subject with the existing `personmask` (Vision) or a manual PNG layer. Both layers are HTML img elements animated by GSAP.
- **Evidence:** medium (2D/3D hybrid, parallax and documentary slow-push looks in 2026 trend lists).

#### 37. 3D flip card (Myth / Fact) · `flip`
- **Look:** a card that rotates in 3D. The front says MYTH with the claim; the back says FACT with an orange edge.
- **Use when:** myth-busting, "akala mo / pero totoo", before/after of a belief.
- **Motion:** the card enters (0.45 s expo.out). The flip runs rotateY 0 → 180° in 0.7 s power2.inOut, with a lift at the midpoint (scale 1.05, shadow deeper) and `perspective: 1600px`. Use `backface-visibility: hidden` and never show mirrored text (design-system rule). The back text rises 0.2 s after the flip.
- **SFX:** `sw_whip` on the flip, `pop` on the FACT chip. `clean: sw_whip`.
- **Place:** CB (860 × 460) or FS.
- **Evidence:** medium (3D card and tri-fold animations highlighted in YouTube motion breakdowns).

#### 38. App dock / tool stack (liquid glass) · `dock`
- **Look:** a frosted glass pill dock (the glass is **on the graphic**, sampling nothing but its own fill) with 4–6 app tiles. A macOS-style magnify wave passes across, then lands on the chosen tool, which gets an orange ring and a label.
- **Use when:** "Ito ang stack ko", "3 tools", introducing a combo of tools.
- **Motion:** the dock rises (y +40, 0.45 s expo.out). Tiles pop with a 0.07 s stagger (0.3 s back.out(2)). The magnify wave runs scale 1 → 1.35 → 1 across the tiles in sequence (0.12 s offset each, power2.inOut). The selected tile holds at 1.25 with its ring (0.25 s) and the label pill rises.
- **SFX:** NEW glass "tink" per tile (thinned), `pop` on select. `clean: sw_air`.
- **Place:** TB (dock 820 × 150) or CB.
- **Build:** "glass" here is a white-to-transparent gradient fill plus a 1.5 px edge plus a highlight. **No `backdrop-filter` over the footage**, because that would blur his video.
- **Evidence:** medium (AutoAE glass dock and glass button templates; Liquid Glass UI element packs on Videohive and Uppbeat).

#### 39. Achievement / quest pop-up · `achieve`
- **Look:** a game-HUD toast: a trophy or orange icon circle, a mono "ACHIEVEMENT UNLOCKED" kicker, a title ("Unang automation mo"), and an XP bar.
- **Use when:** milestones in tutorials ("Na-install mo na!"), gamified learning series, comedic wins.
- **Motion:** slides in from the left (x −120%, 0.4 s expo.out). The icon ring sweeps 360° (0.6 s power2.out), the XP bar fills (0.5 s power3.out), the title shines once (0.6 s gradient sweep on the text fill). Out: x −40 and fade (0.25 s).
- **SFX:** NEW level-up arpeggio (three quick rising notes) or `ding`. `clean: ding`.
- **Place:** TB.
- **Evidence:** weak (a known meme trope; no 2025–26 trend data found, so treat it as an experiment).

---

## 1b. Upgrades to blocks the toolkit already has (not counted above)

| Existing block | Trending upgrade | Spec notes |
|---|---|---|
| `chat` | **Phone-framed thread** with "Delivered / Read", tapback reaction pops, and an **AI "thinking" shimmer** line before a streamed answer | Shimmer: gradient sweep across grey text, 1.2 s linear, 2 loops. Stream: words at 0.03 s stagger. Tapback: 0.3 s back.out(2.4) |
| `choice` | **Poll result**: two options, % bars fill, the winner gets a check and a confetti `burst` | Bars 0.7 s power3.out, % counts up, winner ring 0.25 s |
| `map` | **Route draw**: pin drop, dashed route drawing, travelling dot, destination pin, distance chip (Google-Earth-zoom-style intro optional) | Route DrawSVG 1.2 s power2.inOut. Pins 0.3 s back.out(2.5). Earth-zoom "trend" clips are common on CapCut |
| `cta` | **Follow button tap**: hand cursor glides in, taps, the button morphs "+ Follow" → "Following ✓", and the follower count ticks +1 | Cursor 0.5 s power3.inOut, press 0.12 s, morph 0.3 s |
| `error` | **Retro OS dialog cascade**: 3–6 stacked warning windows pop with offsets ("too many tabs" chaos) | Each 0.12 s apart, scale 0.9 → 1, `pop`. Evidence weak |
| `tiles` | **Bento grid**: mixed-size tiles assemble (2×1, 1×1, 1×2) with icons and stats | Stagger 0.06 s, from scale 0.94 and blur 8 |
| `list` | **Checklist tick-off**: checkboxes draw checks and done rows get a strike-through | Check DrawSVG 0.25 s, strike 0.2 s, `tick` |
| `stamp` | **Ink stamp texture** (rough edge mask, slight rotation jitter, ink spread) | Keep the 0.28 s power4.in slam |
| `tag` | **Lower-third variant** (name, role, socials) for guests and webinar speakers | Top-band placement stays (bottom is UI-covered) |

---

## 2. Hook styles: 21 formats for the first 1–3 s

**Rules for every hook** (drawn from Kineclip, Opus and Klap):
- The spoken hook is about 8–15 words and finished by **2.0–2.5 s**.
- The **caption is on frame 0** (no fade-in).
- The visual, the spoken line and the on-screen text say the same thing.
- On-screen hook text holds at least 2 s, and frame ~2 s doubles as the thumbnail.
- On-screen text is 8 words or fewer.

**Layout defaults that never cover the face:**
- **Behind word:** `behind`, Inter Tight 900, 300–360 px, orange gradient, top y 285–330.
- **Kicker above the head:** Great Vibes 110–118 px, or Inter Tight 800 64–72 px white, top ≥ y 220.
- **Chest lockup:** y 1150–1460.
- **TB card:** y 236–420.
- Captions hide while hook text is up.

| # | Hook | Pattern template + Taglish example | On-screen design | Why it retains |
|---|---|---|---|---|
| 1 | **Contrarian claim** | "[Common belief]? Mali." / *"Hindi mo kailangan marunong mag-code para gumawa ng app."* | Chest lockup: the belief in `--text-2` 70 px gets a hand-drawn strike (0.25 s), then the counter-claim slams in orange 900 at 130 px. Kicker "Unpopular opinion" in Great Vibes above the head | Cognitive dissonance: viewers stay to see it defended |
| 2 | **Result-first / proof-first** | "Ito yung [result]… in [time]." / *"Ginawa ko 'tong buong landing page in 12 minutes. Walang code."* | Frame 0 = the **result** as FS B-roll (1.2–1.8 s) with a TB stat pill "12 MIN", then a REWIND chip plus a 0.4 s reverse scrub back to the face | The payoff is visible, so the open question becomes "paano?" |
| 3 | **Curiosity gap** | "May [thing] na [surprising fact]…" / *"May isang setting sa ChatGPT na halos walang naka-on… pero dapat."* | `redact` card in TB: "Ang setting: [■■■■■■]". The bar stays until the payoff (re-hook at about 10 s) | An unclosed loop |
| 4 | **"Stop doing X"** | "Tigilan mo na ang [habit]." / *"Tigilan mo na 'yang 'act as an expert' sa prompt mo."* | Quote card in TB with the habit in mono; a hand-drawn X draws across it (0.35 s) plus a stamp "HINDI 'TO" | Loss aversion plus self-identification ("ginagawa ko 'yan!") |
| 5 | **Numbered list** | "[N] [things] na [benefit]." / *"3 AI tools na pumalit sa ₱30k/month kong team."* | A giant "3" **behind** him (orange gradient), the kicker line above, then the `rank` badge persists top-left | A visible finish line: viewers count down |
| 6 | **POV** | "POV: [relatable scenario]." / *"POV: unang araw mo gamit ang Claude Code."* | `pov` chip plus a typed line in TB on frame 0. Optional first-person screen footage | Immersion: the viewer casts themself in the scene |
| 7 | **Self-identifying question** | "Ikaw ba 'yung [specific situation]?" / *"Ikaw ba 'yung nag-e-edit pa rin ng captions isa-isa?"* | Two lines in TB, Inter Tight 900 96–110 px, with "Ikaw" in orange. The answer starts within 1.5 s | A personal-relevance filter: the right viewer feels seen |
| 8 | **"I tried X so you don't have to"** | "Sinubukan ko ang [N] [X] para 'di mo na kailangan." / *"Sinubukan ko ang 5 AI video editors… isa lang ang pumasa."* | `dock` flashes the 5 tool tiles, then a `stamp` "1 LANG" on one. Tier-list teaser | The viewer saves effort, and the implied ranking pulls them in |
| 9 | **Reaction cold-open** | Start on the genuine reaction, then the cause. / *"Wait… ginawa niya 'yon nang mag-isa?"* | **Face clean** for 0.5–1.0 s (no overlay), with `hook_zoom` 1.12 → 1. Small TB tag "Claude Code · 2:07 AM", then cut to the screen with a `loupe` on the thing | Emotional contagion plus "what did he see?" |
| 10 | **Mistake / warning** | "Kung [condition], [urgent action] ngayon." / *"Kung naka-on 'to sa account mo, i-off mo na ngayon."* | `island` alert drops at TB with an orange warning icon and title "Babala". Optional low `buzz` | Loss aversion pulls harder than curiosity |
| 11 | **Before / after** | "Dati: [state]. Ngayon: [state]." / *"Ganito thumbnail ko dati… ganito na ngayon."* | FS `wipe` slider with BEFORE/AFTER chips, back on the face by 2.5 s | The transformation is visible: "how?" |
| 12 | **Challenge / Day N experiment** | "Day [N] of [M]: [constraint]." / *"Day 1 of 30: AI lang ang gagawa ng lahat ng content ko."* | `flap` board "DAY 01 / 30" in TB, plus a `streak` badge on later episodes | Serial format: follow for the next day; built-in stakes |
| 13 | **Secret / insider** | "Ito yung [thing] na 'di sinasabi ng [group]." / *"Ito 'yung workflow na 'di sinasabi ng mga agency sa client nila."* | `ransom` or `redact` headline in TB plus a mono kicker "INTERNAL" | Exclusivity and status |
| 14 | **Comparison / versus** | "[A] vs [B]: alin ang [criterion]?" / *"Libre vs ₱1,100 a month: alin mas magaling mag-edit?"* | Two `price` tags in SR left and right of the head, with "VS" in TB (orange, 120 px) | The viewer picks a side and stays for the verdict |
| 15 | **Stat shock** (real, sourced numbers only) | "[Number] ng [group] [surprising fact]." / *"1 sa 3 freelancers, gumagamit na ng AI araw-araw."* (placeholder: verify) | Giant number **behind** him plus a source pill under the kicker | Concrete and credible; the source builds trust |
| 16 | **Direct callout** | "Kung [identity] ka at [pain], para sa'yo 'to." / *"Kung freelancer ka na pagod na sa revisions, para sa'yo 'to."* | TB name-tag chip "PARA SA: FREELANCERS" (mono kicker plus a 900 word) | Identity targeting makes the viewer feel addressed |
| 17 | **Story cold-open (mid-action)** | Drop into the tense middle, no setup. / *"Alas-dos ng madaling araw, nag-crash ang buong website ng client ko."* | `call` banner "Client · incoming call" or a mono timestamp chip "2:07 AM" in TB | Narrative tension: viewers need the resolution |
| 18 | **Ranking / tier-list** | "Ni-rank ko lahat ng [X]." / *"Ni-rank ko lahat ng AI tools na ginamit ko ngayong taon."* | CB mini `tier` with an empty S row and a "?" tile; the first logo drops by 2 s | An opinionated ranking invites disagreement and comments; trend-verified |
| 19 | **Money / value reveal** | "Ito 'yung ₱[low] na [X] na pumalit sa ₱[high]." / *"Ito 'yung ₱0 na tool na pumalit sa ₱5,000 kong subscription."* | `price` slash in TB: ₱5,000 strike, then ₱0 pill | Money specificity is instantly valuable |
| 20 | **Payoff tease** (use sparingly) | "Sa dulo, [reward]." / *"Sa dulo, ibibigay ko 'yung buong template, libre."* | Small TB chip "FREE TEMPLATE SA DULO" plus a progress bar with an orange marker at 100% | Commitment and a reason to finish. Overuse feels baity |
| 21 | **Visual pattern interrupt** | A physical action or snap change, then the claim. / *Closes the laptop: "Tapos na ang manual editing."* | The existing `look` B&W → colour snap, or a hard 1.12 → 1 punch. Caption still on frame 0 | Breaks scroll autopilot before conscious processing |

**Re-hook and loop add-ons**
- **Re-hook (about 10–12 s into a 30 s video):** open a second loop. Examples: a redaction bar that is still closed, a "pero may mas malala pa…" line, a `rank` badge jumping to #1 tease.
- **Loop ending:** the last line or frame flows into the first. Example: end on "…kaya tigilan mo na 'yang—" and cut to frame 0's "Tigilan mo na 'yang…". Practitioners report that clean loops overperform; treat it as a tested heuristic, not a platform rule.

---

## 3. Visual and B-roll styles for screen-demo videos: 14 styles

Hard rule recap: **no dimming, blurring or spotlight-darkening of the screen** (the trendy "spotlight that fades the rest" is **out** for Lloyd). Attention comes from rings, zoom, loupes and pop-outs instead.

#### B1. Click-driven auto-zoom (Screen-Studio style) · extends `zoomclip`
- **Look:** a wide view for context, then a smooth push into whatever he clicks or types into, then back out. The camera eases like a spring, not linearly.
- **Use when:** every step of a software demo.
- **Motion:** levels are 1.0 (context) → 1.6–2.2 (action), never more than 2.5×. The move is a spring-like ease: Screen Studio exposes tension, friction and mass. Approximate it with GSAP `expo.inOut` at 0.7–0.9 s, or precompute a critically damped spring. Start the zoom about 0.3 s **before** the click or the spoken mention, and hold at least 0.5 s after the action settles. For a 30 s clip use about 3 zooms (setup, key action, result).
- **SFX:** soft `sw_air` on push-ins only. `clean: same`.
- **Place:** the screen region of the split layout (top 1080 × 1080) or full frame.
- **Build:** log click and keystroke timestamps and positions during recording (a tiny macOS CGEventTap logger), then auto-generate `zoomclip` keyframes `{t, x, y, w, ease}` anchored to clicks. Merge clicks closer than 1.2 s into one zoom. **Cursor smoothing or enlarging needs the cursor hidden at capture plus a logged path** (draw an SVG cursor on the overlay). If the cursor is baked into the recording, skip smoothing. Motion blur on pans is optional and **off by default** (it is a blur).
- **Evidence:** strong (Screen Studio auto-zoom guide, reviews, FocuSee and Smooth Recorder clones).

#### B2. Floating device / browser frame with 3D tilt · `frame3d`
- **Look:** the recording inside a generic browser window (traffic-light dots, URL pill) or laptop/phone frame, floating on the brand background (#0C0908 plus radial orange glows plus dot grid). Slight perspective tilt, deep soft shadow, thin orange edge glow.
- **Use when:** the intro shot of a tool, "ito yung app", transitions between demo sections, and when the raw recording is too wide for vertical.
- **Motion:** in: scale 0.9 → 1, y +80 → 0, rotateX 12° → 6°, 0.6 s expo.out. While held, drift rotateY −10° → −4° and rotateX 6° → 3° over the shot (sine.inOut). Out: y −40 and fade, 0.3 s.
- **SFX:** `sw_deep` on entry. `clean: sw_deep`.
- **Place:** FS (B-roll).
- **Build:** the HTML renders the background, frame chrome and shadow with a transparent "screen hole". ffmpeg maps the recording into the hole with the `perspective` filter (4 corner points per keyframe, or fixed corners plus an HTML drift on the chrome only), then overlays the chrome on top.
- **Evidence:** strong (Rotato, Screen Studio window treatments, FocuSee 3D motion, Screenhance device templates).

#### B3. UI target ring + leader label · `target`
- **Look:** a rounded-rect outline (6 px orange, outer glow) or four corner brackets around the exact UI element, plus a label chip **outside** the target joined by a 2 px leader line.
- **Use when:** "I-click mo 'to", naming fields, settings, buttons.
- **Motion:** the outline draws on (dashoffset, 0.4 s power2.out) or the brackets fly in from 30 px outside (0.3 s power3.out). One pulse (scale 1 → 1.04 → 1, 0.3 s). The leader draws in 0.2 s and the chip slides in 0.25 s. Hold 1.5–3 s. Out: fade 0.2 s.
- **SFX:** none, or NEW soft click when synced to his click. `clean: none`.
- **Place:** ON. Follow the zoom path (reuse the zoomclip transform so the ring stays locked to the element).
- **Evidence:** strong (callout rules in Clueso, TechSmith and the Adobe community; "arrows, circles, highlight boxes" in Shorts guides).

#### B4. Click ripple + cursor halo · `click`
- **Look:** an expanding orange ring at every click, plus an optional soft orange halo following the cursor.
- **Use when:** fast demos where viewers lose the cursor.
- **Motion:** ripple Ø 36 → 130, stroke 6 → 0, opacity 0.9 → 0, 0.45 s expo.out. Keep it subtle: guides advise a 200–300 ms low-opacity pulse over flashy ripples. Halo Ø 72 at 25% opacity, position from the cursor log.
- **SFX:** NEW soft click at 0.25. `clean: none`.
- **Place:** ON.
- **Evidence:** strong (Clueso, FocuSee click effects, Screen Studio).

#### B5. Keycap shortcut overlay · `keys`
- **Look:** 3D-ish keycaps (r 18, #1D1415 fill, 1.5 px rgba(255,140,60,.3) edge, bottom inner shadow for depth) with JetBrains Mono 52–60 px legends: ⌘ + Shift + 5.
- **Use when:** any keyboard shortcut or typed command he mentions.
- **Motion:** keys rise y +20 → 0 with a 0.06 s stagger (0.25 s power3.out). Each "press" moves y +6 and shrinks the shadow (0.08 s), then releases (0.1 s). Hold 2–3 s, then auto-hide (fade 0.2 s).
- **SFX:** NEW mechanical key clack per key. `clean: none`.
- **Place:** in the lower-left of the screen region but **above y 1480** (e.g. y 1300–1420 on full-frame demos), or TB on split layouts.
- **Evidence:** strong (Clueso keystroke-overlay guidance: bottom-left, 2–3 s; Screen Studio shortcut display).

#### B6. Step-counter rail · `steps`
- **Look:** a TB strip: mono "STEP 2 / 5" kicker, step title (Inter Tight 800 56 px), and a 5-segment progress bar.
- **Use when:** multi-step tutorials, so viewers always know where they are (this also acts as a re-hook).
- **Motion:** on a step change, the segment fills (0.5 s power2.out). The title swaps out with y −14 and blur 6 (0.18 s), and the new one comes in from y +20 (0.3 s expo.out).
- **SFX:** `sw_air` per step. `clean: sw_air`.
- **Place:** TB (y 236–330).
- **Evidence:** strong (how-to hooks recommend a visible label per step; Mosaic product-tutorial preset).

#### B7. Prompt → result split · `promptsplit`
- **Look:** the top half shows the prompt being typed into a generic composer; the bottom half shows the result materialising (preview, generated video, app). A 6 px orange seam sits between them (the zoomclip seam).
- **Use when:** AI-generation demos: "ito yung sinabi ko → ito yung ginawa niya".
- **Motion:** typing at 0.035 s per character (stepped), with a send-button press (0.12 s). A "thinking" shimmer plays for 0.6–1.2 s, then the result reveals (clip-path top → down 0.5 s power3.out, or a hard cut on the beat).
- **SFX:** `typing`, then `sw_shimmer` on the reveal. `clean: sw_shimmer`.
- **Place:** FS split, or top screen with the face at the bottom (existing v7 layout).
- **Evidence:** medium (AutoAE chat and prompt-bar templates; GPT-chat recreations praised in motion breakdowns).

#### B8. Speed-ramp / fast-forward badge · `ff`
- **Look:** while waiting (installs, renders, long generations), the footage runs 4–16× with a "▶▶ 8×" chip and a mono elapsed counter "00:00 → 03:42".
- **Use when:** any wait longer than 2 s; it keeps the honesty without dead air.
- **Motion:** the chip pops (0.25 s back.out(2)). The counter runs on stepped spans. On return to 1×, the chip shrinks out (0.2 s).
- **SFX:** NEW tape-speed whirr (pitch-rising noise) at 0.2, or silence. `clean: none`.
- **Place:** TB on the screen region (x ≤ 936).
- **Build:** ffmpeg `setpts=PTS/8` on that segment (drop audio or duck it).
- **Evidence:** medium (fast-pacing guidance, no dead air; time-lapse badges are common in build vlogs).

#### B9. Scroll-through tall capture · `scrollpage`
- **Look:** a full-length page screenshot (e.g. 1080 × 6000) inside a frame that scrolls in eased segments and rests on key sections, each rest getting a `target` ring.
- **Use when:** showing a whole landing page, doc, results list or long AI output.
- **Motion:** segments of 0.8–1.2 s power2.inOut, with rests of 0.8–1.5 s. An optional thin scroll-position indicator sits inside the frame's right edge.
- **SFX:** soft `swish` per segment. `clean: sw_air` on the first.
- **Place:** FS, or ON inside the split's screen half.
- **Evidence:** medium (screenshot push and jump-zoom already in the Newsroom theme; scrolling backgrounds and loops in vertical kits).

#### B10. Pop-out callout (exploded UI) · `popout`
- **Look:** the exact UI element (button, card, setting row) **lifts out** of the screen as a crisp enlarged copy with a deep shadow and moves to free space. The original spot keeps a thin ring and a leader line back to it.
- **Use when:** when one element matters more than everything else, and a loupe would be too round or small.
- **Motion:** copy scale 1 → 1.4 with rising shadow, moving to its target in 0.5 s expo.out. Hold 1.5–3 s. Return in 0.35 s power2.in.
- **SFX:** `sw_air` up, `sw_reverse` back. `clean: same`.
- **Place:** ON / TB.
- **Build:** crop the element from a still frame (ffmpeg `-ss T -frames:v 1` plus crop) into an HTML img.
- **Evidence:** medium (FocuSee and Screenhance "guided zoom" variants; 3D section pop-outs in AutoAE).

#### B11. Code diff / terminal-tail focus · `diff`
- **Look:** a code or terminal window (JetBrains Mono 28–32 px). Added lines get an orange left rule and an rgba(255,106,0,.12) tint; removed lines are struck through (on the **graphic**). The key output line gets an orange bar and an arrow annotation.
- **Use when:** "ito lang ang binago", AI-edited code, error → fix stories.
- **Motion:** lines reveal with a 0.06 s stagger (x −20, 0.3 s power3.out). The diff tint sweeps left to right (0.3 s). The key line scales 1.02 with the bar drawing (0.25 s), then auto-scrolls to the tail (0.6 s power2.inOut).
- **SFX:** `typing` (if typed), `pop` on the key line. `clean: none`.
- **Place:** FS or ON.
- **Build:** extends `terminal`.
- **Evidence:** medium (minimal tech UI diagrams and product-tutorial overlays).

#### B12. Privacy redaction pills (no blur) · `hide`
- **Look:** a solid charcoal or orange-tinted rounded pill with a lock icon and a tiny mono label "hidden", placed exactly over an email, API key or client name.
- **Use when:** any sensitive data on screen.
- **Motion:** pop (0.2 s back.out(2)). It tracks the zoom path. It stays as long as the data is visible.
- **SFX:** none.
- **Place:** ON (exactly on the data; this is the one allowed "cover", because it only covers data, not his demo action).
- **Build:** HTML overlay keyed to the zoomclip transform, or ffmpeg `drawbox` with `t`-gated enable.
- **Evidence:** strong (redaction guidance in Clueso and ScreenPal; we swap their blur for a solid pill per Lloyd's rules).

#### B13. Desktop zoom-out reveal / window grid · `pullback`
- **Look:** start tight on one app, then pull back to reveal the whole desktop or a 2 × 2 grid of apps all running ("lahat 'to automated"), with chips labelling each.
- **Use when:** showing scale: an automation touching many tools, or "isang click, apat na apps".
- **Motion:** zoom 2.2 → 1 in 1.0 s expo.inOut. Grid tiles settle with a 0.05 s stagger, and chips pop with a 0.08 s stagger.
- **SFX:** `sw_deep` on the pull-back. `clean: sw_deep`.
- **Place:** FS.
- **Evidence:** weak/medium (3D zoom-out reels effects are widely taught; multi-window AI UI mockups on AutoAE).

#### B14. Picture-in-picture face bubble (opt-in) · existing cam bubble
- **Look:** a round face crop with a 6 px orange ring over the screen recording.
- **Use when:** **raw screen-demo stretches only**, when his reaction matters. Lloyd rejected the face bubble on designed pages.
- **Motion:** scale 0.6 → 1, 0.4 s back.out(1.6). Moves to the other side if the demo target goes under it (0.5 s power3.inOut).
- **SFX:** none.
- **Place:** left, x 64, y 1100, Ø 250 (per the §15 safe zone).
- **Evidence:** strong (Tella, Filmora and iOS PiP apps; layout guides note the bubble must stay big enough to read on a phone).

**Layout presets to keep handy:** stacked split with the screen on top and the face below (already built, 50/50 or about 60/40); **70/30** screen-heavy split for dense UIs; **green-screen commentary**, with the speaker cut out (`personmask`) in front of an opaque article or post page. That last one is a strong default for news and reaction formats, and it fits the Newsroom theme without dimming anything.

---

## 4. Caption styles trending now: 8 styles

All are word-by-word, at 1080 × 1920. The design-system shadow stack is `0 0 2px rgba(0,0,0,.85), 0 2px 5px rgba(0,0,0,.6), 0 6px 26px rgba(0,0,0,.55)`. Talking-head `caption_y` is 1250–1290; on screen footage it is about 1390, and on split layouts it sits on the seam.

| # | Style | Exact styling | Animation | When / status |
|---|---|---|---|---|
| C1 | **Dynamic minimalism** (successor to Hormozi) | Inter Tight 800, **96–110 px**, line-height 1.05, tracking −0.015em, white #FFFFFF, keywords #FF6A00 (≤ 30 per video). Shadow stack, no stroke. 1–3 words per chunk, 1 line, max width 860 px | Per word: opacity 0 → 1 plus scale 0.92 → 1 over **0.08 s (2–3 frames)**, power2.out. Hard swap between chunks. **No per-word SFX, no emoji, no shake** | Default for Reels/TikTok/Shorts. **Rising** (Blitzcut 2026) |
| C2 | **Karaoke line** (all words visible, active word lights up) | Inter Tight 800, 72–84 px, 3–5 words per line, 2 lines max. Upcoming words #8C837C (`--text-dim`), spoken words white, **active word #FF6A00 + glow 0 0 24px rgba(255,106,0,.55), scale 1.06** | Colour snaps on the word's start frame (1 frame). The scale eases 0.1 s. Line pages turn on sentence breaks | Screen demos and dense explanations, where context helps reading. Stable |
| C3 | **Moving active-word pill** | Base like C2 (white words). The active word sits in a pill: r 18, padding 6 × 18 px, gradient #FF9A4D → #FF6A00, text ink #1A0B04, 800 weight | The pill's x and width tween from word to word in **0.12 s power3.out**; it sits still on long words | **Rising** trend (pill and chip backgrounds). ⚠ The design system currently says "no boxes behind captions", so offer it as an opt-in style for Lloyd |
| C4 | **Size-hierarchy stack** ("lockup-lite") | Small words in Inter Tight 700, 48 px, white at 85%. The keyword in Inter Tight 900, **140–160 px**, tracking −0.045em, orange + glow, on its own line. 2–3 lines | Small words fade up 0.15 s (y +10). The keyword runs scale 0.8 → 1 with back.out(1.5) over 0.25 s, plus blur 10 → 0 | Hook lines and key claims only (about every 8–10 s); normal lines use C1 |
| C5 | **Script-accent caption** | C1 base, but **one emotional word** ("grabe", "finally", "sayang") set in Great Vibes **118–130 px**, colour #FF9A4D, rotated −4°, baseline overlapping the sans line by about 20% | The script word draws in (clip-path left → right, 0.3 s power2.out) while the sans words pop | Editorial mix trend (serif/script revival). At most 1 per 10 s |
| C6 | **Quiet lowercase / inner thought** | Inter Tight 500–600, **56–64 px**, all lowercase, 1 centred line. Colour white or warm cream #FFE2C7 (the brand-tuned version of the trend's butter yellow). Shadow stack only | **None**: hard cut by phrase | Vlog / back-cam calm moments and reflective asides. Rising in lifestyle; use rarely for tech |
| C7 | **Typewriter mono** | JetBrains Mono 600, **54–60 px**, white, keywords orange, 2 lines max, with a caret block ▍ in orange | Characters reveal so each word completes as it is spoken. The caret blinks only during pauses (finite). **Skip above about 140 wpm** (reads too slow) | Code, prompt and terminal segments; matches the toolkit's third font |
| C8 | **Hormozi classic** (reference only) | Anton or Montserrat Black, uppercase, 2 lines × 4–6 words, white with a highlight colour (yellow #F7C204, which we would swap for orange), heavy shadow or stroke, emoji between lines, a whoosh per word | Pop-in bottom → top per chunk | **Saturated / declining**: don't use as default. Also declining: per-word shake, 3+ colours per line, neon green/electric blue, static sentence blocks |

General rules from the sources:
- Use a bold sans (700–900) for the primary captions; never script or thin weights for the main line.
- Use one base colour plus one accent.
- Keep captions away from the right button column and the bottom UI.
- Animated karaoke can outrun slow readers, so keep chunks at 3 words or fewer when speech is fast.

---

## 5. Top 12 to build first (wow vs effort)

Wow and frequency are scored 1–5 (higher is better); effort is scored 1–5 (lower is easier). The ranking weighs wow and how often Lloyd's AI and tutorial videos would use the item against effort.

| Rank | Template | Wow | Effort | Uses / video | Why first |
|---|---|---|---|---|---|
| 1 | **Hand-drawn annotation kit** `scribble` (circle, underline, arrow, X, check, boil) | 4 | 1 | 3–6 | The most-taught Shorts graphic, works on both talking-head and screen, pure SVG plus DrawSVG |
| 2 | **UI target ring + click ripple** `target` / `click` | 3 | 1 | 4–10 | The core of every screen demo, and it replaces the banned spotlight-dim look |
| 3 | **Dynamic-Island alert** `island` | 4 | 2 | 1–2 | Top marketplace category, great hook interrupt, single-div morph |
| 4 | **Redaction reveal** `redact` | 4 | 1 | 1 | Built for curiosity and secret hooks plus re-hooks; trivial scaleX bars |
| 5 | **Keycap shortcut overlay** `keys` | 3 | 1 | 1–4 | Tutorial staple; tiny build |
| 6 | **Search bar + autocomplete** `search` | 3 | 1 | 1 | Question hooks and "what people search", reusing the typing code |
| 7 | **3D flip card (Myth / Fact)** `flip` | 4 | 1 | 1–2 | CSS 3D only; perfect for contrarian hooks |
| 8 | **Split-flap board** `flap` | 5 | 2 | 1 | High wow for reveals and Day-N series; mono font fits the brand |
| 9 | **Magnifier loupe** `loupe` | 5 | 3 | 1–3 | The signature move for tiny UI in vertical; HTML for stills, ffmpeg crop/scale/mask for live footage |
| 10 | **Click-driven auto-zoom** (B1, extends `zoomclip`) | 5 | 3 | whole demo | Screen-Studio look from plain recordings; needs a click logger plus automatic keyframes |
| 11 | **Tier list** `tier` (FS plus CB-mini) | 4 | 3 | 1 | Trend-verified (YouTube: 1B+ views H1 2025); reviews and rankings content |
| 12 | **Social post card** `post` (+ `thread`) | 3 | 2 | 1–3 | The Newsroom / AI-update staple: quote posts with a source pill |

**Next wave:** before/after slider `wipe`, receipt `receipt`, price slash `price`, floating 3D device frame (B2), polaroid stack, torn-paper reveal, investigation board, dock, step rail (B6), prompt → result split (B7).

**Trending but against Lloyd's rules:**
- Spotlight dim-the-rest.
- Frosted or blurred footage behind cards.
- Film grain, VHS or LUT looks on footage.
- Glitching the footage itself.
- "Brainrot" stacked gameplay.
- The full Hormozi caption package.

Keep any texture or glitch **on the graphic layer only**.

---

## Sources

**Trend roundups (2026)**
- https://www.opus.pro/blog/editing-aesthetics-dominating-short-form-2026
- https://www.mirra.my/en/blog/ai-motion-graphics-social-media-reels-shorts-2026
- https://www.capcut.com/help/latest-capcut-editing-trends
- https://graphicdesignjunction.com/2026/01/video-and-motion-creative-trends-2026/
- https://blog.videobolt.net/post/top-motion-graphics-trends-2026
- https://autoae.online/blog/motion-graphics-trends-2026
- https://www.tangence.com/blog/?p=1093
- https://rndr.beehiiv.com/p/5-visuals-next-video-6629
- https://docs.mosaic.so/tiles/motion-graphics.md
- https://blog.youtube/culture-and-trends/tier-list/
- https://techcrunch.com/2026/07/31/reddit-is-testing-a-new-way-to-watch-and-listen-to-its-viral-posts/
- https://www.kapwing.com/resources/how-to-make-tiktok-videos-from-reddit-stories/
- https://posteverywhere.ai/glossary/tiktok-green-screen
- https://ghostshorts.com/blog/how-to-make-split-screen-videos-for-tiktok-2026
- https://picsart.com/blog/moving-photos-trend-explained/
- https://www.croma.com/unboxed/instagram-edits-gets-new-ai-style-fonts-precise-controls-and-better-content-discovery
- https://onlinemarketing.de/social-media-marketing/edits-update-keyframes-reels-naechste-level

**Template marketplaces (what is being made and sold)**
- https://elements.envato.com/notification-dynamic-island-WHHR4XS
- https://elements.envato.com/reels-mobile-notification-HRYPGJN
- https://elements.envato.com/reels-message-bubble-chat-7CV9QP3
- https://elements.envato.com/liquid-glass-search-bar-XNESCNW
- https://elements.envato.com/top-10-history-vertical-video-DLPZX4W
- https://elements.envato.com/swipe-up-tap-arrows-ui-social-media-elements-inter-EKJ2UGR
- https://elements.envato.com/tweets-pack-6XV2RV6
- https://videohive.net/item/neumorphism-search-bar-text-typing-animation-after-effects-template/59429119
- https://videohive.net/item/liquid-glass-elements/61311144
- https://videohive.net/item/vertical-bold-before-and-after/60632633
- https://motionarray.com/stock-motion-graphics/pack-of-scribble-arrow-overlays-1845713/
- https://motionarray.com/stock-motion-graphics/lower-thirds/
- https://uppbeat.io/motion-graphics/asset/liquid-glass-ui-elements-9791
- https://designcompass.org/en/2025/07/30/liquid-glass-ae-template
- https://autoae.online/hooks/interactive-text-response-animation-b45hb1oe
- https://autoae.online/hooks/chatgpt-mockup-animation-with-2-text-elements-bxhna5hy
- https://aejuice.com/product/connection/
- https://twittershots.com/changelog/2026.8.30.14
- https://jitter.video/templates/before-and-after/
- https://www.capcut.com/explore/record-google-earth-zoom
- https://flexclip.com/learn/annotate-video.html

**Screen-demo tooling and technique**
- https://screen.studio/guide/auto-zoom
- https://daveswift.com/screen-studio/
- https://screenhance.com/blog/animated-app-demos-2026
- https://www.docsie.io/vs/screen-studio-vs-focusee/
- https://www.clueso.io/cluebooks/making-tasteful-screen-recording-videos--adding-visual-effects
- https://www.capcut.com/create/zoom-effects-for-tutorial-videos-guide-attention
- https://community.adobe.com/t5/premiere-pro-discussions/how-to-create-a-tutorial-that-can-highlight-a-part-of-screen-blur-the-rest-and-have-me-on-cam/m-p/15543331
- https://www.tella.com/help/editing/use-layouts
- https://www.upload-post.com/tools/safe-zone-checker/
- https://gsap.com/blog/3-13/

**Hooks and retention**
- https://www.opus.pro/blog/youtube-shorts-hook-formulas
- https://kineclip.com/blog/how-to-write-viral-hooks-short-form-2026/
- https://kineclip.com/blog/short-form-retention-benchmarks-2026/
- https://klap.app/blog/hook-examples
- https://www.argil.ai/blog/top-10-video-hooks-that-stop-the-scroll-in-2025-ai-hook-generator-tools-compared
- https://postlinkapp.com/blog/hook-examples-for-social-media-videos
- https://www.capcut.com/create/short-form-video-hooks
- https://spliceapp.com/blog/destination-arrival-hooks-short-form-videos/
- https://adamconnell.me/improve-video-retention-social-media/

**Captions and sound**
- https://blitzcutai.com/blog/tiktok-caption-trends-2026
- https://blitzcutai.com/blog/best-caption-style-tiktok
- https://www.submagic.co/ja/blog/how-to-make-alex-hormozi-captions
- https://care.submagic.co/en/category/fonts-captions-16gu1vw/
- https://shotstack.io/docs/guide/architecting-an-application/rich-captions/
- https://uppbeat.io/blog/sound-effects/sound-effects-youtubers-use
- https://www.epidemicsound.com/fr/sound-effects/categories/designed/riser/

*Caveat: Instagram, TikTok and X pages could not be opened without a login, so platform-native trend data (TikTok Creative Center and the like) is not included. Most quantitative claims above come from vendor blogs and are labelled as such. Verify any stat before using it on screen.*
