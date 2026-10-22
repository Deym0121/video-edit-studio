# Third-party notices

The code in this repository is MIT-licensed (see `LICENSE`). Other people's work ships with it, or is downloaded by
the installer. Each piece keeps its own license.

## Bundled in this repository: fonts

Every font sits in `assets/fonts/`, `motion/fonts/` and `docs/tutorial/hf/fonts/`, under the **SIL Open Font License 1.1**.
The license text is in `OFL.txt` next to each copy.

| Font | Copyright |
|---|---|
| Anton | Copyright 2020 The Anton Project Authors (https://github.com/googlefonts/AntonFont) |
| Caveat | Copyright 2014 The Caveat Project Authors (https://github.com/googlefonts/caveat) |
| Dancing Script | Copyright 2016 The Dancing Script Project Authors (https://github.com/googlefonts/DancingScript), with Reserved Font Name "Dancing Script" |
| Great Vibes | Copyright 2010 The Great Vibes Pro Project Authors (https://github.com/googlefonts/great-vibes) |
| Inter Tight | Copyright 2022 The Inter Project Authors (https://github.com/rsms/inter-tight) |
| Montserrat | Copyright 2011 The Montserrat Project Authors (https://github.com/JulietaUla/Montserrat) |
| Playfair Display | Copyright 2017 The Playfair Display Project Authors (https://github.com/clauseggers/Playfair-Display), with Reserved Font Name "Playfair Display" |
| Poppins | Copyright 2020 The Poppins Project Authors (https://github.com/itfoundry/Poppins) |

## Downloaded by `tools/setup.sh` / `tools/setup.ps1`: not in this repository

The installer fetches these into this folder. Check each license before you use them in your own work.

| Component | Where it comes from | Note |
|---|---|---|
| Python packages | `tools/requirements.txt` (mlx-whisper or faster-whisper, static-ffmpeg, numpy, pillow, fonttools, scipy, noisereduce, torch, transformers, accelerate, huggingface_hub; on Windows also opencv-python, rapidocr-onnxruntime, torchvision) | Each under its own license |
| uv + Python 3.12 (Windows) | github.com/astral-sh/uv, python-build-standalone | Installs the Python env inside `tools/` |
| ffmpeg / ffprobe | the `static-ffmpeg` package (Mac); BtbN/FFmpeg-Builds win64-gpl (Windows) | ffmpeg is LGPL/GPL, depending on the build |
| Whisper large-v3-turbo | `mlx-community/whisper-large-v3-turbo` (Mac) or the faster-whisper build (Windows) on Hugging Face | Transcription |
| DeepLabV3 MobileNetV3 weights (Windows) | torchvision (PyTorch) | Person cut-out for "text behind you" |
| RapidOCR models (Windows) | the `rapidocr-onnxruntime` package | Text finder for style references |
| MMS (`facebook/mms-1b-all`) | Hugging Face | **CC BY-NC 4.0: non-commercial use only.** It powers the letter-by-letter repeat check; `./tools/setup.sh --lite` skips it |
| DeepFilterNet 3 | the `deepfilternet` package (+ torch / torchaudio) | Voice cleanup; skipped with `--lite` |
| Node.js | nodejs.org | The motion-graphics renderer's runtime |
| HyperFrames | npm, run with `npx hyperframes` | Renders the HTML motion graphics to video |
| GSAP | loaded from the jsDelivr CDN by the motion-graphics pages | Animation library |

The Swift tools in `tools/*.swift` use Apple's Vision and AVFoundation frameworks, which ship with macOS. On Windows their Python twins
(`tools/facebox.py`, `textbox.py`, `personmask.py`) use OpenCV, RapidOCR and torchvision instead.

## Not included

Music and the screenshots or clips you use in your edits stay on your computer. `assets/music/` and `motion/clips/` are kept
out of git because most licenses don't allow sharing those files.
