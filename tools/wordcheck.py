#!/usr/bin/env python3
"""wordcheck — find words the viewer should hear but doesn't (clipped/missing), by aligning the planned
script (kept transcript words) with the literal MMS transcript of the edited audio (literal.json).

Usage: wordcheck.py VIDEO   (run tools/literal.py VIDEO first)
Prints expected words with no literal counterpart, with their edited time, grouped into spots.
"""
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vedit  # noqa: E402

FILLER = {"na", "ng", "sa", "ang", "ay", "po", "ka", "mo", "ko", "o", "at", "yung", "ba", "si", "ni", "so", "a", "i"}


def phon(w):
    w = re.sub(r"[^a-z0-9]", "", w.lower())
    for a, b in (("ph", "f"), ("c", "k"), ("q", "k"), ("v", "b"), ("z", "s"), ("x", "ks"), ("e", "i"), ("o", "u"), ("y", "i"), ("j", "h")):
        w = w.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", w)


def main():
    src, wd, meta = vedit.ctx(sys.argv[1])
    edl = vedit.jload(wd / "edl.json")
    words = vedit.jload(wd / "transcript.json")["words"]
    fixes = vedit.jload(wd / "decisions.json", {}).get("fixes", {})
    exp = []
    for k, s, e in edl["words_out"]:
        for part in vedit.fixed_text(words, fixes, k).replace("-", " ").split():
            if phon(part):
                exp.append((part, s))
    lit = [(w["w"], w["t"]) for w in vedit.jload(wd / "literal.json")]
    A = [phon(w) for w, _ in exp]
    B = [phon(w) for w, _ in lit]
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    miss = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        got = "".join(B[j1:j2])
        for i in range(i1, i2):
            # tolerate merged/split spellings: the expected word appears inside the literal chunk
            if A[i] and (A[i] in got or difflib.SequenceMatcher(None, A[i], got).ratio() > 0.6):
                continue
            miss.append((exp[i][1], exp[i][0], " ".join(w for w, _ in lit[j1:j2])))
    shown = [m for m in miss if vedit.norm(m[1]) not in FILLER]
    for t, w, heard in shown:
        print(f"{vedit.tc(t)}  expected “{w}”  · literal heard: {heard or '—'}")
    print(f"✓ {len(shown)} content words not clearly heard (of {len(exp)})")


if __name__ == "__main__":
    main()
