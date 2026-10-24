"""Render 'Percy Fawcett – the last letter' (The Vanished Files, Case file format).
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


rng = np.random.default_rng(1925)
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

# ---------------------------------------------------------------- map (lon, lat) – stylised, approximate
LON0, LON1, LAT0, LAT1 = -58.6, -51.4, -16.4, -9.6
MX0, MY0, MW = 40, 110, 1000


def mp(lon, lat):
    k = MW / ((LON1 - LON0) * math.cos(math.radians(13)))
    return MX0 + (lon - LON0) * math.cos(math.radians(13)) * k, MY0 + (LAT1 - lat) * k


CUIABA = (-56.1, -15.6)
LETTER = (-54.58, -11.72)    # 11°43'S 54°35'W (letter to his wife)
REPORT = (-54.58, -13.72)    # 13°43'S 54°35'W (report to the newspaper alliance)
_r = np.random.default_rng(3)
RIVERS = []
for lon0 in (-55.6, -53.9, -52.6):
    pts = []; lo = lon0
    for la in np.arange(-15.2, -9.4, 0.25):
        lo += _r.normal(0, 0.09); pts.append((lo, la))
    RIVERS.append(pts)


def draw_map(cv, t, mode):
    cv.drawRect(skia.Rect(0, 0, W, H), P((16, 24, 22)))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, H), SAMP, skia.Paint(Alphaf=0.08, BlendMode=skia.BlendMode.kOverlay))
    # forest texture: soft dark blobs
    r = np.random.default_rng(11)
    for _ in range(140):
        x, y, rr = r.uniform(0, W), r.uniform(100, 1250), r.uniform(20, 60)
        cv.drawCircle(x, y, rr, P((30, 46, 36), 70))
    for lo in range(-58, -51):
        x, _ = mp(lo, 0); cv.drawLine(x, 60, x, 1230, P(STEEL, 30, 1.2))
    for la in range(-16, -9):
        _, y = mp(0, la); cv.drawLine(0, y, W, y, P(STEEL, 34, 1.2))
        text(cv, f"{-la}°S", W - 84, y - 6, font("type", 22), STEEL, 120, shadow=False)
    for pts in RIVERS:
        p = skia.Path()
        for i, q in enumerate(pts):
            (p.moveTo if i == 0 else p.lineTo)(*mp(*q))
        cv.drawPath(p, P((90, 130, 160), 150, 3))
    text(cv, "MATO GROSSO, BRAZIL", 80, 180, font("typeb", 34), ICE, 210)
    cx, cy = mp(*CUIABA)
    cv.drawCircle(cx, cy, 8, P(WHITE)); text(cv, "CUIABÁ", cx + 18, cy + 9, font("typeb", 28), WHITE, 230)
    u = t - CUT[mode]
    if mode == "camp":
        tx, ty = mp(*LETTER)
        prog = ease(u / 3.0)
        ex, ey = cx + (tx - cx) * prog, cy + (ty - cy) * prog
        pth = skia.Path(); pth.moveTo(cx, cy); pth.lineTo(ex, ey)
        rp = P(RED, 230, 5); rp.setPathEffect(skia.DashPathEffect.Make([18, 12], -u * 40)); cv.drawPath(pth, rp)
        if prog > 0.95:
            pulse = 0.5 + 0.5 * math.sin(u * 5)
            cv.drawCircle(tx, ty, 24 + 10 * pulse, P(RED, 70)); cv.drawCircle(tx, ty, 10, P(RED))
            text(cv, "DEAD HORSE CAMP", tx + 26, ty + 10, font("typeb", 32), (255, 120, 110), 245)
    else:
        lx, ly = mp(*LETTER); rx, ry = mp(*REPORT)
        a1 = ease((t - word_t("coords", "eleven") + 0.3) / 0.3)
        a2 = ease((t - word_t("coords", "thirteen") + 0.1) / 0.3)
        if a1 > 0:
            cv.drawCircle(lx, ly, 12, P(WHITE, 255 * a1))
            text(cv, "LETTER: 11°43′S", lx + 26, ly + 12, font("typeb", 40), WHITE, 255 * a1)
        if a2 > 0:
            pulse = 0.5 + 0.5 * math.sin(t * 6)
            cv.drawCircle(rx, ry, 26 + 12 * pulse, P(RED, 80 * a2)); cv.drawCircle(rx, ry, 12, P(RED, 255 * a2))
            text(cv, "REPORT: 13°43′S", rx + 26, ry + 12, font("typeb", 40), (255, 110, 100), 255 * a2)
            ap = P(ICE, 200 * a2, 3); ap.setPathEffect(skia.DashPathEffect.Make([10, 10], 0))
            cv.drawLine(lx - 40, ly + 20, lx - 40, ry - 20, ap)
            text(cv, "≈220 KM", lx - 60, (ly + ry) / 2 + 12, font("typeb", 34), ICE, 230 * a2, "r")
        if mode == "why":
            # footprints that fade out between the two pins
            for j in range(9):
                fy = ly + (ry - ly) * (j / 8); fx = lx + 140 + 30 * math.sin(j * 1.3) + (16 if j % 2 else -16)
                cv.drawOval(skia.Rect(fx - 9, fy - 15, fx + 9, fy + 15), P(ICE, 140 * (1 - j / 9) * (0.6 + 0.4 * math.sin(t * 2 + j))))
    text(cv, "MAP APPROX.", W - 60, 1060, font("type", 24), STEEL, 180, "r", shadow=False)


# ---------------------------------------------------------------- night jungle
def _layer(seed, ybase, hmin, hmax, rmin, rmax, count):
    r = np.random.default_rng(seed); p = skia.Path()
    p.addRect(skia.Rect(-200, ybase, W + 200, H))
    for _ in range(count):
        x = r.uniform(-150, W + 150); h = r.uniform(hmin, hmax); top = ybase - h
        p.addRect(skia.Rect(x - r.uniform(5, 14), top, x + r.uniform(5, 14), ybase + 5))
        for _ in range(7):
            p.addCircle(x + r.normal(0, rmax * 0.6), top + r.normal(0, rmax * 0.35), r.uniform(rmin, rmax))
    # hanging vines / fronds
    for _ in range(count // 2):
        x = r.uniform(0, W); y = ybase - r.uniform(hmin * 0.6, hmax)
        p.addRect(skia.Rect(x, y, x + 3, y + r.uniform(80, 260)))
    p.setFillType(skia.PathFillType.kWinding)
    return p


JLAYERS = [(_layer(1, 860, 380, 620, 50, 110, 18), (22, 32, 34)), (_layer(2, 960, 300, 520, 60, 120, 16), (13, 20, 21)),
           (_layer(3, 1100, 260, 480, 70, 140, 14), (6, 9, 10))]


def jungle(cv, t, moon=(820, 240), fogk=1.0, layers=3):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, 1000)], [C((10, 16, 24)), C((34, 50, 58))])
    cv.drawRect(skia.Rect(0, 0, W, 1300), skia.Paint(Shader=sh))
    if moon:
        g = skia.GradientShader.MakeRadial(moon, 380, [C(ICE, 90), C(ICE, 0)])
        cv.drawRect(skia.Rect(0, 0, W, 1000), skia.Paint(Shader=g))
        cv.drawCircle(moon[0], moon[1], 46, P((214, 222, 230), 230))
    for i, (p, col) in enumerate(JLAYERS[:layers]):
        cv.save(); cv.translate(math.sin(t * 0.2 + i) * (4 + 6 * i), 0)
        cv.drawPath(p, P(col))
        cv.restore()
        if i == 0:
            for j in range(4):
                fx = ((j * 380 + t * (18 + j * 6)) % (W + 900)) - 450
                fp = skia.Paint(Color=C(ICE, 30 * fogk), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
                cv.drawOval(skia.Rect(fx, 780 + j * 40, fx + 760, 880 + j * 40), fp)
    # fireflies
    r = np.random.default_rng(5)
    for j in range(14):
        x = r.uniform(60, W - 60) + 30 * math.sin(t * 0.6 + j); y = r.uniform(700, 1150) + 20 * math.cos(t * 0.5 + j * 2)
        a = max(0, math.sin(t * r.uniform(1, 2.5) + j)) ** 3
        cv.drawCircle(x, y, 4, P((220, 240, 140), 220 * a))
        cv.drawCircle(x, y, 14, skia.Paint(Color=C((220, 240, 140), 60 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
    # ground fog
    gf = skia.GradientShader.MakeLinear([(0, 1000), (0, 1250)], [C(ICE, 0), C((40, 52, 60), 120 * fogk)])
    cv.drawRect(skia.Rect(0, 1000, W, 1300), skia.Paint(Shader=gf))


def figure(cv, x, y, s, step=0.0, hat=True, col=(4, 6, 7), a=255, pack=False):
    """generic walking silhouette (no face), (x, y) = feet"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    p = P(col, a)
    cv.drawRoundRect(skia.Rect(-24, -170, 24, -70), 16, 16, p)          # torso
    cv.drawCircle(0, -192, 22, p)                                         # head
    if hat:
        cv.drawOval(skia.Rect(-38, -212, 38, -200), p); cv.drawRoundRect(skia.Rect(-20, -232, 20, -204), 8, 8, p)
    if pack:
        cv.drawRoundRect(skia.Rect(-46, -168, -14, -100), 10, 10, p)
    for sgn in (-1, 1):
        ang = math.radians(16 * sgn * math.sin(step))
        cv.save(); cv.translate(sgn * 9, -76); cv.rotate(math.degrees(ang)); cv.drawRoundRect(skia.Rect(-9, 0, 9, 78), 8, 8, p); cv.restore()
        cv.save(); cv.translate(sgn * 22, -160); cv.rotate(-math.degrees(ang) * 0.8); cv.drawRoundRect(skia.Rect(-7, 0, 7, 72), 7, 7, p); cv.restore()
    cv.drawLine(30, -150, 52, -10, P(col, a, 5))                          # walking stick
    cv.restore()


def card(cv, rect, a, rot=0.0):
    cv.save(); cv.rotate(rot)
    cv.drawRoundRect(rect, 8, 8, P((214, 206, 186), 255 * a))
    cv.drawImageRect(PAPER, rect, SAMP, skia.Paint(Alphaf=0.25 * a, BlendMode=skia.BlendMode.kMultiply))
    cv.restore()


# ---------------------------------------------------------------- scenes
def sc_hook(cv, t):
    jungle(cv, t, moon=(560, 640), fogk=1.6, layers=2)
    # moonlit clearing / path the figures walk into
    g = skia.GradientShader.MakeRadial((560, 900), 520, [C(ICE, 110), C(ICE, 0)])
    cv.drawRect(skia.Rect(0, 400, W, 1300), skia.Paint(Shader=g))
    path = skia.Path(); path.moveTo(200, 1300); path.lineTo(520, 960); path.lineTo(600, 960); path.lineTo(900, 1300); path.close()
    cv.drawPath(path, P((60, 74, 82), 120))
    for i, (x, y, sc) in enumerate(((470, 1150, 0.95), (560, 1080, 0.8), (630, 1020, 0.68))):
        figure(cv, x + t * 5, y - t * 3, sc, step=t * 3 + i, pack=True, col=(5, 7, 8))
def sc_camp(cv, t):
    draw_map(cv, t, "camp")


def sc_party(cv, t):
    u = t - CUT["party"]
    jungle(cv, t, moon=None, fogk=0.6, layers=2)
    # campfire glow
    fx, fy = 540, 1060
    fl = 0.8 + 0.2 * math.sin(t * 13) * math.sin(t * 5.1)
    g = skia.GradientShader.MakeRadial((fx, fy - 40), 520, [C(AMBER, 150 * fl), C(AMBER, 0)])
    cv.drawRect(skia.Rect(0, 400, W, 1300), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kPlus))
    for k in range(3):
        fp = skia.Path(); w_ = 34 - k * 9; h_ = (110 - k * 25) * fl
        fp.moveTo(fx - w_, fy); fp.quadTo(fx - w_ * 0.4, fy - h_ * 0.6, fx + 4 * math.sin(t * 9 + k), fy - h_)
        fp.quadTo(fx + w_ * 0.4, fy - h_ * 0.6, fx + w_, fy); fp.close()
        cv.drawPath(fp, P([(200, 70, 20), (250, 140, 40), (255, 220, 140)][k], 230))
    names = [("PERCY", 330, 0.95), ("JACK", 720, 0.9), ("RALEIGH", 900, 0.85)]
    for i, (nm, x, sc) in enumerate(names):
        figure(cv, x, 1080, sc, step=0.0, pack=False, col=(5, 6, 7))
        a = ease((u - 0.2 - i * 0.6) / 0.4)
        if a > 0:
            text(cv, nm, x, 1080 - 220 * sc - 40, font("typeb", 34), (255, 210, 160), 255 * a, "c")
    cv.drawRect(skia.Rect(0, 1080, W, 1300), P((6, 8, 9)))


def sc_letter(cv, t):
    u = t - CUT["letter"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((12, 12, 14)))
    g = skia.GradientShader.MakeRadial((540, 560), 700, [C(AMBER, 70), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 1300), skia.Paint(Shader=g))
    a = ease(u / 0.5)
    cv.save(); cv.translate(540, 620 + 40 * (1 - a)); cv.rotate(-2.5)
    r = skia.Rect(-400, -470, 400, 470)
    card(cv, r, a)
    for i in range(12):
        cv.drawLine(-350, -330 + i * 64, 350, -330 + i * 64, P((150, 160, 180), 90 * a, 1.5))
    text(cv, "DEAD HORSE CAMP", -350, -390, font("typeb", 34), (60, 54, 46), 255 * a, shadow=False)
    text(cv, "29 MAY 1925", 350, -390, font("type", 30), (60, 54, 46), 255 * a, "r", shadow=False)
    q = ["“You need have", "no fear of any", "failure...”"]
    words = [w for w, tt in SC["letter"]["words"]]
    tq = word_t("letter", "you")
    for i, ln in enumerate(q):
        aa = ease((t - tq - i * 0.55 + 0.2) / 0.35) * a
        if aa > 0:
            text(cv, ln, -350, -170 + i * 110, font("typeb", 76), (34, 32, 60), 255 * aa, shadow=False)
    text(cv, "— P. H. FAWCETT, LAST LETTER", -350, 260, font("type", 30), (90, 80, 66), 255 * a, shadow=False)
    cv.restore()


def sc_coords(cv, t):
    draw_map(cv, t, "coords")


def sc_why(cv, t):
    draw_map(cv, t, "why")
    a = ease((t - CUT["why"] - 0.1) / 0.3)
    stamp(cv, "TYPO?", 250, 340, -8, 1 + 0.4 * (1 - a), a, 120)
    b = ease((t - word_t("why", "false") + 0.2) / 0.3)
    if b > 0:
        stamp(cv, "FALSE TRAIL?", 720, 310, 6, 1 + 0.4 * (1 - b), b, 104)


def sc_bones(cv, t):
    u = t - CUT["bones"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((11, 13, 16)))
    g = skia.GradientShader.MakeRadial((540, 300), 800, [C(ICE, 50), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 1300), skia.Paint(Shader=g))
    # closed evidence box on a table
    cv.drawRect(skia.Rect(0, 1000, W, 1300), P((30, 24, 20)))
    bx = skia.Path(); bx.moveTo(300, 820); bx.lineTo(780, 820); bx.lineTo(780, 1010); bx.lineTo(300, 1010); bx.close()
    cv.drawPath(bx, P((70, 52, 36)))
    lid = skia.Path(); lid.moveTo(280, 790); lid.lineTo(800, 790); lid.lineTo(780, 830); lid.lineTo(300, 830); lid.close()
    cv.drawPath(lid, P((92, 70, 48)))
    cv.drawRect(skia.Rect(470, 880, 610, 940), P((214, 206, 186)))
    text(cv, "1951", 540, 925, font("typeb", 40), (40, 36, 30), 255, "c", shadow=False)
    a = ease((u - 0.2) / 0.4)
    if a > 0:
        cv.save(); cv.rotate(-1.5)
        r = skia.Rect(140, 150, 940, 620); card(cv, r, a)
        text(cv, "REMAINS SAID TO BE FAWCETT'S", 180, 215, font("typeb", 34), (40, 36, 30), 255 * a, shadow=False)
        cv.drawLine(180, 235, 900, 235, P((60, 54, 46), 255 * a, 2))
        text(cv, "TESTED BY: ROYAL", 180, 320, font("type", 38), (60, 54, 46), 255 * a, shadow=False)
        text(cv, "ANTHROPOLOGICAL INSTITUTE", 180, 370, font("type", 38), (60, 54, 46), 255 * a, shadow=False)
        text(cv, "RESULT:", 180, 520, font("type", 44), (60, 54, 46), 255 * a, shadow=False)
        text(cv, "NOT HIM", 900, 535, font("bebas", 130), (150, 24, 24), 255 * a, "r", shadow=False)
        rev = ease((t - word_t("bones", "not") + 0.05) / 0.35); bw = 420 * (1 - rev)
        if bw > 1:
            cv.drawRect(skia.Rect(906 - bw, 425, 906, 550), P((14, 14, 14), 255 * a))
        cv.restore()


def sc_theory(cv, t):
    jungle(cv, t, moon=(200, 200), fogk=1.4, layers=3)
    cv.drawRect(skia.Rect(0, 0, W, 1300), P((0, 0, 0), 90))
    for i, (lab1, lab2, w) in enumerate((("HUNGER", "OR FEVER?", "hunger"), ("KILLED IN", "THE JUNGLE?", "killed"))):
        a = ease((t - word_t("theory", w) + 0.35) / 0.3)
        if a <= 0:
            continue
        cx = 300 + i * 480; cy = 480 + i * 90; rot = -4 + i * 7
        cv.save(); cv.translate(cx, cy); cv.rotate(rot)
        r = skia.Rect(-220, -190, 220, 190)
        cv.drawRoundRect(r, 8, 8, P((214, 206, 186), 255 * a))
        cv.drawImageRect(PAPER, r, SAMP, skia.Paint(Alphaf=0.25 * a, BlendMode=skia.BlendMode.kMultiply))
        text(cv, "THEORY", 0, -110, font("typeb", 38), (120, 30, 30), 255 * a, "c", shadow=False)
        text(cv, lab1, 0, -10, font("bebas", 96), (24, 22, 20), 255 * a, "c", shadow=False)
        text(cv, lab2, 0, 80, font("bebas", 96), (24, 22, 20), 255 * a, "c", shadow=False)
        cv.drawLine(-180, 115, 180, 115, P((60, 54, 46), 200 * a, 2))
        text(cv, "UNCONFIRMED", 0, 160, font("type", 30), (60, 54, 46), 255 * a, "c", shadow=False)
        cv.restore()


def sc_end(cv, t):
    u = t - CUT["end"]
    jungle(cv, t, fogk=1.5, layers=2)
    for i, (x, sc) in enumerate(((560, 0.5), (610, 0.47), (655, 0.45))):
        figure(cv, x + u * 10, 960, sc, step=t * 3 + i, pack=i > 0, col=(10, 13, 15), a=255 * (1 - ease(u / 2.5)))
    p, col = JLAYERS[2]; cv.drawPath(p, P(col))
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


SCENE_FN = {"hook": sc_hook, "camp": sc_camp, "party": sc_party, "letter": sc_letter, "coords": sc_coords,
            "why": sc_why, "bones": sc_bones, "theory": sc_theory, "end": sc_end}
EXHIBIT = {"camp": "EXHIBIT A · LAST CONTACT", "party": "EXHIBIT B · THE PARTY", "letter": "EXHIBIT C · THE LETTER",
           "coords": "EXHIBIT D · THE STRANGEST CLUE", "why": "EXHIBIT D · THE STRANGEST CLUE", "bones": "EXHIBIT E · 1951",
           "theory": "THEORIES", "end": "CASE STATUS"}
HEAD = {"camp": "DEAD HORSE CAMP", "party": "THREE MEN. NO GUIDES.", "letter": "THE LAST LETTER",
        "coords": "THE NUMBERS DON'T MATCH", "why": "A MISTAKE... OR ON PURPOSE?", "bones": "THE BONES",
        "theory": "THEORIES, NOT FACTS", "end": "NEVER FOUND"}
KICKER = "CASE FILE #007 · MAY 1925 · BRAZIL"


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
    hook = t < CUT["camp"]
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        # hook frame: big two-line hook + stamp
        f = font("bebas", 128)
        text(cv, "HE WENT LOOKING", X, 1370, f, WHITE)
        text(cv, "FOR A LOST CITY.", X, 1490, f, WHITE)
        stamp(cv, "NEVER FOUND", 560, 300, -7, 1.0, 1.0, 116)
    else:
        fl = 1.0 if t - CUT[k] > 0.25 else ease((t - CUT[k]) / 0.25)
        text(cv, EXHIBIT[k], X, 1316, font("typeb", 40), RED, 255 * fl)
        hf = fit(HEAD[k], "bebas", 104, MAXW)
        text(cv, HEAD[k], X, 1436, hf, WHITE, 255 * fl)
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
        y0 = (1548 if len(lines) == 1 else 1528) if not hook else 1606
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
