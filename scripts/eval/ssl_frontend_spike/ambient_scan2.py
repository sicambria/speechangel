"""CP-2 ambient measurement — OPTIMIZED (stream-once). See ambient_scan.py for the protocol.

Speedup vs ambient_scan.py: embed each stream ONCE at the model's native 20ms stride (chunked), then a
window = mean-pool of its cached frame range — instead of re-running a 94M-param forward pass on each of
~14k overlapping windows. For MFCC, extract the stream's MFCC once and DTW each window's frame slice.
torch threads capped to avoid core over-subscription.

Usage: python ambient_scan2.py <arm> [keywords-csv] [enrollN] [win_s] [hop_s]
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
GUARD_S, REFRACTORY_S, MIN_SPEECH = 0.6, 1.0, 1520
STRIDE = 320  # wav2vec2/wavlm/hubert frame stride (20ms)

IS_SSL = arm.startswith("ssl:")
if IS_SSL:
    import torch
    torch.set_num_threads(4)
    from transformers import AutoModel
    _, model, layer = arm.split(":")
    MODELS = {"wavlm": "microsoft/wavlm-base-plus", "hubert": "facebook/hubert-base-ls960",
              "distilhubert": "ntu-spml/distilhubert", "wav2vec2": "facebook/wav2vec2-base"}
    net = AutoModel.from_pretrained(MODELS.get(model, model), output_hidden_states=True).eval()
    torch.set_grad_enabled(False)
    L = int(layer)

    def stream_frames(x, chunk_s=20.0):
        """Frame embeddings (T,H) for a long signal, processed in chunks (native 20ms stride)."""
        cs = int(chunk_s * SR)
        outs = []
        for s in range(0, x.size, cs):
            seg = x[s:s + cs]
            if seg.size < 400:
                continue
            w = (seg - seg.mean()) / (seg.std() + 1e-7)
            h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[L][0].numpy()
            outs.append(h.astype(np.float32))
        return np.concatenate(outs, axis=0) if outs else np.zeros((0, 1), np.float32)

    def pool(frames):
        if frames.shape[0] == 0:
            return None
        v = frames.mean(0)
        return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)

    def enroll_vec(x):
        return pool(stream_frames(x))

    def dist_vv(a, b):
        return 1.0 - float(a @ b)
else:
    fe = H.MfccFrontEnd()


def read_full(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def load_labels(path):
    out = []
    for line in open(path):
        line = line.strip()
        if line:
            a, b = line.replace(",", " ").split()[:2]
            out.append((float(a), float(b)))
    return out


keywords = sorted(glob.glob(os.path.join(PV, "mixed", "*_speech.wav")))
kw_names = [os.path.basename(k)[:-len("_speech.wav")] for k in keywords]
if kw_filter:
    kw_names = [k for k in kw_names if k in kw_filter]

all_scores = []
total_bg_sec = 0.0
total_intervals = 0
t0 = time.time()
win = int(WIN_S * SR); hop = int(HOP_S * SR)
fpw = int(WIN_S * SR / STRIDE)   # frames per window (SSL)
fph = max(1, int(HOP_S * SR / STRIDE))

for kw in kw_names:
    adir = os.path.join(PV, "prepared", "audio", kw.replace("_", " "))
    takes = sorted(glob.glob(os.path.join(adir, "*.wav")))[:ENROLL_N] or \
        sorted(glob.glob(os.path.join(PV, "prepared", "audio", kw, "*.wav")))[:ENROLL_N]
    stream = read_full(os.path.join(PV, "mixed", kw + "_speech.wav"))
    labels = load_labels(os.path.join(PV, "mixed", kw + "_label.txt"))
    dur = stream.size / SR
    total_bg_sec += max(0.0, dur - sum(b - a + 2 * GUARD_S for a, b in labels))
    total_intervals += len(labels)

    def in_pos(tc):
        for k, (a, b) in enumerate(labels):
            if a - GUARD_S <= tc <= b + GUARD_S:
                return k
        return -1

    if IS_SSL:
        templates = [v for v in (enroll_vec(H.energy_vad_trim(read_full(t))) for t in takes) if v is not None]
        frames = stream_frames(stream)  # (T,H) for whole stream — ONE pass set
        nwin = 0
        for fs in range(0, max(0, frames.shape[0] - fpw + 1), fph):
            tc = (fs + fpw / 2) * STRIDE / SR
            v = pool(frames[fs:fs + fpw])
            d = min((dist_vv(v, t) for t in templates), default=math.inf) if v is not None else math.inf
            all_scores.append((d, in_pos(tc) >= 0, in_pos(tc), kw, tc))
            nwin += 1
    else:
        templates = []
        for t in takes:
            sp = H.energy_vad_trim(read_full(t))
            if sp.size >= MIN_SPEECH:
                f = fe(sp)
                if f.shape[0] > 0:
                    templates.append(f)
        nwin = 0
        for s in range(0, stream.size - win + 1, hop):
            sp = H.energy_vad_trim(stream[s:s + win])
            tc = (s + win / 2) / SR
            q = fe(sp) if sp.size >= MIN_SPEECH else None
            d = min((H.dtw_distance(q, t) for t in templates), default=math.inf) if (q is not None and q.shape[0] > 0) else math.inf
            all_scores.append((d, in_pos(tc) >= 0, in_pos(tc), kw, tc))
            nwin += 1
    print(f"[{arm}] {kw}: {len(templates)} templ, {nwin} win, {dur/60:.1f}min ({time.time()-t0:.0f}s)", flush=True)

bg_hours = total_bg_sec / 3600.0
print(f"\n[{arm}] background {bg_hours:.2f} h, {total_intervals} intervals, {len(kw_names)} keywords", flush=True)

cands = sorted({s[0] for s in all_scores if math.isfinite(s[0])})
if len(cands) > 500:
    cands = [cands[i] for i in range(0, len(cands), len(cands) // 500)]

def evaluate(thr):
    detected = set(); fa = 0; last = {}
    for d, inpos, iid, kw, tc in all_scores:
        if d > thr:
            continue
        if inpos:
            detected.add((kw, iid))
        else:
            if tc - last.get(kw, -1e9) > REFRACTORY_S:
                fa += 1
            last[kw] = tc
    return len(detected) / total_intervals if total_intervals else 0.0, fa / bg_hours if bg_hours else 0.0

curve = [(evaluate(t), t) for t in cands]
print(f"[{arm}] FRR (miss) at matched FA/hour:", flush=True)
for target in [0.1, 0.5, 1.0, 5.0, 10.0]:
    best = max((c for c in curve if c[0][1] <= target), key=lambda c: c[0][0], default=None)
    if best:
        (det, fa), thr = best
        print(f"   FA/hr<= {target:5.1f}: FRR {(1-det)*100:5.1f}% (det {det*100:4.1f}%) @ FA/hr {fa:.2f}", flush=True)
d90 = min((c for c in curve if c[0][0] >= 0.9), key=lambda c: c[0][1], default=None)
print(f"   FA/hr to get FRR<10%: {d90[0][1]:.1f}" if d90 else "   FRR<10% unreachable", flush=True)
print(f"[{arm}] done {time.time()-t0:.0f}s", flush=True)
