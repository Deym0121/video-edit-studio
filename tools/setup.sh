#!/bin/bash
# One-time setup — macOS on Apple Silicon. Everything installs INSIDE this folder (.venv, .venv-df, tools/node,
# tools/bin, model cache): nothing system-wide, no password. Safe to re-run: finished steps are skipped.
#
#   ./tools/setup.sh            full install (≈ 8 GB with the models)
#   ./tools/setup.sh --lite     skip the voice-cleanup env and the MMS model (smaller, fewer QC checks)
set -e
cd "$(dirname "$0")/.."
LITE=0; [ "$1" = "--lite" ] && LITE=1
say() { printf "\n\033[1;33m• %s\033[0m\n" "$1"; }
[ "$(uname -s)" = Darwin ] || { echo "✗ macOS only for now (Apple Vision cut-outs + MLX Whisper)."; exit 1; }
[ "$(uname -m)" = arm64 ] || echo "⚠ Intel Mac: transcription falls back to faster-whisper and runs slower."

say "uv (Python installer)"
UV=$(command -v uv || true)
if [ -z "$UV" ]; then
  python3 -m pip install --user --quiet uv
  UV=$(python3 -c 'import site,os;print(os.path.join(site.USER_BASE,"bin","uv"))')
fi

say "Python env (.venv, 3.12)"
[ -x .venv/bin/python ] || "$UV" venv --python 3.12 .venv
"$UV" pip install --python .venv/bin/python -r tools/requirements.txt

say "ffmpeg"
.venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"

if [ $LITE = 0 ]; then
  say "Voice cleanup env (.venv-df: DeepFilterNet3 removes fans / aircon)"
  [ -x .venv-df/bin/python ] || "$UV" venv --python 3.11 .venv-df
  "$UV" pip install --python .venv-df/bin/python "torch==2.2.2" "torchaudio==2.2.2" "deepfilternet==0.5.6" "numpy==1.26.4"
fi

say "Node (motion-graphics renderer — a private copy in tools/node)"
if [ ! -x tools/node/bin/node ]; then
  V=v22.12.0
  curl -fsSL "https://nodejs.org/dist/$V/node-$V-darwin-arm64.tar.gz" | tar -xz -C tools
  mv "tools/node-$V-darwin-arm64" tools/node
fi

say "Apple tools (Swift): person cut-out · natural colour from iPhone HDR · face finder · text finder"
xcode-select -p >/dev/null 2>&1 || { echo "✗ Needs the Xcode Command Line Tools — run: xcode-select --install   (then run this again)"; exit 1; }
mkdir -p tools/bin
build() {  # the newest SDK can be ahead of the installed swiftc — try them newest → oldest
  for sdk in $(ls -d /Library/Developer/CommandLineTools/SDKs/MacOSX[0-9]*.sdk \
               /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX*.sdk 2>/dev/null | sort -rV); do
    swiftc -O -sdk "$sdk" "tools/$1.swift" -o "tools/bin/$1" 2>/dev/null && { echo "  ✓ $1"; return 0; }
  done
  echo "  ✗ could not build $1"; return 1
}
for t in personmask tosdr facebox textbox; do [ -x "tools/bin/$t" ] || build "$t"; done

say "Models (first time only — Whisper ≈ 1.6 GB$( [ $LITE = 0 ] && echo ', MMS ≈ 4 GB'))"
.venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('mlx-community/whisper-large-v3-turbo')"
if [ $LITE = 0 ]; then .venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('facebook/mms-1b-all')"; fi

say "Studio graphics library"
.venv/bin/python tools/mograph.py --gallery >/dev/null && echo "  ✓ $(ls motion/scenes/gal_*.html | wc -l | tr -d ' ') live samples"

./vedit doctor
printf "\n\033[1;32mDone.\033[0m Start the Studio:  .venv/bin/python tools/editor/server.py   →  http://localhost:8765\n"
