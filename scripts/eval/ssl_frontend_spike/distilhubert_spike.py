"""N+9: DistilHuBERT CP-2 calibration — run dual-cascade with DistilHuBERT.

Pre-registered H1: DistilHuBERT-L2 mean-pooled cosine (~23M params, 2 transformer layers)
with dual-cascade achieves >=50% of WavLM-L12's CP-2 performance.

Usage: python distilhubert_spike.py [speakers] [bg_minutes]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2  # 2 layers, 0-indexed -> last layer
PV = os.path.expanduser("~/picovoice-benchmark")

import torch
torch.set_num_threads(4)
from transformers import AutoModel

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed_with_dur(x):
    sp = H.energy_vad_trim(x)
    dur_sp = sp.size if sp.size >= MIN_SPEECH else 0
    if sp.size < MIN_SPEECH:
        return None, dur_sp, x.size
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32), dur_sp, x.size


def cos_d(a, b):
    return 1.0 - float(a @ b)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def binom_two_sided(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


t0 = time.time()

# 1. Load TORGO, embed all
print(f"Loading & embedding TORGO with {MODEL} L{LAYER}...", flush=True)
all_data = {}
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo") if not spk.startswith("FC") else os.path.expanduser(
        "~/torgo/FCX")
    d = H.scan(root).get(spk)
    if d is None:
        continue
    all_data[spk] = d

emb_info = {}
all_wavs = sorted({w for d in all_data.values() for lst in d["commands"].values() for w in lst})
for wav in all_wavs:
    x = read_wav(wav)
    emb_info[wav] = embed_with_dur(x)
print(f"  {sum(1 for v in emb_info.values() if v[0] is not None)}/{len(all_wavs)} embedded ({time.time()-t0:.0f}s)",
      flush=True)

# 2. Build speaker structures
print("Scoring positives...", flush=True)
spk_info = {}
for spk, d in all_data.items():
    all_tmps = []
    for word, wavs in d["commands"].items():
        for w in wavs:
            v, ds, dr = emb_info.get(w, (None, 0, 0))
            if v is not None:
                all_tmps.append((v, ds, word, w))

    n_pos = len(all_tmps)
    pos_records = []
    for i, (qv, qds, qw, qwav) in enumerate(all_tmps):
        dists = []
        for j, (tv, tds, tw, twav) in enumerate(all_tmps):
            if j == i:
                continue
            dists.append((cos_d(qv, tv), j, tw, tds))
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, idx1, w1, tds1 = dists[0]
            d2 = dists[1][0]
            dr_val = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
            mr_val = d1 / max(d2, 1e-8)
        elif len(dists) == 1:
            d1, idx1, w1, tds1 = dists[0]
            dr_val = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
            mr_val = 0.0
        else:
            continue
        pos_records.append((d1, dr_val, mr_val))

    spk_info[spk] = {"all_tmps": all_tmps, "n_pos": n_pos, "pos_records": pos_records}
    print(f"  {spk}: {n_pos} pos", flush=True)

# 3. Background scan
print(f"\nScanning background ({BG_MIN} min)...", flush=True)
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))

win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_vecs, bg_durs, bg_times, bg_sec_total = [], [], [], 0.0
for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v, ds, dr = embed_with_dur(x[s:s + win_samples])
        bg_vecs.append(v)
        bg_durs.append(ds)
        bg_times.append(base + (s + win_samples / 2) / SR)
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows ({time.time()-t0:.0f}s)", flush=True)

# 4. Score background
print("Scoring background...", flush=True)
for spk, info in spk_info.items():
    all_tmps = info["all_tmps"]
    bg_records = []
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        if bv is None:
            bg_records.append((math.inf, 0.0, 1.0, btc))
            continue
        dists = []
        for j, (tv, tds, tw, twav) in enumerate(all_tmps):
            dists.append((cos_d(bv, tv), j, tw, tds))
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, idx1, w1, tds1 = dists[0]
            d2 = dists[1][0]
            dr_val = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
            mr_val = d1 / max(d2, 1e-8)
        elif len(dists) == 1:
            d1, idx1, w1, tds1 = dists[0]
            dr_val = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
            mr_val = 0.0
        else:
            d1, dr_val, mr_val = math.inf, 0.0, 1.0
        bg_records.append((d1, dr_val, mr_val, btc))
    info["bg_records"] = bg_records
    print(f"  {spk}: {len(bg_records)} bg records", flush=True)

# 5. Evaluate
print("\n" + "=" * 70)
print(f"DISTILHUBERT L{LAYER} (23.5M params) — single baseline vs dual-cascade")
print("=" * 70)


def eval_single(info, thr_d):
    pos = info["pos_records"]
    bg = info["bg_records"]
    det = sum(1 for r in pos if r[0] <= thr_d) / len(pos) if pos else 0.0
    fa = 0
    last = -1e9
    for r in bg:
        if r[0] <= thr_d and r[3] - last > REFRACTORY_S:
            fa += 1
            last = r[3]
        elif r[0] <= thr_d:
            last = r[3]
    return det, fa / bg_hours if bg_hours else 0.0


def eval_dual(info, thr_d, thr_dur, thr_margin):
    pos = info["pos_records"]
    bg = info["bg_records"]
    det = sum(1 for r in pos
              if r[0] <= thr_d and r[1] <= thr_dur and r[2] <= thr_margin
              ) / len(pos) if pos else 0.0
    fa = 0
    last = -1e9
    for r in bg:
        if (r[0] <= thr_d and r[1] <= thr_dur and r[2] <= thr_margin and
                r[3] - last > REFRACTORY_S):
            fa += 1
            last = r[3]
        elif r[0] <= thr_d and r[1] <= thr_dur and r[2] <= thr_margin:
            last = r[3]
    return det, fa / bg_hours if bg_hours else 0.0


DUR_CANDS = np.linspace(0.05, 2.0, 15)
MARGIN_CANDS = np.linspace(0.2, 1.0, 9)

for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    pos = info["pos_records"]
    bg = info["bg_records"]

    pos_dists = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_ds = sorted({r[0] for r in bg if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_ds) > 200:
        step = max(1, len(bg_ds) // 200)
        for i in range(0, len(bg_ds), step):
            cands_d.append(bg_ds[i])
    cands_d = sorted(set(cands_d))

    best_single = None
    for t in cands_d:
        det, fa = eval_single(info, t)
        if fa <= 0.5 and (best_single is None or det > best_single[0]):
            best_single = (det, fa, t)

    best_dual = None
    best_params = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = eval_dual(info, td, tdur, tmar)
                if fa <= 0.5 and (best_dual is None or det > best_dual[0]):
                    best_dual = (det, fa)
                    best_params = (td, tdur, tmar)

    print(f"\n--- {spk} (n={info['n_pos']}) ---", flush=True)
    if best_single:
        print(f"  Single:        FRR={(1-best_single[0])*100:.1f}%  det={best_single[0]*100:.1f}%  "
              f"thr_d={best_single[2]:.4f}", flush=True)
    if best_dual:
        print(f"  Dual-cascade:  FRR={(1-best_dual[0])*100:.1f}%  det={best_dual[0]*100:.1f}%  "
              f"d<={best_params[0]:.4f}  dur<={best_params[1]:.3f}  mar<={best_params[2]:.3f}",
              flush=True)
        if best_single:
            frr_s = 1 - best_single[0]
            frr_d = 1 - best_dual[0]
            if frr_s > 0.01:
                rel = (frr_s - frr_d) / frr_s * 100
                print(f"  ★ Rel FRR reduction: {rel:+.1f}%", flush=True)

# 6. McNemar
print("\n" + "=" * 70)
print(f"PAIRED McNEMAR — DistilHuBERT L{LAYER} dual-cascade vs single")
print("=" * 70)
agg_b, agg_c, agg_n = 0, 0, 0
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    pos = info["pos_records"]
    bg = info["bg_records"]
    pos_dists = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_ds = sorted({r[0] for r in bg if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_ds) > 200:
        step = max(1, len(bg_ds) // 200)
        for i in range(0, len(bg_ds), step):
            cands_d.append(bg_ds[i])
    cands_d = sorted(set(cands_d))

    best_single = None
    for t in cands_d:
        det, fa = eval_single(info, t)
        if fa <= 0.5 and (best_single is None or det > best_single[0]):
            best_single = (det, fa, t)

    best_dual = None
    best_params = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = eval_dual(info, td, tdur, tmar)
                if fa <= 0.5 and (best_dual is None or det > best_dual[0]):
                    best_dual = (det, fa)
                    best_params = (td, tdur, tmar)

    if best_single is None or best_params is None:
        continue

    thr_s = best_single[2]
    td_d, td_dur, td_mar = best_params
    det_single = [1 if r[0] <= thr_s else 0 for r in pos]
    det_dual = [1 if (r[0] <= td_d and r[1] <= td_dur and r[2] <= td_mar) else 0 for r in pos]

    b = sum(1 for s, d in zip(det_single, det_dual) if s == 1 and d == 0)
    c = sum(1 for s, d in zip(det_single, det_dual) if s == 0 and d == 1)
    n = b + c
    chi2 = (abs(b - c) - 1) ** 2 / n if n > 0 else float("nan")
    p_chi = math.erfc(math.sqrt(chi2 / 2.0)) if n > 0 else 1.0
    p_bin = binom_two_sided(b, c)

    print(f"  {spk}: single={sum(det_single)/len(pos)*100:.1f}%  dual={sum(det_dual)/len(pos)*100:.1f}%  "
          f"b={b} c={c}  p={p_chi:.4f}  exact-p={p_bin:.4f}", flush=True)
    agg_b += b
    agg_c += c
    agg_n += info["n_pos"]

n_agg = agg_b + agg_c
if n_agg > 0:
    chi2_agg = (abs(agg_b - agg_c) - 1) ** 2 / n_agg
    p_chi_agg = math.erfc(math.sqrt(chi2_agg / 2.0))
    p_bin_agg = binom_two_sided(agg_b, agg_c)
    print(f"\n  AGGREGATE (n={agg_n}): b={agg_b} c={agg_c}  p={p_chi_agg:.4f}  exact-p={p_bin_agg:.4f}",
          flush=True)

print(f"\n{'=' * 70}")
# Compare with WavLM-L12
print("vs WavLM-L12 (from N+3 dual-cascade):")
print("  F01: WavLM 3.1% FRR  |  F03: WavLM 25.4% FRR  |  F04: WavLM 20.0% FRR")
print(f"  Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
