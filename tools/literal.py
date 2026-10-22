#!/usr/bin/env python3
"""literal — letter-by-letter transcript of the EDITED audio with Meta MMS (CTC, Tagalog).

Unlike Whisper, a CTC model has no language model smoothing the output, so a word said
twice comes out twice ("tapos tapos", "auto automation"). Used to find the doubles the
viewer hears.

Usage: literal.py VIDEO [--raw]  → work/<name>/literal.txt + literal.json
       --raw listens to the whole original audio (before any cut) → literal_raw.txt / .json
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

MODEL = "facebook/mms-1b-all"
SR, CHUNK, PAD = 16000, 20.0, 1.5  # seconds
PARTICLES = {"na", "ng", "sa", "ay", "po", "ka", "mo", "ko", "si", "ni", "at", "o", "a", "i", "e"}


def main():
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    src, wd, meta = vedit.ctx(sys.argv[1])
    raw = "--raw" in sys.argv
    segs = [[0.0, meta["dur"]]] if raw else (lambda e: (e.get("hook_segs") or []) + e["segments"])(vedit.jload(wd / "edl.json"))
    tag = "_raw" if raw else ""
    offs, o = [], 0.0
    for a, b in segs:
        offs.append(o)
        o += b - a
    to_src = lambda t: next((a + (t - of) for (a, b), of in zip(segs, offs) if of <= t < of + (b - a)), segs[-1][1])
    with wave.open(str(wd / "audio.wav")) as f:
        full = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    x = np.concatenate([full[int(a * SR):int(b * SR)] for a, b in segs])
    total = len(x) / SR

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(MODEL, target_lang="tgl")
    model = Wav2Vec2ForCTC.from_pretrained(MODEL, target_lang="tgl", ignore_mismatched_sizes=True)
    model.load_adapter("tgl")
    model.to(dev).eval()
    vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
    blank = proc.tokenizer.pad_token_id
    delim = proc.tokenizer.convert_tokens_to_ids("|")

    words = []
    t = 0.0
    while t < total:
        a, b = max(0.0, t - PAD), min(total, t + CHUNK + PAD)
        print(f"\r• literal listening {vedit.tc(t)} / {vedit.tc(total)}", end="", flush=True)
        inp = proc(x[int(a * SR):int(b * SR)], sampling_rate=SR, return_tensors="pt").to(dev)
        with torch.no_grad():
            ids = model(**inp).logits[0].argmax(-1).cpu().numpy()
        stride = (b - a) / len(ids)
        chunk_words = []
        cur, w0, last, prev = "", None, None, None
        for fi, tok in enumerate(ids):
            if tok != prev and tok != blank:
                if tok == delim:
                    if cur:
                        chunk_words.append((cur, a + w0 * stride, a + (last + 1) * stride))
                    cur, w0 = "", None
                else:
                    if w0 is None:
                        w0 = fi
                    cur += vocab.get(int(tok), "")
                    last = fi
            prev = tok
        if cur:
            chunk_words.append((cur, a + w0 * stride, a + (last + 1) * stride))
        # keep only words that start in this chunk's core [t, t+CHUNK) — the pads are just context
        words += [w for w in chunk_words if t <= w[1] < t + CHUNK]
        t += CHUNK
    print()
    # dedupe overlap regions: keep words in each chunk's core
    core = []
    for w, s, e in sorted(words, key=lambda z: z[1]):
        if core and abs(s - core[-1][1]) < 0.12 and w == core[-1][0]:
            continue
        core.append((w, s, e))
    out = [dict(w=w, t=round(s, 2), e=round(e, 2), src=round(to_src(s), 2), flags=[]) for w, s, e in core]
    n = [vedit.norm(w["w"]) for w in out]
    for j in range(1, len(out)):
        for g in (4, 3, 2, 1):
            a = j - 2 * g + 1
            if a < 0:
                continue
            if all(n[a + q] and n[a + q] == n[a + g + q] for q in range(g)) and out[j]["t"] - out[a]["t"] < 3.5:
                if g == 1 and n[j] in PARTICLES:
                    break
                for q in range(a, j + 1):
                    out[q]["flags"].append("DBL")
                break
        # partial repeat: a short fragment that is the start of the next word ("auto automation", "ta tapos")
        if 2 <= len(n[j - 1]) < len(n[j]) and n[j].startswith(n[j - 1]) and out[j]["t"] - out[j - 1]["e"] < 0.8:
            out[j - 1]["flags"].append("FRAG")
    vedit.jsave(wd / f"literal{tag}.json", out)
    lines, cur = [f"# Literal (MMS) transcript of the edited audio — {vedit.tc(total)}, {len(out)} words",
                  "# [[word·DBL]] said twice · [[word·FRAG]] cut-off start of the next word", ""], []
    for w in out:
        if not cur:
            st = w
        tag = "/".join(dict.fromkeys(w["flags"]))
        cur.append(f"[[{w['w']}·{tag}]]" if tag else w["w"])
        if len(cur) >= 14:
            lines.append(f"{vedit.tc(st['t']):>8} ({vedit.tc(st['src'])})  " + " ".join(cur))
            cur = []
    if cur:
        lines.append(f"{vedit.tc(st['t']):>8} ({vedit.tc(st['src'])})  " + " ".join(cur))
    (wd / f"literal{tag}.txt").write_text("\n".join(lines) + "\n")
    print(f"✓ {len(out)} words · {sum('DBL' in w['flags'] for w in out)} DBL · "
          f"{sum('FRAG' in w['flags'] for w in out)} FRAG → {(wd / f'literal{tag}.txt').relative_to(vedit.ROOT)}")


if __name__ == "__main__":
    main()
