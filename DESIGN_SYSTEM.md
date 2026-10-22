# BBD Design System: Orange talking-head edits (v5 · Newsroom + v4 · Glass)

**Updated:** 2026-10-15 (v5: **Newsroom** style for AI-update/news videos — thumbnail hook, editorial pages, real source screenshots, cam bubble; see §14. v4: **glass** scenes, text behind the speaker, big captions, tutorial mock-UIs, face-break pacing — see §13; v3 rules below still apply). This is the **latest** design file. Use it for every new talking-head edit.

**Sources:**
- **`Inspiration video/`** (the JEV classification reel `9c248f….mov` and the 3-month roadmap `final-phone.mp4`). Every token below was measured from full-resolution frames of those two videos. See §0.
- Lloyd's "Design System: Joshua 'Orange' b-roll edits" (his other device). That is where the kinetic lockups, pop captions, motion specs and editing guardrails come from.
- The BBD system built here: orange brand, centred cards over blurred footage, the editor, and the MMS double-check.

**Precedence:**
- Where this file and `.claude/skills/bbd-video-edit/reference/*.md` disagree, **this file wins**.
- Where the Joshua original and Lloyd's later feedback disagree, **Lloyd's feedback wins**. Those cases are marked ⚑.

**Code that implements it:**
- `tools/mograph.py`: scenes and lockups.
- `tools/vedit.py`: cuts, `pop` captions, render.
- `tools/style.json`: tokens and defaults.

---

## 0. What the inspiration actually looks like (frame-by-frame review)
| Element | Measured in the inspiration | How we build it |
|---|---|---|
| Scene background | Warm near-black **#0C0908**. A big orange-brown glow top-right (centre ≈ 86% / 7%, **#572408** at the hot spot, spreading to #35150A across the top). A softer warm glow from the bottom-left corner (#3D1D08). A faint 44 px dot grid. | `.bg` + `.grain` in `mograph.py` |
| Layout | Content is **left-aligned at x = 48**, starting about y ≈ 470–590 and sitting in the upper-middle. The lower half stays empty for the caption. | `.content` top 400 / bottom 480 |
| Kicker | "◆ CUSTOMER EMAIL": an orange **diamond**, 36 px, 800, letter-spacing 0.2em, color #FF9A4D | `.kicker` |
| Headline | Inter 900, about 84 px, tight tracking, white, with one **orange word** ("JEV helps your automation *decide*") | `.title` + `*word*` |
| Cards | Fill **#1D1415**, 1.5 px warm-orange edge, 36 px radius. Rows inside one card are split by 1 px dividers. | `.card`, `.stack` (lists default to a stacked card) |
| Chips / buttons | **Orange gradient #FF9A4D → #FF6A00 with dark ink text #1A0B04** and an orange glow (Billing / Refund / Hot lead / Spam, "✓ Billing · 94% confident") | `.chip.on`, `.pill`, `.tag.on` |
| Muted state | Grey text #8C837C. Struck-out "old way" chips have an orange strike. | `.chip.no`, `.strike` |
| Big word / number | "JEV", "10,000", "2027": Inter 900, solid **#FF6A00** with a glow, auto-sized to the frame. Words are centred, numbers left-aligned with a kicker. Counters tick up. | `big` |
| Captions on scenes | Centred at **y ≈ 1610**, 1–2 words, white Inter 800 about 76 px, keyword orange, shadow only | `pop` captions, mode `low` |
| Captions on the face | About 60% down (y ≈ 1150–1190), 1–2 words | `pop`, `caption_y` |
| Lockups on the face | "Ipapakita ko / sa inyo *bakit* / kaya ng **JEV**", "So the real **skill** with JEV is not *just* using", "**3** months … **AI** automation *from* zero", "So **+ Follow** *me* for more · AI · Automation · App building" | `lockup` (`S:` `X:` `C:` `G:` `P:` tokens) |
| Progress bar | y 63–69, x 64 → 1016, 6 px. Warm-grey track, orange fill across the whole video. The roadmap video adds chapter ticks (OCT / NOV / DEC). | `progress_bar: true` |
| Transitions | Face → blur → scene. The scene content zooms in (scale 1.14 → 1, blur 18 → 0) while the footage behind it blurs, then reverses on exit. | mograph runtime + `vedit` dissolve |
| Recurring UI blocks | Confidence meters with %, multiple-choice cards (A/B/C/D, radio), Inbox → **Label** → Action node rows, 2×2 label tiles, checklists ("SYSTEM.md … documented"), approval cards (Reject / **Approve**), mind map with an orange core, agent loop, "DENIED" / "HINDI 'TO" stamps, chapter cards (MONTH 1 · PART 2 / **OCTOBER** / *Map the system*) | `meter`, `choice`, `flow`, `list`, `chapter`, `stamp` (§5) |
| Half panel (roadmap video) | A dark panel from y ≈ 1000 with a rounded top. The face stays visible above it, and the caption sits on the panel's top edge. | ⚑ Only when the chin is above y ≈ 950 (see §2) |

## 1. Principles
1. **The footage stays natural.** No grade, LUT, vignette, grain or darkening scrim on the camera. Readability comes from text shadows and solid panels.
   - `style.json` → `grade.enabled: false`.
   - Older projects keep `"grade": true` in their decisions.json so re-renders look the same as delivered.
2. **Something changes every 2–4 seconds.** B-roll is animated mock-UI scenes built in HTML (HyperFrames). No stock footage or AI clips unless Lloyd asks.
3. **Every visual is tied to a spoken word.** A scene enters when the idea starts, and each element pops on the word that names it.
4. **One accent: orange.** Everything else is warm near-black, white, and warm greys. No blue or cyan accents.
5. **Every word is complete, and no word is said twice.** A clipped word or doubled phrase ruins the edit more than any visual can save it (§9).
6. ⚑ **Never cover the face.** Lloyd rejected a half-screen panel that blocked his face. Graphics are full scenes, cards centred over **blurred** footage, or lockups and compact cards **under** the face.

## 2. Canvas and safe zones (1080 × 1920, 30 fps, H.264 + AAC)
| Item | Value |
|---|---|
| Face zone (never cover in talking-head mode) | y 230–865 px (12–45%) in the Joshua framing. ⚑ **Check each video**: in Lloyd's framing the chin can sit at y ≈ 1100–1150. |
| Caption zone (talking head) | Top of caption at **y 1150** (~60%). Override per video with `"caption_y"` in decisions.json (1920-scale px) when the chin is lower. |
| Lockup zone (talking head) | y 1135–1655 |
| Top band | Progress bar at y 64, labels below it |
| Side margin | 64 px |
| Bottom UI danger zone (Reels/TikTok) | Below y ≈ 1700. Keep content out of it. |

### Screen modes
| Mode | `mograph` layout | What covers the camera | Captions |
|---|---|---|---|
| Talking head | no overlay | Nothing | y 1150 (`pop`) |
| Kinetic lockup | `"type": "lockup"` | Nothing (words only, transparent) | Hidden while it is up |
| Full scene | default | An opaque scene over the whole frame | Low, y ≈ 1603 |
| Centred card ⚑ | `"layout": "panel"` | A centred card; footage behind it is blurred and dimmed | Low |
| Compact card under the face ⚑ | `"layout": "lower"` | Small cards from y ≈ 1170 down | Top band |
| Side callout (vlog / back-cam demos) | `"type": "tag", "mini": true, "side": "left"\|"right", "y": 200` | A small card at the edge (icon + kicker + one line, or step chips) over the browser chrome / above the head; slides in from its side | Unchanged |
| Half panel (Joshua) | not used | A panel from y 1000 to the bottom | Use only if the chin is above y ≈ 950 in that video |

## 3. Color tokens
| Token | Value | Use |
|---|---|---|
| `--accent` | **#FF6A00** (measured in the inspiration: JEV #F26207, chips #F1640C → #F89053). This replaces the older #FF6B35. | Keywords, badges, progress bar, strikes, icons, hot chips |
| `--accent-hi` | #FF9A4D | Gradient tops, kicker text, tag text |
| `--glow` | rgba(255,106,0,.55) | Glows behind badges and keywords |
| `--text` | #FFFFFF | Captions and headings |
| `--text-2` | #D9D2CC | Secondary lines and descriptions |
| `--text-dim` | #8C837C | Lockup words not yet spoken, disabled rows |
| `--ink` | #120D0A | Text on orange fills |
| Scene background | **#0C0908** + radial orange-brown glows (top-right, bottom-left) + 44 px dot grid at 9% white (§0). The old navy background is retired. | All full scenes |
| Card fill | **#1D1415** (rgba(29,21,19,.94)) + 1.5 px rgba(255,140,60,.30), radius 36 | `.card`, `.stack` |
| Ink | #1A0B04 | Text and icons on orange fills |
| Hot card | rgba(255,106,0,.10) + 1.5 px #FF6A00 + 0 0 50px glow | Highlighted row or card (`on`) |

**Gradients:**
- Orange fills run #FF9A4D → #FF6A00 (→ #C24700 for 3D icons).
- Never put a full-screen linear gradient on a dark background; it bands in H.264. Use a solid fill plus a radial glow instead.

## 4. Typography
| Font | Role | Files |
|---|---|---|
| **Inter Tight** 500–900 (the Joshua spec says Inter; Inter Tight is the same design, narrower, and Lloyd approved it) | Everything except script accents | `assets/fonts/` (libass captions), `motion/fonts/` (HyperFrames `@font-face`, preloaded) |
| **Great Vibes** 400 | Script accents only | `GreatVibes.ttf` in both folders |

Never rely on Google Fonts at render time; it silently falls back to Times.

### Type scale
| Role | Spec |
|---|---|
| Caption pop (talking head) | 800, 72 px / 1.1, tracking −0.015em |
| Caption pop (full scene / card) | 800, 64 px |
| Lockup keyword `X` | 900, 150 px / 0.86, tracking −0.045em, orange + glow. Long words auto-shrink to 110 px, then the whole row scales to fit 930 px. |
| Lockup medium `M` | 800, 70 px / 1.05 |
| Lockup small stacked `S` | 700, 40 px / 1.02 |
| Lockup script `C` | Great Vibes 118 px |
| Lockup tag `G` | 700, 30 px, orange pill |
| Scene headline | 800–900, 92–96 px (76–80 for long lines) |
| Scene subhead | 800, 60 px (36–50 inside cards) |
| Kicker | 800, 30 px, uppercase, tracking 0.16em, orange dot or diamond bullet |
| Body | 600, 36 px / 1.25, `--text-2` |
| Big number | 900, 240–330 px, orange, tabular numbers |

**Rules:**
- Every caption and lockup word gets the shadow `0 0 2px rgba(0,0,0,.85), 0 2px 5px rgba(0,0,0,.6), 0 6px 26px rgba(0,0,0,.55)`. **No boxes or strokes behind captions.**
- Keywords (decisions.json `keywords`) turn orange. Use about 30 per video at most.
- Minimum sizes: 60 px+ for headlines, 26 px+ for body, 22 px+ for labels.
- Numbers are tabular. No emoji in rendered text.

## 5. Components

### Captions: `"caption_style": "pop"` (the default for new videos)
- One or two words per group, ≤14 characters. A group breaks on punctuation, on gaps over 0.25 s, and when the screen mode changes.
- Entrance: 0.16 s fade with scale 0.84 → 1. Exit: a hard cut when the next group starts.
- White Inter Tight ExtraBold with the soft shadow above. Keywords are orange at the same size.
- Captions follow what was said (`fixes` correct the spelling only).
- Older styles still work: `"punch"` (1–3 words, bigger orange keyword) and classic.

### Kinetic lockups: `"type": "lockup"` in scenes.json
These are the "That **confidence** score is *important*" and "Ipapakita ko sa inyo *bakit* kaya ng **JEV**" looks.
- Use them only in talking-head mode, for the **hook, the key claim and the CTA** (2–4 per video). Never use one while a scene is up.
- The words build one by one, from dim to white. The keyword and script pop in on their own word (back.out(1.5), scale 0.72 → 1, blur 14 → 0, 0.38 s).
- The lockup clears in 0.18 s (y −14, blur 6). Captions are hidden while it is up.

```json
{"id": "lk_hook", "type": "lockup", "start": "That confidence", "until": "important",
 "rows": ["That X:confidence", "S:score/is C:important"]}
{"id": "lk_claim", "type": "lockup", "start": "Ipapakita ko", "until": "JEV",
 "rows": [["M:Ipapakita ko", "C:bakit"], ["S:sa inyo/kaya ng", "X:JEV"]]}
```

**Row tokens:**

| Token | Meaning |
|---|---|
| `word` or `M:word` | Medium |
| `X:word` | Orange keyword; `X120:word` forces 120 px |
| `C:word` | Script |
| `S:line one/line two` | Small stacked lines |
| `G:text` | Orange tag pill |
| `<` (first token) | Align the row left |
| `_` | A space inside a token in the string form (`M:sa_inyo`) |
| `@phrase` | Times the token on other words (`X:AI@artificial`) |

A row can be a string split on spaces or a list (list items may contain spaces).

### Scene containers
| Container | In | Out |
|---|---|---|
| Full scene | 0.34 s, content scale 1.14 → 1, blur 18 → 0, expo.out; the scene layer dissolves in over 0.22 s while the footage blurs (`vedit`) | 0.22 s, scale 0.94, blur 14, power2.in + 0.2 s dissolve |
| Centred card ⚑ | Fades in 0.2 s over blurred and dimmed footage | Fades out 0.2 s |

**Chapter card** (`"type": "chapter"`): MONTH 1 · PART 2 / **OCTOBER** (≤168 px) / *Map the system*. Use one per major section in long-form. The flash and camera whip are not built yet.

### Building blocks (mograph `type` ↔ Joshua class)
| mograph type | Joshua building block | Use for |
|---|---|---|
| `list` | `.win` + `.li`, `.ladder` + `.rung` | Steps, examples, questions |
| `chips` | `.chip` / `.chip.hot` / `.chip.no` | Sets of things (tools, fields) |
| `pipeline` | `.flow` + `.fnode` + `.wire` | Trigger → action sequences |
| `big` | `.big`, `.ctr` | One number or word (counts up) |
| `versus` | `.card` vs `.card.hot`, `.strike`, `.stamp` | Wrong vs right |
| `statement` | headline + `.sc` | A quotable line |
| `chat` | `.bub.me` / `.bub.ai` / `.typing` | Conversations |
| `email`, `notify`, `excel`, `map`, `loading`, `error` | `.win`, `.tile`, `.apptile` | Concrete UI examples |
| `cta` (`layout: "lower"` keeps the face) | `.card.hot` + tag | Comment keyword + follow |
| `lockup` | `lockup()` rows | Hook, key claim, CTA over the face |
| `meter` | confidence bars | "Billing 94% / Technical 4% / Sales 2%" + verdict pill; `before` = struck-out old way |
| `choice` | multiple choice | "Anong label nito?" A–D options, `pick` + `pick_at` lights the answer, the rest dim |
| `flow` | `.flow` + `.fnode` + `.wire` (horizontal) | Inbox → **Label** → Action (`hot` or `on` node), optional `items` list card underneath |
| `chapter` | chapter card | `step` "MONTH 1 · PART 2", `mo` "OCTOBER", `what` script "Map the system" |
| any scene + `"stamp": {"t", "at"}` | `.stamp` | "DENIED", "HINDI 'TO" slammed over the last element |

Lists render as **one stacked card with dividers** (inspiration look). Set `"separate": true` for individual row cards. Rows accept `"r": "documented"` (right text) or `"rtag": "Billing"` (orange tag).
Lockup tokens also include `P:text` (small dark pill: "AI", "Automation", "App building").

| `mindmap` | `.map` + `.mcore` + `.mnode` | `core`, `core_at`, `nodes[{t, icon, at, on}]` (≤6) around an orange core, lines draw in |
| `loop` | `.loopwrap` + `.lnode` | `steps[{t, at, on}]` around a circle whose orange arc fills; `core` label |
| `tiles` | 2×2 label tiles + wide button | `tiles[{t, icon, at, on}]`, `button{t, icon, at}` ("Safe for the AI agent") |
| `approval` | approval card | `head`, `tag`, `line`, `right`, `approve_at` lights **Approve**, `note{t, at}` pill |

Scenes always chain: a scene never starts before the previous one ends (mograph clamps it).

## 6. Motion
| Use | Ease | Duration |
|---|---|---|
| Element entrance (rise) | expo.out / power3.out, blur 10 → 0, y +40–50 | 0.42–0.5 s |
| Row or list entrance | power3.out, x −36 to −70 | 0.36–0.45 s |
| Pop, chip or badge | back.out(2) (range 1.6–2.5) | 0.35–0.5 s |
| Stamp slam | power4.in, scale 2.2 → 1, rotate −8° | 0.28 s |
| Strike or bar grow | power2.out / power3.out | 0.25 s / 0.6 s |
| Lockup keyword | back.out(1.5), scale 0.72 → 1, blur 14 → 0 | 0.38 s |
| Lockup clear | power2.in, y −14, blur 6 | 0.18 s |
| Camera punch-ins | Hard cuts between scale 1.00 and 1.10 on jump cuts (`punch_in` in decisions) | none |
| Flash | Radial orange, screen blend, up to 0.85 | 0.06 s in, 0.32 s out |

**Rules:**
- Animate only transforms, opacity, filter, colors and clip-path.
- Everything is deterministic: no `Math.random()`, no `repeat: -1`.
- Typing uses stepped clip-path. Counters swap stacked spans.
- No bouncy easing on text and no spinning text. `bounce.out` is only for small objects landing.

## 7. B-roll density and pacing
⚑ This section merges the Joshua rules with Lloyd's feedback ("why so much graphics" on the 2-minute video).

**Coverage:**
- **Reels and short clips (≤3 min):** at most about 50–60%. Lloyd said video 2 had too many graphics.
- **Long-form:** about 60–80%. The Joshua original runs 85–90%; use that only when Lloyd asks for "full b-roll".
- Leave the hook, key claims, jokes, personal asides and the CTA on his face, with a lockup.

**Inside a scene:** a new element every 0.5–1.5 s, each landing on its spoken word.

**Scene length:** 1.5 s minimum, and about 10 s before the content inside changes. Scenes over 25 s get split.

**One cluster at a time:** never a lockup and a scene together, and never two scenes overlapping.

**Cues are spoken phrases, not times.** Phrases are matched on the edited timeline, in order. After every transcript change, check the mograph ⚠ "skipped" warnings; one bad cue shifts everything after it. The editor retimes graphics automatically.

**Audio consistency.** The phone's noise gate turns pauses into digital silence (−100 dB), so the background "switches off" between words. `vedit render` lays the video's own room tone (the longest clean 0.6–3 s stretch, looped seamlessly) under the voice at its natural level before loudnorm, so every cut and gap sounds the same. Turn it off with `"room_tone": false`.

## 8. Sound design (planned, not yet in the pipeline: there is no SFX library in `assets/`)
| Sound | When | Volume |
|---|---|---|
| whoosh | Every scene entrance | 0.32 (cards) – 0.4 (full) |
| pop | Chips, cards, stats appearing | 0.35–0.45 |
| tick | List rows, checkmarks, counter steps | 0.3–0.45 |
| ding | A positive resolution ("gumagana", "malinaw") | 0.25–0.35 |
| impact | Stamps, chapter cards, big reveals | 0.35–0.5 |
| riser | 0.6 s before a chapter card or big reveal | 0.35–0.4 |
| buzz | Wrong, crossed out, "mahal", bottleneck | 0.35–0.4 |
| typing | Typewriter text in chat bubbles | 0.22 |

The voice is normalized to −14 LUFS. SFX always sit under the voice, and none goes above 0.5.

## 9. Editing guardrails (the cut)
These were learned the hard way on both systems: round after round of fixes for doubled and clipped words.
1. **Ask for the script when there is one.** Each line uses its last complete take.
2. **Never trust Whisper to find doubles.** It silently merges repeated phrases. Run `tools/literal.py` (Meta MMS, letter-by-letter, keeps doubles) and `tools/audit.py` (8–10 s windows of the finished edit) after every plan change, and read both.
2b. **Find hidden retakes before cutting.** Run `tools/literal.py VIDEO --raw` and `tools/listen.py VIDEO 0-12 11-23 … --mms` over the whole raw video (12 s windows). Whisper often stretches one word over a whole retake ("kasama" = 7 s, "lang" = 2.3 s), so compare its words with the MMS words and the energy strip. Then patch the kept take's word timings in `transcript.json` (`"patched": true`) and `cut_ranges` the hidden attempt.
3. **Never cut on Whisper word timestamps alone.** On iPhone footage they run up to 0.5 s late; for example, "final, final" was off by about 0.2 s. Cut points sit in real silence (a run of ≥0.12 s below −45 dB), never on a single dip, because words like "bi|da" dip inside themselves. `vedit plan` splice smoothing does this, and `tools/soundcheck.py` flags splices with speech at the edge.
4. **The phone's noise gate** turns pauses into −100 dB and chops words: "Da · pat", "Pa · ngatlo", "sa · vibe coding", "dala" each arrive as a short blip, 0.1–0.4 s of gate silence, then the rest. Lloyd hears that as "putol". `vedit plan` handles it automatically:
   - **Closes gate holes** around isolated blips (≤0.2 s) on the edited timeline, down to a few frames.
   - **Pulls clip edges** out to a gate-split blip, but never into removed words or `cut_ranges`.
   - Smoothing never moves a clip start later or an end earlier, into a word.
   - **Dead air vs soft speech:** a flat −42…−47 dB stretch is the room heard through an open gate. It is dead air (rolling std < 2.5 dB). Short soft runs (≤0.25 s) touching speech are kept as syllables. Lone 10 ms spikes are ignored.
   - When the gate ate a syllable in the raw take (e.g. take 2's "Pa" at −47 dB), use the take where it is intact ("Pangatlo" from take 1). If no take has it, flag it for a re-record. Widen outward, never inward. Drop a fragment with no transcribed word only if its peak is below −28 dB.
5. **Pauses:** ⚑ Lloyd 2026-10-20 ("di malinis yung pagkakakat"): trimming every 0.33 s pause made dozens of 0.1–0.3 s micro jump cuts inside sentences. Talking heads now use `"tuning": {"max_pause": 0.55, "keep_pause": 0.28}` + `"punch_flip_gap": 0.18` (the punch-in flips on every real cut) and no kept piece under ~0.6 s unless it is a whole line. Older rule: trim any pause of 0.33 s or more, keeping 0.10 s after a word and 0.08 s before the next. A join between two takes keeps at most about 0.2 s of air. For new videos, set `"tuning": {"max_pause": 0.33, "keep_pause": 0.18}`. Long-form still removes only dead air, fillers, retakes and false starts, never content.
6. **Splices:** before keeping a sentence assembled from pieces, listen to it. If it reads wrong, don't use it.
7. **Hand decisions** go in decisions.json (`remove`, `cut_ranges`, `keep_ranges`, `fixes`) with a reason for each one.
8. When the recording differs from the script, caption what was said and tell Lloyd. Never splice in a word from a different sentence.
9. Words clipped in the raw recording can't be repaired. Flag them and offer a re-record.

## 10. Workflow (per video)
```
./vedit transcribe input/NAME.mov            → transcript + energy
(editorial pass) work/NAME/decisions.json    → removes, cuts, fixes, keywords, tuning, caption_style "pop"
./vedit plan input/NAME.mov                  → edl.json + review.md
.venv/bin/python tools/literal.py   input/NAME.mov   → doubles and fragments (MMS)
.venv/bin/python tools/audit.py     input/NAME.mov   → windowed re-listen
.venv/bin/python tools/soundcheck.py input/NAME.mov  → splices with speech at the edge
(write) work/NAME/scenes.json                → scenes + 2–4 lockups
.venv/bin/python tools/mograph.py input/NAME.mov     → renders motion/renders/*, registers overlays
./vedit render input/NAME.mov                → 720p preview → Lloyd reviews (editor: http://localhost:8765)
./vedit render input/NAME.mov --final        → output/NAME_FINAL.mp4 + .srt
```
To preview a single scene or lockup without rendering, start the `motion` preview server (launch.json, port 8777) and open `motion/scenes/<id>.html`.

**After every plan:** run `tools/literal.py` + `tools/wordcheck.py` (planned script vs what MMS actually hears → missing or clipped words) + `tools/soundcheck.py`. wordcheck lists many spelling-only mismatches; look at the lines where the literal model heard "—" or a clearly different word.

## 11. Pre-render checklist
- [ ] literal.txt and audit.txt read: no doubles, no clipped first or last syllables
- [ ] soundcheck: no splice with speech at the edge (except natural onsets)
- [ ] Dead-air scan: no pause of 0.33 s or more left
- [ ] mograph printed no ⚠ skipped scenes
- [ ] Every scene checked at its hero frame: no overflow, no orange-on-orange text, nothing on the face in talking-head mode
- [ ] Lockups: 2–4, none overlapping a scene, rows fit (auto-fit is on)
- [ ] Captions sit below the chin in this video (`caption_y` if needed)

## 12. Don'ts
- No grade, vignette, grain or darkening scrim on the footage (unless decisions say `"grade": true`)
- No blue or cyan accents; orange only
- No emoji in rendered text
- No full-screen linear gradients
- No `Math.random()`, `repeat: -1`, or animating visibility
- No lockup while a scene is up, and no two scenes at once
- ⚑ No graphic covering the face: no half panels over the face, and no boxes behind captions
- No cut point placed on a Whisper timestamp alone

## 13. v4 · Glass short-form tutorials (Lloyd, 2026-10-14)
Lloyd's brief for the 3-video batch (Claude Code + HyperFrames, 30-day roadmap, Pixel Agents): *short form, top-level, "magwala ka"*. Hook and CTA on his face with effects; the body is mostly visuals (step-by-step) with **2–3 face breaks of ~3 s**; smoother **glass** transitions in brand orange; **text behind him**; **big captions with orange keywords**; motion graphics only (no b-roll).

### Structure (per video)
| Part | Screen | What is on it |
|---|---|---|
| Hook (first 3–7 s) | Face | Giant word **behind** him (`behind`) + a lockup on the hook line |
| Body | Glass scenes, chained | One scene per step; `chapter` card per step/week ("STEP 2 · OF 5 / INSTALL / *Pixel Agents*") |
| Face breaks | Face, captions only | 2–3 × ~3–5 s, on a line that is a personal aside or "why" ("Ang goal mo rito…", "Pag may preview na…") |
| CTA | Face | Lockup on the ask → giant comment keyword **behind** him ("MOTION", "CODE30", "PIXEL") → "+ Follow" lockup |

### Glass scenes — `"mograph_theme": "glass"` in decisions.json
- The scene renders **with alpha**; `vedit` lays the footage underneath, blurred (σ ≈ H/34 at quarter size), with an **even neutral dim (×0.8)**. ⚑ Lloyd 2026-10-20: the old warm/desaturated grade (`eq` −0.07 / sat 0.78 + warm colorbalance) looked like a filter on his face, so hue and saturation now stay as shot (`"glass_grade": "warm"` restores the old look). The face keeps moving behind frosted glass.
- Cards are **glass panes**: white 17%→2.5% diagonal fill, 1.5 px white-17% edge, top highlight `inset 0 1.5px rgba(255,255,255,.30)`, deep shadow, `backdrop-filter: blur(28px)`. Hot state = orange edge + tint (unchanged). Chips/pills: orange gradient + ink.
- Content is 13% bigger than v3 (`zoom: 1.13`), area y 300–1520. Captions on scenes stay low (y ≈ 1603).
- **Transitions:** face → glass = 0.35 s dissolve of the frosted layer + scene; content materialises (scale 1.07→1, y +26, blur 22→0, 0.55 s expo.out) while a warm light **sheen** sweeps across (1.0 s). Glass → glass = the frosted background stays (one continuous span), only content swaps (out: 0.3 s scale .965, blur 16). No flash of sharp face between scenes.
- Consecutive glass scenes chain with no gap (mograph floor = previous end; vedit pads the tiny remainder).

### Text behind the speaker — `"type": "behind"`
- `{"type": "behind", "start": "…", "end": "…", "text": "MOTION", "y": 300, "size": 360, "kicker": "Comment", "style": ""|"w"|"o"}`.
- Inter Tight 900, uppercase, orange gradient (#FFB27A→#FF6A00→#E05500) with soft glow; letters rise out of blur (stagger), slow 5% push, clear in 0.3 s.
- `vedit render` cuts him out with **Apple Vision person segmentation** (`tools/bin/personmask`, built from `tools/personmask.swift`, no downloads) on the rendered frames and puts him back on top: text → behind hair/shoulders. Captions stay visible.
- Place the word's top at y ≈ 300–330 so the **head overlaps the lower half** of the letters (check the head top in that video: Lloyd's head top ≈ y 380–450). Behind scenes don't chain with lockups — a lockup can run on top.

### Captions
- `"caption_size": 110` (1920-scale) for short-form — big, 1–2 words, keyword orange. Lockups hide captions (also when a `behind` word is up).

### New mock-UI templates (tutorials)
| type | Use | Key fields |
|---|---|---|
| `terminal` | Claude Code / app window, typed prompt with caret, outputs, code | `wtitle`, `lines[{k: prompt/out/ok/code/dim, t, at}]`, `tabs` + `tab_on` + `tab_at` ("Chat · Cowork · **Code**"), `swatches[{c, t, at}]` |
| `phone` | Preview / storyboard in a phone | `headline`, `items[{t, icon, at, on}]` joined by an orange wire, `name` (script), `cta`, `controls` (play + scrubber), `button{t, icon, at}` |
| `export` | Render progress → file ready | `file`, `s`, `at`, `done_at`, `file_at` (counter 0→100%) |
| `upload` | Drop zone, files drop in | `label`, `files[{t, s, icon, at}]` |
| `duo` | Two tools joined by "+" | `tiles[{t, s, icon, at, on}]` |
| `office` | Pixel Agents office: pixel sprites walk in, sit, type (monitor lines + bubble) | `agents[{name, color, desk, at, type_at, task}]`, `desks`, `live` |
| `behind` | Giant word behind him | see above |
| `chapter` | Step/week divider (word auto-fits) | `step`, `mo`, `what`, `what_at` |

### Checks added
- `tools/hear.py OUTPUT START-END …` listens to the **rendered** preview (Whisper + MMS) — run it over every join before sending.
- `tools/listen.py` handles the last window of a file.

## 14. v5 · Newsroom — AI updates / news (Lloyd, 2026-10-15)
Brief (A1–A4 batch): "pakitaan mo ako ng ibang design… ayoko pare-parehas"; first 3 s = **thumbnail hook** (text that doubles as the thumbnail); many motion graphics showing what he explains; **real proof** — screenshots of the source pages with the **source named on screen**.

### Look
- `"mograph_theme": "news"` (+ `"news_date"`, `"news_section"` for the masthead). Pages are **opaque charcoal editorial pages** (#151311, faint scan lines, soft orange corner glows) — not glass.
- **Masthead** on every page: `AI UPDATE · SECTION ………… DATE` with an orange rule (y 118).
- Headlines in **Playfair Display 800** (serif, editorial) with an **orange highlighter** behind the key phrase (`*word*`); body/UI in Inter Tight; data in JetBrains Mono.
- Cards: solid #1E1B19, 20 px radius, **6 px orange left rule** (newspaper sidebar feel).
- **Source pill** bottom-left on every news page (`"source": {"name", "date"}`); illustrations say `Illustration`.
- **Cam bubble**: his face rides along in a Ø300 orange-ringed circle bottom-right with a `● LIVE` tab (vedit crops `"cam": {"cx","cy","size"}` from the footage, default 540/780/760). The face is never lost even on full pages.

### Motion
- **Orange slab wipe** (300 px, with a charcoal stripe) sweeps right→left to bring a page in (0.55 s, power3.inOut) and back to reveal the face at the end of a chain. Chained pages wipe over the frozen previous page.
- Content slides in from the right (x +70, 0.5 s expo.out); source pill rises after.
- Highlighter sweeps across the marked phrase on its word; screenshots get a slow push then a jump-zoom to the focus area.

### Thumbnail hook — `"type": "thumb"` (first ~3–4 s, on the face)
`{"type":"thumb","start":"What if","until":"…","tag":"AI Update","rows":["AI na ang","kausap ng","H:scammers"],"sizes":[170,170,200]}` — Inter Tight 900 uppercase, rows slam in (scale 1.45→1, small shake), `H:` = orange gradient box with ink text, `O:` = orange text. Placed over the chest (bottom 230). Captions hide. **Frame ~2 s is the thumbnail.**

### Templates
| type | Use |
|---|---|
| `thumb` | thumbnail hook |
| `article` | browser card: `img` (screenshot in motion/clips) + `focus{at,z,x,y}` + `box`, or rebuilt `outlet/headline/by` with `*mark*` |
| `stat` | big number (counts up, auto-fits) + unit + context |
| `chat` (with `meta` labels) | scammer vs AI, examples |
| `flow`, `list`, `chips`, `versus`, `pipeline`, `terminal`, `phone`, `tiles` | explanations (restyled by the theme) |

### Sources (rules)
- Find the story first (WebSearch), verify the numbers, and **flag claims that the sources don't support** to Lloyd (e.g. "17 years wasted", HeyGen scene-image) instead of citing a source for them.
- Ask Lloyd before capturing screenshots. Capture with the headless Chrome HyperFrames uses (`--screenshot`, 1080×1500, no user-agent spoofing). Sites that block bots (403 / "verifying") get a rebuilt article card with the outlet + date instead — never try to bypass the block.

## 15. Short-form SAFE ZONE (Reels · TikTok · Shorts · FB) — mandatory (Lloyd, 2026-10-15)
Canvas 1080 × 1920. Platform UI covers: the **top** (headers "Reels", "Following | For You", camera), the **right column** (like / comment / share / audio), and the **bottom** (username, caption, music). Nothing important may sit there.

| Zone | Keep out of | Our layout |
|---|---|---|
| Top | y < 220 | news masthead at y 236; progress bar at y 63 is decorative only |
| Bottom | y > 1480 | captions on pages centred at y 1420 (`low` = 0.74 H); talking-head captions top at `caption_y` 1250–1290; thumb + lockups end by y 1460 |
| Right | x > 936 (y 700–1480) | content `left 64 / right 144`; thumb & lockup rows fit 860 px; cam bubble moved to the **left** (x 64, y 1100, Ø250) |
| Left | x < 64 | 64 px margin |

Check with `motion/scenes/_gallery.html?…&guides=1` (red = unsafe).

## 16. Sound design — `tools/sfx.py` (replaces §8 "planned")
- All sounds are **synthesized** (numpy/scipy) — no library, no licensing: whoosh (page wipe in / out), **riser** (builds through the hook, 3.6 s max, lands on the first page reveal with a **boom**), hit / boom (thumbnail rows slam), pop (cards / chips / nodes / lockup keywords), tick × n + ding (counters), typing (terminal), shutter (screenshot jump-zoom), swish (highlighter, chained page swap, lockup in).
- Cues are read from the rendered scene HTML (`data-at`, `data-anim`, `data-tat`, `data-mark`, `data-kb`, `data-win/wout`), thinned so light sounds are ≥ 0.28 s apart, mixed into `work/<name>/sfx.wav`, and `vedit render` mixes it under the voice **before** loudnorm (`"sfx_level"`, default 1.0; `"sfx": false` turns it off).
- Order: `mograph.py` → `sfx.py` → `vedit render` (the editor's Render does all three).

## 17. Revisions after Lloyd's review (2026-10-15)
- **Hook text never on the face.** The thumbnail hook is a `behind` scene: a big white **kicker line above the head** (`"kicker_big": true`, auto-fit ≤ 940 px, top ≥ y 220) + the **giant orange word behind him** (Inter Tight 900 gradient, y ≈ 350, fit 960 px), cut out with personmask. It starts at frame 0 so frame ~2 s works as the thumbnail. (`thumb` type stays available but is not the default.)
- **Typography = v3/v4** on every theme: Inter Tight 900 titles with an **orange keyword** (no serif / no highlighter), Inter Tight kickers with the diamond, Inter Tight masthead + source pill.
- **SFX = clean, minimal, varied** (`sfx.py --style clean`, default): five swooshes rotate — `sw_deep`/`sw_air` on page wipes in, `sw_whip`/`sw_shimmer`/`sw_air` on chained page swaps, `sw_whip` on lockups, `sw_shimmer` on the hook, `sw_reverse` on page wipes out. No pops / ticks / booms / hits.
- **Suspense riser** (heartbeat sub that speeds up + dark rising air + a rising minor-second pad, soft hand-off) from ~3 s before the first page reveal.
- **Hook zoom**: footage pops out 1.12 → 1.0 in the first 0.6 s, then eases in 1.0 → 1.13 while the riser builds (vedit `hook_zoom`, written by sfx.py; zoompan on a 2× canvas so it doesn't jitter).
- **Round 3 (same day):** no face bubble on pages (`"cam_bubble": false` default — Lloyd doesn't want to see his face there); pages use the freed space (content y 330–1160, source pill bottom-left at y 1214). **Transitions are smooth**: page in = blur 26→0 + scale 1.06→1 + fade (0.6 s, power2.out); chained pages crossfade (0.35 s) while content rises out of blur; page out = fade + blur + scale 1.04 (0.5 s). No slab wipe. **Great Vibes is back**: the hook's kicker is a Great Vibes line riding on the top edge of the big word (`"kicker_script": true`, word top y ≈ 285 so it reads in the thumbnail), plus script accent lines on 2 pages per video and a script word in the "+ Follow" lockup.

## 18. v6 · Light / On-screen tags (2026-10-16, "AI agents" screen-demo video)
For simple edits where Lloyd says "hindi kailangan fancy, wag haharangan yung video": the A-roll stays full-screen, graphics sit **on** it (not b-roll pages).
- **`tag` scene** (`mograph.py`, panel class `otag`, overlay kind `tag`): small dark-glass card at the top of the safe zone (x 64, y 236): orange kicker · big name (`*orange*` word) · mono role line typed in on `role_at`; `color` = pixel-agent avatar (always brand orange `#FF6A00` — Lloyd: "follow my color branding, the orange"; no per-agent colours), or `icon` = orange tile; card + chips have an orange `#FF6A00` border, orange kicker; optional `steps[{t, at}]` chips that pop + light up (demo flows). Slides in from the left out of blur, fades up out. No blur/dim on the footage; captions stay on. SFX: one soft `sw_air`/`sw_shimmer` per tag (`sfx.py --no-riser`).
- **Captions**: `pop`, `caption_size` 104, `caption_y` 1390 on screen footage. **`caption_zones`** (decisions.json, original seconds) move captions per section — talking-head parts where the face fills the frame go on the wall above the head (`y` 240). Tags and top captions never share a section.
- Combining several takes into one video: normalise with ffmpeg to 1080×1920 30 fps first (`input/<name>.mov`), then run the normal pipeline on the combined file.
- **iPhone HDR footage (HLG + Dolby Vision) → SDR with Apple's own tone mapping, before editing: `tools/bin/tosdr IN.MOV OUT.mov`** (AVFoundation, the same conversion Photos uses for "Most Compatible"; ProRes 422 HQ, original frame timing; build: `swiftc -O -sdk <MacOSX26.x.sdk> tools/tosdr.swift -o tools/bin/tosdr`). Lloyd 2026-10-20: the HLG render "may HDR… wala na yung natural na kulay" — an 8-bit H.264 HLG file without the Dolby Vision metadata plays as HDR and looks different from the camera, even though its pixels match. Never use ffmpeg zscale/tonemap on his footage either (2026-10-16: "looked like colour grading"). Check: `tosdr --frame IN.MOV <sec> ref.png` is Apple's rendering of the original; the SDR source should match it within ~1–2 % (editor_story: MAE ≈ 3/255). Several clips: tosdr each one, then join them with a video+audio concat (each clip's video locked to its own audio; a video-only concat with per-clip `fps=30` drifts 2–3 frames). With an SDR source vedit composites normally and tags the output Rec.709. The old HLG path (graphics through `assets/sdr_to_hlg.cube`, captions through `tools/hdr.py`, output re-tagged HLG) still runs if an HLG file is fed in.

## 19. Pre-webinar demo additions (Lloyd, 2026-10-19 · `roadmap30`)
Brief: motion graphics everywhere, **orbitals** like past videos, **3 fonts** (one wavy script), B&W so viewers see the filter change, face only in the hook, **once** in the body, and the CTA.
- **3 fonts:** Inter Tight (headlines) + Great Vibes (wavy script accents) + **JetBrains Mono** (kickers, chapter step lines, terminal, card labels). `"mono": true` on a scene switches its kicker / chapter step to mono.
- **Orbit text cards:** `orbit` items may use `"card": {k, t, s, d, icon, back}` instead of `src` — mono kicker · Inter Tight word (auto-fit) · Great Vibes line (auto-fit) · mono foot; the back face shows `back` (never mirrored text). Card orbits are 720 px tall.
- **Stamp lift:** `"stamp": {…, "bottom": 190}` raises it over the cards with a solid dark fill so it never meets the low captions.
- **B&W hook:** a `look` scene (`"look": "bw"`, `lead` 1.0) from frame 0 until the hook question, snapping to colour as the lockup lands.

## 20. v7 · Webinar / Zoom clips → vertical shorts (Lloyd, 2026-10-21 · `web19`)
Brief: cut many short-form clips from a 1-hour Zoom webinar (screen share + small speaker tile); content only (no selling / ABC pitch); clean jump cuts, no stutters or dead air. **Layout (his 2nd brief, same day): portrait SPLIT — the screen on top, zooming in/out on every example he's doing (prompting, Claude's replies, the editor, the result video); his face on the bottom; only a little motion graphics; use the whole 9:16.**
- **Base layout first, then the normal pipeline.** `tools/zoomclip.py SRC input/NAME.mp4 --plan plan.json` (default `--layout split`) composes 1080×1920 from the 1280×720 recording: **screen** 1080×1080 on top (square crops of the screen that ease between keyframes `{t,x,y,w,ease}` — wide ≈600 px for context, 320–430 px to zoom into the thing he's talking about), a 6 px **orange seam** with glow at y 1082, his **face** 1080×836 below (the Zoom speaker tile, `--cam-box x,y,w`, default 1100,0,136 — clear of the name label), a dark bottom shade under the app UI. Several source ranges can be joined in one plan (hook line from later + body). Crops stay above the Zoom live-caption strip (y 615) and off the speaker tile (x > 1065, y < 125). `scratch/web19_plans.py` anchors each zoom to a word index so it lands as he says it.
- **Graphics, minimal:** one hook `tag` at the top of the screen (y 236, frame 0, ~3.8 s, doubles as the thumbnail) + 2–4 `mini` tags (alternating sides, `"dur": 3.2`) on the key points. Nothing else over the screen.
- Captions `pop`, `caption_size` 88, `caption_y` 1030 (on the seam), `punch_in` 0, no hook_zoom, `grade` false, `sfx.py --no-riser`.
- The face tile is only ~136 px wide in a Zoom recording, so the bottom half is a soft upscale — tell Lloyd; a separate camera recording would fix it.
- `--layout card` keeps the first version (cam bubble + header cards `"slot": "hdr"` beside it, screen in an orange-edged 1000×760 panel).
