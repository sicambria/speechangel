"""CP-2 IN-REGIME paired significance — MFCC-DTW vs WavLM embedding, same speaker/background.

EVAL-003 confirmation for the in-regime spike. Runs BOTH arms in one process (identical enroll /
positive / background windows -> no confound), selects each arm's ~0-FA/hr operating threshold (max
detection at realized FA/hr <= target), builds the paired per-positive detection vectors, and reports:
  - the paired McNemar (continuity-corrected chi2, df=1) AND the exact two-sided binomial (right for
    the small discordant counts n=32 gives), on the discordant detected/missed pairs;
  - the tail summary (det@5FA/hr, FA/hr for 95% det) for both arms — the robust, low-variance signal.

The ~0-FA/hr point allows 0 background firings in ~1 h, so it is pinned by one nearest background
window x only ~32 positives: high-variance knife-edge. Headline the tail; report ~0-FA/hr WITH this test.

Usage: python inregime_paired.py [speaker] [bg_minutes] [ssl_arm]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

PV = os.path.expanduser("~/picovoice-benchmark")
SPK = sys.argv[1] if len(sys.argv) > 1 else "F01"
BG_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
SSL_ARM = sys.argv[3] if len(sys.argv) > 3 else "ssl:wavlm:12"
WIN_S, HOP_S = 1.5, 0.5
SR, MIN_SPEECH, REFRACTORY_S = 16000, 1520, 1.0
ROOT = os.path.expanduser("~/torgo") if not SPK.startswith("FC") else os.path.expanduser("~/torgo/FCX")

# ---- two arms ----
mfe = H.MfccFrontEnd()
def mfcc_feat(x): return mfe(x) if x.size >= MIN_SPEECH else np.zeros((0, 1), np.float32)
def mfcc_dist(q, t): return H.dtw_distance(q, t)

import torch; torch.set_num_threads(4)
from transformers import AutoModel
_, mname, layer = SSL_ARM.split(":")
MODELS = {"wavlm": "microsoft/wavlm-base-plus", "hubert": "facebook/hubert-base-ls960",
          "distilhubert": "ntu-spml/distilhubert"}
net = AutoModel.from_pretrained(MODELS.get(mname, mname), output_hidden_states=True).eval()
torch.set_grad_enabled(False); L = int(layer)
def ssl_feat(x):
    if x.size < MIN_SPEECH: return np.zeros((0, 1), np.float32)
    w = (x - x.mean()) / (x.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[L][0].numpy()
    v = h.mean(0); return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)[None, :]
def ssl_dist(q, t): return 1.0 - float(q[0] @ t[0])

ARMS = {"mfcc": (mfcc_feat, mfcc_dist), SSL_ARM: (ssl_feat, ssl_dist)}


def read_full(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


data = H.scan(ROOT).get(SPK)
if data is None:
    raise SystemExit(f"speaker {SPK} not found under {ROOT}")

# Trim once per utterance/window; feature per arm (shared VAD -> no asymmetry).
t0 = time.time()
enroll_trim = []
for word, wavs in data["commands"].items():
    for wpath in wavs:
        sp = H.energy_vad_trim(read_full(wpath))
        if sp.size >= MIN_SPEECH:
            enroll_trim.append(sp)
print(f"{SPK}: {len(data['commands'])} words, {len(enroll_trim)} enrolled trims ({time.time()-t0:.0f}s)", flush=True)

bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"), recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))
win, hop = int(WIN_S * SR), int(HOP_S * SR)
bg_trims, bg_times, bg_sec = [], [], 0.0
for bf in bg_files:
    if bg_sec / 60.0 >= BG_MIN: break
    x = read_full(bf); base = bg_sec
    for s in range(0, x.size - win + 1, hop):
        bg_trims.append(H.energy_vad_trim(x[s:s + win]))
        bg_times.append(base + (s + win / 2) / SR)
    bg_sec += x.size / SR
bg_hours = bg_sec / 3600.0
print(f"background {bg_hours:.2f} h ({len(bg_trims)} windows) ({time.time()-t0:.0f}s)", flush=True)


def arm_scores(feat, dist):
    templates = [f for f in (feat(sp) for sp in enroll_trim) if f.shape[0] > 0]
    pos = []  # leave-one-out
    for i, sp in enumerate(enroll_trim):
        f = feat(sp)
        if f.shape[0] == 0:
            pos.append(math.inf); continue
        others = [templates[j] for j in range(len(templates)) if j != i]
        pos.append(min((dist(f, g) for g in others), default=math.inf))
    fa = []
    for sp, tc in zip(bg_trims, bg_times):
        q = feat(sp)
        d = min((dist(q, t) for t in templates), default=math.inf) if q.shape[0] > 0 else math.inf
        fa.append((d, tc))
    return pos, fa


def op_threshold(pos, fa, target):
    cands = sorted({d for d, _ in fa if math.isfinite(d)} | {p for p in pos if math.isfinite(p)})
    if len(cands) > 500:
        cands = [cands[i] for i in range(0, len(cands), len(cands) // 500)]
    def far(thr):
        n = 0; last = -1e9
        for d, tc in fa:
            if d <= thr and tc - last > REFRACTORY_S:
                n += 1; last = tc
            elif d <= thr:
                last = tc
        return n / bg_hours if bg_hours else 0.0
    ok = [t for t in cands if far(t) <= target]
    return max(ok) if ok else -math.inf  # largest thr under budget = max detection


def det_vec(pos, thr): return [1 if p <= thr else 0 for p in pos]


def curve_points(pos, fa):
    cands = sorted({d for d, _ in fa if math.isfinite(d)} | {p for p in pos if math.isfinite(p)})
    if len(cands) > 500:
        cands = [cands[i] for i in range(0, len(cands), len(cands) // 500)]
    def ev(thr):
        det = sum(1 for p in pos if p <= thr) / len(pos)
        n = 0; last = -1e9
        for d, tc in fa:
            if d <= thr and tc - last > REFRACTORY_S:
                n += 1; last = tc
            elif d <= thr:
                last = tc
        return det, n / bg_hours if bg_hours else 0.0
    pts = [ev(t) for t in cands]
    det5 = max((d for d, f in pts if f <= 5.0), default=0.0)
    fa95 = min((f for d, f in pts if d >= 0.95), default=float("inf"))
    return det5, fa95


scores = {}
for name, (feat, dist) in ARMS.items():
    scores[name] = arm_scores(feat, dist)
    print(f"[{name}] scored ({time.time()-t0:.0f}s)", flush=True)

# ---- paired McNemar at each arm's ~0-FA/hr operating threshold ----
def binom_two_sided(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    # two-sided exact under p=0.5
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)

print(f"\n=== {SPK} paired in-regime, {bg_hours:.2f} h background, n={len(enroll_trim)} positives ===", flush=True)
names = list(ARMS)
for target in [0.1, 0.5]:
    thrs = {n: op_threshold(*scores[n], target) for n in names}
    vecs = {n: det_vec(scores[n][0], thrs[n]) for n in names}
    A, B = vecs[names[0]], vecs[names[1]]  # A=mfcc, B=ssl
    b = sum(1 for a, bb in zip(A, B) if a == 1 and bb == 0)  # mfcc det, ssl miss
    c = sum(1 for a, bb in zip(A, B) if a == 0 and bb == 1)  # mfcc miss, ssl det
    da, db = sum(A) / len(A), sum(B) / len(B)
    n = b + c
    chi2 = (abs(b - c) - 1) ** 2 / n if n else float("nan")
    p_chi = math.erfc(math.sqrt(chi2 / 2.0)) if n else 1.0
    p_bin = binom_two_sided(b, c)
    print(f"FA/hr<={target}: {names[0]} det {da*100:.1f}%  {names[1]} det {db*100:.1f}%  "
          f"| discordant b(mfcc-only)={b} c(ssl-only)={c}  McNemar chi2={chi2:.2f} p={p_chi:.3f}  "
          f"exact-binom p={p_bin:.3f}", flush=True)

print("\n--- tail (robust, low-variance) ---", flush=True)
for name in names:
    det5, fa95 = curve_points(*scores[name])
    print(f"[{name}] det@5FA/hr {det5*100:.1f}%   FA/hr for 95% det {fa95:.1f}", flush=True)
print(f"done {time.time()-t0:.0f}s", flush=True)
