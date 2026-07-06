"""CP-2 IN-REGIME ambient measurement — the product regime (speaker-dependent gate + real ambient FA/hr).

Enroll one TORGO speaker's OWN words as the wake vocabulary; detection = their held-out reps
(leave-one-out); FA/hour = false fires when scanning real LibriSpeech/DEMAND background against those
templates. Open-set GATE semantics: a "fire" = min-distance to ANY enrolled template < threshold (Stage-1
wake gate; command identity is the downstream recognizer's job). Sweep threshold -> detection vs FA/hour.

Both arms (MFCC-DTW, WavLM-embedding-cosine) use IDENTICAL preprocessing: every template, positive, AND
background window is energy_vad_trim'd, then feature -> min-distance. (No per-arm asymmetry -> no EVAL-004
confound.) Window matched to a single word (1.5s) so background windows ~ template length.

Usage: python in_regime.py <arm> [speaker] [bg_minutes] [win_s] [hop_s]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

PV = os.path.expanduser("~/picovoice-benchmark")
arm = sys.argv[1] if len(sys.argv) > 1 else "mfcc"
SPK = sys.argv[2] if len(sys.argv) > 2 else "F01"
BG_MIN = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
WIN_S = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
HOP_S = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
SR, MIN_SPEECH, REFRACTORY_S = 16000, 1520, 1.0
ROOT = os.path.expanduser("~/torgo") if not SPK.startswith("FC") else os.path.expanduser("~/torgo/FCX")

if arm == "mfcc":
    fe = H.MfccFrontEnd()
    def feat(x): return fe(x) if x.size >= MIN_SPEECH else np.zeros((0, 1), np.float32)
    def dist(q, t): return H.dtw_distance(q, t)
elif arm.startswith("ssl:"):
    import torch; torch.set_num_threads(4)
    from transformers import AutoModel
    _, model, layer = arm.split(":")
    MODELS = {"wavlm": "microsoft/wavlm-base-plus", "hubert": "facebook/hubert-base-ls960",
              "distilhubert": "ntu-spml/distilhubert"}
    net = AutoModel.from_pretrained(MODELS.get(model, model), output_hidden_states=True).eval()
    torch.set_grad_enabled(False); L = int(layer)
    def feat(x):
        if x.size < MIN_SPEECH: return np.zeros((0, 1), np.float32)
        w = (x - x.mean()) / (x.std() + 1e-7)
        h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[L][0].numpy()
        v = h.mean(0); return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)[None, :]
    def dist(q, t): return 1.0 - float(q[0] @ t[0])
else:
    raise SystemExit("bad arm")


def read_full(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


# ---- enroll the speaker's own words ----
data = H.scan(ROOT)[SPK] if SPK in H.scan(ROOT) else None
if data is None:
    raise SystemExit(f"speaker {SPK} not found under {ROOT}")
utts = []  # (word, feature)
for word, wavs in data["commands"].items():
    for wpath in wavs:
        sp = H.energy_vad_trim(read_full(wpath))
        f = feat(sp)
        if f.shape[0] > 0:
            utts.append((word, f))
templates = [f for _, f in utts]
t0 = time.time()
print(f"[{arm}] {SPK}: {len(data['commands'])} words, {len(utts)} enrolled utts ({time.time()-t0:.0f}s)", flush=True)

# ---- detection: leave-one-out (a positive fires if min-dist to the OTHER templates < thr) ----
pos_scores = []
for i, (w, f) in enumerate(utts):
    others = [g for j, g in enumerate(templates) if j != i]
    pos_scores.append(min((dist(f, g) for g in others), default=math.inf))
print(f"[{arm}] {len(pos_scores)} positives scored ({time.time()-t0:.0f}s)", flush=True)

# ---- FA: scan real background (LibriSpeech) against ALL templates ----
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"), recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))
win, hop = int(WIN_S * SR), int(HOP_S * SR)
fa_scores = []          # (min_dist, global_time) for every background window
bg_sec = 0.0
tprev = 0.0
for bf in bg_files:
    if bg_sec / 60.0 >= BG_MIN:
        break
    x = read_full(bf)
    base = bg_sec
    for s in range(0, x.size - win + 1, hop):
        sp = H.energy_vad_trim(x[s:s + win])
        q = feat(sp)
        d = min((dist(q, t) for t in templates), default=math.inf) if q.shape[0] > 0 else math.inf
        fa_scores.append((d, base + (s + win / 2) / SR))
    bg_sec += x.size / SR
bg_hours = bg_sec / 3600.0
print(f"[{arm}] background {bg_hours:.2f} h ({len(fa_scores)} windows) scanned ({time.time()-t0:.0f}s)", flush=True)

# ---- sweep threshold -> detection vs FA/hour ----
cands = sorted({d for d, _ in fa_scores if math.isfinite(d)} | {p for p in pos_scores if math.isfinite(p)})
if len(cands) > 500:
    cands = [cands[i] for i in range(0, len(cands), len(cands) // 500)]

def evaluate(thr):
    det = sum(1 for p in pos_scores if p <= thr) / len(pos_scores) if pos_scores else 0.0
    fa = 0; last = -1e9
    for d, tc in fa_scores:
        if d <= thr and tc - last > REFRACTORY_S:
            fa += 1; last = tc
        elif d <= thr:
            last = tc
    return det, fa / bg_hours if bg_hours else 0.0

curve = [(evaluate(t), t) for t in cands]
print(f"\n[{arm}] {SPK} IN-REGIME: FRR (miss) at matched FA/hour on real ambient:", flush=True)
for target in [0.1, 0.5, 1.0, 5.0, 10.0]:
    best = max((c for c in curve if c[0][1] <= target), key=lambda c: c[0][0], default=None)
    if best:
        (det, fa), thr = best
        print(f"   FA/hr<= {target:5.1f}: FRR {(1-det)*100:5.1f}% (det {det*100:4.1f}%) @ FA/hr {fa:.2f}", flush=True)
    else:
        print(f"   FA/hr<= {target:5.1f}: (none)", flush=True)
d95 = min((c for c in curve if c[0][0] >= 0.95), key=lambda c: c[0][1], default=None)
print(f"   FA/hr to reach 95% detection (FRR<5%): {d95[0][1]:.1f}" if d95 else "   FRR<5% unreachable", flush=True)
print(f"[{arm}] done {time.time()-t0:.0f}s", flush=True)
