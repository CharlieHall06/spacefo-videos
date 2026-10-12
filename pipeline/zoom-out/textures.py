"""Pre-render the heavy textures once: Earth map, Sun disk + corona, Milky Way,
Laniakea flow map and the observable-universe cosmic web."""
import numpy as np, cv2, os, sys
from scipy.spatial import cKDTree, Voronoi

os.makedirs("tex", exist_ok=True)
rng = np.random.default_rng(7)


def spectral(P, n, fmin, fmax, seed, slope=1.0):
    r = np.random.default_rng(seed)
    out = np.zeros(P.shape[:-1], np.float32)
    for _ in range(n):
        f = fmin * (fmax / fmin) ** r.random()
        d = r.normal(size=3).astype(np.float32); d /= np.linalg.norm(d)
        out += np.sin(f * (P @ d) + r.random() * 6.283) / f ** slope
    return out


def norm01(a):
    a = a - a.min(); return a / a.max()


def tonemap(rgb, exposure):
    return 1.0 - np.exp(-exposure * rgb)


def save(name, rgb):
    out = np.clip(rgb, 0, 1) ** (1 / 1.1)
    cv2.imwrite(f"tex/{name}.png", (out[..., ::-1] * 255).astype(np.uint8))
    print("saved", name, out.shape, flush=True)


# ---------------------------------------------------------------- Earth map
def earth():
    Hh, Ww = 1024, 2048
    lat = (0.5 - (np.arange(Hh) + 0.5) / Hh) * np.pi
    lon = ((np.arange(Ww) + 0.5) / Ww) * 2 * np.pi - np.pi
    LON, LAT = np.meshgrid(lon, lat)
    P = np.stack([np.cos(LAT) * np.cos(LON), np.sin(LAT), np.cos(LAT) * np.sin(LON)], -1).astype(np.float32)
    warp = np.stack([spectral(P, 24, 2, 6, s) for s in (11, 12, 13)], -1) * 0.25
    Pw = P + warp
    n = spectral(Pw, 90, 1.6, 28, 21, 1.15)
    thr = np.percentile(n, 68)
    land = n > thr
    coast = np.clip((thr - n) / (n.std() * 0.35), 0, 1)  # 0 at coast -> 1 deep
    ocean = np.stack([6 + 14 * (1 - coast), 34 + 60 * (1 - coast), 88 + 70 * (1 - coast)], -1) / 255
    arid = norm01(spectral(Pw, 40, 3, 20, 33)) * 0.8 + 0.35 * np.exp(-((np.abs(LAT) - 0.42) / 0.18) ** 2)
    arid = np.clip(arid, 0, 1)[..., None]
    rough = norm01(spectral(Pw, 60, 10, 60, 44))[..., None]
    green = np.array([38, 92, 44]) / 255; dry = np.array([168, 140, 92]) / 255
    landc = green * (1 - arid) + dry * arid
    landc = landc * (0.75 + 0.45 * rough)
    rgb = np.where(land[..., None], landc, ocean)
    ice = (np.abs(LAT) + 0.08 * spectral(P, 20, 4, 18, 55)) > 1.18
    rgb = np.where(ice[..., None], np.array([0.92, 0.95, 0.98]), rgb)
    cl = spectral(Pw * 1.0 + 0.4 * warp, 120, 3, 45, 77, 0.9)
    cl = norm01(cl)
    clouds = np.clip((cl - 0.55) / 0.3, 0, 1) ** 1.2 * 0.9
    lights = (land & ~ice) & (norm01(spectral(P, 80, 20, 90, 91)) > 0.72)
    np.savez_compressed("tex/earth.npz", rgb=rgb.astype(np.float16), clouds=clouds.astype(np.float16),
                        lights=lights, land=land)
    print("saved earth", flush=True)


# ---------------------------------------------------------------- Sun
def sun():
    S = 1024
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    x = (x + 0.5) / S * 2 - 1; y = (y + 0.5) / S * 2 - 1
    r2 = x * x + y * y
    inside = r2 < 1
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    P = np.stack([x, y, z], -1)
    gran = spectral(P, 160, 40, 160, 5, 0.6)
    mott = spectral(P, 50, 4, 20, 6, 1.0)
    g = norm01(gran) * 0.6 + norm01(mott) * 0.4
    mu = z
    I = (1 - 0.62 * (1 - mu)) * (0.86 + 0.28 * g)
    # sunspots
    spots = np.zeros_like(I)
    for cx, cy, rr in [(-0.25, 0.18, 0.045), (-0.18, 0.22, 0.03), (0.32, -0.12, 0.035), (0.38, -0.08, 0.02)]:
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        spots = np.maximum(spots, np.clip(1 - d / rr, 0, 1) ** 0.7)
    I = I * (1 - 0.75 * spots)
    stops = np.array([[0.0, 120, 30, 5], [0.35, 225, 95, 22], [0.6, 255, 160, 55], [0.82, 255, 214, 130], [1.0, 255, 250, 232]])
    Ic = np.clip(I, 0, 1)
    rgb = np.stack([np.interp(Ic, stops[:, 0], stops[:, i]) for i in (1, 2, 3)], -1) / 255
    edge = np.clip((1 - np.sqrt(r2)) * S / 2 / 1.5, 0, 1)  # AA edge
    a = (inside * edge).astype(np.float32)
    rgba = np.dstack([rgb * a[..., None], a])  # premultiplied-ish (rgb already * a)
    out = np.clip(np.dstack([rgb, a]), 0, 1)
    cv2.imwrite("tex/sun_disk.png", (out[..., [2, 1, 0, 3]] * 255).astype(np.uint8))
    # corona sprite: image spans 4 sun radii (radius) -> sun radius = S/8
    C = 1024
    y, x = np.mgrid[0:C, 0:C].astype(np.float32)
    x = (x + 0.5) / C * 2 - 1; y = (y + 0.5) / C * 2 - 1
    r = np.sqrt(x * x + y * y) * 4  # in sun radii
    ang = np.arctan2(y, x)
    streak = 1 + 0.35 * norm01(sum(np.sin(k * ang + rng.random() * 6.28) / k for k in range(2, 14)))
    glow = (np.exp(-(np.maximum(r - 1, 0)) * 3.2) * 0.9 + np.exp(-(np.maximum(r - 1, 0)) * 0.9) * 0.35 * streak
            + np.exp(-r * 0.45) * 0.12)
    glow *= np.clip(1 - r / 4, 0, 1) ** 1.5
    col = np.array([1.0, 0.62, 0.22])
    rgb = glow[..., None] * col
    rgb = tonemap(rgb, 1.6)
    save("sun_corona", rgb)


# ---------------------------------------------------------------- Milky Way
def galaxy():
    N = 4096
    span = 120000.0  # ly across the texture
    px = N / span
    acc = np.zeros((N, N, 3), np.float32)
    dust = np.zeros((N, N), np.float32)

    def splat(buf, xs, ys, w):
        ix = (xs * px + N / 2).astype(np.int64); iy = (ys * px + N / 2).astype(np.int64)
        ok = (ix >= 0) & (ix < N) & (iy >= 0) & (iy < N)
        idx = iy[ok] * N + ix[ok]
        if buf.ndim == 3:
            for c in range(3):
                buf[..., c] += np.bincount(idx, weights=w[ok, c], minlength=N * N).reshape(N, N)
        else:
            buf += np.bincount(idx, weights=w[ok], minlength=N * N).reshape(N, N)

    sun_dir = np.array([0.8, 0.6]); sun_r = 26000.0
    sun_ang = np.arctan2(sun_dir[1], sun_dir[0])
    pitch = np.deg2rad(12.5); b = 1 / np.tan(pitch)
    r0 = 6500.0
    # arm phases: choose so that the Sun sits between two arms, with a spur through it
    base = sun_ang - b * np.log(sun_r / r0)
    arms = [(base + 0.9, 1.0), (base + 0.9 + np.pi, 1.0), (base + 0.9 + np.pi / 2, 0.6), (base + 0.9 + 3 * np.pi / 2, 0.6)]

    waves = [(np.random.default_rng(300 + i).normal(size=2), np.random.default_rng(400 + i).random() * 6.28,
              1 / (500 + 4000 * np.random.default_rng(500 + i).random())) for i in range(40)]

    def clump(x, y):
        v = np.zeros_like(x)
        for d, ph, f in waves:
            d = d / np.linalg.norm(d)
            v += np.sin(f * (x * d[0] + y * d[1]) + ph) * (f * 2500) ** -0.7
        return (v - v.mean()) / (v.std() + 1e-9)

    def keep_clumpy(x, y, bias=0.0, gain=0.55):
        p = np.clip(0.5 + bias + gain * clump(x, y), 0.03, 1)
        return rng.random(len(x)) < p

    def arm_points(n, phase, spread, rmin=r0, rmax=55000):
        r = rmin * np.exp(rng.random(n) * np.log(rmax / rmin))
        th = phase + b * np.log(r / r0) + rng.normal(0, 0.04, n)
        off = rng.normal(0, 1, n) * spread * (0.5 + r / 25000)
        x = r * np.cos(th) - off * np.sin(th)
        y = r * np.sin(th) + off * np.cos(th)
        return x, y, r, th

    # disk background stars (old, warm) - lots of diffuse light
    n = 2_600_000
    r = rng.exponential(12500, n); r = r[r < 58000]
    th = rng.random(len(r)) * 2 * np.pi
    x = r * np.cos(th); y = r * np.sin(th)
    w = np.ones((len(r), 3)) * np.array([1.0, 0.85, 0.66]) * 0.075
    splat(acc, x, y, w)
    # arms: a tight bright core plus a broad diffuse envelope, broken into clumps
    for phase, strength in arms:
        for spread, nn, wt, col in [(1700, 900_000, 0.55, (0.8, 0.88, 1.0)), (4600, 700_000, 0.22, (0.92, 0.9, 0.92))]:
            n = int(nn * strength)
            x, y, r, th = arm_points(n, phase, spread)
            k = keep_clumpy(x, y)
            x, y, r = x[k], y[k], r[k]
            fade = np.exp(-r / 27000)
            splat(acc, x, y, np.ones((len(x), 3)) * np.array(col) * (wt * fade)[:, None])
        # dust lane slightly inside the arm, patchy
        xd, yd, rd, thd = arm_points(int(700_000 * strength), phase - 0.2, 1000)
        k = keep_clumpy(xd, yd, -0.05, 0.7)
        splat(dust, xd[k], yd[k], np.exp(-rd[k] / 30000) * 1.0)
        # HII regions (pink knots) and young blue stars
        m = int(2600 * strength)
        xh, yh, rh, _ = arm_points(m, phase, 1100, rmin=9000)
        sz = rng.uniform(80, 260, m)[:, None]
        cl = rng.normal(0, 1, (m, 40, 2)) * sz[..., None]
        hx = (xh[:, None] + cl[..., 0]).ravel(); hy = (yh[:, None] + cl[..., 1]).ravel()
        splat(acc, hx, hy, np.ones((len(hx), 3)) * np.array([1.0, 0.34, 0.6]) * 0.16)
        xb, yb, rb, _ = arm_points(m * 8, phase, 1700, rmin=8000)
        splat(acc, xb, yb, np.ones((len(xb), 3)) * np.array([0.62, 0.76, 1.0]) * 0.3)
    # Orion spur through the Sun (faint, clumpy)
    t = rng.random(160000)
    spur_len = 15000
    sx = sun_r * np.cos(sun_ang) + (t - 0.5) * spur_len * np.cos(sun_ang + 1.15) + rng.normal(0, 900, len(t))
    sy = sun_r * np.sin(sun_ang) + (t - 0.5) * spur_len * np.sin(sun_ang + 1.15) + rng.normal(0, 900, len(t))
    k = keep_clumpy(sx, sy)
    splat(acc, sx[k], sy[k], np.ones((k.sum(), 3)) * np.array([0.82, 0.88, 1.0]) * 0.035)
    # bulge + bar
    n = 500_000
    bar_ang = sun_ang + np.deg2rad(28)
    u = rng.normal(0, 1, n) * 5600; v = rng.normal(0, 1, n) * 1700
    bx = u * np.cos(bar_ang) - v * np.sin(bar_ang); by = u * np.sin(bar_ang) + v * np.cos(bar_ang)
    splat(acc, bx, by, np.ones((n, 3)) * np.array([1.0, 0.8, 0.52]) * 0.2)
    n = 400_000
    rr = np.abs(rng.normal(0, 2300, n)); th = rng.random(n) * 2 * np.pi
    splat(acc, rr * np.cos(th), rr * np.sin(th), np.ones((n, 3)) * np.array([1.0, 0.88, 0.66]) * 0.16)

    dust = cv2.GaussianBlur(dust, (0, 0), 5)
    dust = dust / np.percentile(dust[dust > 0], 99)
    att = np.exp(-1.6 * np.clip(dust, 0, 3))[..., None]
    base_img = cv2.GaussianBlur(acc, (0, 0), 1.0)
    glow = (base_img + cv2.GaussianBlur(acc, (0, 0), 5) * 0.8 + cv2.GaussianBlur(acc, (0, 0), 24) * 1.0
            + cv2.GaussianBlur(acc, (0, 0), 110) * 1.4)
    glow *= att
    # stars to sparkle on top (single pixels, not dust-attenuated)
    n = 90000
    r = rng.exponential(15000, n); th = rng.random(n) * 2 * np.pi
    sp = np.zeros_like(acc)
    splat(sp, r * np.cos(th), r * np.sin(th), np.ones((n, 3)) * (rng.random((n, 1)) ** 2 * 2.5 + 0.3))
    glow += cv2.GaussianBlur(sp, (0, 0), 0.8)
    rgb = tonemap(glow, 0.75)
    save("galaxy", rgb)


# ---------------------------------------------------------------- Laniakea
def laniakea():
    N = 4096
    span = 640.0  # million ly
    px = N / span
    acc = np.zeros((N, N, 3), np.float32)

    def splat(xs, ys, col, w):
        ix = (xs * px + N / 2).astype(np.int64); iy = (ys * px + N / 2).astype(np.int64)
        ok = (ix >= 0) & (ix < N) & (iy >= 0) & (iy < N)
        idx = iy[ok] * N + ix[ok]
        for c in range(3):
            acc[..., c] += np.bincount(idx, weights=w[ok] * col[c], minlength=N * N).reshape(N, N)

    # irregular boundary
    phis = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    bnd = 255 * (1 + 0.16 * sum(np.sin(k * phis + rng.random() * 6.28) / k ** 0.8 for k in range(2, 9)) / 2.2)

    def Rb(phi):
        return np.interp(np.mod(phi, 2 * np.pi), phis, bnd, period=2 * np.pi)

    # flow field: toward centre, bent by a few sub-attractors and noise
    subs = [(-60, 40, 0.5), (70, -55, 0.45), (20, 110, 0.35), (-110, -70, 0.35), (130, 60, 0.3)]

    def field(p):
        v = -p / (np.linalg.norm(p, axis=1, keepdims=True) + 5) * 1.0
        for sx, sy, s in subs:
            d = np.array([sx, sy]) - p; dist = np.linalg.norm(d, axis=1, keepdims=True) + 8
            v += d / dist * s * np.exp(-dist / 70)
        q = p / 90.0
        v[:, 0] += 0.35 * np.sin(q[:, 1] * 2.1 + 1.3) + 0.2 * np.sin(q[:, 0] * 3.3 + q[:, 1] * 1.7)
        v[:, 1] += 0.35 * np.cos(q[:, 0] * 1.9 + 0.4) + 0.2 * np.cos(q[:, 1] * 2.9 - q[:, 0] * 1.1)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-6)

    M = 3200
    ang = rng.random(M) * 2 * np.pi
    rad = Rb(ang) * np.sqrt(rng.random(M)) * 0.98
    p = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)
    lines = [p.copy()]
    alive = np.ones(M, bool)
    step = 1.2
    for i in range(420):
        v = field(p)
        p = p + v * step * alive[:, None]
        alive &= np.linalg.norm(p, axis=1) > 6
        lines.append(p.copy())
    L = np.stack(lines, 1)  # M x T x 2
    seglen = np.linalg.norm(np.diff(L, axis=1), axis=2)  # M x T-1 (0 once a line has stopped)
    live = seglen > 1e-3
    tt = np.arange(L.shape[1] - 1)[None, :]
    taper = np.clip(tt / 60.0, 0, 1) * np.ones((M, 1))  # streams fade in from their start
    lines_img = np.zeros_like(acc)
    sub = 4
    a = L[:, :-1, :]; bb = L[:, 1:, :]
    for k in range(sub):
        q = a + (bb - a) * (k / sub)
        xs = q[..., 0][live]; ys = q[..., 1][live]
        w = 0.05 * taper[live]
        ix = (xs * px + N / 2).astype(np.int64); iy = (ys * px + N / 2).astype(np.int64)
        ok = (ix >= 0) & (ix < N) & (iy >= 0) & (iy < N)
        idx = iy[ok] * N + ix[ok]
        img = np.bincount(idx, weights=w[ok], minlength=N * N).reshape(N, N).astype(np.float32)
        lines_img += img[..., None] * np.array([0.82, 0.9, 1.0], np.float32)
    lines_img = np.minimum(lines_img, 0.14)  # stop the convergence point from blowing out
    acc += cv2.GaussianBlur(lines_img, (0, 0), 1.2)
    # galaxies: clusters strung along the flow
    gal = np.zeros_like(acc)

    def gsplat(xs, ys, col, w):
        ix = (xs * px + N / 2).astype(np.int64); iy = (ys * px + N / 2).astype(np.int64)
        ok = (ix >= 0) & (ix < N) & (iy >= 0) & (iy < N)
        idx = iy[ok] * N + ix[ok]
        for c in range(3):
            gal[..., c] += np.bincount(idx, weights=w[ok] * col[c], minlength=N * N).reshape(N, N)

    C = 9000
    li = rng.integers(0, M, C); ti = (rng.random(C) ** 1.3 * 380).astype(int)
    keepc = (ti < 250) | (rng.random(C) < 0.12)
    li, ti = li[keepc], ti[keepc]; C = len(li)
    cx = L[li, ti, 0]; cy = L[li, ti, 1]
    per = rng.integers(3, 30, C)
    gx = np.repeat(cx, per) + rng.normal(0, 1.4, per.sum()); gy = np.repeat(cy, per) + rng.normal(0, 1.4, per.sum())
    G = len(gx)
    bright = rng.random(G) ** 3 * 2.4 + 0.35
    hue = rng.random(G)
    gsplat(gx[hue < 0.6], gy[hue < 0.6], (1.0, 0.84, 0.58), bright[hue < 0.6])
    gsplat(gx[hue >= 0.6], gy[hue >= 0.6], (0.7, 0.82, 1.0), bright[hue >= 0.6])
    # neighbouring galaxies outside the boundary (fainter)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    X = (x + 0.5 - N / 2) / px; Y = (y + 0.5 - N / 2) / px
    R = np.sqrt(X * X + Y * Y); PH = np.arctan2(Y, X)
    rb = Rb(PH)
    nc = 2600
    ccx = rng.uniform(-330, 330, nc); ccy = rng.uniform(-330, 330, nc)
    okc = np.sqrt(ccx ** 2 + ccy ** 2) > Rb(np.arctan2(ccy, ccx)) + 10
    ccx, ccy = ccx[okc], ccy[okc]
    per = rng.integers(2, 25, len(ccx))
    ox = np.repeat(ccx, per) + rng.normal(0, 2.2, per.sum()); oy = np.repeat(ccy, per) + rng.normal(0, 2.2, per.sum())
    gsplat(ox, oy, (0.75, 0.8, 0.95), rng.random(len(ox)) ** 3 * 0.9 + 0.12)
    acc += cv2.GaussianBlur(gal, (0, 0), 1.6) * 6.0
    # faint warm haze inside the basin + thin rim
    inside = np.clip((rb - R) / 25, 0, 1)
    haze = inside * (0.012 + 0.035 * np.exp(-R / 110))
    acc += haze[..., None] * np.array([1.0, 0.62, 0.3])
    rim = np.exp(-((R - rb) / 2.0) ** 2) * 0.05
    acc += rim[..., None] * np.array([0.5, 0.85, 1.0])
    glow = acc + cv2.GaussianBlur(acc, (0, 0), 5) * 0.7 + cv2.GaussianBlur(acc, (0, 0), 30) * 0.7
    glow *= (np.clip((316 - R) / 45, 0, 1) ** 1.5)[..., None]
    rgb = tonemap(glow, 1.2)
    save("laniakea", rgb)
    keep = rng.choice(M, 260, replace=False)
    np.save("tex/lani_lines.npy", L[keep].astype(np.float32))


# ---------------------------------------------------------------- cosmic web
def cosmic():
    N = 4096
    span = 100.0  # billion ly
    px = N / span
    Robs = 46.5
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    X = (x + 0.5 - N / 2) / px; Y = (y + 0.5 - N / 2) / px
    R = np.sqrt(X * X + Y * Y)
    pts = np.stack([X.ravel(), Y.ravel()], 1)
    web = np.zeros(N * N, np.float32)
    for nseeds, width, amp in [(170, 0.55, 1.0), (1300, 0.16, 0.55)]:
        seeds = (rng.random((nseeds, 2)) * 2 - 1) * 52
        tree = cKDTree(seeds)
        d, _ = tree.query(pts, k=2, workers=-1)
        e = (d[:, 1] - d[:, 0]).astype(np.float32)
        web += amp * np.exp(-(e / width) ** 2)
        vor = Voronoi(seeds)
        vv = vor.vertices
        vv = vv[np.all(np.abs(vv) < 50, 1)]
        dv, _ = cKDTree(vv).query(pts, k=1, workers=-1)
        web += amp * 1.2 * np.exp(-(dv.astype(np.float32) / (width * 1.6)) ** 2)
        print("web layer", nseeds, flush=True)
    web = web.reshape(N, N)
    edge_fade = np.clip((Robs * 0.9 - R) / (Robs * 0.12), 0, 1)
    web *= edge_fade
    # galaxies sampled from the web density
    low = cv2.resize(web, (1024, 1024), interpolation=cv2.INTER_AREA)
    prob = (low / low.sum()).ravel()
    G = 900000
    idx = rng.choice(len(prob), G, p=prob)
    gx = (idx % 1024 + rng.random(G)) * 4; gy = (idx // 1024 + rng.random(G)) * 4
    pts_img = np.zeros((N, N), np.float32)
    np.add.at(pts_img, (np.clip(gy.astype(int), 0, N - 1), np.clip(gx.astype(int), 0, N - 1)), rng.random(G) ** 2 + 0.2)
    hue = cv2.GaussianBlur(rng.random((64, 64)).astype(np.float32), (0, 0), 4)
    hue = cv2.resize(norm01(hue), (N, N))
    c1 = np.array([0.78, 0.42, 1.0]); c2 = np.array([1.0, 0.45, 0.75]); c3 = np.array([0.45, 0.65, 1.0])
    col = np.where(hue[..., None] < 0.5, c1 * (1 - hue[..., None] * 2) + c3 * hue[..., None] * 2,
                   c1 * (2 - hue[..., None] * 2) + c2 * (hue[..., None] * 2 - 1))
    acc = web[..., None] * col * 0.12 + pts_img[..., None] * (0.55 * col + 0.45) * 0.35
    # CMB edge ring
    cmb = spectral(np.stack([X / 6, Y / 6, np.zeros_like(X)], -1), 70, 2, 14, 99)
    cmb = norm01(cmb)
    ring = np.exp(-((R - Robs * 0.985) / (Robs * 0.035)) ** 2) * (R < Robs * 1.0) + \
        np.exp(-((R - Robs) / 0.25) ** 2) * 0.6
    cmb_col = np.where(cmb[..., None] > 0.5, np.array([1.0, 0.45, 0.15]) * (cmb[..., None] - 0.5) * 2 + np.array([0.9, 0.55, 0.3]) * (1 - (cmb[..., None] - 0.5) * 2),
                       np.array([0.25, 0.45, 1.0]) * (0.5 - cmb[..., None]) * 2 + np.array([0.9, 0.55, 0.3]) * (cmb[..., None] * 2))
    acc += ring[..., None] * cmb_col * 0.75
    inner_glow = np.clip(1 - R / Robs, 0, 1) ** 2 * 0.05 * (R < Robs)
    acc += inner_glow[..., None] * np.array([0.6, 0.4, 1.0])
    glow = cv2.GaussianBlur(acc, (0, 0), 0.8) + cv2.GaussianBlur(acc, (0, 0), 6) * 0.9 + cv2.GaussianBlur(acc, (0, 0), 40) * 0.7
    rgb = tonemap(glow, 1.4)
    save("cosmic", rgb)


if __name__ == "__main__":
    which = sys.argv[1:] or ["earth", "sun", "galaxy", "laniakea", "cosmic"]
    for w in which:
        globals()[w]()
