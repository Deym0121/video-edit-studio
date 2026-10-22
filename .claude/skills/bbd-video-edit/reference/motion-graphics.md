# Motion graphics (HyperFrames): BBD inspiration style

> **Latest look: `DESIGN_SYSTEM.md` in the project root (v4 · Glass, 2026-10-14 — §13 lists the new glass theme, `behind`, `terminal`, `phone`, `export`, `upload`, `duo`, `office`).** It adds kinetic lockups, `pop` captions and natural (ungraded) footage, and wins where this file differs. This file stays the scenes.json field reference.

Reference look: `Inspiration video/` in the project root. It has a dark background with an orange glow, full-screen "explainer cards" that cut in over the talking head while the voice continues, small uppercase orange kickers ("● 01 · TRIGGER"), big bold titles with one orange keyword, glassy UI cards with orange icon tiles, pills and chips that light up as they're mentioned, big orange count-up numbers, handwritten script accents, 1–3 word punchy captions, and a thin orange progress bar at the top. Measured palette (DESIGN_SYSTEM.md §0): orange `#FF6A00` on warm near-black `#0C0908`, cards `#1D1415`, warm grey `#8C837C`/`#A39A93` for secondary text, dark ink on orange fills.

## Tooling
- HyperFrames CLI (`npx hyperframes`, v0.8.x) with Node 22 at `tools/node/bin` (project-local) and ffmpeg from `.venv` static-ffmpeg. The project lives in `motion/`.
- `tools/mograph.py` is the generator: scenes.json → `motion/scenes/<id>.html` → `motion/renders/<id>.mp4|.mov` → `overlays` in decisions.json.
- Full-screen scenes render as MP4 (opaque, small, fast). `"layout": "panel"` scenes render as ProRes 4444 MOV with alpha: the card sits **centre-frame** and `vedit render` **blurs and dims the footage behind it** (fading in and out over 0.2s). These files are big (~20 MB/s).
- **Never put a card over the bottom or top half of the face.** Lloyd rejected the half-screen panel because it blocked his face. Use either full-screen cards or centred cards over blurred footage.
- Render speed is about 4s of wall time per 1s of graphics. Run two mograph processes in parallel with `--only` id lists.

## Typography (matches the inspiration's font design, confirmed by Lloyd)
- **Inter Tight** for everything: titles 800, big numbers/words 900 in solid orange with glow (no gradient), card text 800, sub-text 500–600.
- **Great Vibes** for script accents (the inspiration's calligraphic "built for classification" look).
- Captions: new videos use `caption_style: "pop"` (1–2 words, 72px, shadow only, orange keyword, top at y 1150). The older `"punch"` style uses Inter Tight ExtraBold white. Keywords switch to **Inter Tight Black, 1.38× size, orange**, like the inspiration's big orange "3" / "AI".
- Font files live in `assets/fonts/` (libass captions via `fontsdir`) and `motion/fonts/` (HyperFrames `@font-face`, preloaded at t=0). Never rely on Google Fonts loading at render time: it silently falls back to Times.

## scenes.json
Each scene has `id`, `type`, `start` (phrase), and `end` (phrase where it cuts back to the face) or `until` (phrase whose end closes it). Item times are phrases too (`"at": "new row"`). Phrases are matched on the **edited** timeline with fixes applied, in order after the scene start. Hyphenated tokens are split: "na -upload" → use "upload" or "na upload". Use `*word*` for an orange highlight.

Types and their key fields:
| type | use for | fields |
|---|---|---|
| `list` | numbered steps, examples, questions | `items[{t,s,icon,at,on,state:"x",strike}]`, `small`, `pill{t,icon,at}`, `script{t,at}` |
| `chips` | sets of things (data fields, tools, skills) | `chips[{t,icon,at,on}]` |
| `pipeline` | frameworks / sequences | `steps[{t,s,icon,at,on}]` |
| `big` | one number or word | `big`, `big_at`, `sub`, `sub_at` (numbers count up) |
| `versus` | wrong vs right | `bad{t,s,at,strike}`, `good{t,s,at}` |
| `statement` | quotable line | `lines[{t,at}]`, `script` |
| `loading` | tutorial vs your reality | `tutorial{t,s,at,check,check_t}`, `mine{t,s,at}` |
| `error` | pain points + error toast | `chips`, `toast{t,s,at}`, `code{t,at}` |
| `chat` | customer conversation joke | `messages[{who:"them"/"me",meta,t,at}]`, `verdict{t,at}` |
| `email` | AI classification example | `email{...,read}`, `labels[]`, `draft`, `nosend` |
| `map` | route / navigation analogy | `route_at,dest_at,change_at,lost_at,lost_t` |
| `excel` | messy client data | `tools[]`, `excel_at,tabs_at,final_at` |
| `notify` | phone notifications | `notes[{t,icon,app,at}]` |
| `cta` | comment keyword + follow | `word,word_at,part2,part2_s,part2_at,follow,follow_s,follow_at` |
| `meter` | confidence bars | `rows[{t,v,at,hot}]`, `verdict{t,at}`, `before{t,at,strike}` |
| `choice` | multiple choice | `q`, `options[]`, `pick`, `pick_at` |
| `flow` | horizontal node row | `nodes[{t,icon,at,hot,on}]`, optional `items` (list card below) |
| `chapter` | section card | `step`, `mo`, `what`, `what_at` |
| `mindmap` | orange core + nodes | `core`, `core_at`, `nodes[{t,icon,at,on}]` |
| `loop` | agent loop | `steps[{t,at,on}]`, `core` |
| `tiles` | 2×2 tiles + button | `tiles[{t,icon,at,on}]`, `button{t,icon,at}` |
| `approval` | approve / reject card | `head,tag,line,right,approve_at,note{t,at}` |
| `lockup` | hook / key claim / CTA words over the face (transparent, captions hidden) | `rows`: tokens `word`/`M:` medium, `X:` orange keyword (`X120:` size), `C:` script, `S:a/b` stacked small, `G:` tag, `<` left, `_` space, `@phrase` timing — see DESIGN_SYSTEM.md §5 |
| `carousel` | 3–5 options / audiences / examples, one at a time (coverflow) | `items[{t,s,icon,k,at}]` (cards wait as numbered shells; on its `at` a card slides to the centre, fills in and lights in the accent, said cards step left and dim), `spacing` (px, 400), `kicker`, `title`, `pill`, `script`. Full / glass scene |
| `shrink` | a key line said on camera: the face stays, the point is written around it | `kicker`, `title`, `title_at`, `items[{t,icon,at,on}]` (chips under the card), `scale` (.6), `y`/`h` (card px), `face_y` (footage y kept in view, 720) or `src_y`. `vedit render` shrinks the **real footage** into a rounded card (upper middle, frosted footage behind, accent ring) and grows it back at the end; the page never draws inside the card, so the face is never covered. HLG stays untouched. Captions go low. Needs a talking-head moment, not a scene chain |

Common fields: `stamp{t,at}` ("DENIED" slam), `center` (centre the content), `separate` (list as individual cards), `kicker`, `title`, `title_sm`, `title_at`, `layout: "panel"`, `caption` ("low" default, "hide"), `lead` (seconds before the phrase, default 0.15).
Icons: mail bolt message table file form database check x task send bell lock dollar shield globe alert key gear node link spark play user pin tag question branch eye pen list flag code route moon.

## Pacing rules
- Cover about 60–80% of a talking-head video with graphics, but **always show the face** on hooks, jokes, emotional lines and personal asides.
- One idea per scene. Elements appear exactly when the word is said, never before.
- Scenes about 5–25s. Over 25s, split them.
- The content block must stay above y≈1500 (captions sit at about 1603 on full-screen scenes) and below the progress bar.

## Checking
Grab frames before rendering everything: `ffmpeg -sseof -0.3 -i motion/renders/<id>.mp4 -frames:v 1 x.png`. Look for overflow, orange-on-orange text, and icons that vanish on highlighted chips.
