import json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

LINES = [
    ("hook",  "This is Earth. Now let's zoom out. Wait for the last one."),
    ("sun",   "The Sun. Over a million Earths could fit inside it."),
    ("solar", "Our solar system. Light takes four hours just to reach Neptune."),
    ("milky", "The Milky Way. Hundreds of billions of stars, and the Sun is just one."),
    ("lani",  "Our supercluster, Laniakea. A hundred thousand galaxies."),
    ("obs",   "And the observable universe. Ninety-three billion light-years across, with hundreds of billions of galaxies."),
    ("end",   "And that's only the part we can see. Still feel big?"),
]

k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
info = {}
for key, text in LINES:
    s, sr = k.create(text, voice="am_michael", speed=1.08, lang="en-us")
    s = np.asarray(s, dtype=np.float32)
    # trim leading/trailing silence
    env = np.abs(s) > 0.01
    idx = np.where(env)[0]
    a = max(0, idx[0] - int(0.02 * sr)); b = min(len(s), idx[-1] + int(0.06 * sr))
    s = s[a:b]
    sf.write(f"vo_{key}.wav", s, sr)
    info[key] = {"text": text, "dur": len(s) / sr, "sr": sr}
    print(key, round(len(s) / sr, 2))
json.dump(info, open("vo.json", "w"), indent=1)
print("total", round(sum(v["dur"] for v in info.values()), 2))
