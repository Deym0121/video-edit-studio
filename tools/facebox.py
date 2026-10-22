"""facebox (Python twin of tools/facebox.swift, for Windows and Linux): face rectangles in still images, with OpenCV.
Usage: python tools/facebox.py img1.png [img2.png …]  →  one JSON line per image: {"file": …, "faces": [[x, y, w, h], …]}
Rects are in pixels, origin top-left — the same output as the Apple Vision build, so callers don't care which one runs.
"""
import json
import sys

import cv2

CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

for path in sys.argv[1:]:
    faces = []
    img = cv2.imread(path)
    if img is not None:
        grey = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        side = min(img.shape[:2])
        for x, y, w, h in CASCADE.detectMultiScale(grey, scaleFactor=1.1, minNeighbors=6, minSize=(side // 12, side // 12)):
            faces.append([int(x), int(y), int(w), int(h)])
    print(json.dumps({"file": path, "faces": faces}), flush=True)
