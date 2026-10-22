"""Render 'Carroll A. Deering – the last sightings' (The Vanished Files, Last known moments format).
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


rng = np.random.default_rng(1921)
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

# ---------------------------------------------------------------- map data (lon, lat) – simplified, approximate outlines
COAST = [(-80.5, 33.0), (-79.2, 33.0), (-78.9, 33.6), (-78.55, 33.85), (-78.2, 33.92), (-77.96, 33.84), (-77.9, 34.1),
         (-77.7, 34.32), (-77.35, 34.55), (-77.1, 34.66), (-76.75, 34.7), (-76.53, 34.6), (-76.42, 34.75), (-76.2, 34.88),
         (-75.95, 35.05), (-75.75, 35.19), (-75.53, 35.23), (-75.47, 35.55), (-75.53, 35.85), (-75.62, 36.15),
         (-75.8, 36.5), (-75.92, 36.8), (-75.98, 36.95), (-76.25, 36.97), (-76.35, 37.1), (-76.3, 37.5), (-80.5, 37.5)]
EASTSHORE = [(-75.97, 37.14), (-75.75, 37.4), (-75.55, 37.5), (-76.05, 37.5), (-76.02, 37.25)]
LON0, LON1, LAT0, LAT1 = -79.3, -74.2, 32.9, 37.45
MX0, MY0, MW = 40, 120, 1000


def mp(lon, lat):
    k = MW / ((LON1 - LON0) * math.cos(math.radians(35)))
    return MX0 + (lon - LON0) * math.cos(math.radians(35)) * k, MY0 + (LAT1 - lat) * k


def poly(pts, close=True):
    p = skia.Path()
    for i, (lo, la) in enumerate(pts):
        x, y = mp(lo, la)
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    if close:
        p.close()
    return p


LIGHTSHIP = (-76.38, 34.47)     # Cape Lookout lightship (approx.)
SHOALS = (-75.36, 35.13)        # outer Diamond Shoals (approx.)
HAMPTON = (-76.3, 37.0)         # Hampton Roads, where she was bound
ROUTE = [(-77.2, 33.05), (-76.75, 33.8), LIGHTSHIP, (-75.9, 34.8), SHOALS]


def draw_map(cv, t, t0):
    u = t - t0
    cv.drawRect(skia.Rect(0, 0, W, H), P((14, 22, 32)))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, H), SAMP, skia.Paint(Alphaf=0.07, BlendMode=skia.BlendMode.kOverlay))
    for lo in range(-79, -73):
        x, _ = mp(lo, 0); cv.drawLine(x, 0, x, 1250, P(STEEL, 30, 1.2))
    for la in range(33, 38):
        _, y = mp(0, la); cv.drawLine(0, y, W, y, P(STEEL, 30, 1.2))
        text(cv, f"{la}°N", W - 90, y - 6, font("type", 20), STEEL, 90, shadow=False)
    land = P((58, 70, 84)); edge = P((150, 168, 186), 200, 2.2)
    for path in (poly(COAST), poly(EASTSHORE)):
        cv.drawPath(path, land); cv.drawPath(path, edge)
    text(cv, "NORTH CAROLINA", 90, mp(0, 35.9)[1], font("typeb", 34), ICE, 200)
    text(cv, "ATLANTIC OCEAN", 560, mp(0, 33.7)[1], font("type", 30), STEEL, 170)
    hx, hy = mp(*HAMPTON)
    cv.drawCircle(hx, hy, 7, P(WHITE)); text(cv, "BOUND FOR HAMPTON ROADS", hx + 20, hy - 14, font("type", 22), WHITE, 210)
    # route drawn progressively
    pts = [mp(*q) for q in ROUTE]
    prog = ease(u / 3.0)
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
    text(cv, "FROM BARBADOS", pts[0][0] + 20, pts[0][1] - 10, font("type", 22), ICE, 200)
    lx, ly = mp(*LIGHTSHIP)
    pulse = 0.5 + 0.5 * math.sin(u * 5)
    cv.drawCircle(lx, ly, 22 + 10 * pulse, P(AMBER, 60)); cv.drawCircle(lx, ly, 9, P(AMBER))
    text(cv, "CAPE LOOKOUT LIGHTSHIP", lx - 430, ly + 10, font("typeb", 26), (255, 190, 120), 240)
    sx, sy = mp(*SHOALS)
    cv.drawCircle(sx, sy, 7, P(STEEL, 200))
    text(cv, "DIAMOND SHOALS", sx + 18, sy + 8, font("typeb", 26), ICE, 220)
    # ship marker at the head of the route
    cv.drawCircle(end[0], end[1], 12, P(WHITE)); cv.drawCircle(end[0], end[1], 12, P(RED, 255, 3))
    text(cv, "MAP APPROX.", 40, 1150, font("type", 24), STEEL, 180, shadow=False)


# ---------------------------------------------------------------- sea / sky
def draw_sea(cv, t, sky_top, sky_bot, sea_col, horizon=820, sun=None, chop=1.0, fog=0.5):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, horizon)], [C(sky_top), C(sky_bot)])
    cv.drawRect(skia.Rect(0, 0, W, horizon + 2), skia.Paint(Shader=sh))
    if sun is not None:
        sx, sy, sa = sun
        glow = skia.GradientShader.MakeRadial((sx, sy), 420, [C(AMBER, 120 * sa), C(AMBER, 0)])
        cv.drawRect(skia.Rect(0, 0, W, horizon), skia.Paint(Shader=glow))
    sh2 = skia.GradientShader.MakeLinear([(0, horizon), (0, H)], [C(sea_col), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, horizon, W, H), skia.Paint(Shader=sh2))
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
    for j in range(5):
        fx = ((j * 340 + t * (14 + j * 5)) % (W + 900)) - 450
        fy = horizon - 60 + j * 22
        fp = skia.Paint(Color=C(ICE, 26 * fog), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
        cv.drawOval(skia.Rect(fx, fy - 50, fx + 700, fy + 50), fp)


def schooner(cv, x, y, s, tilt=0.0, hull=(12, 14, 18), sail=(150, 160, 170), a=255, torn=False):
    """generic five-masted schooner, side view, bow to the right; (x, y) = waterline centre"""
    cv.save(); cv.translate(x, y); cv.rotate(tilt); cv.scale(s, s)
    hp = P(hull, a)
    h = skia.Path(); h.moveTo(-250, -40); h.lineTo(262, -46); h.lineTo(238, 8); h.lineTo(-232, 8); h.close()
    cv.drawPath(h, hp)
    cv.drawLine(255, -42, 330, -78, P(hull, a, 4))             # bowsprit
    mast_x = [-180, -95, -10, 75, 160]
    for i, mx in enumerate(mast_x):
        top = -330 + abs(i - 2) * 6
        cv.drawLine(mx, -40, mx, top, P(hull, a, 5))
        sp = skia.Path()                                        # gaff sail (fore-and-aft)
        sp.moveTo(mx + 4, top + 22); sp.lineTo(mx + 70, top + 6); sp.lineTo(mx + 74, -58); sp.lineTo(mx + 4, -58); sp.close()
        cv.drawPath(sp, P(sail, a * 0.92))
        cv.drawPath(sp, P(hull, a * 0.5, 2))
        if torn and i in (1, 3):
            cv.drawLine(mx + 30, top + 60, mx + 52, top + 140, P((40, 44, 50), a, 5))
    jib = skia.Path(); jib.moveTo(168, -300); jib.lineTo(318, -76); jib.lineTo(176, -60); jib.close()
    cv.drawPath(jib, P(sail, a * 0.85))
    cv.restore()


def breakers(cv, t, y, x0, x1, k=1.0):
    r = np.random.default_rng(7)
    for j in range(26):
        bx = r.uniform(x0, x1); ph = r.uniform(0, 6.28); sp = r.uniform(1.2, 2.2)
        hh = (0.5 + 0.5 * math.sin(t * sp + ph)) * r.uniform(30, 80) * k
        fp = skia.Paint(Color=C(WHITE, 120 * k), AntiAlias=True, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        cv.drawOval(skia.Rect(bx - 90, y - hh, bx + 90, y + 18), fp)


def lightvessel(cv, x, y, s, t, a=255):
    """generic lightship: low hull, one mast with a lantern"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    pa = P((12, 14, 18), a)
    h = skia.Path(); h.moveTo(-130, -30); h.lineTo(140, -34); h.lineTo(120, 10); h.lineTo(-115, 10); h.close(); cv.drawPath(h, pa)
    cv.drawRect(skia.Rect(-40, -62, 20, -30), pa)
    cv.drawLine(0, -30, 0, -230, P((12, 14, 18), a, 7))
    cv.drawRect(skia.Rect(-16, -250, 16, -214), pa)
    on = 0.6 + 0.4 * math.sin(t * 3)
    glow = skia.GradientShader.MakeRadial((0, -232), 160, [C(AMBER, 230 * on), C(AMBER, 0)])
    cv.drawCircle(0, -232, 160, skia.Paint(Shader=glow, BlendMode=skia.BlendMode.kPlus))
    cv.drawCircle(0, -232, 12, P((255, 230, 180), a))
    cv.restore()


def lighthouse(cv, x, y, s, t, a=255):
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    tw = skia.Path(); tw.moveTo(-22, 0); tw.lineTo(-12, -200); tw.lineTo(12, -200); tw.lineTo(22, 0); tw.close()
    cv.drawPath(tw, P((14, 16, 20), a))
    cv.drawRect(skia.Rect(-15, -222, 15, -200), P((14, 16, 20), a))
    ang = t * 1.2
    for d in (0, math.pi):
        bx = math.cos(ang + d)
        if bx > -0.2:
            beam = skia.Path(); beam.moveTo(0, -211); beam.lineTo(900 * bx, -260); beam.lineTo(900 * bx, -160); beam.close()
            cv.drawPath(beam, skia.Paint(Color=C((255, 230, 180), 26 * max(0, bx) * a / 255), AntiAlias=True,
                                         MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12)))
    cv.drawCircle(0, -211, 7, P((255, 230, 180), a))
    cv.restore()


# ---------------------------------------------------------------- scenes
def sc_hook(cv, t):
    u = t
    draw_sea(cv, t, (30, 38, 50), (84, 96, 110), (30, 38, 48), horizon=760, chop=1.4, fog=1.1)
    breakers(cv, t, 860, 120, 980, 1.0)
    schooner(cv, 560, 850, 1.25, -5 + 0.8 * math.sin(u * 0.9), sail=(178, 186, 194))
    breakers(cv, t + 1.3, 905, 60, 1040, 0.8)


def sc_lightship(cv, t):
    draw_map(cv, t, CUT["lightship"])


def sc_shout(cv, t):
    u = t - CUT["shout"]
    draw_sea(cv, t, (22, 28, 40), (70, 80, 96), (24, 30, 40), horizon=780, chop=1.0, fog=0.9)
    schooner(cv, 700 - u * 20, 810, 0.85, 0.6 * math.sin(u), sail=(160, 168, 178))
    lightvessel(cv, 250, 980, 1.25, t)
    # sound rings from the schooner, while the shout is heard
    ts = word_t("shout", "we've") - 0.1
    if ts - 0.2 < t < ts + 2.4:
        for j in range(3):
            r = ((t - ts) * 160 + j * 70) % 260
            cv.drawCircle(700 - u * 20 + 120, 470, 30 + r, P(ICE, 140 * (1 - r / 260), 3))
    # "not an officer" note on a paper slip
    a = ease((t - word_t("shout", "officer") + 0.6) / 0.4)
    if a > 0:
        cv.save(); cv.rotate(-3)
        card = skia.Rect(470, 300, 1000, 470)
        cv.drawRoundRect(card, 6, 6, P((214, 206, 186), 255 * a))
        cv.drawImageRect(PAPER, card, SAMP, skia.Paint(Alphaf=0.25 * a, BlendMode=skia.BlendMode.kMultiply))
        text(cv, "LIGHTSHIP KEEPER'S NOTE", 500, 352, font("typeb", 28), (60, 54, 46), 255 * a, shadow=False)
        text(cv, "SPEAKER: NOT AN OFFICER", 500, 420, font("type", 34), (30, 28, 24), 255 * a, shadow=False)
        cv.restore()


def sc_course(cv, t):
    u = t - CUT["course"]; dur = CUT["aground"] - CUT["course"]
    k = ease(u / dur)
    draw_sea(cv, t, (40, 34, 48), (150, 82, 60), (26, 28, 38), horizon=800, sun=(260, 800 + 40 * k, 0.8 - 0.4 * k),
             chop=1.2, fog=0.6)
    breakers(cv, t, 830, 640, 1080, 0.6)
    sx = 260 + u * 70
    schooner(cv, sx, 815, 0.55, 0, sail=(110, 104, 110))
    # dashed course arrow heading straight into the breakers
    pth = skia.Path(); pth.moveTo(sx + 190, 760); pth.lineTo(900, 780)
    dp = P(RED, 230, 5); dp.setPathEffect(skia.DashPathEffect.Make([16, 12], -u * 50)); cv.drawPath(pth, dp)
    ar = skia.Path(); ar.moveTo(930, 781); ar.lineTo(896, 760); ar.lineTo(898, 802); ar.close(); cv.drawPath(ar, P(RED))
    text(cv, "SHOALS", 900, 730, font("typeb", 34), (255, 90, 80), 240, "c")


def sc_aground(cv, t):
    u = t - CUT["aground"]
    draw_sea(cv, t, (20, 26, 38), (110, 112, 120), (30, 36, 46), horizon=760, chop=2.2, fog=1.0)
    lighthouse(cv, 120, 760, 0.9, t, 200)
    breakers(cv, t, 870, 200, 1080, 1.2)
    schooner(cv, 600, 880, 1.15, -7, sail=(176, 182, 190), torn=True)
    breakers(cv, t + 2.0, 930, 100, 1080, 1.0)
    # "lifeboats gone": empty davits outline
    a = ease((t - word_t("aground", "lifeboats") + 0.1) / 0.3)
    if a > 0:
        f = font("typeb", 48); w = f.measureText("LIFEBOATS: GONE")
        cv.drawRoundRect(skia.Rect(540 - w / 2 - 28, 340, 540 + w / 2 + 28, 420), 40, 40, P((10, 10, 12), 220 * a))
        cv.drawRoundRect(skia.Rect(540 - w / 2 - 28, 340, 540 + w / 2 + 28, 420), 40, 40, P(RED, 255 * a, 4))
        text(cv, "LIFEBOATS: GONE", 540, 397, f, (255, 90, 80), 255 * a, "c")


def sc_board(cv, t):
    u = t - CUT["board"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((10, 12, 16)))
    # galley table under a swinging lantern
    sw = 6 * math.sin(u * 1.4)
    lx = 540 + sw * 8
    glow = skia.GradientShader.MakeRadial((lx, 300), 700, [C(AMBER, 90), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 1200), skia.Paint(Shader=glow))
    cv.drawLine(540, 0, lx, 250, P((40, 40, 44), 255, 4))
    cv.drawRoundRect(skia.Rect(lx - 34, 250, lx + 34, 340), 10, 10, P((30, 28, 26)))
    cv.drawRoundRect(skia.Rect(lx - 24, 262, lx + 24, 328), 8, 8, P((255, 200, 120), 230))
    tb = skia.Path(); tb.moveTo(80, 760); tb.lineTo(1000, 760); tb.lineTo(1080, 1000); tb.lineTo(0, 1000); tb.close()
    cv.drawPath(tb, P((48, 36, 28)))
    for i in range(6):
        cv.drawLine(80 - i * 14, 760 + i * 46, 1000 + i * 14, 760 + i * 46, P((30, 22, 16), 160, 2))
    for px in (250, 540, 830):      # plates, untouched
        cv.drawOval(skia.Rect(px - 95, 820, px + 95, 880), P((200, 196, 186)))
        cv.drawOval(skia.Rect(px - 60, 832, px + 60, 868), P((170, 164, 150)))
    cv.drawRoundRect(skia.Rect(420, 640, 660, 780), 20, 20, P((26, 26, 30)))   # pot
    for j in range(3):   # faint steam
        sy = 620 - ((u * 40 + j * 50) % 150)
        cv.drawOval(skia.Rect(480 + j * 40, sy - 30, 540 + j * 40, sy + 30),
                    skia.Paint(Color=C(ICE, 30), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)))
    # inventory card revealed from under redaction bars
    cv.save(); cv.rotate(-1.5)
    card = skia.Rect(140, 120, 940, 560)
    a0 = ease((t - word_t("board", "log") + 0.6) / 0.4)
    if a0 > 0:
        cv.drawRoundRect(card, 10, 10, P((214, 206, 186), 255 * a0))
        cv.drawImageRect(PAPER, card, SAMP, skia.Paint(Alphaf=0.25 * a0, BlendMode=skia.BlendMode.kMultiply))
        text(cv, "BOARDED · FEB 4, 1921", 180, 185, font("typeb", 34), (40, 36, 30), 255 * a0, shadow=False)
        cv.drawLine(180, 205, 900, 205, P((60, 54, 46), 255 * a0, 2))
        rows = [("SHIP'S LOG", "MISSING", word_t("board", "log")), ("CREW", "NONE", word_t("board", "crew"))]
        for i, (lab, val, tt) in enumerate(rows):
            y = 310 + i * 150
            text(cv, lab, 180, y, font("type", 40), (60, 54, 46), 255 * a0, shadow=False)
            text(cv, val, 900, y + 8, font("bebas", 100), (150, 24, 24) if val == "NONE" else (24, 22, 20), 255 * a0, "r",
                 shadow=False)
            rev = ease((t - tt + 0.05) / 0.35)
            bw = 330 * (1 - rev)
            if bw > 1:
                cv.drawRect(skia.Rect(900 - bw, y - 76, 906, y + 20), P((14, 14, 14), 255 * a0))
    cv.restore()


def sc_theory(cv, t):
    u = t - CUT["theory"]
    draw_sea(cv, t, (6, 8, 12), (16, 20, 28), (10, 12, 16), horizon=900, chop=1.0, fog=0.6)
    for i, (lab, w) in enumerate((("MUTINY?", "mutiny"), ("PIRATES?", "pirates"))):
        a = ease((t - word_t("theory", w) + 0.35) / 0.3)
        if a <= 0:
            continue
        cx = 300 + i * 480; cy = 450 + i * 70; rot = -4 + i * 7
        cv.save(); cv.translate(cx, cy); cv.rotate(rot)
        card = skia.Rect(-210, -150, 210, 150)
        cv.drawRoundRect(card, 8, 8, P((214, 206, 186), 255 * a))
        cv.drawImageRect(PAPER, card, SAMP, skia.Paint(Alphaf=0.25 * a, BlendMode=skia.BlendMode.kMultiply))
        text(cv, "THEORY", 0, -70, font("typeb", 38), (120, 30, 30), 255 * a, "c", shadow=False)
        text(cv, lab, 0, 40, font("bebas", 110), (24, 22, 20), 255 * a, "c", shadow=False)
        cv.drawLine(-170, 80, 170, 80, P((60, 54, 46), 200 * a, 2))
        text(cv, "UNCONFIRMED", 0, 122, font("type", 30), (60, 54, 46), 255 * a, "c", shadow=False)
        cv.restore()
    a = ease((t - word_t("theory", "proven") + 0.1) / 0.25)
    if a > 0:
        stamp(cv, "NEVER PROVEN", 540, 800, -8, 1 + 0.6 * (1 - a), a, 110)


def sc_end(cv, t):
    u = t - CUT["end"]
    draw_sea(cv, t, (4, 5, 9), (14, 16, 22), (8, 10, 14), horizon=760, chop=1.2, fog=1.1)
    schooner(cv, 540, 780, 0.8, -3, hull=(30, 34, 42), sail=(90, 98, 108), a=255 * (1 - 0.6 * ease(u / 3.0)))
    breakers(cv, t, 790, 200, 900, 0.5)
    text(cv, "STATUS:", 540, 300, font("typeb", 50), ICE, 230, "c")
    a = ease((t - word_t("end", "unsolved") + 0.1) / 0.3)
    if a > 0:
        stamp(cv, "UNSOLVED", 540, 450, -6, 1 + 0.5 * (1 - a), a, 130)


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


SCENE_FN = {"hook": sc_hook, "lightship": sc_lightship, "shout": sc_shout, "course": sc_course, "aground": sc_aground,
            "board": sc_board, "theory": sc_theory, "end": sc_end}
STAMPTIME = {"hook": "", "lightship": "JAN 29, 1921", "shout": "JAN 29, 1921", "course": "JAN 30 · 5:45 PM",
             "aground": "JAN 31 · 6:30 AM", "board": "FEB 4, 1921", "theory": "1921–22 INQUIRY", "end": "STILL OPEN"}
HEAD = {"hook": "", "lightship": "PASSING CAPE LOOKOUT", "shout": "LOST BOTH ANCHORS", "course": "A STRANGE COURSE",
        "aground": "AGROUND. SAILS SET.", "board": "NO ONE ON BOARD", "theory": "THEORIES, NOT FACTS", "end": "WHAT HAPPENED?"}
KICKER = "CASE FILE #006 · JAN 1921 · NORTH CAROLINA"


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
    hook = t < CUT["lightship"]
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        # hook frame: big two-line hook + stamp
        f = font("bebas", 128)
        text(cv, "EVERY SAIL SET.", X, 1370, f, WHITE)
        text(cv, "NOBODY ON BOARD.", X, 1490, f, WHITE)
        stamp(cv, "CREW VANISHED", 560, 300, -7, 1.0, 1.0, 104)
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
        text(cv, ts, X + 84, 1336, font("typeb", 76), RED if k in ("aground", "board") else WHITE, 255 * fl)
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
