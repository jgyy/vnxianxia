#!/usr/bin/env python3
"""Synthesise every voice line of godot/data/story.json with Piper TTS.

    python3 tools/gen_voices.py              # synthesise missing / stale files (resumable)
    python3 tools/gen_voices.py --check      # list missing / stale files, exit 1 if any (stdlib only)
    python3 tools/gen_voices.py --prune      # also delete .ogg files no longer referenced
    python3 tools/gen_voices.py --only q01   # restrict synthesis to keys starting with a prefix

Output: godot/audio/voice/<key>.ogg (mono Ogg Vorbis, 22050 Hz) and
godot/audio/voice/manifest.json, which records for every file the hash of
(spoken text, voice, processing settings), its subtitle and its duration.
A file is regenerated only when that hash changes, so an interrupted run
simply resumes.

Only lines with a "voice" path are synthesised: the 90 chapters added for the
2000-quest saga are text-only ("voice": null) and are skipped.

Gendered lines (spoken by the protagonist, or containing {player}-style
tokens) get two files, <key>_m.ogg and <key>_f.ogg. Casting lives in
tools/story/voices.py.

Synthesis needs piper-tts, numpy and soundfile. If they are not importable
the script re-executes itself with $PIPER_PYTHON (default
~/.venv313/bin/python, then /home/user/.venv313/bin/python). Voice models are
read from $PIPER_VOICES (default ~/voices, then /home/user/voices). --check needs only the standard library.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from story import voices as casting  # noqa: E402  (pure data, stdlib only)

STORY = os.path.join(ROOT, "godot", "data", "story.json")
VOICE_DIR = os.path.join(ROOT, "godot", "audio", "voice")
MANIFEST = os.path.join(VOICE_DIR, "manifest.json")


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return paths[-1]


MODELS_DIR = _first_existing(os.environ.get("PIPER_VOICES"), os.path.expanduser("~/voices"), "/home/user/voices")
PIPER_PYTHON = _first_existing(os.environ.get("PIPER_PYTHON"), os.path.expanduser("~/.venv313/bin/python"),
                               "/home/user/.venv313/bin/python")

SAMPLE_RATE = 22050
# Bump PROCESS_VERSION whenever the DSP chain below changes: every file is regenerated.
PROCESS_VERSION = 4
VORBIS_COMPRESSION = 0.93      # soundfile compression_level (~31 kbps for 22 kHz mono speech)
SENTENCE_GAP = 0.22            # seconds of silence between sentences
EDGE_SILENCE = 0.08            # seconds kept before/after speech
TARGET_RMS_DB = -18.0          # gated RMS of speech, roughly -16 LUFS for dialogue
PEAK_DB = -2.6                 # a little under -2 dBFS: Vorbis overshoots the ceiling slightly

TOKENS = {
    "m": {"player": "Lin Feng", "junior": "Junior Brother", "senior": "Senior Brother", "sibling": "brother",
          "they": "he", "them": "him", "their": "his"},
    "f": {"player": "Su Yue", "junior": "Junior Sister", "senior": "Senior Sister", "sibling": "sister",
          "they": "she", "them": "her", "their": "her"},
}
TOKEN_RE = re.compile(r"\{(\w+)\}")
PRONOUNCE = [(re.compile(r"\b%s\b" % re.escape(a)), b) for a, b in casting.PRONOUNCE]


# ------------------------------------------------------------------ jobs (stdlib)

def voice_for(speaker, variant):
    if speaker == "narrator":
        return casting.NARRATOR
    if speaker == "player":
        return casting.PLAYER_F if variant == "f" else casting.PLAYER_M
    return casting.NPC_VOICES[speaker]


def substitute(text, variant):
    if variant is None:
        return text
    return TOKEN_RE.sub(lambda m: TOKENS[variant].get(m.group(1), m.group(0)), text)


def spoken(text):
    for rx, repl in PRONOUNCE:
        text = rx.sub(repl, text)
    return text


def iter_story_lines(data):
    """Every voiced line. Lines of the chapters added for the 2000-quest saga are
    text-only ("voice": null) and are skipped: they need no synthesis."""
    for q in data["quests"]:
        for o in q["objectives"]:
            for ln in o.get("dialogue", []):
                if ln.get("voice"):
                    yield ln["speaker"], ln["text"], ln["voice"], ln["gendered"]
    for c in data["cinematics"].values():
        for s in c["shots"]:
            if s.get("voice"):
                yield s["speaker"], s["text"], s["voice"], s["gendered"]


def build_jobs(data):
    jobs = {}
    for speaker, text, voice_path, gendered in iter_story_lines(data):
        key = os.path.splitext(os.path.basename(voice_path))[0]
        for variant in (("m", "f") if gendered else (None,)):
            name = key + ("_" + variant if variant else "") + ".ogg"
            v = voice_for(speaker, variant)
            subtitle = substitute(text, variant)
            say = spoken(subtitle)
            h = hashlib.sha1(json.dumps({"text": say, "voice": v, "sr": SAMPLE_RATE, "proc": PROCESS_VERSION,
                                         "q": VORBIS_COMPRESSION}, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            jobs[name] = {"file": name, "speaker": speaker, "subtitle": subtitle, "say": say, "voice": v, "hash": h}
    return jobs


def load_manifest():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"version": 1, "files": {}}


def save_manifest(man):
    man["files"] = dict(sorted(man["files"].items()))
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def status(jobs, man):
    missing, stale = [], []
    for name, job in jobs.items():
        entry = man["files"].get(name)
        if not os.path.exists(os.path.join(VOICE_DIR, name)):
            missing.append(name)
        elif not entry or entry.get("hash") != job["hash"]:
            stale.append(name)
    on_disk = {f for f in os.listdir(VOICE_DIR) if f.endswith(".ogg")} if os.path.isdir(VOICE_DIR) else set()
    orphans = sorted(on_disk - set(jobs))
    return sorted(missing), sorted(stale), orphans


def folder_size():
    if not os.path.isdir(VOICE_DIR):
        return 0
    return sum(os.path.getsize(os.path.join(VOICE_DIR, f)) for f in os.listdir(VOICE_DIR))


# ------------------------------------------------------------------ synthesis (numpy / piper)

_VOICES = {}


def _load(model):
    import onnxruntime
    from piper import PiperVoice
    if model not in _VOICES:
        path = os.path.join(MODELS_DIR, model + ".onnx")
        voice = PiperVoice.load(path)
        # One intra-op thread per worker: these small VITS models run ~2x faster
        # single-threaded than with onnxruntime's default thread pool, and we
        # parallelise across worker processes instead.
        opts = onnxruntime.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        voice.session = onnxruntime.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])
        _VOICES[model] = voice
    return _VOICES[model]


def _resample(x, sr_in, sr_out):
    import numpy as np
    if sr_in == sr_out:
        return x
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _ir(seconds, rt60, seed, damp):
    """Deterministic exponentially decaying noise impulse response (a small room)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    ir = rng.standard_normal(n) * np.exp(-6.91 * t / rt60)
    k = max(1, int(damp))                       # moving average = cheap low-pass (darker tail)
    ir = np.convolve(ir, np.ones(k) / k, mode="same")
    ir[: int(0.004 * SAMPLE_RATE)] = 0          # pre-delay
    return ir / np.sqrt(np.sum(ir ** 2))


FX = {  # (ir length s, rt60 s, wet gain, damping taps)
    "room": (0.35, 0.30, 0.085, 3),
    "hall": (0.9, 0.85, 0.16, 4),
    "demon": (0.8, 0.70, 0.20, 6),
}


def _process(x, fx):
    import numpy as np
    # trim silence
    frame = int(0.01 * SAMPLE_RATE)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 1e-6:
        return np.zeros(int(0.3 * SAMPLE_RATE), dtype=np.float32)
    env = np.array([np.max(np.abs(x[i:i + frame])) for i in range(0, len(x), frame)])
    loud = np.nonzero(env > peak * 10 ** (-38 / 20))[0]
    a, b = loud[0] * frame, min(len(x), (loud[-1] + 1) * frame)
    pad = int(EDGE_SILENCE * SAMPLE_RATE)
    x = np.concatenate([np.zeros(pad), x[a:b], np.zeros(pad)]).astype(np.float64)
    # high-pass (remove DC / rumble): one-pole
    y = np.empty_like(x)
    prev_x = prev_y = 0.0
    r = 0.995
    for i in range(len(x)):  # noqa: small loop over one line is fine
        prev_y = x[i] - prev_x + r * prev_y
        prev_x = x[i]
        y[i] = prev_y
    x = y
    # effects
    length, rt60, wet, damp = FX.get(fx, FX["room"])
    if fx == "demon":
        # slightly lower, slightly delayed double for an unsettling chorus
        dbl = _resample(x, SAMPLE_RATE, int(SAMPLE_RATE * 1.03))[: len(x)]
        d = int(0.014 * SAMPLE_RATE)
        dbl = np.concatenate([np.zeros(d), dbl])[: len(x)]
        x = x + 0.38 * dbl
    ir = _ir(length, rt60, seed=7, damp=damp)
    n = len(x) + len(ir)
    tail = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    out = np.concatenate([x, np.zeros(len(ir))]) + wet * tail
    # cut the reverb tail once it has decayed
    env = np.abs(out)
    thr = np.max(env) * 10 ** (-50 / 20)
    last = np.nonzero(env > thr)[0][-1]
    out = out[: min(len(out), last + int(0.05 * SAMPLE_RATE))]
    # loudness: gated RMS of 20 ms frames
    f = int(0.02 * SAMPLE_RATE)
    frames = out[: len(out) // f * f].reshape(-1, f)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    gate = rms > np.max(rms) * 10 ** (-30 / 20)
    level = np.sqrt(np.mean(frames[gate] ** 2)) if np.any(gate) else np.max(rms)
    out = out * (10 ** (TARGET_RMS_DB / 20) / max(level, 1e-9))
    # soft limiter to the peak ceiling
    ceil = 10 ** (PEAK_DB / 20)
    knee = ceil * 0.7
    mag = np.abs(out)
    over = mag > knee
    out[over] = np.sign(out[over]) * (knee + (ceil - knee) * np.tanh((mag[over] - knee) / (ceil - knee)))
    # fades
    fade = int(0.01 * SAMPLE_RATE)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def synth_job(job):
    import numpy as np
    import soundfile as sf
    from piper import SynthesisConfig
    v = job["voice"]
    voice = _load(v["model"])
    cfg = SynthesisConfig(speaker_id=v["speaker"], length_scale=v["length_scale"],
                          noise_scale=v["noise_scale"], noise_w_scale=v["noise_w"])
    parts = []
    sr = voice.config.sample_rate
    for chunk in voice.synthesize(job["say"], syn_config=cfg):
        if parts:
            parts.append(np.zeros(int(SENTENCE_GAP * sr), dtype=np.float32))
        parts.append(chunk.audio_float_array.astype(np.float32))
        sr = chunk.sample_rate
    x = np.concatenate(parts) if parts else np.zeros(sr // 4, dtype=np.float32)
    x = _resample(x, sr, SAMPLE_RATE)
    y = _process(x, v.get("fx", "room"))
    path = os.path.join(VOICE_DIR, job["file"])
    tmp = path + ".part"  # not an audio extension, so the Godot importer ignores half-written files
    sf.write(tmp, y, SAMPLE_RATE, format="OGG", subtype="VORBIS", compression_level=VORBIS_COMPRESSION)
    os.replace(tmp, path)
    return job["file"], round(len(y) / SAMPLE_RATE, 2)


def _init_worker():
    # keep onnxruntime from oversubscribing the cores when several workers run
    os.environ.setdefault("OMP_NUM_THREADS", "1")


def ensure_synth_python():
    try:
        import numpy  # noqa: F401
        import piper  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError:
        if os.path.exists(PIPER_PYTHON) and os.path.realpath(sys.executable) != os.path.realpath(PIPER_PYTHON):
            os.execv(PIPER_PYTHON, [PIPER_PYTHON] + sys.argv)
        sys.exit("gen_voices: piper-tts, numpy and soundfile are required (set PIPER_PYTHON to a venv that has them)")


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report missing/stale files (exit 1 if any)")
    ap.add_argument("--prune", action="store_true", help="delete .ogg files that no line references")
    ap.add_argument("--only", default="", help="only synthesise files whose name starts with this prefix")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="synthesise at most N files (for testing)")
    args = ap.parse_args()

    with open(STORY, encoding="utf-8") as f:
        data = json.load(f)
    jobs = build_jobs(data)
    man = load_manifest()
    missing, stale, orphans = status(jobs, man)

    if args.check:
        for name in missing:
            print("missing: " + name)
        for name in stale:
            print("stale:   " + name)
        for name in orphans:
            print("orphan:  " + name + " (not referenced; run with --prune)", file=sys.stderr)
        mb = folder_size() / 1e6
        print("gen_voices: %d voice files expected, %d missing, %d stale, %d orphaned, folder %.1f MB"
              % (len(jobs), len(missing), len(stale), len(orphans), mb))
        return 1 if (missing or stale) else 0

    ensure_synth_python()
    os.makedirs(VOICE_DIR, exist_ok=True)
    if args.prune:
        for name in orphans:
            os.remove(os.path.join(VOICE_DIR, name))
            man["files"].pop(name, None)
            print("pruned " + name)
    for name in list(man["files"]):
        if name not in jobs:
            man["files"].pop(name)
    todo = [jobs[n] for n in missing + stale if n.startswith(args.only)]
    todo.sort(key=lambda j: (j["voice"]["model"], j["voice"]["speaker"] or 0, j["file"]))
    if args.limit:
        todo = todo[: args.limit]
    print("gen_voices: %d files to synthesise (%d total)" % (len(todo), len(jobs)), flush=True)
    t0 = time.time()
    done = 0

    def record(name, dur):
        j = jobs[name]
        man["files"][name] = {"hash": j["hash"], "speaker": j["speaker"], "text": j["subtitle"], "duration": dur}

    if todo:
        if args.workers > 1:
            import multiprocessing as mp
            ctx = mp.get_context("spawn")
            with ctx.Pool(args.workers, initializer=_init_worker) as pool:
                for name, dur in pool.imap_unordered(synth_job, todo, chunksize=4):
                    record(name, dur)
                    done += 1
                    if done % 20 == 0 or done == len(todo):
                        save_manifest(man)
                        el = time.time() - t0
                        print("  %d/%d  %.0fs elapsed, ~%.0fs left" % (done, len(todo), el, el / done * (len(todo) - done)),
                              flush=True)
        else:
            for job in todo:
                name, dur = synth_job(job)
                record(name, dur)
                done += 1
                if done % 20 == 0 or done == len(todo):
                    save_manifest(man)
                    print("  %d/%d" % (done, len(todo)), flush=True)
    save_manifest(man)
    print("gen_voices: done in %.0fs, folder %.1f MB" % (time.time() - t0, folder_size() / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
