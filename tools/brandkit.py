"""Brand kit: the choices the Studio wizard offers, and how a project's "look" is applied to renders.

decisions.json → "look": {
  "palette": "bbd-orange" | …,  "accent": "#FF6A00",          # 1 Colours (accent wins over the palette)
  "fonts": "signature" | "editorial" | "punchy" | "friendly" | "classic",   # 2 Fonts
  "hook": {"type": <HOOKS id>, "text", "kicker"},  # 3 Hook  (written to scenes.json as the hook scene)
  "visuals": {"density": "light" | "medium" | "heavy", "types": [...]},          # 5 Visuals (Claude places them)
  "extras": {"elements": [...], "motion": [...]}                                  # 6 Extras
}
Captions (4) use the existing keys: caption_style, caption_size, caption_y.
Everything here is optional: a project without "look" renders exactly as before (signature orange + Inter Tight).
"""
from __future__ import annotations

import colorsys
import re

DEFAULT_ACCENT = "#FF6A00"

PALETTES = [
    {"id": "bbd-orange", "name": "Signature Orange", "accent": "#FF6A00", "note": "Warm and bold"},
    {"id": "sunshine", "name": "Sunshine", "accent": "#F5C518", "note": "Bright, friendly, optimistic"},
    {"id": "mint", "name": "Mint", "accent": "#16C79A", "note": "Fresh, calm, wellness"},
    {"id": "electric", "name": "Electric", "accent": "#3D7BFF", "note": "Tech, clean, confident"},
    {"id": "berry", "name": "Berry", "accent": "#E8336D", "note": "Beauty, lifestyle, playful"},
    {"id": "mono", "name": "Mono", "accent": "#EDE7E1", "note": "Minimal, editorial, quiet"},
]

# display = headlines / big words / captions · script = the handwritten accent line
FONT_PAIRS = [
    {"id": "signature", "name": "Signature", "note": "Tight sans + elegant script",
     "display": "Inter Tight", "files": {500: "InterTight-wght-500", 600: "InterTight-wght-600", 700: "InterTight-wght-700",
                                         800: "InterTight-wght-800", 900: "InterTight-wght-900"},
     "script": "Great Vibes", "script_file": "GreatVibes", "caption": "Inter Tight ExtraBold", "caption_black": "Inter Tight Black"},
    {"id": "editorial", "name": "Editorial", "note": "Magazine serif headlines",
     "display": "Playfair Display", "files": {800: "PlayfairDisplay-800", 900: "PlayfairDisplay-900"},
     "script": "Great Vibes", "script_file": "GreatVibes", "caption": "Playfair Display ExtraBold", "caption_black": "Playfair Display Black"},
    {"id": "punchy", "name": "Punchy", "note": "Tall condensed + marker script",
     "display": "Anton", "files": {400: "Anton-400"}, "upper": True,
     "script": "Caveat", "script_file": "Caveat-700", "caption": "Anton", "caption_black": "Anton"},
    {"id": "friendly", "name": "Friendly", "note": "Round geometric + playful script",
     "display": "Poppins", "files": {800: "Poppins-800", 900: "Poppins-900"},
     "script": "Dancing Script", "script_file": "DancingScript-700", "caption": "Poppins ExtraBold", "caption_black": "Poppins Black"},
    {"id": "classic", "name": "Classic Bold", "note": "Wide heavy sans + script",
     "display": "Montserrat", "files": {800: "Montserrat-800", 900: "Montserrat-900"},
     "script": "Great Vibes", "script_file": "GreatVibes", "caption": "Montserrat ExtraBold", "caption_black": "Montserrat Black"},
]

CAPTION_STYLES = [
    {"id": "pop", "name": "Pop", "note": "1–2 big words at a time, keyword in colour", "size": 104},
    {"id": "highlight", "name": "Highlight", "note": "A short line; each word lights up as you say it", "size": 84},
    {"id": "box", "name": "Boxed", "note": "Words sit on a solid colour box", "size": 88},
    {"id": "outline", "name": "Bold outline", "note": "All caps, thick black outline — loud and readable", "size": 96},
    {"id": "punch", "name": "Punch", "note": "Short phrases, keyword bigger and heavier", "size": 80},
    {"id": "classic", "name": "Classic", "note": "One clean line, easy to read", "size": 64},
    # 2026 trends (reference/motion_trends_2026.md §4): "dynamic minimalism" is replacing the loud Hormozi look
    {"id": "lower", "name": "Quiet lowercase", "note": "Soft lowercase, no colour — calm, premium, 2026 minimal", "size": 80},
    {"id": "script", "name": "Script keyword", "note": "Bold words, the keyword in your handwritten font + colour", "size": 100},
    {"id": "none", "name": "No captions", "note": "Clean video, add captions later", "size": 0},
]
CAPTION_POSITIONS = [
    {"id": "top", "name": "Above your head", "y": 240, "note": "Best when your face fills the frame"},
    {"id": "middle", "name": "Under your chin", "y": 1150, "note": "Classic talking-head spot"},
    {"id": "low", "name": "Lower third", "y": 1290, "note": "Inside the Reels / TikTok safe zone"},
]

# 3 Hooks — every variant maps to a real scene in scenes.json (studio_api.set_hook) that mograph renders.
# group: "behind" (text behind you) · "title" (kinetic words over the top) · "thumb" (cover title) · "social" · "none"
HOOKS = [
    {"id": "behind", "group": "behind", "name": "Word behind you", "note": "A giant word sits behind your head, script line on top"},
    {"id": "behind_big", "group": "behind", "name": "Headline + word behind", "note": "Big white line above your head, the word behind you"},
    {"id": "behind_outline", "group": "behind", "name": "Outline behind you", "note": "Hollow outline letters behind your head — clean, premium"},
    {"id": "lockup", "group": "title", "name": "Kinetic title", "note": "Script line + big word pop in on your words"},
    {"id": "lockup_tag", "group": "title", "name": "Tag + big word", "note": "A colour pill, then the big word slams in"},
    {"id": "typing", "group": "title", "name": "Typed headline", "note": "Your title types out with key clicks"},
    {"id": "thumb", "group": "thumb", "name": "Thumbnail · boxed", "note": "Stacked cover title, last words in a colour box. Best when your face is in the top half"},
    {"id": "thumb_tone", "group": "thumb", "name": "Thumbnail · two-tone", "note": "Stacked cover title in white + your colour, no box"},
    {"id": "comment", "group": "social", "name": "Comment pop-up", "note": "A viewer's comment pops in as the reason for the video"},
    {"id": "counter", "group": "social", "name": "Proof counter", "note": "A number counts up — views, clients, hours saved"},
    # 2026 trend hooks (tools/mograph_more.py, reference/motion_trends_2026.md §2): on frame 0, never over the face
    {"id": "pov", "group": "trend", "name": "POV", "note": "POV chip + your scenario, up on frame 0"},
    {"id": "redact", "group": "trend", "name": "Redacted secret", "note": "The key word hides under a black bar, then it's revealed"},
    {"id": "island", "group": "trend", "name": "Phone alert", "note": "A phone alert pops open at the top — instant pattern interrupt"},
    {"id": "search", "group": "trend", "name": "Search bar", "note": "Your question types into a search bar"},
    {"id": "glitch", "group": "trend", "name": "Breaking glitch", "note": "RGB-glitch headline with a BREAKING tag"},
    {"id": "flap", "group": "trend", "name": "Split-flap", "note": "Airport-board letters flip into your word"},
    {"id": "price", "group": "trend", "name": "Price drop", "note": "Old price struck, the new one slams in (small line = old price)"},
    {"id": "flip", "group": "trend", "name": "Myth vs fact", "note": "Small line = the myth, title = the fact — the card flips"},
    {"id": "none", "group": "none", "name": "Just me", "note": "No hook graphic, captions only"},
]
HOOK_GROUPS = [
    {"id": "behind", "name": "Behind you"}, {"id": "title", "name": "Titles"}, {"id": "thumb", "name": "Thumbnail"},
    {"id": "social", "name": "Social proof"}, {"id": "trend", "name": "Trending 2026"}, {"id": "none", "name": "Simple"},
]

# 5 Visuals — motion-graphic templates Claude can place on the lines that match. sample = a real render to preview.
VISUALS = [
    {"id": "versus", "name": "Before vs after", "note": "Old way struck out, new way lights up", "sample": "i79_time"},
    {"id": "big", "name": "Big number / word", "note": "One huge word or number on its line", "sample": "i79_ticket"},
    {"id": "chips", "name": "Chips", "note": "A set of things pops in, one per word", "sample": "i79_free"},
    {"id": "list", "name": "Step list", "note": "Steps or questions stack up in a card"},
    {"id": "flow", "name": "Flow", "note": "Trigger → step → result, wired together"},
    {"id": "chat", "name": "Chat", "note": "A conversation plays out in bubbles"},
    {"id": "terminal", "name": "App window", "note": "A prompt types into a window"},
    {"id": "phone", "name": "Phone screen", "note": "A mini app on a phone"},
    {"id": "stat", "name": "Counter", "note": "A number counts up with its unit"},
    {"id": "orbit", "name": "Orbit", "note": "Cards circle around at chest height", "sample": "abc_orbit"},
    {"id": "carousel", "name": "Carousel", "note": "Cards slide in one by one; the one you're saying lights up", "sample": "tpl_carousel"},
    {"id": "shrink", "name": "Shrink card", "note": "Your video shrinks into a card, title and points around it", "sample": "tpl_shrink"},
    {"id": "notify", "name": "Notifications", "note": "Phone notifications drop in"},
    {"id": "chapter", "name": "Chapter card", "note": "STEP 2 · INSTALL section divider"},
]
DENSITY = [
    {"id": "light", "name": "Light", "note": "≈25% graphics — mostly your face", "coverage": 0.25},
    {"id": "medium", "name": "Balanced", "note": "≈45% — the short-form default", "coverage": 0.45},
    {"id": "heavy", "name": "Full b-roll", "note": "≈70% — graphics carry the story", "coverage": 0.70},
]

# 6 Extras. kind "setting" = applied by the renderer right away; "claude" = Claude places it while editing.
EXTRAS = {
    "elements": [
        {"id": "progress", "name": "Progress bar", "note": "Thin bar fills across the top", "kind": "setting"},
        {"id": "keywords", "name": "Keyword colour", "note": "Key words light up in your colour", "kind": "setting"},
        {"id": "comment", "name": "Comment pop-up", "note": "A comment bubble appears", "kind": "claude"},
        {"id": "counter", "name": "Counter", "note": "A number ticks up on screen", "kind": "claude"},
        {"id": "typing", "name": "Typing line", "note": "A line types out like a terminal", "kind": "claude"},
        {"id": "script", "name": "Script accents", "note": "Handwritten words in the titles", "kind": "claude"},
    ],
    "motion": [
        {"id": "punch", "name": "Punch-in zoom", "note": "Subtle zoom on every other cut", "kind": "setting"},
        {"id": "hookzoom", "name": "Hook zoom", "note": "Pops out, then pushes in during the hook", "kind": "setting"},
        {"id": "glass", "name": "Glass transitions", "note": "Graphics over frosted footage", "kind": "setting"},
        {"id": "sfx", "name": "Swooshes", "note": "Clean whooshes on every graphic", "kind": "setting"},
        {"id": "riser", "name": "Suspense riser", "note": "Builds into the first reveal", "kind": "setting"},
    ],
}
DEFAULT_EXTRAS = {"elements": ["progress", "keywords"], "motion": ["punch", "hookzoom", "glass", "sfx", "riser"]}


def catalog():
    import mograph_more  # the 2026 motion library: live sample pages motion/scenes/gal_<id>.html (mograph.py --gallery)
    dur = {g["id"]: g["dur"] for g in mograph_more.GALLERY}
    motion = [dict(id=i, name=n, note=t, group=g, dur=dur.get(i, 4.0), type=next(x["type"] for x in mograph_more.GALLERY if x["id"] == i))
              for i, n, t, g in mograph_more.CATALOG]
    return dict(palettes=PALETTES, fonts=FONT_PAIRS, captions=CAPTION_STYLES, positions=CAPTION_POSITIONS,
                hooks=HOOKS, hook_groups=HOOK_GROUPS, visuals=VISUALS, density=DENSITY, extras=EXTRAS,
                motion=motion, motion_groups=[dict(id=a, name=b) for a, b in mograph_more.GROUPS])


# ---------------------------------------------------------------- resolve a project's look
def font_pair(dec):
    fid = (dec.get("look") or {}).get("fonts", "signature")
    return next((f for f in FONT_PAIRS if f["id"] == fid), FONT_PAIRS[0])


def accent(dec):
    lk = dec.get("look") or {}
    if lk.get("accent") and re.fullmatch(r"#[0-9A-Fa-f]{6}", lk["accent"]):
        return lk["accent"].upper()
    pal = next((p for p in PALETTES if p["id"] == lk.get("palette")), None)
    return pal["accent"] if pal else DEFAULT_ACCENT


def extras(dec):
    ex = (dec.get("look") or {}).get("extras")
    return ex if ex else DEFAULT_EXTRAS


# ---------------------------------------------------------------- recolouring (orange family → accent)
def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def shift_rgb(rgb, target):
    """Move one colour of the signature orange family onto the target accent, keeping its relative light/dark.
    Colours outside the orange family (warm blacks, greys, white) are returned unchanged."""
    r, g, b = (v / 255 for v in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if not (5 / 360 <= h <= 45 / 360 and s >= 0.38 and 0.12 <= l <= 0.95):
        return rgb
    th, tl, ts = colorsys.rgb_to_hls(*(v / 255 for v in _hex(target)))
    base_l = 0.5  # #FF6A00
    nl = min(0.97, max(0.04, tl + (l - base_l) * (1 - abs(tl - 0.5))))
    ns = min(1.0, s * ts) if ts > 0.08 else 0.0
    nr, ng, nb = colorsys.hls_to_rgb(th, nl, ns)
    return tuple(round(v * 255) for v in (nr, ng, nb))


def recolor(text, target):
    if not target or target.upper() == DEFAULT_ACCENT:
        return text

    def hx(m):
        return "#%02X%02X%02X" % shift_rgb(_hex(m.group(0)), target)

    def rg(m):
        r, g, b = (int(x) for x in m.group(2).split(","))
        return f"{m.group(1)}({','.join(str(v) for v in shift_rgb((r, g, b), target))},{m.group(3)})"
    text = re.sub(r"#[0-9A-Fa-f]{6}\b", hx, text)
    return re.sub(r"(rgba)\((\s*\d+\s*,\s*\d+\s*,\s*\d+)\s*,\s*([\d.]+)\s*\)", rg, text)


def ink_for(target):
    """Dark ink on light accents, white on dark ones (text sitting on an accent fill)."""
    r, g, b = _hex(target)
    return "#1A0B04" if (0.299 * r + 0.587 * g + 0.114 * b) > 120 else "#FFFFFF"


# ---------------------------------------------------------------- fonts for HyperFrames pages
def font_css(pair):
    if pair["id"] == "signature":
        return ""
    faces = "".join(
        f'@font-face{{font-family:"BrandDisplay";font-weight:{w};font-display:block;src:url("../fonts/{f}.ttf")}}'
        for w, f in pair["files"].items())
    if len(pair["files"]) == 1:  # single-weight family (Anton): serve it for every weight
        f = next(iter(pair["files"].values()))
        faces = "".join(f'@font-face{{font-family:"BrandDisplay";font-weight:{w};font-display:block;src:url("../fonts/{f}.ttf")}}'
                        for w in (400, 500, 600, 700, 800, 900))
    faces += f'@font-face{{font-family:"BrandScript";font-weight:400;font-display:block;src:url("../fonts/{pair["script_file"]}.ttf")}}'
    return faces


def brandize_page(doc, dec):
    """Apply the project's look to one rendered HyperFrames page (mograph). No look → unchanged."""
    if not dec.get("look"):
        return doc
    a, pair = accent(dec), font_pair(dec)
    doc = recolor(doc, a)
    if a.upper() != DEFAULT_ACCENT and ink_for(a) == "#FFFFFF":
        doc = doc.replace("#1A0B04", "#FFFFFF").replace("--ink:#1A0B04", "--ink:#FFFFFF")
    if pair["id"] != "signature":
        doc = re.sub(r'"Inter Tight"', '"BrandDisplay","Inter Tight"', doc)
        doc = re.sub(r'"Great Vibes"', '"BrandScript","Great Vibes"', doc)
        # lining figures: Playfair's default old-style "7" drops below the line and hits the sub-line under big numbers
        extra = font_css(pair) + "body{font-variant-numeric:lining-nums tabular-nums}" + (
            'body{text-transform:none}.title,.big,.lk.xl,.bt{text-transform:uppercase}' if pair.get("upper") else "")
        doc = doc.replace("</style>", extra + "</style>", 1) if "</style>" in doc else f"<style>{extra}</style>" + doc
    return doc


def measure_file(dec, font):
    """mograph.text_w font key → font file stem for the project's look (so lockups auto-fit the chosen font)."""
    pair = font_pair(dec)
    if isinstance(font, int):
        if pair["id"] == "signature":
            return f"InterTight-wght-{font}"
        ws = sorted(pair["files"])
        best = min(ws, key=lambda w: abs(w - font))
        return pair["files"][best]
    if font == "GreatVibes":
        return pair["script_file"]
    return font
