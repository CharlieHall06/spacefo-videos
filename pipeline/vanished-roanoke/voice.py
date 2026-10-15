"""Voiceover for 'Roanoke – one word left behind' (The Vanished Files, One detail format).
bm_george, one sentence at a time with small speed/pause variation, then the 'Yeti mic' chain.
Writes vo.wav (processed, 48 kHz) and vo.json (scene + word timings). Run in the build dir."""
import json, random, subprocess, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

M = "/home/claude/build/models/"
# pronunciation fixes for the TTS only (captions keep the real spelling; same word count)
SAY = {"Roanoke": "Rowanoke"}
# scene key, [sentences], extra pause after scene
SCENES = [
    ("sail",    ["In fifteen ninety, John White sails back to his colony on Roanoke Island."], 0.3),
    ("waited",  ["More than a hundred settlers were waiting for him."], 0.35),
    ("gone",    ["Every one of them is gone.", "No sign of a fight."], 0.4),
    ("word",    ["Just one word, carved into a post of the fort."], 0.65),
    ("reveal",  ["Croatoan."], 0.5),
    ("signal",  ["They'd agreed a signal:", "if they were ever forced out, carve a cross."], 0.45),
    ("nocross", ["There's no cross."], 0.55),
    ("island",  ["Croatoan was a friendly island to the south.", "A storm stops White ever getting there."], 0.4),
    ("end",     ["It's still unsolved.", "Where do you think they went?"], 0.0),
]
k = Kokoro(M + "kokoro-v1.0.onnx", M + "voices-v1.0.bin")
rnd = random.Random(1590)
SR = 24000
lead = 0.25
parts = [np.zeros(int(lead * SR), np.float32)]
t = lead
info = []
for key, sents, tail in SCENES:
    sc = {"key": key, "start": t, "words": []}
    for i, s in enumerate(sents):
        spoken = s
        for a_, b_ in SAY.items():
            spoken = spoken.replace(a_, b_)
        sp = 1.05 * rnd.uniform(0.97, 1.03)
        if key == "reveal":
            sp = 0.88
        a, sr = k.create(spoken, voice="bm_george", speed=sp, lang="en-gb")
        a = np.asarray(a, np.float32)
        idx = np.where(np.abs(a) > 0.008)[0]
        a = a[max(0, idx[0] - 240): idx[-1] + 1200]
        d = len(a) / SR
        ws = s.split()
        wt = np.array([len(w.strip(".,:?'")) + 2.5 for w in ws], float)
        cum = np.concatenate([[0], np.cumsum(wt)]) / wt.sum() * (d - 0.08)
        for w, c in zip(ws, cum[:-1]):
            sc["words"].append([w, round(t + 0.04 + c, 3)])
        parts.append(a); t += d
        gap = rnd.uniform(0.3, 0.42) if i < len(sents) - 1 else tail
        parts.append(np.zeros(int(gap * SR), np.float32)); t += gap
    sc["end"] = t - tail
    info.append(sc)
raw = np.concatenate(parts)
sf.write("vo_raw.wav", raw, SR)
dur = len(raw) / SR
chain = ("[0:a]aresample=48000,highpass=f=70,"
         "equalizer=f=170:t=q:w=1.0:g=2.5,equalizer=f=3400:t=q:w=1.2:g=1.2,equalizer=f=8000:t=q:w=1.5:g=-2.5,"
         "acompressor=threshold=-22dB:ratio=2.4:attack=8:release=140:makeup=2,"
         "aecho=0.85:0.55:17|29:0.14|0.09[v];"
         f"anoisesrc=color=pink:amplitude=0.0022:sample_rate=48000:duration={dur + 0.5:.2f},lowpass=f=6000,highpass=f=120[n];"
         "[v][n]amix=inputs=2:duration=first:normalize=0[out]")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "vo_raw.wav", "-filter_complex", chain,
                "-map", "[out]", "-ar", "48000", "vo.wav"], check=True)
json.dump({"dur": dur, "scenes": info}, open("vo.json", "w"), indent=1)
print("voice", round(dur, 2), "s;", sum(len(s.split()) for _, ss, _ in SCENES for s in ss), "words")
for sc in info:
    print(f'{sc["key"]:8s} {sc["start"]:6.2f} {sc["end"]:6.2f}')
