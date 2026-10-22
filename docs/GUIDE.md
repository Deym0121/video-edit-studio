# Studio guide: install and make your first edit

This guide takes you from the GitHub page to your first finished video, one step at a time. It needs no coding experience. 🇵🇭 Tagalog / Taglish: **[GABAY.md](GABAY.md)**

📺 **Video version:** `docs/tutorial/Studio_Tutorial.mp4` (about 4 min): a screen-share walkthrough of every click, from this GitHub page to your brief, style references, Auto-edit, Hook Lab, Edit Health, Talk to edit, the Post Kit and Brand Kits. The narration script is in `docs/tutorial/VOICEOVER.md`.

---

## Before you start

It runs on a **Mac** or a **Windows PC**.

| You need | Why | How to check |
|---|---|---|
| **Mac:** Apple Silicon (M1, M2, M3 or M4) | Fast transcription and Apple's own person cut-out and colour tools | Apple menu → About This Mac → "Chip: Apple M…" |
| **Windows:** Windows 10 or 11, 64-bit | The same Studio, with open-source cut-out, face and text tools | Settings → System → About → "System type: 64-bit" |
| **About 10 GB free** | AI models and tools | Mac: System Settings → General → Storage · Windows: Settings → System → Storage |
| **Mac only: Xcode Command Line Tools** | They build four small Apple tools | Open Terminal and run `xcode-select --install`. If it says "already installed", you're done. |
| **The Claude app** (recommended) | Claude installs the Studio for you, and powers **Auto-edit** and **Apply notes** | Download it from [claude.ai/download](https://claude.ai/download) and sign in. On Windows, Claude runs commands through [Git for Windows](https://git-scm.com/download/win), so install that too. |

> **Mac:** Terminal is at Applications → Utilities → Terminal. **Windows:** open the Studio folder in File Explorer, click the address bar, type `powershell` and press Enter: a PowerShell window opens in that folder. Each grey block below is one command. Paste it in and press Return (Enter).

---

## Step 1: get the code and put it on your Desktop

1. Go to **github.com** and search for **video edit studio**, or open https://github.com/Deym0121/video-edit-studio.
2. Click the green **Code** button, then **Download ZIP**.
3. Open the download so it unzips into a `video-edit-studio-main` folder.
4. Drag that folder onto your **Desktop**.

**With git instead:**

```bash
cd ~/Desktop
git clone https://github.com/Deym0121/video-edit-studio.git
```

## Step 2: install

### Option A: let Claude do it (easiest)

1. Open the **Claude app** and go to the **Code** tab.
2. Choose the folder on your Desktop as the folder to work in.
3. Type **`install this`** and send it.
4. Claude asks before it runs a command. Click **Allow**. It runs the installer, checks every piece and starts the Studio, then gives you the link.

Using Claude Code in Terminal instead? Go into the folder (`cd ~/Desktop/video-edit-studio-main`), run `claude`, and type `install this`.

### Option B: install it yourself

**Mac.** In Terminal, go into the folder first: type `cd ` with a space after it, drag the folder from your Desktop into the Terminal window, and press Return. Then:

```bash
./tools/setup.sh
```

**Windows.** In PowerShell, opened in the folder (see the tip above):

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

- The first install takes **10–20 minutes**, because it downloads the AI models (about 8 GB). Later runs skip what's already done.
- `--lite` (Mac) or `-Lite` (Windows) makes a smaller install that skips the voice cleanup and one QC model.
- No admin rights, no system Python: everything goes inside the folder.

Then check that everything is in place:

```bash
./vedit doctor
```

On Windows: `.\vedit.cmd doctor`

Each line should show ✓. What to do if one doesn't:

| You see | Fix |
|---|---|
| `✗ could not build …` or "Needs the Xcode Command Line Tools" (Mac) | Run `xcode-select --install`, wait for it to finish, then run `./tools/setup.sh` again |
| `✗ no whisper backend` | Run the installer again; the download was probably interrupted |
| `✗ … (not installed)` next to a finder (Windows) | Run `tools\setup.ps1` again; a Python package didn't finish installing |
| `– Claude Code CLI` | That's optional. Install Claude Code only if you want Auto-edit |
| `– voice cleanup` | You used `--lite`. Run the installer without it to add the voice cleanup |

## Step 3: open the Studio

```bash
./vedit studio
```

On Windows: `.\vedit.cmd studio`

It opens **http://localhost:8765** in your browser. Keep the Terminal (PowerShell) window open while you use the Studio; closing it stops the Studio.

**Make it yours:** click the Studio's name at the top left and type your brand.

## Step 4: upload a video

- On **Start**, drag a `.mov` or `.mp4` onto **Upload a video**.
- The Studio **transcribes it and cleans the cuts by itself**: retakes, repeats and dead air are removed. This takes a few minutes.
- **iPhone HDR footage becomes natural colour automatically**, so the edit looks like your camera.

## Step 4b: tell Claude what you want (don't skip this)

The Studio works best when you say what you're after, instead of only clicking cards.

- **🗣 Tell Claude what you want:** tap where you'll post it, the vibe (clean, bold, premium, fun, teach), the captions and how many graphics. Then write it in your own words, or say it with 🎤, for example: *"clean, yellow keywords, big captions at the bottom, fast cuts, a hook with a big number, arrows on the screen demo"*.
- Click **✨ Build my look**. Your colours, fonts, captions, graphics, hook and pace change at once, and the Studio lists **what changed and why** ("Colours → Sunshine · you said 'yellow'"). The live preview shows it right away.
- **Render a preview after** (ticked) renders the video with the new look. With Claude Code installed, **Let Claude fit the edit too** has Claude adjust the edit itself (graphics, hook, pace) before that preview.
- **🎬 Learn a style from videos you like:** add up to 3 videos from creators you like. In a few seconds the Studio studies each one: caption case, position and size, highlight colour, how often it cuts, how much on-screen graphics, and whether it opens on a big title. In **Mix & match**, take each part from the video you like best, then click **✨ Make it my style** (tick **Also save as a Brand Kit** to keep it). Only the style is kept: the video you add is deleted after it's studied, and nothing from it ends up in your edit.
- **✨ Auto-edit with Claude** (needs Claude Code) does the whole editorial pass in one click, following your brief and your style: cuts, hook, captions and motion graphics. It asks for a brief first. Tick **Auto-edit every new upload** to run it on every new upload.

### What runs by itself, and what waits for a click

| You do | What happens |
|---|---|
| Click a card (colour, font, caption, graphic…) | The look is saved and the live preview updates at once. The video itself re-renders only when you click **Render preview**. |
| **Build my look** | The look changes at once. If **Render a preview after** is ticked, a preview renders by itself; with Claude Code, Claude first fits the edit, then the preview renders. |
| **Make it my style** | The look changes at once. Click **Render preview** to see it rendered. |
| **Auto-edit** / **Apply notes with Claude** | Claude runs, then a preview renders by itself. |

## Step 5: colours and fonts

- **Colours:** pick a palette, or any brand colour with **Custom**.
- **Fonts:** pick a pairing (a bold headline font plus a handwritten accent).
- **Hover** any card to see it move, and **click** to pick it and hear it on your video.

## Step 6: the hook (the first 2 seconds)

- **🎯 Hook Lab** shows your 3 strongest lines. Press **Play** to hear each one, edit the thumbnail title (top line / boxed words / bottom line), then click **Use as cold open**. That line plays first, and the video still runs through it later.
- Below Hook Lab there are **19 hook styles**: word behind you, kinetic titles, thumbnail titles, comment pop-up, counter, POV, redacted secret, phone alert, search bar, glitch, split-flap, price drop and myth vs fact. Type your hook word, then click a style to hear it.

## Step 7: captions

- Choose from **8 styles**: Pop, Highlight, Boxed, Bold outline, Punch, Classic, Quiet lowercase and Script keyword.
- Pick the **position** and **size**, then **tap keywords** to colour them.

## Step 8: visuals (motion graphics)

- Choose how much b-roll you want: **Light**, **Balanced** or **Full**.
- **In this video** lists the graphics already placed. Click one to play it, or remove it.
- **✨ 2026 trends** has 44 new motion graphics, such as marker circles, target rings, a magnifier loupe, before/after wipes, phone alerts, search bars, tier lists, countdowns, charts and myth/fact flips. Tick the ones you like, and Claude places them on the lines they explain.

## Step 9: extras (optional)

Elements (progress bar, keyword colour, comment pop-up…) and Motion (punch-in zoom, hook zoom, swooshes, riser). Skip this step if you like it simple.

## Step 10: watch, check and post

1. **Render preview** makes a 720p preview in a few minutes.
2. **🩺 Edit Health** finds words said twice, clipped words, dead air, "filtered" HDR colour, graphics over your face, text under the TikTok/Reels buttons, a missing hook and quiet audio. Click an item to jump to it, or use its one-click fix.
3. **💬 Talk to edit:** pause where something is wrong, type or say a note (🎤) and click **Add**. **Apply notes with Claude** fixes them all. Without Claude Code, **Copy notes** lets you paste them into a Claude chat.
4. **Export final 1080p** makes the full-quality video plus a captions file (`.srt`).
5. **📦 Post Kit** gives you 9:16, 1:1 and 16:9 videos, captions, a cover image and the post caption, in one zip.

---

## Good to know

- **◎ Live graphics** (under the phone) play your changes instantly, with no render. Turn it off to see the last render instead.
- **▯ Safe zones** shows where TikTok, Reels and Shorts put their buttons.
- **🎨 Brand Kit** saves your look and reuses it on every video, or shares it as a file.
- **EN / TL** switches the Studio between English and Taglish.
- **Fine-tune cuts ↗** opens the detailed editor (word by word) if you want to restore or remove a word yourself.
- **Prefer chatting?** In Claude Code, say *"edit input/my-video.mov"*. The same pipeline runs.

## Update · uninstall

- **Update:** run `git pull`, then the installer again (`./tools/setup.sh`, or `tools\setup.ps1` on Windows).
- **Uninstall:** quit the Studio and delete the folder. Nothing was installed outside it.

## FAQ

- **Windows?** Yes, Windows 10 and 11 (64-bit). The Studio and every feature are the same. A few tools differ under the hood: transcription runs on the CPU (slower than on Apple Silicon), and the person cut-out, face finder and text finder use open-source models instead of Apple's. Every change is tested on a clean Windows machine by the repo's Windows check.
- **Linux?** Not tested yet.
- **Where are my files?** Your videos are in `input/`, edits in `work/` and renders in `output/`. They stay on your computer, and git ignores them.
- **Is it private?** The Studio runs on `127.0.0.1` only. Auto-edit sends your transcript to Claude through your own Claude Code account; nothing else leaves your computer.
