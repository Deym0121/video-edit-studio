# The Studio: how it works

The Studio is the step-by-step screen in front of the video pipeline. **Its name is editable**: click the name in the top-left (default **Joshua Ladero Studio**, saved in `studio.json`), so every buyer can brand it as their own. A creator picks a look in 7 short steps. Claude and the pipeline turn those choices into the real edit: cuts, captions, motion graphics, sound and the final MP4.

Open it at **http://localhost:8765/**. The detailed editor (cuts, words, flags) is at **/editor** ("Fine-tune cuts" in the top right).

```bash
cd ~/Desktop/"Video Edit with claude" && .venv/bin/python tools/editor/server.py
```

---

## 1. What we took from the reference

**Their UI (what made it easy).**
- A dark screen with one accent colour.
- Numbered steps with a ✓ when done.
- One plain sentence per step, for example "Tick as many as you like" and "Skip this step if you like it simple".
- Big numbered cards with a **Picked** badge. The cards show the creator's own video, not stock art.
- A phone-size quick preview with −5s / Play / +5s and the note "timing is a guide".
- Back / Next at the bottom.
- Extras split into **Elements** vs **Motion**.

**Their branding.**
- One loud accent (mustard/yellow) on near-black.
- A bold sans for the main words, plus one script or serif accent line.
- Their extras are social-proof props:
  - a comment pop-up
  - a view counter ("2,487 views in a week")
  - a typing line ("film once, post all week")
  - check/star badges

**How they hook (first 3 seconds).**
1. **Payoff first**: the result is said and shown before the how ("film once, post all week").
2. **Social-proof number**: a big counter on screen early.
3. **Comment bubble**: a viewer's comment on screen as the reason for the video.

**How they CTA.**
- The post had about 220 comments against about 434 likes. That ratio usually means a "comment KEYWORD to get it" call to action.
- This is an inference: we only had one screenshot.
- The toolkit already has a matching `cta` scene (comment keyword + follow), and the webinar videos use "Link sa comments".

**What we kept as our own.**
- Orange `#FF6A00`, Inter Tight + Great Vibes and the "word behind you" hook are the defaults.
- The reference's ideas became choices the buyer can pick, not a copy of their look.

---

## 2. The screens: what the buyer clicks and what it changes

| Step | The buyer… | What changes in the real video |
|---|---|---|
| **Start** | uploads a video or picks a project; sees what's already done (cuts, QC) | transcribe + plan run in the background |
| **1 Colours** | picks 6 palettes or any custom colour | every motion graphic is recoloured (`brandkit.recolor`); caption keywords and the progress bar use the accent |
| **2 Fonts** | picks 5 pairings: Signature, Editorial, Punchy, Friendly, Classic | graphics swap to the pair's display + script fonts; captions use its caption font |
| **3 Hook** | types the hook word + small line; picks 1 of **11 hooks** in 5 groups. **Behind you**: word behind you, headline + word behind, outline behind you. **Titles**: kinetic title, tag + big word, typed headline. **Thumbnail**: boxed, two-tone. **Social proof**: comment pop-up, proof counter. **Simple**: just me | rewrites the hook scene in `scenes.json` (marked `"hook": <id>`); every one renders for real (behind/lockup/thumb/tag templates) |
| **4 Captions** | picks Pop, **Highlight** (karaoke: the spoken word lights up), **Boxed** (colour box), **Bold outline** (caps + stroke), Punch, Classic or none; position; size; keyword chips | `caption_style`, `caption_y`, `caption_size`, `keywords` (vedit writes each style as ASS subtitles) |
| **5 Visuals** | picks how much b-roll (Light / Balanced / Full); keeps or removes each graphic in this video; ticks templates from the Library (hover to play real samples) | removed scenes are dropped at once; density + templates guide Claude's next graphics pass |
| **6 Extras** | ticks Elements (progress bar, keyword colour, comment pop-up, counter, typing line, script line) and Motion (punch-in zoom, hook zoom, glass, swooshes, riser) | "Applies on render" items switch real settings; "Claude places it" items are placed by Claude on the right line |
| **7 Watch** | Render preview (720p) → Export final 1080p + .srt; sees a "Your look" summary | runs plan → mograph → sfx → render |

Every click saves at once (top-right "Saved"). EN / TL switches the whole UI between English and Taglish.

**Seeing and hearing every choice (no render needed):**
- **Hover** any card: its graphic moves (silently).
- **Click** a card: it is picked **and** plays in the phone, with the voice and the render's own sound effects. The sounds are the real `tools/sfx.py` sounds at render level, served from `/sfx/<name>.wav`.
- **▶ Play** on a card: just watch it, without changing your pick. ■ on the phone stops it.
- **Hooks** play on the real first 6 s of your edit. For "behind you" hooks, a moving Apple-Vision cut-out keeps the text behind your head (built once per edit: `hookbg_*.mp4` + `hookcut_*.webm` in `work/<n>/studio/`).
- **Colours / Fonts**: clicking one replays your hook in the new look.
- **Captions** play 6 s of a talking-head moment in that style.
- **Visuals**: "In this video" plays that moment of your **last render** (graphic + voice + sound). Library samples play the moment from the past video they came from.
- **Extras** each have a demo with sound: comment pop, counter ticks + ding, typing clicks, script write-on, punch-in, hook zoom, glass blur, swooshes, riser.
- On a narrow window the phone sits on top as a strip, so previews are always visible.

---

## 2b. Studio v2 (2026-10-21): what's new

| Where | Feature | What it does |
|---|---|---|
| Phone preview | **Live graphics** ◎ | Plays the real scene pages (HTML + GSAP) at the playhead. A new colour or font shows in motion about 1 s later, with no render. The text behind you and the shrink card still play from the last render. |
| Phone preview | **Safe zones** ▯ | Cycles TikTok, Reels and Shorts button overlays so you can see what the app will cover. |
| Start | **🗣 Tell Claude what you want** | A design brief: chips (platform, vibe, captions, graphics) + the creator's own words → the look, with a reason for each change (`tools/editor/studio_brief.py`). Saved as `decisions.json` `look.brief`, which Auto-edit and Apply notes follow. Optionally Claude fits the edit, then a preview renders. |
| Start | **🎬 Style references** | Up to 3 videos the creator likes → `tools/refstyle.py` learns caption case/position/size, highlight colour, cut pace, graphics share and title-first hooks (Apple Vision text + face finders). Mix & match part by part → the look (+ Brand Kit). Kept in `refs/<id>/` as a contact sheet + numbers; the video is deleted. |
| Start | **✨ Auto-edit with Claude** | Runs Claude Code headless on the project (the full editorial pass and checks), then renders a preview. Each step Claude takes shows live. It can also auto-edit every new upload. Needs Claude Code installed. |
| Start / Watch | **🎨 Brand Kit** | Saves the look to `brandkits/<kit>.json`. Apply it to any video, set a default for every new upload, or export and import it as a file. |
| Hook | **🎯 Hook Lab** | Shows the 3 strongest 2–7 s lines with a play button and an editable thumbnail title (top / boxed / bottom). The line you pick is **copied** to the top as a cold open; the body still runs through it. |
| Hook | **Trending 2026 hooks** | POV, redacted secret, phone alert, search bar, breaking glitch, split-flap, price drop, myth vs fact. Each preview is the real template in your look, with your text. |
| Captions | 2 new styles | **Quiet lowercase** (calm, no colour) and **Script keyword** (the keyword in your handwritten font). |
| Visuals | **✨ 2026 trends** tab | 44 new motion graphics in 6 groups (point at it, screen demo, phone & apps, numbers & rankings, type, cards & fun). Hover a card to watch it; click it to pick it and play it on your video with sound. |
| Watch | **🩺 Edit Health** | `tools/health.py` gives a score out of 100 and a list. Click an item to jump to it; one-click fixes include *Tighten* (dead air), *Natural colour* (HDR), *Turn off graphic* (over the face), *Add as note* and *Open Hook Lab*. |
| Watch | **💬 Talk to edit** | Type a note or say it (🎤) at the current time. *Apply notes with Claude* fixes them all and re-renders. Without Claude Code, *Copy notes* lets you paste them into a chat. |
| Watch | **📦 Post Kit** | 9:16, 1:1 and 16:9 versions (letterboxed, never cropped), `captions.srt`, `cover.jpg` and `post.txt`, plus one zip. |
| Upload | **Natural colour** | iPhone HDR → SDR with Apple's own tone mapping (`tools/bin/tosdr`) before transcribing. |

---

## 3. Under the hood

```
Studio click ─► POST /api/project/<n>/look ─► work/<n>/decisions.json  ("look" + caption/extras keys)
                                            └► work/<n>/scenes.json     (hook scene)
Render ─► vedit plan ─► mograph.py ─► brandkit: recolour + font swap per scene (only changed scenes re-render)
                    ─► sfx.py (riser on/off) ─► vedit render: captions in the caption font + accent, progress bar in accent
                    ─► output/<n>_preview_vN.mp4  /  final + .srt
```

- No `look` means the video renders exactly as before (Signature Orange, Inter Tight / Great Vibes).
- Fonts are bundled locally in `assets/fonts` and `motion/fonts`. All are SIL Open Font License, so they're OK to ship in a paid product. Renders never depend on Google Fonts loading.
- The skill (`SKILL.md` step 2c) and `CLAUDE.md` tell Claude to read `look` before editing. That is what makes "Claude places it" extras and the visual preferences work.

---

## 4. Bugs found and fixed while testing

| # | What the user would have seen | Fix |
|---|---|---|
| B1 | Opening a project froze the machine (20+ video encodes at once) | at most 2 preview encodes at a time |
| B2 | Preview captions in a different place and colour than the render | preview uses the real `caption_y`, accent, captions on/off |
| B3 | Removing a word sometimes did nothing, silently | warning when the voice runs straight through the word |
| B4 | Timeline didn't refit after resizing the window | refits on resize |
| B5 | Switching the hook to Kinetic merged the small line into the title ("free WEBINAR") | correct read-back; hook switching is lossless (tested behind → kinetic → thumbnail → behind) |
| B6 | Two quick clicks: the second one got undone | one edit at a time on the server + saves queued in order (tested with 6 parallel saves) |
| B7 | Unticking Hook zoom deleted its timings for good | timings are parked and come back when re-ticked |
| B8 | Visuals cards were black boxes with raw codes as titles ("2–3 2 hours hours") | mid-scene preview frames, the real video behind transparent graphics, readable titles, clear "Removed · tap to bring it back" |
| B9 | "Removed" / "Claude places it" tags covered card titles | tags sit inside the thumbnail |
| B10 | Two uploads named IMG_7779 / IMG_7780 would share one hook graphic file and overwrite each other | every new hook gets a unique id per project |
| B11 | Editorial (Playfair) big numbers: the "7" dropped below the line into the sub-line | brand fonts use lining figures |
| B12 | Suggested hook word picked Tagalog verb forms ("NAGKAKAROON") | uses Claude's keywords, else the video's most repeated topic word (ROADMAP, AGENTS, FEATURES…) |
| B13 | Hovering a Visuals card never played it (an empty overlay sat on top of the video) | hover finds the card's video; every card type animates on hover |
| B14 | In a narrow window the phone preview was hidden, so clicked previews played where nobody could see them | phone stays on screen as a top strip |
| B15 | Kinetic-title hooks were timed to the first word "So", which sits before the scene start, so they jumped to the next "so" (2.4 s late) | lockup tokens accept seconds (`@0.2`); Studio hooks use them |
| B16 | A caption card's ▶ played your current style, not that card's style | preview uses the card's style without changing your pick |

## 4b. Proof it renders

- `output/studio_look_test.png` compares two renders of img_7779 at the same moments.
  - Top: the original orange final (Inter Tight).
  - Bottom: the Studio render with **Sunshine + Editorial** (`output/img_7779_preview_v4.mp4`).
  - The hook word, every card, the caption keywords and the fonts all follow the Studio choice, and nothing else changed.
- Upload test: a 6 s clip went upload → transcribe → plan → opens in the Studio with a frame, cut-out and hook in about 1 minute.

---

## 5. Honest limits (today)

- **Quick preview plays the graphics from the last render.** A new colour or font shows in the still previews right away, but in motion only after **Render preview**. A look change re-renders every graphic, which takes a few minutes. The hint under the player says this.
- **Thumbnail title** sits over the chest. If the face is framed low (like img_7779), it touches the chin, so use Word behind you. The card says this.
- **Carousel** and **Shrink card** are templates now (Visuals → Library; samples come from the `work/tpl_test` scratch project). The quick previews (Studio phone, Fine-tune) now play the shrink too: the browser scales and clips the video into the card with the same curve and window as `vedit render`, over a frosted copy of the frame. It is still a stand-in: the card edge is a CSS clip (no sub-pixel mask) and the frosted backdrop is the browser's blur, not the render's grade. Click the card's ▶ to see the real render.
- Hook previews mirror the renderer's layout and timing closely, but the exact frame comes from **Render preview**. The sounds are exact: same files, same levels.
- With "Swooshes" (sound effects) off, the render has no sound effects, so the previews play voice only.
- **"Claude places it" extras** (comment pop-up, counter, typing line, script line) are wishes for Claude's graphics pass. Ticking them doesn't add them by itself.
- **Mac and Windows**: on a Mac the person cut-out (text behind you) uses Apple Vision; on Windows, torchvision's DeepLabV3 (`tools/personmask.py`), a little softer at the edges.
- **Local, single-user app** (127.0.0.1). Selling it as SaaS would need accounts, storage and a render queue.

## 6. To make it sellable (suggested next)

1. Save the look as a **brand kit** that every new video starts with (now it's per video).
2. Auto-place the comment pop-up and counter without a Claude pass.
3. Add a **first-run sample project**, so a buyer sees a finished edit before uploading.
4. Make a **one-click installer** (`tools/setup.sh` + fonts + models), plus a licence key if needed.
