"""CP-2 ambient measurement — does the WavLM embedding cut FA/hr vs MFCC-DTW on real background speech?

The binding always-on axis is FALSE-FIRES PER HOUR (not per-utterance OOV FAR). Uses the Picovoice
wake-word-benchmark mixed streams (~20 min each, 6 keywords, 40 labeled wake-word intervals) already on
disk. Speaker-dependent detection is out-of-regime here (no speaker labels — cross-speaker, an
explicitly-labelled LOWER bound, per the committed PicovoiceBenchmark caveat); the FA/hr side (background
speech false-firing an enrolled template) is regime-independent and is the real question.

Both arms (mfcc-DTW, ssl-embedding-cosine) get identical enroll/stream/window logic — only the
feature+distance differ. Sweep the accept threshold -> detection-rate vs FA/hr curve; compare at matched FA/hr.

Usage: python ambient_scan.py <arm> [keywords-csv] [enrollN] [win_s] [hop_s]
  arm = mfcc | ssl:<model>:<layer>
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

PV = os.path.expanduser("~/picovoice-benchmark")
arm = sys.argv[1] if len(sys.argv) > 1 else "mfcc"
kw_filter = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None
ENROLL_N = int(sys.argv[3]) if len(sys.argv) > 3 else 10
WIN_S = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
HOP_S = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
SR = 16000
GUARD_S = 0.6          # a firing within GUARD of a labeled interval counts as detection, not FA
REFRACTORY_S = 1.0     # merge background firings within this window into one FA event
MIN_SPEECH = 1520

# ---- front end ----
if arm == "mfcc":
    fe = H.MfccFrontEnd()
    def feat(x): return fe(x)
    def dist(q, t): return H.dtw_distance(q, t)
elif arm.startswith("ssl:"):
    import torch
    from transformers import AutoModel
    _, model, layer = arm.split(":")
    MODELS = {"wavlm": "microsoft/wavlm-base-plus", "hubert": "facebook/hubert-base-ls960",
              "distilhubert": "ntu-spml/distilhubert", "wav2vec2": "facebook/wav2vec2-base"}
    net = AutoModel.from_pretrained(MODELS.get(model, model), output_hidden_states=True).eval()
    torch.set_grad_enabled(False)
    L = int(layer)
    def feat(x):
        if x.size < MIN_SPEECH: return np.zeros((0, 1), dtype=np.float32)
        w = (x - x.mean()) / (x.std() + 1e-7)
        h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[L][0].numpy()
        v = h.mean(0); return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)[None, :]
    def dist(q, t): return 1.0 - float(q[0] @ t[0])  # cosine distance on unit mean-pooled vecs
else:
    raise SystemExit("bad arm")


def read_full(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def load_labels(path):
    out = []
    for line in open(path):
        line = line.strip()
        if not line: continue
        a, b = line.replace(",", " ").split()[:2]
        out.append((float(a), float(b)))
    return out


keywords = sorted(glob.glob(os.path.join(PV, "mixed", "*_speech.wav")))
kw_names = [os.path.basename(k)[:-len("_speech.wav")] for k in keywords]
if kw_filter:
    kw_names = [k for k in kw_names if k in kw_filter]

all_scores = []   # (min_dist, in_positive, interval_id, keyword, t_center)
total_bg_sec = 0.0
total_intervals = 0
t0 = time.time()
for kw in kw_names:
    # enroll dir name uses spaces (e.g. "smart mirror"); mixed uses underscores
    adir = os.path.join(PV, "prepared", "audio", kw.replace("_", " "))
    takes = sorted(glob.glob(os.path.join(adir, "*.wav")))[:ENROLL_N]
    if not takes:
        adir = os.path.join(PV, "prepared", "audio", kw)
        takes = sorted(glob.glob(os.path.join(adir, "*.wav")))[:ENROLL_N]
    templates = []
    for tk in takes:
        sp = H.energy_vad_trim(read_full(tk))
        if sp.size >= MIN_SPEECH:
            f = feat(sp)
            if f.shape[0] > 0: templates.append(f)
    stream = read_full(os.path.join(PV, "mixed", kw + "_speech.wav"))
    labels = load_labels(os.path.join(PV, "mixed", kw + "_label.txt"))
    dur = stream.size / SR
    # background seconds = total minus positive intervals (+guard)
    pos_sec = sum(b - a + 2 * GUARD_S for a, b in labels)
    total_bg_sec += max(0.0, dur - pos_sec)
    total_intervals += len(labels)
    win = int(WIN_S * SR); hop = int(HOP_S * SR)
    nwin = 0
    for s in range(0, stream.size - win + 1, hop):
        seg = stream[s:s + win]
        tc = (s + win / 2) / SR
        sp = H.energy_vad_trim(seg)
        q = feat(sp) if sp.size >= MIN_SPEECH else None
        d = math.inf
        if q is not None and q.shape[0] > 0 and templates:
            d = min(dist(q, t) for t in templates)
        iid = -1
        for k, (a, b) in enumerate(labels):
            if a - GUARD_S <= tc <= b + GUARD_S:
                iid = k; break
        all_scores.append((d, iid >= 0, iid, kw, tc))
        nwin += 1
    print(f"[{arm}] {kw}: {len(templates)} templ, {nwin} windows, {dur/60:.1f}min ({time.time()-t0:.0f}s)", flush=True)

bg_hours = total_bg_sec / 3600.0
print(f"\n[{arm}] background {bg_hours:.2f} h, {total_intervals} positive intervals across {len(kw_names)} keywords", flush=True)

# threshold sweep: detection-rate vs FA-events/hr
cands = sorted({s[0] for s in all_scores if math.isfinite(s[0])})
# subsample candidates for speed
if len(cands) > 400:
    cands = [cands[i] for i in range(0, len(cands), len(cands) // 400)]

def evaluate(thr):
    # detection: an interval is detected if any window in it fires
    detected = set()
    # FA events: background firing windows merged by REFRACTORY per keyword
    fa_events = 0
    last_fire = {}
    for d, inpos, iid, kw, tc in all_scores:
        if d > thr:
            continue
        if inpos:
            detected.add((kw, iid))
        else:
            lt = last_fire.get(kw, -1e9)
            if tc - lt > REFRACTORY_S:
                fa_events += 1
            last_fire[kw] = tc
    det_rate = len(detected) / total_intervals if total_intervals else 0.0
    return det_rate, fa_events / bg_hours if bg_hours else 0.0

curve = [(evaluate(t), t) for t in cands]
print(f"\n[{arm}] detection @ target FA/hr:", flush=True)
for target in [0.1, 0.5, 1.0, 5.0, 10.0]:
    best = max((c for c in curve if c[0][1] <= target), key=lambda c: c[0][0], default=None)
    if best:
        (det, fa), thr = best
        print(f"   FA/hr<= {target:5.1f}:  detection {det*100:5.1f}%  (miss {100-det*100:4.1f}%)  @ realized FA/hr {fa:.2f}, thr {thr:.3f}", flush=True)
    else:
        print(f"   FA/hr<= {target:5.1f}:  (no operating point)", flush=True)
# also the best detection at any FA/hr and the FA/hr at 90% detection
d90 = min((c for c in curve if c[0][0] >= 0.9), key=lambda c: c[0][1], default=None)
if d90:
    print(f"   to reach >=90% detection: FA/hr = {d90[0][1]:.1f}", flush=True)
print(f"[{arm}] done {time.time()-t0:.0f}s", flush=True)
