"""Render 'Flannan Isles – the coat left behind' (The Vanished Files, Case file format).
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


rng = np.random.default_rng(1900)
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




# ---------------------------------------------------------------- props
def person(cv, x, y, s, a, rgb=(14, 16, 20), coat=True):
    """plain standing silhouette – no face"""
    pa = P(rgb, a)
    cv.drawCircle(x, y - 150 * s, 17 * s, pa)
    b = skia.Path(); w = 30 if coat else 22
    b.moveTo(x - 24 * s, y - 128 * s); b.lineTo(x + 24 * s, y - 128 * s); b.lineTo(x + w * s, y - (0 if coat else 60) * s)
    b.lineTo(x - w * s, y - (0 if coat else 60) * s); b.close(); cv.drawPath(b, pa)
    if not coat:
        cv.drawRect(skia.Rect(x - 16 * s, y - 62 * s, x - 4 * s, y), pa); cv.drawRect(skia.Rect(x + 4 * s, y - 62 * s, x + 16 * s, y), pa)


def ghost(cv, x, y, s, a, t):
    """dashed empty outline where a keeper should stand"""
    p = skia.Path(); p.addCircle(x, y - 150 * s, 17 * s)
    p.moveTo(x - 24 * s, y - 128 * s); p.lineTo(x + 24 * s, y - 128 * s); p.lineTo(x + 30 * s, y); p.lineTo(x - 30 * s, y); p.close()
    dp = P(ICE, a, 3); dp.setPathEffect(skia.DashPathEffect.Make([9, 7], -t * 20)); cv.drawPath(p, dp)


def fog_bank(cv, t, y, a=1.0, speed=12):
    for j in range(6):
        fx = ((j * 300 + t * (speed + j * 4)) % (W + 900)) - 450
        fp = skia.Paint(Color=C(ICE, 30 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 70))
        cv.drawOval(skia.Rect(fx, y + j * 26 - 60, fx + 760, y + j * 26 + 60), fp)


def rain(cv, t, a=1.0):
    r = np.random.default_rng(5)
    xs = r.uniform(-200, W, 160); ys = r.uniform(0, H, 160); sp = r.uniform(1400, 2000, 160)
    p = P(ICE, 46 * a, 2)
    for x, y, v in zip(xs, ys, sp):
        yy = (y + t * v) % (H + 100) - 50; xx = x + (yy * 0.25)
        cv.drawLine(xx, yy, xx + 10, yy + 42, p)


def lighthouse(cv, x, base, s, lamp, t, rgb=(18, 21, 26), beam=False):
    """generic short stone lighthouse with keepers' buildings; lamp 0..1"""
    cv.save(); cv.translate(x, base); cv.scale(s, s)
    pa = P(rgb)
    cv.drawRect(skia.Rect(-210, -70, -40, 0), pa); cv.drawRect(skia.Rect(40, -60, 170, 0), pa)       # cottages / walls
    roof = skia.Path(); roof.moveTo(-220, -70); roof.lineTo(-125, -112); roof.lineTo(-30, -70); roof.close(); cv.drawPath(roof, pa)
    tw = skia.Path(); tw.moveTo(-38, 0); tw.lineTo(-28, -230); tw.lineTo(28, -230); tw.lineTo(38, 0); tw.close(); cv.drawPath(tw, pa)
    cv.drawRect(skia.Rect(-44, -240, 44, -228), pa)                                                  # gallery
    cv.drawRect(skia.Rect(-26, -290, 26, -240), P((30, 34, 40)))                                     # lantern room
    for xx in (-26, -9, 9, 26):
        cv.drawLine(xx, -290, xx, -240, P(rgb, 255, 3))
    dome = skia.Path(); dome.moveTo(-30, -290); dome.quadTo(0, -330, 30, -290); dome.close(); cv.drawPath(dome, pa)
    if lamp > 0:
        fl = 0.9 + 0.1 * math.sin(t * 7)
        g = skia.GradientShader.MakeRadial((0, -265), 160, [C((255, 220, 150), 200 * lamp * fl), C(AMBER, 0)])
        cv.drawCircle(0, -265, 160, skia.Paint(Shader=g))
        cv.drawRect(skia.Rect(-20, -286, 20, -244), P((255, 230, 170), 240 * lamp))
        if beam:
            ang = (t * 40) % 360
            for side in (0, 180):
                a_ = math.radians(ang + side); dx = math.cos(a_)
                bp = skia.Path(); bp.moveTo(0, -265); bp.lineTo(dx * 1400, -265 - 120); bp.lineTo(dx * 1400, -265 + 120); bp.close()
                cv.drawPath(bp, skia.Paint(Color=C((255, 230, 180), 40 * lamp * abs(math.sin(a_ * 0.5 + 0.8)) + 10),
                                           AntiAlias=True, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20)))
    cv.restore()


def island(cv, y, rgb, x0=110, x1=980, top=170):
    r = np.random.default_rng(4)
    p = skia.Path(); p.moveTo(x0 - 60, y + 4)
    p.lineTo(x0, y - top * 0.55); p.lineTo(x0 + 70, y - top * 0.85)
    for xx in np.linspace(x0 + 120, x1 - 120, 12):
        p.lineTo(xx, y - top + r.uniform(-14, 14))
    p.lineTo(x1 - 60, y - top * 0.8); p.lineTo(x1, y - top * 0.4); p.lineTo(x1 + 50, y + 4); p.close()
    cv.drawPath(p, P(rgb))
    return y - top


def steamer(cv, x, y, s, a=255, rgb=(8, 10, 13), lights=True, t=0.0):
    """generic c.1900 steamship silhouette (waterline at y)"""
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    pa = P(rgb, a)
    h = skia.Path(); h.moveTo(-260, -60); h.lineTo(250, -60); h.lineTo(285, -80); h.quadTo(250, -10, 210, 0); h.lineTo(-240, 0)
    h.quadTo(-262, -20, -260, -60); h.close(); cv.drawPath(h, pa)
    cv.drawRect(skia.Rect(-120, -105, 120, -60), pa); cv.drawRect(skia.Rect(-60, -140, 40, -105), pa)
    cv.drawRect(skia.Rect(-25, -220, 15, -140), pa)                                # funnel
    for mx in (-200, 190):
        cv.drawRect(skia.Rect(mx - 3, -230, mx + 3, -60), pa)
    cv.drawLine(-200, -228, 190, -228, P(rgb, a, 2))
    if lights:
        for lx in range(-100, 120, 34):
            cv.drawCircle(lx, -82, 4, P((255, 200, 120), 200 * a / 255))
        cv.drawCircle(190, -232, 6, P((255, 235, 200), a))
    # smoke
    for j in range(6):
        sm = skia.Paint(Color=C((60, 66, 74), 60 * a / 255), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
        cv.drawCircle(-5 - j * 45 - (t * 12) % 45, -250 - j * 18, 26 + j * 8, sm)
    cv.restore()


def night_sky(cv, top, bot, horizon, stars=40):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, horizon)], [C(top), C(bot)])
    cv.drawRect(skia.Rect(0, 0, W, horizon + 2), skia.Paint(Shader=sh))
    r = np.random.default_rng(7)
    for _ in range(stars):
        cv.drawCircle(r.uniform(0, W), r.uniform(0, horizon * 0.6), r.uniform(0.8, 2.0), P(ICE, r.uniform(30, 110)))


def storm_clouds(cv, t, a=1.0):
    for j in range(8):
        cx = ((j * 230 + t * (8 + j)) % (W + 600)) - 300; cy = 120 + (j % 3) * 110
        cp = skia.Paint(Color=C((26, 30, 38), 200 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50))
        cv.drawOval(skia.Rect(cx, cy - 70, cx + 560, cy + 70), cp)


# ---------------------------------------------------------------- cliff cross-section (west landing)
SEA_Y = 1110; LEDGE_Y = 600; CLIFF_X = 560


def cliff(cv, t, box_broken=0.0):
    cv.drawRect(skia.Rect(0, 0, W, H), P((10, 13, 18)))
    storm_clouds(cv, t, 0.9)
    sh = skia.GradientShader.MakeLinear([(0, SEA_Y), (0, H)], [C((22, 30, 40)), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, SEA_Y, W, H), skia.Paint(Shader=sh))
    for i in range(14):
        y = SEA_Y + 8 + i * 22; amp = 6 + i * 2
        p = skia.Path(); ph = t * 2 + i
        for xi in range(0, CLIFF_X + 60, 30):
            (p.moveTo if xi == 0 else p.lineTo)(xi, y + amp * math.sin(xi * 0.02 + ph))
        cv.drawPath(p, P(ICE, 30 + 4 * i, 2))
    # rock face (right side), stepped ledge with the landing
    r = np.random.default_rng(8)
    rock = skia.Path(); rock.moveTo(W + 20, 140); rock.lineTo(760, 160)
    for yy in np.linspace(200, LEDGE_Y - 20, 6):
        rock.lineTo(720 + r.uniform(-25, 25), yy)
    rock.lineTo(720, LEDGE_Y); rock.lineTo(CLIFF_X, LEDGE_Y); rock.lineTo(CLIFF_X + 10, LEDGE_Y + 30)
    for yy in np.linspace(LEDGE_Y + 60, SEA_Y + 40, 8):
        rock.lineTo(CLIFF_X + r.uniform(-30, 30) + (yy - LEDGE_Y) * 0.05, yy)
    rock.lineTo(CLIFF_X + 60, H); rock.lineTo(W + 20, H); rock.close()
    cv.drawPath(rock, P((32, 36, 42)))
    cv.drawPath(rock, P((70, 80, 92), 160, 3))
    # railings along the path above the ledge (bent when broken)
    for i in range(5):
        x = 740 + i * 60; bend = box_broken * (14 + i * 9)
        cv.drawLine(x, 160 - 2, x + bend * 0.6, 160 - 70 + bend, P((90, 98, 108), 230, 6))
    cv.drawLine(740, 160 - 70, 980 + box_broken * 20, 160 - 70 + box_broken * 40, P((90, 98, 108), 230, 5))
    # rope box on the ledge
    bx = 600
    if box_broken < 0.5:
        cv.drawRect(skia.Rect(bx, LEDGE_Y - 100, bx + 140, LEDGE_Y), P((78, 62, 44)))
        cv.drawRect(skia.Rect(bx, LEDGE_Y - 100, bx + 140, LEDGE_Y), P((30, 22, 16), 255, 4))
    else:
        for j, (dx, dy, rot) in enumerate(((-30, -10, -35), (70, -30, 50), (120, -8, 12), (20, -40, 80))):
            cv.save(); cv.translate(bx + dx, LEDGE_Y + dy); cv.rotate(rot)
            cv.drawRect(skia.Rect(-60, -9, 60, 9), P((78, 62, 44))); cv.restore()
        for j in range(4):
            cv.drawOval(skia.Rect(bx - 70 + j * 70, LEDGE_Y - 30, bx + j * 70, LEDGE_Y - 4), P((150, 130, 96), 230, 6))


def height_marker(cv, a, label="≈110 FT"):
    x = 470
    p = P(RED, 230 * a, 4)
    cv.drawLine(x, LEDGE_Y, x, SEA_Y, p)
    for yy, d in ((LEDGE_Y, 1), (SEA_Y, -1)):
        cv.drawLine(x - 18, yy, x + 18, yy, p)
        tri = skia.Path(); tri.moveTo(x, yy); tri.lineTo(x - 14, yy + 26 * d); tri.lineTo(x + 14, yy + 26 * d); tri.close()
        cv.drawPath(tri, P(RED, 230 * a))
    cv.save(); cv.translate(x - 26, (LEDGE_Y + SEA_Y) / 2); cv.rotate(-90)
    text(cv, label, 0, 0, font("bebas", 74), (255, 90, 80), 255 * a, "c")
    cv.restore()


def giant_wave(cv, t, u):
    h = ease(u / 1.6)                    # rise
    crest = SEA_Y - h * (SEA_Y - LEDGE_Y + 130)
    fall = ease((u - 1.7) / 1.4)
    crest += fall * 380
    p = skia.Path(); p.moveTo(-40, H); p.lineTo(-40, SEA_Y)
    for xi in range(0, CLIFF_X + 140, 20):
        k = xi / (CLIFF_X + 120)
        yy = SEA_Y - (SEA_Y - crest) * (k ** 1.6) + 10 * math.sin(xi * 0.03 + t * 5)
        p.lineTo(xi, yy)
    p.lineTo(CLIFF_X + 140, H); p.close()
    cv.drawPath(p, skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, crest), (0, H)], [C((70, 92, 112), 240), C((10, 16, 24), 250)]),
                              AntiAlias=True))
    # foam spray over the ledge
    r = np.random.default_rng(int(u * 10))
    for _ in range(int(80 * h * (1 - fall * 0.7))):
        fx = CLIFF_X + r.uniform(-120, 260); fy = crest + r.uniform(-140, 60)
        cv.drawCircle(fx, fy, r.uniform(3, 14), P((210, 225, 235), r.uniform(60, 180)))


# ---------------------------------------------------------------- scenes
ISL_Y = 900


def sc_island_night(cv, t, ship_x=None):
    night_sky(cv, (5, 7, 12), (30, 38, 50), ISL_Y, 25)
    storm_clouds(cv, t)
    if int(t * 10) % 37 == 0:
        cv.drawRect(skia.Rect(0, 0, W, ISL_Y), P(ICE, 40))
    sh = skia.GradientShader.MakeLinear([(0, ISL_Y), (0, H)], [C((20, 27, 36)), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, ISL_Y, W, H), skia.Paint(Shader=sh))
    top = island(cv, ISL_Y + 10, (12, 15, 19))
    lighthouse(cv, 560, top + 6, 1.15, 0.0, t)
    # "no light" marker
    a = 0.55 + 0.45 * math.sin(t * 4)
    cv.drawCircle(560, top + 6 - 265 * 1.15, 46, P(RED, 160 * a, 4))
    for i in range(46):
        z = i / 46; y = ISL_Y + 12 + (z ** 1.9) * (H - ISL_Y); amp = (3 + 24 * z ** 2) * 1.3
        p = skia.Path(); ph = t * (0.9 + z * 1.8) + i * 1.7
        for xi in range(0, W + 40, 40):
            yy = y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph) + amp * 0.5 * math.sin(xi * 0.031 + ph * 1.7)
            (p.moveTo if xi == 0 else p.lineTo)(xi, yy)
        cv.drawPath(p, P(ICE, 16 + 50 * z, 1.2 + 2.4 * z))
    if ship_x is not None:
        steamer(cv, ship_x, 1010 + 5 * math.sin(t * 1.3), 0.9, 255, (6, 8, 11), True, t)
    rain(cv, t, 0.8)
    fog_bank(cv, t, ISL_Y - 30, 0.5)


def sc_hook(cv, t):
    sc_island_night(cv, t)


def sc_dark(cv, t):
    u = t - CUT["dark"]
    sc_island_night(cv, t, ship_x=-200 + u * 95)


def sc_relief(cv, t):
    u = t - CUT["relief"]
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, 820)], [C((58, 66, 78)), C((112, 124, 138))])
    cv.drawRect(skia.Rect(0, 0, W, 822), skia.Paint(Shader=sh))
    storm_clouds(cv, t, 0.6)
    sh2 = skia.GradientShader.MakeLinear([(0, 820), (0, H)], [C((40, 50, 62)), C((6, 9, 13))])
    cv.drawRect(skia.Rect(0, 820, W, H), skia.Paint(Shader=sh2))
    for i in range(40):
        z = i / 40; y = 826 + (z ** 1.9) * (H - 820); amp = (2 + 16 * z ** 2)
        p = skia.Path(); ph = t * (0.6 + z * 1.4) + i * 1.7
        for xi in range(0, W + 40, 40):
            (p.moveTo if xi == 0 else p.lineTo)(xi, y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph))
        cv.drawPath(p, P(ICE, 16 + 40 * z, 1.2 + 2 * z))
    # big island close, landing steps on the left
    rk = skia.Path(); rk.moveTo(300, 1100); rk.lineTo(330, 700); rk.lineTo(520, 560); rk.lineTo(1100, 520); rk.lineTo(1100, 1100); rk.close()
    cv.drawPath(rk, P((30, 34, 40)))
    lighthouse(cv, 840, 540, 0.95, 0.0, t, (24, 27, 32))
    for i in range(10):     # steps
        cv.drawRect(skia.Rect(330 + i * 18, 1010 - i * 34, 400 + i * 18, 1018 - i * 34), P((70, 76, 86)))
    # three empty places
    for i in range(3):
        a = ease((u - 0.4 - i * 0.25) / 0.4) * (0.7 + 0.3 * math.sin(t * 3 + i))
        ghost(cv, 470 + i * 90, 760 - i * 10, 0.9, 220 * a, t)
    # rowing boat arriving
    bx = 60 + ease(u / 3) * 180
    bt = skia.Path(); bt.moveTo(bx - 90, 1040); bt.lineTo(bx + 90, 1040); bt.quadTo(bx + 70, 1075, bx, 1078); bt.quadTo(bx - 70, 1075, bx - 90, 1040)
    cv.drawPath(bt, P((14, 16, 20)))
    for j in range(3):
        person(cv, bx - 50 + j * 50, 1042, 0.38, 255, (14, 16, 20))
    fog_bank(cv, t, 800, 0.5)


def sc_inside(cv, t):
    u = t - CUT["inside"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((16, 18, 22)))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, 1200), SAMP, skia.Paint(Alphaf=0.06, BlendMode=skia.BlendMode.kOverlay))
    cv.drawRect(skia.Rect(0, 1040, W, H), P((10, 11, 14)))
    # closed plank door with latch
    dr = skia.Rect(340, 260, 740, 1040)
    cv.drawRect(dr, P((44, 36, 28)))
    for i in range(1, 6):
        cv.drawLine(340 + i * 66, 260, 340 + i * 66, 1040, P((24, 19, 14), 255, 4))
    for yy in (360, 640, 920):
        cv.drawRect(skia.Rect(350, yy, 730, yy + 34), P((34, 27, 20)))
    cv.drawRect(skia.Rect(330, 250, 750, 262), P((28, 24, 20)))
    cv.drawRect(skia.Rect(640, 600, 720, 620), P((120, 120, 118)))           # bolt
    # grey daylight from the left window
    g = skia.GradientShader.MakeLinear([(0, 0), (700, 0)], [C((170, 185, 200), 70), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 1040), skia.Paint(Shader=g))
    cv.drawRect(skia.Rect(60, 340, 230, 640), P((120, 135, 150), 120))
    cv.drawLine(145, 340, 145, 640, P((16, 18, 22), 255, 8)); cv.drawLine(60, 490, 230, 490, P((16, 18, 22), 255, 8))
    a = ease((t - word_t("inside", "shut") + 0.05) / 0.25)
    if a > 0:
        stamp(cv, "SHUT", 540, 600, -6, 1 + 0.5 * (1 - a), a, 110)


def sc_coat(cv, t):
    u = t - CUT["coat"]
    cv.drawRect(skia.Rect(0, 0, W, H), P((14, 16, 20)))
    cv.drawRect(skia.Rect(0, 210, W, 236), P((40, 34, 28)))   # peg rail
    sp = skia.GradientShader.MakeRadial((800, 560), 520, [C((255, 220, 160), 70), C((0, 0, 0), 0)])
    cv.drawRect(skia.Rect(0, 0, W, 1200), skia.Paint(Shader=sp))
    for i, x in enumerate((260, 530, 800)):
        cv.drawRect(skia.Rect(x - 10, 236, x + 10, 270), P((90, 80, 66)))
        if i < 2:   # empty pegs: dashed outline of the missing coats
            a = ease((u - 0.3) / 0.5)
            pth = coat_path(x)
            dp = P(ICE, 150 * a, 3); dp.setPathEffect(skia.DashPathEffect.Make([12, 9], -u * 18)); cv.drawPath(pth, dp)
            text(cv, "WORN", x, 1020, font("typeb", 32), STEEL, 200 * a, "c")
    pth = coat_path(800)
    cv.drawPath(pth, skia.Paint(Shader=skia.GradientShader.MakeLinear([(700, 260), (900, 980)], [C((150, 128, 60)), C((70, 60, 30))]),
                                AntiAlias=True))
    cv.drawPath(pth, P((40, 34, 18), 255, 3))
    cv.drawLine(800, 300, 800, 960, P((50, 42, 22), 255, 3))
    a = ease((t - word_t("coat", "oilskins") + 0.1) / 0.3)
    text(cv, "STILL HERE", 800, 1020, font("typeb", 32), (255, 90, 80), 255 * a, "c")
    if a > 0:
        cv.drawRoundRect(skia.Rect(650, 240, 950, 1050), 20, 20, P(RED, 220 * a, 5))


def coat_path(x):
    p = skia.Path()
    p.moveTo(x - 18, 268); p.lineTo(x + 18, 268); p.lineTo(x + 60, 300); p.lineTo(x + 115, 560); p.lineTo(x + 95, 570)
    p.lineTo(x + 80, 470); p.lineTo(x + 95, 960); p.lineTo(x - 95, 960); p.lineTo(x - 80, 470); p.lineTo(x - 95, 570)
    p.lineTo(x - 115, 560); p.lineTo(x - 60, 300); p.close(); return p


def sc_landing(cv, t):
    u = t - CUT["landing"]
    br = ease((t - word_t("landing", "smashed") + 0.05) / 0.2)
    cliff(cv, t, br)
    height_marker(cv, ease((t - word_t("landing", "hundred") + 0.2) / 0.5))
    text(cv, "WEST LANDING", 600, LEDGE_Y + 80, font("typeb", 40), ICE, 220)
    text(cv, "ROPE BOX", 600, LEDGE_Y - 130, font("typeb", 40), (255, 200, 140), 220 * (1 - br) + 120)
    text(cv, "CROSS-SECTION STYLISED", 90, 230, font("type", 26), STEEL, 200, shadow=False)


def sc_wave(cv, t):
    u = t - CUT["wave"]
    cliff(cv, t, 1.0)
    giant_wave(cv, t, u)


def sc_warn(cv, t):
    u = t - CUT["warn"]
    cliff(cv, t, 1.0)
    # two keepers at the ledge (in coats), a third running down the path without a coat
    for i, x in enumerate((600, 690)):
        person(cv, x, LEDGE_Y, 0.85, 255, (6, 7, 9))
    pr = ease(u / 2.4)
    rx, ry = 980 - pr * 220, 160 + pr * (LEDGE_Y - 160)
    person(cv, rx, ry, 0.85, 255, (6, 7, 9), coat=False)
    dp = P(ICE, 160, 3); dp.setPathEffect(skia.DashPathEffect.Make([12, 9], -u * 30))
    cv.drawLine(1000, 160, 760, LEDGE_Y, dp)
    text(cv, "NO COAT", rx - 230, ry - 120, font("typeb", 40), (255, 90, 80), 230)


def sc_end(cv, t):
    u = t - CUT["end"]
    night_sky(cv, (4, 6, 10), (24, 30, 40), ISL_Y, 60)
    sh = skia.GradientShader.MakeLinear([(0, ISL_Y), (0, H)], [C((16, 22, 30)), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, ISL_Y, W, H), skia.Paint(Shader=sh))
    top = island(cv, ISL_Y + 10, (10, 12, 16))
    lighthouse(cv, 560, top + 6, 1.15, 0.0, t)
    for i in range(30):
        z = i / 30; y = ISL_Y + 12 + (z ** 1.9) * (H - ISL_Y); amp = (2 + 16 * z ** 2)
        p = skia.Path(); ph = t * (0.6 + z * 1.4) + i * 1.7
        for xi in range(0, W + 40, 40):
            (p.moveTo if xi == 0 else p.lineTo)(xi, y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph))
        cv.drawPath(p, P(ICE, 14 + 40 * z, 1.2 + 2 * z))
    for i in range(3):
        ghost(cv, 470 + i * 90, top + 2, 0.45, 150, t)
    fog_bank(cv, t, ISL_Y - 40, 1.0, 16)
    a = ease((t - word_t("end", "found") + 0.1) / 0.3)
    if a > 0:
        stamp(cv, "NEVER FOUND", 540, 330, -7, 1 + 0.5 * (1 - a), a, 120)


SCENE_FN = {"hook": sc_hook, "dark": sc_dark, "relief": sc_relief, "inside": sc_inside, "coat": sc_coat,
            "landing": sc_landing, "wave": sc_wave, "warn": sc_warn, "end": sc_end}
HEAD = {"hook": "", "dark": "15 DEC 1900 · THE LIGHT IS OUT", "relief": "26 DEC · NOBODY THERE",
        "inside": "GATE SHUT. DOOR SHUT.", "coat": "ONE COAT LEFT BEHIND", "landing": "SMASHED 110 FT ABOVE THE SEA",
        "wave": "A FREAK WAVE?", "warn": "ONE RAN TO WARN THEM?", "end": "WHAT HAPPENED TO THEM?"}
PILLS = {"coat": "THE STRANGEST CLUE", "wave": "THEORY 1 · OFFICIAL VERDICT", "warn": "THEORY 2", "end": "STILL UNEXPLAINED"}
KICKER = "CASE FILE #004 · DEC 1900 · FLANNAN ISLES"


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
    hook = t < CUT["dark"]
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        f = fit("3 KEEPERS VANISHED.", "bebas", 140, 900)
        text(cv, "3 KEEPERS VANISHED.", X, 1372, f, WHITE)
        text(cv, "ONE LEFT HIS COAT.", X, 1496, f, (255, 90, 80))
        stamp(cv, "NEVER FOUND", 660, 1090, -8, 1.0, 1.0, 96)
    else:
        fl = 1.0 if t - CUT[k] > 0.25 else ease((t - CUT[k]) / 0.25)
        if k in PILLS:
            pill(cv, PILLS[k], X, 1316, 255 * fl)
        hf = fit(HEAD[k], "bebas", 100, MAXW)
        text(cv, HEAD[k], X, 1436, hf, (255, 90, 80) if k in ("coat",) else WHITE, 255 * fl)
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
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "3000k", "-bufsize", "6000k",
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
