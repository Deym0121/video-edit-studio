"""SDR (BT.709) graphics → HLG (BT.2020) signal, so brand colours stay true on iPhone HDR footage.

Graphics white is placed at full HLG white (1000 nits nominal, signal 100 %) — at the BT.2408 reference
(203 nits = 75 %) white text read as grey next to Lloyd's bright wall (≈ 70–75 %). The footage itself is never touched — only the
graphics and captions that go on top of it are converted. Used by vedit when the source is HLG."""
from pathlib import Path

import numpy as np

M709_2020 = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
A, B, C = 0.17883277, 0.28466892, 0.55991073


WHITE_NITS = 1000


def sdr_to_hlg(rgb, white_nits=WHITE_NITS):
    """rgb: (..., 3) floats 0–1, BT.709 display-referred (gamma 2.4) → HLG BT.2020 signal 0–1."""
    lin = np.clip(rgb, 0, 1) ** 2.4                      # BT.1886 display light, 1 = SDR white
    lin = np.clip(lin @ M709_2020.T, 0, None) * white_nits / 1000  # BT.2020 primaries, nits / 1000-nit peak
    yd = lin @ np.array([0.2627, 0.6780, 0.0593])
    e = lin * np.where(yd > 0, yd, 1)[..., None] ** ((1 - 1.2) / 1.2)  # inverse HLG OOTF (γ 1.2)
    e = np.clip(e, 0, 1)
    return np.where(e <= 1 / 12, np.sqrt(3 * e), A * np.log(np.maximum(12 * e - B, 1e-9)) + C)


def hex_to_hlg(h):
    h = h.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    return "#" + "".join(f"{round(float(v) * 255):02X}" for v in sdr_to_hlg(rgb))


def write_cube(path, n=33):
    path = Path(path).with_name(f"{Path(path).stem}_{WHITE_NITS}.cube")
    if path.exists():
        return path
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")    # .cube order: red changes fastest
    out = sdr_to_hlg(np.stack([r, gg, b], -1).reshape(-1, 3))
    lines = [f"LUT_3D_SIZE {n}"] + [f"{x:.6f} {y:.6f} {z:.6f}" for x, y, z in out]
    path.write_text("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    for c in ("#FFFFFF", "#FF6A00", "#FF9A4D", "#0C0908", "#000000"):
        print(c, "→", hex_to_hlg(c))
