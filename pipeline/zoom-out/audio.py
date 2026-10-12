"""Original soundtrack + sound design + voice mix for the zoom-out video."""
import numpy as np, soundfile as sf
from scipy.signal import lfilter, resample_poly, butter, sosfilt
from timeline import *

SR = 48000
N = int((TOTAL + 0.05) * SR)
rng = np.random.default_rng(11)
T = np.arange(N) / SR


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "Eb": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "Bb": 1, "B": 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)


def lp(x, fc):
    sos = butter(2, fc, "low", fs=SR, output="sos"); return sosfilt(sos, x)


def hp(x, fc):
    sos = butter(2, fc, "high", fs=SR, output="sos"); return sosfilt(sos, x)


def bp(x, lo, hi):
    sos = butter(2, [lo, hi], "band", fs=SR, output="sos"); return sosfilt(sos, x)


def env_ad(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


def add(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    if sig.ndim == 1:
        l = sig * np.sqrt(0.5 * (1 - pan)) * 1.41; r = sig * np.sqrt(0.5 * (1 + pan)) * 1.41
        sig = np.stack([l, r], 1)
    j = min(N, i + len(sig)); k0 = 0
    if i < 0:
        k0 = -i; i = 0
    buf[i:j] += sig[k0:k0 + (j - i)] * gain


def reverb(x, seconds=3.2, mix=0.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = r.normal(0, 1, n) * np.exp(-t * 6.9 / seconds)
        ir = lp(ir, 6000); ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch], len(x) + n) * np.fft.rfft(ir, len(x) + n))[: len(x)]
    return x * (1 - mix) + out * mix * 1.6


music = np.zeros((N, 2))
sfx = np.zeros((N, 2))

# ---------------------------------------------------------------- pad chords (change at each arrival)
chords = [
    (0.0, ["A2", "E3", "A3", "C4", "E4"]),
    (za["sun"], ["F2", "C3", "A3", "C4", "F4"]),
    (za["solar"], ["C3", "G3", "C4", "E4", "G4"]),
    (za["milky"], ["G2", "D3", "B3", "D4", "G4"]),
    (za["lani"], ["E2", "B2", "G3", "B3", "E4"]),
    (za["obs"], ["A1", "A2", "E3", "B3", "C4", "E4"]),
    (vs["end"] + 0.4, ["F2", "C3", "A3", "E4", "G4"]),
    (TOTAL + 5, []),
]
pad = np.zeros((N, 2))
for (t0, ns), (t1, _) in zip(chords[:-1], chords[1:]):
    a0 = max(0.0, t0 - 0.5); a1 = min(TOTAL + 0.05, t1 + 1.2)
    i0, i1 = int(a0 * SR), int(a1 * SR)
    tt = np.arange(i1 - i0) / SR
    e = np.clip(tt / 0.9, 0, 1) * np.clip((a1 - a0 - tt) / 1.2, 0, 1)
    chunk = np.zeros((i1 - i0, 2))
    for q, nm in enumerate(ns):
        f = note(nm)
        for d, pan in [(-0.006, -0.6), (0.0, 0.0), (0.0065, 0.6)]:
            ph = rng.random()
            saw = 2 * ((f * (1 + d) * tt + ph) % 1.0) - 1
            chunk[:, 0] += saw * (1 - pan) * 0.5; chunk[:, 1] += saw * (1 + pan) * 0.5
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.12 * tt)
    for ch in range(2):
        chunk[:, ch] = lp(chunk[:, ch], 900) * 0.6 + lp(chunk[:, ch], 2400) * 0.15 * lfo
    chunk *= e[:, None] / max(1, len(ns))
    pad[i0:i1] += chunk
# sub bass on the root
for (t0, ns), (t1, _) in zip(chords[:-1], chords[1:]):
    if not ns:
        continue
    a0 = max(0.0, t0 - 0.2); a1 = min(TOTAL + 0.05, t1 + 0.6)
    i0, i1 = int(a0 * SR), int(a1 * SR)
    tt = np.arange(i1 - i0) / SR
    f = note(ns[0]) / (2 if note(ns[0]) > 80 else 1)
    s = np.sin(2 * np.pi * f * tt) * np.clip(tt / 0.4, 0, 1) * np.clip((a1 - a0 - tt) / 0.6, 0, 1)
    pad[i0:i1] += np.stack([s, s], 1) * 0.35
music += pad * 0.55

# ---------------------------------------------------------------- bell arpeggio (8ths at 100 BPM), sparse at start
beat = 60 / 100 / 2
arp = np.zeros((N, 2))
tt = 0.15
idx = 0
while tt < vs["end"] + 2.2:
    cur = [c for c in chords if c[0] <= tt + 0.05][-1][1]
    if cur:
        tones = sorted(cur, key=note)[-4:]
        nm = tones[[0, 2, 1, 3, 2, 1][idx % 6]]
        f = note(nm) * 2
        n = int(1.1 * SR); x = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.01 * x) + 0.12 * np.sin(2 * np.pi * f * 3.98 * x))
        s *= env_ad(n, 0.004, 0.32)
        g = 0.05 if tt < za["sun"] else 0.075
        if za["obs"] - 2.0 < tt < za["obs"]:
            g = 0.0  # drop out for the riser
        add(arp, s, tt, g, pan=0.45 * np.sin(idx * 1.3))
    tt += beat; idx += 1
music += arp

# soft pulse (kick-like thump on beats) from the solar system on, stops before the payoff riser
k_n = int(0.35 * SR); kx = np.arange(k_n) / SR
kick = np.sin(2 * np.pi * (48 + 60 * np.exp(-kx * 30)) * kx) * np.exp(-kx * 9)
tt = za["solar"]
while tt < za["obs"] - 1.9:
    add(music, kick, tt, 0.22)
    tt += beat * 2
tt = za["obs"] + 1.2
while tt < vs["end"]:
    add(music, kick, tt, 0.26)
    tt += beat * 2

music = reverb(music, 3.0, 0.38, 1)

# ---------------------------------------------------------------- sound effects


def whoosh(dur, gain, f_hi=6000, f_lo=250):
    n = int(dur * SR); x = np.arange(n) / SR
    noise = rng.normal(0, 1, (n, 2))
    u = x / dur
    e = np.sin(np.pi * np.clip(u, 0, 1)) ** 1.6
    # filter sweep downward (zooming out): crossfade between bands
    bands = [(3000, 9000), (1200, 4000), (500, 1800), (180, 800)]
    out = np.zeros((n, 2))
    for bi, (lo, hi) in enumerate(bands):
        w = np.clip(1 - np.abs(u * (len(bands) - 1) - bi), 0, 1)
        for ch in range(2):
            out[:, ch] += bp(noise[:, ch], lo, hi) * w
    return out * e[:, None] * gain


def boom(gain, length=1.6, f0=75, f1=34):
    n = int(length * SR); x = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-x * 4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-x * 2.4)
    click = lp(rng.normal(0, 1, n), 2500) * np.exp(-x * 40) * 0.5
    rumble = lp(rng.normal(0, 1, n), 160) * np.exp(-x * 1.8) * 1.2
    return np.tanh((s + click + rumble) * 1.4) * gain


for k in STEPS[1:]:
    add(sfx, whoosh(TD[k] + 0.25, 0.32 if k != "milky" else 0.42), zs[k] - 0.1)
    add(sfx, boom(0.42 if k != "obs" else 0.0), za[k] - 0.02)

# riser into the payoff + big boom
r0, r1 = za["obs"] - 2.0, za["obs"]
n = int((r1 - r0) * SR); x = np.arange(n) / SR; u = x / (r1 - r0)
riser = np.stack([hp(rng.normal(0, 1, n), 1500), hp(rng.normal(0, 1, n), 1500)], 1) * (u ** 2.5)[:, None] * 0.35
f = 120 * 2 ** (u * 3.2)
riser += (np.sin(2 * np.pi * np.cumsum(f) / SR) * u ** 2 * 0.18)[:, None]
add(sfx, riser, r0)
big = boom(0.62, 2.6, 90, 28)
add(sfx, big, za["obs"] - 0.01)
add(sfx, whoosh(1.5, 0.28, 9000, 120), za["obs"] - 0.05)

# light-ring plucks as it crosses each planet's orbit
plan = [0.387, 0.723, 1.0, 1.524, 5.203, 9.537, 19.19, 30.07]
pn = ["A4", "C5", "D5", "E5", "G5", "A5", "C6", "E6"]
for a_au, nm in zip(plan, pn):
    tt = RING0 + a_au / 30.07 * (RING1 - RING0)
    n = int(0.9 * SR); x = np.arange(n) / SR
    f = note(nm)
    s = (np.sin(2 * np.pi * f * x) * 0.8 + 0.25 * np.sin(2 * np.pi * 2 * f * x) + 0.1 * np.sin(2 * np.pi * 3 * f * x)) * env_ad(n, 0.002, 0.22)
    add(sfx, s, tt, 0.16, pan=(a_au / 30.07) * 0.8 - 0.4)
# soft shimmer while light travels
n = int((RING1 - RING0 + 0.4) * SR); x = np.arange(n) / SR
sh = np.stack([bp(rng.normal(0, 1, n), 5000, 11000), bp(rng.normal(0, 1, n), 5000, 11000)], 1)
sh *= (np.sin(np.pi * np.clip(x / (RING1 - RING0 + 0.4), 0, 1)) * 0.05)[:, None]
add(sfx, sh, RING0)


# counter tick rolls
def ticks(t0, dur, gain=0.11):
    tt = 0.0
    while tt < dur:
        u = tt / dur
        n = int(0.02 * SR); x = np.arange(n) / SR
        s = np.sin(2 * np.pi * (2400 + 800 * u) * x) * np.exp(-x * 400)
        add(sfx, s, t0 + tt, gain * (1 - 0.5 * u), pan=0.2)
        tt += 0.035 + 0.09 * u ** 2


ticks(seg("sun", 1), 0.8)
ticks(seg("milky", 1), 0.9)
ticks(seg("lani", 1), 0.9)
ticks(seg("obs", 1), 1.3, 0.13)


# soft pops for text
def popfx(t0, gain=0.10, f=900):
    n = int(0.12 * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * (f + 900 * np.exp(-x * 60)) * x) * np.exp(-x * 35)
    add(sfx, s, t0, gain)


for k in STEPS[1:]:
    popfx(vs[k])
popfx(vs["end"], 0.1, 700)
popfx(seg("end", 1), 0.14, 1100)
# final bell chord after "Still feel big?"
for nm, g in [("A4", 0.09), ("E5", 0.07), ("C6", 0.05), ("E6", 0.04)]:
    n = int(3.5 * SR); x = np.arange(n) / SR
    f = note(nm)
    s = (np.sin(2 * np.pi * f * x) + 0.2 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 3)) * env_ad(n, 0.003, 1.2)
    add(sfx, s, seg("end", 1) + 0.05, g)
sfx = reverb(sfx, 2.2, 0.22, 2)

# ---------------------------------------------------------------- voice
voice = np.zeros((N, 2))
for k in ["hook", "sun", "solar", "milky", "lani", "obs", "end"]:
    v, sr = sf.read(f"vo_{k}.wav")
    v = resample_poly(v, SR, sr)
    v = hp(v, 70)
    add(voice, v, vs[k], 1.0)
peak_rms = np.sqrt(np.mean(voice[np.abs(voice[:, 0]) > 0.02] ** 2))
voice *= 0.16 / peak_rms
# light presence / room
voice = reverb(voice, 0.9, 0.08, 3)

# duck music under voice
venv = np.abs(voice[:, 0])
hop = 240
blocks = venv[: len(venv) // hop * hop].reshape(-1, hop).max(1)
att, rel = np.exp(-1 / (0.03 * SR / hop)), np.exp(-1 / (0.35 * SR / hop))
e = np.zeros_like(blocks); cur = 0
for i, b in enumerate(blocks):
    cur = att * cur + (1 - att) * b if b > cur else rel * cur + (1 - rel) * b
    e[i] = cur
e = np.interp(np.arange(N), np.arange(len(e)) * hop, e)
duck = 1 - 0.62 * np.clip(e / 0.1, 0, 1)
music *= duck[:, None]

sfx *= (1 - 0.35 * np.clip(e / 0.1, 0, 1))[:, None]
mix = music * 0.45 + sfx * 0.9 + voice
mix[:, :] *= np.clip((TOTAL + 0.05 - T) / 0.6, 0, 1)[:, None]
mix = np.tanh(mix * 1.1) / 1.1
sf.write("mix_raw.wav", mix.astype(np.float32), SR)
np.savez("stems.npz", music=(music * 0.45).astype(np.float32), sfx=(sfx * 0.9).astype(np.float32), voice=voice.astype(np.float32))
print("mix written", mix.shape[0] / SR, "s, peak", np.abs(mix).max())
