#!/usr/bin/env python3
"""Zoom/screen-share webinar → vertical short base layout (1080×1920), before the normal vedit pipeline.

--layout split (default, Lloyd 2026-10-21): the screen fills the top 1080×1080 and zooms in/out on whatever he is
doing; his face (the Zoom speaker tile) fills the bottom 1080×836; a thin orange seam between them, captions on the seam.
--layout card: cam bubble top-left + header slot for `tag` `"slot": "hdr"` cards, the screen in a 1000×760 orange-edged
panel (motion/layouts/zoomclip_bg.html), captions below it.

  zoomclip.py SRC OUT --start 1210.4 --end 1290 --crops '[{"t":0,"x":320,"y":40,"w":420}, …]'

crops: keyframes in seconds from --start; x,y,w = the source rectangle shown in the panel (h = w·0.7).
A move eases (cubic in-out) over `ease` s (default 0.7) starting at its t. Keep y+h above the Zoom
live-caption strip (y ≈ 630) and away from the cam tile when it isn't wanted.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vedit  # noqa: E402

W, H = 1080, 1920
PX, PY, PW, PH, PR = 40, 545, 1000, 760, 28          # card: screen panel inner rect (inside the 2 px border)
BC, BR = (194, 378), 130                             # card: cam bubble centre + radius (inside the ring)
SPLIT_SCR, SPLIT_CAM = (0, 0, 1080, 1080), (0, 1084, 1080, 836)  # split: screen box, face box (x, y, w, h)
ZOOM_CAP_Y = 615
SR = ROOT / "tools" / "bin" / "facesr"  # Apple VideoToolbox low-latency super-resolution (tools/facesr.swift)  # Zoom burns its live captions in below this line: crops stay above it
SW, SH = 1280, 720


def rounded_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def circle_mask(r, ss=4):
    m = Image.new("L", (2 * r * ss, 2 * r * ss), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * r * ss - 1, 2 * r * ss - 1], fill=255)
    return m.resize((2 * r, 2 * r), Image.LANCZOS)


def ease(u):
    u = min(1.0, max(0.0, u))
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2


def seam_strip():
    """orange seam between screen and face: a 6 px line with a soft glow both ways (RGBA, 1080×40, centred on y 962)."""
    import numpy as np
    a = np.zeros((40, W), np.float32)
    d = np.abs(np.arange(40) - 19.5)[:, None]
    a[:] = np.where(d <= 3, 1.0, np.clip(0.55 * np.exp(-(d - 3) / 4.5), 0, 1))
    rgb = np.zeros((40, W, 3), np.uint8)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = 255, 106, 0
    g = np.linspace(-1, 1, W)[None, :]
    rgb[..., 1] = (106 + 48 * (1 - np.abs(g)) * (d <= 3)).astype(np.uint8)  # brighter at the centre of the line
    return Image.fromarray(rgb), Image.fromarray((a * 255).astype(np.uint8))


def rect_at(t, keys, aspect=PW / PH, max_y=SH):
    cur = keys[0]
    out = (cur["x"], cur["y"], cur["w"])
    for k in keys[1:]:
        if t < k["t"]:
            break
        u = ease((t - k["t"]) / k.get("ease", 0.7))
        out = tuple(a + (b - a) * u for a, b in zip(out, (k["x"], k["y"], k["w"])))
        cur = k
    x, y, w = out
    w = min(w, max_y * aspect)
    h = w / aspect
    x, y = min(max(0, x), SW - w), min(max(0, y), max_y - h)
    return x, y, x + w, y + h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    ap.add_argument("--crops", default='[{"t":0,"x":0,"y":0,"w":900}]')
    ap.add_argument("--plan", help='JSON file: [{"start","end","crops"}, …] — several source ranges joined in order')
    ap.add_argument("--cam", default="1168,56,56", help="card: cx,cy,r of the speaker's face in the source")
    ap.add_argument("--cam-box", default="1100,0,136", help="split: x,y,w of the face crop in the source (h from the box aspect)")
    ap.add_argument("--layout", default="split", choices=["split", "card"])
    a = ap.parse_args()
    segs = (json.loads(Path(a.plan).read_text()) if a.plan
            else [dict(start=a.start, end=a.end, crops=json.loads(a.crops))])
    cx, cy, cr = (float(v) for v in a.cam.split(","))
    split = a.layout == "split"
    if split:
        sx, sy, sw, sh = SPLIT_SCR
        kx, ky, kw, kh = SPLIT_CAM
        fx, fy, fw = (float(v) for v in a.cam_box.split(","))
        fbox = (fx, fy, fx + fw, fy + fw * kh / kw)
        seam, seam_a = seam_strip()
        base = Image.new("RGB", (W, H), (12, 9, 8))
        import numpy as np  # bottom shade: hides the Zoom name label and keeps the app's caption/username legible
        ramp = np.clip((np.arange(220) - 20) / 200, 0, 1) ** 1.4 * 0.62
        shade_a = Image.fromarray(np.repeat((ramp * 255).astype(np.uint8)[:, None], W, 1))
        shade = Image.new("RGB", (W, 220), (8, 6, 5))
    else:
        bg = Image.open(ROOT / "motion/layouts/zoomclip_bg.png").convert("RGB")
        pm, cm = rounded_mask(PW, PH, PR), circle_mask(BR)
    ff = vedit.binpath("ffmpeg")
    for sg in segs:  # whole frames per range, so each range's audio is trimmed to exactly its video length
        sg["n"] = round((sg["end"] - sg["start"]) * 30)
    k = len(segs)
    fc = [f"[1:a]asplit={k}" + "".join(f"[s{i}]" for i in range(k))] if k > 1 else []
    for i, sg in enumerate(segs):
        d = sg["n"] / 30
        fc.append(f"[{'s%d' % i if k > 1 else '1:a'}]atrim={sg['start']:.4f}:{sg['start'] + d:.4f},asetpts=PTS-STARTPTS,"
                  f"afade=t=in:d=0.012,afade=t=out:st={d - 0.012:.4f}:d=0.012[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1[aout]")
    fc.append("[0:v]unsharp=5:5:0.45:5:5:0[vout]")  # upscaled screen/cam: light luma sharpen
    enc = subprocess.Popen([ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                            "-i", "-", "-i", a.src, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
                            "-c:v", "h264_videotoolbox", "-b:v", "24M", "-pix_fmt", "yuv420p",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-c:a", "aac", "-b:a", "192k", a.out], stdin=subprocess.PIPE)
    fsz, total = SW * SH * 3, 0
    for sg in segs:
        keys = sorted(sg["crops"], key=lambda c: c["t"])
        dec = subprocess.Popen([ff, "-v", "error", "-ss", f"{sg['start']:.3f}", "-i", a.src, "-t", f"{sg['n'] / 30 + 0.5:.3f}",
                                "-vf", "fps=30", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
        fdec = None
        if split and SR.exists():  # face: deblock + temporal denoise → Apple low-latency super-resolution ×4 → lanczos + sharpen
            cw, ch = int(fw) // 2 * 2, int(round(fw * kh / kw)) // 2 * 2
            fdec = subprocess.Popen(
                f'"{ff}" -v quiet -ss {sg["start"]:.3f} -i "{a.src}" -t {sg["n"] / 30 + 0.5:.3f} -vf "fps=30,crop={cw}:{ch}:{int(fx)}:{int(fy)},'
                f'deblock=filter=strong:block=8,hqdn3d=0:0:3:3,format=nv12" -f rawvideo - | "{SR}" {cw} {ch} 4 2>/dev/null | '
                f'"{ff}" -v quiet -f rawvideo -pix_fmt nv12 -s {cw * 4}x{ch * 4} -r 30 -i - '
                f'-vf "scale={kw}:{kh}:flags=lanczos,unsharp=7:7:1.1:5:5:0,cas=0.4,format=rgb24" -f rawvideo -',
                shell=True, stdout=subprocess.PIPE)
        last, face = None, None
        for n in range(sg["n"]):
            buf = dec.stdout.read(fsz)
            if len(buf) == fsz:
                im = Image.frombuffer("RGB", (SW, SH), buf, "raw", "RGB", 0, 1)
                if split:
                    fr = base.copy()
                    fr.paste(im.resize((sw, sh), Image.BICUBIC, box=rect_at(n / 30, keys, sw / sh, ZOOM_CAP_Y)), (sx, sy))
                    fb = fdec.stdout.read(kw * kh * 3) if fdec else b""
                    if len(fb) == kw * kh * 3:
                        face = Image.frombuffer("RGB", (kw, kh), fb, "raw", "RGB", 0, 1)
                    elif face is None or not fdec:
                        face = im.resize((kw, kh), Image.LANCZOS, box=fbox)
                    fr.paste(face, (kx, ky))
                    fr.paste(shade, (0, H - 220), shade_a)
                    fr.paste(seam, (0, ky - 22), seam_a)
                else:
                    scr = im.resize((PW, PH), Image.BICUBIC, box=rect_at(n / 30, keys))
                    face = im.resize((2 * BR, 2 * BR), Image.BICUBIC, box=(cx - cr, cy - cr, cx + cr, cy + cr))
                    fr = bg.copy()
                    fr.paste(scr, (PX, PY), pm)
                    fr.paste(face, (BC[0] - BR, BC[1] - BR), cm)
                last = fr.tobytes()
            enc.stdin.write(last)  # (a short read at the very end repeats the last frame)
        dec.stdout.close(); dec.kill(); dec.wait()
        if fdec:
            fdec.stdout.close(); fdec.kill(); fdec.wait()
        total += sg["n"]
    enc.stdin.close()
    enc.wait()
    print(f"✓ {a.out}: {total} frames ({total / 30:.1f}s, {k} range{'s' if k > 1 else ''})")


if __name__ == "__main__":
    main()
