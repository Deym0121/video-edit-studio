#!/usr/bin/env python3
"""listen — re-transcribe short windows of the ORIGINAL audio, verbatim, to find hidden retakes and doubles.

Usage: listen.py VIDEO START-END [START-END ...] [--mms]   (seconds; --mms adds literal CTC words)
Prints Whisper words (no prompt, Tagalog, short window = no repeat-collapsing) with absolute times,
plus a compact energy strip (10 ms dB frames, one char per 50 ms: ' ' gate, '.' room, ':' soft, '#' voice).
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

SR = 16000


_mms = {}


def mms_words(x):
    """Literal (CTC) words with times for a 16 kHz float clip — keeps every repeat."""
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC
    if not _mms:
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        proc = AutoProcessor.from_pretrained("facebook/mms-1b-all", target_lang="tgl")
        m = Wav2Vec2ForCTC.from_pretrained("facebook/mms-1b-all", target_lang="tgl", ignore_mismatched_sizes=True)
        m.load_adapter("tgl")
        _mms.update(proc=proc, m=m.to(dev).eval(), dev=dev)
    proc, m = _mms["proc"], _mms["m"]
    with torch.no_grad():
        ids = m(**proc(x, sampling_rate=SR, return_tensors="pt").to(_mms["dev"])).logits[0].argmax(-1).cpu().numpy()
    vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
    blank, delim = proc.tokenizer.pad_token_id, proc.tokenizer.convert_tokens_to_ids("|")
    stride = len(x) / SR / len(ids)
    out, cur, w0, prev = [], "", None, None
    for fi, tok in enumerate(ids):
        if tok != prev and tok != blank:
            if tok == delim:
                if cur:
                    out.append((cur, w0 * stride))
                cur, w0 = "", None
            else:
                w0 = fi if w0 is None else w0
                cur += vocab.get(int(tok), "")
        prev = tok
    if cur:
        out.append((cur, w0 * stride))
    return out


def main():
    src, wd, meta = vedit.ctx(sys.argv[1])
    use_mms = "--mms" in sys.argv
    sys.argv = [v for v in sys.argv if v != "--mms"]
    db = np.load(wd / "energy.npy")
    with wave.open(str(wd / "audio.wav")) as f:
        x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    tmp = wd / "_listen.wav"
    for rng in sys.argv[2:]:
        a, b = (float(v) for v in rng.split("-"))
        with wave.open(str(tmp), "wb") as o:
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR)
            o.writeframes(x[int(a * SR):int(b * SR)].tobytes())
        ws, _ = vedit.whisper_words(tmp, "tl", prompt="Verbatim, kasama ang bawat ulit at utal.")
        print(f"== {a:.2f}–{b:.2f}")
        print("   W " + "  ".join(f"{w.strip()}@{a + s:.2f}" for w, s, e, p in ws))
        if use_mms:
            xf = x[int(a * SR):int(b * SR)].astype(np.float32) / 32768
            print("   M " + "  ".join(f"{w}@{a + s:.2f}" for w, s in mms_words(xf)))
        strip = ""
        for t in np.arange(a, b, 0.05):
            seg = db[int(t * 100):int(t * 100) + 5]
            v = seg.max() if len(seg) else -100
            strip += " " if v < -70 else "." if v < -42 else ":" if v < -28 else "#"
        for k in range(0, len(strip), 100):
            print(f"   {a + k * 0.05:7.2f} |{strip[k:k + 100]}|")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
