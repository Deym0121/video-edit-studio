# Video Edit with Claude — Studio

**Your own AI video editor, on your Mac or Windows PC.** Drop in a talking-head or screen-demo video. Claude cuts the retakes, repeats and dead air, writes the captions, places motion graphics that never cover your face, and adds sound effects. You pick the look in a step-by-step Studio and **see every choice play on your own video before you render.**

No CapCut, no timeline, no stock footage. Your videos never leave your computer.

> Built by Joshua Ladero with Claude. Rename the Studio to your own brand: click its name in the top-left.

---

## What you get

| | |
|---|---|
| **Studio wizard** | Start → Colours → Fonts → Hook → Captions → Visuals → Extras → Watch, in English or Taglish. Every card plays on *your* video, with the real sound effects. |
| **Live preview** | The motion graphics are real HTML scenes, so the phone preview plays them instantly in your colours and fonts. No render needed. |
| **🗣 Tell Claude what you want** | A design brief: tap the platform, vibe, captions and graphics, then say the look in your own words (Taglish is fine). The Studio builds the look from it and shows why each part changed, and Auto-edit and your notes follow it. |
| **🎬 Learn a style from videos you like** | Add up to 3 videos from creators you like. The Studio studies their captions, colours, pacing and graphics (never their footage), and you mix them part by part into your own style or a Brand Kit. |
| **✨ Auto-edit with Claude** | One button runs the whole editorial pass, following your brief (needs [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)). |
| **🎯 Hook Lab** | Finds your strongest 2–7 s lines, proposes a thumbnail title, and copies the best one to the top as a cold open. |
| **🩺 Edit Health** | Flags words said twice, clipped words, dead air, "filtered" HDR colour, graphics over your face, text under the TikTok/Reels buttons, a missing hook and quiet audio. Each item has a one-click fix or a jump-to button. |
| **💬 Talk to edit** | Pause where something's wrong, type or say "tanggalin 'to", and Claude applies every note. |
| **📦 Post Kit** | 9:16 + 1:1 + 16:9 videos, captions (.srt), a cover image and the post caption, in one zip. |
| **🎨 Brand Kits** | Save your look and use it on every video, or share it as a file. |
| **2026 motion library** | 44 trending motion graphics: marker annotations, target rings, a magnifier loupe, before/after wipes, 3D device frames, phone alerts, search bars, feed scrolls, social post cards, tier lists, scorecards, price slashes, countdowns, charts, word clouds, split-flap boards, glitch titles, redacted reveals, myth/fact flips, polaroids and confetti. Also 19 hook styles and 8 caption styles. |
| **Natural colour** | iPhone HDR is converted to normal colour (Apple's own tone mapping on a Mac), so the edit looks like your camera. |

## Install

📘 Step-by-step guides: **[English](docs/GUIDE.md)** · **[Taglish](docs/GABAY.md)** · 📺 4-min screen-share tutorial (`docs/tutorial/Studio_Tutorial.mp4`)

**Easiest:**

1. **Code → Download ZIP**, open it, and drag the `video-edit-studio-main` folder onto your Desktop (Mac or Windows).
2. In the **Claude app**, go to the **Code** tab and choose that folder.
3. Say:

> install this

Claude runs the installer, checks everything and starts the Studio. Click **Allow** when it asks to run a command.

**By hand, on a Mac** (Terminal):

```bash
./tools/setup.sh          # ≈ 8 GB with the models · --lite for a smaller install
./vedit doctor            # checks every piece
./vedit studio            # opens http://localhost:8765
```

**By hand, on Windows** (PowerShell, in the folder):

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1     # -Lite for a smaller install
.\vedit.cmd doctor
.\vedit.cmd studio
```

**Requirements:**
- **Mac:** macOS on Apple Silicon, plus the Xcode Command Line Tools (`xcode-select --install`)
- **Windows:** Windows 10 or 11, 64-bit. No Python or admin rights needed. For "install this" in the Claude app, also [Git for Windows](https://git-scm.com/download/win)
- about 10 GB of free space

Everything installs inside this folder: no system packages and no password.

## Use it

1. **Start** → upload a video. It is transcribed and cleaned automatically, and iPhone HDR becomes natural colour.
2. Pick your **colours, fonts, hook, captions, graphics and extras**. Hover a card to watch it; click to pick it and hear it on your video.
3. **Watch** → *Render preview*. Run **Edit Health**, leave notes, then *Export final 1080p* and build the **Post Kit**.

Prefer chatting? Open the folder in Claude Code and say *"i-edit mo 'tong video na 'to"*. The same pipeline runs (`.claude/skills/bbd-video-edit/SKILL.md`).

## How it works

```
upload ─► tosdr (natural colour) ─► vedit transcribe (Whisper) ─► vedit plan (cuts at energy dips)
       ─► Claude: decisions.json (cuts, hook, keywords) + scenes.json (motion graphics)
       ─► mograph (HTML/GSAP → alpha video) ─► sfx ─► vedit render (captions, graphics, sound) ─► health checks
```

| File | What it does |
|---|---|
| `tools/vedit.py` | Transcribe, plan, render and verify |
| `tools/mograph.py` + `tools/mograph_more.py` | Motion-graphic templates |
| `tools/sfx.py` | Synthesized sound design |
| `tools/health.py` | Edit Health |
| `tools/editor/` | The Studio: `studio.html`, `studio_pro.js`, `studio_api.py`, `studio_pro.py`, `server.py` |
| `DESIGN_SYSTEM.md` | Brand and motion rules |
| `reference/motion_trends_2026.md` | Research behind the 2026 library |

## License

MIT: see `LICENSE`. The bundled fonts are SIL OFL 1.1, and the installer downloads models and tools under their own licenses (one of them, the MMS model, is non-commercial). Details are in `THIRD_PARTY_NOTICES.md`.

## Privacy

The Studio runs on `127.0.0.1` only. Your videos, transcripts and renders stay in `input/`, `work/` and `output/`, and `.gitignore` keeps them out of git. Auto-edit sends your transcript to Claude through your own Claude Code account; nothing else leaves your computer.

## Limits (today)

- On Windows, transcription runs on the CPU (faster-whisper), so it's slower than on Apple Silicon, and the person cut-out, face finder and text finder use open-source models (DeepLabV3, OpenCV, RapidOCR) instead of Apple Vision. A clean Windows machine installs and runs the whole path on every change (`.github/workflows/windows.yml`).
- Linux isn't tested yet.
- The live preview plays graphics exactly. Two pieces, the text behind you and the shrink card, show the last render, because they need the person cut-out.
- It is a single-user local app, not a hosted service.
