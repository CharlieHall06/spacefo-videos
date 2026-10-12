"""Render the zoom-out video frames with skia and pipe them to ffmpeg.
usage: python3 render.py <first_frame> <last_frame_exclusive> <out.mp4>   (or: --still t1,t2,... out_prefix)"""
import sys, math, subprocess
import numpy as np, cv2, skia
from timeline import *

W, H, FPS = 1080, 1920, 30
FX, FY = 540.0, 740.0
AU = 1.495978707e8; LY = 9.4607e12; R_E = 6371.0; R_S = 696340.0
AMBER = (255, 183, 77); WHITE = (255, 255, 255)

# ------------------------------------------------------------------ world layout (km, screen-oriented: +y is down)
O = np.zeros(2)
E_DIR = np.array([-0.70710678, -0.70710678])
E_COMP = E_DIR * 1.12 * R_S          # Earth placed beside the Sun for the size comparison
E_ORB = E_DIR * AU                   # Earth on its real orbit
G = -np.array([0.8, 0.6]) * 26000 * LY            # galactic centre (Sun 26,000 ly out)
LANI = G + np.array([0.925, -0.381]) * 200e6 * LY   # Laniakea centre
CAM = [(E_COMP, 2 * R_E / 0.6), (O, 2 * R_S / 0.62), (O, 2 * 30.07 * AU / 0.86),
       (G, 1e5 * LY / 0.95), (LANI, 520e6 * LY / 0.95), (O, 93e9 * LY / 0.88)]
ANCH = [E_COMP, O, O, G, G]
DRIFT = [0.018, 0.02, 0.02, 0.022, 0.022, 0.012]
ARR = [0.0] + [za[k] for k in STEPS[1:]]
DEP = [zs[k] for k in STEPS[1:]] + [1e9]


def smoother(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def smooth(a, b, x):
    if a == b:
        return float(x >= b)
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def hold_V(i, t):
    return CAM[i][1] * math.exp(DRIFT[i] * (t - ARR[i]))


def camera(t):
    """returns centre (km), view width (km), continuous step index"""
    for i in range(6):
        if i > 0 and t < ARR[i]:
            j = i - 1
            u = (t - DEP[j]) / TD[STEPS[i]]
            e = smoother(u)
            Vd = hold_V(j, DEP[j])
            V = math.exp(lerp(math.log(Vd), math.log(CAM[i][1]), e))
            A = ANCH[j]
            p0 = (A - CAM[j][0]) / Vd * W
            p1 = (A - CAM[i][0]) / CAM[i][1] * W
            p = lerp(p0, p1, e)
            return A - p * V / W, V, j + e
        if t < DEP[i]:
            V = hold_V(i, t)
            if i == 5:  # final pull-back reveals the dark beyond the edge
                V *= math.exp(0.32 * smoother((t - vs["end"] + 0.3) / 2.6))
            return CAM[i][0].copy(), V, float(i)
    return CAM[5][0].copy(), CAM[5][1], 5.0


def earth_world(t):
    if t < zs["solar"]:
        return E_COMP
    u = smoother((t - zs["solar"]) / TD["solar"])
    r = math.exp(lerp(math.log(1.12 * R_S), math.log(AU), u))
    return E_DIR * r


# ------------------------------------------------------------------ assets
def load_rgb(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGBA)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    return skia.Image.fromarray(np.ascontiguousarray(im), colorType=skia.kRGBA_8888_ColorType).withDefaultMipmaps()


TEX = {n: load_rgb(f"tex/{n}.png") for n in ["galaxy", "laniakea", "cosmic", "sun_corona"]}
SUN_DISK = load_rgb("tex/sun_disk.png")
EZ = np.load("tex/earth.npz")
E_ALB = np.ascontiguousarray(EZ["rgb"].astype(np.float32))
E_CLD = np.ascontiguousarray(EZ["clouds"].astype(np.float32))
E_LIT = np.ascontiguousarray(EZ["lights"].astype(np.float32))
E_LAND = np.ascontiguousarray(EZ["land"].astype(np.float32))
LANI_LINES = np.load("tex/lani_lines.npy")  # (n, T, 2) in Mly relative to Laniakea centre
SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

FONT = {w: skia.Typeface.MakeFromFile(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf")
        for w in ["Black", "ExtraBold", "Bold", "SemiBold", "Medium"]}

rng = np.random.default_rng(3)
# screen-space parallax stars (log-uniform radius -> invariant under zoom)
NS = 1300
S_TH = rng.random(NS) * 2 * np.pi
S_F0 = rng.random(NS)
S_MAG = rng.random(NS) ** 2.2
S_TW = rng.random(NS) * 6.283
S_COL = np.array([(255, 255, 255), (200, 220, 255), (255, 235, 210), (255, 210, 190)])[rng.integers(0, 4, NS)]
RMIN, RMAX = math.log(16), math.log(1320)
KPAR = 0.085
# world-space nearby stars around the Sun (log-uniform distance 0.4 - 6000 ly)
NL = 900
L_D = np.exp(rng.uniform(math.log(0.4), math.log(6000), NL)) * LY
L_TH = rng.random(NL) * 2 * np.pi
L_POS = np.stack([L_D * np.cos(L_TH), L_D * np.sin(L_TH)], 1)
L_MAG = rng.random(NL) ** 1.5
L_COL = np.array([(255, 200, 170), (255, 245, 230), (190, 210, 255), (255, 170, 120)])[rng.integers(0, 4, NL)]
# solar system
PLANETS = [  # name, a (AU), angle deg, colour, dot radius px
    ("Mercury", 0.387, 30, (175, 165, 155), 2.2), ("Venus", 0.723, 160, (235, 205, 150), 3.0),
    ("Mars", 1.524, 300, (235, 120, 80), 2.6), ("Jupiter", 5.203, 70, (230, 190, 140), 5.5),
    ("Saturn", 9.537, 330, (235, 210, 160), 5.0), ("Uranus", 19.19, 120, (160, 225, 235), 4.2),
    ("Neptune", 30.07, 210, (100, 140, 255), 4.2)]
AST = rng.uniform(2.2, 3.3, 1400) * AU; AST_TH = rng.random(1400) * 2 * np.pi
KUI = rng.uniform(30.5, 50, 2600) * AU; KUI_TH = rng.random(2600) * 2 * np.pi
# nearby galaxies around the Milky Way (fill the gap before Laniakea)
NLG = 230
LG_D = np.exp(rng.uniform(math.log(1.2), math.log(90), NLG)) * 1e6 * LY
LG_TH = rng.random(NLG) * 2 * np.pi
LG_POS = G + np.stack([LG_D * np.cos(LG_TH), LG_D * np.sin(LG_TH)], 1)
LG_SIZE = rng.uniform(15000, 110000, NLG) * LY
LG_ROT = rng.random(NLG) * 360
LG_SQ = rng.uniform(0.3, 1.0, NLG)
LG_POS[0] = G + np.array([0.6, -0.8]) * 2.5e6 * LY; LG_SIZE[0] = 220000 * LY; LG_SQ[0] = 0.32; LG_ROT[0] = 35   # Andromeda
LG_POS[1] = G + np.array([0.72, -0.62]) * 2.73e6 * LY; LG_SIZE[1] = 60000 * LY; LG_SQ[1] = 0.6; LG_ROT[1] = 120  # Triangulum
# Laniakea flow dots
NDOT = 520
D_LINE = rng.integers(0, len(LANI_LINES), NDOT)
D_OFF = rng.random(NDOT)
D_SPEED = rng.uniform(0.02, 0.05, NDOT)
seg_len = np.linalg.norm(np.diff(LANI_LINES, axis=1), axis=2)
LINE_LIVE = (seg_len > 1e-3).sum(1) + 1


# ------------------------------------------------------------------ helpers
def paint(color=(255, 255, 255), alpha=1.0, stroke=None, blur=None, blend=None, aa=True):
    p = skia.Paint(AntiAlias=aa)
    p.setColor(skia.Color(int(color[0]), int(color[1]), int(color[2]), int(max(0, min(1, alpha)) * 255)))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    return p


def glow_dot(c, x, y, r, color, alpha, core=None):
    if alpha <= 0.01:
        return
    sh = skia.GradientShader.MakeRadial(skia.Point(x, y), r,
                                        [skia.Color(*color, int(255 * min(1, alpha))), skia.Color(*color, int(90 * min(1, alpha))), skia.Color(*color, 0)],
                                        [0.0, 0.25, 1.0])
    p = skia.Paint(AntiAlias=True, Shader=sh); p.setBlendMode(skia.BlendMode.kScreen)
    c.drawCircle(x, y, r, p)
    if core:
        c.drawCircle(x, y, core, paint((255, 255, 255), alpha))


def draw_texture(c, img, cx, cy, size_px, alpha, blend=skia.BlendMode.kScreen):
    if alpha <= 0.005 or size_px < 1:
        return
    p = skia.Paint(AntiAlias=True); p.setAlphaf(min(1, alpha)); p.setBlendMode(blend)
    s = size_px / img.width()
    c.save(); c.translate(cx, cy); c.scale(s, s)
    c.drawImage(img, -img.width() / 2, -img.height() / 2, SAMPLING, p)
    c.restore()


def log_ramp(x, a, b):
    """1 when x <= b, 0 when x >= a (a > b), smooth in log space"""
    if x <= 0:
        return 1.0
    return 1 - smooth(math.log(b), math.log(a), math.log(x))


def text_width(s, font, tracking):
    g = font.textToGlyphs(s)
    return sum(font.getWidths(g)) + tracking * (len(g) - 1)


def draw_text(c, s, cx, y, weight, size, color, alpha, tracking=0.0, maxw=940, shadow=0.75, glow=None, align="c", scale=1.0):
    if alpha <= 0.005 or not s:
        return 0
    font = skia.Font(FONT[weight], size * scale)
    font.setSubpixel(True); font.setEdging(skia.Font.Edging.kAntiAlias)
    tr = tracking * scale
    w = text_width(s, font, tr)
    if w > maxw:
        f = maxw / w
        font.setSize(size * scale * f); tr *= f; w = maxw
    g = font.textToGlyphs(s); ws = font.getWidths(g)
    x0 = cx - w / 2 if align == "c" else cx
    xs = []; x = x0
    for wi in ws:
        xs.append(x); x += wi + tr
    blob = skia.TextBlob.MakeFromPosTextH(s, xs, 0, font)
    if shadow:
        c.drawTextBlob(blob, 0, y + 4, paint((0, 0, 0), alpha * shadow, blur=max(4, size * 0.09)))
    if glow:
        c.drawTextBlob(blob, 0, y, paint(color, alpha * glow, blur=size * 0.18))
    c.drawTextBlob(blob, 0, y, paint(color, alpha))
    return w


def pill(c, s, cx, y, alpha, scale=1.0, size=34):
    if alpha <= 0.005:
        return
    font = skia.Font(FONT["Black"], size * scale)
    tr = 3.5 * scale
    w = text_width(s, font, tr)
    h = size * 1.9 * scale; padx = 30 * scale
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2 - padx, y - h / 2, w + 2 * padx, h), h / 2, h / 2)
    c.drawRRect(r, paint(AMBER, alpha * 0.55, blur=18))
    c.drawRRect(r, paint(AMBER, alpha))
    draw_text(c, s, cx, y + size * 0.36 * scale, "Black", size * scale, (18, 12, 6), alpha, tracking=tr, shadow=0)


def pop(t, t0, t1=1e9, dur=0.22):
    """alpha, scale, dy for an element appearing at t0 and leaving at t1"""
    if t < t0:
        return 0.0, 1.0, 0.0
    u = min(1.0, (t - t0) / dur)
    a = smooth(0, 1, u)
    k = 1.70158
    ob = 1 + (k + 1) * (u - 1) ** 3 + k * (u - 1) ** 2  # easeOutBack
    out = 1 - smooth(t1, t1 + 0.22, t)
    return a * out, 0.9 + 0.1 * ob, (1 - ob) * 16


# ------------------------------------------------------------------ Earth sphere (numpy)
_egrid = {}


def render_earth(D, rot):
    D = int(D)
    if D not in _egrid:
        g = (np.arange(D, dtype=np.float32) + 0.5) / D * 2 - 1
        X, Y = np.meshgrid(g, g)
        r2 = X * X + Y * Y
        Z = np.sqrt(np.clip(1 - r2, 0, 1))
        tilt = math.radians(23.4)
        Xr = X * math.cos(tilt) + Y * math.sin(tilt); Yr = -X * math.sin(tilt) + Y * math.cos(tilt)
        lon0 = np.arctan2(Xr, Z); lat = -np.arcsin(np.clip(Yr, -1, 1))
        v = ((0.5 - lat / np.pi) * 1024 - 0.5).astype(np.float32)
        Lv = np.array([0.62, -0.06, 0.78], np.float32); Lv /= np.linalg.norm(Lv)
        ndl = X * Lv[0] + Y * Lv[1] + Z * Lv[2]
        Hv = Lv + np.array([0, 0, 1], np.float32); Hv /= np.linalg.norm(Hv)
        ndh = np.clip(X * Hv[0] + Y * Hv[1] + Z * Hv[2], 0, 1)
        edge = np.clip((1 - np.sqrt(r2)) * D / 2 / 1.1, 0, 1)
        _egrid[D] = (lon0, v, ndl, ndh, Z, edge)
    lon0, v, ndl, ndh, Z, edge = _egrid[D]
    u = ((((lon0 + rot) / (2 * np.pi) + 0.5) % 1.0) * 2048 - 0.5).astype(np.float32)
    alb = cv2.remap(E_ALB, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    cld = cv2.remap(E_CLD, (u + 37.0) % 2048, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    lit = cv2.remap(E_LIT, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    land = cv2.remap(E_LAND, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    diff = np.clip(ndl, 0, 1)
    day = np.clip((ndl + 0.08) / 0.33, 0, 1)
    light = (0.035 + 1.08 * diff)[..., None]
    col = alb * light
    ca = cld[..., None]
    col = col * (1 - ca) + ca * (0.97 * light)
    spec = (ndh ** 50 * 0.55 * (1 - land) * (1 - cld))[..., None]
    col += spec * np.array([1.0, 0.95, 0.85], np.float32)
    night = (lit * (1 - day) * (1 - cld))[..., None] * np.array([1.0, 0.72, 0.38], np.float32) * 0.85
    col += night
    rim = ((1 - Z) ** 2.4 * (0.2 + 0.8 * day))[..., None] * np.array([0.35, 0.62, 1.0], np.float32) * 0.95
    col = col + rim
    col = 1 - np.exp(-col * 1.15)  # soft tone curve
    rgba = np.dstack([np.clip(col, 0, 1) * 255, edge * 255]).astype(np.uint8)
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)


_earth_cache = {"img": None}


def draw_earth(c, sx, sy, r, t, alpha):
    if alpha <= 0.01:
        return
    if r > 2.6:
        if r > 30 or _earth_cache["img"] is None:
            D = int(min(max(2 * r, 64), 760))
            _earth_cache["img"] = render_earth(D, 0.05 + t * 0.12)
        img = _earth_cache["img"]
        # atmosphere halo
        sh = skia.GradientShader.MakeRadial(skia.Point(sx, sy), r * 1.16,
                                            [skia.Color(90, 160, 255, int(150 * alpha)), skia.Color(90, 160, 255, 0)], [0.86, 1.0])
        p = skia.Paint(AntiAlias=True, Shader=sh); p.setBlendMode(skia.BlendMode.kScreen)
        c.drawCircle(sx, sy, r * 1.16, p)
        p = skia.Paint(AntiAlias=True); p.setAlphaf(alpha)
        c.drawImageRect(img, skia.Rect.MakeXYWH(sx - r, sy - r, 2 * r, 2 * r), SAMPLING, p)
    if r < 6:
        a = alpha * (1 - smooth(3.5, 6, r))
        glow_dot(c, sx, sy, 9, (110, 170, 255), a * 0.9)
        c.drawCircle(sx, sy, max(r, 2.3), paint((140, 190, 255), a))


# ------------------------------------------------------------------ scene
def text_layer(c, t):
    # ---- hook (visible from frame 0)
    out = zs["sun"] + 0.3
    a = 1 - smooth(out, out + 0.25, t)
    if a > 0:
        draw_text(c, "EARTH · 12,742 KM WIDE", 540, 1222, "Bold", 30, AMBER, a, tracking=7)
        draw_text(c, "HOW SMALL", 540, 1338, "Black", 112, WHITE, a, tracking=-1)
        draw_text(c, "ARE WE REALLY?", 540, 1446, "Black", 96, AMBER, a, tracking=-1, glow=0.25)
        pill(c, "WAIT FOR THE LAST ONE", 540, 1540, a)

    def block(kicker, t_k, head, t_h, amber, sub, t_out, sub_t=None, head_size=116):
        a, s, dy = pop(t, t_k, t_out)
        draw_text(c, kicker, 540, 1222 + dy, "Bold", 30, AMBER, a, tracking=7, scale=1)
        a, s, dy = pop(t, t_h, t_out)
        if a <= 0:
            return
        hs = head(t) if callable(head) else head
        c.save(); c.translate(540, 1340); c.scale(s, s); c.translate(-540, -1340)
        draw_text(c, hs, 540, 1338 + dy, "Black", head_size, WHITE, a, tracking=-1)
        y = 1418
        for line in amber:
            draw_text(c, line, 540, y + dy, "Black", 62, AMBER, a, tracking=0, glow=0.22)
            y += 68
        c.restore()
        if sub:
            a2, _, dy2 = pop(t, sub_t if sub_t else t_h + 0.12, t_out)
            ss = sub(t) if callable(sub) else sub
            draw_text(c, ss, 540, y + 4 + dy2, "Medium", 34, WHITE, a2 * 0.9, tracking=0.5)

    def counter(t0, dur, fmt, v1, ease_pow=3):
        def f(t):
            u = min(1, max(0, (t - t0) / dur))
            e = 1 - (1 - u) ** ease_pow
            return fmt(v1 * e, u >= 1)
        return f

    th = seg("sun", 1)
    block("#1 · THE SUN", vs["sun"], counter(th, 0.8, lambda v, d: f"{v:.1f} MILLION", 1.3), th,
          ["EARTHS FIT INSIDE"], "109 Earths wide", zs["solar"] + 0.25)

    def light_sub(t):
        u = min(1, max(0, (t - RING0) / (RING1 - RING0)))
        mins = int(round(u * 250.2))
        return f"Light-travel time: {mins // 60}h {mins % 60:02d}m"
    block("#2 · THE SOLAR SYSTEM", vs["solar"], "4 HOURS", seg("solar", 1),
          ["FOR LIGHT TO", "REACH NEPTUNE"], light_sub, zs["milky"] + 0.25)

    th = seg("milky", 1)
    block("#3 · THE MILKY WAY", vs["milky"], counter(th, 0.9, lambda v, d: f"{int(round(v))} BILLION+", 100), th,
          ["STARS. THE SUN", "IS JUST ONE."], "About 100,000 light-years across", zs["lani"] + 0.25)

    th = seg("lani", 1)
    block("#4 · LANIAKEA SUPERCLUSTER", seg("lani", 0), counter(th, 0.9, lambda v, d: f"{int(round(v)):,}", 100000), th,
          ["GALAXIES"], "About 520 million light-years across", zs["obs"] + 0.25)

    th = seg("obs", 1)
    block("#5 · THE OBSERVABLE UNIVERSE", vs["obs"], counter(th, 1.3, lambda v, d: f"{int(round(v))} BILLION", 93), th,
          ["LIGHT-YEARS ACROSS"], "Hundreds of billions of galaxies", vs["end"] - 0.2, sub_t=seg("obs", 2))

    # ---- ending
    a, s, dy = pop(t, vs["end"])
    if a > 0:
        c.save(); c.translate(540, 1380); c.scale(s, s); c.translate(-540, -1380)
        draw_text(c, "THAT’S ONLY THE", 540, 1330 + dy, "Black", 92, WHITE, a, tracking=-1)
        draw_text(c, "PART WE CAN SEE", 540, 1428 + dy, "Black", 92, AMBER, a, tracking=-1, glow=0.25)
        c.restore()
    a, s, dy = pop(t, seg("end", 1))
    if a > 0:
        c.save(); c.translate(540, 1530); c.scale(s, s); c.translate(-540, -1530)
        pill(c, "STILL FEEL BIG?", 540, 1530 + dy, a, size=40)
        c.restore()
        draw_text(c, "Sizes are estimates. Galaxy counts range from ~100 billion to 2 trillion.", 540, 1608, "Medium", 21,
                  WHITE, a * 0.55, shadow=0.6)


PALETTE = np.array([(8, 20, 46), (46, 20, 6), (7, 12, 34), (18, 9, 38), (6, 22, 34), (24, 7, 38)], float)


def frame(t, dt=1 / FPS):
    C, V, sidx = camera(t)
    C0, V0, _ = camera(max(0, t - dt))
    k = W / V
    shake = np.zeros(2)
    if t >= za["obs"]:
        e = math.exp(-(t - za["obs"]) * 5)
        shake = np.array([math.sin(t * 91), math.cos(t * 77)]) * 11 * e

    def S(p):
        return FX + (p[0] - C[0]) * k + shake[0], FY + (p[1] - C[1]) * k + shake[1]

    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = surf.getCanvas()
    c.clear(skia.Color(0, 0, 0))
    # background tint
    i0 = int(min(5, math.floor(sidx))); i1 = min(5, i0 + 1)
    col = PALETTE[i0] * (1 - (sidx - i0)) + PALETTE[i1] * (sidx - i0)
    sh = skia.GradientShader.MakeRadial(skia.Point(FX, FY), 1450,
                                        [skia.Color(*[int(v) for v in col], 255), skia.Color(*[int(v * 0.35) for v in col], 255), skia.Color(0, 0, 0, 255)],
                                        [0, 0.45, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))

    # ---- parallax star field
    Z = math.log(V); Zp = math.log(V0)
    span = RMAX - RMIN
    f = (S_F0 - KPAR * Z / span) % 1.0
    fp = (S_F0 - KPAR * Zp / span) % 1.0
    r = np.exp(RMIN + f * span); rp = np.exp(RMIN + fp * span)
    cs, sn = np.cos(S_TH), np.sin(S_TH)
    star_a = 0.95 - 0.45 * smooth(4.6, 5.0, sidx)
    fade = np.minimum(np.clip(f / 0.08, 0, 1), np.clip((1 - f) / 0.06, 0, 1)) * np.clip(r / 520, 0.25, 1)
    tw = 0.72 + 0.28 * np.sin(t * 2.7 + S_TW)
    alpha = (0.18 + 0.82 * S_MAG) * fade * tw * star_a
    for i in range(NS):
        if alpha[i] < 0.03:
            continue
        x, y = FX + r[i] * cs[i] + shake[0], FY + r[i] * sn[i] + shake[1]
        if x < -20 or x > W + 20 or y < -20 or y > H + 20:
            continue
        sz = 0.7 + 1.5 * S_MAG[i]
        p = paint(S_COL[i], alpha[i])
        if abs(fp[i] - f[i]) < 0.5 and rp[i] - r[i] > 2.0:
            xp, yp = FX + rp[i] * cs[i], FY + rp[i] * sn[i]
            p.setStrokeWidth(sz * 1.3); p.setStrokeCap(skia.Paint.kRound_Cap)
            c.drawLine(xp, yp, x, y, p)
        else:
            c.drawCircle(x, y, sz, p)

    # ---- cosmic web (observable universe)
    Dcos = 93e9 * LY * k
    a_cos = log_ramp(Dcos, 45000, 7000)
    if a_cos > 0:
        sx, sy = S(O)
        draw_texture(c, TEX["cosmic"], sx, sy, 100e9 * LY * k, a_cos)
        # shockwave at arrival
    # ---- Laniakea
    Dl = 520e6 * LY * k
    a_l = log_ramp(Dl, 26000, 6000) * (1 - log_ramp(Dl, 12, 3))
    if a_l > 0:
        sx, sy = S(LANI)
        draw_texture(c, TEX["laniakea"], sx, sy, 640e6 * LY * k, a_l)
        if 150 < Dl < 30000:
            mly = 1e6 * LY * k  # px per Mly
            da = a_l * smooth(150, 400, Dl)
            for i in range(NDOT):
                ln = LANI_LINES[D_LINE[i]]; n = LINE_LIVE[D_LINE[i]]
                pos = (D_OFF[i] + D_SPEED[i] * t) % 1.0 * (n - 1)
                j = int(pos); fr = pos - j
                pt = ln[j] * (1 - fr) + ln[min(j + 1, n - 1)] * fr
                x, y = sx + pt[0] * mly, sy + pt[1] * mly
                if -10 < x < W + 10 and -10 < y < H + 10:
                    c.drawCircle(x, y, 1.6, paint((255, 236, 200), da * 0.75))
    # ---- Milky Way
    Dg = 1e5 * LY * k
    a_g = log_ramp(Dg, 60000, 9000) * (1 - log_ramp(Dg, 14, 3))
    if a_g > 0:
        sx, sy = S(G)
        draw_texture(c, TEX["galaxy"], sx, sy, 1.2e5 * LY * k, a_g)
    if 0 < Dg <= 14 and a_l > 0:  # galaxy as a glowing point inside Laniakea
        sx, sy = S(G)
        glow_dot(c, sx, sy, 10, (255, 230, 190), log_ramp(Dg, 14, 3) * 0.9)

    # ---- nearby galaxies (between the Milky Way and Laniakea)
    a_lg = (1 - log_ramp(Dg, 500, 140)) * log_ramp(Dl, 14000, 3000)
    if a_lg > 0.01:
        img = TEX["galaxy"]
        for i in range(NLG):
            d_px = LG_D[i] * k
            if d_px < 8 or d_px > 1700:
                continue
            x, y = S(LG_POS[i])
            if not (-60 < x < W + 60 and -60 < y < H + 60):
                continue
            a = a_lg * smooth(8, 50, d_px) * (1 - smooth(1200, 1700, d_px))
            sp = LG_SIZE[i] * k
            if sp < 2.5:
                glow_dot(c, x, y, 5 + sp * 2, (225, 215, 255), a * 0.7)
            else:
                p = skia.Paint(AntiAlias=True); p.setAlphaf(min(1, a)); p.setBlendMode(skia.BlendMode.kScreen)
                sc = sp * 1.2 / img.width()
                c.save(); c.translate(x, y); c.rotate(LG_ROT[i]); c.scale(sc, sc * LG_SQ[i])
                c.drawImage(img, -img.width() / 2, -img.height() / 2, SAMPLING, p)
                c.restore()

    # ---- nearby stars (between the solar system and the galaxy)
    Npx = 30.07 * AU * k
    a_loc = (1 - log_ramp(Npx, 40, 8)) * log_ramp(Dg, 25000, 4000) if Npx < 40 else 0.0
    if a_loc > 0.01:
        sun_x, sun_y = S(O)
        kp = W / V0
        for i in range(NL):
            d_px = L_D[i] * k
            if d_px < 10 or d_px > 1500:
                continue
            x = sun_x + L_POS[i, 0] * k; y = sun_y + L_POS[i, 1] * k
            if not (-20 < x < W + 20 and -20 < y < H + 20):
                continue
            a = a_loc * (0.35 + 0.65 * L_MAG[i]) * smooth(10, 70, d_px) * (1 - smooth(1100, 1500, d_px))
            xp = FX + (L_POS[i, 0] - C0[0]) * kp; yp = FY + (L_POS[i, 1] - C0[1]) * kp
            sz = 0.9 + 1.6 * L_MAG[i]
            p = paint(L_COL[i], a)
            if math.hypot(xp - x, yp - y) > 2.5 and math.hypot(xp - x, yp - y) < 400:
                p.setStrokeWidth(sz * 1.4); p.setStrokeCap(skia.Paint.kRound_Cap)
                c.drawLine(xp, yp, x, y, p)
            else:
                glow_dot(c, x, y, sz * 4, tuple(int(v) for v in L_COL[i]), a * 0.5)
                c.drawCircle(x, y, sz, p)

    # ---- solar system
    a_orb = log_ramp(Npx, 20000, 3500) * (1 - log_ramp(Npx, 40, 7))
    sun_x, sun_y = S(O)
    if a_orb > 0:
        ring_u = (t - RING0) / (RING1 - RING0)
        for name, a_au, ang, colr, rad in PLANETS + [("Earth", 1.0, 225, (110, 170, 255), 0)]:
            rp = a_au * AU * k
            if 1.5 < rp < 16000:
                c.drawCircle(sun_x, sun_y, rp, paint((255, 255, 255), a_orb * (0.3 if name == "Neptune" else 0.17), stroke=1.6))
            if rad == 0:
                continue
            th = math.radians(ang)
            x, y = sun_x + rp * math.cos(th), sun_y + rp * math.sin(th)
            boost = 0.0
            if 0 <= ring_u:
                ft = t - (RING0 + (a_au / 30.07) * (RING1 - RING0))
                if 0 <= ft < 1.0:
                    boost = math.exp(-ft * 5)
            if -20 < x < W + 20 and -20 < y < H + 20:
                glow_dot(c, x, y, rad * 3.2 + boost * 22, colr, a_orb * (0.55 + boost * 0.45))
                c.drawCircle(x, y, rad * (1 + 0.5 * boost), paint(colr, a_orb))
                if name == "Saturn":
                    c.drawOval(skia.Rect.MakeXYWH(x - rad * 2.2, y - rad * 0.7, rad * 4.4, rad * 1.4), paint((235, 215, 170), a_orb * 0.8, stroke=1.4))
                if name == "Neptune" and t > vs["solar"] - 0.5:
                    na = a_orb * smooth(vs["solar"], vs["solar"] + 0.4, t) * (1 - smooth(zs["milky"], zs["milky"] + 0.3, t))
                    draw_text(c, "NEPTUNE", x, y - 18, "Bold", 22, (170, 195, 255), na, tracking=4, shadow=0.6)
        # belts
        for arr, th, aa in [(AST, AST_TH, 0.45), (KUI, KUI_TH, 0.3)]:
            xs = sun_x + arr * k * np.cos(th); ys = sun_y + arr * k * np.sin(th)
            ok = (xs > -5) & (xs < W + 5) & (ys > -5) & (ys < H + 5)
            if ok.sum():
                pts = [skia.Point(float(a), float(b)) for a, b in zip(xs[ok], ys[ok])]
                p = paint((200, 190, 170), a_orb * aa); p.setStrokeWidth(1.6); p.setStrokeCap(skia.Paint.kRound_Cap)
                c.drawPoints(skia.Canvas.kPoints_PointMode, pts, p)
        # light ring: Sun -> Neptune
        if RING0 <= t <= RING1 + 0.8:
            u = min(1.0, (t - RING0) / (RING1 - RING0))
            ra = a_orb * (1 - smooth(RING1 + 0.15, RING1 + 0.8, t))
            rr = max(1.0, u * Npx)
            c.drawCircle(sun_x, sun_y, rr, paint((255, 214, 140), ra * 0.55, stroke=10, blur=8))
            c.drawCircle(sun_x, sun_y, rr, paint((255, 245, 220), ra, stroke=2.6))

    # ---- Sun
    rs = R_S * k
    a_sun_disk = log_ramp(rs, 3200, 1300)
    if a_sun_disk > 0 and rs > 2.5:
        draw_texture(c, TEX["sun_corona"], sun_x, sun_y, rs * 8, a_sun_disk * 0.95)
        p = skia.Paint(AntiAlias=True); p.setAlphaf(a_sun_disk)
        c.save(); c.translate(sun_x, sun_y); c.rotate(t * 1.5)
        c.drawImageRect(SUN_DISK, skia.Rect.MakeXYWH(-rs, -rs, 2 * rs, 2 * rs), SAMPLING, p)
        c.restore()
    if rs < 40:
        ga = (1 - log_ramp(rs, 40, 12)) * (1 - log_ramp(Npx, 10, 2.5))
        glow_dot(c, sun_x, sun_y, 34, (255, 200, 110), ga * 0.95, core=2.4 if ga > 0.05 else None)

    # ---- Earth
    ew = earth_world(t)
    ex, ey = S(ew)
    er = R_E * k
    a_e = 1 - log_ramp(Npx, 30, 8)
    draw_earth(c, ex, ey, er, t, a_e)

    # ---- YOU ARE HERE marker
    ma = 1 - smooth(60, 110, er)
    if ma > 0.01:
        ring_r = max(er * 1.3 + 7, 14) + 1.6 * math.sin(t * 5)
        c.drawCircle(ex, ey, ring_r, paint(AMBER, ma * 0.35, stroke=6, blur=5))
        c.drawCircle(ex, ey, ring_r, paint(AMBER, ma, stroke=2.6))
        lx_dir = 1 if ex < 700 else -1
        x1 = ex + lx_dir * ring_r * 0.72; y1 = ey - ring_r * 0.72
        x2 = x1 + lx_dir * 34; y2 = y1 - 34
        p = paint(AMBER, ma, stroke=2.2); c.drawLine(x1, y1, x2, y2, p)
        font = skia.Font(FONT["Bold"], 24)
        tw_ = text_width("YOU ARE HERE", font, 4)
        tx = x2 + 8 if lx_dir > 0 else x2 - 8 - tw_
        draw_text(c, "YOU ARE HERE", tx, y2 + 8, "Bold", 24, AMBER, ma, tracking=4, align="l", shadow=0.8)

    # ---- arrival flashes + shockwave
    for kk in STEPS[1:]:
        dt_a = t - za[kk]
        if 0 <= dt_a < 0.6:
            amp = 0.5 if kk == "obs" else 0.10
            c.drawRect(skia.Rect.MakeWH(W, H), paint((255, 245, 235), amp * math.exp(-dt_a * 7)))
    if t >= za["obs"] and t < za["obs"] + 1.6:
        d = t - za["obs"]
        rr = 40 + 1500 * (1 - math.exp(-d * 2.6))
        sx, sy = S(O)
        c.drawCircle(sx, sy, rr, paint((215, 185, 255), 0.75 * math.exp(-d * 2.4), stroke=26 * math.exp(-d * 2) + 2, blur=10))
        c.drawCircle(sx, sy, rr, paint((255, 255, 255), 0.6 * math.exp(-d * 2.4), stroke=3))

    # ---- legibility gradient + vignette
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 1080), skia.Point(0, 1700)],
                                        [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 150)])
    c.drawRect(skia.Rect.MakeXYWH(0, 1080, W, H - 1080), skia.Paint(Shader=sh))
    sh = skia.GradientShader.MakeRadial(skia.Point(FX, 900), 1250, [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 170)], [0, 0.6, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))

    text_layer(c, t)
    return surf.makeImageSnapshot().toarray()


def main():
    if sys.argv[1] == "--still":
        times = [float(x) for x in sys.argv[2].split(",")]
        for tt in times:
            img = frame(tt)
            cv2.imwrite(f"{sys.argv[3]}_{tt:05.2f}.jpg", cv2.cvtColor(img, cv2.COLOR_RGBA2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
        return
    f0, f1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        img = frame(fi / FPS)
        ff.stdin.write(img.tobytes())
        if fi % 60 == 0:
            print(out, fi, flush=True)
    ff.stdin.close(); ff.wait()


if __name__ == "__main__":
    main()
