"""Render 'Flight 19 – the last hours' (The Vanished Files, Last known moments format).
Dark case-file look: skia frames piped to ffmpeg.  Run in the build dir (needs vo.json).
usage: python3 render.py out.mp4            (full video, silent)
       python3 render.py --still t1,t2,... prefix   (PNG stills for checking)"""
import sys, math, json, subprocess
import numpy as np, skia

W, H, FPS = 1080, 1920, 30
FONTS = "/home/claude/build/fonts/"
TF = {
    "type": skia.Typeface.MakeFromFile(FONTS + "CourierPrime-Regular.ttf"),
    "typeb": skia.Typeface.MakeFromFile(FONTS + "CourierPrime-Bold.ttf"),
    "osw": skia.Typeface.MakeFromFile(FONTS + "Oswald%5Bwght%5D.ttf"),
    "bebas": skia.Typeface.MakeFromFile(FONTS + "BebasNeue-Regular.ttf"),
}
BG = (8, 10, 14); STEEL = (122, 140, 160); ICE = (196, 210, 224); RED = (214, 40, 40); WHITE = (244, 244, 240)
AMBER = (255, 150, 60)

VO = json.load(open("vo.json"))
SC = {s["key"]: s for s in VO["scenes"]}
ORDER = [s["key"] for s in VO["scenes"]]
CUT = {k: (0.0 if i == 0 else SC[k]["start"] - 0.12) for i, k in enumerate(ORDER)}
TOTAL = VO["dur"] + 1.15
WORDS = []  # (word, t, sentence id)
for s in VO["scenes"]:
    sid = 0
    for w, t in s["words"]:
        WORDS.append((w, t, (s["key"], sid)))
        if w[-1] in ".?:":
            sid += 1


def word_t(key, word, n=0):
    hits = [t for w, t in SC[key]["words"] if w.strip(".,:?").lower() == word]
    return hits[n]


def scene_at(t):
    cur = ORDER[0]
    for k in ORDER:
        if t >= CUT[k]:
            cur = k
    return cur


def C(rgb, a=255):
    return skia.Color(rgb[0], rgb[1], rgb[2], int(max(0, min(255, a))))


def P(rgb, a=255, stroke=None, aa=True):
    p = skia.Paint(Color=C(rgb, a), AntiAlias=aa)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
    return p


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def font(name, size):
    f = skia.Font(TF[name], size)
    f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def text(cv, s, x, y, f, rgb, a=255, align="l", shadow=True):
    w = f.measureText(s)
    if align == "c":
        x -= w / 2
    elif align == "r":
        x -= w
    if shadow:
        sp = skia.Paint(Color=C((0, 0, 0), a * 0.7), AntiAlias=True,
                        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        cv.drawString(s, x + 2, y + 3, f, sp)
    cv.drawString(s, x, y, f, P(rgb, a))
    return w


rng = np.random.default_rng(45)
# ---------------------------------------------------------------- shared textures
def mk_img(arr):
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


GRAIN = []
for i in range(6):
    g = rng.normal(128, 38, (960, 540)).clip(0, 255).astype(np.uint8)
    a = np.dstack([g, g, g, np.full_like(g, 255)])
    GRAIN.append(mk_img(a))
yy, xx = np.mgrid[0:H // 4, 0:W // 4]
d = np.sqrt(((xx - W / 8) / (W / 8)) ** 2 * 1.0 + ((yy - H / 8) / (H / 8)) ** 2 * 0.85)
va = (np.clip((d - 0.55) / 0.7, 0, 1) ** 1.6 * 235).astype(np.uint8)
VIG = mk_img(np.dstack([np.zeros_like(va)] * 3 + [va]))
# paper fibre texture for cards
pf = rng.normal(0, 1, (480, 270)); pf = (pf - pf.min()) / (pf.max() - pf.min())
PAPER = mk_img(np.dstack([(pf * 255).astype(np.uint8)] * 3 + [np.full(pf.shape, 255, np.uint8)]))
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)

# ---------------------------------------------------------------- map data (lon, lat) – simplified outlines
FLORIDA = [(-87.6, 31.6), (-81.5, 31.6), (-81.45, 30.7), (-81.3, 30.0), (-81.1, 29.4), (-80.8, 28.9), (-80.55, 28.45),
           (-80.6, 28.1), (-80.4, 27.75), (-80.2, 27.2), (-80.05, 26.6), (-80.1, 26.1), (-80.15, 25.75), (-80.3, 25.4),
           (-80.45, 25.2), (-80.75, 25.15), (-81.1, 25.15), (-81.25, 25.6), (-81.7, 25.95), (-81.85, 26.4), (-82.1, 26.65),
           (-82.4, 27.0), (-82.65, 27.5), (-82.8, 28.0), (-82.7, 28.7), (-82.85, 29.1), (-83.2, 29.35), (-83.7, 29.9),
           (-84.2, 30.05), (-84.6, 29.9), (-85.3, 29.7), (-85.6, 30.1), (-86.5, 30.4), (-87.6, 30.3)]
KEYS = [(-80.45, 25.12), (-80.6, 24.98), (-80.85, 24.82), (-81.1, 24.7), (-81.4, 24.64), (-81.65, 24.58), (-81.8, 24.55)]
BAHAMAS = [
    [(-79.0, 26.68), (-78.6, 26.55), (-78.2, 26.6), (-77.9, 26.66), (-78.15, 26.74), (-78.6, 26.72), (-78.98, 26.8)],  # Grand Bahama
    [(-77.15, 26.95), (-77.0, 26.55), (-77.2, 26.0), (-77.35, 25.9), (-77.4, 26.25), (-77.5, 26.6), (-77.75, 26.92), (-77.5, 27.0)],  # Abaco
    [(-78.15, 25.2), (-77.75, 25.0), (-77.7, 24.6), (-77.75, 24.2), (-78.0, 24.05), (-78.3, 24.4), (-78.4, 24.8), (-78.3, 25.1)],  # Andros
    [(-77.55, 25.08), (-77.3, 25.05), (-77.28, 24.98), (-77.52, 24.98)],  # New Providence
    [(-76.75, 25.55), (-76.6, 25.3), (-76.2, 24.9), (-76.15, 24.65), (-76.3, 24.75), (-76.5, 25.15), (-76.65, 25.4)],  # Eleuthera
    [(-79.3, 25.78), (-79.24, 25.76), (-79.25, 25.66), (-79.3, 25.7)],  # Bimini
]
LON0, LON1, LAT0, LAT1 = -83.0, -75.6, 23.4, 30.2
MX0, MY0, MW = 60, 150, 960


def mp(lon, lat):
    k = MW / ((LON1 - LON0) * math.cos(math.radians(27)))
    return MX0 + (lon - LON0) * math.cos(math.radians(27)) * k, MY0 + (LAT1 - lat) * k


def poly(pts, close=True):
    p = skia.Path()
    for i, (lo, la) in enumerate(pts):
        x, y = mp(lo, la)
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    if close:
        p.close()
    return p


FT_LAUD = (-80.14, 26.12)
TARGET = (-79.15, 25.6)        # practice bombing area near Bimini (approx.)
LIKELY = (-78.0, 28.4)         # roughly north-east of the Bahamas (approx.)
ROUTE = [FT_LAUD, TARGET, (-78.1, 25.85), (-78.2, 26.9), (-79.2, 26.95), (-78.6, 27.8), LIKELY]


def draw_map(cv, t, t0, mode):
    """mode 'keys': belief vs likely position."""
    u = t - t0
    cv.save()
    cv.drawRect(skia.Rect(0, 0, W, H), P((14, 22, 32)))
    # paper
    pp = skia.Paint(Alphaf=0.07, BlendMode=skia.BlendMode.kOverlay)
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, H), SAMP, pp)
    # grid
    for lo in range(-84, -74):
        x, _ = mp(lo, 0); cv.drawLine(x, 0, x, 1250, P(STEEL, 30, 1.2))
    for la in range(24, 31):
        _, y = mp(0, la); cv.drawLine(0, y, W, y, P(STEEL, 30, 1.2))
        text(cv, f"{la}°N", 14, y - 6, font("type", 20), STEEL, 90, shadow=False)
    land = P((58, 70, 84)); edge = P((150, 168, 186), 200, 2.2)
    for path in [poly(FLORIDA)] + [poly(b) for b in BAHAMAS]:
        cv.drawPath(path, land); cv.drawPath(path, edge)
    for lo, la in KEYS:
        x, y = mp(lo, la); cv.drawCircle(x, y, 4.5, P((150, 168, 186), 220))
    f = font("typeb", 30)
    x, y = mp(-81.9, 28.2); text(cv, "FLORIDA", x - 70, y, f, ICE, 200)
    x, y = mp(-76.5, 26.3); text(cv, "BAHAMAS", x, y, f, ICE, 200)
    x, y = mp(-77.6, 30.1); text(cv, "ATLANTIC OCEAN", x - 60, y, font("type", 28), STEEL, 170)
    fx, fy = mp(*FT_LAUD)
    cv.drawCircle(fx, fy, 8, P(WHITE)); text(cv, "FT. LAUDERDALE", fx - 250, fy + 8, font("typeb", 24), WHITE, 230)
    # route (approx) drawn progressively
    pts = [mp(*q) for q in ROUTE]
    prog = ease(u / 2.6)
    segs = list(zip(pts[:-1], pts[1:]))
    L = [math.dist(a, b) for a, b in segs]; tot = sum(L) * prog
    path = skia.Path(); path.moveTo(*pts[0]); end = pts[0]
    for (a, b), l in zip(segs, L):
        if tot <= 0:
            break
        f_ = min(1, tot / l); end = (a[0] + (b[0] - a[0]) * f_, a[1] + (b[1] - a[1]) * f_)
        path.lineTo(*end); tot -= l
    rp = P(RED, 230, 5); rp.setPathEffect(skia.DashPathEffect.Make([18, 12], -u * 40))
    cv.drawPath(path, rp)
    tx, ty = mp(*TARGET)
    if prog > 0.15:
        text(cv, "PRACTICE TARGET", tx + 18, ty + 34, font("type", 22), ICE, 200)
    text(cv, "ROUTE & POSITIONS APPROX.", 60, 1120, font("type", 26), STEEL, 200, shadow=False)
    # belief: circle on the Keys
    a1 = ease((t - word_t("keys", "keys") + 0.6) / 0.5)
    if a1 > 0:
        kx, ky = mp(-81.0, 24.85)
        cv.drawOval(skia.Rect(kx - 130, ky - 60, kx + 130, ky + 60), P(ICE, 220 * a1, 4))
        text(cv, "WHERE HE THOUGHT", kx - 140, ky + 105, font("typeb", 30), ICE, 255 * a1)
    a2 = ease((t - word_t("keys", "not") + 0.15) / 0.35)
    if a2 > 0:
        kx, ky = mp(-81.0, 24.85)
        xp = P(RED, 255 * a2, 9)
        cv.drawLine(kx - 60, ky - 45, kx + 60, ky + 45, xp); cv.drawLine(kx - 60, ky + 45, kx + 60, ky - 45, xp)
    if prog >= 0.99:
        lx, ly = mp(*LIKELY)
        pulse = 1 + 0.25 * math.sin(u * 6)
        cv.drawCircle(lx, ly, 26 * pulse, P(RED, 70)); cv.drawCircle(lx, ly, 11, P(RED))
        a3 = ease((t - word_t("keys", "not")) / 0.4)
        text(cv, "ACTUALLY: FAR NORTH-EAST", lx - 330, ly - 48, font("typeb", 36), (255, 80, 70), 255 * a3)
    cv.restore()


# ---------------------------------------------------------------- sea / sky
def draw_sea(cv, t, sky_top, sky_bot, sea_col, horizon=820, sun=None, chop=1.0, fog=0.5):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, horizon)], [C(sky_top), C(sky_bot)])
    cv.drawRect(skia.Rect(0, 0, W, horizon + 2), skia.Paint(Shader=sh))
    if sun is not None:
        sx, sy, sa = sun
        glow = skia.GradientShader.MakeRadial((sx, sy), 420, [C(AMBER, 120 * sa), C(AMBER, 0)])
        cv.drawRect(skia.Rect(0, 0, W, horizon), skia.Paint(Shader=glow))
        cv.save(); cv.clipRect(skia.Rect(0, 0, W, horizon))
        cv.drawCircle(sx, sy, 46, P((255, 170, 90), 230 * sa)); cv.restore()
    sh2 = skia.GradientShader.MakeLinear([(0, horizon), (0, H)], [C(sea_col), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, horizon, W, H), skia.Paint(Shader=sh2))
    # wave lines (perspective)
    for i in range(46):
        z = i / 46
        y = horizon + 6 + (z ** 1.9) * (H - horizon)
        amp = (2 + 22 * z ** 2) * chop
        p = skia.Path()
        ph = t * (0.7 + z * 1.6) + i * 1.7
        for xi in range(0, W + 40, 40):
            yy = y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph) + amp * 0.5 * math.sin(xi * 0.031 + ph * 1.7)
            (p.moveTo if xi == 0 else p.lineTo)(xi, yy)
        cv.drawPath(p, P(ICE, 18 + 50 * z, 1.2 + 2.4 * z))
    # drifting fog banks
    for j in range(5):
        fx = ((j * 340 + t * (14 + j * 5)) % (W + 900)) - 450
        fy = horizon - 60 + j * 22
        fp = skia.Paint(Color=C(ICE, 26 * fog), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
        cv.drawOval(skia.Rect(fx, fy - 50, fx + 700, fy + 50), fp)


def plane_top(cv, x, y, s, rot, rgb=(20, 24, 30), a=255):
    """generic single-engine WWII torpedo-bomber silhouette, top view, nose up"""
    cv.save(); cv.translate(x, y); cv.rotate(rot); cv.scale(s, s)
    p = skia.Path()
    p.addOval(skia.Rect(-7, -46, 7, 44))                                  # fuselage
    w = skia.Path(); w.moveTo(-58, -4); w.lineTo(58, -4); w.lineTo(52, 8); w.lineTo(-52, 8); w.close()   # wings
    tl = skia.Path(); tl.moveTo(-20, 34); tl.lineTo(20, 34); tl.lineTo(17, 42); tl.lineTo(-17, 42); tl.close()
    pa = P(rgb, a)
    for q in (p, w, tl):
        cv.drawPath(q, pa)
    cv.drawRect(skia.Rect(-14, -49, 14, -46), pa)   # prop disc
    cv.restore()


def flying_boat(cv, x, y, s, rot, rgb=(16, 19, 24), a=255):
    """generic twin-engine flying boat, top view, nose up: long gull wing, two engines, twin-fin tail"""
    cv.save(); cv.translate(x, y); cv.rotate(rot); cv.scale(s, s)
    pa = P(rgb, a)
    hull = skia.Path(); hull.addRoundRect(skia.Rect(-12, -70, 12, 80), 12, 12); cv.drawPath(hull, pa)
    wing = skia.Path(); wing.moveTo(-150, -8); wing.lineTo(150, -8); wing.lineTo(140, 12); wing.lineTo(-140, 12); wing.close()
    cv.drawPath(wing, pa)
    for ex in (-46, 46):
        cv.drawRoundRect(skia.Rect(ex - 9, -38, ex + 9, 26), 8, 8, pa)
        cv.drawRect(skia.Rect(ex - 20, -42, ex + 20, -39), pa)
    for fx in (-128, 128):   # wing floats
        cv.drawRoundRect(skia.Rect(fx - 5, -2, fx + 5, 20), 4, 4, pa)
    tl = skia.Path(); tl.moveTo(-44, 66); tl.lineTo(44, 66); tl.lineTo(40, 78); tl.lineTo(-40, 78); tl.close(); cv.drawPath(tl, pa)
    for fx in (-44, 44):
        cv.drawRect(skia.Rect(fx - 3, 58, fx + 3, 84), pa)
    cv.restore()


def tanker(cv, x, y, s, a=255):
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    pa = P((10, 12, 16), a)
    h = skia.Path(); h.moveTo(-160, 0); h.lineTo(170, 0); h.lineTo(150, 22); h.lineTo(-150, 22); h.close()
    cv.drawPath(h, pa)
    cv.drawRect(skia.Rect(-150, -26, -96, 0), pa); cv.drawRect(skia.Rect(-140, -46, -110, -26), pa)
    cv.drawRect(skia.Rect(-128, -62, -120, -46), pa); cv.drawRect(skia.Rect(-10, -14, 20, 0), pa)
    cv.drawRect(skia.Rect(118, -14, 150, 0), pa)
    for lx in (-112, -12, 132):   # tiny deck lights
        cv.drawCircle(lx, -30 if lx == -112 else -18, 2.4, P((255, 220, 160), a))
    cv.restore()


# ---------------------------------------------------------------- scenes
def sc_takeoff(cv, t):
    u = t - CUT["takeoff"]
    draw_sea(cv, t, (40, 50, 62), (92, 104, 116), (34, 44, 54), horizon=760, chop=0.8, fog=0.9)
    # five aircraft in loose formation crossing the frame, slowly climbing away
    base = [(0, 0), (-110, 90), (110, 90), (-220, 180), (220, 180)]
    cx = 540 + 10 * math.sin(u * 0.4); cy = 610 - u * 14
    sc = 1.15 - u * 0.03
    for i, (dx, dy) in enumerate(base):
        bob = 4 * math.sin(u * 1.3 + i)
        plane_top(cv, cx + dx * sc, cy + dy * sc + bob, sc, -4 + 2 * math.sin(u * 0.5 + i), (16, 19, 25), 245)


def sc_compass(cv, t):
    u = t - CUT["compass"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((10, 13, 18)))
    cx, cy, R = 540, 700, 330
    s = 1.0 + 0.015 * u
    cv.save(); cv.translate(cx, cy); cv.scale(s, s)
    glow = skia.GradientShader.MakeRadial((0, 0), R * 1.5, [C((60, 80, 100), 90), C((0, 0, 0), 0)])
    cv.drawCircle(0, 0, R * 1.5, skia.Paint(Shader=glow))
    cv.drawCircle(0, 0, R + 26, P((30, 34, 40))); cv.drawCircle(0, 0, R + 26, P(STEEL, 200, 4))
    cv.drawCircle(0, 0, R, P((18, 22, 28))); cv.drawCircle(0, 0, R, P(STEEL, 150, 2))
    for i in range(72):
        a = math.radians(i * 5); l = 34 if i % 9 == 0 else (20 if i % 3 == 0 else 10)
        cv.drawLine(math.sin(a) * (R - 6), -math.cos(a) * (R - 6), math.sin(a) * (R - 6 - l), -math.cos(a) * (R - 6 - l),
                    P(ICE, 200, 3 if i % 9 == 0 else 1.6))
    f = font("typeb", 64)
    for lab, ang in [("N", 0), ("E", 90), ("S", 180), ("W", 270)]:
        a = math.radians(ang)
        text(cv, lab, math.sin(a) * (R - 90), -math.cos(a) * (R - 90) + 22, f, RED if lab == "N" else ICE, 230, "c")
    # erratic needle
    ang = 40 * math.sin(u * 2.1) + 70 * math.sin(u * 0.83 + 1) + 25 * math.sin(u * 5.7)
    cv.rotate(ang)
    nd = skia.Path(); nd.moveTo(0, -R + 50); nd.lineTo(18, 0); nd.lineTo(0, R - 50); nd.lineTo(-18, 0); nd.close()
    cv.drawPath(nd, P(ICE, 230))
    nr = skia.Path(); nr.moveTo(0, -R + 50); nr.lineTo(18, 0); nr.lineTo(-18, 0); nr.close()
    cv.drawPath(nr, P(RED))
    cv.drawCircle(0, 0, 14, P((40, 44, 50))); cv.restore()
    # glass glare
    gl = skia.Paint(Color=C(WHITE, 22), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
    cv.drawOval(skia.Rect(cx - 250, cy - 300, cx + 60, cy - 120), gl)


def sc_sunset(cv, t):
    u = t - CUT["sunset"]; dur = CUT["ditch"] - CUT["sunset"]
    k = ease(u / dur)
    top = tuple(int(a + (b - a) * k) for a, b in zip((52, 46, 58), (8, 10, 18)))
    bot = tuple(int(a + (b - a) * k) for a, b in zip((170, 90, 60), (24, 28, 40)))
    draw_sea(cv, t, top, bot, (26, 30, 40), horizon=800, sun=(700, 790 + 70 * k, 1 - 0.5 * k), chop=1.0 + 1.6 * k, fog=0.7)
    # fuel gauge (top-left inset)
    gx, gy, R = 300, 420, 150
    cv.drawCircle(gx, gy, R + 18, P((14, 16, 20), 235)); cv.drawCircle(gx, gy, R + 18, P(STEEL, 200, 3))
    for i in range(9):
        a = math.radians(-120 + i * 30)
        cv.drawLine(gx + math.sin(a) * R * 0.78, gy - math.cos(a) * R * 0.78, gx + math.sin(a) * R * 0.95, gy - math.cos(a) * R * 0.95,
                    P(RED if i <= 1 else ICE, 220, 4))
    text(cv, "E", gx - R * 0.62, gy + 20, font("typeb", 40), RED, 240, "c")
    text(cv, "F", gx + R * 0.62, gy + 20, font("typeb", 40), ICE, 240, "c")
    text(cv, "FUEL", gx, gy + 80, font("typeb", 34), ICE, 220, "c")
    fk = ease((t - word_t("sunset", "fuel") + 0.3) / 1.6)
    ang = math.radians(-35 - 70 * fk + 2.5 * math.sin(t * 9))
    cv.drawLine(gx, gy, gx + math.sin(ang) * R * 0.85, gy - math.cos(ang) * R * 0.85, P(WHITE, 240, 7))
    cv.drawCircle(gx, gy, 12, P((60, 64, 70)))


def sc_ditch(cv, t):
    u = t - CUT["ditch"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((7, 9, 13)))
    # radio set panel
    cv.drawRoundRect(skia.Rect(70, 300, 1010, 1060), 26, 26, P((20, 24, 30)))
    cv.drawRoundRect(skia.Rect(70, 300, 1010, 1060), 26, 26, P(STEEL, 140, 3))
    scr = skia.Rect(130, 380, 950, 800)
    cv.drawRoundRect(scr, 14, 14, P((10, 18, 22)))
    for i in range(1, 8):
        cv.drawLine(scr.left() + i * scr.width() / 8, scr.top(), scr.left() + i * scr.width() / 8, scr.bottom(), P(STEEL, 30, 1))
    for i in range(1, 5):
        cv.drawLine(scr.left(), scr.top() + i * scr.height() / 5, scr.right(), scr.top() + i * scr.height() / 5, P(STEEL, 30, 1))
    # waveform: bursts while the last words are spoken, otherwise static
    talk = 1.0 if (word_t("ditch", "we'll") - 0.1 < t < word_t("ditch", "ditch") + 0.6) else 0.25
    p = skia.Path(); mid = scr.centerY()
    for i in range(0, 821, 4):
        x = scr.left() + i
        n = math.sin(i * 0.21 + u * 40) * math.sin(i * 0.033 + u * 3) + 0.6 * (rng.random() - 0.5)
        y = mid + n * 150 * talk * (0.6 + 0.4 * math.sin(u * 7 + i * 0.01))
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    gp = P((150, 220, 230), 230, 3)
    cv.drawPath(p, skia.Paint(Color=C((150, 220, 230), 70), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=12,
                              MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
    cv.drawPath(p, gp)
    # dials + label
    for i, dx in enumerate((260, 540, 820)):
        cv.drawCircle(dx, 930, 62, P((34, 38, 46))); cv.drawCircle(dx, 930, 62, P(STEEL, 160, 3))
        a = math.radians(-60 + i * 50 + 6 * math.sin(u * 2 + i))
        cv.drawLine(dx, 930, dx + math.sin(a) * 48, 930 - math.cos(a) * 48, P(ICE, 230, 6))
    text(cv, "LAST MESSAGE PICKED UP", 540, 350, font("typeb", 30), STEEL, 220, "c", shadow=False)
    if (u * 2) % 2 < 1.2:
        cv.drawCircle(940, 340, 10, P(RED))


def sc_rescue(cv, t):
    u = t - CUT["rescue"]
    draw_sea(cv, t, (6, 8, 14), (18, 22, 32), (12, 15, 22), horizon=860, chop=2.2, fog=0.5)
    # rain streaks
    for i in range(90):
        x = (i * 137 + u * 300) % (W + 200) - 100; y = (i * 263 + u * 1300) % 900
        cv.drawLine(x, y, x - 14, y + 46, P(ICE, 40, 1.5))
    x = 470 + u * 30; y = 900 - u * 95; sc = 1.75 - u * 0.12
    flying_boat(cv, x, y, sc, 8, (40, 47, 58), 255)
    # navigation lights blinking on the wingtips
    if (u * 1.6) % 1 < 0.35:
        ca, sa = math.cos(math.radians(8)), math.sin(math.radians(8))
        for wx, col in ((-150, RED), (150, (80, 220, 120))):
            cv.drawCircle(x + wx * sc * ca, y + wx * sc * sa, 8, P(col))


def sc_flames(cv, t):
    u = t - CUT["flames"]
    draw_sea(cv, t, (4, 6, 10), (14, 17, 26), (9, 11, 16), horizon=820, chop=1.8, fog=0.35)
    tanker(cv, 300 - u * 8, 834, 1.5)
    fb = word_t("flames", "burst")
    k = t - fb
    if k > 0:
        bx, by = 790, 660
        fl = (0.35 + 0.65 * math.exp(-k * 0.9)) * (1 + 0.18 * math.sin(k * 31) * math.sin(k * 7))
        glow = skia.GradientShader.MakeRadial((bx, by), 520, [C(AMBER, 210 * fl), C((200, 60, 20), 70 * fl), C((0, 0, 0), 0)])
        cv.drawRect(skia.Rect(0, 0, W, 1100), skia.Paint(Shader=glow, BlendMode=skia.BlendMode.kPlus))
        fr = np.random.default_rng(int(k * 30))
        for j in range(14):   # flickering fire tongues, falling slowly
            ox = fr.normal(0, 26); h = fr.uniform(40, 120) * fl; wdt = fr.uniform(14, 34)
            cy_ = by + 40 * k
            pth = skia.Path(); pth.moveTo(bx + ox - wdt, cy_); pth.quadTo(bx + ox, cy_ - h * 1.4, bx + ox + wdt, cy_); pth.close()
            cv.drawPath(pth, skia.Paint(Color=C((255, 140 + int(fr.uniform(0, 90)), 50), 200 * min(1, fl)), AntiAlias=True,
                                        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4)))
        cv.drawCircle(bx, by + 40 * k, 30 * fl + 6, P((255, 235, 190), 255 * min(1, fl * 1.5)))
        # reflection on the water
        rp = skia.Paint(Color=C(AMBER, 120 * fl), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18), BlendMode=skia.BlendMode.kPlus)
        cv.drawRect(skia.Rect(bx - 40, 830, bx + 40, 1150), rp)


def sc_gone(cv, t):
    u = t - CUT["gone"]
    draw_sea(cv, t, (4, 5, 9), (10, 12, 18), (8, 10, 14), horizon=700, chop=1.2, fog=0.6)
    # case card with stats revealed from under redaction bars
    cx0, cy0 = 120, 230
    card = skia.Rect(cx0, cy0, 960, 980)
    cv.save(); cv.rotate(-1.5)
    cv.drawRoundRect(card, 10, 10, P((214, 206, 186)))
    cv.drawImageRect(PAPER, card, SAMP, skia.Paint(Alphaf=0.25, BlendMode=skia.BlendMode.kMultiply))
    text(cv, "CASE FILE #002 · FLIGHT 19", cx0 + 50, cy0 + 80, font("typeb", 36), (40, 36, 30), 255, shadow=False)
    cv.drawLine(cx0 + 50, cy0 + 105, 910, cy0 + 105, P((60, 54, 46), 255, 2))
    rows = [("MEN LOST", "27", word_t("gone", "twenty-seven")), ("AIRCRAFT", "6", word_t("gone", "six")),
            ("WRECKAGE FOUND", "NONE", word_t("gone", "no"))]
    for i, (lab, val, tt) in enumerate(rows):
        y = cy0 + 230 + i * 160
        text(cv, lab, cx0 + 50, y, font("type", 40), (60, 54, 46), 255, shadow=False)
        text(cv, val, 900, y + 8, font("bebas", 110), (24, 22, 20), 255, "r", shadow=False)
        rev = ease((t - tt + 0.05) / 0.35)
        bw = 330 * (1 - rev)
        if bw > 1:
            cv.drawRect(skia.Rect(900 - 330 + (330 - bw), y - 82, 900 + 6, y + 22), P((14, 14, 14)))
    cv.restore()
    a = ease((t - word_t("gone", "found") + 0.1) / 0.25)
    if a > 0:
        stamp(cv, "NEVER FOUND", 560, 900, -11, 1 + 0.6 * (1 - a), a)


def sc_end(cv, t):
    u = t - CUT["end"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((8, 10, 14)))
    draw_sea(cv, t, (4, 5, 9), (10, 12, 18), (8, 10, 14), horizon=700, chop=1.0, fog=0.8)
    for i in range(5):  # five faint aircraft fading into fog
        plane_top(cv, 540 + (i - 2) * 140, 470 + abs(i - 2) * 70 - u * 10, 0.75, 0, ICE, 60 * (1 - ease(u / 3.5)))
    f = font("typeb", 46)
    text(cv, "OFFICIAL CAUSE:", 540, 820, f, ICE, 230, "c")
    a = ease((t - word_t("end", "unknown") + 0.1) / 0.3)
    if a > 0:
        stamp(cv, "UNKNOWN", 540, 960, -6, 1 + 0.5 * (1 - a), a, 120)


def stamp(cv, s, x, y, rot, scale, a, size=104):
    cv.save(); cv.translate(x, y); cv.rotate(rot); cv.scale(scale, scale)
    f = font("bebas", size)
    w = f.measureText(s)
    r = skia.Rect(-w / 2 - 30, -size * 0.78, w / 2 + 30, size * 0.22)
    cv.drawRoundRect(r, 8, 8, P(RED, 235 * a, 7))
    cv.drawString(s, -w / 2, 0, f, P(RED, 235 * a))
    # worn ink: knock out speckles
    sp = P((0, 0, 0), 0)
    sp.setBlendMode(skia.BlendMode.kDstOut)
    r2 = np.random.default_rng(len(s))
    for _ in range(160):
        px, py = r2.uniform(r.left(), r.right()), r2.uniform(r.top(), r.bottom())
        sp.setColor(C((0, 0, 0), 120 * a)); cv.drawCircle(px, py, r2.uniform(0.8, 2.6), sp)
    cv.restore()


SCENE_FN = {"takeoff": sc_takeoff, "compass": sc_compass, "keys": lambda cv, t: draw_map(cv, t, CUT["keys"], "keys"),
            "sunset": sc_sunset, "ditch": sc_ditch, "rescue": sc_rescue, "flames": sc_flames, "gone": sc_gone, "end": sc_end}
STAMPTIME = {"takeoff": "2:10 PM", "compass": "3:40 PM", "keys": "3:40 PM", "sunset": "5:30 PM", "ditch": "7:04 PM",
             "rescue": "7:30 PM", "flames": "7:50 PM", "gone": "DEC 1945", "end": "STILL OPEN"}
HEAD = {"takeoff": "5 BOMBERS. 14 MEN.", "compass": "“BOTH MY COMPASSES ARE OUT”", "keys": "LOST – BUT WHERE?",
        "sunset": "NIGHT FALLS. FUEL LOW.", "ditch": "“WE'LL HAVE TO DITCH”", "rescue": "RESCUE PLANE · 13 MEN",
        "flames": "A SHIP SEES FLAMES", "gone": "NO TRACE. EVER.", "end": "WHAT HAPPENED?"}
KICKER = "CASE FILE #002 · 5 DEC 1945 · OFF FLORIDA"


def fit(s, fname, size, maxw):
    f = font(fname, size)
    while f.measureText(s) > maxw and size > 30:
        size -= 2; f = font(fname, size)
    return f


def overlay_text(cv, t):
    k = scene_at(t)
    # dark band for legibility
    sh = skia.GradientShader.MakeLinear([(0, 1080), (0, 1820)],
                                        [C((0, 0, 0), 0), C((4, 5, 8), 200), C((4, 5, 8), 200), C((0, 0, 0), 0)],
                                        [0.0, 0.25, 0.84, 1.0])
    cv.drawRect(skia.Rect(0, 1080, W, 1820), skia.Paint(Shader=sh))
    X = 64; MAXW = 830
    hook = t < 3.1
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        # hook frame: big two-line hook + stamp
        f = font("bebas", 128)
        text(cv, "5 PLANES. 14 MEN.", X, 1370, f, WHITE)
        text(cv, "GONE IN ONE NIGHT.", X, 1490, f, WHITE)
        stamp(cv, "NEVER FOUND", 640, 1080, -8, 1.0, 1.0, 96)
    else:
        # ticking clock + timestamp
        ts = STAMPTIME[k]
        cx, cy = X + 34, 1310
        cv.drawCircle(cx, cy, 30, P(ICE, 230, 4))
        sec = math.floor(t * 1.0)
        a = math.radians(sec * 30)
        cv.drawLine(cx, cy, cx + math.sin(a) * 22, cy - math.cos(a) * 22, P(RED, 255, 4))
        cv.drawLine(cx, cy, cx, cy - 15, P(ICE, 255, 4))
        fl = 1.0 if t - CUT[k] > 0.25 else ease((t - CUT[k]) / 0.25)
        text(cv, ts, X + 84, 1336, font("typeb", 76), RED if k in ("ditch", "flames") else WHITE, 255 * fl)
        hf = fit(HEAD[k], "bebas", 96, MAXW)
        text(cv, HEAD[k], X, 1446, hf, WHITE, 255 * fl)
    # live captions: current sentence, words appear as spoken
    cur = [w for w in WORDS if w[1] <= t + 0.02]
    if cur and t < TOTAL - 0.6:
        sid = cur[-1][2]
        last_t = cur[-1][1]
        sent = [w for w in WORDS if w[2] == sid]
        nxt = [w for w in WORDS if w[1] > last_t]
        if sent[-1][1] + 1.6 < t and (not nxt or nxt[0][2] != sid):
            return
        f = font("osw", 50)
        line, lines = "", []
        shown = [w[0] for w in sent if w[1] <= t + 0.02]
        for w in shown:
            tryl = (line + " " + w).strip()
            if f.measureText(tryl) > MAXW and line:
                lines.append(line); line = w
            else:
                line = tryl
        lines.append(line)
        y0 = (1548 if len(lines) == 1 else 1528) if not hook else 1596
        for i, ln in enumerate(lines[-2:]):
            text(cv, ln, X, y0 + i * 62, f, ICE, 245)


def post(cv, surf, t, fi):
    k = scene_at(t)
    # flicker + grain + vignette
    fl = 0.04 + 0.03 * math.sin(t * 23) * math.sin(t * 7.3)
    cv.drawRect(skia.Rect(0, 0, W, H), P((0, 0, 0), 255 * max(0, fl)))
    gp = skia.Paint(Alphaf=0.16, BlendMode=skia.BlendMode.kOverlay)
    g = GRAIN[fi % len(GRAIN)]
    ox = (fi * 37) % 60
    cv.drawImageRect(g, skia.Rect(-ox, -ox, W + 60 - ox, H + 60 - ox), SAMP, gp)
    cv.drawImageRect(VIG, skia.Rect(0, 0, W, H), SAMP, skia.Paint())
    # cut flash + glitch
    dt = t - CUT[k]
    if k != ORDER[0] and 0 <= dt < 0.2:
        a = 1 - dt / 0.2
        snap = surf.makeImageSnapshot()
        r = np.random.default_rng(fi)
        for _ in range(5):
            y = r.uniform(0, H); h = r.uniform(20, 120); dx = r.uniform(-40, 40) * a
            cv.save(); cv.clipRect(skia.Rect(0, y, W, y + h))
            cv.drawImage(snap, dx, 0); cv.restore()
        cv.drawRect(skia.Rect(0, 0, W, H), P(ICE, 120 * a ** 2))


def render_frame(surf, t, fi):
    cv = surf.getCanvas()
    cv.clear(C(BG))
    k = scene_at(t)
    cv.save()
    # slow drift/zoom on every scene
    u = t - CUT[k]
    s = 1.02 + 0.012 * u
    cv.translate(W / 2 + 6 * math.sin(u * 0.3), 760); cv.scale(s, s); cv.translate(-W / 2, -760)
    SCENE_FN[k](cv, t)
    cv.restore()
    overlay_text(cv, t)
    post(cv, surf, t, fi)


def main():
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    if sys.argv[1] == "--still":
        for ts in sys.argv[2].split(","):
            t = float(ts)
            render_frame(surf, t, int(t * FPS))
            surf.makeImageSnapshot().save(f"{sys.argv[3]}_{t:05.2f}.png", skia.kPNG)
        return
    out = sys.argv[1]
    nf = int(math.ceil(TOTAL * FPS))
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(nf):
        render_frame(surf, fi / FPS, fi)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
        if fi % 150 == 0:
            print("frame", fi, "/", nf, flush=True)
    ff.stdin.close(); ff.wait()
    print("done", nf, "frames", round(TOTAL, 2), "s")


if __name__ == "__main__":
    main()
