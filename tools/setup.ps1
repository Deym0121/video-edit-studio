# One-time setup - Windows 10 / 11 (64-bit). The twin of tools/setup.sh for the Mac.
# Everything installs INSIDE this folder (.venv, .venv-df, tools\uv, tools\python, tools\node; models go to the
# usual user cache): nothing system-wide, no admin. Safe to re-run: finished steps are skipped.
#
#   powershell -ExecutionPolicy Bypass -File tools\setup.ps1            full install (about 8 GB with the models)
#   powershell -ExecutionPolicy Bypass -File tools\setup.ps1 -Lite      skip the voice-cleanup env and the MMS model
#   powershell -ExecutionPolicy Bypass -File tools\setup.ps1 -NoModels  skip the model downloads (they load on first use)
param([switch]$Lite, [switch]$NoModels)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Invoke-WebRequest crawls with the progress bar on
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = "1"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\tools\python"

function Say($m) { Write-Host "`n* $m" -ForegroundColor Yellow }
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }
function Fetch($url, $zip, $into) {
  Invoke-WebRequest -UseBasicParsing $url -OutFile $zip
  Expand-Archive -Force $zip $into
  Remove-Item $zip
}

if (-not [Environment]::Is64BitOperatingSystem) { throw "Needs 64-bit Windows 10 or 11." }

Say "uv (Python installer, a private copy in tools\uv)"
$UV = "tools\uv\uv.exe"
if (-not (Test-Path $UV)) {
  Fetch "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" "tools\uv.zip" "tools\uv"
}

Say "Python env (.venv, 3.12)"
$PY = ".venv\Scripts\python.exe"
if (-not (Test-Path $PY)) { & $UV venv --python 3.12 .venv; Check "uv" }
& $UV pip install --python $PY -r tools\requirements.txt; Check "uv"

Say "ffmpeg"
& $PY -c "import static_ffmpeg; static_ffmpeg.add_paths()"; Check "python"

if (-not $Lite) {
  Say "Voice cleanup env (.venv-df: DeepFilterNet3 removes fans / aircon)"
  try {
    if (-not (Test-Path .venv-df\Scripts\python.exe)) { & $UV venv --python 3.11 .venv-df; Check "uv" }
    & $UV pip install --python .venv-df\Scripts\python.exe "torch==2.2.2" "torchaudio==2.2.2" "deepfilternet==0.5.6" "numpy==1.26.4"; Check "uv"
  } catch {
    Write-Host "  ! skipped ($_) - the lighter noise filter is used instead" -ForegroundColor DarkYellow
    if (Test-Path .venv-df) { Remove-Item -Recurse -Force .venv-df }
  }
}

Say "Node (motion-graphics renderer - a private copy in tools\node)"
if (-not (Test-Path tools\node\node.exe)) {
  $V = "v22.12.0"
  Fetch "https://nodejs.org/dist/$V/node-$V-win-x64.zip" "tools\node.zip" "tools"
  Rename-Item "tools\node-$V-win-x64" node
}

Say "Finders (the Windows twins of the Apple tools): face finder, text finder, person cut-out"
& $PY -c "import cv2, rapidocr_onnxruntime; print('  OK face finder (OpenCV) + text finder (RapidOCR)')"; Check "python"
& $PY -c "from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large as m, DeepLabV3_MobileNet_V3_Large_Weights as W; m(weights=W.DEFAULT); print('  OK person cut-out (DeepLabV3)')"; Check "python"

if (-not $NoModels) {
  $msg = "Models (first time only - Whisper about 1.6 GB"
  if (-not $Lite) { $msg += ", MMS about 4 GB" }
  Say "$msg)"
  & $PY -c "import os; from faster_whisper import download_model; download_model(os.environ.get('VEDIT_WHISPER', 'large-v3-turbo'))"; Check "python"
  if (-not $Lite) { & $PY -c "from huggingface_hub import snapshot_download as s; s('facebook/mms-1b-all')"; Check "python" }
}

Say "Studio graphics library"
& $PY tools\mograph.py --gallery | Out-Null; Check "python"
Write-Host "  OK $((Get-ChildItem motion\scenes\gal_*.html).Count) live samples"

& .\vedit.cmd doctor
Write-Host "`nDone. Start the Studio:  .\vedit.cmd studio   ->  http://localhost:8765" -ForegroundColor Green
