"""personmask (Python twin of tools/personmask.swift, for Windows and Linux): person cut-out for "text behind the speaker".
Usage: ffmpeg … -f rawvideo -pix_fmt bgra - | python tools/personmask.py <w> <h> > masks.gray
Reads raw BGRA frames (w*h*4 bytes) on stdin, writes one 8-bit grey mask per frame (w*h bytes, 255 = person) on stdout,
exactly like the Apple Vision build. Uses torchvision's DeepLabV3 (MobileNetV3) person class, on the GPU when there is one.
"""
import sys

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.models.segmentation import DeepLabV3_MobileNet_V3_Large_Weights, deeplabv3_mobilenet_v3_large

w, h = int(sys.argv[1]), int(sys.argv[2])
weights = DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
dev = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
model = deeplabv3_mobilenet_v3_large(weights=weights).eval().to(dev)
person = weights.meta["categories"].index("person")
mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
scale = min(1.0, 520 / max(w, h))  # the model's native size; the mask is scaled back up
sw, sh = max(8, round(w * scale)), max(8, round(h * scale))
n = w * h * 4
inp, out = sys.stdin.buffer, sys.stdout.buffer

with torch.inference_mode():
    while True:
        buf = inp.read(n)
        while buf and len(buf) < n:
            more = inp.read(n - len(buf))
            if not more:
                break
            buf += more
        if len(buf) < n:
            break
        rgb = torch.from_numpy(np.frombuffer(buf, np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0]].copy()).to(dev)
        x = rgb.permute(2, 0, 1).unsqueeze(0).float() / 255
        x = F.interpolate(x, size=(sh, sw), mode="bilinear", align_corners=False)
        prob = model((x - mean) / std)["out"].softmax(1)[:, person:person + 1]
        prob = F.interpolate(prob, size=(h, w), mode="bilinear", align_corners=False)
        out.write((prob[0, 0].clamp(0, 1) * 255).round().byte().cpu().numpy().tobytes())
        out.flush()
