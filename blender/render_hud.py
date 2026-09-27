"""Render the xianxia HUD kit to godot/ui/hud/ (headless Blender + numpy).

    python blender/render_hud.py [--out godot/ui/hud] [--only panel,gauge_hp] [--samples 48]

Every piece is modelled as small 3D geometry (bevelled lacquer slabs, round
gold-leaf wires, jade cabochons, bevelled brush-font glyphs, ruyi cloud-scroll
curls) and rendered with Cycles through an orthographic top-down camera to a
transparent PNG. Soft brush/ink textures, troughs and glows are numpy. The run
is deterministic (fixed seeds, fixed Cycles seed) and regenerates everything.

Pixel density: every PNG is rendered at SCALE (2) x its *logical* size, the
size it occupies on a 1280x720 screen. Godot draws it at the logical size, so
with the canvas_items stretch mode it stays crisp up to 1440p and beyond.
``hud_kit.json`` (written next to the PNGs) records, per piece and in LOGICAL
pixels: the canvas size, the 9-slice patch margins [left, top, right, bottom],
the drop-shadow pad, suggested content margins, and for gauges the window rect
[x, y, w, h] where the trough/fill textures go. ui_theme.gd / hud.gd read it.

Kit (logical sizes):
  panel_fill / panel_frame   96x96  9-slice, margins 26, pad 6. Two layers so a
                             caller's bg colour tints the lacquer and its border
                             colour tints the gilt frame independently.
  scroll                     300x150 quest-tracker hanging scroll, margins
                             26/28/26/28 (rollers live in the top/bottom margins).
  button_{normal,hover,pressed,disabled}  120x34, margins 12/10.
  toast                      240x36 ribbon (arrow tip / swallowtail), margins 22/9/18/9.
  prompt                     220x40 capsule plate, margins 24/14.
  chip                       30x28 keycap, margins 9.
  portrait_frame             144x144, 128x128 opening at (8,8), margins 26.
  gauge_{hp,qi}_frame        244x32 medallion (血 / 气) + bronze housing; window 30,11 200x10.
  gauge_xp_frame             244x14; window 30,4.5 200x5.
  boss_frame                 560x44; window 48,18 464x12.
  fill_{hp,qi,xp,boss}       liquid capsules exactly the window size.
  trough_{gauge,xp,boss,compass}  recessed dark channels, window size.
  glow_gauge / glow_ring     additive white halos (tinted in Godot).
  spark                      8x16 leading-edge highlight of a draining/filling bar.
  compass_frame              320x44; window 32,9 256x26.
  compass_strip              768x26, 360 degrees (north at x=0 and x=768), tileable.
  marker / marker_edge       objective pin (20x26) and edge chevron (12x16).
  ring_{frame,fill,under}    112x112 meditation ring (radial fill, clockwise).
  lotus / lotus_done         20x20 objective bullets.
  divider                    300x14 ornamental rule.
  banner                     720x110 ink brush stroke with gilt swashes.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from xianxia import hud_art as A  # noqa: E402
from xianxia.hud_art import Canvas, mat  # noqa: E402

ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(ROOT, "godot", "ui", "fonts")
HANZI = os.path.join(FONT_DIR, "MaShanZheng-HudSubset.ttf")
LATIN = os.path.join(FONT_DIR, "Marcellus-Regular.ttf")
SCALE = 2

KIT = {"scale": SCALE, "items": {}}
OUT = ""
SAMPLES = 48


def out(name):
    return os.path.join(OUT, name + ".png")


def record(name, **info):
    KIT["items"][name] = info


def rr(x0, y0, x1, y1, r):
    return A.rounded_rect_pts(x0, y0, x1, y1, r)


def corner_curls(cv, x0, y0, x1, y1, inset, size, material, z, radius=0.62):
    """Cloud scrolls on the four corners of a rectangle (inset px in)."""
    a, b = x0 + inset, y0 + inset
    c, d = x1 - inset, y1 - inset
    for cx, cy, ang, mir in ((a, b, 0, False), (c, b, 0, True), (a, d, 180, True), (c, d, 180, False)):
        A.draw_strokes(cv, A.place(A.xiangyun(), cx, cy, size, ang, mir), radius, material, z)


def lozenge(cx, cy, rx, ry):
    return [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]


# ------------------------------------------------------------------- panels

def build_panel():
    W = H = 96
    pad = 6
    x0, y0, x1, y1 = pad, pad, W - pad, H - pad
    depth = 3.0

    def slab(cv):
        return A.slab(cv, [rr(x0 + 1.2, y0 + 1.2, x1 - 1.2, y1 - 1.2, 6)], depth, 1.2, mat("lacquer"))

    cv = Canvas(W, H)
    slab(cv)
    cv.render(out("panel_fill"))

    cv = Canvas(W, H)
    s = slab(cv)
    s.is_shadow_catcher = True
    A.tube(cv, rr(x0 + 2.4, y0 + 2.4, x1 - 2.4, y1 - 2.4, 5), 0.85, mat("gold"), z=depth, closed=True)
    A.tube(cv, rr(x0 + 5.6, y0 + 5.6, x1 - 5.6, y1 - 5.6, 2.5), 0.4, mat("gold_dim"), z=depth, closed=True)
    corner_curls(cv, x0, y0, x1, y1, 8.5, 7.0, mat("gold"), depth + 0.9)
    for cx, cy in ((x0 + 2.6, y0 + 2.6), (x1 - 2.6, y0 + 2.6), (x0 + 2.6, y1 - 2.6), (x1 - 2.6, y1 - 2.6)):
        A.sphere(cv, cx, cy, depth + 0.6, 1.9, mat("jade"), squash=0.7)
    cv.render(out("panel_frame"))
    record("panel", kind="box", size=[W, H], margins=[26, 26, 26, 26], pad=[pad] * 4,
           content=[14, 11, 14, 11], layers=["panel_fill.png", "panel_frame.png"])


def build_scroll():
    W, H = 300, 150
    cv = Canvas(W, H)
    sx0, sy0, sx1, sy1 = 16, 12, 284, 138
    A.slab(cv, [rr(sx0 + 0.6, sy0 + 0.6, sx1 - 0.6, sy1 - 0.6, 1.5)], 1.6, 0.6, mat("silk"))
    # gilt border and corner clouds on the silk
    A.tube(cv, rr(sx0 + 5, sy0 + 12, sx1 - 5, sy1 - 12, 1.5), 0.45, mat("gold_dim"), z=1.6, closed=True)
    corner_curls(cv, sx0 + 5, sy0 + 12, sx1 - 5, sy1 - 12, 6.5, 5.0, mat("gold"), 2.0, 0.5)
    # rollers with gold bands and jade finials
    for y in (sy0 + 1, sy1 - 1):
        A.cylinder_x(cv, 11, 289, y, 5.0, 4.4, mat("lacquer_red"))
        for bx in (14, 286):
            A.cylinder_x(cv, bx - 2.2, bx + 2.2, y, 5.0, 4.9, mat("gold"))
        for kx in (6.5, 293.5):
            A.sphere(cv, kx, y, 5.0, 5.2, mat("jade"), squash=0.9, sx=0.85)
    cv.render(out("scroll"))
    record("scroll", kind="box", size=[W, H], margins=[26, 28, 26, 28], pad=[0, 0, 0, 0],
           content=[28, 29, 26, 27], layers=["scroll.png"])


def build_buttons():
    W, H = 120, 34
    states = {
        "normal": ("lacquer", "gold_dim", "gold_dim"),
        "hover": ("lacquer_hover", "gold_bright", "jade"),
        "pressed": ("lacquer_press", "gold", "gold"),
        "disabled": ("lacquer_grey", "gold_grey", "gold_grey"),
    }
    for state, (plate, wire, gem) in states.items():
        cv = Canvas(W, H)
        d = 2.2 if state != "pressed" else 1.6
        A.slab(cv, [rr(4, 4, W - 4, H - 4, 4)], d, 1.0, mat(plate))
        A.tube(cv, rr(5.2, 5.2, W - 5.2, H - 5.2, 3.4), 0.6, mat(wire), z=d, closed=True)
        for cx in (10.5, W - 10.5):
            A.slab(cv, [lozenge(cx, H / 2, 2.6, 3.8)], 1.2, 0.4, mat(gem), z=d)
        cv.render(out("button_" + state))
    record("button", kind="box", size=[W, H], margins=[14, 11, 14, 11], pad=[3, 3, 3, 3],
           content=[18, 6, 18, 6], layers=["button_normal.png"],
           states={s: "button_%s.png" % s for s in states})


def build_toast():
    W, H = 240, 36
    cv = Canvas(W, H)
    poly = [(16, 8), (234, 8), (225, 18), (234, 28), (16, 28), (6, 18)]
    A.slab(cv, [poly], 2.0, 0.8, mat("lacquer"))
    A.tube(cv, [(15, 10.2), (229, 10.2)], 0.5, mat("gold"), z=2.0)
    A.tube(cv, [(15, 25.8), (229, 25.8)], 0.5, mat("gold"), z=2.0)
    A.tube(cv, [(16.5, 8.5), (8, 18), (16.5, 27.5)], 0.55, mat("gold"), z=2.0)
    A.sphere(cv, 15.5, 18, 2.2, 3.0, mat("jade"), squash=0.7)
    cv.render(out("toast"))
    record("toast", kind="box", size=[W, H], margins=[24, 11, 18, 11], pad=[0, 0, 0, 0],
           content=[25, 5, 22, 5], layers=["toast.png"])


def build_prompt():
    W, H = 220, 40
    cv = Canvas(W, H)
    A.slab(cv, [rr(6.8, 6.8, W - 6.8, H - 6.8, 13)], 2.4, 0.8, mat("lacquer"))
    A.tube(cv, rr(8.6, 8.6, W - 8.6, H - 8.6, 11.4), 0.7, mat("gold"), z=2.4, closed=True)
    for cx in (15, W - 15):
        A.sphere(cv, cx, H / 2, 2.4, 3.1, mat("jade"), squash=0.7)
    cv.render(out("prompt"))
    record("prompt", kind="box", size=[W, H], margins=[24, 14, 24, 14], pad=[4, 4, 4, 4],
           content=[22, 5, 22, 5], layers=["prompt.png"])


def build_chip():
    W, H = 30, 28
    cv = Canvas(W, H)
    A.slab(cv, [rr(3.4, 3.4, W - 3.4, H - 3.4, 4)], 3.4, 1.4, mat("lacquer"))
    A.tube(cv, rr(3.6, 3.6, W - 3.6, H - 3.6, 3.6), 0.55, mat("gold_dim"), z=3.4, closed=True)
    cv.render(out("chip"))
    record("chip", kind="box", size=[W, H], margins=[9, 9, 9, 9], pad=[2, 2, 2, 2],
           content=[7, 2, 7, 3], layers=["chip.png"])


def build_portrait():
    W = H = 144
    cv = Canvas(W, H)
    outer = rr(2.5, 2.5, W - 2.5, H - 2.5, 5)
    hole = list(reversed(rr(8, 8, W - 8, H - 8, 1)))
    A.slab(cv, [outer, hole], 3.0, 1.0, mat("bronze"))
    A.tube(cv, rr(5, 5, W - 5, H - 5, 3.5), 0.7, mat("gold"), z=3.0, closed=True)
    A.tube(cv, rr(8.4, 8.4, W - 8.4, H - 8.4, 1.2), 0.5, mat("gold_dim"), z=2.4, closed=True)
    corner_curls(cv, 0, 0, W, H, 10.5, 8.5, mat("gold"), 3.8, 0.75)
    for cx, cy in ((W / 2, 5), (W / 2, H - 5), (5, H / 2), (W - 5, H / 2)):
        A.slab(cv, [lozenge(cx, cy, 5, 3.2) if cy in (5, H - 5) else lozenge(cx, cy, 3.2, 5)], 1.4, 0.5, mat("jade"), z=3.0)
    cv.render(out("portrait_frame"))
    record("portrait_frame", kind="box", size=[W, H], margins=[26, 26, 26, 26], pad=[0, 0, 0, 0],
           content=[8, 8, 8, 8], layers=["portrait_frame.png"], opening=[8, 8, 128, 128])


# ------------------------------------------------------------------- gauges

def _fill(name, w, h, material):
    """A glass tube of glowing liquid: a rod with rounded ends."""
    cv = Canvas(w, h, shadow=False, key=2.6)
    r = h / 2
    A.cylinder_x(cv, r, w - r, r, 0, r, mat(material))
    for x in (r, w - r):
        A.sphere(cv, x, r, 0, r, mat(material))
    cv.render(out(name))


def trough(name, w, h, radius):
    """A recessed dark channel with an inner shadow along its top edge."""
    s = SCALE
    tw, th = int(w * s), int(h * s)
    m = A.rounded_mask(th, tw, 0, 0, tw, th, radius * s, aa=1.2)
    ys = (np.arange(th)[:, None] + 0.5) / th
    base = np.array([0.075, 0.068, 0.058])
    shade = 0.45 + 0.55 * ys  # darker toward the top (inner shadow)
    noise = A.value_noise(th, tw, max(2, th / 2), 14 * s, 11)
    rgb = base[None, None, :] * shade[..., None] * (0.8 + 0.4 * noise[..., None])
    inner = A.blur(1 - m, max(1, int(1.5 * s)))
    rgb *= (1 - 0.8 * inner[..., None])
    arr = np.concatenate([rgb, (m * 0.94)[..., None]], axis=-1)
    A.save_rgba(arr, out(name))


def glow(name, w, h, rect, radius, blur_px, ring=None):
    s = SCALE
    tw, th = int(w * s), int(h * s)
    if ring:
        cx, cy, r0, r1 = [v * s for v in ring]
        ys, xs = np.mgrid[0:th, 0:tw] + 0.5
        d = np.hypot(xs - cx, ys - cy)
        m = ((d > r0) & (d < r1)).astype(np.float32)
    else:
        x, y, rw, rh = [v * s for v in rect]
        m = A.rounded_mask(th, tw, x, y, x + rw, y + rh, radius * s)
    g = A.blur(m, int(blur_px * s / 2))
    g = g / max(g.max(), 1e-6)
    arr = np.ones((th, tw, 4), dtype=np.float32)
    arr[..., 3] = np.clip(g, 0, 1) ** 1.2
    A.save_rgba(arr, out(name))


def spark():
    s = SCALE
    tw, th = 8 * s, 16 * s
    ys, xs = np.mgrid[0:th, 0:tw] + 0.5
    d = np.hypot((xs - tw / 2) / (tw / 2), (ys - th / 2) / (th / 2))
    a = np.clip(1 - d, 0, 1) ** 1.6
    arr = np.ones((th, tw, 4), dtype=np.float32)
    arr[..., 3] = a
    A.save_rgba(arr, out("spark"))


def gauge_frame(name, glyph, medal_mat):
    W, H = 244, 32
    wx0, wy0, wx1, wy1 = 30, 11, 230, 21
    cv = Canvas(W, H)
    outer = rr(22.8, 7.8, 236.2, 24.2, 4.5)
    hole = list(reversed(rr(wx0 - 0.6, wy0 - 0.6, wx1 + 0.6, wy1 + 0.6, 4)))
    A.slab(cv, [outer, hole], 2.6, 0.8, mat("bronze"))
    A.tube(cv, rr(wx0 - 0.9, wy0 - 0.9, wx1 + 0.9, wy1 + 0.9, 4.5), 0.55, mat("gold"), z=2.6, closed=True)
    A.slab(cv, [lozenge(239.2, 16, 4.2, 6.2)], 2.6, 0.7, mat("gold"))
    A.slab(cv, [A.circle_pts(16, 16, 13.2)], 3.6, 1.4, mat(medal_mat), z=0.4)
    A.tube(cv, A.circle_pts(16, 16, 13.4, 72), 1.0, mat("gold"), z=4.0, closed=True)
    A.text(cv, glyph, HANZI, 17, 16, 16.5, mat("gold"), z=4.0, extrude=0.5, bevel=0.3)
    cv.render(out(name))


def build_gauges():
    gauge_frame("gauge_hp_frame", "血", "lacquer_red")
    gauge_frame("gauge_qi_frame", "气", "jade_dark")
    trough("trough_gauge", 200, 10, 4)
    _fill("fill_hp", 200, 10, "liquid_hp")
    _fill("fill_qi", 200, 10, "liquid_qi")
    glow("glow_gauge", 264, 52, (38, 19, 204, 14), 6, 9)
    for g in ("hp", "qi"):
        record("gauge_" + g, kind="gauge", size=[244, 32], window=[30, 11, 200, 10],
               frame="gauge_%s_frame.png" % g, trough="trough_gauge.png", fill="fill_%s.png" % g,
               glow="glow_gauge.png", glow_rect=[-10, -10, 264, 52])
    # cultivation
    W, H = 244, 14
    cv = Canvas(W, H)
    outer = rr(22.6, 2.2, 236.4, 11.8, 4.2)
    hole = list(reversed(rr(29.4, 4.0, 230.6, 10.0, 2.6)))
    A.slab(cv, [outer, hole], 2.0, 0.6, mat("bronze"))
    A.tube(cv, rr(29.2, 3.8, 230.8, 10.2, 3), 0.42, mat("gold"), z=2.0, closed=True)
    A.sphere(cv, 16, 7, 2.2, 4.4, mat("jade"), squash=0.7)
    A.tube(cv, A.circle_pts(16, 7, 4.6, 48), 0.55, mat("gold"), z=1.6, closed=True)
    A.slab(cv, [lozenge(239.5, 7, 3.4, 4.4)], 2.0, 0.6, mat("gold"))
    cv.render(out("gauge_xp_frame"))
    trough("trough_xp", 200, 5, 2.5)
    _fill("fill_xp", 200, 5, "liquid_xp")
    record("gauge_xp", kind="gauge", size=[244, 14], window=[30, 4.5, 200, 5],
           frame="gauge_xp_frame.png", trough="trough_xp.png", fill="fill_xp.png")
    # boss
    W, H = 560, 44
    wx0, wy0, wx1, wy1 = 48, 18, 512, 30
    cv = Canvas(W, H)
    outer = rr(38.8, 13.8, 521.2, 34.2, 5.5)
    hole = list(reversed(rr(wx0 - 0.6, wy0 - 0.6, wx1 + 0.6, wy1 + 0.6, 5)))
    A.slab(cv, [outer, hole], 3.0, 1.0, mat("bronze"))
    A.tube(cv, rr(wx0 - 1.0, wy0 - 1.0, wx1 + 1.0, wy1 + 1.0, 6), 0.65, mat("gold"), z=3.0, closed=True)
    for cx, mir in ((22, False), (W - 22, True)):
        A.draw_strokes(cv, A.place(A.xiangyun(), cx, 22, 15, 0, mir), 1.1, mat("gold"), 2.0)
    A.slab(cv, [lozenge(W / 2, 12, 9, 7)], 3.0, 1.0, mat("lacquer_red"), z=1.0)
    A.tube(cv, lozenge(W / 2, 12, 9.6, 7.6), 0.7, mat("gold"), z=4.0, closed=True)
    for mir in (False, True):
        A.draw_strokes(cv, A.place(A.xiangyun(), W / 2 + (-20 if not mir else 20), 10, 6.5, 0, not mir), 0.6, mat("gold"), 3.2)
    cv.render(out("boss_frame"))
    trough("trough_boss", 464, 12, 5)
    _fill("fill_boss", 464, 12, "liquid_boss")
    record("boss", kind="gauge", size=[W, H], window=[wx0, wy0, wx1 - wx0, wy1 - wy0],
           frame="boss_frame.png", trough="trough_boss.png", fill="fill_boss.png")


# ------------------------------------------------------------------- compass

def build_compass():
    W, H = 320, 44
    wx0, wy0, wx1, wy1 = 32, 9, 288, 35
    cv = Canvas(W, H)
    outer = rr(21, 4.5, 299, 39.5, 9)
    hole = list(reversed(rr(wx0 - 0.5, wy0 - 0.5, wx1 + 0.5, wy1 + 0.5, 4)))
    A.slab(cv, [outer, hole], 2.8, 1.0, mat("bronze"))
    A.tube(cv, rr(wx0 - 1.0, wy0 - 1.0, wx1 + 1.0, wy1 + 1.0, 5), 0.6, mat("gold"), z=2.8, closed=True)
    A.tube(cv, rr(22.8, 6.3, 297.2, 37.7, 7.5), 0.45, mat("gold_dim"), z=2.8, closed=True)
    for cx in (12, W - 12):
        A.sphere(cv, cx, H / 2, 2.2, 5.2, mat("jade"), squash=0.75)
        A.tube(cv, A.circle_pts(cx, H / 2, 5.6, 48), 0.7, mat("gold"), z=2.0, closed=True)
    # lubber line: a gilt pointer above and a small one below
    A.slab(cv, [[(153.5, 1.2), (166.5, 1.2), (160, 12)]], 2.2, 0.6, mat("gold"), z=2.8)
    A.slab(cv, [[(160, 34), (164.5, 42.5), (155.5, 42.5)]], 1.8, 0.5, mat("gold"), z=2.8)
    cv.render(out("compass_frame"))
    trough("trough_compass", 256, 26, 4)

    # the scrolling dial: 360 degrees over 768 px, north at both ends
    SW, SH = 768, 26
    cv = Canvas(SW, SH, key=3.0)
    ppd = SW / 360.0
    marks = {0: ("北", "N"), 90: ("东", "E"), 180: ("南", "S"), 270: ("西", "W"), 360: ("北", "N")}
    for deg, (hz, lat) in marks.items():
        x = deg * ppd
        A.text(cv, hz, HANZI, 17.5, x, 10.0, mat("gold"), z=0.5, extrude=0.4, bevel=0.3)
        A.text(cv, lat, LATIN, 7.5, x, 22.2, mat("jade_pale"), z=0.5, extrude=0.3, bevel=0.15)
    for deg in range(0, 361, 15):
        if deg % 90 == 0:
            continue
        x = deg * ppd
        if deg % 45 == 0:
            A.slab(cv, [lozenge(x, 11, 2.2, 3.4)], 1.0, 0.4, mat("jade"), z=0.3)
            A.tube(cv, [(x, 17), (x, 24)], 0.55, mat("gold"), z=0.8)
        else:
            A.tube(cv, [(x, 19), (x, 24)], 0.45, mat("gold_dim"), z=0.8)
    cv.render(out("compass_strip"))
    record("compass", kind="compass", size=[W, H], window=[wx0, wy0, wx1 - wx0, wy1 - wy0],
           frame="compass_frame.png", trough="trough_compass.png", strip="compass_strip.png",
           strip_size=[SW, SH], span_deg=120)

    cv = Canvas(20, 26)
    pin = [(10, 1.5), (18.2, 11), (10, 24.5), (1.8, 11)]
    A.slab(cv, [pin], 3.0, 1.2, mat("jade"))
    A.tube(cv, pin, 0.7, mat("gold"), z=3.0, closed=True)
    A.sphere(cv, 10, 11, 3.2, 1.8, mat("gold_bright"), squash=0.8)
    cv.render(out("marker"))
    record("marker", kind="icon", size=[20, 26])
    cv = Canvas(12, 16)
    A.tube(cv, [(3.2, 2.5), (9, 8), (3.2, 13.5)], 1.35, mat("gold"), z=1.4)
    cv.render(out("marker_edge"))
    record("marker_edge", kind="icon", size=[12, 16])


# ------------------------------------------------------------------- ring

def build_ring():
    W = H = 112
    c = W / 2
    cv = Canvas(W, H)
    ring = lambda r, seg=96: A.circle_pts(c, c, r, seg)  # noqa: E731
    A.slab(cv, [ring(52), list(reversed(ring(46)))], 3.0, 1.0, mat("bronze"))
    A.slab(cv, [ring(36.2), list(reversed(ring(31)))], 3.0, 1.0, mat("bronze"))
    A.tube(cv, ring(46.4, 128), 0.65, mat("gold"), z=3.0, closed=True)
    A.tube(cv, ring(35.8, 128), 0.65, mat("gold"), z=3.0, closed=True)
    for i in range(8):
        a = math.radians(i * 45 - 90)
        A.sphere(cv, c + 49 * math.cos(a), c + 49 * math.sin(a), 3.0, 1.7, mat("gold"), squash=0.8)
    for i in range(4):
        a = i * 90 + 45
        rad = math.radians(a)
        px, py = c + 50 * math.cos(rad), c + 50 * math.sin(rad)
        A.draw_strokes(cv, A.place(A.xiangyun(), px, py, 6.5, -a + 90 + 180, False), 0.6, mat("gold"), 3.4)
    _lotus(cv, c, c, 11, "rose_jade", "jade_pale", z=0.0)
    cv.render(out("ring_frame"))
    cv = Canvas(W, H, shadow=False, key=2.6)
    A.slab(cv, [ring(46.2), list(reversed(ring(35.8)))], 3.0, 2.2, mat("liquid_ring"), bevel_res=5)
    cv.render(out("ring_fill"))
    s = SCALE
    ys, xs = np.mgrid[0:H * s, 0:W * s] + 0.5
    d = np.hypot(xs - c * s, ys - c * s) / s
    m = np.clip(46.5 - d, 0, 1) * np.clip(d - 35.5, 0, 1)
    arr = np.zeros((H * s, W * s, 4), dtype=np.float32)
    arr[..., :3] = np.array([0.02, 0.035, 0.04])
    arr[..., 3] = m * 0.9
    A.save_rgba(arr, out("ring_under"))
    glow("glow_ring", W, H, None, 0, 10, ring=(c, c, 36, 46))
    record("ring", kind="ring", size=[W, H], frame="ring_frame.png", fill="ring_fill.png",
           under="ring_under.png", glow="glow_ring.png")


# ------------------------------------------------------------------- icons

def _lotus(cv, cx, cy, r, outer, inner, z=0.0):
    for i in range(8):
        a = i * 45
        rad = math.radians(a - 90)
        A.sphere(cv, cx + 0.55 * r * math.cos(rad), cy + 0.55 * r * math.sin(rad), z + 0.8, r * 0.45,
                 mat(outer), squash=0.35, sx=0.42, rot=math.radians(-a))
    for i in range(5):
        a = i * 72 + 36
        rad = math.radians(a - 90)
        A.sphere(cv, cx + 0.3 * r * math.cos(rad), cy + 0.3 * r * math.sin(rad), z + 1.8, r * 0.3,
                 mat(inner), squash=0.45, sx=0.5, rot=math.radians(-a))
    A.sphere(cv, cx, cy, z + 2.4, r * 0.16, mat("gold_bright"), squash=0.8)


def build_icons():
    cv = Canvas(20, 20)
    _lotus(cv, 10, 10, 9.2, "rose_jade", "jade_pale")
    cv.render(out("lotus"))
    cv = Canvas(20, 20)
    _lotus(cv, 10, 10, 9.2, "gold", "gold_bright")
    cv.render(out("lotus_done"))
    record("lotus", kind="icon", size=[20, 20])
    record("lotus_done", kind="icon", size=[20, 20])
    W, H = 300, 14
    cv = Canvas(W, H)
    n = 60
    for side in (-1, 1):
        pts = [(W / 2 + side * (12 + 128 * i / n), 7) for i in range(n + 1)]
        radii = [1.0 - 0.85 * (i / n) ** 1.3 for i in range(n + 1)]
        A.tube(cv, pts, 0.75, mat("gold"), z=0.6, radii=radii)
        A.draw_strokes(cv, A.place(A.xiangyun(), W / 2 + side * 20, 7.5, 4.2, 0, side < 0), 0.4, mat("gold"), 1.4)
    A.slab(cv, [lozenge(W / 2, 7, 5, 5.5)], 2.0, 0.7, mat("jade"))
    A.tube(cv, lozenge(W / 2, 7, 5.6, 6.1), 0.5, mat("gold"), z=2.0, closed=True)
    cv.render(out("divider"))
    record("divider", kind="icon", size=[W, H])


# ------------------------------------------------------------------- banner

def build_banner():
    W, H = 720, 110
    s = SCALE
    tw, th = W * s, H * s
    ys, xs = np.mgrid[0:th, 0:tw].astype(np.float32) + 0.5
    u = xs / tw
    # brush pressure: fast attack at the left, long dry lift to the right
    env = np.clip(u / 0.08, 0, 1) ** 0.6 * np.clip((1 - u) / 0.3, 0, 1) ** 0.8
    wob = (A.value_noise(1, tw, 1, 60 * s, 3)[0] - 0.5) * 8 * s
    centre = th * 0.5 + wob[None, :]
    half = (20 + 16 * env) * s
    edge_n = (A.value_noise(th, tw, 3 * s, 5 * s, 5) - 0.5) * 6 * s
    d = np.abs(ys - centre) - half - edge_n
    body = np.clip(0.5 - d / (1.5 * s), 0, 1)
    streak = A.value_noise(th, tw, 1.2 * s, 90 * s, 9)
    dry = np.clip((streak - (0.72 - 0.55 * env)) * 4.0, 0, 1)
    alpha = body * (0.25 + 0.75 * dry) * np.clip(env * 1.6, 0, 1)
    alpha = A.blur(alpha, 1) * 0.9
    tone = A.value_noise(th, tw, 20 * s, 40 * s, 13)
    rgb = np.stack([0.015 + 0.02 * tone, 0.03 + 0.03 * tone, 0.035 + 0.03 * tone], axis=-1)
    brush = np.concatenate([rgb, alpha[..., None]], axis=-1)

    cv = Canvas(W, H, shadow=False)
    n = 80
    for y, span in ((17, 250), (93, 210)):
        for side in (-1, 1):
            pts = [(W / 2 + side * span * i / n, y) for i in range(n + 1)]
            radii = [1.0 - 0.8 * (i / n) ** 1.5 for i in range(n + 1)]
            A.tube(cv, pts, 0.9, mat("gold"), z=0.5, radii=radii)
        A.slab(cv, [lozenge(W / 2, y, 6, 4.5)], 2.0, 0.7, mat("jade"), z=0.5)
    for side in (-1, 1):
        A.draw_strokes(cv, A.place(A.xiangyun(), W / 2 + side * 262, 17, 9, 0, side < 0), 0.8, mat("gold"), 0.5)
        A.draw_strokes(cv, A.place(A.xiangyun(), W / 2 + side * 222, 93, 8, 180, side > 0), 0.75, mat("gold"), 0.5)
    tmp = out("_banner_gold")
    cv.render(tmp)
    gold = A.load_rgba(tmp)
    os.remove(tmp)
    A.save_rgba(A.over(gold, brush), out("banner"))
    record("banner", kind="icon", size=[W, H])


BUILDERS = {
    "panel": build_panel, "scroll": build_scroll, "buttons": build_buttons, "toast": build_toast,
    "prompt": build_prompt, "chip": build_chip, "portrait": build_portrait, "gauges": build_gauges,
    "spark": spark, "compass": build_compass, "ring": build_ring, "icons": build_icons,
    "banner": build_banner,
}


def main():
    global OUT, SAMPLES
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "godot", "ui", "hud"))
    ap.add_argument("--only", default="", help="comma list of: " + ",".join(BUILDERS))
    ap.add_argument("--samples", type=int, default=48)
    args = ap.parse_args(argv)
    OUT = os.path.abspath(args.out)
    SAMPLES = args.samples
    os.makedirs(OUT, exist_ok=True)
    A.setup_render(samples=SAMPLES)
    only = {s for s in args.only.split(",") if s}
    kit_path = os.path.join(OUT, "hud_kit.json")
    if only and os.path.exists(kit_path):
        with open(kit_path) as f:
            KIT["items"].update(json.load(f).get("items", {}))
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        fn()
    if "spark" in KIT["items"] or not only or "spark" in only:
        record("spark", kind="icon", size=[8, 16])
    with open(kit_path, "w") as f:
        json.dump({"scale": SCALE, "items": dict(sorted(KIT["items"].items()))}, f, indent=1)
        f.write("\n")
    print("wrote", kit_path)


if __name__ == "__main__":
    main()
