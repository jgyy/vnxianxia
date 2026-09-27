"""Hairstyles: each cfg["hair_style"] as a recipe of groomed layers.

Layers (all built from hair_groom primitives and emitted as hair_cards bundles):
  loose     - hair falling from a scalp region: guides are combed along a flow field,
              draped by the solver, then interpolated into clumped children and cut to
              a layered hem line (longest at the back, face-framing pieces shorter).
  gathered  - scalp hair pulled tight to a tie (topknot, half-up, ponytail, nape bun),
              with soft volume at the crown and a slightly flattened band at the tie.
  bun       - strands coiled around the knot.
  tail      - a ponytail / half-up tail hanging from the tie, draped on head and back.
  bangs     - see-through fringe: sparse wispy cards from a narrow hairline band.
  locks     - face-framing side locks (skinned head -> chest so they rest on the robe).
  flyaways  - thin single strands lifted off the surface (candid photos always have them).
  beard     - moustache and chin beard cards (elders / bandit), own material.

Styles (xianxia, informed by K-drama / C-drama costume hair and modern Korean cuts):
  topknot   male hero / disciples: everything combed up into a crown knot under a
            guan, a long high tail from beneath it, loose face-framing strands and a
            few comma-shaped fringe wisps.
  buns      heroines: long flowing half-up - the crown half gathered into a small
            twisted knot with buyao hairpins and two thin braids from the temples, the
            rest loose to the waist, see-through bangs and layered side locks.
  crown     sect master: formal updo in a tall bun under a phoenix crown, lower hair
            loose and long.
  disciple  outer-sect disciple: topknot in a cloth wrap, short tail.
  elder     grey topknot with a small guan; long beard and moustache cards.
  hat       villager: short hair tied in a small knot under a douli.
  scarf     villager woman: hair drawn back to a nape bun and a plait under a scarf.
  ponytail  bandit: messy high ponytail, frizz and flyaways, headband.
  loose     demon cultivator / blood patriarch: long loose centre-parted hair.
"""
import math
import zlib

import numpy as np

from . import hair_cards, hair_groom as G, hair_props, util

PI = math.pi


class Groom:
    """Accumulates the card bundles and accessory parts of one character."""

    def __init__(self, cfg, mats, head, body, s, budget=1.0, seed=7):
        self.cfg, self.mats, self.head, self.body, self.s = cfg, mats, head, body, s
        self.budget = budget
        self.rng = np.random.default_rng(seed)
        self.bundles = []
        self.beard_bundles = []
        self.parts = []
        self.frizz = cfg.get("frizz", 0.25)

    def n(self, k):
        return max(6, int(k * self.budget))

    # ------------------------------------------------------------------
    # flow fields
    # ------------------------------------------------------------------
    def flow_down(self, part_x=0.0, back=0.55, out=0.75, spread=0.15):
        """Loose hair: away from the parting line, backward and down."""
        c = self.head.c

        def f(p, lon, lat):
            sx = np.sign(p[..., 0] - c[0] - part_x * self.s)
            sx = np.where(sx == 0, 1.0, sx)
            top = G.smooth((lat + 0.1) / 0.5)          # sideways only while over the crown
            side = sx * (out * top + spread * (1 - top))
            # roots in front of the ears are combed back first so nothing hangs over the face
            front = np.clip(np.cos(lon), 0, 1) * top
            v = np.stack([side, back + 0.4 * (1 - top) + 1.8 * front, -np.ones_like(sx)], -1)
            return v.astype(np.float32)
        return f

    def flow_to(self, target):
        target = np.asarray(target, np.float32)
        return lambda p, lon, lat: target - p

    # ------------------------------------------------------------------
    # layer builders
    # ------------------------------------------------------------------
    def _points(self, L, seg=0.07, lo=4, hi=9):
        return int(np.clip(round(float(np.max(L)) / seg), lo, hi))

    def loose(self, count, lon_range, lat_range, length, flow, strips=("dense", "dense2", "medium"),
              width=0.022, hem=None, kind="free", clump=0.45, layer=(0.004, 0.02), accept=None,
              gravity=0.004, stiff_root=0.55, n_guides=None, root_lift=0.35, v0=0.0):
        """Loose hair from a scalp window. hem(lon_root, P) -> per-strand z of the cut."""
        s, rng, head = self.s, self.rng, self.head
        count = self.n(count)
        ng = n_guides or max(24, count // 6)
        glon, glat = head.sample(rng, ng, lon_range, lat_range, accept)
        if len(glon) == 0:
            return None
        L = np.full(len(glon), length * s, np.float32) * rng.uniform(0.95, 1.05, len(glon))
        lay = rng.uniform(layer[0], layer[1], len(glon)).astype(np.float32) * s
        g = G.comb(head, glon, glat, L, flow, n_pts=24, layer=lay, root_lift=root_lift)
        g = G.relax(g, head, self.body, gravity=gravity * s, stiff_root=stiff_root)
        clon, clat = head.sample(rng, count, lon_range, lat_range, accept)
        croots = head.point(clon, clat, 0.003 * s)
        P = G.children(g, g[:, 0], croots, rng, clump=clump, frizz=self.frizz, head=head, body=self.body,
                       head_off=0.004 * s)
        keep = None
        if hem is not None:
            keep = self._cut(P, hem(clon, P))
        M = self._points(G.lengths(P) * (1 if keep is None else keep))
        P = G.resample(P, M, keep)
        self._emit(P, strips, width, kind, v0=v0)
        return P

    def _cut(self, P, zcut):
        """Arc-length fraction of each strand above its hem height zcut (S,)."""
        z = P[..., 2]
        below = z < zcut[:, None]
        first = np.where(below.any(1), below.argmax(1), P.shape[1] - 1)
        seg = np.linalg.norm(np.diff(P, axis=1), axis=2)
        cum = np.concatenate([np.zeros((len(P), 1)), np.cumsum(seg, 1)], 1)
        return np.clip(cum[np.arange(len(P)), first] / np.maximum(cum[:, -1], 1e-6), 0.15, 1.0)

    def _emit(self, P, strips, width, kind, beard=False, tip=0.55, root=0.8, twist=0.35, axis=None, v0=0.0):
        C = len(P)
        if isinstance(strips, np.ndarray):
            choice = strips                                   # already one strip name per card
        else:
            choice = self.rng.choice(list(strips), C) if not isinstance(strips, str) else strips
        w = width * self.s * self.rng.uniform(0.75, 1.2, C)
        b = hair_cards.Bundle(P, w, choice, kind, tip=tip, root=root, twist=twist, axis=axis, v0=v0)
        (self.beard_bundles if beard else self.bundles).append(b)
        return b

    def gathered(self, count, lon_range, lat_range, tie, bulge=0.012, width=0.018, accept=None,
                 strips=("dense", "dense2", "medium"), tie_radius=0.012, margin=0.0, sections=28, groove=0.35):
        s, rng, head = self.s, self.rng, self.head
        lon, lat = head.sample(rng, self.n(count), lon_range, lat_range, accept, hairline_margin=margin)
        P = G.gather(head, lon, lat, tie, rng, n_pts=16, bulge=bulge * s, tight=0.004 * s,
                     tie_radius=tie_radius * s)
        P = self._comb_sections(P, lon, sections, groove)
        P = G.resample(P, self._points(G.lengths(P), 0.04, 4, 6))
        # sparse, wispy cards along the hairline so it fades in instead of ending in a hard edge
        edge = np.sin(lat) - head.hairline(np.abs(lon)) < 0.07
        names = np.where(edge, rng.choice(["wisp", "wisp2", "medium2"], len(lon)), rng.choice(list(strips), len(lon)))
        self._emit(P, names, width, "head", tip=0.8, twist=0.2)
        return P

    def _comb_sections(self, P, lon, sections, groove=0.35):
        """Combed-back hair gathers into sections with shallow grooves between them.

        Cards are binned by root longitude (with jitter so the partings wander); each is
        pulled toward its section's mean path, most strongly mid-way to the tie.
        """
        if sections <= 1 or len(P) < sections:
            return P
        key = (lon + math.pi) / (2 * math.pi) * sections + self.rng.normal(0, 0.25, len(lon))
        sec = np.floor(key).astype(int) % sections
        t = np.linspace(0, 1, P.shape[1], dtype=np.float32)[None, :, None]
        pull = groove * np.clip(np.sin(np.pi * t), 0, 1) ** 1.5
        out = P.copy()
        for k in range(sections):
            m = sec == k
            if m.sum() < 2:
                continue
            mean = P[m].mean(0)
            out[m] = P[m] + (mean[None] - P[m]) * pull[0]
        out[:, 1:] = self.head.push(out[:, 1:], 0.003 * self.s)
        return out

    def bun(self, count, centre, axis, radius, height, turns=1.3, width=0.016, strips=("medium", "tip")):
        s = self.s
        P = G.coil(centre, axis, radius * s, height * s, turns, self.n(count), 16, self.rng)
        P = G.resample(P, 8)
        self._emit(P, strips, width, "head", tip=0.6, root=0.7, twist=0.25, axis=np.repeat(
            np.asarray(centre, np.float32)[None], 8, 0))
        return P

    def tail(self, count, tie, direction, length, spread=0.012, width=0.02, strips=("dense2", "medium", "tip"),
             clump=0.6, gravity=0.004, stiff_root=0.7, fan=0.25):
        s, rng, head = self.s, self.rng, self.head
        tie = np.asarray(tie, np.float32)
        ng = max(20, self.n(count) // 6)
        off = G.norm(rng.normal(0, 1, (ng, 3)).astype(np.float32)) * spread * s * np.sqrt(rng.random((ng, 1)))
        d = G.norm(np.asarray(direction, np.float32)[None] + off / (spread * s) * fan)
        L = length * s * rng.uniform(0.8, 1.05, ng).astype(np.float32)
        g = G.hang(tie + off, d, L, n_pts=24)
        g = G.relax(g, head, self.body, gravity=gravity * s, stiff_root=stiff_root, head_off=0.012 * s)
        C = self.n(count)
        coff = G.norm(rng.normal(0, 1, (C, 3)).astype(np.float32)) * spread * s * np.sqrt(rng.random((C, 1)))
        P = G.children(g, g[:, 0], tie + coff, rng, clump=clump, frizz=self.frizz, head=head, body=self.body,
                       head_off=0.01 * s)
        keep = rng.uniform(0.75, 1.0, C)          # uneven, tapering ends
        P = G.resample(P, self._points(G.lengths(P) * keep, 0.07, 5, 9), keep)
        self._emit(P, strips, width, "free", tip=0.45, twist=0.5, axis=P.mean(0))
        return P

    def bangs(self, count, lon_half=0.42, length=0.085, width=0.012, strips=("wisp", "wisp2", "tip"),
              sweep=0.0, depth=0.1, brow_lat=0.2, curtain=0.012):
        """See-through fringe: sparse wispy clumps from a narrow band behind the front hairline.

        The hem is cut just above the brows with ragged, pointed ends; with `curtain` the
        pieces at the sides fall a little longer (curtain bangs framing the eyes).
        """
        s, head, rng = self.s, self.head, self.rng
        z_front = float(head.hairline(np.float32(0.0)))

        def accept(lon, lat):
            return np.sin(lat) < head.hairline(np.abs(lon)) + depth

        def hem(lon, P):
            brow = head.point(lon, np.full_like(lon, brow_lat))[:, 2]
            side = G.smooth(np.abs(lon) / lon_half)
            return brow + (rng.uniform(0.0, 0.012, len(lon)) - curtain * side) * s
        lon_range = (-lon_half, lon_half)
        lat_range = (math.asin(max(-1, z_front - 0.02)), math.asin(min(1, z_front + depth + 0.05)))
        forward = np.array([sweep, -0.3, -1.0], np.float32)
        flow = lambda p, lon, lat: np.broadcast_to(forward, p.shape).astype(np.float32)
        return self.loose(count, lon_range, lat_range, length, flow, strips, width, hem=hem, kind="head",
                          clump=0.65, layer=(0.002, 0.006), accept=accept, gravity=0.002, stiff_root=0.35,
                          root_lift=0.45, n_guides=max(12, self.n(count) // 3),
                          v0=0.3)   # short fringe cards use the tapered end of the strip

    def locks(self, count, length, lon=(0.9, 1.25), lat=(0.05, 0.5), width=0.014,
              strips=("medium2", "wisp", "tip")):
        """Face-framing side locks falling in front of the ears onto the chest."""
        for side in (1, -1):
            lr = (lon[0], lon[1]) if side > 0 else (-lon[1], -lon[0])
            flow = lambda p, lo, la, sd=side: np.broadcast_to(
                np.array([sd * 0.3, -0.1, -1.0], np.float32), p.shape).astype(np.float32)
            self.loose(count // 2, lr, lat, length, flow, strips, width, kind="side", clump=0.6,
                       layer=(0.004, 0.012), gravity=0.004, stiff_root=0.45)

    def plait(self, start, direction, length, width=0.03, crossings=9, cards=4):
        """A hanging three-strand braid: one draped guide, plaited locks around it."""
        s, head = self.s, self.head
        g = G.hang(np.asarray(start, np.float32)[None], np.asarray(direction, np.float32)[None],
                   np.array([length * s], np.float32), n_pts=24)
        g = G.relax(g, head, self.body, gravity=0.005 * s, stiff_root=0.6, head_off=0.012 * s, body_off=0.02 * s)
        axis = G.resample(g, 28)[0]
        P = G.braid(axis, width * s, crossings, self.rng, cards)
        self._emit(P, ("dense2", "medium"), width * 0.55, "free", tip=0.5, root=0.9, twist=0.15, axis=axis)
        # the tail below the tie: a short loose tuft
        end = axis[-1]
        self.tail(max(8, cards * 4), end, direction, 0.08, spread=0.006, width=0.012, clump=0.5)

    def crown_braids(self, tie, lon=1.0, lat=0.35, width=0.014, crossings=11):
        """Two thin braids from the temples wrapped back over the scalp to the knot."""
        head, s = self.head, self.s
        for side in (1, -1):
            path = G.gather(head, np.array([side * lon], np.float32), np.array([lat], np.float32), tie, self.rng,
                            n_pts=24, lift=0.008 * s, bulge=0.012 * s, tight=0.008 * s, tie_radius=0.004 * s)
            axis = G.resample(path, 26)[0]
            P = G.braid(axis, width * s, crossings, self.rng, 3, taper=0.8)
            self._emit(P, ("dense2", "medium"), width * 0.6, "head", tip=0.8, root=0.9, twist=0.1, axis=axis)

    def flyaways(self, count, lift=0.012, width=0.005):
        """Stray single hairs: copies of random cards pushed off the surface and bent."""
        src = [b for b in self.bundles if b.P.shape[1] >= 5]
        if not src:
            return
        rng, s = self.rng, self.s
        out = []
        for _ in range(self.n(count)):
            b = src[rng.integers(len(src))]
            P = G.resample(b.P[rng.integers(len(b.P))][None], 6)[0]
            M = len(P)
            t = np.linspace(0, 1, M, dtype=np.float32)[:, None]
            d = G.norm(rng.normal(0, 1, 3).astype(np.float32))
            P = P + d * lift * s * t ** 1.3 * rng.uniform(0.4, 1.6) + \
                np.cumsum(rng.normal(0, 0.002 * s, (M, 3)), 0).astype(np.float32) * t
            out.append(P)
        P = self.head.push(np.stack(out), 0.004 * s)
        self._emit(P, "fly", width, "free", tip=0.8, root=1.0, twist=0.8)

    def beard(self, kind, count):
        """Moustache and chin beard (roots on the face below the nose)."""
        s, rng, head = self.s, self.rng, self.head

        def sample(n, lon_r, lat_r, accept):
            lon = rng.uniform(*lon_r, n * 4).astype(np.float32)
            lat = rng.uniform(*lat_r, n * 4).astype(np.float32)
            ok = accept(lon, lat)
            return lon[ok][:n], lat[ok][:n]

        long_ = kind == "long"
        # moustache: above the upper lip, flowing down and outward past the mouth corners
        lm_up = -0.47                                  # upper lip line in face coordinates (skin.LANDMARKS)
        lon, lat = sample(max(24, self.n(count // 3)), (-0.3, 0.3), (lm_up + 0.005, lm_up + 0.05),
                          lambda a, b: np.abs(a) > 0.03)
        flow = lambda p, lo, la: np.stack([np.sign(lo) * 1.2, np.full_like(lo, -0.3), -np.ones_like(lo)], -1)
        L = np.full(len(lon), (0.075 if long_ else 0.022) * s, np.float32) * rng.uniform(0.7, 1.1, len(lon))
        P = G.comb(head, lon, lat, L, flow, n_pts=10, layer=np.full(len(lon), 0.002 * s, np.float32),
                   root_lift=0.2)
        P = G.relax(P, head, self.body, gravity=0.0015 * s, stiff_root=0.5, head_off=0.0025 * s)
        self._emit(G.resample(P, 6), ("coarse", "tip"), 0.009 if long_ else 0.005, "head", beard=True, tip=0.5,
                   twist=0.2)
        # chin beard and jaw: skip the lower lip
        lip = lambda a, b: ~((np.abs(a) < 0.26) & (b > -0.6))
        lon, lat = sample(self.n(count), (-1.0, 1.0), (-0.95, -0.45),
                          lambda a, b: lip(a, b) & (b < -0.42 - 0.2 * a ** 2))
        down = lambda p, lo, la: np.stack([lo * 0.15, np.full_like(lo, -0.45), -np.ones_like(lo)], -1)
        base = 0.2 if long_ else 0.03
        L = (base * s * (1 - 0.5 * (np.abs(lon) / 1.0) ** 2) * rng.uniform(0.75, 1.1, len(lon))).astype(np.float32)
        P = G.comb(head, lon, lat, L, down, n_pts=16 if long_ else 8,
                   layer=np.full(len(lon), 0.003 * s, np.float32), root_lift=0.3)
        P = G.relax(P, head, self.body, gravity=0.003 * s, stiff_root=0.4, head_off=0.003 * s)
        P = G.children(P, P[:, 0], P[:, 0], rng, clump=0.5, frizz=0.6, head=head, body=self.body,
                       head_off=0.003 * s)
        self._emit(G.resample(P, 8 if long_ else 4), ("coarse", "tip"), 0.014 if long_ else 0.01, "head",
                   beard=True, tip=0.35, twist=0.3)

    # ------------------------------------------------------------------
    # tie helpers
    # ------------------------------------------------------------------
    def at(self, lon, lat, h):
        return self.head.point(np.float32(lon), np.float32(lat), h * self.s)

    def out_dir(self, lon, lat):
        return self.head.normal(np.float32(lon), np.float32(lat))


# --------------------------------------------------------------------------
# style recipes
# --------------------------------------------------------------------------
def _lower(head, below):
    return lambda lon, lat: np.sin(lat) < below


def _upper(head, above):
    return lambda lon, lat: np.sin(lat) >= above


def style_topknot(g, tail_len=0.6, guan_size=1.0, grey=False):
    """Crown knot under a guan, long high tail, face-framing strands, comma wisps."""
    s = g.s
    knot_lat = 1.2
    tie = g.at(PI, knot_lat, 0.01)
    up = G.norm(g.out_dir(PI, knot_lat) + np.array([0, 0, 0.8], np.float32))
    # front: combed straight back over the crown (volume at the crown, no parting)
    g.gathered(900, (-PI, PI), (-0.6, 1.57), tie, bulge=0.016, width=0.02, tie_radius=0.014, margin=0.02)
    # a second, looser top layer for depth
    # (it lies close and smooth: a high bulge with wispy strips stood up as stiff spikes)
    g.gathered(420, (-1.6, 1.6), (0.1, 1.5), tie, bulge=0.013, width=0.018, tie_radius=0.016,
               strips=("dense", "dense2", "medium"), sections=40, groove=0.18)
    knot = tie + up * 0.018 * s
    g.bun(220, knot, up, 0.022, 0.03, turns=1.4)
    hair_props.guan(g.parts, g.mats, knot + up * 0.006 * s, up, s, size=guan_size)
    if tail_len > 0:
        g.tail(520, tie + np.array([0, 0.012, -0.01], np.float32) * s, (0, 0.45, -1), tail_len, spread=0.018,
               width=0.024, fan=0.4)
    if not grey:
        g.locks(60, 0.3, lon=(0.82, 1.05), lat=(0.2, 0.45), width=0.012)
        g.bangs(14, lon_half=0.3, length=0.08, width=0.012, sweep=0.35, depth=0.06, curtain=0.02,
                strips=("medium2", "tip"))
    g.flyaways(60)


def style_buns(g, ornaments=True):
    """Long flowing half-up: gathered crown knot with hairpins, loose to the waist, air bangs."""
    s, head = g.s, g.head
    split = 0.28                                   # unit-sphere z dividing up / down halves
    tie = g.at(PI, 0.42, 0.012)
    back = g.out_dir(PI, 0.42)
    # lower half: loose, long, a soft U-shaped hem (face-framing sides shorter)
    hem = lambda lon, P: (0.98 + 0.16 * (np.cos(lon) + 1) * 0.5 + g.rng.uniform(-0.03, 0.04, len(lon))) * s
    g.loose(1000, (-PI, PI), (-1.2, math.asin(split)), 0.95, g.flow_down(back=0.9, out=0.45),
            hem=hem, layer=(0.004, 0.022), accept=lambda lon, lat: np.abs(lon) > 0.55, width=0.024)
    # upper half: combed back to the knot with a soft crown lift
    g.gathered(760, (-PI, PI), (math.asin(split) - 0.05, 1.57), tie, bulge=0.018, width=0.02, margin=0.01)
    g.bun(150, tie + back * 0.012 * s, back, 0.02, 0.02, turns=1.6)
    g.crown_braids(tie)
    # tail from the knot over the loose hair
    g.tail(260, tie + back * 0.01 * s, (0, 0.35, -1), 0.72, spread=0.016, width=0.022, gravity=0.005)
    g.bangs(45, lon_half=0.55, length=0.09, width=0.011, depth=0.08, strips=("wisp", "medium2", "tip"))
    g.locks(170, 0.5, lon=(0.95, 1.3), lat=(0.0, 0.45), width=0.014)
    g.flyaways(110)
    if ornaments:
        for side in (1, -1):
            hair_props.buyao(g.parts, g.mats, tie + np.array([side * 0.04, -0.01, 0.02], np.float32) * s, side, s,
                             blossom=side > 0)


def style_crown(g):
    """Formal updo: tall bun under a phoenix crown, lower hair loose and long."""
    s = g.s
    tie = g.at(PI, 1.25, 0.012)
    up = G.norm(g.out_dir(PI, 1.25) + np.array([0, 0, 1.0], np.float32))
    g.gathered(800, (-PI, PI), (math.asin(0.2), 1.57), tie, bulge=0.018, width=0.02, margin=0.01)
    g.bun(260, tie + up * 0.03 * s, up, 0.028, 0.06, turns=1.8)
    hem = lambda lon, P: (1.02 + 0.12 * (np.cos(lon) + 1) * 0.5) * s
    g.loose(700, (-PI, PI), (-1.2, math.asin(0.24)), 0.9, g.flow_down(back=1.0, out=0.4), hem=hem,
            accept=lambda lon, lat: np.abs(lon) > 0.6)
    g.locks(80, 0.36, lon=(0.75, 1.1), lat=(0.0, 0.3), width=0.012)
    hair_props.phoenix_crown(g.parts, g.mats, tie + up * 0.035 * s, s)
    hair_props.hairstick(g.parts, g.mats, tie + up * 0.03 * s, s)
    g.flyaways(50)


def style_disciple(g):
    """Outer-sect disciple: plain topknot wrapped in a cloth band, short tail, no guan."""
    s = g.s
    tie = g.at(PI, 1.2, 0.01)
    up = G.norm(g.out_dir(PI, 1.2) + np.array([0, 0, 0.8], np.float32))
    g.gathered(800, (-PI, PI), (-0.6, 1.57), tie, bulge=0.014, width=0.02, tie_radius=0.014, margin=0.02)
    knot = tie + up * 0.016 * s
    g.bun(160, knot, up, 0.02, 0.026, turns=1.3)
    hair_props.knot_wrap(g.parts, g.mats, knot, up, s)
    g.tail(260, tie + np.array([0, 0.012, -0.01], np.float32) * s, (0, 0.5, -1), 0.28, spread=0.014, width=0.02)
    g.locks(40, 0.2, lon=(0.85, 1.05), lat=(0.2, 0.42), width=0.011)
    g.flyaways(40)


def style_elder(g):
    style_topknot(g, tail_len=0.0, guan_size=0.85, grey=True)
    g.beard("long", 260)


def style_hat(g):
    """Short hair gathered into a small knot under a douli; nape wisps."""
    s = g.s
    tie = g.at(PI, 1.2, 0.008)
    g.gathered(420, (-PI, PI), (-0.6, 1.57), tie, bulge=0.008, width=0.02, margin=0.02)
    up = G.norm(g.out_dir(PI, 1.2) + np.array([0, 0, 0.8], np.float32))
    g.bun(80, tie + up * 0.012 * s, up, 0.016, 0.02)
    hem = lambda lon, P: np.full(len(lon), 1.5 * s)
    g.loose(120, (1.9, 4.4), (-1.0, -0.2), 0.12, g.flow_down(back=0.3, out=0.2), hem=hem,
            strips=("medium2", "wisp"), width=0.014)
    hair_props.douli(g.parts, g.mats, g.head, s)


def style_scarf(g):
    """Centre-parted hair drawn back to a low nape bun; the rest hidden by the scarf."""
    s = g.s
    tie = g.at(PI, -0.35, 0.012)
    back = g.out_dir(PI, -0.35)
    g.gathered(380, (-PI, PI), (-1.0, 0.7), tie, bulge=0.01, width=0.018, margin=0.01)
    g.bun(110, tie + back * 0.015 * s, back, 0.022, 0.025, turns=1.5)
    g.plait(tie + back * 0.01 * s + np.array([0, 0, -0.02], np.float32) * s, (0, 0.25, -1), 0.42, width=0.032)
    cap = hair_cards.scalp_cap(g.head, g.mats["scarf"], lift=0.013 * s, margin=0.0,
                               lo=lambda lon: 0.28 if abs(lon) < 1.3 else -0.3, name="Scarf")
    util.solidify(cap, 0.004 * s, offset=1.0)
    g.parts.append(("head", cap))
    hair_props.scarf_knot(g.parts, g.mats, g.head, s)


def style_ponytail(g):
    """Bandit: messy high ponytail, frizz, lots of flyaways, headband."""
    s = g.s
    g.frizz = 0.8
    tie = g.at(PI, 0.8, 0.012)
    back = g.out_dir(PI, 0.8)
    g.gathered(700, (-PI, PI), (-0.6, 1.57), tie, bulge=0.02, width=0.02, tie_radius=0.016, margin=0.015,
               strips=("dense2", "medium", "medium2"))
    g.tail(380, tie + back * 0.01 * s, (0, 0.8, -0.7), 0.34, spread=0.02, width=0.022, clump=0.75, fan=0.5)
    g.locks(40, 0.16, lon=(0.55, 0.85), lat=(0.3, 0.5), width=0.012, strips=("wisp", "tip"))
    g.flyaways(160, lift=0.02)
    hair_props.headband(g.parts, g.mats, g.head, s)


def style_loose(g):
    """Long loose centre-parted hair to the waist with face-framing front pieces."""
    s = g.s
    hem = lambda lon, P: (0.9 + 0.2 * (np.cos(lon) + 1) * 0.5 + g.rng.uniform(-0.04, 0.05, len(lon))) * s
    g.loose(1200, (-PI, PI), (-1.2, 1.57), 1.05, g.flow_down(back=0.7, out=0.9), hem=hem,
            accept=lambda lon, lat: (np.abs(lon) > 0.7) | (np.sin(lat) > 0.6), layer=(0.004, 0.026),
            width=0.024)
    g.locks(160, 0.62, lon=(0.45, 0.95), lat=(0.3, 0.75), width=0.016)
    g.flyaways(100)
    if g.cfg.get("horns"):
        hair_props.horns(g.parts, g.mats, g.head, s)


STYLES = {
    "topknot": style_topknot, "disciple": style_disciple, "buns": style_buns, "crown": style_crown, "elder": style_elder,
    "hat": style_hat, "scarf": style_scarf, "ponytail": style_ponytail, "loose": style_loose,
}


def build(cfg, mats, head, body, s, layout, budget=1.0):
    """Groom a character. Returns [(weight kind, object)] plus the card objects' weights.

    The card meshes carry their own vertex groups (per-vertex skinning computed here);
    the accessory parts are returned with a kind for characters.assign.
    """
    g = Groom(cfg, mats, head, body, s, budget, seed=zlib.crc32(cfg["name"].encode()) % 10000)
    style = cfg.get("hair_style", "buns" if cfg["female"] else "topknot")
    if style == "buns":
        STYLES[style](g, ornaments=cfg.get("ornaments", True))
    else:
        STYLES[style](g)
    if cfg.get("beard") and style != "elder":
        g.beard(cfg["beard"], 160)
    cards = []
    for bundles, mat, name in ((g.bundles, mats["hair"], "HairCards"), (g.beard_bundles, mats["beard"], "BeardCards")):
        if not bundles:
            continue
        obj, kinds, V = hair_cards.card_mesh(bundles, head, layout, g.rng, name, mat)
        hair_cards.assign_weights(obj, hair_cards.hair_weights(V, kinds, s, head.c))
        cards.append(obj)
    return g.parts, cards
