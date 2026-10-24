"""Original soundtrack + sound design + voice mix for 'Percy Fawcett – the last letter'.
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
rng = np.random.default_rng(1925)


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
prog = {"hook": ["E2", "B2", "E3", "G3"], "camp": ["C2", "G2", "E3", "G3"], "party": ["A1", "E2", "C3", "E3"],
        "letter": ["F1", "C2", "A2", "C3"], "coords": ["D2", "A2", "D3", "F3"], "why": ["C2", "G2", "Eb3", "G3"],
        "bones": ["Bb1", "F2", "D3", "F3"], "theory": ["B1", "F#2", "D3", "F#3"], "end": ["E2", "B2", "E3", "G3"]}
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


def insects(t0, t1, gain):
    """night jungle: pulsing cicada-like hiss + scattered chirps"""
    n = int((t1 - t0) * SR); x = np.arange(n) / SR
    z = filt(filt(rng.normal(0, 1, (n, 2)), 7500, "low"), 4200, "high")
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 9.5 * x)[:, None] * np.sin(2 * np.pi * 0.23 * x[:, None] + np.array([[0, 1.3]]))
    e = np.clip(x / 0.8, 0, 1) * np.clip((t1 - t0 - x) / 0.8, 0, 1)
    add(sfx, z * am * e[:, None], t0, gain)
    tt = t0 + 0.5
    while tt < t1 - 0.5:
        m = int(0.18 * SR); y = np.arange(m) / SR; f = rng.uniform(2600, 4200)
        c = np.sin(2 * np.pi * f * y) * (np.sin(2 * np.pi * 38 * y) > 0) * np.sin(np.pi * y / 0.18)
        add(sfx, c, tt, gain * 0.25, pan=rng.uniform(-0.8, 0.8)); tt += rng.uniform(0.4, 1.6)


def bird(t0, gain):
    """distant two-note night bird call"""
    for j, (f0, f1) in enumerate(((1450, 1100), (1300, 950))):
        m = int(0.32 * SR); y = np.arange(m) / SR
        f = f0 + (f1 - f0) * y / 0.32
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * y / 0.32) ** 2
        add(sfx, c, t0 + j * 0.45, gain, pan=-0.6)


def frogs(t0, t1, gain):
    tt = t0 + 0.3
    while tt < t1 - 0.3:
        m = int(0.09 * SR); y = np.arange(m) / SR
        c = np.sign(np.sin(2 * np.pi * 190 * y)) * np.sin(np.pi * y / 0.09) * (0.5 + 0.5 * np.sin(2 * np.pi * 40 * y))
        add(sfx, filt(c, 1200, "low"), tt, gain, pan=0.6); tt += rng.choice([0.22, 0.22, 0.9, 1.4])


insects(0.0, TOTAL, 0.05)
for k in ("hook", "party", "theory", "end"):
    frogs(CUT[k], nxt(k), 0.035)
for tb in (1.5, CUT["party"] + 1.2, CUT["why"] + 0.6, CUT["end"] + 2.0):
    bird(tb, 0.035)
for k in ORDER:
    noise_bed(CUT[k], nxt(k), 250, 1300, 0.035, 0.4)
noise_bed(0.0, TOTAL, 300, 2400, 0.02, 1.0)
# campfire crackle on the party scene
tt = CUT["party"] + 0.1
while tt < nxt("party"):
    m = int(0.02 * SR); y = np.arange(m) / SR
    add(sfx, filt(rng.normal(0, 1, m), 2000, "high") * np.exp(-y * 300), tt, rng.uniform(0.04, 0.12), pan=rng.uniform(-0.3, 0.3))
    tt += rng.uniform(0.04, 0.3)
# paper rustle as the letter appears
n = int(0.7 * SR); x = np.arange(n) / SR
add(sfx, filt(filt(rng.normal(0, 1, (n, 2)), 6000, "low"), 1500, "high") * (np.sin(np.pi * x / 0.7) ** 2 * (rng.random(n) > 0.5))[:, None],
    CUT["letter"] + 0.1, 0.10)
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
# radio static on the 'report to the papers' line
n = int(1.6 * SR); x = np.arange(n) / SR
st = filt(filt(rng.normal(0, 1, (n, 2)), 4500, "low"), 600, "high") * (0.6 + 0.4 * (rng.random((n, 1)) > 0.97))
add(sfx, st * np.clip(x / 0.1, 0, 1)[:, None] * np.clip((1.6 - x) / 0.4, 0, 1)[:, None], wt("coords", "report") - 0.2, 0.05)
# heartbeat into the reveal, big hit on "thirteen"
REV = wt("coords", "thirteen") - 0.05
t = CUT["coords"] + 0.6; i = 0
while t < REV - 0.4:
    for dt, g in ((0, 0.24), (0.2, 0.17)):
        add(sfx, boom(g, 0.32, 70, 40), t + dt)
    t += 0.85 - min(0.25, i * 0.05); i += 1
add(sfx, boom(0.8, 2.8, 95, 28), REV)
n = int(1.4 * SR); x = np.arange(n) / SR
add(sfx, filt(rng.normal(0, 1, (n, 2)), 1500, "low") * np.exp(-x * 3)[:, None], REV, 0.2)
# stamps: theory cards, "not him", "unsolved"
add(sfx, boom(0.3, 0.6, 120, 50), wt("theory", "hunger") - 0.3)
add(sfx, boom(0.3, 0.6, 120, 50), wt("theory", "killed") - 0.3)
add(sfx, boom(0.4, 0.8, 110, 40), wt("bones", "not"))
add(sfx, boom(0.25, 0.6, 120, 50), wt("why", "typo"))
# distant thunder under the bones scene
add(sfx, boom(0.18, 3.5, 60, 25), CUT["bones"] + 0.3)

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
