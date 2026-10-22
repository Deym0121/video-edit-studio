#!/usr/bin/env python3
"""hear — listen to windows of ANY media file (a rendered preview/final), Whisper + literal MMS.

Usage: hear.py FILE START-END [START-END ...]
Use it on the edited output to confirm a join sounds complete before sending it to Lloyd.
"""
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402
from listen import SR, mms_words  # noqa: E402


def main():
    src = Path(sys.argv[1])
    tmp = Path(tempfile.gettempdir())
    wav = tmp / f"_hear_{src.stem}.wav"
    subprocess.run([vedit.binpath("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR),
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    with wave.open(str(wav)) as f:
        x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    clip = tmp / f"_hear_clip.wav"
    for rng in sys.argv[2:]:
        a, b = (float(v) for v in rng.split("-"))
        seg = x[int(a * SR):int(b * SR)]
        with wave.open(str(clip), "wb") as o:
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR)
            o.writeframes(seg.tobytes())
        ws, _ = vedit.whisper_words(clip, "tl", prompt="Verbatim, kasama ang bawat ulit at utal.")
        print(f"== {a:.2f}–{b:.2f}")
        print("   W " + "  ".join(f"{w.strip()}@{a + s:.2f}" for w, s, e, p in ws))
        print("   M " + "  ".join(f"{w}@{a + s:.2f}" for w, s in mms_words(seg.astype(np.float32) / 32768)))
    wav.unlink(missing_ok=True)
    clip.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
