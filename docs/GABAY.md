# Gabay sa Studio: i-install at gawin ang unang edit mo

Simple at step-by-step ang gabay na ito, mula sa GitHub hanggang sa tapos mong video. Hindi mo kailangang marunong mag-code. 🇺🇸 English: **[GUIDE.md](GUIDE.md)**

📺 **Video version:** `docs/tutorial/Studio_Tutorial.mp4` (mga 4 min): screen-share na walkthrough ng bawat click, mula sa GitHub page hanggang sa brief mo, style references, Auto-edit, Hook Lab, Edit Health, Talk to edit, Post Kit at Brand Kit. Nasa `docs/tutorial/VOICEOVER.md` ang script (English at Taglish).

---

## Bago magsimula

| Kailangan mo | Bakit | Paano i-check |
|---|---|---|
| **Mac na Apple Silicon** (M1, M2, M3 o M4) | Dito gumagana ang cut-out, ang pag-convert ng kulay at ang mabilis na transcription | Apple menu → About This Mac → "Chip: Apple M…" |
| **Mga 10 GB na bakanteng space** | Para sa AI models at tools | Apple menu → System Settings → General → Storage |
| **Xcode Command Line Tools** | Para mabuo ang tatlong maliit na Apple tool | Buksan ang Terminal at i-run ang `xcode-select --install`. Kung "already installed" ang lumabas, ayos na. |
| **Claude app** (recommended) | Si Claude ang mag-i-install ng Studio, at siya rin ang gumagawa ng **Auto-edit** at **Apply notes** | I-download sa [claude.ai/download](https://claude.ai/download) at mag-sign in |

> Ang **Terminal** ay nasa Applications → Utilities → Terminal. Isang command ang bawat gray na box sa ibaba. I-paste ito at pindutin ang Return.

---

## Step 1: kunin ang code at ilagay sa Desktop

1. Pumunta sa **github.com** at i-search ang **video edit studio**, o buksan ang https://github.com/Deym0121/video-edit-studio.
2. I-click ang berdeng **Code** button, tapos **Download ZIP**.
3. Buksan ang download para maging `video-edit-studio-main` na folder.
4. I-drag ang folder na iyon papunta sa **Desktop** mo.

**Kung git ang gamit mo:**

```bash
cd ~/Desktop
git clone https://github.com/Deym0121/video-edit-studio.git
```

## Step 2: i-install

### Option A: si Claude ang mag-install (pinakamadali)

1. Buksan ang **Claude app** at pumunta sa **Code** tab.
2. Piliin ang folder sa Desktop mo bilang folder na pagtatrabahuhan.
3. I-type ang **`install this`** at i-send.
4. Nagtatanong muna si Claude bago mag-run ng command. I-click ang **Allow**. Siya ang magpapatakbo ng installer, magche-check ng lahat, at magbubukas ng Studio, tapos ibibigay niya ang link.

Sa Terminal ka ba gumagamit ng Claude Code? Pumasok sa folder (`cd ~/Desktop/video-edit-studio-main`), i-run ang `claude`, at i-type ang `install this`.

### Option B: ikaw mismo ang mag-install

Sa Terminal, pumasok muna sa folder: i-type ang `cd ` (may space sa dulo), i-drag ang folder mula sa Desktop papunta sa Terminal window, at pindutin ang Return. Tapos:

```bash
./tools/setup.sh
```

- **10–20 minuto** ang unang install dahil nagda-download ito ng AI models (mga 8 GB). Sa susunod, nilalaktawan na nito ang tapos na.
- Mas maliit ang `./tools/setup.sh --lite` dahil wala itong voice cleanup at isang QC model.

Pagkatapos, i-check kung kumpleto:

```bash
./vedit doctor
```

Dapat ✓ ang bawat linya. Kung hindi:

| Lumabas | Gawin |
|---|---|
| `✗ could not build …` o "Needs the Xcode Command Line Tools" | I-run ang `xcode-select --install`, hintaying matapos, tapos i-run ulit ang `./tools/setup.sh` |
| `✗ no whisper backend` | I-run ulit ang `./tools/setup.sh`; baka naputol ang download |
| `– Claude Code CLI` | Optional ito. I-install lang ang Claude Code kung gusto mo ng Auto-edit |
| `– voice cleanup` | Gumamit ka ng `--lite`. I-run ang `./tools/setup.sh` nang wala nito para maidagdag |

## Step 3: buksan ang Studio

```bash
.venv/bin/python tools/editor/server.py
```

Buksan ang **http://localhost:8765** sa browser. Huwag isara ang Terminal habang ginagamit mo ang Studio, dahil titigil ang Studio kapag isinara mo ito.

**Gawing sa'yo:** i-click ang pangalan ng Studio sa itaas na kaliwa at i-type ang brand mo.

## Step 4: mag-upload ng video

- Sa **Simula**, i-drag ang `.mov` o `.mp4` sa **Mag-upload ng video**.
- **Kusa nitong ita-transcribe at lilinisin ang cuts**: tatanggalin ang retakes, ulit at dead air. Ilang minuto ito.
- **Ginagawang natural na kulay ang iPhone HDR nang automatic**, kaya kamukha ng camera mo ang edit.

## Step 4b: sabihin kay Claude ang gusto mo (huwag laktawan)

Pinakamaganda ang resulta kapag sinabi mo ang gusto mo, hindi lang puro click sa cards.

- **🗣 Sabihin kay Claude ang gusto mo:** i-tap kung saan mo ipo-post, ang vibe (malinis, bold, premium, masaya, pagtuturo), ang captions at kung gaano karaming graphics. Tapos isulat sa sarili mong salita, o sabihin gamit ang 🎤. Halimbawa: *"malinis, dilaw ang keywords, malaking captions sa baba, mabilis ang cuts, hook na may malaking number, may arrows sa screen demo"*.
- I-click ang **✨ Buuin ang look ko**. Agad na magbabago ang kulay, fonts, captions, graphics, hook at bilis, at ililista ng Studio **kung ano ang nagbago at bakit** ("Kulay → Sunshine · you said 'dilaw'"). Makikita agad sa live preview.
- Kapag naka-tick ang **Mag-render ng preview pagkatapos**, magre-render ang video gamit ang bagong look. Kung may Claude Code ka, ang **Si Claude na rin ang mag-ayos ng edit** ay pinapaayos kay Claude ang mismong edit (graphics, hook, bilis) bago ang preview.
- **🎬 Gayahin ang style ng videos na gusto mo:** magdagdag ng hanggang 3 video ng creators na gusto mo. Sa loob ng ilang segundo, pag-aaralan ng Studio ang bawat isa: case, posisyon at laki ng captions, kulay ng highlight, gaano kadalas ang cut, gaano karami ang graphics, at kung nagsisimula ito sa malaking title. Sa **Mix & match**, kunin ang bawat bahagi sa video na pinakagusto mo, tapos i-click ang **✨ Gawin itong style ko** (i-tick ang **I-save din bilang Brand Kit** para maitabi). Style lang ang itinatabi: dine-delete ang video pagkatapos pag-aralan, at walang bahagi nito na mapupunta sa edit mo.
- **✨ Auto-edit gamit si Claude** (kailangan ng Claude Code): buong edit sa isang click, ayon sa brief at style mo: cuts, hook, captions at motion graphics. Hihingi muna ito ng brief. I-tick ang **I-auto-edit ang bawat bagong upload** para awtomatiko ito sa bawat bagong upload.

### Ano ang kusang tumatakbo, at ano ang naghihintay ng click

| Ginawa mo | Ang mangyayari |
|---|---|
| Mag-click ng card (kulay, font, caption, graphic…) | Nase-save ang look at agad na nag-a-update ang live preview. Magre-render lang ang mismong video kapag pinindot mo ang **Render preview**. |
| **Buuin ang look ko** | Agad na nagbabago ang look. Kapag naka-tick ang **Mag-render ng preview pagkatapos**, kusang magre-render ang preview; kung may Claude Code, aayusin muna ni Claude ang edit, tapos magre-render. |
| **Gawin itong style ko** | Agad na nagbabago ang look. Pindutin ang **Render preview** para makita ang render. |
| **Auto-edit** / **Ipaayos kay Claude ang notes** | Tatakbo si Claude, tapos kusang magre-render ang preview. |

## Step 5: kulay at fonts

- **Kulay:** pumili ng palette, o kahit anong brand color gamit ang **Custom**.
- **Fonts:** pumili ng pares (bold na headline font at handwritten na accent).
- **I-hover** ang card para gumalaw ito, at **i-click** para piliin at marinig sa video mo.

## Step 6: ang hook (unang 2 segundo)

- **🎯 Hook Lab:** ipinapakita nito ang 3 pinakamalakas mong linya. Pindutin ang **Play** para marinig ang bawat isa, ayusin ang thumbnail title (itaas na linya / nakabox / ibaba), tapos i-click ang **Gawing cold open**. Ito ang mauunang mapanood, at dadaanan pa rin ito sa gitna ng video.
- Sa ilalim nito, may **19 hook styles**: word behind you, kinetic titles, thumbnail, comment pop-up, counter, POV, redacted secret, phone alert, search bar, glitch, split-flap, price drop at myth vs fact. I-type ang hook word mo, tapos i-click ang style para marinig.

## Step 7: captions

- Pumili sa **8 styles**: Pop, Highlight, Boxed, Bold outline, Punch, Classic, Quiet lowercase at Script keyword.
- Piliin ang **posisyon** at **laki**, tapos **i-tap ang keywords** para kulayan.

## Step 8: visuals (motion graphics)

- Piliin kung gaano karaming b-roll: **Light**, **Balanced** o **Full**.
- Nasa **Nasa video na ito** ang graphics na nakalagay na. I-click para i-play, o alisin.
- **✨ 2026 trends:** may 44 na bagong motion graphics dito, gaya ng marker circle, target ring, magnifier loupe, before/after wipe, phone alert, search bar, tier list, countdown, chart at myth/fact flip. I-tick ang gusto mo, at si Claude ang maglalagay sa tamang linya.

## Step 9: extras (optional)

Elements (progress bar, kulay ng keyword, comment pop-up…) at Motion (punch-in zoom, hook zoom, swooshes, riser). I-skip kung gusto mo ng simple.

## Step 10: panoorin, i-check, i-post

1. **Render preview:** 720p na preview sa loob ng ilang minuto.
2. **🩺 Edit Health:** hinahanap nito ang dobleng salita, putol na salita, dead air, kulay na mukhang may filter (HDR), graphics na tumatakip sa mukha, text na matatakpan ng TikTok/Reels buttons, kulang na hook at mahinang tunog. I-click ang item para tumalon doon, o gamitin ang one-click fix.
3. **💬 Talk to edit:** i-pause kung saan may mali, i-type o sabihin ang note (🎤), at i-click ang **Idagdag**. Aayusin lahat ng **Ipaayos kay Claude ang notes**. Kung wala kang Claude Code, gamitin ang **Kopyahin ang notes** at i-paste ito sa Claude chat.
4. **I-export ang final 1080p:** full-quality na video at captions file (`.srt`).
5. **📦 Post Kit:** 9:16, 1:1 at 16:9 na video, captions, cover image at caption text, sa isang zip.

---

## Magandang malaman

- **◎ Live graphics** (sa ilalim ng phone): lalabas agad ang pagbabago, walang render. I-off kung gusto mong makita ang huling render.
- **▯ Safe zones:** makikita mo kung saan ang buttons ng TikTok, Reels at Shorts.
- **🎨 Brand Kit:** i-save ang look mo para magamit ulit sa bawat video, o i-share bilang file.
- **EN / TL:** palitan ang wika ng Studio.
- **Ayusin ang cuts ↗:** detalyadong editor (salita por salita) kung ikaw mismo ang magbabalik o mag-aalis ng salita.
- **Mas gusto mong mag-chat?** Sa Claude Code, sabihin ang *"i-edit mo ang input/video-ko.mov"*. Parehong pipeline ang tatakbo.

## Update · tanggalin

- **Update:** `git pull`, tapos `./tools/setup.sh`.
- **Tanggalin:** isara ang Studio at i-delete ang folder. Walang na-install sa labas nito.

## Mga tanong

- **Windows o Linux?** Hindi pa. Gumagamit ng Apple frameworks ang cut-out at ang pag-convert ng kulay.
- **Nasaan ang files ko?** Nasa `input/` ang videos, `work/` ang edits, at `output/` ang renders. Nasa Mac mo lang ang lahat, at hindi sila isasama ng git.
- **Private ba?** Sa `127.0.0.1` lang tumatakbo ang Studio. Ang Auto-edit ay nagpapadala ng transcript kay Claude gamit ang sarili mong Claude Code account; wala nang iba pang lumalabas sa computer mo.
