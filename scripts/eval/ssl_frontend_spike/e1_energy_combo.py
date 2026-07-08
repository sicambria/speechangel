"""E1: DistilHuBERT + energy-ratio combo on F04. Quick single-model variant."""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPK = sys.argv[1] if len(sys.argv) > 1 else "F04"
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
PV = os.path.expanduser("~/picovoice-benchmark")

import torch
torch.set_num_threads(4)
from transformers import AutoModel
net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed_with_features(x):
    sp = H.energy_vad_trim(x)
    dur_sp = sp.size if sp.size >= MIN_SPEECH else 0
    rms = float(np.sqrt(np.mean(sp.astype(np.float64) ** 2))) if dur_sp > 0 else 0.0
    if sp.size < MIN_SPEECH:
        return None, dur_sp, x.size, rms
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32), dur_sp, x.size, rms


def cos_d(a, b):
    return 1.0 - float(a @ b)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


t0 = time.time()

# Load
root = os.path.expanduser("~/torgo") if not SPK.startswith("FC") else os.path.expanduser("~/torgo/FCX")
d = H.scan(root).get(SPK)
if d is None:
    raise SystemExit(f"{SPK} not found")

emb_info = {}
all_wavs = sorted([w for lst in d["commands"].values() for w in lst])
for wav in all_wavs:
    x = read_wav(wav)
    emb_info[wav] = embed_with_features(x)
print(f"  {sum(1 for v in emb_info.values() if v[0] is not None)}/{len(all_wavs)} embedded "
      f"({time.time()-t0:.0f}s)", flush=True)

# Build flat templates
all_tmps = []
for word, wavs in d["commands"].items():
    for w in wavs:
        v, ds, dr, rms = emb_info.get(w, (None, 0, 0, 0.0))
        if v is not None:
            all_tmps.append((v, ds, rms, word, w))

n_pos = len(all_tmps)
pos_records = []
for i, (qv, qds, qrms, qw, qwav) in enumerate(all_tmps):
    dists = []
    for j, (tv, tds, trms, tw, twav) in enumerate(all_tmps):
        if j == i:
            continue
        dists.append((cos_d(qv, tv), j, tw, tds, trms))
    dists.sort(key=lambda x: x[0])
    if len(dists) >= 2:
        d1, idx1, w1, tds1, trms1 = dists[0]
        d2 = dists[1][0]
        dr_val = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        mr_val = d1 / max(d2, 1e-8)
        er_val = abs(math.log(max(qrms, 1e-10) / max(trms1, 1e-10))) if qrms > 0 and trms1 > 0 else 0.0
    elif len(dists) == 1:
        d1, idx1, w1, tds1, trms1 = dists[0]
        dr_val = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        mr_val = 0.0
        er_val = abs(math.log(max(qrms, 1e-10) / max(trms1, 1e-10))) if qrms > 0 and trms1 > 0 else 0.0
    else:
        continue
    pos_records.append((d1, dr_val, mr_val, er_val))

# Background
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))
win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_records = []
bg_sec_total = 0.0
for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v, ds, dr, rms = embed_with_features(x[s:s + win_samples])
        if v is None:
            bg_records.append((math.inf, 0.0, 1.0, 0.0, base + (s + win_samples / 2) / SR))
            continue
        btc = base + (s + win_samples / 2) / SR
        dists = []
        for j, (tv, tds, trms, tw, twav) in enumerate(all_tmps):
            dists.append((cos_d(v, tv), j, tw, tds, trms))
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, idx1, w1, tds1, trms1 = dists[0]
            d2 = dists[1][0]
            dr_val = abs(math.log(max(ds, 1) / max(tds1, 1))) if ds > 0 and tds1 > 0 else 0.0
            mr_val = d1 / max(d2, 1e-8)
            er_val = abs(math.log(max(rms, 1e-10) / max(trms1, 1e-10))) if rms > 0 and trms1 > 0 else 0.0
        elif len(dists) == 1:
            d1, idx1, w1, tds1, trms1 = dists[0]
            d2 = 1.0
            dr_val = abs(math.log(max(ds, 1) / max(tds1, 1))) if ds > 0 and tds1 > 0 else 0.0
            mr_val = 0.0
            er_val = abs(math.log(max(rms, 1e-10) / max(trms1, 1e-10))) if rms > 0 and trms1 > 0 else 0.0
        else:
            d1, dr_val, mr_val, er_val = math.inf, 0.0, 1.0, 0.0
        bg_records.append((d1, dr_val, mr_val, er_val, btc))
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h bg, {len(bg_records)} windows ({time.time()-t0:.0f}s)", flush=True)

# Grid search
DUR_CANDS = np.linspace(0.05, 2.0, 15)
MARGIN_CANDS = np.linspace(0.2, 1.0, 9)
ENR_CANDS = np.linspace(0.05, 2.0, 15)

pos_dists = sorted({r[0] for r in pos_records if math.isfinite(r[0])})
bg_ds = sorted({r[0] for r in bg_records if math.isfinite(r[0])})
cands_d = list(pos_dists)
if len(bg_ds) > 200:
    step = max(1, len(bg_ds) // 200)
    for i in range(0, len(bg_ds), step):
        cands_d.append(bg_ds[i])
cands_d = sorted(set(cands_d))


def evaluate(conds, use_enr):
    det = sum(1 for r in pos_records
              if r[0] <= conds[0] and r[1] <= conds[1] and r[2] <= conds[2]
              and (not use_enr or r[3] <= conds[3])
              ) / len(pos_records) if pos_records else 0.0
    fa = 0
    last = -1e9
    for r in bg_records:
        passes = (r[0] <= conds[0] and r[1] <= conds[1] and r[2] <= conds[2]
                  and (not use_enr or r[3] <= conds[3]))
        if passes and r[4] - last > REFRACTORY_S:
            fa += 1
            last = r[4]
        elif passes:
            last = r[4]
    return det, fa / bg_hours if bg_hours else 0.0


# 2-stage best
best_2 = None
for td in cands_d:
    for tdur in DUR_CANDS:
        for tmar in MARGIN_CANDS:
            det, fa = evaluate((td, tdur, tmar, 0.0), False)
            if fa <= 0.5 and (best_2 is None or det > best_2[0]):
                best_2 = (det, fa, td, tdur, tmar)

# 3-stage best
best_3 = None
for td in cands_d:
    for tdur in DUR_CANDS:
        for tmar in MARGIN_CANDS:
            for tenr in ENR_CANDS:
                det, fa = evaluate((td, tdur, tmar, tenr), True)
                if fa <= 0.5 and (best_3 is None or det > best_3[0]):
                    best_3 = (det, fa, td, tdur, tmar, tenr)

print(f"\n=== {SPK} DistilHuBERT + Energy-Ratio ===", flush=True)
if best_2:
    print(f"  2-stage (dist+dur):    FRR={(1-best_2[0])*100:.1f}%  det={best_2[0]*100:.1f}%  "
          f"d<={best_2[2]:.4f}  dur<={best_2[3]:.3f}", flush=True)
if best_3:
    print(f"  3-stage (+enr):        FRR={(1-best_3[0])*100:.1f}%  det={best_3[0]*100:.1f}%  "
          f"d<={best_3[2]:.4f}  dur<={best_3[3]:.3f}  enr<={best_3[5]:.3f}", flush=True)
    if best_2:
        frr_2 = 1 - best_2[0]
        frr_3 = 1 - best_3[0]
        if frr_2 > 0.01:
            rel = (frr_2 - frr_3) / frr_2 * 100
            print(f"  Rel FRR reduction: {rel:+.1f}%", flush=True)
else:
    print(f"  3-stage: no valid point", flush=True)

print(f"\n  Previous results:")
print(f"    DistilHuBERT + dual (no enr): F04 FRR=6.0% (N+9)")
print(f"    WavLM + dual + enr:           F04 FRR=2.0% (N+5)")
print(f"  Total: {time.time()-t0:.0f}s", flush=True)
