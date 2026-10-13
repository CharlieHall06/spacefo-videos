"""Voiceover for 'Flight 19 – the last hours' (The Vanished Files).
bm_george, one sentence at a time with small speed/pause variation, then the 'Yeti mic' chain.
Writes vo.wav (processed, 48 kHz) and vo.json (scene + word timings)."""
import json, random, subprocess, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

M = "/home/claude/build/models/"
# scene key, [sentences], extra pause after scene
SCENES = [
    ("takeoff", ["December fifth, nineteen forty-five.", "Five Navy bombers leave Florida on a training flight, fourteen men on board."], 0.35),
    ("compass", ["Three forty.", "The leader radios: both my compasses are out."], 0.3),
    ("keys",    ["He's sure they're over the Florida Keys.", "They're not."], 0.42),
    ("sunset",  ["Sunset.", "The sea turns rough, and fuel is running low."], 0.35),
    ("ditch",   ["Seven oh four.", "The last words heard:", "we'll have to ditch."], 0.5),
    ("rescue",  ["A flying boat with thirteen men goes to find them."], 0.25),
    ("flames",  ["Twenty minutes later, a tanker sees a burst of flames."], 0.6),
    ("gone",    ["Twenty-seven men.", "Six aircraft.", "No wreckage ever found."], 0.4),
    ("end",     ["The cause is still unknown.", "What do you think happened?"], 0.0),
]
k = Kokoro(M + "kokoro-v1.0.onnx", M + "voices-v1.0.bin")
rnd = random.Random(19)
SR = 24000
lead = 0.30
parts = [np.zeros(int(lead * SR), np.float32)]
t = lead
info = []
for key, sents, tail in SCENES:
    sc = {"key": key, "start": t, "words": []}
    for i, s in enumerate(sents):
        sp = 1.03 * rnd.uniform(0.97, 1.03)
        a, sr = k.create(s, voice="bm_george", speed=sp, lang="en-gb")
        a = np.asarray(a, np.float32)
        idx = np.where(np.abs(a) > 0.008)[0]
        a = a[max(0, idx[0] - 240): idx[-1] + 1200]
        d = len(a) / SR
        # word timings ~ proportional to letters (+ small constant per word)
        ws = s.split()
        wt = np.array([len(w.strip(".,:?'")) + 2.5 for w in ws], float)
        cum = np.concatenate([[0], np.cumsum(wt)]) / wt.sum() * (d - 0.08)
        for w, c in zip(ws, cum[:-1]):
            sc["words"].append([w, round(t + 0.04 + c, 3)])
        parts.append(a); t += d
        gap = rnd.uniform(0.2, 0.34) if i < len(sents) - 1 else tail
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
