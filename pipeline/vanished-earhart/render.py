"""Render 'Amelia Earhart – 4 theories ranked' (The Vanished Files, Theories ranked format).
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


rng = np.random.default_rng(1937)
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




def fog_bank(cv, t, y, a=1.0, speed=12):
    for j in range(6):
        fx = ((j * 300 + t * (speed + j * 4)) % (W + 900)) - 450
        fp = skia.Paint(Color=C(ICE, 30 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 70))
        cv.drawOval(skia.Rect(fx, y + j * 26 - 60, fx + 760, y + j * 26 + 60), fp)


def storm_clouds(cv, t, a=1.0):
    for j in range(8):
        cx = ((j * 230 + t * (8 + j)) % (W + 600)) - 300; cy = 120 + (j % 3) * 110
        cp = skia.Paint(Color=C((26, 30, 38), 200 * a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50))
        cv.drawOval(skia.Rect(cx, cy - 70, cx + 560, cy + 70), cp)


def night_sky(cv, top, bot, horizon, stars=40):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, horizon)], [C(top), C(bot)])
    cv.drawRect(skia.Rect(0, 0, W, horizon + 2), skia.Paint(Shader=sh))
    r = np.random.default_rng(7)
    for _ in range(stars):
        cv.drawCircle(r.uniform(0, W), r.uniform(0, horizon * 0.6), r.uniform(0.8, 2.0), P(ICE, r.uniform(30, 110)))


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


# ---------------------------------------------------------------- props
def plane_top(cv, x, y, s, ang, rgb=(230, 236, 240), a=255):
    """generic 1930s twin-engine, twin-tail airliner seen from above (stylised)"""
    cv.save(); cv.translate(x, y); cv.rotate(ang); cv.scale(s, s)
    pa = P(rgb, a)
    cv.drawOval(skia.Rect(-60, -9, 64, 9), pa)                       # fuselage (nose to +x)
    w = skia.Path(); w.moveTo(18, -6); w.lineTo(6, -92); w.lineTo(-10, -92); w.lineTo(-14, -6)
    w.lineTo(-14, 6); w.lineTo(-10, 92); w.lineTo(6, 92); w.lineTo(18, 6); w.close(); cv.drawPath(w, pa)
    for e in (-34, 34):
        cv.drawRoundRect(skia.Rect(-4, e - 6, 34, e + 6), 5, 5, pa)
    cv.drawRect(skia.Rect(-62, -30, -50, 30), pa)                    # tailplane
    cv.drawRect(skia.Rect(-64, -34, -48, -27), pa); cv.drawRect(skia.Rect(-64, 27, -48, 34), pa)  # twin fins
    cv.restore()


def plane_side(cv, x, y, s, ang, rgb=(10, 12, 16), a=255):
    """same aircraft from the side (stylised silhouette)"""
    cv.save(); cv.translate(x, y); cv.rotate(ang); cv.scale(s, s)
    pa = P(rgb, a)
    b = skia.Path(); b.moveTo(120, 0); b.quadTo(118, -16, 90, -18); b.lineTo(-90, -10); b.lineTo(-130, -6)
    b.lineTo(-130, 2); b.lineTo(-90, 6); b.lineTo(90, 12); b.quadTo(118, 12, 120, 0); b.close(); cv.drawPath(b, pa)
    cv.drawRect(skia.Rect(-20, 4, 40, 12), pa)                       # wing root
    cv.drawRoundRect(skia.Rect(30, -6, 78, 14), 6, 6, pa)            # engine nacelle
    f = skia.Path(); f.moveTo(-112, -6); f.lineTo(-130, -44); f.lineTo(-140, -44); f.lineTo(-134, -6); f.close(); cv.drawPath(f, pa)
    cv.drawRect(skia.Rect(-150, -6, -104, 0), pa)                    # tailplane
    cv.drawLine(79, -14, 79, 22, P(rgb, a, 3))                       # propeller blur
    cv.restore()


def sea_night(cv, t, horizon=880, stars=40, chop=1.0):
    night_sky(cv, (4, 6, 11), (26, 34, 48), horizon, stars)
    sh = skia.GradientShader.MakeLinear([(0, horizon), (0, H)], [C((18, 26, 36)), C((3, 5, 8))])
    cv.drawRect(skia.Rect(0, horizon, W, H), skia.Paint(Shader=sh))
    for i in range(42):
        z = i / 42; y = horizon + 6 + (z ** 1.9) * (H - horizon); amp = (2 + 20 * z ** 2) * chop
        p = skia.Path(); ph = t * (0.7 + z * 1.6) + i * 1.7
        for xi in range(0, W + 40, 40):
            yy = y + amp * math.sin(xi * (0.012 / (0.3 + z)) + ph) + amp * 0.5 * math.sin(xi * 0.031 + ph * 1.7)
            (p.moveTo if xi == 0 else p.lineTo)(xi, yy)
        cv.drawPath(p, P(ICE, 16 + 48 * z, 1.2 + 2.4 * z))


# map projection for the stylised Pacific chart
def mp(lon, lat):
    return 60 + (lon - 143) * 21.5, 640 - lat * 46


def chart(cv, t, show_niku=0.0, route=1.0, plane_u=None):
    cv.drawRect(skia.Rect(0, 0, W, H), P((22, 30, 40)))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, 1250), SAMP, skia.Paint(Alphaf=0.10, BlendMode=skia.BlendMode.kOverlay))
    for i in range(0, W, 108):
        cv.drawLine(i, 120, i, 1250, P(STEEL, 34, 1.5))
    for j in range(120, 1250, 108):
        cv.drawLine(0, j, W, j, P(STEEL, 34, 1.5))
    # equator
    ey = mp(150, 0)[1]
    dp = P(STEEL, 120, 2); dp.setPathEffect(skia.DashPathEffect.Make([16, 10], 0)); cv.drawLine(0, ey, W, ey, dp)
    text(cv, "EQUATOR", 330, ey - 12, font("type", 26), STEEL, 170, shadow=False)
    # New Guinea (very stylised blob around Lae)
    ng = skia.Path(); pts = [(141, -2.4), (144, -3.6), (146.5, -5.6), (147.4, -6.4), (147.8, -7.6), (149.6, -9.4),
                             (150.5, -10.6), (147, -10.2), (144, -8.2), (141, -9.2)]
    for i, (lo, la) in enumerate(pts):
        x, y = mp(lo, la); (ng.moveTo if i == 0 else ng.lineTo)(x, y)
    ng.close(); cv.drawPath(ng, P((44, 52, 60))); cv.drawPath(ng, P(ICE, 110, 2))
    lx, ly = mp(147.0, -6.7); hx, hy = mp(183.4, 0.8); nx, ny = mp(185.5, -4.7)
    # route
    rp = P((255, 90, 80), 230, 5); rp.setPathEffect(skia.DashPathEffect.Make([18, 12], -t * 30))
    ex, ey2 = lx + (hx - lx) * route, ly + (hy - ly) * route
    cv.drawLine(lx, ly, ex, ey2, rp)
    for (x, y, lab, dx) in ((lx, ly, "LAE", -10), (hx, hy, "HOWLAND I.", -250)):
        cv.drawCircle(x, y, 11, P((255, 90, 80)))
        text(cv, lab, x + dx if lab == "LAE" else x + dx, y - 26, font("typeb", 36), WHITE, 240)
    pulse = (t * 0.8) % 1.0
    cv.drawCircle(hx, hy, 14 + 60 * pulse, P((255, 90, 80), 200 * (1 - pulse), 3))
    if show_niku > 0:
        cv.drawCircle(nx, ny, 10, P(ICE, 255 * show_niku))
        text(cv, "NIKUMARORO", nx - 300, ny + 12, font("typeb", 34), ICE, 240 * show_niku)
    text(cv, "≈2,550 MI", (lx + hx) / 2 - 40, (ly + hy) / 2 + 120, font("bebas", 64), (255, 200, 140), 220 * route)
    if plane_u is not None:
        px, py = lx + (hx - lx) * plane_u, ly + (hy - ly) * plane_u
        ang = math.degrees(math.atan2(hy - ly, hx - lx))
        plane_top(cv, px, py, 0.55, ang, WHITE)
    text(cv, "MAP STYLISED · NOT TO SCALE", 64, 230, font("type", 26), STEEL, 190, shadow=False)


def radio_scope(cv, t, y, live, a=1.0):
    cv.drawRoundRect(skia.Rect(70, y - 120, W - 70, y + 120), 18, 18, P((6, 10, 12), 230 * a))
    cv.drawRoundRect(skia.Rect(70, y - 120, W - 70, y + 120), 18, 18, P((90, 200, 160), 120 * a, 3))
    for i in range(1, 8):
        cv.drawLine(70 + i * 117, y - 120, 70 + i * 117, y + 120, P((90, 200, 160), 30 * a, 1))
    p = skia.Path()
    for xi in range(80, W - 70, 6):
        amp = live * 80 * (0.5 + 0.5 * math.sin(xi * 0.013 + t * 3)) * abs(math.sin(xi * 0.09 + t * 21)) * (0.6 + 0.4 * math.sin(t * 9 + xi * 0.002))
        yy = y + amp * math.sin(xi * 0.21 + t * 37) + (1 - live) * 1.5 * math.sin(xi * 0.4 + t * 50)
        (p.moveTo if xi == 80 else p.lineTo)(xi, yy)
    cv.drawPath(p, P((120, 255, 200), 230 * a, 3))
    text(cv, "3105 kc", 96, y - 82, font("typeb", 28), (120, 255, 200), 190 * a, shadow=False)


def reef(cv, t, cx, cy, s):
    """atoll seen from above: ring of land round a lagoon (stylised)"""
    cv.drawRect(skia.Rect(0, 0, W, H), P((10, 22, 34)))
    for i in range(18):
        r = 520 + i * 40 + 8 * math.sin(t * 1.5 + i)
        cv.drawOval(skia.Rect(cx - r * s * 1.25, cy - r * s * 0.62, cx + r * s * 1.25, cy + r * s * 0.62), P(ICE, 18 - i * 0.8, 2))
    ring = skia.Path(); ring.addOval(skia.Rect(cx - 470 * s, cy - 220 * s, cx + 470 * s, cy + 220 * s))
    cv.drawPath(ring, P((150, 170, 150), 255, 70 * s))                                 # sand/vegetation band
    cv.drawPath(ring, P((60, 82, 60), 255, 40 * s))
    lag = skia.GradientShader.MakeRadial((cx, cy), 430 * s, [C((60, 130, 140)), C((24, 70, 84))])
    cv.drawOval(skia.Rect(cx - 432 * s, cy - 186 * s, cx + 432 * s, cy + 186 * s), skia.Paint(Shader=lag, AntiAlias=True))
    for i in range(30):   # palm dots on the ring
        a_ = i / 30 * 2 * math.pi
        cv.drawCircle(cx + math.cos(a_) * 470 * s, cy + math.sin(a_) * 220 * s, 12 * s, P((30, 52, 34)))


# ---------------------------------------------------------------- scenes
def sc_hook(cv, t):
    sea_night(cv, t, 880, 60)
    g = skia.GradientShader.MakeRadial((700, 500), 520, [C((200, 215, 230), 90), C((0, 0, 0), 0)])
    cv.drawCircle(700, 500, 520, skia.Paint(Shader=g))
    cv.drawCircle(700, 500, 175, P((214, 222, 230)))
    cv.drawCircle(640, 450, 34, P((190, 198, 208))); cv.drawCircle(770, 560, 22, P((192, 200, 210)))
    for i in range(10):   # moon path on the sea
        cv.drawLine(560 + i * 8, 900 + i * 40, 840 - i * 8, 900 + i * 40, P((200, 215, 230), 60 - i * 5, 3))
    storm_clouds(cv, t, 0.55)
    plane_side(cv, 540 + t * 38, 520 + 6 * math.sin(t * 1.4), 2.2, -3, (4, 5, 8))
    fog_bank(cv, t, 850, 0.6)


def sc_flight(cv, t):
    u = t - CUT["flight"]
    chart(cv, t, 0, ease(u / 2.5), min(0.9, u / 4.2 * 0.9))


def sc_radio(cv, t):
    u = t - CUT["radio"]
    sea_night(cv, t, 860, 30, 1.2)
    storm_clouds(cv, t, 0.6)
    steamer(cv, 640, 980 + 4 * math.sin(t * 1.2), 0.85, 255, (6, 8, 11), True, t)
    text(cv, "USCGC ITASCA", 520, 1060, font("typeb", 30), STEEL, 200)
    live = 1.0 if t < word_t("radio", "silence") - 0.2 else max(0.0, 1 - (t - word_t("radio", "silence") + 0.2) / 0.3)
    for j in range(4):   # radio rings from the ship's mast
        ph = ((t * 0.6 + j * 0.25) % 1.0)
        cv.drawCircle(830, 750, 30 + ph * 500, P((120, 255, 200), 90 * (1 - ph) * live, 3))
    radio_scope(cv, t, 400, live)
    if live < 0.5:
        text(cv, "NO SIGNAL", 540, 412, font("bebas", 90), (255, 90, 80), 255 * (1 - live * 2), "c")


def rank_bg(cv, t, rgb):
    cv.drawRect(skia.Rect(0, 0, W, H), P(rgb))
    cv.drawImageRect(PAPER, skia.Rect(0, 0, W, 1250), SAMP, skia.Paint(Alphaf=0.07, BlendMode=skia.BlendMode.kOverlay))


def big_rank(cv, t, k, n):
    u = t - CUT[k]
    a = ease(u / 0.25)
    f = font("bebas", 420)
    cv.save(); cv.translate(980, 600); cv.scale(1 + 0.25 * (1 - a), 1 + 0.25 * (1 - a))
    text(cv, f"#{n}", 0, 0, f, (255, 90, 80) if n == 1 else STEEL, 70 * a, "r", shadow=False)
    cv.restore()


def sc_t4(cv, t):
    rank_bg(cv, t, (14, 16, 22))
    big_rank(cv, t, "t4", 4)
    # quiet street at night, one lit window
    cv.drawRect(skia.Rect(0, 980, W, 1100), P((8, 9, 12)))
    for x0, w0, h0 in ((40, 300, 300), (380, 340, 360), (760, 300, 280)):
        cv.drawRect(skia.Rect(x0, 980 - h0, x0 + w0, 980), P((20, 22, 28)))
        rf = skia.Path(); rf.moveTo(x0 - 20, 980 - h0); rf.lineTo(x0 + w0 / 2, 980 - h0 - 120); rf.lineTo(x0 + w0 + 20, 980 - h0); rf.close()
        cv.drawPath(rf, P((20, 22, 28)))
    cv.drawRect(skia.Rect(500, 740, 600, 830), P((255, 200, 120), 200 + 30 * math.sin(t * 2)))
    g = skia.GradientShader.MakeRadial((550, 785), 220, [C((255, 190, 110), 70), C((0, 0, 0), 0)])
    cv.drawCircle(550, 785, 220, skia.Paint(Shader=g))
    # ID card with a redaction bar where the "new name" would be
    cv.save(); cv.translate(110, 230); cv.rotate(-4)
    cv.drawRoundRect(skia.Rect(0, 0, 560, 250), 10, 10, P((196, 184, 156)))
    text(cv, "NAME:", 30, 70, font("typeb", 34), (40, 34, 26), 255, shadow=False)
    red = ease((t - CUT["t4"] - 0.4) / 0.6)
    cv.drawRect(skia.Rect(160, 40, 160 + 360 * red, 80), P((10, 10, 10)))
    text(cv, "ALIAS?", 30, 150, font("typeb", 34), (40, 34, 26), 255, shadow=False)
    cv.drawRect(skia.Rect(180, 120, 180 + 280 * red, 160), P((10, 10, 10)))
    cv.restore()
    a = ease((t - word_t("t4", "debunked") + 0.05) / 0.25)
    if a > 0:
        stamp(cv, "DEBUNKED", 540, 520, -9, 1 + 0.5 * (1 - a), a, 130)


def sc_t3(cv, t):
    rank_bg(cv, t, (16, 18, 22))
    big_rank(cv, t, "t3", 3)
    # stylised "photo" print: an empty dock, no people
    cv.save(); cv.translate(150, 210); cv.rotate(3)
    cv.drawRect(skia.Rect(-20, -20, 640, 520), P((226, 220, 204)))
    cv.drawRect(skia.Rect(0, 0, 620, 440), P((120, 118, 110)))
    cv.drawRect(skia.Rect(0, 0, 620, 210), P((168, 166, 158)))
    cv.drawRect(skia.Rect(0, 270, 620, 300), P((70, 68, 62)))                      # dock edge
    for x in range(30, 620, 90):
        cv.drawRect(skia.Rect(x, 300, x + 10, 440), P((60, 58, 52)))
    sh = skia.Path(); sh.moveTo(380, 200); sh.lineTo(600, 200); sh.lineTo(580, 240); sh.lineTo(400, 240); sh.close()
    cv.drawPath(sh, P((80, 78, 72))); cv.drawRect(skia.Rect(470, 90, 478, 200), P((80, 78, 72)))
    r = np.random.default_rng(3)
    for _ in range(500):
        cv.drawCircle(r.uniform(0, 620), r.uniform(0, 440), r.uniform(0.5, 2), P((40, 40, 36), r.uniform(20, 80)))
    text(cv, "THE 'PROOF' PHOTO · STYLISED", 0, 495, font("typeb", 28), (60, 56, 48), 255, shadow=False)
    cv.restore()
    a = ease((t - word_t("t3", "printed") + 0.05) / 0.25)
    if a > 0:
        stamp(cv, "PRINTED IN 1935", 470, 520, -7, 1 + 0.5 * (1 - a), a, 112)


def sc_t2(cv, t):
    u = t - CUT["t2"]
    reef(cv, t, 540, 600, 0.95 + 0.01 * u)
    big_rank(cv, t, "t2", 2)
    # search sweep over the lagoon
    ang = (u * 90) % 360
    sw = skia.Path(); sw.moveTo(540, 600)
    sw.arcTo(skia.Rect(540 - 460, 600 - 460, 540 + 460, 600 + 460), ang, 28, False); sw.close()
    cv.drawPath(sw, P((120, 255, 200), 40))
    cv.drawCircle(540, 600, 460, P((120, 255, 200), 60, 2))
    # boat
    bx = 760 - u * 12
    bt = skia.Path(); bt.moveTo(bx - 40, 560); bt.lineTo(bx + 46, 560); bt.lineTo(bx + 30, 578); bt.lineTo(bx - 34, 578); bt.close()
    cv.drawPath(bt, P((230, 230, 224)))
    a1 = ease((t - word_t("t2", "bones") + 0.1) / 0.3)
    cv.drawCircle(300, 420, 14, P((255, 200, 140), 255 * a1)); cv.drawLine(300, 375, 300, 410, P((255, 200, 140), 200 * a1, 3))
    text(cv, "1940: BONES FOUND", 130, 310, font("typeb", 34), (255, 200, 140), 250 * a1)
    a2 = ease((t - word_t("t2", "lost") + 0.1) / 0.3)
    if a2 > 0:
        text(cv, "LATER LOST", 130, 360, font("typeb", 34), (255, 90, 80), 250 * a2)
    text(cv, "ATOLL STYLISED", 64, 230, font("type", 26), STEEL, 190, shadow=False)
    a = ease((t - word_t("t2", "plane") + 0.05) / 0.25)
    if a > 0:
        stamp(cv, "NO PLANE FOUND", 540, 860, -6, 1 + 0.5 * (1 - a), a, 110)


def fuel_gauge(cv, x, y, level, a=1.0):
    cv.drawCircle(x, y, 120, P((12, 14, 18), 240 * a))
    cv.drawCircle(x, y, 120, P(STEEL, 200 * a, 5))
    for i in range(9):
        ang = math.radians(210 - i * 30)
        cv.drawLine(x + math.cos(ang) * 92, y - math.sin(ang) * 92, x + math.cos(ang) * 110, y - math.sin(ang) * 110,
                    P(ICE, 200 * a, 4))
    text(cv, "E", x - 82, y + 70, font("bebas", 48), (255, 90, 80), 255 * a, "c")
    text(cv, "F", x + 82, y + 70, font("bebas", 48), ICE, 255 * a, "c")
    text(cv, "FUEL", x, y + 60, font("typeb", 26), STEEL, 230 * a, "c")
    ang = math.radians(210 - level * 240)
    cv.drawLine(x, y, x + math.cos(ang) * 96, y - math.sin(ang) * 96, P((255, 90, 80), 255 * a, 7))
    cv.drawCircle(x, y, 12, P(ICE, 255 * a))


def sc_t1(cv, t):
    u = t - CUT["t1"]
    sea_night(cv, t, 880, 30, 1.3)
    storm_clouds(cv, t, 0.8)
    big_rank(cv, t, "t1", 1)
    snk = word_t("t1", "sank")
    d = ease((t - (snk - 1.4)) / 1.4)                      # descent towards the sea
    px = 360 + u * 80; py = 600 + d * 330
    if t < snk + 0.1:
        plane_side(cv, px, py + 6 * math.sin(t * 3), 1.7, 4 + 14 * d, (3, 4, 6))
    else:
        v = t - snk
        for j in range(3):
            r = 30 + v * 120 + j * 50
            cv.drawOval(skia.Rect(px - r * 1.6, 950 - r * 0.25, px + r * 1.6, 950 + r * 0.25), P(ICE, max(0, 160 - v * 60 - j * 40), 3))
    fuel_gauge(cv, 250, 330, max(0.0, 0.25 - u * 0.09))


def sc_end(cv, t):
    u = t - CUT["end"]
    sea_night(cv, t, 860, 70, 0.9)
    fog_bank(cv, t, 830, 1.0, 16)
    ph = (u * 0.5) % 1.0
    cv.drawOval(skia.Rect(540 - 900 * ph, 1000 - 140 * ph, 540 + 900 * ph, 1000 + 140 * ph), P((120, 255, 200), 120 * (1 - ph), 3))
    plane_top(cv, 540, 470, 1.0, -90, ICE, 0)
    p = skia.Path(); p.addCircle(540, 520, 1)
    # dashed empty outline where the plane should be
    cv.save(); cv.translate(540, 470); cv.rotate(-90); cv.scale(1.4, 1.4)
    out = skia.Path(); out.addOval(skia.Rect(-60, -9, 64, 9)); out.addRect(skia.Rect(-14, -92, 18, 92)); out.addRect(skia.Rect(-62, -30, -50, 30))
    dp = P(ICE, 170, 2.5); dp.setPathEffect(skia.DashPathEffect.Make([9, 7], -t * 14)); cv.drawPath(out, dp)
    cv.restore()
    a = ease((t - word_t("end", "found") + 0.1) / 0.3)
    if a > 0:
        stamp(cv, "NEVER FOUND", 540, 300, -7, 1 + 0.5 * (1 - a), a, 120)


SCENE_FN = {"hook": sc_hook, "flight": sc_flight, "radio": sc_radio, "t4": sc_t4, "t3": sc_t3, "t2": sc_t2,
            "t1": sc_t1, "end": sc_end}
HEAD = {"hook": "", "flight": "2 JULY 1937 · LAE TO HOWLAND", "radio": "“WE MUST BE ON YOU…”",
        "t4": "SHE LIVED ON IN SECRET", "t3": "CAPTURED BY JAPAN", "t2": "CASTAWAY ON NIKUMARORO",
        "t1": "OUT OF FUEL. LOST AT SEA.", "end": "WHICH THEORY DO YOU BELIEVE?"}
PILLS = {"radio": "LAST CALLS · USCGC ITASCA LOG", "t4": "THEORY #4 · LEAST LIKELY", "t3": "THEORY #3", "t2": "THEORY #2",
         "t1": "THEORY #1 · MOST LIKELY", "end": "STILL UNSOLVED"}
KICKER = "CASE FILE #005 · JULY 1937 · PACIFIC"
RANK_OF = {"t4": 4, "t3": 3, "t2": 2, "t1": 1}


def rank_ladder(cv, t, k):
    """four small boxes top-left: the current theory lights up red, earlier ones dim"""
    if k not in RANK_OF and k != "end":
        return
    cur = RANK_OF.get(k, 0)
    for i, n in enumerate((4, 3, 2, 1)):
        x = 64 + i * 112; y = 1040
        on = n == cur; done = cur and n > cur or k == "end"
        cv.drawRoundRect(skia.Rect(x, y - 62, x + 96, y + 10), 10, 10, P(RED if on else (24, 28, 34), 235 if on else 200))
        cv.drawRoundRect(skia.Rect(x, y - 62, x + 96, y + 10), 10, 10, P(STEEL, 160, 2))
        text(cv, f"#{n}", x + 48, y - 6, font("bebas", 60), WHITE if on else (STEEL if not done else (90, 98, 108)), 255, "c", shadow=False)
        if done and not on:
            cv.drawLine(x + 14, y - 26, x + 82, y - 26, P((255, 90, 80), 200, 4))


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
    hook = t < CUT["flight"]
    rank_ladder(cv, t, k)
    text(cv, KICKER, X, 1236, font("type", 31), STEEL, 235)
    if hook:
        f = fit("AMELIA EARHART VANISHED.", "bebas", 140, 900)
        text(cv, "AMELIA EARHART VANISHED.", X, 1372, f, WHITE)
        text(cv, "4 THEORIES, RANKED.", X, 1496, f, (255, 90, 80))
        stamp(cv, "NEVER FOUND", 690, 1100, -8, 1.0, 1.0, 96)
    else:
        fl = 1.0 if t - CUT[k] > 0.25 else ease((t - CUT[k]) / 0.25)
        if k in PILLS:
            pill(cv, PILLS[k], X, 1316, 255 * fl)
        hf = fit(HEAD[k], "bebas", 100, MAXW)
        text(cv, HEAD[k], X, 1436, hf, (255, 90, 80) if k in ("t1",) else WHITE, 255 * fl)
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
