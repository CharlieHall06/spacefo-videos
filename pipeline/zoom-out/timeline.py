"""Shared timing for picture and sound."""
import json, os

VO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vo.json")))
STEPS = ["hook", "sun", "solar", "milky", "lani", "obs"]
LEAD = {"sun": 0.5, "solar": 0.35, "milky": 0.25, "lani": 0.4, "obs": 0.3}   # zoom starts this long before previous line ends
TD = {"sun": 1.1, "solar": 1.1, "milky": 1.6, "lani": 1.15, "obs": 1.4}      # zoom durations

vs, ve, zs, za = {}, {}, {}, {}
vs["hook"] = 0.25
ve["hook"] = vs["hook"] + VO["hook"]["dur"]
prev = "hook"
for k in STEPS[1:]:
    zs[k] = ve[prev] - LEAD[k]
    za[k] = zs[k] + TD[k]
    vs[k] = za[k] - 0.2 if k != "obs" else za[k] + 0.25
    ve[k] = vs[k] + VO[k]["dur"]
    prev = k
vs["end"] = ve["obs"] + 0.45
ve["end"] = vs["end"] + VO["end"]["dur"]
TOTAL = ve["end"] + 1.25


def seg(k, i):
    """start time of spoken segment i (0 = start of line, 1 = after first pause...)"""
    if i == 0:
        return vs[k]
    return vs[k] + VO[k]["pauses"][i - 1][1]


RING0 = seg("solar", 1)            # light leaves the Sun ("Light takes...")
RING1 = vs["solar"] + 3.70         # reaches Neptune

if __name__ == "__main__":
    for k in STEPS[1:]:
        print(f"{k:6s} zoom {zs[k]:6.2f}-{za[k]:6.2f}  voice {vs[k]:6.2f}-{ve[k]:6.2f}")
    print("hook voice", vs["hook"], ve["hook"], " end voice", round(vs["end"], 2), round(ve["end"], 2))
    print("ring", round(RING0, 2), round(RING1, 2), "TOTAL", round(TOTAL, 2))
