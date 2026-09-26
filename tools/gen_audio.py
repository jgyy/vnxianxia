#!/usr/bin/env python3
"""Procedural music & sound-effect generator for the xianxia action-RPG.

Everything is synthesised from scratch (no samples): modal plucked strings
(guzheng / guqin / pipa), breathy flutes (dizi / xiao), a bowed erhu, formant
choirs, taiko & small percussion, gongs, cymbals and bianzhong-style bells,
then mixed on a *cyclic* timeline (notes, echoes and the convolution reverb all
wrap around the loop point, so every music loop is seamless by construction),
mastered (K-weighted loudness normalisation + look-ahead limiter) and written
as Ogg Vorbis.

Melodies are written in jianpu (Chinese numbered notation, see `jp`) on
pentatonic modes (gong / shang / jue / zhi / yu).  All randomness is seeded from
string keys, so the decoded audio is bit-for-bit identical on every run (only the
random Ogg stream serial number in the file header differs).

Usage:
    python tools/gen_audio.py [--only title,sword_hit] [--out godot/audio]
                              [--jobs 4] [--verbose]

Dependencies: numpy, scipy, soundfile (libsndfile >= 1.0.29 with Vorbis).
Outputs: <out>/music/<id>.ogg (stereo, looped unless noted), <out>/sfx/<id>.ogg
(mono).  See docs/AUDIO.md for a description of every cue.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100
TAU = 2.0 * np.pi
MUSIC_QUALITY = 0.66   # soundfile compression_level (0 = best quality, 1 = smallest)
SFX_QUALITY = 0.25

# =============================================================================
# Utilities
# =============================================================================


def ns(sec: float) -> int:
    """Seconds -> samples."""
    return int(round(sec * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def hz(m):
    """MIDI note number(s) -> frequency in Hz."""
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def dbg(db: float) -> float:
    return 10.0 ** (db / 20.0)


def rng(*key) -> np.random.Generator:
    """Deterministic generator seeded from an arbitrary (repr-able) key."""
    return np.random.default_rng(zlib.crc32(repr(key).encode()))


def decay(n: int, t60: float) -> np.ndarray:
    """Exponential decay reaching -60 dB after t60 seconds."""
    return np.exp(-6.9078 * np.arange(n) / (max(t60, 1e-4) * SR))


def ramp(n: int, sec: float) -> np.ndarray:
    """Raised-cosine fade-in over `sec`, then 1."""
    e = np.ones(n)
    k = min(n, max(1, ns(sec)))
    e[:k] = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    return e


def fade_out(x: np.ndarray, sec: float) -> np.ndarray:
    x = np.array(x, dtype=float)
    k = min(x.shape[-1], max(1, ns(sec)))
    x[..., -k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(k) / k)
    return x


def hump(n: int, a: float, r: float) -> np.ndarray:
    """Attack/release envelope (raised cosine ends) filling n samples."""
    return ramp(n, a) * ramp(n, r)[::-1]


def norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return x * (peak / m) if m > 0 else x


def smooth(x: np.ndarray, tau: float) -> np.ndarray:
    """One-pole low-pass (time constant tau seconds), initialised at x[0]."""
    a = math.exp(-1.0 / max(tau * SR, 1.0))
    y, _ = signal.lfilter([1 - a], [1, -a], x, zi=[a * x[0]])
    return y


def lfo_noise(n: int, rate: float, r: np.random.Generator) -> np.ndarray:
    """Smooth random control curve with roughly unit standard deviation."""
    k = max(4, int(n / SR * rate) + 4)
    y = np.interp(np.arange(n), np.linspace(0, n, k), r.standard_normal(k))
    y = smooth(y, 0.25 / rate)
    s = y.std()
    return y / s if s > 0 else y


def periodic_noise(n: int, r: np.random.Generator, lo=20.0, hi=20000.0, tilt=0.0) -> np.ndarray:
    """Noise that loops perfectly after n samples, band-limited in the FFT domain.
    tilt: spectral slope in dB/octave (e.g. -3 for pink, -6 for brown)."""
    X = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    g = ((f >= lo) & (f <= hi)).astype(float)
    g[1:] *= (f[1:] / 1000.0) ** (tilt / 6.02)
    y = np.fft.irfft(X * g, n)
    return y / (y.std() + 1e-12)


def periodic_lfo(n: int, r: np.random.Generator, cycles=(1, 2, 3, 5)) -> np.ndarray:
    """Slow modulation made of whole cycles over n samples (loops seamlessly)."""
    t = np.arange(n) / n
    y = sum(r.uniform(0.4, 1.0) / c * np.sin(TAU * c * t + r.uniform(0, TAU)) for c in cycles)
    return y / (np.max(np.abs(y)) + 1e-12)


def cyc(fn, x: np.ndarray, pad: int) -> np.ndarray:
    """Run a causal process on a looping signal so its state wraps around the seam."""
    pad = min(pad, x.shape[-1])
    y = fn(np.concatenate([x[..., -pad:], x], axis=-1))
    return y[..., pad:]


def pan_gains(p: float):
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return math.cos(th), math.sin(th)


# =============================================================================
# Filters
# =============================================================================


def biquad(kind: str, f0: float, q: float = 0.7071, gain_db: float = 0.0):
    """RBJ-cookbook biquad coefficients (b, a)."""
    f0 = float(np.clip(f0, 5.0, SR * 0.47))
    w = TAU * f0 / SR
    cw, sw = math.cos(w), math.sin(w)
    al = sw / (2 * q)
    A = 10 ** (gain_db / 40)
    if kind == 'lp':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'hp':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'bp':
        b = [al, 0.0, -al]; a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'peak':
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind in ('lowshelf', 'highshelf'):
        s = 1 if kind == 'lowshelf' else -1
        sq = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) - s * (A - 1) * cw + sq), s * 2 * A * ((A - 1) - s * (A + 1) * cw),
             A * ((A + 1) - s * (A - 1) * cw - sq)]
        a = [(A + 1) + s * (A - 1) * cw + sq, -s * 2 * ((A - 1) + s * (A + 1) * cw),
             (A + 1) + s * (A - 1) * cw - sq]
    else:
        raise ValueError(kind)
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return b, a


def filt(x, kind, f0, q=0.7071, gain_db=0.0):
    b, a = biquad(kind, f0, q, gain_db)
    return signal.lfilter(b, a, x, axis=-1)


def lp(x, f, order=2):
    sos = signal.butter(order, min(f, SR * 0.45), 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def hp(x, f, order=2):
    sos = signal.butter(order, f, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, min(hi, SR * 0.45)], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def sweep(x: np.ndarray, kind: str, fcurve, q: float = 0.7071, block: int = 256) -> np.ndarray:
    """Time-varying biquad (coefficients updated every `block` samples)."""
    fcurve = np.broadcast_to(np.asarray(fcurve, dtype=float), x.shape)
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        b, a = biquad(kind, fcurve[min(i + block // 2, len(x) - 1)], q)
        y[i:i + block], zi = signal.lfilter(b, a, x[i:i + block], zi=zi)
    return y


def flanger(x: np.ndarray, rate=0.4, depth=0.004, base=0.001, mix=0.7) -> np.ndarray:
    n = len(x)
    d = (base + depth * (0.5 - 0.5 * np.cos(TAU * rate * tvec(n)))) * SR
    idx = np.arange(n) - d
    return x + mix * np.interp(idx, np.arange(n), x, left=0.0)


# =============================================================================
# Oscillators and noise bands
# =============================================================================


def phase(f: np.ndarray) -> np.ndarray:
    """Per-sample frequency (Hz) -> running phase in cycles."""
    return np.cumsum(f) / SR


def saw(f: np.ndarray, ph0: float = 0.0) -> np.ndarray:
    """PolyBLEP band-limited sawtooth for a per-sample frequency curve."""
    dt = np.clip(f / SR, 1e-7, 0.45)
    p = (ph0 + np.cumsum(dt)) % 1.0
    y = 2.0 * p - 1.0
    m = p < dt
    u = p[m] / dt[m]
    y[m] -= u + u - u * u - 1.0
    m = p > 1.0 - dt
    u = (p[m] - 1.0) / dt[m]
    y[m] -= u * u + u + u + 1.0
    return y


def band_noise(n: int, bands, key, raw=None) -> np.ndarray:
    """Sum of noise bands, each with its own exponential decay.
    bands: [(lo_hz, hi_hz, t60_s, gain), ...] (white spectral density, not normalised)."""
    r = rng('bandnoise', key)
    X = np.fft.rfft(r.standard_normal(n) if raw is None else raw)
    f = np.fft.rfftfreq(n, 1 / SR)
    y = np.zeros(n)
    for lo, hi, t60, g in bands:
        b = np.fft.irfft(X * ((f >= lo) & (f < hi)), n)
        y += g * b * decay(n, t60)
    return y


# =============================================================================
# Instruments: plucked strings (modal / additive with pitch bends)
# =============================================================================

#         inharmonicity  pluck-pos  t60@C4  hf-damping  tilt  pick-noise  body resonances (Hz, dB, Q)
PLUCK = {
    'zheng': (1.0e-4, 0.13, 3.2, 0.10, 0.85, 0.10, ((190, 4, 1.2), (420, 3, 1.4), (1800, 2.5, 1.0))),
    'qin':   (2.5e-5, 0.19, 4.6, 0.22, 1.30, 0.03, ((110, 4, 1.0), (260, 3, 1.3), (900, -3, 1.0))),
    'pipa':  (5.0e-5, 0.11, 1.0, 0.30, 0.80, 0.18, ((330, 4, 1.4), (950, 3, 1.5), (2600, 3.5, 1.2))),
}
RING = {'zheng': 2.8, 'qin': 3.6, 'pipa': 0.8}
PLUCKED = set(PLUCK)


@lru_cache(maxsize=700)
def pluck(midi: float, ring: float, kind: str = 'zheng', vel: float = 0.8,
          bend: tuple = (), vib: float = 0.0, harm: bool = False) -> np.ndarray:
    """One plucked-string note.

    bend: ((t_sec, semitones), ...) press-bend / slide breakpoints after the pluck.
    vib:  rou-xian vibrato depth in semitones.  harm: fanyin (flageolet harmonic)."""
    B, pos, t60, hfd, tilt, nz, body = PLUCK[kind]
    f0 = float(hz(midi))
    n = ns(ring)
    t = tvec(n)
    r = rng('pluck', midi, kind, harm, bend)
    semis = np.zeros(n)
    if bend:
        bt, bs = zip(*bend)
        semis = smooth(np.interp(t, bt, bs), 0.02)
    if vib:
        semis = semis + vib * np.sin(TAU * 5.3 * t) * np.clip((t - 0.18) / 0.3, 0, 1)
    ratio = 2.0 ** (semis / 12)
    ph = np.cumsum(ratio) * (f0 / SR)
    t60_1 = float(np.clip(t60 * (261.6 / f0) ** 0.35, 0.3, 9.0))
    fmax = f0 * ratio.max()
    y = np.zeros(n)
    if harm:
        for k, a, d in ((1, 1.0, 1.0), (2, 0.10, 0.5), (3, 0.035, 0.3)):
            if k * fmax < 16000:
                y += a * np.sin(TAU * k * ph + r.uniform(0, TAU)) * decay(n, t60_1 * 0.75 * d)
        y *= ramp(n, 0.004)
    else:
        bright = 0.55 + 0.45 * min(vel, 1.2)
        for k in range(1, 31):
            rk = k * math.sqrt(1 + B * k * k)
            if rk * fmax > 15000:
                break
            a = abs(math.sin(math.pi * k * pos)) / k ** tilt * math.exp(-(k - 1) * 0.3 * (1.2 - bright))
            if a < 0.004:
                continue
            t60k = t60_1 / (1 + hfd * (k - 1) ** 1.3)
            m = min(n, ns(t60k * 1.1))      # stop once the partial is ~-66 dB
            y[:m] += a * np.sin(TAU * rk * ph[:m] + r.uniform(0, TAU)) * decay(m, t60k)
        y *= ramp(n, 0.0015)
        k = min(n, ns(0.03))
        click = hp(r.standard_normal(k) * np.exp(-np.arange(k) / (0.004 * SR)), 900)
        y[:k] += nz * vel * click
        if bend:   # finger-slide squeak while the pitch moves
            speed = np.abs(np.gradient(semis)) * SR
            y += 0.03 * bp(r.standard_normal(n), 1200, 3500) * np.clip(speed / 15, 0, 1)
        for fc, g, q in body:
            y = filt(y, 'peak', fc, q, g)
    return norm(fade_out(y, 0.03), vel).astype(np.float32)


# =============================================================================
# Instruments: legato voices (dizi, xiao, erhu, gehu, choir)
# =============================================================================

LEG = {  # glide s, vibrato rate Hz / depth semitones / onset s, attack s, release s, articulation dip
    'dizi':    dict(glide=0.035, vr=5.4, vd=0.17, von=0.22, att=0.035, rel=0.12, dip=0.30),
    'xiao':    dict(glide=0.06, vr=4.8, vd=0.13, von=0.30, att=0.09, rel=0.28, dip=0.45),
    'erhu':    dict(glide=0.10, vr=6.0, vd=0.30, von=0.16, att=0.06, rel=0.20, dip=0.55),
    'gehu':    dict(glide=0.02, vr=5.0, vd=0.05, von=0.40, att=0.012, rel=0.08, dip=0.15),
    'choir':   dict(glide=0.14, vr=4.8, vd=0.10, von=0.40, att=0.45, rel=0.9, dip=0.9),
    'choir_o': dict(glide=0.14, vr=4.6, vd=0.08, von=0.40, att=0.6, rel=1.2, dip=0.9),
    'stab':    dict(glide=0.02, vr=5.0, vd=0.04, von=0.50, att=0.012, rel=0.35, dip=0.0),
}
VOWEL = {  # formant (Hz, bandwidth Hz, gain)
    'a': ((800, 90, 1.0), (1150, 100, 0.55), (2800, 140, 0.12), (3500, 160, 0.06)),
    'o': ((450, 70, 1.0), (800, 90, 0.35), (2830, 120, 0.03), (3500, 130, 0.02)),
}


def formant(x: np.ndarray, vowel: str) -> np.ndarray:
    return sum(g * filt(x, 'bp', f, f / bw) for f, bw, g in VOWEL[vowel])


def legato(ev, kind: str, key) -> np.ndarray:
    """Render one continuous phrase.

    ev: [(t_s, dur_s, midi, vel, flags, grace_midi|None), ...] with t relative to
    the phrase start.  Flags: '~' deep vibrato, 's' long slide in, 'u' scoop from
    below, 'v' fall-off at the end, '>' accent.  Returns mono samples from t=0."""
    P = LEG[kind]
    r = rng('legato', kind, key)
    evs = []
    for t0, d, m, v, fl, gr in ev:   # expand grace notes (a quick upper neighbour)
        if gr is not None and d > 0.15:
            gd = min(0.075, 0.3 * d)
            evs.append((t0, gd, gr, v * 0.9, 'G'))
            evs.append((t0 + gd, d - gd, m, v, fl + 'L'))
        else:
            evs.append((t0, d, m, v, fl))
    end = evs[-1][0] + evs[-1][1]
    n = ns(end + P['rel'] + 0.05)
    t = tvec(n)

    # --- pitch curve with portamento, scoops and fall-offs
    tp, mp = [], []
    prev_end_m = None
    for i, (t0, d, m, v, fl) in enumerate(evs):
        if i == 0:
            if 'u' in fl:
                tp += [t0, t0 + min(0.12, 0.5 * d)]; mp += [m - 1.5, m]
            else:
                tp += [t0]; mp += [m]
        else:
            pd = evs[i - 1][1]
            g = 0.012 if ('G' in fl or 'G' in evs[i - 1][4]) else P['glide'] * (3.5 if 's' in fl else 1.0)
            g = min(g, 0.6 * pd, 0.6 * d)
            if 'u' in fl:
                su = min(0.12, 0.5 * d)
                tp += [t0 - 0.01, t0 + 0.003, t0 + su]; mp += [prev_end_m, m - 1.5, m]
            else:
                tp += [t0 - 0.6 * g, t0 + 0.4 * g]; mp += [prev_end_m, m]
        prev_end_m = m
        if 'v' in fl:
            fall = min(0.35, 0.4 * d)
            tp += [t0 + d - fall, t0 + d - 0.01]; mp += [m, m - 2.0]
            prev_end_m = m - 2.0
    tp.append(n / SR); mp.append(mp[-1])
    midi = smooth(np.interp(t, np.maximum.accumulate(tp), mp), 0.006)

    # --- vibrato (delayed onset per note)
    td, vd = [0.0], [0.0]
    for t0, d, m, v, fl in evs:
        dep = P['vd'] * (1.8 if '~' in fl else 1.0)
        if d > 0.3 and 'G' not in fl:
            on = min(P['von'], 0.4 * d)
            td += [t0, t0 + on, t0 + on + min(0.35, 0.4 * d), t0 + d]; vd += [0, 0, dep, dep]
        else:
            td += [t0, t0 + d]; vd += [0, 0]
    td.append(n / SR); vd.append(vd[-1])
    depth = smooth(np.interp(t, np.maximum.accumulate(td), vd), 0.04)
    rate = P['vr'] * (1 + 0.04 * lfo_noise(n, 0.7, r))
    vib = depth * np.sin(TAU * np.cumsum(rate) / SR)
    f = hz(midi + vib + 0.04 * lfo_noise(n, 1.3, r))

    # --- amplitude envelope with articulations
    ta, va = [], []
    onsets = []
    for i, (t0, d, m, v, fl) in enumerate(evs):
        acc = 1.3 if '>' in fl else 1.0
        att = P['att'] * (0.5 if '>' in fl else 1.0)
        slur = 'L' in fl or (i > 0 and 'G' in evs[i - 1][4])
        if i == 0:
            ta.append(t0); va.append(0.0); onsets.append((t0, v))
        elif not slur:
            ta.append(t0); va.append(v * P['dip']); onsets.append((t0, v))
        ta.append(t0 + min(att, 0.5 * d)); va.append(v * acc)
        if d > 0.8:
            ta.append(t0 + 0.6 * d); va.append(v * (1.08 if kind in ('erhu', 'choir', 'choir_o') else 0.98))
        ta.append(t0 + d - 0.006); va.append(v * (0.9 if d > 0.8 else 1.0))
    ta += [end + P['rel'], n / SR]; va += [0.0, 0.0]
    amp = np.clip(smooth(np.interp(t, np.maximum.accumulate(ta), va), 0.01), 0, None)

    noise = r.standard_normal(n)
    ph = np.cumsum(f) / SR
    fmean = float(np.median(f))
    if kind == 'dizi':
        b = np.clip(amp, 0, 1.3)
        y = (np.sin(TAU * ph) + 0.42 * b * np.sin(2 * TAU * ph + 0.4) + 0.2 * b * b * np.sin(3 * TAU * ph + 1.1)
             + 0.1 * b * b * np.sin(4 * TAU * ph + 0.3) + 0.05 * b ** 3 * np.sin(5 * TAU * ph))
        buzz = sum(np.sin(TAU * k * ph + k) / k for k in range(6, 17) if k * f.max() < 15000)
        y += 0.3 * b * b * buzz * (1 + 0.6 * lfo_noise(n, 80, r))       # dimo membrane buzz
        breath = 0.035 * hp(noise, 1800) + 0.09 * filt(noise, 'bp', 2 * fmean, 3.0)
        y = y * amp + breath * amp
        for t0, v in onsets:    # tongued chiff
            i0 = ns(t0); k = min(n - i0, ns(0.04))
            y[i0:i0 + k] += 0.25 * v * filt(noise[i0:i0 + k], 'bp', 2800, 1.2) * np.exp(-np.arange(k) / (0.012 * SR))
    elif kind == 'xiao':
        y = np.sin(TAU * ph) + 0.22 * np.sin(2 * TAU * ph) + 0.08 * np.sin(3 * TAU * ph) + 0.03 * np.sin(4 * TAU * ph)
        breath = 0.22 * filt(noise, 'bp', 1.5 * fmean, 1.5) + 0.035 * hp(noise, 3000)
        y = lp((y + breath * (1 + 0.3 * lfo_noise(n, 6, r))) * amp, 6000)
    elif kind in ('erhu', 'gehu'):
        jit = 1 + (0.05 if kind == 'erhu' else 0.02) * lfo_noise(n, 9, r)
        y = saw(f) * amp * jit
        y = hp(y, 180 if kind == 'erhu' else 50)
        if kind == 'erhu':
            for fc, g, q in ((480, 3, 1.2), (1050, 6, 2.0), (2400, 4, 1.6), (3800, -4, 1.0)):
                y = filt(y, 'peak', fc, q, g)
            y = lp(y, 7500) + 0.02 * hp(noise, 1500) * amp
        else:
            y = lp(filt(y, 'peak', 300, 1.0, 5), 1600) + 0.01 * lp(noise, 800) * amp
    else:  # choir voices: detuned saws through vowel formants
        vowel = 'o' if kind == 'choir_o' else 'a'
        nv = 5 if kind == 'stab' else 3
        src = np.zeros(n)
        for j in range(nv):
            det = (j - (nv - 1) / 2) * 0.09 + 0.05 * lfo_noise(n, 0.5, rng('det', key, j))
            src += saw(f * 2 ** (det / 12), ph0=j / nv)
        src = src * amp + 0.15 * noise * amp
        y = lp(formant(src, vowel), 5000)
    peak = max(v for _, _, _, v, _ in evs)
    return norm(y, peak)


# =============================================================================
# Instruments: pads, percussion, bells, gongs, textures
# =============================================================================


def pad_note(midi: float, dur: float, key, bright=1400.0, att=1.2, rel=1.8, det=0.08, warm=False) -> np.ndarray:
    """Soft sustained pad voice (detuned saws or sine-organ) with slow envelope."""
    r = rng('pad', midi, key)
    n = ns(dur + rel)
    f = float(hz(midi)) * 2 ** (0.03 * lfo_noise(n, 0.3, r) / 12)
    if warm:
        ph = np.cumsum(f) / SR
        y = np.sin(TAU * ph) + 0.3 * np.sin(2 * TAU * ph + 0.5) + 0.12 * np.sin(3 * TAU * ph + 1.0)
        y += 0.5 * np.sin(TAU * ph * 2 ** (det / 12))
    else:
        y = saw(f * 2 ** (det / 12), 0.1) + saw(f * 2 ** (-det / 12), 0.6) + 0.8 * np.sin(TAU * np.cumsum(f) / SR)
        y = lp(y, bright)
    env = ramp(n, att)
    k = ns(rel)
    env[-k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(k) / k)
    return 0.3 * y * env


@lru_cache(maxsize=48)
def taiko(size: float = 1.0, var: int = 0) -> np.ndarray:
    """Big barrel drum: pitch-swept membrane modes + skin slap + stick click."""
    r = rng('taiko', size, var)
    n = ns(0.5 + 1.1 * size)
    t = tvec(n)
    f1 = 62.0 / size * (1 + 0.03 * r.standard_normal())
    f = f1 * (1 + 1.4 * np.exp(-t / 0.028))
    ph = np.cumsum(f) / SR
    body = (np.sin(TAU * ph) * decay(n, 0.9 * size) + 0.35 * np.sin(TAU * 1.52 * ph) * decay(n, 0.4 * size)
            + 0.18 * np.sin(TAU * 2.31 * ph + 1) * decay(n, 0.2))
    noise = r.standard_normal(n)
    skin = 0.5 * lp(noise, 1200) * np.exp(-t / 0.02)
    click = 0.25 * hp(noise, 2500) * np.exp(-t / 0.003)
    y = np.tanh(1.8 * (body + skin + click))
    return norm(y * ramp(n, 0.001), 1.0).astype(np.float32)


@lru_cache(maxsize=48)
def hand_drum(pitch: float = 180.0, t60: float = 0.3, snap: float = 0.3, var: int = 0) -> np.ndarray:
    """Small drums (tanggu / bangu): short pitched membrane with a snappy attack."""
    r = rng('hdrum', pitch, t60, var)
    n = ns(t60 + 0.05)
    t = tvec(n)
    f = pitch * (1 + 0.02 * r.standard_normal()) * (1 + 0.5 * np.exp(-t / 0.012))
    ph = np.cumsum(f) / SR
    y = np.sin(TAU * ph) * decay(n, t60) + 0.4 * np.sin(TAU * 1.6 * ph) * decay(n, t60 * 0.5)
    y += snap * bp(r.standard_normal(n), 1500, 7000) * np.exp(-t / 0.012)
    return norm(y * ramp(n, 0.0008), 1.0).astype(np.float32)


@lru_cache(maxsize=48)
def woodblock(f0: float = 1100.0, var: int = 0, t60: float = 0.08) -> np.ndarray:
    """Woodblock / muyu (temple wood-fish): damped inharmonic modes plus a click."""
    r = rng('wood', f0, var)
    n = ns(t60 * 1.5 + 0.02)
    t = tvec(n)
    f = f0 * (1 + 0.015 * r.standard_normal())
    y = sum(a * np.sin(TAU * f * k * t) * decay(n, t60 * d) for k, a, d in ((1, 1, 1), (2.57, 0.4, 0.5), (4.1, 0.2, 0.3)))
    y += 0.3 * hp(r.standard_normal(n), 3000) * np.exp(-t / 0.002)
    return norm(y * ramp(n, 0.0005), 1.0).astype(np.float32)


@lru_cache(maxsize=32)
def cymbal(size: float = 1.0, var: int = 0) -> np.ndarray:
    """Bo / nao cymbal: frequency-dependent decaying noise + inharmonic ring."""
    r = rng('cym', size, var)
    t60 = 2.8 * size
    n = ns(t60)
    t = tvec(n)
    y = band_noise(n, ((300, 1500, 0.5 * t60, 0.5), (1500, 4000, 0.8 * t60, 1.0),
                       (4000, 9000, 0.6 * t60, 0.9), (9000, 16000, 0.35 * t60, 0.6)), ('cym', size, var))
    for _ in range(24):
        fr = r.uniform(400, 7000) / size
        y += 0.02 * np.sin(TAU * fr * t + r.uniform(0, TAU)) * decay(n, r.uniform(0.3, 1.0) * t60)
    y += 1.5 * hp(r.standard_normal(n), 2000) * np.exp(-t / 0.01)
    return norm(hp(y, 250) * ramp(n, 0.001), 1.0).astype(np.float32)


@lru_cache(maxsize=32)
def gong(f0: float = 110.0, t60: float = 5.0, glide: float = 0.0, bloom: float = 0.6, var: int = 0) -> np.ndarray:
    """Tam-tam / opera gong: dense inharmonic partials; high partials bloom slowly.
    glide: pitch change in semitones (Chinese opera gongs fall or rise)."""
    r = rng('gong', f0, t60, glide, var)
    n = ns(t60 * 1.05)
    t = tvec(n)
    pitch = 2 ** (glide / 12 * (1 - np.exp(-t / 0.45)))
    ph = np.cumsum(pitch) * f0 / SR
    ratios = [1.0, 1.51, 1.97, 2.45, 2.92, 3.51, 4.02, 4.58] + list(np.sort(r.uniform(4.8, 16.0, 36)))
    y = np.zeros(n)
    for rt in ratios:
        if rt * f0 * pitch.max() > 16000:
            continue
        a = rt ** -0.85 * r.uniform(0.6, 1.0)
        att = 0.004 if rt < 3 else 0.01 + bloom * min(1.0, (rt - 3) / 10)
        y += a * np.sin(TAU * rt * ph + r.uniform(0, TAU)) * (1 - np.exp(-t / att)) * decay(n, t60 / (1 + 0.12 * rt))
    y += 0.4 * lp(r.standard_normal(n), 900) * np.exp(-t / 0.02)
    y += 0.02 * band_noise(n, ((2000, 9000, t60 * 0.4, 1.0),), ('gongwash', f0, var)) * (1 - np.exp(-t / (bloom + 0.05)))
    return norm(y * ramp(n, 0.002), 1.0).astype(np.float32)


BELL_TEMPLE = ((0.5, 0.6, 1.6), (1.0, 1.0, 1.0), (1.183, 0.8, 0.8), (1.506, 0.35, 0.6), (2.0, 0.7, 0.55),
               (2.514, 0.3, 0.4), (2.662, 0.25, 0.35), (3.011, 0.2, 0.3), (4.166, 0.15, 0.2), (5.433, 0.08, 0.15),
               (6.796, 0.05, 0.1))
BELL_ZHONG = ((1.0, 1.0, 1.0), (1.2, 0.7, 0.9), (2.42, 0.45, 0.5), (2.9, 0.3, 0.45), (3.6, 0.25, 0.3),
              (4.95, 0.12, 0.2), (6.3, 0.06, 0.12))
BELL_CHIME = ((1.0, 1.0, 1.0), (2.756, 0.35, 0.4), (5.404, 0.15, 0.2), (8.933, 0.06, 0.1))


@lru_cache(maxsize=160)
def bell(f0: float, t60: float = 4.0, kind: str = 'zhong', var: int = 0) -> np.ndarray:
    """Struck bells: 'temple' (large bronze bell), 'zhong' (bianzhong), 'chime' (small qing / shimmer)."""
    r = rng('bell', round(f0, 2), t60, kind, var)
    parts = {'temple': BELL_TEMPLE, 'zhong': BELL_ZHONG, 'chime': BELL_CHIME}[kind]
    n = ns(t60 * 1.05)
    t = tvec(n)
    y = np.zeros(n)
    for k, (rt, a, d) in enumerate(parts):
        fr = f0 * rt
        if fr > 16000:
            continue
        beat = 0.25 + 0.4 * k
        for s in (-1, 1):   # doublets -> slow beating ("warble")
            y += 0.5 * a * np.sin(TAU * (fr + s * beat * 0.5) * t + r.uniform(0, TAU)) * decay(n, t60 * d)
    y += 0.25 * bp(r.standard_normal(n), min(f0 * 3, 8000), min(f0 * 12, 16000)) * np.exp(-t / 0.004)
    return norm(y * ramp(n, 0.0015), 1.0).astype(np.float32)


def thump(f0: float = 55.0, t60: float = 0.3, key=0) -> np.ndarray:
    """Soft low thump (heartbeat, footfalls, body hits)."""
    r = rng('thump', f0, t60, key)
    n = ns(t60 + 0.05)
    t = tvec(n)
    f = f0 * (1 + 0.8 * np.exp(-t / 0.02))
    y = np.sin(TAU * np.cumsum(f) / SR) * decay(n, t60) + 0.3 * lp(r.standard_normal(n), 300) * np.exp(-t / 0.03)
    return norm(y * ramp(n, 0.002), 1.0)


def heartbeat(key=0) -> np.ndarray:
    n = ns(0.75)
    y = np.zeros(n)
    a = thump(52, 0.25, (key, 1)); y[:len(a)] += a
    b = 0.7 * thump(46, 0.3, (key, 2)); y[ns(0.28):ns(0.28) + len(b)] += b[:n - ns(0.28)]
    return y


def bird(key) -> np.ndarray:
    """Small songbird phrase: a few fast frequency-swept chirps."""
    r = rng('bird', key)
    out = []
    for _ in range(r.integers(3, 7)):
        d = r.uniform(0.04, 0.11)
        n = ns(d)
        t = np.linspace(0, 1, n)
        f0, f1 = r.uniform(2600, 5200), r.uniform(2400, 6000)
        f = f0 + (f1 - f0) * t ** r.uniform(0.5, 2) + 250 * np.sin(TAU * r.uniform(20, 45) * t * d)
        ph = np.cumsum(f) / SR
        out.append((np.sin(TAU * ph) + 0.15 * np.sin(2 * TAU * ph)) * np.sin(np.pi * t) ** 2)
        out.append(np.zeros(ns(r.uniform(0.03, 0.09))))
    return np.concatenate(out) * 0.6


def thunder(dur: float, key) -> np.ndarray:
    """Lightning crack(s) followed by a long, rolling rumble."""
    r = rng('thunder', key)
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    for _ in range(5):
        i0 = ns(r.uniform(0, 0.25))
        k = min(ns(0.4), n - i0)
        c = hp(r.standard_normal(k), r.uniform(800, 2500)) * np.exp(-np.arange(k) / (r.uniform(0.02, 0.08) * SR))
        y[i0:i0 + k] += r.uniform(0.4, 1.0) * c
    brown = hp(np.cumsum(r.standard_normal(n)), 20)
    rumble = lp(brown, 220, 4) * (0.6 + 0.4 * lfo_noise(n, 3.0, r)) * (1 - np.exp(-t / 0.15)) * decay(n, dur * 0.95)
    y = 0.5 * y + 1.3 * norm(rumble)
    return norm(np.tanh(1.5 * y), 1.0)


def riser(dur: float, key, lo=300.0, hi=6000.0) -> np.ndarray:
    """Noise sweep rising in pitch and loudness (tension builder)."""
    r = rng('riser', key)
    n = ns(dur)
    x = np.linspace(0, 1, n)
    fc = lo * (hi / lo) ** (x ** 1.5)
    y = sweep(r.standard_normal(n), 'bp', fc, q=3.0) * x ** 2
    return norm(fade_out(y, 0.02), 1.0)


# =============================================================================
# Effects: reverb, echo, mastering
# =============================================================================


@lru_cache(maxsize=8)
def reverb_ir(t60: float = 3.0, predelay: float = 0.03, bright: float = 0.7) -> np.ndarray:
    """Stereo synthetic room IR: band-wise exponentially decaying noise + early reflections."""
    n = ns(min(t60 * 1.15, 7.0) + predelay)
    out = np.zeros((2, n))
    for ch in range(2):
        r = rng('ir', t60, predelay, bright, ch)
        body = band_noise(n, ((20, 250, 1.1 * t60, 1.0), (250, 1000, t60, 1.0), (1000, 3000, 0.8 * t60, 0.85),
                              (3000, 6000, 0.55 * t60, 0.6 * bright), (6000, 12000, 0.35 * t60, 0.4 * bright),
                              (12000, 22050, 0.2 * t60, 0.25 * bright)), ('ir', t60, bright, ch))
        body *= ramp(n, 0.012)
        pd = ns(predelay)
        ir = np.zeros(n)
        ir[pd:] = body[:n - pd]
        for _ in range(10):   # early reflections
            i = ns(r.uniform(0.004, 0.07))
            ir[i] += r.choice([-1, 1]) * r.uniform(0.3, 1.0) * np.std(body[:ns(0.1)]) * 12
        out[ch] = ir / np.sqrt(np.sum(ir ** 2))
    return out


def conv_cyclic(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Circular convolution: the reverb tail of the loop end wraps onto its start."""
    L = x.shape[1]
    return np.fft.irfft(np.fft.rfft(x, axis=1) * np.fft.rfft(ir, n=L, axis=1), n=L, axis=1)


def conv_linear(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = x.shape[-1] + ir.shape[-1] - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m, axis=-1) * np.fft.rfft(ir, m, axis=-1), m, axis=-1)[..., :n]


def echo_fx(x: np.ndarray, delay: float, fb: float = 0.4, taps: int = 6, lpf: float = 3500.0) -> np.ndarray:
    """Ping-pong feedback delay computed in the frequency domain (cyclic over the buffer)."""
    n = x.shape[1]
    X = np.fft.rfft(x, axis=1)
    f = np.fft.rfftfreq(n, 1 / SR)
    lpr = 1 / np.sqrt(1 + (f / lpf) ** 2)
    Y = np.zeros_like(X)
    for k in range(1, taps + 1):
        g = fb ** (k - 1) * lpr ** k * np.exp(-2j * np.pi * f * k * delay)
        if k % 2:
            Y[0] += g * X[1]; Y[1] += g * X[0]
        else:
            Y += g * X
    return np.fft.irfft(Y, n=n, axis=1)


def k_weight(x: np.ndarray) -> np.ndarray:
    x = filt(x, 'highshelf', 1681.97, 0.7072, 3.9998)
    return filt(x, 'hp', 38.135, 0.5003)


def loudness(x: np.ndarray) -> float:
    """Integrated loudness (ITU-R BS.1770 style, gated) in LUFS."""
    x = np.atleast_2d(x)
    y = k_weight(x)
    p = np.sum(y ** 2, axis=0)
    c = np.concatenate([[0.0], np.cumsum(p)])
    blk, hop = ns(0.4), ns(0.1)
    if len(p) <= blk:
        e = np.array([p.mean()])
    else:
        idx = np.arange(0, len(p) - blk, hop)
        e = (c[idx + blk] - c[idx]) / blk
    lk = -0.691 + 10 * np.log10(e + 1e-20)
    e = e[lk > -70]
    if not len(e):
        return -70.0
    rel = -0.691 + 10 * np.log10(e.mean()) - 10
    e2 = e[-0.691 + 10 * np.log10(e) > rel]
    return float(-0.691 + 10 * np.log10(e2.mean()))


def limiter(x: np.ndarray, ceiling: float, cyclic: bool, win: float = 0.03) -> np.ndarray:
    """Look-ahead peak limiter (min-filtered gain, then smoothed)."""
    x = np.atleast_2d(x)
    need = np.minimum(1.0, ceiling / np.maximum(np.max(np.abs(x), axis=0), 1e-9))
    w = max(3, ns(win))
    mode = 'wrap' if cyclic else 'nearest'
    g = minimum_filter1d(need, 2 * w + 1, mode=mode)
    g = uniform_filter1d(g, w, mode=mode)
    return np.clip(x * g, -ceiling, ceiling)


def master(x: np.ndarray, target_lufs: float, cyclic: bool, ceiling_db: float = -1.2) -> np.ndarray:
    """High-pass, loudness-normalise (at most 5 dB into the limiter), then limit."""
    x = cyc(lambda z: hp(z, 28), x, ns(1.0)) if cyclic else hp(x, 28)
    g = dbg(target_lufs - loudness(x))
    c = dbg(ceiling_db)
    pk = float(np.max(np.abs(x))) * g
    if pk > c * dbg(5.0):
        g *= c * dbg(5.0) / pk
    return limiter(x * g, c, cyclic)


# =============================================================================
# Composition helpers: jianpu parser, scales, track timeline, players
# =============================================================================

PENT = (0, 2, 4, 7, 9)                 # gong shang jue zhi yu  (1 2 3 5 6)
DEG = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
TOKEN = re.compile(r"^([gsu]*)(?:([#b]?)([0-7])([',]*)|([A-G][#b]?)(-?\d))([~^v>th]*)(?:/([\d.]+))?([~^v>th]*)$")


@dataclass
class Note:
    beat: float
    dur: float
    midi: float
    vel: float = 1.0
    flags: str = ''
    grace: float | None = None
    up: int = 2          # semitones to the next pentatonic tone above
    dn: int = 2          # ... and below


def jp(text: str, key: int, meter: int = 4, vel: float = 1.0) -> list[Note]:
    """Parse jianpu.  `key` is the MIDI note of '1' (e.g. 62 means 1=D4).

    Tokens: digit 1-7 (0 = rest) with ' / , octave marks, optional #/b, or an
    absolute name like C#4; '/d' sets the length in beats (default 1); '-'
    extends the previous note by a beat; '|' is a bar line (bar lengths are
    checked).  Prefix flags: g grace, s slide-in, u scoop.  Suffix flags:
    ~ vibrato, ^ press-bend up, v bend/fall down, > accent, t tremolo, h harmonic."""
    pcs = {(key + p) % 12 for p in PENT}
    notes: list[Note] = []
    beat = bar_start = 0.0
    bars = False
    last = None
    for tok in text.split():
        if tok == '|':
            if abs(beat - bar_start - meter) > 1e-6:
                raise ValueError(f'bar of {beat - bar_start} beats near beat {beat} in: {text}')
            bars, bar_start = True, beat
            continue
        if tok == '-':
            if last is not None:
                last.dur += 1
            beat += 1
            continue
        m = TOKEN.match(tok)
        if not m:
            raise ValueError(f'bad jianpu token {tok!r}')
        pre, acc, d, octs, name, octn, suf0, dur, suf = m.groups()
        suf = suf0 + suf
        dur = float(dur) if dur else 1.0
        if d is not None:
            if d == '0':
                beat += dur
                last = None
                continue
            midi = key + DEG[int(d)] + 12 * (octs.count("'") - octs.count(',')) + {'#': 1, 'b': -1}.get(acc, 0)
        else:
            midi = 12 * (int(octn) + 1) + NAMES[name[0]] + {'#': 1, 'b': -1}.get(name[1:], 0)
        up = next(k for k in range(1, 13) if (midi + k) % 12 in pcs)
        dn = next(k for k in range(1, 13) if (midi - k) % 12 in pcs)
        last = Note(beat, dur, midi, vel, pre.replace('g', '') + suf, midi + up if 'g' in pre else None, up, dn)
        notes.append(last)
        beat += dur
    if bars and abs(beat - bar_start) > 1e-6 and abs(beat - bar_start - meter) > 1e-6:
        raise ValueError(f'last bar has {beat - bar_start} beats in: {text}')
    return notes


class Scale:
    """Pentatonic scale; sc(i) maps a scale index (0 = tonic '1') to MIDI."""

    def __init__(self, tonic: int, steps=PENT):
        self.tonic, self.steps = tonic, steps

    def __call__(self, i: int) -> int:
        o, k = divmod(int(i), len(self.steps))
        return self.tonic + 12 * o + self.steps[k]


class Track:
    """Stereo mix buffer.  Looping tracks use a cyclic timeline of exactly the
    loop length: anything that runs past the end wraps onto the beginning."""

    def __init__(self, name, bpm, bars, meter=4, loop=True, tail=0.0, rev=(3.0, 0.03, 0.7),
                 lufs=-15.0, echo_beats=0.75, echo_fb=0.4):
        self.name, self.bpm, self.meter, self.loop = name, bpm, meter, loop
        self.spb = 60.0 / bpm
        self.L = ns(bars * meter * self.spb)
        self.N = self.L if loop else self.L + ns(tail)
        self.dry = np.zeros((2, self.N))
        self.send = np.zeros((2, self.N))
        self.eko = np.zeros((2, self.N))
        self.rev, self.lufs = rev, lufs
        self.echo_time, self.echo_fb = echo_beats * self.spb, echo_fb
        self.rng = rng('track', name)

    def sec(self, beat: float) -> float:
        return beat * self.spb

    def _mix(self, buf, st, i0):
        n = min(st.shape[1], self.N)
        if self.loop:
            i0 %= self.N
            first = min(n, self.N - i0)
            buf[:, i0:i0 + first] += st[:, :first]
            if n > first:
                buf[:, :n - first] += st[:, first:n]
        else:
            if i0 < 0:
                st, n, i0 = st[:, -i0:], n + i0, 0
            m = min(n, self.N - i0)
            if m > 0:
                buf[:, i0:i0 + m] += st[:, :m]

    def add(self, sig, t: float, pan=0.0, gain=1.0, rev=0.25, echo=0.0):
        gl, gr = pan_gains(pan)
        sig = np.asarray(sig, dtype=float) * gain
        st = np.vstack([sig * gl, sig * gr])
        i0 = int(round(t * SR))
        self._mix(self.dry, st, i0)
        if rev:
            self._mix(self.send, st * rev, i0)
        if echo:
            self._mix(self.eko, st * echo, i0)

    def add_at(self, sig, bar: float, beat: float = 0.0, **kw):
        self.add(sig, self.sec(bar * self.meter + beat), **kw)

    def render(self) -> np.ndarray:
        mix = self.dry
        if np.any(self.eko):
            e = echo_fx(self.eko, self.echo_time, self.echo_fb)
            mix = mix + e
            self.send += 0.5 * e
        ir = reverb_ir(*self.rev)
        wet = conv_cyclic(self.send, ir) if self.loop else conv_linear(self.send, ir)[:, :self.N]
        out = master(mix + wet, self.lufs, self.loop)
        if not self.loop:
            out = fade_out(out, 1.2)
        return out


def play(tr: Track, kind: str, notes, bar: float = 0, key: int | None = None, oct: int = 0, pan=0.0,
         gain=1.0, rev=0.3, echo=0.0, ring=None, vel=1.0, human=0.006):
    """Play a note list (or jianpu text with `key`) on an instrument, starting at `bar`."""
    if isinstance(notes, str):
        notes = jp(notes, key, tr.meter)
    beat0 = bar * tr.meter
    R = tr.rng
    if kind in PLUCKED:
        for nt in notes:
            m = nt.midi + 12 * oct
            t = tr.sec(beat0 + nt.beat) + R.normal(0, human)
            d = nt.dur * tr.spb
            v = vel * nt.vel * (1.25 if '>' in nt.flags else 1.0) * (1 + 0.06 * R.standard_normal())
            vq = round(float(np.clip(v, 0.1, 1.2)) * 20) / 20
            if 't' in nt.flags:   # lun-zhi tremolo
                rate = 13.0
                k = max(2, int(d * rate))
                for j in range(k):
                    pv = round(vq * (0.62 + 0.18 * (j % 2) + 0.15 * math.sin(math.pi * j / k)) * 20) / 20
                    tr.add(pluck(m, 0.5, kind, pv), t + j / rate + R.normal(0, 0.004), pan, gain, rev, echo)
                continue
            bend = ()
            if '^' in nt.flags:
                tb = round(min(0.45 * d, 0.35), 2)
                bend = ((0, 0), (tb, 0), (tb + 0.18, nt.up))
            elif 'v' in nt.flags:
                tb = round(min(0.5 * d, 0.4), 2)
                bend = ((0, 0), (tb, 0), (tb + 0.25, -nt.dn))
            elif 's' in nt.flags:
                bend = ((0, -nt.dn), (0.02, -nt.dn), (0.17, 0))
            rg = ring or RING[kind]
            if kind == 'pipa':
                rg = min(rg, d + 0.3)
            elif bend or '~' in nt.flags:
                rg = max(rg, d + 0.8)
            rg = round(max(rg, 0.25), 1)
            s = pluck(m, rg, kind, vq, bend, 0.25 if '~' in nt.flags else 0.0, 'h' in nt.flags)
            tr.add(s, t, pan, gain, rev, echo)
        return
    phrases: list[list[Note]] = []
    for nt in notes:
        if phrases and abs(nt.beat - (phrases[-1][-1].beat + phrases[-1][-1].dur)) < 1e-6:
            phrases[-1].append(nt)
        else:
            phrases.append([nt])
    for i, ph in enumerate(phrases):
        b0 = ph[0].beat
        ev = [(tr.sec(nt.beat - b0), nt.dur * tr.spb, nt.midi + 12 * oct,
               vel * nt.vel * (1 + 0.04 * R.standard_normal()), nt.flags,
               None if nt.grace is None else nt.grace + 12 * oct) for nt in ph]
        sig = legato(ev, kind, (tr.name, kind, beat0, i, oct))
        tr.add(sig, tr.sec(beat0 + b0) + R.normal(0, 0.004), pan, gain, rev, echo)


def arp(tr, kind, sc: Scale, roots, bar, pattern, step=0.5, base=-5, vel=0.5, accent=1.25, **kw):
    """Broken-chord accompaniment: one root (scale index, None = tacet) per bar."""
    notes = []
    per_bar = int(round(tr.meter / step))
    for b, root in enumerate(roots):
        if root is None:
            continue
        for i in range(per_bar):
            off = pattern[i % len(pattern)]
            if off is not None:
                notes.append(Note(b * tr.meter + i * step, step, sc(root + off + base), vel * (accent if i == 0 else 1.0)))
    play(tr, kind, notes, bar=bar, **kw)


def gliss(tr, kind, sc: Scale, i0, i1, bar, beat=0.0, dt=0.032, vel=0.6, **kw):
    """Guzheng-style glissando sweeping the pentatonic strings from index i0 to i1."""
    step = 1 if i1 >= i0 else -1
    idx = list(range(i0, i1 + step, step))
    notes = [Note(beat + j * dt / tr.spb, 0.5, sc(i), vel * (0.55 + 0.45 * j / max(1, len(idx) - 1)))
             for j, i in enumerate(idx)]
    play(tr, kind, notes, bar=bar, human=0.002, **kw)


def chords(tr, kind, progression, bar, beats_each, pans=None, **kw):
    """Voice-led chord lines: voice k of every chord forms one legato line."""
    nv = max(len(c) for c in progression if c)
    pans = pans or np.linspace(-0.5, 0.5, nv)
    for k in range(nv):
        notes = [Note(i * beats_each, beats_each, c[min(k, len(c) - 1)]) for i, c in enumerate(progression) if c]
        play(tr, kind, notes, bar=bar, pan=float(pans[k]), **kw)


def pads(tr, progression, bar, beats_each, gain=0.5, rev=0.4, pan_spread=0.6, **kw):
    """Pad chords; repeated pitches in a voice are tied instead of re-attacked."""
    nv = max(len(c) for c in progression if c)
    for k in range(nv):
        seq = [(c[min(k, len(c) - 1)] if c else None) for c in progression]
        i = 0
        while i < len(seq):
            if seq[i] is None:
                i += 1
                continue
            j = i
            while j + 1 < len(seq) and seq[j + 1] == seq[i]:
                j += 1
            dur = (j - i + 1) * beats_each * tr.spb
            s = pad_note(seq[i], dur + 0.6, (tr.name, k, i), **kw)
            p = pan_spread * (2 * k / max(1, nv - 1) - 1)
            tr.add(s, tr.sec(bar * tr.meter + i * beats_each) - 0.3, p, gain, rev)
            i = j + 1


VEL = {'X': 1.0, 'x': 0.7, 'o': 0.38}


def beats(tr, pattern: str, sample, bar, bars=1, step=0.25, gain=1.0, pan=0.0, rev=0.2, human=0.004,
          nvar=4, cresc=0.0):
    """Drum pattern: 'X' accent, 'x' normal, 'o' ghost, '.' rest; `sample(var)` returns audio."""
    pat = pattern.replace(' ', '')
    total = bars * len(pat)
    for b in range(bars):
        for i, c in enumerate(pat):
            if c in VEL:
                pos = b * len(pat) + i
                g = gain * VEL[c] * (1 + 0.06 * tr.rng.standard_normal()) * (1 + cresc * (pos / total - 1))
                tr.add(sample(pos % nvar), tr.sec(bar * tr.meter + b * len(pat) * step + i * step)
                       + tr.rng.normal(0, human), pan, g, rev)


def wind_layer(tr, gain=0.2, lo=200.0, hi=2500.0, key='wind', rev=0.2):
    """Seamless wind bed: periodic filtered noise with periodic gusts + a faint whistle."""
    r = rng('windlayer', tr.name, key)
    n = tr.N
    base = periodic_noise(n, r, lo, hi, tilt=-4)
    whistle = periodic_noise(n, r, 700, 950, tilt=0)
    g1 = 0.6 + 0.4 * periodic_lfo(n, r, (2, 3, 5, 7))
    g2 = np.clip(periodic_lfo(n, r, (3, 4, 9)), 0, 1) ** 2
    L = base * g1 + 0.25 * whistle * g2
    R = np.roll(base, n // 3) * g1 + 0.25 * np.roll(whistle, n // 5) * g2
    for ch, x in enumerate((L, R)):
        tr.dry[ch] += gain * 0.3 * x
        tr.send[ch] += rev * gain * 0.3 * x


def far(x: np.ndarray, cutoff: float = 600.0) -> np.ndarray:
    """Make a sample sound distant (dull)."""
    return lp(np.asarray(x, dtype=float), cutoff)


@lru_cache(maxsize=16)
def stab(midis: tuple, dur: float = 0.25, key=0) -> np.ndarray:
    """Short choir 'HA!' chord (all voices summed)."""
    parts = [legato([(0.0, dur, m, 1.0, '>', None)], 'stab', ('stab', m, key)) for m in midis]
    n = max(len(p) for p in parts)
    return norm(sum(np.pad(p, (0, n - len(p))) for p in parts), 1.0)


def sprinkle(tr, bar0, bars, step, prob, make, key, gain=0.2, pan=0.8, rev=0.4, echo=0.0):
    """Random sparse events (bells, knocks...): make(r) -> samples, one chance per `step` beats."""
    r = rng('sprinkle', tr.name, key)
    k = int(round(bars * tr.meter / step))
    for i in range(k):
        p = prob(i / k) if callable(prob) else prob
        if r.random() < p:
            tr.add(make(r), tr.sec(bar0 * tr.meter + i * step) + r.normal(0, 0.01),
                   r.uniform(-pan, pan), gain * r.uniform(0.6, 1.0), rev, echo)


# =============================================================================
# Music tracks
# =============================================================================


def m_title() -> Track:
    """Majestic main theme: guzheng + dizi over pads and bells, D gong mode, 72 bpm."""
    tr = Track('title', 72, 24, rev=(3.8, 0.04, 0.8), lufs=-15.0)
    sc = Scale(62)
    roots = [0, -1, 1, 3] + [0, -1, 1, 3, 0, -1, 3, 0] + [-1, 1, 3, 1, 0, -1, 3, 0] + [0, -1, 1, 3]
    pads(tr, [[sc(r - 5), sc(r - 2), sc(r), sc(r + 3)] for r in roots], 0, 4, gain=0.32, bright=1200)
    # guzheng: opening glissando, rolling arpeggios, calls, closing glissando
    zk = dict(pan=-0.35, rev=0.35)
    gliss(tr, 'zheng', sc, -5, 10, 0, vel=0.8, **zk)
    arp(tr, 'zheng', sc, roots[:4], 0, (0, 3, 5, 7, 8, 7, 5, 3), vel=0.42, **zk)
    arp(tr, 'zheng', sc, roots[4:12], 4, (0, 3, 5, None, 7, None, 5, 3), vel=0.34, **zk)
    arp(tr, 'zheng', sc, roots[12:20], 12, (0, 3, 5, 7, 5, 3, 7, 3), vel=0.28, pan=-0.55, rev=0.35)
    play(tr, 'zheng', "6 1' 2'/2^", key=62, bar=12, vel=0.85, **zk)
    play(tr, 'zheng', "5 6 1'/2~", key=62, bar=14, vel=0.85, **zk)
    play(tr, 'zheng', "3'/2 2' 1' | 6 1' 2'/2 | 3' 5' 3' 2' | 1'/4~", key=62, bar=16, vel=0.8, **zk)
    gliss(tr, 'zheng', sc, 13, -5, 20, vel=0.7, **zk)
    arp(tr, 'zheng', sc, roots[20:], 20, (0, 3, 5, 7), step=1.0, vel=0.35, **zk)
    # dizi: A theme, answers, climax, closing fragment
    dk = dict(key=74, pan=0.15, rev=0.4, echo=0.12, gain=0.9)
    play(tr, 'dizi', "3/1.5 5/0.5 6 1' | g6/1.5 5/0.5 3/2~ | 2/1.5 3/0.5 5 6 | 5/4~ | "
                     "3/1.5 5/0.5 6 1' | g2'/1.5 1'/0.5 6 5 | 6 5/0.5 3/0.5 2 3 | 1/4~", bar=4, **dk)
    play(tr, 'dizi', "3 2/0.5 1/0.5 2/2~", bar=13, **dk)
    play(tr, 'dizi', "2 1/0.5 6,/0.5 5,/2~", bar=15, **dk)
    play(tr, 'dizi', "3'/2 2' 1' | 6 1' g2'/2 | 3' 5' 3' 2' | 1'/4~", bar=16, **dk)
    play(tr, 'dizi', "6/2 5 3 | 2/4~", bar=21, vel=0.7, **dk)
    chords(tr, 'choir', [[sc(r), sc(r + 3), sc(r + 5)] for r in roots[12:20]], 12, 4, gain=0.22, rev=0.6)
    # percussion, bells, gongs
    big = lambda v: taiko(1.2, v)
    beats(tr, 'X.........x.....', big, 4, bars=8, gain=0.5, rev=0.35)
    beats(tr, 'X.....x.x...X...', big, 12, bars=4, gain=0.6, rev=0.35)
    beats(tr, 'X..x..x.X...X.x.', big, 16, bars=3, gain=0.7, rev=0.35)
    beats(tr, '..o...o...o...oo', lambda v: hand_drum(210, 0.25, 0.4, v), 16, bars=3, gain=0.3, pan=0.3)
    beats(tr, 'X...X...X.x.XxXX', big, 19, gain=0.7, cresc=0.5, rev=0.35)
    beats(tr, 'X...............', big, 20, gain=0.9, rev=0.4)
    tr.add_at(bell(float(hz(50)), 7.0, 'temple'), 0, gain=0.5, rev=0.5)
    tr.add_at(bell(float(hz(50)), 7.0, 'temple', 1), 20, gain=0.45, rev=0.5)
    tr.add_at(gong(98, 6.0, -0.5), 20, gain=0.4, rev=0.4)
    tr.add_at(gong(196, 4.0, 0.4, var=1), 12, gain=0.18, rev=0.4)
    tr.add_at(cymbal(1.1), 20, gain=0.18, rev=0.5)
    for b, m in ((11, 74), (11, 81), (19, 74), (19, 86)):
        tr.add_at(bell(float(hz(m)), 3.5, 'zhong'), b, gain=0.22, pan=0.4 if m > 80 else -0.2, rev=0.5)
    sc6 = Scale(86)
    sprinkle(tr, 20, 4, 0.5, 0.35, lambda r: bell(float(hz(sc6(int(r.integers(0, 6))))), 2.5, 'chime'),
             'title-chimes', gain=0.12, echo=0.3)
    return tr


def m_sect() -> Track:
    """Serene mountain sect: guqin harmonics & slides, xiao melody, birds, F zhi mode, 60 bpm."""
    tr = Track('sect', 60, 20, rev=(3.2, 0.03, 0.7), lufs=-17.0, echo_beats=0.75)
    sc = Scale(53)
    roots = [0, -2, -1, -2, 0, -1, 1, -2, 0, -2]
    pads(tr, [[sc(r - 5), sc(r - 2), sc(r)] for r in roots], 0, 8, gain=0.26, warm=True, att=2.0, rel=2.5)
    wind_layer(tr, gain=0.1, lo=300, hi=3000, key='sect')
    qk = dict(pan=-0.3, rev=0.4, echo=0.15)
    play(tr, 'qin', "5h 6h 1'/2h | 2'/1.5h 1'/0.5h 6/2h | 5h 3h 2h 3h | 5/4h", key=65, bar=0, gain=1.8, **qk)
    play(tr, 'qin', "1/2 5,/2 | s2/2 1/2 | 6,/2 5,/2 | 1/2 5/2v | 2/2 3/2 | 5,/2 1/2 | 6,/2 1/2 | 5,/4~",
         key=53, bar=4, vel=0.6, **qk)
    play(tr, 'qin', "5 6/0.5 1'/0.5 s2'/2 | 1' 6 5/2~ | 3 5 6 5/0.5 3/0.5 | 2/2v 1/2", key=53, bar=12, vel=0.85, **qk)
    play(tr, 'qin', "3'h 2'h 1'/2h | 6h 1'h 2'/2h | 3'/2h 2'h 6h | 5/4h", key=65, bar=16, gain=1.8, **qk)
    play(tr, 'xiao', "0/2 3/2 | 2/4~ | 0/4 | 0/2 6,/2~", key=65, bar=16, vel=0.5, pan=0.15, rev=0.5, echo=0.2)
    xk = dict(key=65, pan=0.15, rev=0.45, echo=0.2)
    play(tr, 'xiao', "5,/2 6, 1 | 2/3~ 1 | 6,/2 5, 6, | 1/4~ | 2/1.5 3/0.5 5/2~ | 3 2 1/2 | 2 1 6, 1 | 5,/4~",
         bar=4, **xk)
    play(tr, 'xiao', "5,/4 | 6,/4 | 1/4 | 5,/4~", bar=12, vel=0.55, **xk)
    for i, (b, beat) in enumerate(((1, 2.5), (3, 1.0), (9, 3.0), (11, 2.0), (16, 1.5), (17, 3.2), (19, 0.5))):
        tr.add(bird(('sect', i)), tr.sec(b * 4 + beat), pan=(-0.7, 0.6, -0.5, 0.8, 0.5, -0.8, 0.2)[i], gain=0.12, rev=0.35)
    tr.add_at(bell(float(hz(53)), 7.0, 'temple'), 0, gain=0.3, rev=0.6)
    tr.add_at(bell(float(hz(53)), 7.0, 'temple', 1), 10, gain=0.22, rev=0.7)
    return tr


def m_forest() -> Track:
    """Mysterious bamboo forest: xiao in B yu mode, sparse echoing plucks, bamboo knocks, wind, 56 bpm."""
    tr = Track('forest', 56, 18, rev=(4.2, 0.05, 0.55), lufs=-18.0, echo_beats=0.75, echo_fb=0.45)
    wind_layer(tr, gain=0.35, lo=150, hi=2000, key='forest')
    B, E, A = [35, 42, 47], [40, 47, 52], [33, 40, 45]
    pads(tr, [B, B, E, B, A, B], 0, 12, gain=0.4, bright=500, att=2.5, rel=3.0)
    xk = dict(key=62, pan=0.1, rev=0.5, echo=0.25)
    play(tr, 'xiao', "6,/2 1 2 | 3/3~ 2/0.5 1/0.5 | 2/2 6,/2 | 6,/4~", bar=2, **xk)
    play(tr, 'xiao', "3 5 6/2~ | 5 3 2/2 | 3 2/0.5 1/0.5 6,/2 | 5,/2 6,/2~", bar=8, **xk)
    play(tr, 'xiao', "1/2 2 3 | 6,/4~", bar=13, **xk)
    motifs = {'A': "6 3'/0.5 2'/2.5", 'B': "6'/1h 5'/1h 3'/2h", 'C': "3/0.5 6/0.5 2' 1'/2v"}
    for b, m in ((0, 'A'), (1, 'B'), (6, 'C'), (7, 'B'), (12, 'A'), (15, 'C'), (16, 'B'), (17, 'A')):
        play(tr, 'zheng', motifs[m], key=50, bar=b, pan=-0.35, vel=0.45, rev=0.45, echo=0.35)
    sprinkle(tr, 0, 18, 0.5, 0.07, lambda r: woodblock(float(r.choice([480, 560, 740])), int(r.integers(4)), 0.12),
             'knocks', gain=0.16, rev=0.5, echo=0.3)
    tr.add_at(far(bell(float(hz(47)), 7.0, 'temple'), 1500), 9, gain=0.25, rev=0.8)
    return tr


TOWN_A = ("5/0.5 5/0.5 6/0.5 1'/0.5 6 5 | 3/0.5 5/0.5 6/0.5 5/0.5 3 2 | 1/0.5 2/0.5 3/0.5 5/0.5 2/0.5 3/0.5 1 | "
          "6,/0.5 1/0.5 2 5,/2{L} | 5/0.5 5/0.5 6/0.5 1'/0.5 2' 1'/0.5 6/0.5 | 5/0.5 6/0.5 1'/0.5 6/0.5 5 3 | "
          "2/0.5 3/0.5 5/0.5 6/0.5 5/0.5 3/0.5 2/0.5 3/0.5 | 1/2{L} 1 0")


def m_town() -> Track:
    """Lively market town: pipa and erhu trading a G gong-mode folk dance over small percussion, 112 bpm."""
    tr = Track('town', 112, 40, rev=(1.6, 0.015, 0.8), lufs=-14.5)
    sc = Scale(55)
    rA, rB = [0, -1, 0, -2, 0, -1, 1, 0], [0, -1, 0, -1, -2, -1, -2, 0]
    roots = [0, 0, -2, 0] + rA + rA + rB + rA + [0, -1, -2, 0]
    arp(tr, 'pipa', sc, roots, 0, (0, None, 3, 5, 0, None, 3, 5), vel=0.42, pan=0.45, rev=0.2)
    pipa_a, erhu_a = TOWN_A.replace('{L}', 't'), TOWN_A.replace('{L}', '~')
    pk = dict(key=67, pan=0.2, rev=0.25)
    ek = dict(key=67, pan=-0.2, rev=0.3)
    play(tr, 'pipa', "0/4 | 0/4 | 2/0.5 3/0.5 5/0.5 6/0.5 1' 6/0.5 5/0.5 | 1 5, 1/2t", bar=0, vel=0.9, **pk)
    play(tr, 'pipa', pipa_a, bar=4, vel=0.95, **pk)
    play(tr, 'erhu', erhu_a, bar=12, **ek)
    calls = ["1'/0.5 1'/0.5 6/0.5 1'/0.5 2' 1'", "3'/0.5 2'/0.5 1'/0.5 2'/0.5 6 5",
             "5/0.5 6/0.5 5/0.5 3/0.5 2/0.5 3/0.5 5"]
    answers = ["6 5/0.5 6/0.5 1'/2~", "3 5/0.5 3/0.5 2/2~", "6 1' 6/0.5 5/0.5 3"]
    for i in range(3):
        play(tr, 'pipa', calls[i], bar=20 + 2 * i, vel=0.95, **pk)
        play(tr, 'erhu', answers[i], bar=21 + 2 * i, **ek)
    both = "2/0.5 3/0.5 5/0.5 6/0.5 1' 6/0.5 5/0.5 | 1 5, 1/2"
    play(tr, 'pipa', both.replace('1/2', '1/2t'), bar=26, vel=0.95, **pk)
    play(tr, 'erhu', both, bar=26, **ek)
    play(tr, 'pipa', pipa_a, bar=28, oct=1, vel=0.8, **pk)
    play(tr, 'erhu', erhu_a, bar=28, **ek)
    play(tr, 'dizi', erhu_a, key=79, bar=28, pan=0.05, gain=0.35, rev=0.3)
    play(tr, 'pipa', TOWN_A.split('|', 2)[0] + '|' + TOWN_A.split('|', 2)[1], key=67, bar=36, vel=0.9, pan=0.2)
    # percussion
    beats(tr, 'x.xx.x.x', lambda v: woodblock(1300, v, 0.06), 0, bars=40, step=0.5, gain=0.22, pan=0.3, rev=0.15)
    beats(tr, 'X.......x.......', lambda v: hand_drum(150, 0.35, 0.3, v), 0, bars=40, gain=0.45, rev=0.2)
    beats(tr, 'X..x..x.x.x.x...', lambda v: hand_drum(420, 0.12, 0.6, v), 4, bars=32, gain=0.28, pan=-0.25, rev=0.15)
    beats(tr, 'X..x..x.x.xxX.XX', lambda v: hand_drum(420, 0.12, 0.6, v), 36, bars=4, gain=0.3, pan=-0.25, rev=0.15)
    beats(tr, '....x.......x...', lambda v: cymbal(0.45, v), 12, bars=24, gain=0.12, pan=0.35, rev=0.2)
    luo = lambda v: gong(420, 1.2, 2.0, 0.05, v)
    for b in (4, 12, 20, 28):
        tr.add_at(luo(0), b, gain=0.28, pan=-0.3, rev=0.25)
    beats(tr, 'X.......x.x.X...', luo, 36, bars=4, gain=0.22, pan=-0.3, rev=0.25)
    tr.add_at(cymbal(0.8), 28, gain=0.2, pan=0.2, rev=0.3)
    return tr


def m_abyss() -> Track:
    """Dark demonic abyss: C# drones with semitone rubs, dissonant erhu, heartbeat and distant taiko, 60 bpm."""
    tr = Track('abyss', 60, 22, rev=(5.5, 0.06, 0.35), lufs=-17.0, echo_beats=1.5, echo_fb=0.45)
    r = rng('abyss-rumble')
    rum = periodic_noise(tr.N, r, 25, 180, tilt=-3) * (0.6 + 0.4 * periodic_lfo(tr.N, r, (1, 2, 3)))
    tr.dry += 0.1 * np.vstack([rum, np.roll(rum, tr.N // 7)])
    A, T, S, C = [37, 44, 49], [37, 43, 49], [37, 44, 50], [36, 44, 49]
    pads(tr, [A, A, A, A, T, T, S, S, C, C, A], 0, 8, gain=0.5, bright=420, att=2.5, rel=3.0)
    for b in range(22):   # heartbeat: slow, then racing in the middle section
        for beat in ((0, 1, 2, 3) if 12 <= b < 20 else (0, 2)):
            tr.add(heartbeat((b, beat)), tr.sec(b * 4 + beat), gain=0.5 if 12 <= b < 20 else 0.4, rev=0.25)
    beats(tr, 'X.....x.........' + '.' * 16, lambda v: far(taiko(1.4, v), 500), 0, bars=11, step=0.25,
          gain=0.45, rev=0.9)
    ek = dict(pan=-0.2, rev=0.55, echo=0.2)
    play(tr, 'erhu', "C#4/3 D4/1 | C#4/2~ 0/2 | E4/1.5 F4/0.5 E4 D4 | C#4/4v", key=61, bar=4, **ek)
    play(tr, 'erhu', "G#4/2 A4/2 | G4/3~ F#4/1 | E4 D4 E4 G4 | F#4/2 D4/1 C#4/1 | C#4/4~", key=61, bar=12, **ek)
    play(tr, 'gehu', "D3/4~ | C#3/4 | C3/2 C#3/2~ | C#3/4v", key=61, bar=13, pan=0.35, gain=0.6, rev=0.5)
    chords(tr, 'choir_o', [[49, 56], [50, 56]], 8, 8, gain=0.3, rev=0.7)
    chords(tr, 'choir_o', [[49, 56], [48, 55]], 17, 8, gain=0.3, rev=0.7)
    tr.add_at(gong(55, 7.0, -2.0), 0, gain=0.4, rev=0.6)
    tr.add_at(gong(55, 7.0, -2.0, var=1), 12, gain=0.35, rev=0.6)
    tr.add_at(far(thunder(5.0, 'abyss'), 400), 8, gain=0.3, rev=0.5)
    return tr


def m_sky() -> Track:
    """Ethereal celestial isles: choir pad, shimmering chimes, bianzhong, slow dizi, E gong mode, 66 bpm."""
    tr = Track('sky', 66, 22, rev=(5.0, 0.05, 0.9), lufs=-17.0, echo_beats=1.5, echo_fb=0.45)
    sc = Scale(52)
    I, vi, II, V = ([sc(i) for i in c] for c in ((0, 3, 5, 7), (-1, 2, 4, 5), (1, 4, 6, 8), (-2, 1, 3, 4)))
    prog = [I, vi, II, V, I, vi, II, V, I, vi, V]
    chords(tr, 'choir', prog, 0, 8, gain=0.34, rev=0.65)
    pads(tr, [[m - 12 for m in c[:2]] for c in prog], 0, 8, gain=0.25, warm=True, att=2.0, rel=2.5)
    wind_layer(tr, gain=0.06, lo=400, hi=4000, key='sky')
    hi = Scale(76)
    dens = lambda x: 0.32 if (x < 4 / 22 or x > 20 / 22) else 0.16
    sprinkle(tr, 0, 22, 0.25, dens, lambda r: bell(float(hz(hi(int(r.integers(0, 8))))), 2.5, 'chime', int(r.integers(3))),
             'sky-shimmer', gain=0.12, rev=0.55, echo=0.3)
    zs = Scale(64)
    for b in (0, 2, 20):
        for j, i in enumerate((0, 2, 3, 5)):
            tr.add(bell(float(hz(zs(i))), 3.5, 'zhong', j), tr.sec(b * 4 + j), pan=-0.4 + 0.25 * j, gain=0.2, rev=0.55)
    play(tr, 'zheng', "5h/2 6h 1'h | 2'/4h | 3'h 2'h 1'/2h | 6/4h", key=64, bar=0, pan=-0.3, vel=0.6, rev=0.5, echo=0.3)
    play(tr, 'zheng', "5h 3h 2h 1h | 6,/4h", key=64, bar=20, pan=-0.3, vel=0.6, rev=0.5, echo=0.3)
    play(tr, 'dizi', "5/2 6 1' | 2'/4~ | 3'/1.5 2'/0.5 1' 6 | 5/4~ | 6/2 1' 2' | 3'/3~ 5' | 3' 2' 1' 2' | 3'/4~ | "
                     "5'/2 3' 2' | 1'/2 6/2 | 5 6 1' 3' | 2'/4~ | 1'/2 2' 3' | 6/4~ | 5/2 3 2 | 1/4~",
         key=76, bar=4, pan=0.1, rev=0.5, echo=0.2, gain=0.8)
    return tr


def riff_notes(sc: Scale, roots, cell, vels) -> list[Note]:
    """16th-note ostinato: `cell` scale offsets applied to one root per bar."""
    out = []
    for b, root in enumerate(roots):
        for i, off in enumerate(cell):
            out.append(Note(b * 4 + i * 0.25, 0.25, sc(root + off), vels[i % len(vels)]))
    return out


def bass_notes(sc: Scale, roots, pattern=(1.0, 0.55, 0.8, 0.55, 0.95, 0.55, 0.8, 0.6), step=0.5) -> list[Note]:
    out = []
    for b, root in enumerate(roots):
        for i, v in enumerate(pattern):
            out.append(Note(b * 4 + i * step, step, sc(root), v))
    return out


def m_battle() -> Track:
    """Combat: taiko 3-3-2 ostinato, pipa riff, erhu melody in D yu mode, breakdown and fills, 140 bpm."""
    tr = Track('battle', 140, 48, rev=(2.0, 0.02, 0.7), lufs=-14.0)
    sc = Scale(53)
    cyc4 = [-1, -1, -2, 0]
    roots = cyc4 * 12
    cell = (0, 0, 2, 3, 0, 0, 4, 3, 0, 0, 2, 3, 5, 4, 3, 2)
    vels = (1.0, 0.55, 0.7, 0.65, 0.8, 0.55, 0.75, 0.65)
    rk = dict(pan=0.3, rev=0.18)
    play(tr, 'pipa', riff_notes(sc, roots[4:28], cell, vels), bar=4, vel=0.8, **rk)
    play(tr, 'pipa', riff_notes(sc, roots[36:48], cell, vels), bar=36, vel=0.85, **rk)
    bass = Scale(41)
    play(tr, 'gehu', bass_notes(bass, roots[4:28]), bar=4, gain=0.55, rev=0.1)
    play(tr, 'gehu', bass_notes(bass, roots[36:48]), bar=36, gain=0.55, rev=0.1)
    play(tr, 'gehu', [Note(i * 4, 4, bass(r)) for i, r in enumerate(roots[28:36])], bar=28, gain=0.5, rev=0.2)
    play(tr, 'gehu', [Note(i * 4, 4, bass(r)) for i, r in enumerate(roots[:4])], bar=0, gain=0.45, rev=0.2)
    ek = dict(key=65, pan=-0.15, rev=0.3)
    melody = ("6,/1.5 1/0.5 2 3 | 2/0.5 1/0.5 6, 5,/2~ | 6, 1/0.5 2/0.5 3 5 | 3/3~ 2 | "
              "6,/1.5 1/0.5 2 3 | 5 3/0.5 2/0.5 1 2 | 6,/0.5 5,/0.5 3,/0.5 5,/0.5 6, 1 | 6,/4~")
    play(tr, 'erhu', melody, bar=12, **ek)
    motifs = ["5/0.5 6/0.5 1'", "3/0.5 2/0.5 6,", "1'/0.5 6/0.5 5", "3/0.5 5/0.5 6~"]
    runs = []
    for i in range(6):   # call (pipa run) and response (erhu)
        b = 20 + i
        runs += [Note(i * 4 + j * 0.25, 0.25, sc(roots[b] + 5 + j), 0.9 if j == 0 else 0.7) for j in range(8)]
        play(tr, 'erhu', motifs[i % 4], bar=b + 0.5, **ek)
    play(tr, 'pipa', runs, bar=20, pan=0.35, rev=0.2)
    play(tr, 'erhu', "6 5 3 5 | 6/4~", bar=26, **ek)
    play(tr, 'erhu', "6/4~ | 5/4~ | 3/4~ | 5/2 6/2 | 1'/4~ | 2'/4~ | 3'/2 2'/2 | 6/4~", bar=28, **ek)
    play(tr, 'pipa', "6/4t | 5/4t | 1'/4t | 6/4t", key=65, bar=32, pan=0.4, vel=0.55, rev=0.3)
    chords(tr, 'choir', [[50, 57, 62], [48, 55, 60], [53, 60, 65], [50, 57, 62]], 28, 8, gain=0.3, rev=0.5)
    play(tr, 'erhu', melody, bar=36, **ek)
    play(tr, 'dizi', melody, key=77, bar=36, pan=0.1, gain=0.5, rev=0.35)
    play(tr, 'erhu', "6 1' 6 5 | 3/2 5/2 | 6 5 3 2 | 6,/4~", key=65, bar=44, pan=-0.15, rev=0.3)
    # drums
    big = lambda v: taiko(1.3, v)
    mid = lambda v: taiko(0.75, v)
    small = lambda v: hand_drum(260, 0.18, 0.5, v)
    main = 'X..x..x.X..x..x.'
    fill = 'X..x..x.X.xxX.XX'
    for b in list(range(0, 28)) + list(range(36, 47)):
        beats(tr, fill if b % 4 == 3 else main, big, b, gain=0.8, rev=0.2)
        if b >= 4:
            beats(tr, '....X.......X..x', mid, b, gain=0.5, pan=0.15, rev=0.2)
            beats(tr, '..o...o...o.o.oo', small, b, gain=0.3, pan=-0.3, rev=0.15)
    beats(tr, 'X.......X.......', big, 28, bars=8, gain=0.9, rev=0.3)
    beats(tr, 'x...x...x...x...', small, 28, bars=8, gain=0.25, pan=-0.3, rev=0.2)
    beats(tr, 'X.......X...X.X.', big, 47, gain=0.85, rev=0.2)
    beats(tr, 'x.x.x.x.xxxxXXXX', mid, 47, gain=0.7, cresc=0.6, rev=0.2)
    for b in (4, 12, 20, 24, 36, 44):
        tr.add_at(cymbal(1.0, b % 3), b, gain=0.28, pan=0.25, rev=0.3)
    beats(tr, '....x.......x...', lambda v: cymbal(0.5, v), 36, bars=8, gain=0.1, pan=0.35)
    for b in (28, 32):
        tr.add_at(gong(80, 5.0, -1.5, var=b), b, gain=0.45, rev=0.4)
    return tr


def m_boss() -> Track:
    """Boss fight: heavy double taiko, gongs, choir stabs, G minor with b2 tension, 148 bpm."""
    tr = Track('boss', 148, 48, rev=(2.4, 0.02, 0.7), lufs=-13.5)
    osA = [43, 43, 44, 43, 43, 43, 46, 44]
    osB = [43, 43, 44, 43, 49, 48, 46, 44]
    acc = (1.0, 0.55, 0.8, 0.55, 0.9, 0.55, 0.8, 0.6)
    ost = []
    for i, b in enumerate(list(range(0, 24)) + list(range(32, 48))):
        pat = osB if b % 4 == 3 else osA
        ost += [Note(b * 4 + j * 0.5, 0.5, m, acc[j]) for j, m in enumerate(pat)]
    play(tr, 'gehu', ost, bar=0, gain=0.6, rev=0.1)
    play(tr, 'gehu', "G2/8 Ab2/4 G2/4", key=58, bar=24, gain=0.55, rev=0.2)
    play(tr, 'gehu', "G1/8 G1/4 Ab1/2 G1/2", key=58, bar=28, gain=0.5, rev=0.2)
    ek = dict(key=58, pan=-0.15, rev=0.3)
    mel = ("G4/1.5 Bb4/0.5 C5 D5 | D5/0.5 C5/0.5 Bb4/0.5 C5/0.5 D5/2~ | F5 D5 C5/0.5 Bb4/0.5 Ab4 | G4/4~ | "
           "G5/1.5 F5/0.5 D5 F5 | G5/2~ Ab5 G5 | F5/0.5 D5/0.5 C5/0.5 D5/0.5 F5 D5 | G5/4~")
    play(tr, 'erhu', mel, bar=8, **ek)
    play(tr, 'erhu', "G4/4~ | Ab4/4~ | G4/2 F4/2 | D4/4~ | G4/4~ | Bb4/2 Ab4/2 | G4/2 F4/2 | G4/4v", bar=16, **ek)
    play(tr, 'pipa', "D5/4t | Eb5/4t | D5/2t C5/2t | D5/4t | D5/4t | Eb5/4t | F5/2t Eb5/2t | D5/4t",
         key=58, bar=16, pan=0.4, vel=0.6, rev=0.25)
    play(tr, 'erhu', mel, bar=32, **ek)
    play(tr, 'dizi', mel, key=70, bar=32, oct=1, pan=0.1, gain=0.45, rev=0.35)
    play(tr, 'erhu', "G5/1.5 F5/0.5 D5 F5 | G5/2~ Ab5 G5 | Bb5/2 Ab5/2 | G5/4~", bar=40, **ek)
    chords(tr, 'choir_o', [[55, 56, 62], [55, 56, 62]], 24, 16, gain=0.4, rev=0.6)
    tr.add_at(riser(tr.sec(8), 'boss-riser'), 30, gain=0.35, rev=0.3)
    tr.add_at(riser(tr.sec(4), 'boss-riser2'), 47, gain=0.3, rev=0.3)
    for b in range(24, 32):
        for beat in range(4):
            tr.add(heartbeat((b, beat)), tr.sec(b * 4 + beat), gain=0.55, rev=0.2)
    # choir stabs
    sA = stab((43, 50, 55, 56), 0.22, 'a')
    sB = stab((43, 50, 55, 58), 0.22, 'b')
    for b in range(0, 24, 2):
        tr.add_at(sA if b % 4 == 0 else sB, b, gain=0.55, rev=0.35)
        if b >= 8:
            tr.add_at(sB, b, 2.5, gain=0.45, rev=0.35)
    for b in range(32, 48, 2):
        for beat, s in ((0, sA), (1.5, sB), (3, sA)):
            tr.add_at(s, b, beat, gain=0.5, rev=0.35)
    # drums
    big = lambda v: taiko(1.4, v)
    mid = lambda v: taiko(0.9, v)
    small = lambda v: hand_drum(300, 0.15, 0.5, v)
    for b in list(range(0, 24)) + list(range(32, 47)):
        beats(tr, 'X..X..X.X.X.X.XX' if b % 8 == 7 else 'X..X..X.X.X.X...', big, b, gain=0.85, rev=0.2)
        beats(tr, '....X.......X.X.', mid, b, gain=0.55, pan=0.2, rev=0.2)
        if b >= 8:
            beats(tr, 'ooxoooxoooxoooxo', small, b, gain=0.28, pan=-0.3, rev=0.15)
    beats(tr, 'X.......X.......', big, 24, bars=8, gain=0.9, rev=0.35)
    beats(tr, 'X...X...X.x.XxXX', big, 47, gain=0.9, rev=0.2)
    beats(tr, 'xxxxxxxxxxxxXXXX', mid, 47, gain=0.7, cresc=0.7, rev=0.2)
    for b in (0, 8, 16, 32, 40):
        tr.add_at(cymbal(1.2, b % 3), b, gain=0.3, pan=-0.2, rev=0.3)
    for b in (0, 16, 24, 32):
        tr.add_at(gong(70, 6.0, -2.0, var=b), b, gain=0.5, rev=0.4)
    return tr


def m_tribulation() -> Track:
    """Heavenly tribulation finale: thunder, taiko ensemble, rising choir & erhu in C yu mode,
    resolving to a triumphant Eb gong-mode phrase that loops back into the storm, 120 bpm."""
    tr = Track('tribulation', 120, 44, rev=(3.0, 0.03, 0.75), lufs=-13.5)
    for b, g, p in ((0, 0.6, -0.3), (3, 0.4, 0.4), (12, 0.45, 0.2), (28, 0.5, -0.4), (36, 0.4, 0.3)):
        tr.add_at(thunder(5.0, ('trib', b)), b, gain=g, pan=p, rev=0.4)
    big = lambda v: taiko(1.4, v)
    mid = lambda v: taiko(0.85, v)
    small = lambda v: hand_drum(280, 0.16, 0.5, v)
    beats(tr, 'X.x.............', big, 0, bars=4, gain=0.8, rev=0.35)
    for b in range(4, 28):
        beats(tr, 'X...x.x.X...x.xx' if b % 4 == 3 else 'X...x.x.X...x.x.', big, b, gain=0.8, rev=0.25)
        beats(tr, '....X.......X...', mid, b, gain=0.5, pan=0.2, rev=0.2)
        if b >= 20:
            beats(tr, 'oxooxoxooxooxoxo', small, b, gain=0.3, pan=-0.3, rev=0.15)
    for b in range(28, 36):
        k = (b - 28) / 8
        beats(tr, 'X...X...X...X...', big, b, gain=0.7 + 0.25 * k, rev=0.3)
        beats(tr, 'xxxxxxxxxxxxxxxx' if b >= 32 else 'x.x.x.x.x.x.x.x.', small, b, gain=0.2 + 0.2 * k, pan=-0.2)
    for b in range(36, 43):
        beats(tr, 'X.......X...x.x.', big, b, gain=0.85, rev=0.3)
        beats(tr, '....X.......X...', mid, b, gain=0.5, pan=0.2, rev=0.25)
    beats(tr, 'X.......X.x.XxXX', big, 43, gain=0.85, cresc=0.4, rev=0.3)
    for b in (4, 12, 20, 24, 36, 40):
        tr.add_at(cymbal(1.2, b % 3), b, gain=0.3, pan=0.25, rev=0.35)
    tr.add_at(gong(65, 7.0, -1.5), 36, gain=0.6, rev=0.4)
    tr.add_at(gong(90, 5.0, -1.0, var=1), 20, gain=0.4, rev=0.4)
    # choir: low hum, rising progressions, ascent, triumph
    sc = Scale(51)   # 1 = Eb3 ; 6, = C3
    tri = lambda i: [sc(i), sc(i + 3), sc(i + 5)]
    chords(tr, 'choir_o', [tri(-1), tri(-1)], 0, 8, gain=0.3, rev=0.5)
    chords(tr, 'choir', [tri(i) for i in (-1, 0, 1, 2)], 12, 8, gain=0.34, rev=0.5)
    chords(tr, 'choir', [tri(i) for i in (3, -1, 3, -1)], 20, 8, gain=0.3, rev=0.5)
    chords(tr, 'choir', [tri(i) for i in (-1, 0, 1, 2, 3, 4, 5, 6)], 28, 4, gain=0.38, rev=0.5)
    chords(tr, 'choir', [[sc(i), sc(i + 2), sc(i + 3), sc(i + 5)] for i in (5, 4, 3, 5)], 36, 8, gain=0.4, rev=0.5)
    # erhu / dizi / pipa
    ek = dict(pan=-0.15, rev=0.35)
    theme = "6,/2 1 2 | 3/3~ 2 | 1 2 3 5 | 3/2 2/2~ | 6/2 5 3 | 5/3~ 3 | 2 3 1 6, | 6,/4~"
    play(tr, 'erhu', theme, key=63, bar=4, **ek)
    play(tr, 'erhu', theme, key=75, bar=12, **ek)
    play(tr, 'pipa', "6,/4t | 1/4t | 2/4t | 3/4t | 6,/4t | 1/4t | 2/4t | 6,/4t", key=63, bar=12, pan=0.4, vel=0.5)
    play(tr, 'dizi', "3 5 6/2 | 5 3 2/2 | 1 2 3 5 | 6/4~ | 1'/2 6 5 | 3/2 5/2 | 6 5 3 2 | 1/4~", key=75, bar=20,
         pan=0.15, gain=0.7, rev=0.4)
    play(tr, 'erhu', "6,/4~ | 1/4 | 2/4~ | 3/4 | 6/4~ | 5/4 | 3/2 5/2 | 6,/4~", key=63, bar=20, **ek)
    play(tr, 'erhu', "6,/2 1/2 | 2/2 3/2 | 5/2 6/2 | 1'/4~ | 2'/2 3'/2 | 5'/4~ | 3'/2 5'/2 | 6'/4~", key=63, bar=28, **ek)
    triumph = "1/1.5 2/0.5 3 5 | 6/2 5/2 | 3 5 6 1' | 2'/4~ | 3'/1.5 2'/0.5 1' 6 | 5 6 1'/2 | 1'/4~"
    play(tr, 'dizi', triumph, key=75, bar=36, pan=0.1, gain=0.8, rev=0.4)
    play(tr, 'erhu', triumph, key=63, bar=36, **ek)
    zs = Scale(75)
    for j, i in enumerate((0, 2, 3, 5, 7, 8)):
        tr.add(bell(float(hz(zs(i))), 3.5, 'zhong', j), tr.sec(42 * 4 + j * 0.5), pan=-0.5 + 0.2 * j, gain=0.25, rev=0.5)
    gliss(tr, 'zheng', Scale(63), -5, 12, 36, vel=0.8, pan=-0.35, rev=0.35)
    return tr


def m_victory() -> Track:
    """Short triumphant jingle (non-looping): taiko, gong, dizi/erhu fanfare, zheng glissando, bells."""
    tr = Track('victory', 100, 4, loop=False, tail=3.2, rev=(3.0, 0.03, 0.8), lufs=-14.0)
    sc = Scale(62)
    fan = "5,/0.5 1/0.5 2/0.5 3/0.5 5 3/0.5 5/0.5 | 6 1' 6/0.5 5/0.5 3 | 5/1.5 6/0.5 1' 2' | 1'/4~"
    play(tr, 'dizi', fan, key=74, pan=0.12, rev=0.35)
    play(tr, 'erhu', fan, key=62, pan=-0.15, rev=0.35, gain=0.8)
    pads(tr, [[50, 57, 62, 66], [47, 54, 59, 62], [45, 52, 57, 64], [50, 57, 62, 66]], 0, 4, gain=0.3)
    gliss(tr, 'zheng', sc, -5, 10, 0, vel=0.8, pan=-0.35)
    gliss(tr, 'zheng', sc, -5, 12, 3, vel=0.9, pan=-0.35)
    big = lambda v: taiko(1.2, v)
    beats(tr, 'X.......x...X.x.', big, 0, gain=0.8)
    beats(tr, 'X.......X.......', big, 1, gain=0.7)
    beats(tr, 'X.......X.x.XXXX', big, 2, gain=0.75, cresc=0.3)
    beats(tr, 'X...............', big, 3, gain=1.0)
    tr.add_at(gong(98, 6.0, -0.5), 0, gain=0.35, rev=0.4)
    tr.add_at(gong(98, 6.0, -0.5, var=1), 3, gain=0.5, rev=0.4)
    tr.add_at(cymbal(1.1), 3, gain=0.3, rev=0.4)
    for j, i in enumerate((5, 7, 8, 10)):
        tr.add(bell(float(hz(sc(i))), 3.5, 'zhong', j), tr.sec(12 + 0.5 * j), pan=-0.4 + 0.25 * j, gain=0.3, rev=0.5)
    return tr


def m_sorrow() -> Track:
    """Melancholic erhu solo in E yu mode over soft guzheng and pad, xiao echo, 54 bpm."""
    tr = Track('sorrow', 54, 20, rev=(3.4, 0.035, 0.6), lufs=-17.0)
    sc = Scale(55)
    roots = [-1, 0, -2, -1, -1, 1, 0, -1, -2, -1]
    pads(tr, [[sc(r - 5), sc(r - 2), sc(r)] for r in roots], 0, 8, gain=0.3, bright=900, att=2.0, rel=2.5)
    arp(tr, 'zheng', sc, [r for r in roots for _ in (0, 1)], 0, (0, 3, 5, 7, None, 5, 3, None),
        step=0.5, base=-5, vel=0.3, pan=-0.35, rev=0.4)
    play(tr, 'erhu', "6,/2 1 2 | s3/3~ 2/0.5 3/0.5 | 5/1.5 3/0.5 2 1 | 2/4~ | 3/1.5 5/0.5 6 5/0.5 3/0.5 | "
                     "2/2 1 6, | 1 2 3/0.5 2/0.5 1 | 6,/4~ | 6/2 5 6 | s1'/3~ 6 | 5 6/0.5 5/0.5 3 2 | 3/4~ | "
                     "5/1.5 6/0.5 3 2 | 1/2 2 3 | 2/1.5 1/0.5 6, 5, | 6,/4v", key=67, bar=2, pan=-0.05, rev=0.45)
    play(tr, 'xiao', "3/2 2 1 | 6,/4~", key=67, bar=18, pan=0.3, rev=0.5, gain=0.6)
    tr.add_at(bell(float(hz(52)), 6.0, 'temple'), 0, gain=0.18, rev=0.6)
    return tr


MUSIC = {
    'title': m_title, 'sect': m_sect, 'forest': m_forest, 'town': m_town, 'abyss': m_abyss, 'sky': m_sky,
    'battle': m_battle, 'boss': m_boss, 'tribulation': m_tribulation, 'victory': m_victory, 'sorrow': m_sorrow,
}


# =============================================================================
# Sound effects (mono)
# =============================================================================


def _n(sec):
    return ns(sec), tvec(ns(sec))


def place(buf: np.ndarray, x: np.ndarray, t: float, gain: float = 1.0) -> np.ndarray:
    i0 = ns(t)
    k = max(0, min(len(x), len(buf) - i0))
    buf[i0:i0 + k] += gain * np.asarray(x[:k], dtype=float)
    return buf


def room(x: np.ndarray, t60: float = 0.8, mix: float = 0.2, bright: float = 0.7) -> np.ndarray:
    """Small mono reverb for effects (tail extends the sound)."""
    ir = reverb_ir(t60, 0.01, bright)[0]
    wet = conv_linear(np.asarray(x, dtype=float), ir)
    return np.pad(x, (0, len(wet) - len(x))) + mix * wet


def room_cyclic(x: np.ndarray, t60: float, mix: float) -> np.ndarray:
    ir = reverb_ir(t60, 0.01, 0.6)[0]
    wet = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir, n=len(x)), n=len(x))
    return x + mix * wet


def whoosh(dur, f0, f1, q=2.0, key='w', peak_at=0.5) -> np.ndarray:
    n, t = _n(dur)
    x = np.linspace(0, 1, n)
    env = np.where(x < peak_at, (x / peak_at) ** 2, ((1 - x) / (1 - peak_at)) ** 1.5)
    fc = f0 * (f1 / f0) ** x
    return sweep(rng('whoosh', key).standard_normal(n), 'bp', fc, q) * env


def metal(f0, ratios, dur, t60s, key, amps=None) -> np.ndarray:
    """Struck metal: inharmonic partials with individual decays."""
    r = rng('metal', key)
    n, t = _n(dur)
    amps = amps or [1.0 / (1 + 0.5 * i) for i in range(len(ratios))]
    return sum(a * np.sin(TAU * f0 * rt * (1 + 0.004 * r.standard_normal()) * t + r.uniform(0, TAU)) * decay(n, d)
               for rt, a, d in zip(ratios, amps, t60s))


def growl(dur, f0, key, rough=0.6, vowel='o', jitter=0.08) -> np.ndarray:
    """Animal growl: jittery low sawtooth with rough AM through vowel formants."""
    r = rng('growl', key)
    n, t = _n(dur)
    f = f0 * (1 + jitter * lfo_noise(n, 6, r))
    am = 1 + rough * lfo_noise(n, 35, r)
    y = formant(saw(f) * np.clip(am, 0, None), vowel) + 0.3 * lp(r.standard_normal(n), 1500) * np.clip(am, 0, None)
    return y


def sfx_sword_swing():
    y = whoosh(0.34, 500, 3200, 2.2, 'swing', 0.45)
    y = y / (np.max(np.abs(y)) + 1e-9)
    n, t = _n(0.34)
    y += 0.05 * np.sin(TAU * np.cumsum(1500 + 1800 * np.linspace(0, 1, n)) / SR) * hump(n, 0.1, 0.2)
    return room(y, 0.4, 0.1)


def sfx_sword_hit():
    n, t = _n(0.8)
    r = rng('swordhit')
    y = metal(1250, (1, 2.32, 3.87, 5.1, 6.8, 8.3), 0.8, (0.6, 0.45, 0.3, 0.22, 0.15, 0.1), 'sh')
    y += 1.2 * hp(r.standard_normal(n), 2000) * np.exp(-t / 0.006)
    place(y, thump(140, 0.12), 0, 0.8)
    return room(y, 0.5, 0.15)


def sfx_hit_flesh():
    n, t = _n(0.3)
    r = rng('flesh')
    y = place(np.zeros(n), thump(95, 0.15), 0)
    y += 0.6 * lp(r.standard_normal(n), 900) * np.exp(-t / 0.04)
    y += 0.3 * bp(r.standard_normal(n), 800, 2500) * np.exp(-t / 0.015) * (1 + np.sin(TAU * 60 * t))
    return y


def sfx_hit_stone():
    n, t = _n(0.5)
    r = rng('stone')
    y = place(np.zeros(n), thump(120, 0.12), 0)
    for i in range(7):
        k = ns(r.uniform(0.008, 0.02))
        g = bp(r.standard_normal(k), r.uniform(900, 2000), r.uniform(2500, 5000)) * np.exp(-np.arange(k) / (0.004 * SR))
        place(y, g, r.uniform(0, 0.06), r.uniform(0.5, 1.0))
    y += 0.3 * lp(r.standard_normal(n), 600) * np.exp(-t / 0.12)
    return room(y, 0.5, 0.15)


def sfx_qi_charge():
    n, t = _n(1.6)
    r = rng('qicharge')
    x = t / 1.6
    f = 180 * 2 ** (2.2 * x)
    tone = saw(f) + saw(f * 1.007) + 2 * np.sin(TAU * np.cumsum(f) / SR)
    tone = lp(tone, 2500) * (0.7 + 0.3 * np.sin(TAU * np.cumsum(6 + 16 * x) / SR))
    swirl = sweep(r.standard_normal(n), 'bp', 400 * (12 ** x), 4.0)
    y = (0.25 * tone / 3 + 0.5 * swirl / (np.std(swirl) * 4)) * x ** 1.5
    for i in range(18):
        tt = 1.6 * (1 - (r.random() ** 2))
        place(y, bell(float(r.uniform(1800, 4200)), 0.6, 'chime', i % 3), tt, 0.08 * (tt / 1.6))
    return fade_out(y, 0.05)


def sfx_qi_blast():
    pre = whoosh(0.3, 300, 3000, 3.0, 'qib-pre', 0.95)
    pre /= np.max(np.abs(pre)) + 1e-9
    n, t = _n(1.5)
    r = rng('qiblast')
    y = place(np.zeros(n), 0.5 * pre, 0)
    t2 = np.clip(t - 0.28, 0, None)
    on = (t >= 0.28)
    boom = np.sin(TAU * np.cumsum(35 + 60 * np.exp(-t2 / 0.08)) / SR) * decay(n, 0.7) * on
    burst = sweep(r.standard_normal(n), 'lp', 300 + 7000 * np.exp(-t2 / 0.12), 0.9) * np.exp(-t2 / 0.25) * on
    y += 0.9 * boom + 0.8 * burst / (np.std(burst[on]) * 3)
    for i in range(10):
        place(y, bell(float(r.uniform(2000, 5000)), 0.8, 'chime', i % 3), 0.3 + r.uniform(0, 0.5), 0.06)
    return room(np.tanh(1.5 * y), 0.8, 0.2)


def sfx_player_hurt():
    n, t = _n(0.45)
    r = rng('hurt')
    y = place(np.zeros(n), thump(80, 0.15), 0, 0.8)
    f = (380 - 150 * t / 0.45) * (1 + 0.03 * np.sin(TAU * 28 * t))
    tone = filt(saw(f), 'bp', 900, 1.5) * hump(n, 0.01, 0.2) * decay(n, 0.5)
    y += 0.8 * tone / (np.max(np.abs(tone)) + 1e-9)
    y += 0.3 * bp(r.standard_normal(n), 500, 3000) * np.exp(-t / 0.02)
    return y


def sfx_enemy_death():
    n, t = _n(1.4)
    r = rng('death')
    y = place(np.zeros(n), thump(65, 0.6), 0)
    f = 300 * 2 ** (-2 * t / 1.4)
    dark = lp(saw(f) + saw(f * 1.5) + saw(f * 0.749), 1200) * hump(n, 0.02, 0.6)
    y += 0.25 * dark
    disp = sweep(r.standard_normal(n), 'bp', 6000 * 2 ** (-3 * t / 1.4), 2.0) * hump(n, 0.1, 0.8)
    y += 0.4 * disp / (np.std(disp) * 3)
    for i in range(12):
        place(y, bell(float(r.uniform(1500, 4000)), 0.7, 'chime', i % 3), r.uniform(0.1, 0.9), 0.05)
    return room(y, 1.0, 0.25)


def sfx_block():
    n, t = _n(0.45)
    r = rng('block')
    y = 0.7 * metal(1450, (1, 2.13, 3.3, 4.7), 0.45, (0.3, 0.2, 0.12, 0.08), 'blk')
    place(y, woodblock(180, 0, 0.1), 0, 0.6)
    y += 0.8 * bp(r.standard_normal(n), 1500, 8000) * np.exp(-t / 0.005)
    return room(y, 0.4, 0.12)


def sfx_footstep_stone():
    n, t = _n(0.15)
    r = rng('fstone')
    y = place(np.zeros(n), thump(90, 0.05), 0, 0.7)
    y += 0.6 * hp(r.standard_normal(n), 2000) * np.exp(-t / 0.003)
    y += 0.35 * bp(r.standard_normal(n), 1200, 3500) * np.exp(-t / 0.02)
    return y


def sfx_footstep_grass():
    n, t = _n(0.22)
    r = rng('fgrass')
    y = place(np.zeros(n), thump(70, 0.06), 0, 0.4)
    for i in range(6):
        k = ns(r.uniform(0.015, 0.035))
        g = hp(r.standard_normal(k), 2500) * np.sin(np.linspace(0, np.pi, k)) ** 2
        place(y, g, r.uniform(0, 0.09), r.uniform(0.3, 0.7))
    return y


def sfx_jump():
    y = whoosh(0.28, 250, 1400, 1.5, 'jump', 0.35)
    y = y / (np.max(np.abs(y)) + 1e-9)
    n, t = _n(0.28)
    y += 0.4 * lp(rng('jump2').standard_normal(n), 800) * np.exp(-t / 0.03) * (1 + np.sin(TAU * 40 * t))
    return y


def sfx_land():
    n, t = _n(0.35)
    r = rng('land')
    y = place(np.zeros(n), thump(75, 0.14), 0)
    y += 0.5 * lp(r.standard_normal(n), 500) * np.exp(-t / 0.08)
    y += 0.2 * bp(r.standard_normal(n), 1500, 4000) * np.exp(-t / 0.03)
    return y


def sfx_pickup():
    n, t = _n(0.8)
    y = np.zeros(n)
    for j, m in enumerate((88, 95, 100)):
        place(y, bell(float(hz(m)), 0.9, 'chime', j), 0.06 * j, 1.0 - 0.15 * j)
    y += 0.15 * hp(rng('pick').standard_normal(n), 6000) * np.exp(-t / 0.15) * (0.5 + 0.5 * np.sin(TAU * 30 * t))
    return room(y, 0.8, 0.2)


def sfx_quest_accept():
    y = lp(gong(220, 2.2, 0.3, 0.2), 4000)
    return room(fade_out(y * ramp(len(y), 0.01), 0.3), 1.0, 0.2)


def sfx_quest_complete():
    n, t = _n(2.4)
    y = np.zeros(n)
    for j, m in enumerate((72, 76, 79, 84, 88)):
        place(y, bell(float(hz(m)), 2.2, 'zhong', j), 0.09 * j, 0.8)
    place(y, bell(float(hz(96)), 1.5, 'chime', 1), 0.45, 0.4)
    return room(y, 1.2, 0.25)


def sfx_objective_update():
    n, t = _n(0.9)
    y = np.zeros(n)
    place(y, bell(float(hz(91)), 0.8, 'chime', 0), 0, 0.8)
    place(y, bell(float(hz(96)), 0.8, 'chime', 1), 0.1, 0.9)
    return room(y, 0.7, 0.2)


def sfx_breakthrough():
    n, t = _n(3.8)
    r = rng('break')
    y = np.zeros(n)
    rise = 2.3
    k = ns(rise)
    x = np.linspace(0, 1, k)
    f = 110 * 2 ** (2 * x)
    pad = sweep(saw(f) + saw(f * 1.5 * 1.003) + saw(f * 2.005), 'lp', 900 + 4000 * x) * x ** 2
    place(y, 0.18 * pad, 0)
    sw = sweep(r.standard_normal(k), 'bp', 300 * 20 ** x, 3.0) * x ** 2
    place(y, 0.3 * sw / (np.std(sw) * 3), 0)
    sc = Scale(76)
    for i in range(40):
        tt = rise * math.sqrt(r.random())
        idx = int(tt / rise * 12) + int(r.integers(0, 3))
        place(y, bell(float(hz(sc(idx))), 0.8, 'chime', i % 3), tt, 0.1 * (0.3 + tt / rise))
    place(y, gong(110, 3.0, -0.5, 0.3), rise, 0.9)
    place(y, bell(float(hz(69)), 2.5, 'zhong'), rise, 0.5)
    place(y, cymbal(1.0), rise, 0.35)
    place(y, taiko(1.3), rise, 0.6)
    return fade_out(room(y, 2.0, 0.25)[:n], 0.3)


def sfx_ui_click():
    y = woodblock(1800, 0, 0.02)
    n = ns(0.06)
    return np.pad(y, (0, max(0, n - len(y))))[:n]


def sfx_ui_hover():
    n, t = _n(0.05)
    return np.sin(TAU * 2600 * t) * decay(n, 0.04) * ramp(n, 0.002)


def sfx_ui_open():
    y = whoosh(0.3, 700, 3200, 2.0, 'uiopen', 0.6)
    y = 0.5 * y / (np.max(np.abs(y)) + 1e-9)
    place(y, bell(1318.5, 0.3, 'chime'), 0.12, 0.4)
    return y


def sfx_ui_close():
    y = whoosh(0.26, 3000, 700, 2.0, 'uiclose', 0.35)
    y = 0.5 * y / (np.max(np.abs(y)) + 1e-9)
    place(y, woodblock(900, 1, 0.03), 0.2, 0.3)
    return y


def sfx_dialogue_next():
    y = woodblock(650, 2, 0.04)
    return lp(y, 5000)


def sfx_typewriter():
    n, t = _n(0.03)
    r = rng('type')
    return hp(r.standard_normal(n), 2500) * np.exp(-t / 0.002) * 0.5 + np.sin(TAU * 2100 * t) * decay(n, 0.015)


def sfx_teleport():
    n, t = _n(2.0)
    r = rng('tele')
    x = t / 2.0
    fc = np.where(x < 0.55, 300 * 20 ** (x / 0.55), 6000 * (300 / 6000) ** ((x - 0.55) / 0.45))
    w = sweep(r.standard_normal(n), 'bp', fc, 3.0) * hump(n, 0.6, 0.8)
    y = flanger(0.5 * w / (np.std(w) * 3), 0.7, 0.005)
    sc = Scale(76)
    for i in range(24):
        tt = 0.05 + 1.1 * i / 24
        place(y, bell(float(hz(sc(i // 2))), 0.9, 'chime', i % 3), tt, 0.12)
    return fade_out(room(y, 1.2, 0.3)[:n], 0.2)


def sfx_meditate_loop():
    """6 s loop: soft drone + singing-bowl hum + breathing noise (all periodic in 6 s)."""
    n, t = _n(6.0)
    r = rng('medit')
    y = np.zeros(n)
    for fr, a in ((98.0, 1.0), (98 + 1 / 6, 0.8), (147.0, 0.5), (196.0, 0.3), (294.0, 0.12), (523.0 + 1 / 3, 0.06)):
        y += a * np.sin(TAU * fr * t + r.uniform(0, TAU))
    y *= 0.8 + 0.2 * np.sin(TAU * t / 6.0)
    inhale = np.clip(np.sin(TAU * t / 6.0), 0, None) ** 1.5
    exhale = np.clip(-np.sin(TAU * t / 6.0), 0, None) ** 1.5
    y += 1.2 * periodic_noise(n, r, 600, 2500, -3) * inhale + 1.2 * periodic_noise(n, r, 250, 1200, -3) * exhale
    return room_cyclic(y, 2.0, 0.3)


def sfx_wind_loop():
    n, t = _n(8.0)
    r = rng('windloop')
    base = periodic_noise(n, r, 120, 3000, tilt=-4)
    gust = 0.55 + 0.45 * periodic_lfo(n, r, (1, 2, 3, 4))
    wh = cyc(lambda z: sweep(z, 'bp', np.resize(700 + 400 * periodic_lfo(n, r, (1, 2)), len(z)), 8.0),
             periodic_noise(n, r, 200, 4000), ns(1.0))
    return base * gust + 0.8 * wh * np.clip(gust - 0.5, 0, None) * 2


def sfx_fire_loop():
    n, t = _n(4.0)
    r = rng('fire')
    roar = periodic_noise(n, r, 40, 500, -3) * (0.7 + 0.3 * periodic_lfo(n, r, (3, 5, 8, 13)))
    hiss = 0.15 * periodic_noise(n, r, 3000, 9000) * (0.6 + 0.4 * periodic_lfo(n, r, (7, 11)))
    y = roar + hiss
    for i in range(45):
        k = ns(r.uniform(0.002, 0.012))
        pop = bp(r.standard_normal(k + 40), r.uniform(800, 2500), 8000)[:k] * np.exp(-np.arange(k) / (0.002 * SR))
        i0 = int(r.integers(0, n))
        idx = (i0 + np.arange(k)) % n
        y[idx] += r.uniform(1.0, 4.0) * pop
    return y


def sfx_wolf_howl():
    n, t = _n(2.6)
    r = rng('howl')
    cont = np.interp(t, (0, 0.45, 1.5, 1.9, 2.5), (380, 620, 640, 600, 420))
    f = cont * (1 + 0.012 * np.sin(TAU * 5 * t) * np.clip((t - 0.5) / 0.3, 0, 1))
    ph = np.cumsum(f) / SR
    y = sum(a * np.sin(TAU * k * ph) for k, a in ((1, 1), (2, 0.45), (3, 0.2), (4, 0.08)))
    y = 0.6 * y + 0.4 * filt(y, 'bp', 750, 2.0) * 3
    y += 0.08 * bp(r.standard_normal(n), 800, 2500)
    return room(y * hump(n, 0.25, 0.45), 2.0, 0.35)


def sfx_wolf_growl():
    n, t = _n(1.3)
    y = growl(1.3, 80, 'wg', 0.8) * hump(n, 0.2, 0.3)
    return room(y, 0.5, 0.1)


def sfx_wolf_attack():
    n, t = _n(0.7)
    r = rng('wa')
    y = np.zeros(n)
    place(y, growl(0.35, 110, 'wa1', 1.0) * hump(ns(0.35), 0.1, 0.05), 0, 0.6)
    k = ns(0.14)
    f = np.linspace(260, 170, k)
    bark = formant(saw(f), 'a') * hump(k, 0.005, 0.08)
    place(y, bark / (np.max(np.abs(bark)) + 1e-9), 0.22, 1.0)
    for dt in (0.42, 0.435):
        place(y, hp(r.standard_normal(ns(0.01)), 3000) * np.exp(-np.arange(ns(0.01)) / (0.002 * SR)), dt, 0.9)
    place(y, whoosh(0.2, 400, 1500, 1.5, 'wa-w', 0.6), 0.25, 0.1)
    return room(y, 0.5, 0.12)


def sfx_serpent_roar():
    n, t = _n(2.2)
    r = rng('serp')
    hiss = hp(r.standard_normal(n), 3500) * (0.7 + 0.3 * lfo_noise(n, 20, r))
    roar = growl(2.2, 58, 'serp', 0.9, 'a', 0.15)
    env = hump(n, 0.25, 0.9)
    y = (0.35 * hiss + 0.8 * roar / (np.max(np.abs(roar)) + 1e-9)) * env
    return room(y, 1.5, 0.3)


def sfx_golem_rumble():
    n, t = _n(2.6)
    r = rng('golem')
    brown = hp(np.cumsum(r.standard_normal(n)), 15)
    y = lp(brown, 120, 4)
    y = y / np.max(np.abs(y)) * (0.7 + 0.3 * lfo_noise(n, 4, r))
    grind = bp(r.standard_normal(n), 300, 1200) * np.clip(lfo_noise(n, 12, r), 0, None) * 0.25
    y += grind + 0.4 * np.sin(TAU * 38 * t)
    for i in range(20):
        k = ns(0.01)
        place(y, hp(r.standard_normal(k), 1500) * np.exp(-np.arange(k) / (0.002 * SR)), r.uniform(0, 2.3), 0.3)
    return y * hump(n, 0.4, 0.8)


def sfx_golem_step():
    n, t = _n(0.9)
    r = rng('gstep')
    f = 32 + 30 * np.exp(-t / 0.05)
    y = np.sin(TAU * np.cumsum(f) / SR) * decay(n, 0.5)
    y += 0.6 * lp(r.standard_normal(n), 250) * np.exp(-t / 0.08)
    for i in range(10):
        k = ns(0.012)
        place(y, bp(r.standard_normal(k), 800, 4000) * np.exp(-np.arange(k) / (0.003 * SR)), r.uniform(0.03, 0.4), 0.2)
    return np.tanh(1.5 * y)


def sfx_demon_laugh_ish():
    n, t = _n(2.6)
    r = rng('demon')
    y = sum(saw(np.full(n, float(hz(m))) * (1 + 0.003 * lfo_noise(n, 0.5, rng('dm', m)))) for m in (33, 34, 40, 45))
    y = sweep(y, 'lp', 200 + 1400 * np.clip(t / 1.6, 0, 1) ** 2, 2.0)
    pulses = 0.45 + 0.55 * np.clip(np.sin(TAU * np.cumsum(np.interp(t, (0, 2.6), (3.5, 5.5))) / SR), 0, None) ** 2
    vox = formant(y, 'o') * 2 + formant(y, 'a') * np.clip((t - 1.0) / 1.2, 0, 1)
    rev_cym = np.asarray(cymbal(0.9), dtype=float)[:ns(1.8)][::-1]
    out = (0.7 * vox / (np.max(np.abs(vox)) + 1e-9)) * pulses * hump(n, 0.8, 0.6)
    place(out, 0.3 * rev_cym, 0.0)
    return room(out, 1.8, 0.35)


def sfx_thunder():
    return thunder(4.0, 'sfx')


def sfx_chest_open():
    n, t = _n(1.3)
    r = rng('chest')
    y = np.zeros(n)
    place(y, woodblock(1400, 3, 0.02), 0, 0.5)
    k = ns(0.6)
    f = np.linspace(140, 230, k) * (1 + 0.05 * lfo_noise(k, 20, r))
    stick = 0.5 + 0.5 * np.sign(np.sin(TAU * np.cumsum(np.full(k, 38.0) * (1 + 0.3 * lfo_noise(k, 5, r))) / SR))
    creak = formant(saw(f) * stick, 'a') * hump(k, 0.05, 0.1)
    place(y, 0.6 * creak / (np.max(np.abs(creak)) + 1e-9), 0.03)
    place(y, woodblock(160, 1, 0.12), 0.66, 0.9)
    place(y, thump(100, 0.1), 0.66, 0.5)
    for j, m in enumerate((84, 88, 91, 96)):
        place(y, bell(float(hz(m)), 0.7, 'chime', j), 0.75 + 0.07 * j, 0.25)
    return room(y, 0.7, 0.15)


def sfx_bell_toll():
    return fade_out(room(bell(98.0, 7.0, 'temple'), 2.5, 0.3)[:ns(7.0)], 0.5)


def sfx_drum_hit():
    return room(taiko(1.25), 1.2, 0.2)[:ns(1.8)]


def sfx_heartbeat():
    return np.pad(heartbeat('sfx'), (0, ns(0.25)))


def sfx_chapter_title():
    n = ns(3.2)
    y = np.zeros(n)
    place(y, taiko(1.4), 0, 1.0)
    place(y, gong(80, 3.2, -1.0), 0.0, 0.8)
    place(y, cymbal(1.2), 0.0, 0.2)
    place(y, taiko(1.1, 2), 0.18, 0.5)
    return fade_out(room(y, 2.0, 0.25)[:n], 0.4)


def sfx_gameover():
    n, t = _n(4.0)
    y = np.zeros(n)
    place(y, gong(60, 4.0, -1.5), 0, 0.9)
    f = 440 * 2 ** (-2 * np.clip(t / 3.2, 0, 1))
    tone = lp(filt(saw(f), 'peak', 1000, 2.0, 5), 2500) * hump(n, 0.3, 1.2)
    y += 0.35 * tone / (np.max(np.abs(tone)) + 1e-9)
    return fade_out(room(y, 2.0, 0.3)[:n], 0.4)


# id -> (function, peak dBFS, is_loop)
SFX = {
    'sword_swing': (sfx_sword_swing, -1.0, False), 'sword_hit': (sfx_sword_hit, -1.0, False),
    'hit_flesh': (sfx_hit_flesh, -1.0, False), 'hit_stone': (sfx_hit_stone, -1.0, False),
    'qi_blast': (sfx_qi_blast, -1.0, False), 'qi_charge': (sfx_qi_charge, -2.0, False),
    'player_hurt': (sfx_player_hurt, -1.0, False), 'enemy_death': (sfx_enemy_death, -1.0, False),
    'block': (sfx_block, -1.0, False), 'footstep_stone': (sfx_footstep_stone, -6.0, False),
    'footstep_grass': (sfx_footstep_grass, -6.0, False), 'jump': (sfx_jump, -4.0, False),
    'land': (sfx_land, -3.0, False), 'pickup': (sfx_pickup, -2.0, False),
    'quest_accept': (sfx_quest_accept, -2.0, False), 'quest_complete': (sfx_quest_complete, -1.0, False),
    'objective_update': (sfx_objective_update, -3.0, False), 'breakthrough': (sfx_breakthrough, -1.0, False),
    'ui_click': (sfx_ui_click, -6.0, False), 'ui_hover': (sfx_ui_hover, -12.0, False),
    'ui_open': (sfx_ui_open, -6.0, False), 'ui_close': (sfx_ui_close, -6.0, False),
    'dialogue_next': (sfx_dialogue_next, -8.0, False), 'typewriter': (sfx_typewriter, -14.0, False),
    'teleport': (sfx_teleport, -1.0, False), 'meditate_loop': (sfx_meditate_loop, -6.0, True),
    'wolf_howl': (sfx_wolf_howl, -1.0, False), 'wolf_growl': (sfx_wolf_growl, -1.0, False),
    'wolf_attack': (sfx_wolf_attack, -1.0, False), 'serpent_roar': (sfx_serpent_roar, -1.0, False),
    'golem_rumble': (sfx_golem_rumble, -1.0, False), 'golem_step': (sfx_golem_step, -1.0, False),
    'demon_laugh_ish': (sfx_demon_laugh_ish, -1.0, False), 'thunder': (sfx_thunder, -1.0, False),
    'wind_loop': (sfx_wind_loop, -6.0, True), 'fire_loop': (sfx_fire_loop, -6.0, True),
    'chest_open': (sfx_chest_open, -2.0, False), 'bell_toll': (sfx_bell_toll, -1.0, False),
    'drum_hit': (sfx_drum_hit, -1.0, False), 'heartbeat': (sfx_heartbeat, -2.0, False),
    'chapter_title': (sfx_chapter_title, -1.0, False), 'gameover': (sfx_gameover, -1.0, False),
}


# =============================================================================
# Rendering, verification, main
# =============================================================================


def trim_silence(y: np.ndarray, floor_db: float = -70.0) -> np.ndarray:
    """Drop the inaudible end of a one-shot and add a short fade."""
    a = np.abs(y)
    idx = np.nonzero(a > dbg(floor_db) * a.max())[0]
    end = min(len(y), (idx[-1] + ns(0.01)) if len(idx) else len(y))
    return fade_out(y[:end], min(0.02, end / SR / 4))


def write_ogg(path: str, data: np.ndarray, quality: float):
    """Write (channels, n) float audio as Ogg Vorbis.  Written in blocks: libsndfile 1.2
    segfaults when a single Vorbis write call is very large."""
    frames = np.ascontiguousarray(data.T, dtype=np.float32)
    with sf.SoundFile(path, 'w', SR, frames.shape[1], format='OGG', subtype='VORBIS',
                      compression_level=quality) as f:
        for i in range(0, len(frames), 32768):
            f.write(frames[i:i + 32768])


def render_one(kind: str, cid: str, out_dir: str) -> dict:
    """Synthesise one cue, write it, read it back and return verification stats."""
    t0 = time.time()
    if kind == 'music':
        tr = MUSIC[cid]()
        data = tr.render()
        loop = tr.loop
        path = os.path.join(out_dir, 'music', cid + '.ogg')
        q = MUSIC_QUALITY
    else:
        fn, peak_db, loop = SFX[cid]
        y = np.asarray(fn(), dtype=float)
        y = y - (np.mean(y) if loop else 0.0)
        if not loop:
            y = trim_silence(hp(y, 20))
        data = norm(y, dbg(peak_db))[None, :]
        path = os.path.join(out_dir, 'sfx', cid + '.ogg')
        q = SFX_QUALITY
    if not np.all(np.isfinite(data)):
        raise RuntimeError(f'{cid}: non-finite samples')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_ogg(path, data, q)
    for fn in (pluck, taiko, hand_drum, woodblock, cymbal, gong, bell, stab):
        fn.cache_clear()
    return verify(path, cid, kind, loop, data.shape[1] / SR, time.time() - t0)


def verify(path: str, cid: str, kind: str, loop: bool, want_dur: float, secs: float) -> dict:
    d, sr = sf.read(path, always_2d=True)
    peak = float(np.max(np.abs(d)))
    rms = float(np.sqrt(np.mean(d ** 2)))
    st = dict(id=cid, kind=kind, dur=len(d) / sr, want=want_dur, peak_db=20 * np.log10(peak + 1e-12),
              rms_db=20 * np.log10(rms + 1e-12), size=os.path.getsize(path), loop=loop, secs=secs,
              nan=bool(np.any(~np.isfinite(d))), lufs=loudness(d.T) if d.shape[0] > ns(0.5) else float('nan'))
    if loop:
        # Click test: curvature (2nd difference) of the samples straddling the wrap point vs. the
        # track's 99.9th percentile (a discontinuity would show up exactly there).
        w = 2
        x = np.concatenate([d[-w:], d[:w]])
        curv = np.abs(np.diff(d, 2, axis=0)).max(axis=1)
        w2 = ns(0.1)
        head = np.sqrt(np.mean(d[:w2] ** 2)) + 1e-9
        tail = np.sqrt(np.mean(d[-w2:] ** 2)) + 1e-9
        st.update(seam_jump=float(np.abs(np.diff(x, 2, axis=0)).max()), seam_ref=float(np.percentile(curv, 99.9)),
                  seam_db=20 * np.log10(head / tail))
    return st


def profile(path: str, parts: int = 10) -> str:
    d, _ = sf.read(path, always_2d=True)
    seg = np.array_split(d, parts)
    return ' '.join(f'{20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-9):5.1f}' for s in seg)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--only', default='', help='comma-separated cue ids (music and/or sfx)')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'godot', 'audio'))
    ap.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument('--verbose', action='store_true', help='print a loudness profile of every music track')
    a = ap.parse_args(argv)
    only = [s for s in a.only.split(',') if s]
    unknown = [s for s in only if s not in MUSIC and s not in SFX]
    if unknown:
        ap.error(f'unknown ids: {unknown}')
    jobs = [('music', c) for c in MUSIC if not only or c in only] + [('sfx', c) for c in SFX if not only or c in only]
    jobs.sort(key=lambda j: j[0] != 'music')      # long jobs first
    out = os.path.normpath(a.out)
    t0 = time.time()
    if a.jobs > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            stats = list(ex.map(render_one, *zip(*jobs), [out] * len(jobs)))
    else:
        stats = [render_one(k, c, out) for k, c in jobs]
    bad = 0
    print(f"{'id':18s} {'kind':5s} {'dur s':>7s} {'peak dB':>8s} {'rms dB':>7s} {'LUFS':>6s} {'size KB':>8s} "
          f"{'seam curv/ref99.9':>20s} {'t s':>5s}")
    for s in stats:
        seam = ''
        if s['loop']:
            ok = s['seam_jump'] <= s['seam_ref']
            seam = f"{'ok' if ok else 'CLICK'} {s['seam_jump']:.4f}/{s['seam_ref']:.4f}"
            bad += not ok
        flags = []
        if s['nan']:
            flags.append('NaN')
        if s['peak_db'] > -0.1:
            flags.append('CLIP?')
        if abs(s['dur'] - s['want']) > 0.01:
            flags.append(f"dur!={s['want']:.2f}")
        bad += len(flags)
        print(f"{s['id']:18s} {s['kind']:5s} {s['dur']:7.2f} {s['peak_db']:8.2f} {s['rms_db']:7.1f} {s['lufs']:6.1f} "
              f"{s['size'] / 1024:8.1f} {seam:>20s} {s['secs']:5.1f} {' '.join(flags)}")
        if a.verbose and s['kind'] == 'music':
            print('   profile dB:', profile(os.path.join(out, 'music', s['id'] + '.ogg')))
    for kind in ('music', 'sfx'):
        d = os.path.join(out, kind)
        if os.path.isdir(d):
            tot = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.endswith('.ogg'))
            print(f'total {kind}: {tot / 1024 / 1024:.2f} MB')
    print(f'done in {time.time() - t0:.1f} s, {bad} problem(s)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
