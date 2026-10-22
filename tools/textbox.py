"""textbox (Python twin of tools/textbox.swift, for Windows and Linux): text lines in still images, with RapidOCR.
Usage: python tools/textbox.py img1.jpg [img2.jpg …]  →  one JSON line per image:
       {"file": …, "w": …, "h": …, "lines": [{"t": text, "c": conf, "r": [x, y, w, h]}, …]}
Rects are in pixels, origin top-left — the same output as the Apple Vision build.
"""
import json
import sys

from PIL import Image
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()

for path in sys.argv[1:]:
    lines, w, h = [], 0, 0
    try:
        w, h = Image.open(path).size
        result, _ = ocr(path)
        for box, text, conf in result or []:
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            x0, y0 = min(xs), min(ys)
            lines.append({"t": text, "c": float(conf), "r": [int(x0), int(y0), int(max(xs) - x0), int(max(ys) - y0)]})
    except Exception as e:  # noqa: BLE001 — one unreadable frame shouldn't stop the others
        print(f"textbox: {path}: {e}", file=sys.stderr)
    print(json.dumps({"file": path, "w": w, "h": h, "lines": lines}, ensure_ascii=False), flush=True)
