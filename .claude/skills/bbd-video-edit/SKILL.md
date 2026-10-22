---
name: bbd-video-edit
description: Edit talking-head / educational / ad videos for Beyond Breakeven Digital (BBD) end-to-end — clean cuts that never chop words, retake and filler removal, brand captions, colour grade, logo, export. Use whenever Lloyd gives a video to edit ("i-edit mo to", "edit this video", "linisin mo yung cuts", "lagyan ng subtitles"), for any length from 15-second Reels to 16+ minute long-form.
---

# BBD Video Edit

Turns a raw video into a clean, on-brand edit in **one pass with few revisions**.
**Design: `DESIGN_SYSTEM.md` (project root) is the latest look — kinetic lockups, pop captions, natural footage, editing guardrails. It wins over the reference files.** Tool: `./vedit` (project root). Brand: `tools/style.json`. Structure per format: `reference/structures.md`. Visual/audio rules: `reference/style-guide.md`.

## The #1 rule: the message must stay complete

Lloyd's past edits needed many revisions because **words went missing and splices were choppy**. So:

1. **Never cut inside a sentence that is being kept.** The only things removed from inside a kept sentence are standalone fillers (um, uh, ah, eh, hmm) and stutters ("ang ang ang") — never meaningful words, even short ones like "ano" when it means "what", "kasi", "so", "pero".
2. **Retakes:** keep the *complete, best* take (usually the last). Remove the whole failed attempt, from its first word to the word right before the good take starts. Never splice half of take 1 with half of take 2.
3. **When unsure, KEEP it** and list it in your message to Lloyd as a "possible cut". A slightly long video costs one comment; a missing word costs a re-edit.
4. **Long-form is not short-form.** For 3–20 minute videos, do NOT cut content to make it shorter. Remove only dead air, fillers, retakes, false starts, and off-camera junk. Pauses are tightened to about 0.3s, not removed, so speech still breathes.
5. **Cuts are by word index, never by guessed time.** That is what `vedit` enforces. Don't bypass it with raw ffmpeg cutting.

## Workflow (do the steps in order; stay fast)

**0. Setup (once per machine):** `./vedit doctor`. If it isn't ready → `./tools/setup.sh`.

**1. Intake.** Videos go in `input/` (or use the path Lloyd gives). Pick the format from the duration: ≤30s short · ≤60s mid · otherwise long (`reference/structures.md`). Defaults, no questions needed: captions ON (`pop`), grade OFF (natural footage, DESIGN_SYSTEM.md §1), logo if `assets/logo.png` exists. Ask only what you can't infer (e.g. "may logo file ka ba?" if there's no logo and it's client work).
**iPhone HDR (HLG / Dolby Vision, check `ffprobe … color_transfer=arib-std-b67`):** convert to SDR with Apple's tone mapping BEFORE transcribing: `tools/bin/tosdr IN.MOV input/NAME.mov` (several clips: tosdr each, then a video+audio concat). Never ship an HLG render: it plays as "HDR" and Lloyd sees a filter (2026-10-20). Never ffmpeg-tonemap it either. DESIGN_SYSTEM.md has the details.

**2. Transcribe:** `./vedit transcribe input/NAME.mp4` (add `--language tl` if auto-detect returns garbage on Taglish). Run it in the background for videos over ~5 min. With several videos, transcribe them one after another and do step 3 for video A while B transcribes.

**2a. Background noise (fan, aircon, hum).** Lloyd records with an electric fan on. Before rendering, run `.venv/bin/python tools/cleanaudio.py input/NAME.mov --test 20-45` and check the pause floor drops ≥25 dB per clip with every word still heard, then run it without `--test` (DeepFilterNet3 voice isolation from `.venv-df` — spectral gating was not enough, Lloyd still heard the fan — + voice EQ/de-ess/compression; the original is kept at `work/NAME/source_noisy.*`) and set `"room_tone": false` in decisions.json. Timings don't change, so no re-transcribe.

**2b. Listen before you cut (hidden retakes).** Run `.venv/bin/python tools/literal.py input/NAME.mp4 --raw` and `.venv/bin/python tools/listen.py input/NAME.mp4 0-12 11-23 … --mms` over the whole raw video. listen.py prints, per 12 s window, Whisper words (W), literal MMS words (M) and an energy strip (`#` voice, `:` soft, `.` room, space = gate). Whisper hides retakes inside one stretched word, so wherever W and M disagree or a word spans a voiced-gap-voiced pattern, re-listen to a tighter window. Then patch the kept take's timings in transcript.json (`"patched": true`) and add `cut_ranges` for the hidden attempt (see DESIGN_SYSTEM.md §9).

**2c. Studio choices.** If `work/NAME/decisions.json` already has a `"look"` (set in BBD Studio, CLAUDE.md), keep it and edit to it: graphics coverage from `look.visuals.density`, templates from `look.visuals.types`, and place the ticked "Claude places it" extras from `look.extras`. Never overwrite `look` or the caption keys the Studio set. `look.brief` (the creator's own words about the design) and `look.style_notes` (styles learned from videos they like) come first: when they ask for something the cards don't cover (a pace, a kind of graphic, a hook idea), do it in decisions.json / scenes.json. `look.pace` fast = tighter pauses and more cuts; calm = leave breathing room.

**3. Editorial pass — read `work/NAME/transcript.txt` in full.** Each line starts with the index of its first word (`#812`); count forward within the line, or use `./vedit locate input/NAME.mp4 --text "exact phrase"` to get exact indices. Then write `work/NAME/decisions.json`:

```json
{
  "mode": "long",
  "remove": [
    {"from": 0,   "to": 14,  "reason": "pre-roll chatter before the real start"},
    {"from": 212, "to": 240, "reason": "retake — kept 2nd take (#241–)"},
    {"from": 518, "to": 518, "reason": "filler 'um'"}
  ],
  "hook": {"from": 1430, "to": 1452},
  "protect": [{"start": 300.0, "end": 330.0, "reason": "silent screen demo — keep pauses"}],
  "fixes": {"57": "Beyond", "58": "Breakeven", "903": "ROI"},
  "keywords": ["libre", "50%", "ROI"],
  "captions": true,
  "caption_style": "pop",
  "tuning": {"max_pause": 0.33, "keep_pause": 0.18},
  "punch_in": 1.08
}
```
- `remove`: inclusive word-index ranges. Look for retakes (repeated phrases, "ulit", "sorry", "wait", restarts), false starts, filler words, pre-roll and post-roll chatter ("okay na ba?", "cut"), and Whisper hallucinations in silence ("Thank you for watching").
- `hook` (optional, for long and mid): a 3–15s line from later in the video that works as a cold open (a strong claim, result or question). It plays first, and the video then starts normally. Only use it when there's a genuinely strong line.
- `protect`: time ranges (original seconds) where silence is intentional (demos, b-roll moments). No pause trimming there.
- `fixes`: caption spelling corrections by word index (brand names, English words Whisper misspelled, Taglish spelling). The audio is untouched.
- `keywords`: words highlighted in brand orange in the captions. Use sparingly, about one per 10–20 seconds.
- `punch_in`: 1.05–1.10 alternates a subtle zoom on every other segment to hide jump cuts (good for single-camera talking heads; leave it out for screen recordings).
- `tuning`: override pause preset values. New videos use `{"max_pause": 0.33, "keep_pause": 0.18}` (DESIGN_SYSTEM.md §9: trim every pause ≥0.33 s); use e.g. `{"keep_pause": 0.4}` for a slower, calmer delivery.
- `caption_style`: `"pop"` (default, DESIGN_SYSTEM.md §5), `"punch"` or classic. `caption_y`: top of talking-head captions in 1920-scale px (default 1150). `grade`: `true` only if Lloyd wants the old colour grade.

**4. Plan:** `./vedit plan input/NAME.mp4` → read `work/NAME/review.md`. Check: every content cut is justified, and the "Final script" reads as complete sentences with no orphaned fragments. Fix `decisions.json` and re-plan if needed (it takes seconds).

**Dead air is removed from the real waveform, not just the transcript.** After the word-based cuts, `plan` trims every clip head to ≤0.10s and every tail to ≤0.16s before/after voice, and shortens any flat stretch inside a clip longer than `max_pause`. It respects `keep_ranges` (time the editor dragged back in) and includes gated soft onsets and breaths. Lloyd noticed flat audio at clip edges before this existed. Disable it with `"no_silence_pass": true` only if a video needs its silences.

**4b. Resolve the review warnings. They are where words used to go missing.** `transcribe` automatically re-listens to every gap of 1.2s or more (`[+word]` in the transcript = recovered words, often hidden retakes). `review.md` then flags:
- *Pauses kept because they contain voice*: re-transcribe that spot (see below). If it's noise, a laugh or a bump, cut it with `"cut_ranges": [{"start": s, "end": e, "reason": "..."}]` (original seconds). If it's words, handle them like any other words.
- *Suspiciously long words (>1.2s)*: Whisper often stretches one word over a **hidden retake** ("decide kung lead… decide kung lead, support"). Re-transcribe the window `[prev word start, next word end]` with `whisper_words(clip, "tl", prompt=None)`. If there's a hidden take, patch the real timings of the kept words in `transcript.json` (add `"patched": true`) and `cut_ranges` the earlier attempt.
- Energy check: `work/NAME/energy.npy` holds 10 ms dB frames. Normal speech is about −10 to −30 dB, room tone about −40 dB, and noise-gate silence −100 dB. A "word" sitting in −40 to −100 audio is a hallucination; a take with no energy where a word should be means that word wasn't actually said. Prefer the other take.

**5. Preview + self-check:** `./vedit render input/NAME.mp4` (fast 720p, hardware encoder, same look as the final), then `./vedit verify input/NAME.mp4 --apply`. If verify reports splice suspects, it widens the padding at exactly those cuts: re-run `plan` + `render` once. Run renders in the background for long videos.
Verify compares 5s windows, so short-window Whisper noise produces false alarms. Before trusting a suspect, re-listen to a 10s window of the preview around it and compare with the plan's words at those output times.

**5·0. Doubles and broken audio: trust the literal model and the waveform, not Whisper.** Whisper is trained to clean up speech and *deletes* repeated words, so a transcript can look clean while the viewer hears doubles (Lloyd caught this several times). Before delivering:
1. `.venv/bin/python tools/literal.py input/NAME.mp4` uses Meta MMS (CTC, Tagalog). It has no language model, so a word said twice is written twice. Read `work/NAME/literal.txt` (phonetic spelling is normal) and fix every real `DBL`. Ignore particle flags ("na nanood", "hindi pa paid").
1b. `.venv/bin/python tools/wordcheck.py input/NAME.mp4` aligns the planned script with literal.json and lists words the viewer should hear but the literal model didn't (clipped onsets like "Pangatlo"→"tlo", missing "AI"). Check every "heard: —" line and any clearly different word.
2. `.venv/bin/python tools/soundcheck.py input/NAME.mp4` reports `CUT` (a splice made while the voice is loud, which clips a word) and `CHOPPY` spots. The planner's splice smoothing moves edges to quiet moments automatically; anything left over is a natural onset after gate silence.
3. Leftovers from removed retakes show up as fragments glued to the next take ("-ay bakit", "pa- pagising"). Cut them at the energy dip.
4. Lloyd can press **M** in the editor to flag spots; they are stored in `work/NAME/marks.json`. When he says "ayusin ang mga minarkahan ko", fix every mark.

**5a. Run `.venv/bin/python tools/audit.py input/NAME.mp4` after every plan change, before rendering the final.** It rebuilds the edited audio from edl.json, re-listens in 10s windows, dedupes seam duplicates, and auto-confirms each repeat with a centred window. Then read `work/NAME/audit.txt` line by line. Words that seem missing are often just seam drops, so confirm with a centred 8s window before acting. Fix the confirmed repeats, fragments and incomplete sentences ("Yung someone who can... and", "And once, …"), and after every cut re-check the words right next to it (a cut once clipped "builder"). Then patch the transcript timings of kept words in the new take so captions match the audio.

**Repeat & noise QC on the FINAL audio (mandatory before delivering).** Whisper silently **collapses repeated words** ("tapos tapos", "auto- automation", "wow wow") in long audio, so the transcript looks clean while the viewer hears doubles. Re-listen to the rendered file in **4s windows with a 2s hop** using a verbatim prompt ("Verbatim, kasama ang bawat ulit at utal: tapos tapos, automation automation, so so.") and flag adjacent repeated 1–3-word n-grams. For each hit, map the output time to source through `edl.json` segments, inspect 10 ms energy plus a short-window Whisper pass, and cut the stutter with `cut_ranges` (add `keep_ranges` if a cut had clipped the good word). Parallel phrasing ("ibang business na, ibang client na", "kapag…, kapag…") and jokes ("final, final") are intentional, so leave them. Mumbles and mouth noises right after a sentence (soft −25 to −40 dB, no words) get cut too, because Lloyd hates hearing them. Don't auto-cut "voice without a word" spots from transcript coverage alone: most are real syllables with bad timestamps.

**5b. Motion graphics (when asked, or for the inspiration-reel style):** see `reference/motion-graphics.md`. In short: write `work/NAME/scenes.json` (each scene anchored to *phrases*, not times), run `.venv/bin/python tools/mograph.py input/NAME.mp4` (renders HyperFrames scenes to `motion/renders/` and registers them as `overlays` in decisions.json), then `./vedit render`. Use `"caption_style": "pop"` and `"progress_bar": true`. Add 2–4 **kinetic lockups** (`"type": "lockup"`, DESIGN_SYSTEM.md §5) on the hook, key claim and CTA — they stay on his face, captions hide while they're up. Check the chin height in the frame and set `"caption_y"` if the face sits low.
**v4 short-form tutorials (DESIGN_SYSTEM.md §13):** `"mograph_theme": "glass"`, `"caption_size": 110`, `"final_height": 1920` (4K phone source → 1080×1920 final); hook + CTA on the face with a `behind` word (text behind him, cut out with Apple Vision — `tools/bin/personmask`); body = chained glass scenes (`chapter` per step, `terminal`/`phone`/`export`/`upload`/`duo`/`office` mock-UIs) with 2–3 face breaks of ~3 s. Before sending, run `.venv/bin/python tools/hear.py output/NAME_preview_vN.mp4 a-b …` over the joins.
**2026 library (`tools/mograph_more.py`, CLAUDE.md "Studio v2"):** 43 extra scene types that sit ON the footage. Screen demos use `scribble` / `target` / `ping` / `keys` / `rail` / `ff` placed on the UI (`box` / `point` in 1080×1920 px), never over what he demos; `loupe` magnifies tiny text on a screenshot, `wipe` is a before/after slider (screenshots `before` / `after`), `dock` shows the tool stack, `frame3d` floats a screenshot in a tilted browser or phone (full-screen). Proof and numbers use `tier`, `score`, `price`, `timer`, `ring`, `chart`, `timeline`, `streak`, `receipt` (side rail) and `venn`. Phone-UI beats use `island`, `search`, `post`, `call`, `thread`, `voicenote` and `feed`. Type moments use `flap`, `glitch`, `redact`, `define`, `pov`, `rank`, `ransom`, `cloud` and `tear`. Fun beats use `flip`, `polaroid`, `achieve`, `sticker`, `burst`, `slot` and `board` (full-screen investigation board). Screenshots are files in `motion/clips`. Prefer the ones ticked in `look.visuals.types`. Top band `y` 236–420 on talking heads (each type's default already fits), right button column (x > 936, y 700–1480) stays clear; `"bg": true` makes an opaque full-screen page for B-roll moments (`board` and `frame3d` always are). **Hooks:** pick the strongest line from anywhere in the video as a COPIED cold open (`"hook": {from, to}`) with a `thumb` title on its first 3 s, or use Hook Lab in the Studio.
**Before delivering, run `.venv/bin/python tools/health.py input/NAME.mov`** (Edit Health). Fix every `!!!` item. Check each `!` item and either fix it or explain why it stays (an intentional "bye bye" is fine).
**v5 news videos (§14):** `"mograph_theme": "news"`, a `thumb` hook in the first 3 s, `article` cards with real screenshots (ask Lloyd first; never bypass bot blocks), source pill on every page. **Always:** keep everything inside the short-form safe zone (§15) and run `.venv/bin/python tools/sfx.py input/NAME.mov` after mograph (riser into the hook reveal + synced SFX, §16).

**6. Deliver the preview to Lloyd (in Taglish, short):** the preview path, original → edited duration, the content-cuts list with timestamps, possible cuts you deliberately kept, and the verify result. Ask for feedback **by timestamp** ("sa 02:13, …").

**7. Revisions:** `./vedit locate input/NAME.mp4 --at 02:13` shows the word indices around that edited timestamp. Update `decisions.json` → plan → render. Each revision is minutes, not hours.

**8. Final:** `./vedit render input/NAME.mp4 --final` → `output/NAME_FINAL.mp4` (full resolution) + `output/NAME.srt` (for YouTube/Facebook upload captions).

## Speed habits
- Never wait idle. Run long transcribes and renders in the background and read transcripts meanwhile.
- One editorial pass, done properly, beats three quick ones. Read the whole transcript once and make every decision then.
- Previews are 720p and use the hardware encoder. Only the final render is full quality.
- Don't re-transcribe the original after edits. `plan` and `render` reuse `work/NAME/`.

## Files
- `work/NAME/`: transcript.txt, words.tsv, decisions.json (yours), edl.json, review.md, verify.md, captions.ass
- `output/`: previews (`_preview_vN.mp4`), `_FINAL.mp4`, `.srt`
- `assets/logo.png`: brand logo (transparent PNG), auto-applied top-left
