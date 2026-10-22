"""Studio: tell Claude what you want (a design brief) and learn a style from videos you like (style references).

  Brief             chips (platform, vibe, captions, graphics) + the creator's own words → the look, with a reason
                    for every change. It is saved as decisions.json "look.brief", so Auto-edit and Apply notes follow
                    it too. With Claude Code installed, Claude then fits the edit itself (graphics, hook, pace) and the
                    Studio renders a preview; without it, the Studio maps the brief itself and can render right away.
  Style references  videos the creator likes, from any creator → tools/refstyle.py learns their pacing, captions,
                    colours, graphics and hook. "Make it my style" mixes them part by part into the look (and can
                    save it as a Brand Kit). Only a contact sheet and numbers are kept: the reference video itself is
                    deleted once it has been studied, and its footage is never used in an edit.
"""
from __future__ import annotations

import re
import shutil
import sys
import threading
import time
from pathlib import Path

import studio_api as sa
import studio_pro as sp
from studio_api import ROOT, brandkit, vedit

sys.path.insert(0, str(ROOT / "tools"))
import refstyle  # noqa: E402

REFS = ROOT / "refs"
ref_jobs: dict = {}


# ================================================================ style references
def _rid(s):
    return re.sub(r"[^a-z0-9-]+", "", str(s).lower())[:48]


def _style(rid):
    return vedit.jload(REFS / _rid(rid) / "style.json", None)


def refs():
    REFS.mkdir(exist_ok=True)
    out = []
    for d in sorted((p for p in REFS.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime):
        st, j = _style(d.name), ref_jobs.get(d.name, {})
        r = dict(id=d.name, name=(st or {}).get("name") or j.get("name") or d.name,
                 state="ready" if st else j.get("state", "error"), log=j.get("log", ""))
        if st:
            v = int((d / "style.json").stat().st_mtime)
            r.update({k: st.get(k) for k in ("summary", "look", "why", "captions", "pace", "graphics", "accent")},
                     thumb=f"/refs/{d.name}/thumb.jpg?v={v}", sheet=f"/refs/{d.name}/sheet.jpg?v={v}")
        out.append(r)
    return dict(refs=out)


def ref_upload(filename, stream, length):
    """A video the creator likes → refs/<id>/ → studied in the background (then the video itself is deleted)."""
    REFS.mkdir(exist_ok=True)
    stem = _rid(re.sub(r"[^A-Za-z0-9]+", "-", Path(filename).stem)).strip("-")[:32] or "reference"
    rid, n = stem, 2
    while (REFS / rid).exists():
        rid, n = f"{stem}-{n}", n + 1
    d = REFS / rid
    d.mkdir()
    ext = Path(filename).suffix.lower() if Path(filename).suffix.lower() in (".mov", ".mp4", ".m4v", ".webm") else ".mp4"
    src = d / f"source{ext}"
    left = length
    with open(src, "wb") as f:
        while left > 0:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    pretty = Path(filename).stem[:40]
    ref_jobs[rid] = dict(state="running", log="Studying its style…", name=pretty)

    def run():
        try:
            st = refstyle.analyze(src, d)
            st["id"], st["name"] = rid, pretty
            vedit.jsave(d / "style.json", st)
            ref_jobs[rid] = dict(state="ready", name=pretty)
        except Exception as e:  # noqa: BLE001 — shown on the card
            ref_jobs[rid] = dict(state="error", log=str(e)[-400:], name=pretty)
        finally:
            src.unlink(missing_ok=True)  # only the style is kept, never the footage
            shutil.rmtree(d / "frames", ignore_errors=True)
    threading.Thread(target=run, daemon=True).start()
    return dict(id=rid, state="running")


def ref_delete(rid):
    d = REFS / _rid(rid)
    if rid and d.is_dir() and d.parent == REFS:
        shutil.rmtree(d)
    ref_jobs.pop(_rid(rid), None)
    return refs()


def ref_file(rid, fn):
    p = REFS / _rid(rid) / fn
    return p if fn in ("thumb.jpg", "sheet.jpg") and p.exists() else None


# ================================================================ applying a look (shared by both)
def _names():
    c = brandkit.catalog()
    return dict(palette={p["id"]: p["name"] for p in c["palettes"]}, fonts={f["id"]: f["name"] for f in c["fonts"]},
                caption={x["id"]: x["name"] for x in c["captions"]}, pos={x["id"]: x["name"] for x in c["positions"]},
                hook={x["id"]: x.get("name", x["id"]) for x in c["hooks"]}, density={x["id"]: x["name"] for x in c["density"]},
                motion={m["id"]: m.get("name", m["id"]) for m in c["motion"]})


def _apply(name, body):
    """Look changes → decisions.json, through the same calls the Studio's cards use."""
    lk = sa.get_look(name)
    out = {}
    if body.get("palette"):
        out["palette"] = body["palette"]
    elif body.get("accent"):
        out["accent"] = body["accent"]
    if body.get("fonts"):
        out["fonts"] = body["fonts"]
    if body.get("caption"):
        cur = lk.get("caption", {})
        out["caption"] = dict(style=body["caption"].get("style", cur.get("style")), pos=body["caption"].get("pos", cur.get("pos")),
                              size=body["caption"].get("size", cur.get("size")))
    if body.get("visuals") or body.get("types"):
        v = lk.get("visuals", {})
        types = sorted(set(v.get("types") or []) | set(body.get("types") or []))
        out["visuals"] = dict(density=(body.get("visuals") or {}).get("density", v.get("density", "medium")), types=types)
    if body.get("extras_add"):
        ex = lk.get("extras", {})
        out["extras"] = dict(elements=sorted(set(ex.get("elements", [])) | set(body["extras_add"])), motion=ex.get("motion", []))
    if out:
        sa.set_look(name, out)
    if body.get("hook") and body["hook"] != lk.get("hook", {}).get("type"):
        cur = sa.get_look(name).get("hook", {})
        sa.set_hook(name, dict(type=body["hook"], text=cur.get("text", ""), kicker=cur.get("kicker", "")))
    if body.get("pace"):
        dec = sa._dec(name)
        dec.setdefault("look", {})["pace"] = body["pace"]
        sa._save_dec(name, dec)


def style_apply(name, body):
    """"Make it my style": the references mixed part by part ({part: ref id}) → the look (+ a Brand Kit)."""
    ids = body.get("ids") or [r["id"] for r in refs()["refs"] if r["state"] == "ready"]
    styles = [s for s in (_style(i) for i in ids) if s]
    if not styles:
        return dict(ok=False, msg="Add a video you like first.")
    look_body, notes = refstyle.mix(styles, body.get("picks") or {})
    _apply(name, look_body)
    dec = sa._dec(name)
    lk = dec.setdefault("look", {})
    lk["style_refs"] = [dict(id=s["id"], name=s["name"], summary=s.get("summary", "")) for s in styles]
    lk["style_notes"] = "; ".join(f"{p} like “{n}” ({w})" for p, n, w in notes)
    sa._save_dec(name, dec)
    r = dict(ok=True, look=sa.get_look(name), notes=[dict(part=p, ref=n, why=w) for p, n, w in notes])
    if body.get("kit"):
        r["kits"] = sp.kit_save(name, {"kit": body["kit"]})
    return r


# ================================================================ brief → look
VIBES = {  # chip → the look it stands for
    "clean": dict(fonts="signature", caption=dict(style="lower"), visuals=dict(density="light"), hook="lockup", pace="medium"),
    "bold": dict(fonts="punchy", caption=dict(style="punch"), visuals=dict(density="heavy"), hook="thumb", pace="fast"),
    "premium": dict(fonts="editorial", palette="mono", caption=dict(style="script"), visuals=dict(density="light"), hook="lockup", pace="calm"),
    "fun": dict(fonts="friendly", caption=dict(style="pop"), visuals=dict(density="medium"), hook="comment", pace="fast", types=["sticker", "burst"]),
    "teach": dict(fonts="signature", caption=dict(style="highlight"), visuals=dict(density="medium"), pace="medium",
                  types=["scribble", "target", "rail", "keys", "chart"], extras_add=["keywords", "progress"]),
}
CAPS = {"big": dict(style="pop", size=124), "subtle": dict(style="lower", size=78), "none": dict(style="none")}
GFX = {"few": "light", "some": "medium", "lots": "heavy"}

# words the creator might type (English + Taglish) → what they mean
WORDS = [
    # colours
    (r"\b(orange|kahel)\b", dict(palette="bbd-orange")),
    (r"\b(yellow|dilaw|gold|ginto)\b", dict(palette="sunshine")),
    (r"\b(green|berde|mint)\b", dict(palette="mint")),
    (r"\b(blue|asul|bughaw)\b", dict(palette="electric")),
    (r"\b(pink|red|pula|rosas|berry|magenta)\b", dict(palette="berry")),
    (r"\b(black and white|black & white|mono|monochrome|itim at puti|neutral)\b", dict(palette="mono")),
    # vibe
    (r"\b(clean|minimal|minimalist|simple|malinis|simple lang)\b", "clean"),
    (r"\b(bold|energetic|hype|viral|masigla|maingay|energetic)\b", "bold"),
    (r"\b(premium|luxury|elegant|sosyal|classy|cinematic)\b", "premium"),
    (r"\b(fun|funny|playful|masaya|nakakatawa|kwela)\b", "fun"),
    (r"\b(teach|tutorial|explain|educational|explainer|turo|ituro|paliwanag|how[- ]to)\b", "teach"),
    # captions
    (r"\b(no captions?|walang captions?|without captions?)\b", dict(caption=dict(style="none"))),
    (r"\b(big|bigger|large|malaki|malaking|malalaki|malalaking)\b[^.]*\bcaptions?\b|\bcaptions?\b[^.]*\b(big|bigger|large|malaki|malaking|malalaki|malalaking)\b", dict(caption=dict(size=124))),
    (r"\b(small|smaller|subtle|maliit|maliliit|maliit na)\b[^.]*\bcaptions?\b|\bcaptions?\b[^.]*\b(small|smaller|subtle|maliit|maliliit)\b", dict(caption=dict(size=78))),
    (r"\b(lowercase|small letters|maliliit na letra)\b", dict(caption=dict(style="lower"))),
    (r"\b(all caps|uppercase|capital letters|malalaking letra)\b", dict(caption=dict(style="punch"))),
    (r"\b(boxed|box|naka-?box|may box)\b", dict(caption=dict(style="box"))),
    (r"\b(highlight|keywords?|naka-?highlight)\b", dict(caption=dict(style="highlight"), extras_add=["keywords"])),
    (r"\b(top|taas|itaas|above)\b", dict(caption=dict(pos="top"))),
    (r"\b(bottom|baba|ibaba|lower third)\b", dict(caption=dict(pos="low"))),
    (r"\b(middle|gitna|center)\b", dict(caption=dict(pos="middle"))),
    # graphics
    (r"\b(no graphics|walang graphics|less graphics|konting graphics|kaunting graphics)\b", dict(visuals=dict(density="light"))),
    (r"\b(lots of graphics|more graphics|maraming graphics|full b-?roll|madaming graphics)\b", dict(visuals=dict(density="heavy"))),
    # pace
    (r"\b(fast|faster|mabilis|bilisan|quick cuts|fast cuts)\b", dict(pace="fast")),
    (r"\b(slow|calm|chill|relaxed|dahan-dahan|mabagal)\b", dict(pace="calm")),
    # hooks
    (r"\b(big number|number|numero|counter|count up)\b", dict(hook="counter")),
    (r"\bpov\b", dict(hook="pov")),
    (r"\b(secret|sikreto|redacted)\b", dict(hook="redact")),
    (r"\b(comment|komento)\b", dict(hook="comment")),
    (r"\b(price|presyo|discount)\b", dict(hook="price")),
    (r"\b(myth|fact|mali)\b", dict(hook="flip")),
    (r"\b(thumbnail|big title|malaking title)\b", dict(hook="thumb")),
    (r"\b(glitch)\b", dict(hook="glitch")),
    (r"\b(search bar|google)\b", dict(hook="search")),
    (r"\b(text behind|behind me|sa likod)\b", dict(hook="behind")),
    # motion graphics
    (r"\b(arrows?|palaso)\b", dict(types=["arrow"])),
    (r"\b(circle|bilog|marker)\b", dict(types=["scribble"])),
    (r"\b(charts?|graphs?)\b", dict(types=["chart"])),
    (r"\b(before and after|before/after|before & after)\b", dict(types=["wipe"])),
    (r"\b(keyboard|shortcuts?)\b", dict(types=["keys"])),
    (r"\b(zoom|magnif\w*|loupe)\b", dict(types=["loupe"])),
    (r"\b(countdown|timer)\b", dict(types=["timer"])),
    (r"\b(tier list|ranking|rank)\b", dict(types=["tier", "rank"])),
    (r"\b(confetti|celebrat\w*)\b", dict(types=["burst"])),
    (r"\b(stickers?)\b", dict(types=["sticker"])),
    (r"\b(notification|phone|iphone)\b", dict(types=["island"])),
]


def _merge(a, b):
    for k, v in b.items():
        if k == "caption":
            a.setdefault("caption", {}).update(v)
        elif k in ("types", "extras_add"):
            a[k] = sorted(set(a.get(k, [])) | set(v))
        else:
            a[k] = v
    return a


def brief_to_look(answers, text):
    """Chips first, then the creator's own words (more specific, so they win). → (look body, [(part, source)])."""
    body, src = {}, []
    v = (answers or {}).get("vibe")
    if v in VIBES:
        _merge(body, VIBES[v])
        src.append(("vibe", f"you picked {v}"))
    c = (answers or {}).get("captions")
    if c in CAPS:
        _merge(body, dict(caption=CAPS[c]))
        src.append(("captions", f"you picked {c} captions"))
    g = (answers or {}).get("graphics")
    if g in GFX:
        _merge(body, dict(visuals=dict(density=GFX[g])))
        src.append(("graphics", f"you picked {g} graphics"))
    low = (text or "").lower()
    for pat, what in WORDS:
        m = re.search(pat, low)
        if not m:
            continue
        said = f"you said “{m.group(0).strip()}”"
        if isinstance(what, str):
            _merge(body, VIBES[what])
            src.append(("vibe", said))
        else:
            _merge(body, what)
            src.append((next(iter(what)), said))
    hx = re.search(r"#[0-9a-f]{6}\b", low)
    if hx:
        body.pop("palette", None)
        body["accent"] = hx.group(0).upper()
        src.append(("palette", f"you gave the colour {hx.group(0).upper()}"))
    return body, src


def _reasons(body, src):
    """What changed, in plain words, with why."""
    N = _names()
    why = {}
    for part, s in src:
        why.setdefault(part, s)
    out = []

    def r(label, value, *parts):
        out.append(dict(part=label, value=value, why=next((why[p] for p in parts if p in why), why.get("vibe", ""))))
    if body.get("palette"):
        r("Colours", N["palette"].get(body["palette"], body["palette"]), "palette")
    if body.get("accent"):
        r("Colours", body["accent"], "palette")
    if body.get("fonts"):
        r("Fonts", N["fonts"].get(body["fonts"], body["fonts"]), "fonts")
    c = body.get("caption") or {}
    if c:
        val = " · ".join(x for x in (N["caption"].get(c.get("style"), ""), N["pos"].get(c.get("pos"), ""), f"size {c['size']}" if c.get("size") else "") if x)
        r("Captions", val, "caption", "captions")
    if body.get("visuals"):
        r("Graphics", N["density"].get(body["visuals"]["density"], body["visuals"]["density"]), "visuals", "graphics")
    if body.get("types"):
        r("Motion graphics", ", ".join(N["motion"].get(t, t) for t in body["types"]), "types")
    if body.get("hook"):
        r("Hook", N["hook"].get(body["hook"], body["hook"]), "hook")
    if body.get("pace"):
        r("Pace", body["pace"], "pace")
    return out


def brief_get(name):
    lk = sa._dec(name).get("look", {})
    return dict(lk.get("brief") or {}, styled=bool(lk.get("style_refs")))


def brief_apply(name, body, render=None):
    """The brief → the look now (live preview updates at once). Then, with Claude Code: Claude fits the edit to the
    brief and the Studio renders a preview. Without it: render a preview right away if asked."""
    answers, text = body.get("answers") or {}, (body.get("text") or "").strip()
    look_body, src = brief_to_look(answers, text)
    _apply(name, look_body)
    dec = sa._dec(name)
    dec.setdefault("look", {})["brief"] = dict(answers=answers, text=text, t=time.time())
    sa._save_dec(name, dec)
    out = dict(ok=True, look=sa.get_look(name), changes=_reasons(look_body, src), claude=None, render=False)
    if body.get("claude") and sp.claude_bin():
        out["claude"] = brief_claude(name, answers, text, render if body.get("render") else None)
    elif body.get("render") and render:
        render()
        out["render"] = True
    return out


def brief_claude(name, answers, text, after=None):
    chips = ", ".join(f"{k}: {v}" for k, v in answers.items() if v) or "none"
    prompt = (f"The creator told the Studio the design they want for work/{name}. Chips: {chips}. In their own words: \"{text or '(none)'}\".\n"
              "Read CLAUDE.md, DESIGN_SYSTEM.md and .claude/skills/bbd-video-edit/SKILL.md first. The Studio already set what it could "
              f"in work/{name}/decisions.json \"look\" (palette, fonts, captions, graphics density, hook, look.pace, look.brief"
              f"{', look.style_refs / look.style_notes' if sa._dec(name).get('look', {}).get('style_refs') else ''}). Now make the edit itself match "
              f"the brief: captions and keywords, the hook, the pace (tighten pauses with remove / cut_ranges if they want it faster), and the "
              f"motion graphics in work/{name}/scenes.json (pick tools/mograph_more.py types that fit; never cover the face). "
              "Do NOT render and do not touch files outside this folder. Reply with 3 short lines in the creator's language: what you changed.")
    return sp.claude_run(name, "brief", prompt, after)
