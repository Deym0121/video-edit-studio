"""Assemble a story A-roll from several source videos by WORD INDEX (each source must be transcribed first).

spec JSON: [{"src": "input/x.mov", "from": 12, "to": 23, "label": "..."}, ...] — inclusive word ranges.
Each piece is cut with small handles at real word edges, normalised to 1080×1920 30 fps SDR BT.709, 48 kHz mono,
loudness-matched (testimonials are recorded at very different levels), then concatenated. HDR (HLG) sources are
colour-space converted without a tone curve (Lloyd: no "grading" look). Writes the output + a pieces map json.
usage: tools/assemble.py spec.json out.mov"""
import json
import subprocess as sp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vedit  # noqa: E402

HEAD, TAIL = 0.14, 0.34


def piece_filter(src, trc):
    cs = "zscale=tin=bt709:min=bt2020nc:pin=bt2020:rin=tv:t=bt709:m=bt709:p=bt709:r=tv," if trc == "arib-std-b67" else ""
    return (f"{cs}scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
            "fps=30,setsar=1,format=yuv420p")


def main():
    spec, out = json.load(open(sys.argv[1])), Path(sys.argv[2])
    tmp = out.parent / (out.stem + "_pieces")
    tmp.mkdir(exist_ok=True)
    ff = vedit.binpath("ffmpeg")
    files, pmap = [], []
    for k, p in enumerate(spec):
        f = tmp / f"{k:02d}.mov"
        if p.get("gap"):  # breathing room for a bridge card: warm near-black + silence (music + card fill it)
            g = float(p["gap"])
            sp.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x0C0908:s=1080x1920:r=30:d={g}",
                    "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={g}", "-shortest", "-c:v", "libx264", "-preset",
                    "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709", str(f)], check=True)
            files.append((f, g, p))
            pmap.append(dict(k=k, label=p.get("label", "gap"), gap=g))
            print(f"• {k:02d} {'— gap ' + p.get('label', ''):<28} {g:.1f}s", flush=True)
            continue
        src = vedit.ROOT / p["src"]
        wd = vedit.WORK / src.stem
        words = vedit.jload(wd / "transcript.json")["words"]
        meta = vedit.probe(src)
        # a crossfade eats x seconds at both sides of the join → grow the handles so only room tone overlaps, never words
        x_in = float(p.get("xfade", 0))
        x_out = float(spec[k + 1].get("xfade", 0)) if k + 1 < len(spec) else 0.0
        prv = words[p["from"] - 1]["e"] if p["from"] > 0 else 0.0
        a = max(0.0, words[p["from"]]["s"] - p.get("head", HEAD) - x_in, min(words[p["from"]]["s"] - p.get("head", HEAD), prv + 0.04))
        nxt = words[p["to"] + 1]["s"] if p["to"] + 1 < len(words) else meta["dur"]
        b = min(meta["dur"], words[p["to"]]["e"] + p.get("tail", TAIL) + x_out,
                meta["dur"] if p.get("hold") else max(words[p["to"]]["e"] + p.get("tail", TAIL), nxt - 0.04))
        sp.run([ff, "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
                "-vf", piece_filter(src, meta.get("trc")),
                "-af", "aresample=48000,aformat=channel_layouts=mono,highpass=f=70,loudnorm=I=-18:TP=-2:LRA=9,"
                       f"afade=t=in:d=0.03,afade=t=out:st={max(0, b - a - 0.05):.3f}:d=0.05",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le", "-ar", "48000",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(f)], check=True)
        d = vedit.probe(f)["dur"]
        files.append((f, d, p))
        pmap.append(dict(k=k, label=p.get("label", ""), src=p["src"], src_from=round(a, 3), src_to=round(b, 3),
                         dur=round(d, 3), speaker=p.get("speaker", "")))
        print(f"• {k:02d} {p.get('label', ''):<28} {vedit.tc(a)}–{vedit.tc(b)} ({d:.1f}s)", flush=True)
    # join: crossfade (video dissolve + audio crossfade) where a piece asks for "xfade", plain concat elsewhere
    args, fl = [], []
    for f, _, _ in files:
        args += ["-i", str(f)]
    for i in range(len(files)):  # same timebase/format on every input, or xfade refuses to link
        fl.append(f"[{i}:v]setpts=PTS-STARTPTS,fps=30,format=yuv420p,settb=AVTB[n{i}];[{i}:a]asetpts=PTS-STARTPTS,aresample=48000[m{i}]")
    vcur, acur, L = "[n0]", "[m0]", files[0][1]
    pmap[0]["at"] = 0.0
    for i in range(1, len(files)):
        d, p = files[i][1], files[i][2]
        x = float(p.get("xfade", 0))
        if x > 0:
            fl.append(f"{vcur}[n{i}]xfade=transition=fade:duration={x}:offset={L - x:.4f}[v{i}]")
            fl.append(f"{acur}[m{i}]acrossfade=d={x}:c1=tri:c2=tri[a{i}]")
            pmap[i]["at"] = round(L - x, 3)
            L += d - x
        else:
            fl.append(f"{vcur}{acur}[n{i}][m{i}]concat=n=2:v=1:a=1[v{i}][a{i}]")
            pmap[i]["at"] = round(L, 3)
            L += d
        vcur, acur = f"[v{i}]", f"[a{i}]"
    script = tmp / "join.txt"
    script.write_text(";\n".join(fl))
    sp.run([ff, "-v", "error", "-y", *args, "-/filter_complex", str(script), "-map", vcur, "-map", acur,
            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", str(out)], check=True)
    json.dump(pmap, open(out.with_suffix(".pieces.json"), "w"), indent=1, ensure_ascii=False)
    print(f"✓ {out} ({L:.1f}s, {len(spec)} pieces)")


if __name__ == "__main__":
    main()
