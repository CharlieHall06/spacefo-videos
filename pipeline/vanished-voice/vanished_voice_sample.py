"""Two short narrator samples for The Vanished Files, with a 'human / Yeti mic' treatment:
sentence-by-sentence delivery with small speed and pause variations, then EQ, gentle
compression, a small-room reflection and a faint room-tone noise floor (done in ffmpeg)."""
import numpy as np, soundfile as sf, subprocess, random
from kokoro_onnx import Kokoro

LINES = [
    "In eighteen seventy-two, a ship was found drifting in the middle of the Atlantic.",
    "Her sails were set.",
    "Her cargo was untouched.",
    "There was still food on board, and fresh water.",
    "But every single person... was gone.",
]
VOICES = [("A_british", "bm_george", "en-gb", 0.96), ("B_american_deep", "am_onyx", "en-us", 0.97)]

k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
for tag, voice, lang, base in VOICES:
    rnd = random.Random(7)
    parts = []
    sr = 24000
    for i, line in enumerate(LINES):
        sp = base * rnd.uniform(0.96, 1.03)
        s, sr = k.create(line, voice=voice, speed=sp, lang=lang)
        s = np.asarray(s, np.float32)
        idx = np.where(np.abs(s) > 0.008)[0]
        s = s[max(0, idx[0] - 240): idx[-1] + 1200]
        parts.append(s)
        gap = rnd.uniform(0.32, 0.55) if i < len(LINES) - 1 else 0.6
        if i == len(LINES) - 2:
            gap += 0.25  # let the last line land
        parts.append(np.zeros(int(gap * sr), np.float32))
    raw = np.concatenate([np.zeros(int(0.25 * sr), np.float32)] + parts)
    sf.write(f"vf_raw_{tag}.wav", raw, sr)
    dur = len(raw) / sr
    chain = (
        "[0:a]aresample=48000,highpass=f=70,"
        "equalizer=f=170:t=q:w=1.0:g=2.5,equalizer=f=3400:t=q:w=1.2:g=1.2,equalizer=f=8000:t=q:w=1.5:g=-2.5,"
        "acompressor=threshold=-22dB:ratio=2.4:attack=8:release=140:makeup=2,"
        "aecho=0.85:0.55:17|29:0.14|0.09[v];"
        f"anoisesrc=color=pink:amplitude=0.0022:sample_rate=48000:duration={dur + 0.5:.2f},lowpass=f=6000,highpass=f=120[n];"
        "[v][n]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    )
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"vf_raw_{tag}.wav",
                    "-filter_complex", chain, "-map", "[out]", "-c:a", "aac", "-b:a", "160k",
                    f"vanished_voice_{tag}.m4a"], check=True)
    print(tag, round(dur, 2), "s")
