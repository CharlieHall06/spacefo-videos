"""Voiceover for 'Percy Fawcett – the last letter' (The Vanished Files, Case file format).
bm_george, one sentence at a time with small speed/pause variation, then the 'Yeti mic' chain.
Writes vo.wav (processed, 48 kHz) and vo.json (scene + word timings). Run in the build dir."""
import json, random, subprocess, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

M = "/home/claude/build/models/"
# pronunciation fixes for the TTS only (captions keep the real spelling; same word count)
SAY = {"Rimell": "Rimmel"}
# scene key, [sentences], extra pause after scene
SCENES = [
    ("hook",   ["He went into the Amazon to find a lost city, and never came back."], 0.4),
    ("camp",   ["May twenty-ninth, nineteen twenty-five.", "Percy Fawcett sends his guides home from Dead Horse Camp."], 0.3),
    ("party",  ["With him: his son Jack, and Jack's friend Raleigh Rimell."], 0.35),
    ("letter", ["His last letter to his wife: you need have no fear of any failure."], 0.45),
    ("coords", ["But that letter puts the camp at eleven degrees south.", "His report to the papers says thirteen."], 0.45),
    ("why",    ["A typo?", "Or a false trail?"], 0.4),
    ("bones",  ["In nineteen fifty-one, bones said to be his turn up.", "Tests say they're not him."], 0.4),
    ("theory", ["Theory: hunger or fever.", "Theory: killed in the jungle."], 0.35),
    ("end",    ["None of them was ever found.", "Still unsolved.", "What do you think happened?"], 0.0),
]
k = Kokoro(M + "kokoro-v1.0.onnx", M + "voices-v1.0.bin")
rnd = random.Random(1925)
SR = 24000
import sys
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 1.12
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
        sp = SPEED * rnd.uniform(0.97, 1.03)
        if s.startswith("Theory") or s.startswith("His report") or s == "A typo?":
            sp *= 0.95
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
