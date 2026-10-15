"""Render 'Roanoke – one word left behind' (The Vanished Files, One detail format).
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
TOTAL = VO["dur"] + 0.7
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


rng = np.random.default_rng(1590)
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




# ---------------------------------------------------------------- generic props
def ship(cv, x, y, s, a=255, rgb=(10, 12, 16), lamp=True, t=0.0):
    """generic late-1500s three-masted sailing ship silhouette, side view (waterline at y)"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    pa = P(rgb, a)
    h = skia.Path()
    h.moveTo(-210, -95); h.lineTo(-150, -88); h.lineTo(-140, -60); h.lineTo(130, -60); h.lineTo(190, -85); h.lineTo(205, -78)
    h.quadTo(175, -20, 120, 0); h.lineTo(-150, 0); h.quadTo(-195, -30, -210, -95); h.close()
    cv.drawPath(h, pa)
    for mx, mh in ((-100, 230), (10, 290), (115, 210)):
        cv.drawRect(skia.Rect(mx - 4, -60 - mh, mx + 4, -60), pa)
        for (yt, yb, w) in ((-60 - mh + 18, -60 - mh * 0.62, 52), (-60 - mh * 0.56, -60 - mh * 0.2, 70)):
            sail = skia.Path(); sail.moveTo(mx - w * 0.85, yt); sail.lineTo(mx + w * 0.85, yt)
            sail.quadTo(mx + w * 1.05, (yt + yb) / 2, mx + w, yb); sail.lineTo(mx - w, yb)
            sail.quadTo(mx - w * 0.75, (yt + yb) / 2, mx - w * 0.85, yt); sail.close()
            cv.drawPath(sail, pa)
    for q in ((205, -80, 300, -140), (-100, -290, 205, -80), (10, -350, 300, -140), (-210, -95, -100, -290)):
        cv.drawLine(q[0], q[1], q[2], q[3], P(rgb, a, 2.5))   # bowsprit + rigging lines
    if lamp:
        fl = 0.8 + 0.2 * math.sin(t * 9) * math.sin(t * 3.1)
        g = skia.GradientShader.MakeRadial((-185, -110), 90, [C(AMBER, 170 * fl * a / 255), C(AMBER, 0)])
        cv.drawCircle(-185, -110, 90, skia.Paint(Shader=g))
        cv.drawCircle(-185, -110, 7, P((255, 210, 140), a))
    cv.restore()


def treeline(cv, y, rgb, a, seed, amp=60, step=18):
    r = np.random.default_rng(seed)
    p = skia.Path(); p.moveTo(-50, H)
    x = -50
    while x < W + 60:
        hgt = r.uniform(0.3, 1.0) * amp
        p.lineTo(x, y); p.lineTo(x + step * 0.5, y - hgt); p.lineTo(x + step, y)
        x += step
    p.lineTo(W + 60, H); p.close()
    cv.drawPath(p, P(rgb, a))


def person(cv, x, y, s, a, rgb=(14, 16, 20)):
    """plain standing silhouette – no face"""
    pa = P(rgb, a)
    cv.drawCircle(x, y - 150 * s, 17 * s, pa)
    b = skia.Path(); b.moveTo(x - 24 * s, y - 128 * s); b.lineTo(x + 24 * s, y - 128 * s); b.lineTo(x + 30 * s, y)
    b.lineTo(x - 30 * s, y); b.close(); cv.drawPath(b, pa)


def fog_bank(cv, t, y, a=1.0, speed=12):
    for j in range(6):
        fx = ((j * 300 + t * (speed + j * 4)) % (W + 900)) - 450
        fp = skia.Paint(Color=C(ICE, 30 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 70))
        cv.drawOval(skia.Rect(fx, y + j * 26 - 60, fx + 760, y + j * 26 + 60), fp)


def palisade(cv, y, x0, x1, rgb, a, seed=3):
    r = np.random.default_rng(seed)
    x = x0
    while x < x1:
        h = r.uniform(190, 240); w = r.uniform(22, 30)
        p = skia.Path(); p.moveTo(x, y); p.lineTo(x, y - h); p.lineTo(x + w / 2, y - h - 22); p.lineTo(x + w, y - h); p.lineTo(x + w, y); p.close()
        cv.drawPath(p, P(rgb, a)); x += w + 3


def night_sky(cv, top, bot, horizon):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, horizon)], [C(top), C(bot)])
    cv.drawRect(skia.Rect(0, 0, W, horizon + 2), skia.Paint(Shader=sh))
    r = np.random.default_rng(7)
    for _ in range(70):
        cv.drawCircle(r.uniform(0, W), r.uniform(0, horizon * 0.7), r.uniform(0.8, 2.0), P(ICE, r.uniform(40, 140)))


# wooden post texture (vertical grain)
_g = np.zeros((480, 120)); _r = np.random.default_rng(11)
for i in range(120):
    _g[:, i] = 0.5 + 0.5 * np.sin(i * 0.9 + _r.normal(0, 0.4)) * _r.uniform(0.3, 1)
_g += _r.normal(0, 0.12, _g.shape)
_g = np.clip(_g, 0, 1)
WOOD = mk_img(np.dstack([(46 + _g * 40).astype(np.uint8), (38 + _g * 30).astype(np.uint8), (30 + _g * 22).astype(np.uint8),
                         np.full(_g.shape, 255, np.uint8)]))


def draw_post(cv, t, reveal_t, zoom=1.0, cross_slot=False):
    """close-up of a palisade post; 'CROATOAN' carved letter by letter from reveal_t"""
    cv.drawRect(skia.Rect(0, 0, W, H), P((6, 8, 11)))
    fog_bank(cv, t, 300, 0.6, 6)
    for i, xo in enumerate((-360, 360)):    # neighbouring posts, dim
        cv.drawImageRect(WOOD, skia.Rect(540 + xo - 120, -40, 540 + xo + 120, 1250), SAMP, skia.Paint(Alphaf=0.35))
    cv.save(); cv.translate(540, 640); cv.scale(zoom, zoom); cv.translate(-540, -640)
    pr = skia.Rect(540 - 190, -60, 540 + 190, 1300)
    cv.drawImageRect(WOOD, pr, SAMP, skia.Paint())
    side = skia.GradientShader.MakeLinear([(pr.left(), 0), (pr.right(), 0)],
                                          [C((0, 0, 0), 170), C((0, 0, 0), 0), C((0, 0, 0), 30), C((0, 0, 0), 200)],
                                          [0, 0.35, 0.6, 1])
    cv.drawRect(pr, skia.Paint(Shader=side))
    # carved letters, stacked vertically down the post
    word = "CROATOAN"
    f = font("bebas", 124)
    n = len(word) if t >= reveal_t + 0.8 else max(0, int((t - reveal_t) / 0.1) + 1) if t >= reveal_t else 0
    for i, ch in enumerate(word[:n]):
        y = 190 + i * 112
        w = f.measureText(ch)
        cv.drawString(ch, 540 - w / 2 + 3, y + 4, f, P((90, 74, 58), 200))       # cut edge highlight
        cv.drawString(ch, 540 - w / 2, y, f, P((16, 11, 8), 245))                # carved groove
    if t >= reveal_t:
        k = t - reveal_t
        glow = skia.GradientShader.MakeRadial((540, 600), 520, [C(AMBER, 60 * math.exp(-k * 0.6)), C(AMBER, 0)])
        cv.drawRect(skia.Rect(0, 0, W, 1250), skia.Paint(Shader=glow, BlendMode=skia.BlendMode.kPlus))
    if cross_slot:
        pass
    cv.restore()


def cross_pattee(cv, x, y, r, paint):
    p = skia.Path()
    for ang in range(0, 360, 90):
        cv.save(); cv.translate(x, y); cv.rotate(ang)
        q = skia.Path(); q.moveTo(-r * 0.12, -r * 0.12); q.lineTo(-r * 0.5, -r); q.quadTo(0, -r * 0.88, r * 0.5, -r)
        q.lineTo(r * 0.12, -r * 0.12); q.close()
        cv.drawPath(q, paint); cv.restore()
    cv.drawRect(skia.Rect(x - r * 0.13, y - r * 0.13, x + r * 0.13, y + r * 0.13), paint)


# ---------------------------------------------------------------- map (lon, lat) – stylised Outer Banks
OUTER = [(-75.74, 36.30), (-75.67, 36.10), (-75.59, 35.95), (-75.52, 35.80), (-75.47, 35.62), (-75.46, 35.45), (-75.49, 35.30),
         (-75.53, 35.23), (-75.62, 35.21), (-75.75, 35.18), (-75.90, 35.11), (-76.02, 35.06)]
INNER = [(-76.02, 35.09), (-75.90, 35.14), (-75.75, 35.21), (-75.63, 35.25), (-75.56, 35.27), (-75.52, 35.35), (-75.50, 35.45),
         (-75.51, 35.62), (-75.56, 35.80), (-75.625, 35.95), (-75.70, 36.10), (-75.77, 36.30)]
ROANOKE = [(-75.73, 35.95), (-75.67, 35.955), (-75.645, 35.90), (-75.65, 35.83), (-75.68, 35.80), (-75.72, 35.84), (-75.735, 35.90)]
MAINLAND = [(-76.60, 36.40), (-75.92, 36.40), (-75.88, 36.15), (-75.82, 35.98), (-75.79, 35.86), (-75.84, 35.72), (-76.00, 35.56),
            (-76.18, 35.42), (-76.33, 35.28), (-76.42, 35.05), (-76.60, 35.00)]
LON0, LON1, LAT0, LAT1 = -76.38, -75.22, 35.12, 36.04
MX0, MY0, MW = 60, 170, 960
ROA = (-75.69, 35.88); CRO = (-75.53, 35.27)


def mp(lon, lat):
    c = math.cos(math.radians(35.6)); k = MW / ((LON1 - LON0) * c)
    return MX0 + (lon - LON0) * c * k, MY0 + (LAT1 - lat) * k


def poly(pts):
    p = skia.Path()
    for i, (lo, la) in enumerate(pts):
        x, y = mp(lo, la); (p.moveTo if i == 0 else p.lineTo)(x, y)
    p.close(); return p


def draw_map(cv, t):
    u = t - CUT["island"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((14, 22, 32)))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, H), SAMP, skia.Paint(Alphaf=0.07, BlendMode=skia.BlendMode.kOverlay))
    for i in range(12):
        lo = -76.3 + i * 0.1; x, _ = mp(lo, 0); cv.drawLine(x, 0, x, 1150, P(STEEL, 26, 1.2))
    for i in range(10):
        la = 35.2 + i * 0.1; _, y = mp(0, la); cv.drawLine(0, y, W, y, P(STEEL, 26, 1.2))
    land = P((58, 70, 84)); edge = P((150, 168, 186), 200, 2.2)
    for path in (poly(MAINLAND), poly(OUTER + INNER), poly(ROANOKE)):
        cv.drawPath(path, land); cv.drawPath(path, edge)
    x, y = mp(-76.25, 35.75); text(cv, "MAINLAND", x, y, font("typeb", 30), ICE, 170)
    x, y = mp(-75.42, 36.0); text(cv, "ATLANTIC", x - 40, y, font("type", 28), STEEL, 170)
    # Roanoke pin
    rx, ry = mp(*ROA)
    cv.drawCircle(rx, ry, 9, P(WHITE)); text(cv, "ROANOKE", rx - 250, ry + 10, font("typeb", 34), WHITE, 235)
    # Croatoan pin (appears with the word)
    cx, cy = mp(*CRO)
    a = ease((t - word_t("island", "croatoan") + 0.2) / 0.4)
    pulse = 1 + 0.25 * math.sin(u * 6)
    cv.drawCircle(cx, cy, 26 * pulse, P(RED, 70 * a)); cv.drawCircle(cx, cy, 11, P(RED, 255 * a))
    text(cv, "CROATOAN", cx - 330, cy - 40, font("typeb", 40), (255, 90, 80), 255 * a)
    text(cv, "(TODAY: HATTERAS ISLAND)", cx - 470, cy + 4, font("type", 26), ICE, 210 * a)
    # dashed route Roanoke -> Croatoan, cut short by the storm
    pts = [mp(*ROA), mp(-75.62, 35.62), mp(-75.58, 35.42), mp(*CRO)]
    st = word_t("island", "storm")
    prog = ease((t - CUT["island"] - 0.6) / 2.8) * 0.62
    segs = list(zip(pts[:-1], pts[1:])); Ls = [math.dist(p, q) for p, q in segs]; tot = sum(Ls) * prog
    path = skia.Path(); path.moveTo(*pts[0]); end = pts[0]
    for (p, q), l in zip(segs, Ls):
        if tot <= 0:
            break
        f_ = min(1, tot / l); end = (p[0] + (q[0] - p[0]) * f_, p[1] + (q[1] - p[1]) * f_); path.lineTo(*end); tot -= l
    rp = P(ICE, 230, 5); rp.setPathEffect(skia.DashPathEffect.Make([18, 12], -u * 40)); cv.drawPath(path, rp)
    # storm
    sa = ease((t - st + 0.3) / 0.6)
    if sa > 0:
        sx, sy = end[0] + 120, end[1] + 40
        for j in range(7):
            cv.save(); cv.translate(sx, sy); cv.rotate(u * 40 + j * 51)
            arc = skia.Path(); arc.addArc(skia.Rect(-60 - j * 34, -60 - j * 34, 60 + j * 34, 60 + j * 34), 0, 200)
            cv.drawPath(arc, skia.Paint(Color=C((150, 160, 175), 110 * sa), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                        StrokeWidth=18, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)))
            cv.restore()
        xp = P(RED, 255 * sa, 9)
        cv.drawLine(end[0] - 30, end[1] - 30, end[0] + 30, end[1] + 30, xp); cv.drawLine(end[0] - 30, end[1] + 30, end[0] + 30, end[1] - 30, xp)
        if (t - st) % 1.7 < 0.08:   # lightning flash
            cv.drawRect(skia.Rect(0, 0, W, 1150), P(ICE, 60))
    text(cv, "MAP STYLISED · POSITIONS APPROX.", 100, 160, font("type", 26), STEEL, 200, shadow=False)


# ---------------------------------------------------------------- scenes
def sc_sail(cv, t):
    u = t - CUT["sail"]
    night_sky(cv, (6, 9, 16), (40, 50, 64), 800)
    mg = skia.GradientShader.MakeRadial((620, 520), 520, [C((150, 165, 185), 110), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 800), skia.Paint(Shader=mg))
    cv.drawCircle(620, 520, 60, P((205, 214, 226), 200))
    # dark island on the horizon
    treeline(cv, 800, (12, 16, 20), 255, 5, amp=34, step=14)
    sh2 = skia.GradientShader.MakeLinear([(0, 800), (0, H)], [C((22, 28, 36)), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, 800, W, H), skia.Paint(Shader=sh2))
    for i in range(40):
        z = i / 40; y = 806 + (z ** 1.9) * (H - 800); amp = (2 + 20 * z ** 2)
        p = skia.Path(); ph = t * (0.7 + z * 1.6) + i * 1.7
        for xi in range(0, W + 40, 40):
            yy = y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph) + amp * 0.5 * math.sin(xi * 0.031 + ph * 1.7)
            (p.moveTo if xi == 0 else p.lineTo)(xi, yy)
        cv.drawPath(p, P(ICE, 16 + 46 * z, 1.2 + 2.4 * z))
    ship(cv, 470 + u * 10, 985 + 6 * math.sin(u * 1.2), 1.25, 255, (7, 9, 12), True, t)
    fog_bank(cv, t, 780, 0.6)


def sc_settlement(cv, t, fade):
    night_sky(cv, (8, 10, 16), (40, 46, 56), 880)
    treeline(cv, 700, (22, 28, 34), 255, 9, amp=110, step=26)
    fog_bank(cv, t, 640, 0.8)
    cv.drawRect(skia.Rect(0, 870, W, H), P((12, 14, 18)))
    palisade(cv, 900, -30, W + 30, (16, 18, 22), 255)
    # settlers standing in the clearing (plain silhouettes), fading away in the 'gone' scene
    r = np.random.default_rng(3)
    for row in range(3):
        for i in range(13):
            x = 40 + i * 80 + r.uniform(-20, 20) + row * 30; y = 960 + row * 60
            s = 0.62 + row * 0.12
            fa = fade(i, row)
            if fa > 0:
                person(cv, x, y, s, 255 * fa, (24 + row * 4, 27 + row * 4, 33 + row * 4))
    cv.drawRect(skia.Rect(0, 1110, W, H), P((8, 9, 12)))
    fog_bank(cv, t, 980, 0.7, 18)


def sc_waited(cv, t):
    u = t - CUT["waited"]
    sc_settlement(cv, t, lambda i, row: ease((u * 3 - (i + row * 4) * 0.12)))


def sc_gone(cv, t):
    u = t - CUT["gone"]
    sc_settlement(cv, t, lambda i, row: 1 - ease((u * 1.8 - ((i * 7 + row * 5) % 13) * 0.1)))
    # a single lantern left on the ground
    fl = 0.8 + 0.2 * math.sin(t * 8) * math.sin(t * 2.3)
    g = skia.GradientShader.MakeRadial((760, 1060), 160, [C(AMBER, 120 * fl), C(AMBER, 0)])
    cv.drawCircle(760, 1060, 160, skia.Paint(Shader=g))
    cv.drawRoundRect(skia.Rect(744, 1030, 776, 1076), 6, 6, P((30, 26, 20)))
    cv.drawRect(skia.Rect(750, 1038, 770, 1068), P((255, 200, 120), 220 * fl))


def sc_word(cv, t):
    u = t - CUT["word"]
    draw_post(cv, t, word_t("reveal", "croatoan") - 0.05, 0.94 + 0.02 * u)
    # redaction bar hiding where the carving is (teases the word)
    cv.drawRect(skia.Rect(400, 60, 680, 1080), P((10, 10, 10), 230))
    text(cv, "?", 540, 640, font("bebas", 200), RED, 220 + 35 * math.sin(u * 5), "c", shadow=False)


def sc_reveal(cv, t):
    u = t - CUT["reveal"]
    draw_post(cv, t, word_t("reveal", "croatoan") - 0.05, 0.98 + 0.03 * u)


def sc_signal(cv, t):
    u = t - CUT["signal"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((8, 10, 14)))
    fog_bank(cv, t, 300, 0.5)
    card = skia.Rect(130, 200, 950, 1080)
    cv.save(); cv.rotate(-1.2)
    cv.drawRoundRect(card, 10, 10, P((214, 206, 186)))
    cv.drawImageRect(PAPER, card, SAMP, skia.Paint(Alphaf=0.25, BlendMode=skia.BlendMode.kMultiply))
    ink = (40, 36, 30)
    text(cv, "THE AGREED SIGNAL · 1587", 180, 280, font("typeb", 36), ink, 255, shadow=False)
    cv.drawLine(180, 305, 900, 305, P((60, 54, 46), 255, 2))
    a1 = ease((t - word_t("signal", "if") + 0.1) / 0.3)
    text(cv, "MOVED ON? CARVE WHERE.", 180, 400, font("type", 40), ink, 255, shadow=False)
    text(cv, "FORCED OUT? ADD A CROSS:", 180, 470, font("type", 40), ink, 255 * a1, shadow=False)
    a2 = ease((t - word_t("signal", "cross") + 0.15) / 0.35)
    if a2 > 0:
        cross_pattee(cv, 540, 760, 190 * (0.8 + 0.2 * a2), P((150, 26, 26), 235 * a2))
    text(cv, "(AS JOHN WHITE LATER DESCRIBED IT)", 540, 1040, font("type", 26), (90, 82, 70), 220, "c", shadow=False)
    cv.restore()


def sc_nocross(cv, t):
    u = t - CUT["nocross"]
    draw_post(cv, t, -10, 0.9)
    # empty dashed outline where the cross would be
    dp = P(ICE, 200, 5); dp.setPathEffect(skia.DashPathEffect.Make([14, 10], -u * 30))
    cv.drawCircle(540, 640, 220, dp)
    a = ease((t - word_t("nocross", "cross") + 0.05) / 0.25)
    if a > 0:
        stamp(cv, "NO CROSS", 540, 980, -9, 1 + 0.6 * (1 - a), a, 140)


def sc_end(cv, t):
    u = t - CUT["end"]
    night_sky(cv, (5, 7, 12), (26, 32, 42), 900)
    treeline(cv, 900, (14, 18, 22), 255, 21, amp=220, step=34)
    fog_bank(cv, t, 820, 1.0)
    cv.drawRect(skia.Rect(0, 895, W, H), P((9, 11, 14)))
    # the lone post with the word, small, in the fog
    cv.drawImageRect(WOOD, skia.Rect(510, 560, 570, 1000), SAMP, skia.Paint())
    f = font("bebas", 30)
    for i, ch in enumerate("CROATOAN"):
        w = f.measureText(ch); cv.drawString(ch, 540 - w / 2, 610 + i * 34, f, P((16, 11, 8), 240))
    fog_bank(cv, t, 950, 0.7, 20)
    a = ease((t - word_t("end", "unsolved") + 0.1) / 0.3)
    if a > 0:
        stamp(cv, "UNSOLVED", 540, 400, -7, 1 + 0.5 * (1 - a), a, 130)


SCENE_FN = {"sail": sc_sail, "waited": sc_waited, "gone": sc_gone, "word": sc_word, "reveal": sc_reveal,
            "signal": sc_signal, "nocross": sc_nocross, "island": draw_map, "end": sc_end}
HEAD = {"sail": "THE GOVERNOR RETURNS", "waited": "100+ SETTLERS", "gone": "ALL GONE. NO STRUGGLE.",
        "word": "ONE CLUE LEFT BEHIND", "reveal": "“CROATOAN”", "signal": "THE AGREED SIGNAL",
        "nocross": "NO DISTRESS SIGN", "island": "THE ISLAND HE NEVER REACHED", "end": "WHERE DID THEY GO?"}
KICKER = "CASE FILE #003 · AUG 1590 · ROANOKE ISLAND"


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


def fit(s, fname, size, maxw):
    f = font(fname, size)
    while f.measureText(s) > maxw and size > 30:
        size -= 2; f = font(fname, size)
    return f



def pill(cv, s, x, y, a=255):
    f = font("typeb", 30); w = f.measureText(s)
    cv.drawRoundRect(skia.Rect(x, y - 34, x + w + 36, y + 12), 23, 23, P(RED, 235 * a / 255))
    cv.drawString(s, x + 18, y, f, P(WHITE, a))


def overlay_text(cv, t):
    k = scene_at(t)
    sh = skia.GradientShader.MakeLinear([(0, 1080), (0, 1820)],
                                        [C((0, 0, 0), 0), C((4, 5, 8), 205), C((4, 5, 8), 205), C((0, 0, 0), 0)],
                                        [0.0, 0.25, 0.84, 1.0])
    cv.drawRect(skia.Rect(0, 1080, W, 1820), skia.Paint(Shader=sh))
    X = 64; MAXW = 830
    hook = t < 3.0
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        f = fit("100+ PEOPLE VANISHED.", "bebas", 132, 900)
        text(cv, "100+ PEOPLE VANISHED.", X, 1370, f, WHITE)
        text(cv, "ONE WORD WAS LEFT.", X, 1490, f, WHITE)
        stamp(cv, "NEVER FOUND", 660, 1090, -8, 1.0, 1.0, 96)
    else:
        fl = 1.0 if t - CUT[k] > 0.25 else ease((t - CUT[k]) / 0.25)
        if ORDER.index(k) >= ORDER.index("reveal"):
            pill(cv, "THE ONE DETAIL", X, 1316, 255 * fl)
        hf = fit(HEAD[k], "bebas", 100, MAXW)
        text(cv, HEAD[k], X, 1436, hf, (255, 90, 80) if k in ("reveal", "nocross") else WHITE, 255 * fl)
    cur = [w for w in WORDS if w[1] <= t + 0.02]
    if cur and t < TOTAL - 0.4:
        sid = cur[-1][2]; last_t = cur[-1][1]
        sent = [w for w in WORDS if w[2] == sid]
        nxt = [w for w in WORDS if w[1] > last_t]
        if sent[-1][1] + 1.6 < t and (not nxt or nxt[0][2] != sid):
            return
        f = font("osw", 50)
        line, lines = "", []
        for w in [w[0] for w in sent if w[1] <= t + 0.02]:
            tryl = (line + " " + w).strip()
            if f.measureText(tryl) > MAXW and line:
                lines.append(line); line = w
            else:
                line = tryl
        lines.append(line)
        y0 = (1540 if len(lines) == 1 else 1520) if not hook else 1590
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
