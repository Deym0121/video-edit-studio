# Video structures by format

Pick by duration. The structure guides **editorial decisions** (what to cut, what goes in the hook, where to add emphasis). It is not a template to force content into. If the speaker's content runs out, stop. Never pad.

## SHORT: 15–30s (mode `short`)
One idea, one point, one CTA.
| Beat | Time | Edit notes |
|---|---|---|
| Hook | 0–3s (max 5) | First clip is the shortest and punchiest. Result or close-up first. No intro. |
| Value | 3–25s | One message only. Every second is content. |
| CTA | last ~5s | One CTA, spoken AND on screen. |

## MID: 30–60s (mode `mid`), the Reels sweet spot
| Beat | Time | Edit notes |
|---|---|---|
| Hook | 0–3s | Bold question / statement / result. |
| Problem | 3–8s | Pain point. Slightly faster cuts to build tension. |
| Solution | 8–20s | Can breathe. B-roll supports what's said. |
| Proof | 20–40s | Testimonial, result, demo. Crisp cuts, on-screen text for key points. |
| CTA | last 5–8s | Slow down slightly. 1–2 shots max. Clear audio. |

Rules: shot or b-roll change every 3–5s, pattern interrupt every 5–7s, each point in 1–2 sentences.

## LONG REEL: 60–90s (mode `long`)
Same beats as MID with more depth. It still needs a hard hook in the first 3 seconds. Length earns trust only *after* the hook earns attention.

## LONG-FORM VIDEO: 3–20+ min (mode `long`)
For Lloyd's 5-minute and 16-minute videos (YouTube, Facebook long video, course and education content, webinars). **Completeness of the message is the priority, not shortness.**

| Beat | Time | Edit notes |
|---|---|---|
| Cold-open hook | 0–15s | Use `hook` in decisions.json: the strongest line or result from later in the video, played first. Skip it if no line is strong enough. Then cut straight into the start. |
| Promise / intro | ~15–45s | Who is talking and what the viewer gets by staying. Trim greeting fluff ("hi guys, welcome back…") only if it carries no information, and list it in the content cuts. |
| Body: chapters | bulk | Keep the speaker's order. Each point: claim → explanation → example/proof. Remove only retakes, false starts, fillers, and dead air. |
| Re-hooks | every 60–90s | The speaker's own pivot lines ("pero eto yung pinaka-importante…") get a keyword highlight and/or a punch-in. |
| Recap | near end | Keep if present. |
| CTA | last 10–20s | ONE CTA, spoken + on-screen. |

Long-form pacing:
- Pauses are tightened to about 0.3s, not eliminated. Natural breathing makes long videos watchable.
- Pattern interrupt every 20–40s (punch-in zoom, keyword pop, b-roll), not every 5–7s like Reels.
- `punch_in: 1.06–1.08` on single-camera talking heads hides jump cuts.
- Captions: one line, about 7 words, lower area (YouTube-safe), keywords in orange.
- Never speed up the voice. Never cut a sentence short to save time.

## Which format?
- Single tip / promo / before-after → SHORT
- How-to with context, 3-point list, mini case study → MID
- Full tutorial, problem→solution story, multiple tips → LONG REEL
- Anything recorded as a full talk, lesson, or interview over 3 min → LONG-FORM (edit it as long-form; propose Reel cut-downs separately if useful)
