"""Original soundtrack + sound design + voice mix for 'Carroll A. Deering – the last sightings'.
Helpers adapted from pipeline/zoom-out/audio.py.  Run in the build dir after voice.py.  Writes mix_raw.wav."""
import json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 48000
VO = json.load(open("vo.json"))
SC = {s["key"]: s for s in VO["scenes"]}
ORDER = [s["key"] for s in VO["scenes"]]
CUT = {k: (0.0 if i == 0 else SC[k]["start"] - 0.12) for i, k in enumerate(ORDER)}
TOTAL = VO["dur"] + 0.7
N = int((TOTAL + 0.05) * SR)
rng = np.random.default_rng(1921)


def wt(key, word):
    return [t for w, t in SC[key]["words"] if w.strip(".,:?").lower() == word][0]


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "Eb": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "Bb": 1, "B": 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)


def filt(x, fc, kind):
    return sosfilt(butter(2, fc, kind, fs=SR, output="sos"), x, axis=0)


def env_ad(n, a, d):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR)); return e


def add(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    if sig.ndim == 1:
        sig = np.stack([sig * np.sqrt(0.5 * (1 - pan)) * 1.41, sig * np.sqrt(0.5 * (1 + pan)) * 1.41], 1)
    j = min(N, i + len(sig)); k0 = 0
    if i < 0:
        k0 = -i; i = 0
    buf[i:j] += sig[k0:k0 + (j - i)] * gain


def reverb(x, seconds=3.0, mix=0.35, seed=1):
    r = np.random.default_rng(seed); n = int(seconds * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = r.normal(0, 1, n) * np.exp(-t * 6.9 / seconds); ir = filt(ir, 5000, "low"); ir[: int(0.015 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch], len(x) + n) * np.fft.rfft(ir, len(x) + n))[: len(x)]
    return x * (1 - mix) + out * mix * 1.6


music = np.zeros((N, 2)); sfx = np.zeros((N, 2))
T = np.arange(N) / SR

# ---------------------------------------------------------------- dark pad chords (D minor world), change on scene cuts
prog = {"hook": ["E2", "B2", "E3", "G3"], "lightship": ["C2", "G2", "E3", "G3"], "shout": ["A1", "E2", "C3", "E3"],
        "course": ["F1", "C2", "A2", "C3"], "aground": ["D2", "A2", "D3", "F3"], "board": ["C2", "G2", "Eb3", "G3"],
        "theory": ["B1", "F#2", "D3", "F#3"], "end": ["E2", "B2", "E3", "G3"]}
keys = ORDER + [None]
for k, k2 in zip(keys[:-1], keys[1:]):
    a0 = max(0, CUT[k] - 0.3); a1 = min(TOTAL, (CUT[k2] if k2 else TOTAL) + 0.9)
    i0, i1 = int(a0 * SR), int(a1 * SR); tt = np.arange(i1 - i0) / SR
    e = np.clip(tt / 0.6, 0, 1) * np.clip((a1 - a0 - tt) / 0.9, 0, 1)
    ch = np.zeros((i1 - i0, 2))
    for nm in prog[k]:
        f = note(nm)
        for d, pan in [(-0.004, -0.7), (0.0, 0.0), (0.005, 0.7)]:
            saw = 2 * ((f * (1 + d) * tt + rng.random()) % 1.0) - 1
            ch[:, 0] += saw * (1 - pan) * 0.5; ch[:, 1] += saw * (1 + pan) * 0.5
    ch = filt(ch, 700, "low") * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * tt))[:, None]
    ch *= e[:, None] / len(prog[k])
    music[i0:i1] += ch * 0.5
    # sub drone on the root
    f = note(prog[k][0]); s = np.sin(2 * np.pi * f * tt) * e
    music[i0:i1] += np.stack([s, s], 1) * 0.3

# sparse piano-like plucks
plucks = ["E5", "G5", "B4", "F#5", "E5", "D5", "B4", "C5"]
tt = 1.2; i = 0
while tt < TOTAL - 3:
    nm = plucks[i % len(plucks)]; n = int(2.4 * SR); x = np.arange(n) / SR; f = note(nm)
    s = (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * 2 * f * x) * np.exp(-x * 4) + 0.1 * np.sin(2 * np.pi * 3.01 * f * x) * np.exp(-x * 7))
    add(music, s * env_ad(n, 0.003, 0.7), tt, 0.06, pan=0.5 * np.sin(i * 1.7))
    tt += 2.4 if i % 3 != 2 else 3.6; i += 1
music = reverb(music, 3.4, 0.4, 1)

def boom(gain, length=2.2, f0=80, f1=30):
    n = int(length * SR); x = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-x * 4); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2.0)
    rumble = filt(rng.normal(0, 1, n), 180, "low") * np.exp(-x * 1.5) * 1.4
    return np.tanh((s + rumble) * 1.5) * gain


# ---------------------------------------------------------------- textures
def noise_bed(t0, t1, lo, hi, gain, fade=0.6):
    n = int((t1 - t0) * SR); x = np.arange(n) / SR
    z = rng.normal(0, 1, (n, 2)); z = filt(filt(z, hi, "low"), lo, "high")
    e = np.clip(x / fade, 0, 1) * np.clip((t1 - t0 - x) / fade, 0, 1)
    add(sfx, z * e[:, None], t0, gain)


def nxt(k):
    return CUT[ORDER[ORDER.index(k) + 1]] if k != ORDER[-1] else TOTAL


def swell_bed(t0, t1, gain, period=4.2):
    n = int((t1 - t0) * SR); x = np.arange(n) / SR
    z = filt(filt(rng.normal(0, 1, (n, 2)), 900, "low"), 80, "high")
    sw = 0.55 + 0.45 * np.sin(2 * np.pi * x[:, None] / period + np.array([[0, 1.1]]))
    e = np.clip(x / 0.4, 0, 1) * np.clip((t1 - t0 - x) / 0.5, 0, 1)
    add(sfx, z * sw * e[:, None], t0, gain)


def engine(t0, t1, gain, f=46.0, fade=0.6):
    """distant twin radial-engine drone with slow beating"""
    n = int((t1 - t0) * SR); x = np.arange(n) / SR
    s = np.zeros(n)
    for ff, g in ((f, 1.0), (f * 1.013, 0.9), (f * 2, 0.5), (f * 3.02, 0.25)):
        s += g * np.sign(np.sin(2 * np.pi * ff * x)) * 0.5
    s = filt(s, 420, "low") * (0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * x))
    s += filt(rng.normal(0, 1, n), 300, "low") * 0.6
    e = np.clip(x / fade, 0, 1) * np.clip((t1 - t0 - x) / fade, 0, 1)
    add(sfx, s * e, t0, gain)


for k, g in [("hook", 0.11), ("lightship", 0.04), ("shout", 0.07), ("course", 0.07), ("aground", 0.12), ("theory", 0.06), ("end", 0.09)]:
    swell_bed(CUT[k], nxt(k), g)
for k in ORDER:
    noise_bed(CUT[k], nxt(k), 250, 1300, 0.04, 0.4)
# wind over the whole piece
noise_bed(0.0, TOTAL, 300, 2400, 0.025, 1.0)


def bell(t0, gain, f=620.0):
    n = int(3.0 * SR); x = np.arange(n) / SR
    s = sum(g * np.sin(2 * np.pi * f * r * x) * np.exp(-x * d) for r, g, d in ((1, 1, 1.4), (2.76, 0.5, 2.5), (5.4, 0.25, 4), (0.5, 0.3, 1)))
    add(sfx, s * np.clip(x / 0.002, 0, 1), t0, gain, pan=-0.4)


def foghorn(t0, dur, gain, f=88.0):
    n = int(dur * SR); x = np.arange(n) / SR
    s = sum(np.sign(np.sin(2 * np.pi * f * h * x)) / h for h in (1, 2, 3))
    s = filt(s, 600, "low") * np.clip(x / 0.25, 0, 1) * np.clip((dur - x) / 0.6, 0, 1)
    add(sfx, s, t0, gain, pan=-0.3)


# lightship: bell + distant foghorn
bell(CUT["lightship"] + 1.0, 0.05); bell(CUT["shout"] + 0.3, 0.06); bell(CUT["shout"] + 3.2, 0.05)
foghorn(CUT["lightship"] + 2.5, 2.4, 0.07)
# ticking clock on every timestamped scene (Last known moments)
for k in ORDER[1:]:
    tt = CUT[k] + 0.3; j = 0
    while tt < nxt(k) - 0.2:
        n = int(0.03 * SR); x = np.arange(n) / SR
        c = filt(rng.normal(0, 1, n), 2500, "high") * np.exp(-x * 200)
        add(sfx, c, tt, 0.05 if j % 2 == 0 else 0.035, pan=0.3)
        tt += 0.5; j += 1
# typewriter clacks when each headline appears
for k in ORDER[1:]:
    for j in range(6):
        n = int(0.05 * SR); x = np.arange(n) / SR
        c = filt(rng.normal(0, 1, n), 1800, "high") * np.exp(-x * 120) + np.sin(2 * np.pi * 180 * x) * np.exp(-x * 90) * 0.5
        add(sfx, c, CUT[k] + 0.05 + j * 0.055 + rng.uniform(0, 0.015), 0.11, pan=-0.2)
# cut whooshes
for k in ORDER[1:]:
    n = int(0.35 * SR); x = np.arange(n) / SR
    z = filt(rng.normal(0, 1, (n, 2)), 3000, "low") * (np.sin(np.pi * x / 0.35) ** 2)[:, None]
    add(sfx, z, CUT[k] - 0.15, 0.10)
# breaking surf on the shoals
for k, g in (("hook", 0.18), ("aground", 0.24)):
    tt = CUT[k] + 0.4
    while tt < nxt(k) - 0.5:
        n = int(2.2 * SR); x = np.arange(n) / SR
        z = filt(filt(rng.normal(0, 1, (n, 2)), 3500, "low"), 150, "high") * (np.clip(x / 0.5, 0, 1) * np.exp(-np.maximum(0, x - 0.5) * 2.2))[:, None]
        add(sfx, z, tt, g); tt += rng.uniform(1.8, 2.6)
add(sfx, boom(0.35, 1.6, 90, 30), CUT["aground"] + 0.1)   # hull hits the shoal
# creaking timber in the galley
for j in range(3):
    n = int(0.9 * SR); x = np.arange(n) / SR
    f = 140 + 60 * np.sin(2 * np.pi * 0.8 * x)
    c = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (rng.random(n) > 0.6)
    add(sfx, filt(c, 900, "low") * np.sin(np.pi * x / 0.9) ** 2, CUT["board"] + 0.4 + j * 1.9, 0.03, pan=0.5)
# stamps on the theory cards and "never proven"
add(sfx, boom(0.3, 0.6, 120, 50), wt("theory", "mutiny") - 0.3)
add(sfx, boom(0.3, 0.6, 120, 50), wt("theory", "pirates") - 0.3)
add(sfx, boom(0.35, 0.6, 120, 50), wt("theory", "proven"))
# heartbeat into the reveal, big hit on "No crew"
REV = wt("board", "crew") - 0.25
t = CUT["board"] + 0.8; i = 0
while t < REV - 0.4:
    for dt, g in ((0, 0.24), (0.2, 0.17)):
        add(sfx, boom(g, 0.32, 70, 40), t + dt)
    t += 0.85 - min(0.25, i * 0.05); i += 1
add(sfx, boom(0.8, 2.8, 95, 28), REV)
n = int(1.4 * SR); x = np.arange(n) / SR
add(sfx, filt(rng.normal(0, 1, (n, 2)), 1500, "low") * np.exp(-x * 3)[:, None], REV, 0.2)
# final bell
bell(CUT["end"] + 0.3, 0.06, 560)

# stamp thuds
add(sfx, boom(0.35, 0.6, 120, 50), 0.0)
add(sfx, boom(0.32, 0.6, 120, 50), wt("end", "unsolved"))
sfx = reverb(sfx, 1.8, 0.2, 2)

# ---------------------------------------------------------------- voice (already processed in voice.py)
v, sr = sf.read("vo.wav")
if v.ndim == 1:
    v = np.stack([v, v], 1)
if sr != SR:
    v = resample_poly(v, SR, sr, axis=0)
voice = np.zeros((N, 2)); add(voice, v[: N], 0.0)
voice *= 0.16 / np.sqrt(np.mean(voice[np.abs(voice[:, 0]) > 0.02] ** 2))

# duck music ~10 dB under the voice
env = np.abs(voice[:, 0]); hop = 240
blocks = env[: len(env) // hop * hop].reshape(-1, hop).max(1)
att, rel = np.exp(-1 / (0.03 * SR / hop)), np.exp(-1 / (0.4 * SR / hop))
e = np.zeros_like(blocks); cur = 0
for i, b in enumerate(blocks):
    cur = att * cur + (1 - att) * b if b > cur else rel * cur + (1 - rel) * b; e[i] = cur
e = np.interp(np.arange(N), np.arange(len(e)) * hop, e)
duck = 1 - 0.68 * np.clip(e / 0.08, 0, 1)
mix = music * 0.5 * duck[:, None] + sfx * (1 - 0.3 * np.clip(e / 0.08, 0, 1))[:, None] + voice
mix *= np.clip((TOTAL - T) / 0.8, 0, 1)[:, None]
mix = np.tanh(mix * 1.1) / 1.1
sf.write("mix_raw.wav", mix.astype(np.float32), SR)
print("mix", round(N / SR, 2), "s")
