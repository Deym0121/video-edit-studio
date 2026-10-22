# BBD on-screen style guide

Source: `BBD_CapCut_EditingMasterclass.pptx` and `BBD VIDEO EDITOR.pptx` (Lloyd's Google Drive). Lloyd confirmed on 2026-10-03 that the **orange / navy** palette from the CapCut Masterclass is correct. Machine-readable values live in `tools/style.json`.

## Brand
| Role | Colour | Use |
|---|---|---|
| Background | Deep Navy `#0D1B2A` | Video backgrounds, overlays, title cards |
| Accent | Fiery Orange `#FF6B35` | Hook text, keywords, CTAs |
| Text | Pure White `#FFFFFF` | All subtitle and body text |
| Secondary | Muted Blue `#8BA3B8` | Supporting text, labels |

Fonts: **Impact / Anton** for hook text and big overlays · **Arial Black** for sub-headers and short labels · **Calibri Bold** for subtitles and captions (falls back to Arial Bold if Calibri isn't installed).

Logo: **top-left**, 8–12% of screen width, transparent PNG. Never in the bottom 15% (platform buttons). Only one corner.

## Cutting & pacing
| Clip type | Duration |
|---|---|
| Hook clip | 1–3s (shortest, most impactful) |
| Talking head | 3–6s per shot in Reels; longer is fine in long-form with punch-ins |
| B-roll | 2–4s |
| Text / title card | 2–3s |
| Product close-up | 2–5s |
| Slow motion | 4–8s, sparingly |

- Remove dead air, "uh / um", awkward silence, re-takes, stumbles.
- "Bored watching your own edit? Your viewer got bored 2 seconds earlier."
- Hard cuts 80% of the time. Transitions only at major scene changes, under 0.5s, max 1–2 styles per video.

## Subtitles (always on, since 85% watch muted)
- Bold sans-serif, white, black outline (stroke) and soft shadow.
- Reels (9:16): 3–4 words per line, one line, about 20% up from the bottom (above the platform buttons).
- Long-form (16:9): one line of about 7 words, lower area.
- One style for the whole video. Keywords in orange.
- Review every word: brand names, English terms, Taglish spelling → `fixes` in decisions.json. Grammar errors break trust.

## Audio
| Layer | Level |
|---|---|
| Voice | 100%, always the loudest |
| Music | 15–30% (target 20%) |
| SFX (whoosh on transitions, pop on text) | 50–70% |
Output loudness is normalised to −14 LUFS (social / YouTube standard).

## Colour grade (one consistent look)
Brightness +5–15 · Contrast +10–25 (the most important control) · Saturation +5–20 · Highlights −10–25 · Shadows +5–15 · Sharpness +10–20. If using a filter: one filter for the whole video at 30–60% intensity. `vedit` applies a mild version of this automatically (`grade` in style.json).

## Export
1080p (or source resolution), 30fps for social (24fps for a cinematic look), 9:16 for Reels and 16:9 for YouTube.

## Final QC before delivery
- [ ] Hook in the first 3s, no long intro
- [ ] All dead air, fillers and retakes removed, and **no words missing** (`vedit verify`)
- [ ] Story order matches the format (structures.md)
- [ ] Subtitles reviewed word by word, in the safe zone, consistent style
- [ ] Voice clear at 100%, music not drowning it
- [ ] Grade consistent start to finish
- [ ] Logo top-left, not covering the face
- [ ] One clear CTA, spoken + on screen
