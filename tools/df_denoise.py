"""DeepFilterNet3 speech enhancement (run with .venv-df/bin/python): 48 kHz mono 16-bit in.wav → out.wav, voice only.
usage: .venv-df/bin/python tools/df_denoise.py in.wav out.wav [atten_lim_db]"""
import sys
import warnings
import wave

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import torch  # noqa: E402
from df.enhance import enhance, init_df  # noqa: E402

src, dst = sys.argv[1], sys.argv[2]
lim = float(sys.argv[3]) if len(sys.argv) > 3 else None  # None = remove as much noise as the model can
model, state, _ = init_df(log_level="ERROR")
with wave.open(src) as w:
    assert w.getframerate() == state.sr() and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 48k mono s16 wav"
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
out = enhance(model, state, torch.from_numpy(x)[None], atten_lim_db=lim)[0].numpy()
with wave.open(dst, "wb") as w:
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(state.sr())
    w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
print("ok")
