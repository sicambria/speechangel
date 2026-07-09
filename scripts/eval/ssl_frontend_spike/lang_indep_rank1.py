"""SOTA Domain 10 — language-independence DIAGNOSTIC (proves NO valid rank-1 proxy exists on this data).

## What this script establishes (and why D10 is argued from first principles, not measured)
SpeechAngel's language independence is an *architectural* property: the front-end is 13 MFCC + DTW
alignment (`core/dsp/.../MfccExtractor.kt`) with NO language model, lexicon, or phoneme layer — the exact
same code path for every language (Zhang 2014 language-independent DTW, PLOS ONE; corroborated by the same
MFCC-DTW family reaching 89.2% cross-speaker English rank-1 on the Picovoice benchmark, untuned). That
argument, not a table cell, is D10's basis — see `docs/product/2026-07-08_sota-domain-bands.md` §10.

This script is the DIAGNOSTIC that justifies taking the first-principles route: it demonstrates that
Common Voice (single-read distinct sentences, **no repeated command-words per speaker**) cannot support a
Domain-1-style rank-1. Two protocols were tried and both fail for the same first-principles reason — DTW
distance is only informative for *same-content* pairs:
  - augment-self-match (enroll clip, query an augmented copy of itself) → ~100% for every language: a
    tautology (audio fingerprinting), no discrimination.
  - cross-clip identification (below: enroll one word-window per clip, query a DIFFERENT window from the
    same clip, rank-1 = nearest template is own clip) → **chance** (~1/N_CLIPS) in every language,
    English anchor included.
Because the English anchor itself sits at chance, a cross-language Δ is a difference of two noise values —
uninformative. This is the null result, NOT "any measurable signal": it is therefore reported as a
diagnostic and does **NOT** emit a `domain10_value` that would feed a band. Its purpose is to make the
absence of a valid proxy verifiable and reproducible.

Usage: python lang_indep_rank1.py [--emit=<file>] [n_clips] [win_s]
  --emit appends a `#`-commented diagnostic line (SotaScorecard's metrics parser skips comments), so D10
  stays NOT_MEASURED-with-reason rather than being handed a band from noise.
"""
import os, sys, glob, math, time
import numpy as np
import harness as H

_EMIT = None
_argv = []
for _a in sys.argv[1:]:
    if _a.startswith("--emit="):
        _EMIT = _a.split("=", 1)[1]
    else:
        _argv.append(_a)
sys.argv = [sys.argv[0]] + _argv

CV = os.path.expanduser("~/picovoice-benchmark/common-voice")
LIBRI = os.path.expanduser("~/picovoice-benchmark/prepared/librispeech")
SR = 16000
N_CLIPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
WIN_S = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
MAX_Q_PER_CLIP = 3
MIN_SPEECH = 1520  # matches in_regime.py — a window must hold at least this many speech samples

# Non-English CV languages present as 16 kHz wav dirs (see `ls ~/picovoice-benchmark/common-voice`).
LANGUAGES = ["french", "german", "italian", "spanish", "portuguese", "dutch"]

fe = H.MfccFrontEnd()  # mirrors the shipped `none` config (13 MFCC, n_mel=26, DCT-II matches Kotlin)
t0 = time.time()


def read_wav16(path):
    import wave
    with wave.open(path, "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1:
            return None
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def clip_windows(x):
    """VAD-trim then split into non-overlapping word-length windows with enough speech."""
    sp = H.energy_vad_trim(x)
    win = int(WIN_S * SR)
    out = []
    for s in range(0, sp.size - win + 1, win):
        seg = sp[s:s + win]
        if seg.size >= MIN_SPEECH:
            f = fe(seg)
            if f.shape[0] > 0:
                out.append(f)
    return out


def rank1_for(files):
    """Cross-clip identification rank-1 over up to N_CLIPS clips."""
    templates = []  # (clip_id, feature) — one enroll window per clip
    queries = []    # (clip_id, feature) — other windows from the same clip
    cid = 0
    for path in files:
        if cid >= N_CLIPS:
            break
        x = read_wav16(path)
        if x is None:
            continue
        wins = clip_windows(x)
        if len(wins) < 2:
            continue  # need ≥1 enroll + ≥1 query window
        templates.append((cid, wins[0]))
        for q in wins[1:1 + MAX_Q_PER_CLIP]:
            queries.append((cid, q))
        cid += 1
    if not queries or len(templates) < 3:
        return None, len(templates), len(queries)
    hits = 0
    for qid, qf in queries:
        best_id, best_d = None, math.inf
        for tid, tf in templates:
            d = H.dtw_distance(qf, tf)
            if d < best_d:
                best_d, best_id = d, tid
        if best_id == qid:
            hits += 1
    return hits / len(queries), len(templates), len(queries)


# English anchor (LibriSpeech, same protocol).
en_files = sorted(glob.glob(os.path.join(LIBRI, "**", "*.wav"), recursive=True)) or \
    sorted(glob.glob(os.path.join(LIBRI, "*.wav")))
en_rank1, en_t, en_q = rank1_for(en_files)
print(f"[langindep] english anchor rank-1 {en_rank1*100 if en_rank1 else float('nan'):.1f}% "
      f"({en_t} clips, {en_q} queries) ({time.time()-t0:.0f}s)", flush=True)
if en_rank1 is None:
    raise SystemExit("english anchor unavailable")

# Each non-English language, same protocol.
deltas = []       # per-language pp delta = max(0, en - lang) * 100
per_lang = []     # (code, rank1, delta)
print(f"[langindep] {'lang':<12} {'rank-1':>8} {'Δ vs En (pp)':>14}", flush=True)
for lang in LANGUAGES:
    files = sorted(glob.glob(os.path.join(CV, lang, "*.wav")))
    if not files:
        continue
    r1, nt, nq = rank1_for(files)
    if r1 is None:
        continue
    delta = max(0.0, en_rank1 - r1) * 100.0
    deltas.append(delta)
    per_lang.append((lang, r1, delta))
    print(f"[langindep] {lang:<12} {r1*100:>7.1f}% {delta:>13.1f}", flush=True)

if len(deltas) < 1:
    raise SystemExit("no non-English languages measurable")

mean_delta = sum(deltas) / len(deltas)
print(f"[langindep] mean Δ over {len(deltas)} languages = {mean_delta:.1f} pp "
      f"(English anchor {en_rank1*100:.1f}%) ({time.time()-t0:.0f}s)", flush=True)

# Anchor-meaningfulness gate: rank-1 must clear ~2× chance to be a real signal. Below that, the whole
# metric is at the noise floor and a Δ is uninformative — we do NOT emit a band-feeding value.
chance = 1.0 / max(1, en_t)
anchor_meaningful = en_rank1 >= 2.0 * chance
if _EMIT:
    lang_summary = ", ".join(f"{c} {r*100:.0f}%" for c, r, _ in per_lang)
    with open(_EMIT, "a") as _f:
        # `#`-commented → SotaScorecard.readMetrics() skips it. Diagnostic record only, never a band.
        _f.write(
            f"# domain10 DIAGNOSTIC: cross-clip rank-1 English anchor {en_rank1*100:.1f}% "
            f"(chance {chance*100:.1f}%, {'ABOVE' if anchor_meaningful else 'AT NOISE FLOOR'}); "
            f"per-lang [{lang_summary}]; mean Δ {mean_delta:.1f} pp. "
            f"{'Uninformative — no valid rank-1 proxy on single-read CV; D10 argued by-construction (domain-bands §10).' if not anchor_meaningful else 'anchor above floor.'}\n"
        )
    print(f"[langindep] wrote diagnostic (anchor_meaningful={anchor_meaningful}) -> {_EMIT}", flush=True)
if not anchor_meaningful:
    print("[langindep] NULL RESULT: no above-chance rank-1 proxy exists on single-read CV data; "
          "D10 language-independence is argued by-construction (see domain-bands §10), not measured.", flush=True)
