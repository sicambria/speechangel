"""N+5: Energy-ratio cross-verify spike — extends dual-cascade with a 4th signal.

Pre-registered H1: Adding energy-ratio (|log(q_rms / t_rms)| ≤ θ_enr) as third cascade stage
reduces FRR at ≤0.5 FA/hr by ≥10% relative vs the 2-stage (dist + dur) dual-cascade.

Protocol: Same as dual_cascade_verify.py but with RMS energy feature. For each utterance and
background window, compute sqrt(mean(x²)) post-VAD. For each (query, template) pair, compute
|log(q_rms / t_rms)|. 4D grid search (dist, dur, enr, margin).

Usage: python energy_ratio_spike.py [speakers] [bg_minutes]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "microsoft/wavlm-base-plus", 12
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


def binom_two_sided(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


t0 = time.time()

# 1. Load TORGO, embed all with RMS
print("Loading & embedding TORGO with RMS energy...", flush=True)
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
    emb_info[wav] = embed_with_features(x)
n_emb = sum(1 for v in emb_info.values() if v[0] is not None)
print(f"  {n_emb}/{len(all_wavs)} embedded ({time.time()-t0:.0f}s)", flush=True)

# 2. Build speaker structures with energy
print("\nScoring positives with energy...", flush=True)
spk_info = {}
for spk, d in all_data.items():
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

    spk_info[spk] = {"all_tmps": all_tmps, "n_pos": n_pos, "pos_records": pos_records}
    print(f"  {spk}: {n_pos} pos, dur_med={np.median([r[1] for r in pos_records]):.3f}, "
          f"enr_med={np.median([r[3] for r in pos_records]):.3f}", flush=True)

# 3. Background scan with energy
print(f"\nScanning background with energy ({BG_MIN} min)...", flush=True)
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))
win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_vecs, bg_durs, bg_rms, bg_times, bg_sec_total = [], [], [], [], 0.0
for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v, ds, dr, rms = embed_with_features(x[s:s + win_samples])
        bg_vecs.append(v)
        bg_durs.append(ds)
        bg_rms.append(rms)
        bg_times.append(base + (s + win_samples / 2) / SR)
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows ({time.time()-t0:.0f}s)", flush=True)

# 4. Score background with energy
print("Scoring background with energy...", flush=True)
for spk, info in spk_info.items():
    all_tmps = info["all_tmps"]
    bg_records = []
    for bv, bds, brms, btc in zip(bg_vecs, bg_durs, bg_rms, bg_times):
        if bv is None:
            bg_records.append((math.inf, 0.0, 1.0, 0.0, btc))
            continue
        dists = []
        for j, (tv, tds, trms, tw, twav) in enumerate(all_tmps):
            dists.append((cos_d(bv, tv), j, tw, tds, trms))
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, idx1, w1, tds1, trms1 = dists[0]
            d2 = dists[1][0]
            dr_val = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
            mr_val = d1 / max(d2, 1e-8)
            er_val = abs(math.log(max(brms, 1e-10) / max(trms1, 1e-10))) if brms > 0 and trms1 > 0 else 0.0
        elif len(dists) == 1:
            d1, idx1, w1, tds1, trms1 = dists[0]
            dr_val = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
            mr_val = 0.0
            er_val = abs(math.log(max(brms, 1e-10) / max(trms1, 1e-10))) if brms > 0 and trms1 > 0 else 0.0
        else:
            d1, dr_val, mr_val, er_val = math.inf, 0.0, 1.0, 0.0
        bg_records.append((d1, dr_val, mr_val, er_val, btc))
    info["bg_records"] = bg_records
    print(f"  {spk}: enr_med={np.median([r[3] for r in bg_records if math.isfinite(r[0])]):.3f}", flush=True)

# 5. Evaluation
DUR_CANDS = np.linspace(0.05, 2.0, 15)
MARGIN_CANDS = np.linspace(0.2, 1.0, 9)
ENR_CANDS = np.linspace(0.05, 2.0, 15)


def evaluate(scores, conds):
    """conds = (thr_d, thr_dur, thr_margin, thr_enr, use_enr).
    scores = (pos_records, bg_records)."""
    pos, bg = scores
    det = sum(1 for r in pos
              if r[0] <= conds[0] and r[1] <= conds[1] and r[2] <= conds[2]
              and (not conds[4] or r[3] <= conds[3])
              ) / len(pos) if pos else 0.0
    fa = 0
    last = -1e9
    for r in bg:
        if (r[0] <= conds[0] and r[1] <= conds[1] and r[2] <= conds[2]
                and (not conds[4] or r[3] <= conds[3])
                and r[4] - last > REFRACTORY_S):
            fa += 1
            last = r[4]
        elif (r[0] <= conds[0] and r[1] <= conds[1] and r[2] <= conds[2]
              and (not conds[4] or r[3] <= conds[3])):
            last = r[4]
    return det, fa / bg_hours if bg_hours else 0.0


print("\n" + "=" * 70)
print("2-STAGE (dist+dur) vs 3-STAGE (dist+dur+enr), matched ≤0.5 FA/hr")
print("=" * 70)

for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    scores = (info["pos_records"], info["bg_records"])

    pos_dists = sorted({r[0] for r in info["pos_records"] if math.isfinite(r[0])})
    bg_ds = sorted({r[0] for r in info["bg_records"] if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_ds) > 200:
        step = max(1, len(bg_ds) // 200)
        for i in range(0, len(bg_ds), step):
            cands_d.append(bg_ds[i])
    cands_d = sorted(set(cands_d))

    # 2-stage best (dur + margin, no enr)
    best_2 = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = evaluate(scores, (td, tdur, tmar, 0.0, False))
                if fa <= 0.5 and (best_2 is None or det > best_2[0]):
                    best_2 = (det, fa, td, tdur, tmar)

    # 3-stage best (+ enr)
    best_3 = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                for tenr in ENR_CANDS:
                    det, fa = evaluate(scores, (td, tdur, tmar, tenr, True))
                    if fa <= 0.5 and (best_3 is None or det > best_3[0]):
                        best_3 = (det, fa, td, tdur, tmar, tenr)

    print(f"\n--- {spk} (n={info['n_pos']}) ---", flush=True)
    if best_2:
        print(f"  2-stage (dist+dur):    FRR={(1-best_2[0])*100:.1f}%  det={best_2[0]*100:.1f}%  "
              f"d<={best_2[2]:.4f}  dur<={best_2[3]:.3f}  mar<={best_2[4]:.3f}", flush=True)
    if best_3:
        print(f"  3-stage (dist+dur+enr): FRR={(1-best_3[0])*100:.1f}%  det={best_3[0]*100:.1f}%  "
              f"d<={best_3[2]:.4f}  dur<={best_3[3]:.3f}  mar<={best_3[4]:.3f}  enr<={best_3[5]:.3f}",
              flush=True)
        if best_2:
            frr_2 = 1 - best_2[0]
            frr_3 = 1 - best_3[0]
            if frr_2 > 0.01:
                rel = (frr_2 - frr_3) / frr_2 * 100
                print(f"  Rel FRR reduction vs 2-stage: {rel:+.1f}%  "
                      f"({'WIN >= 10%' if rel >= 10 else 'GAIN' if rel > 2 else 'TIE'})", flush=True)
    else:
        print(f"  3-stage: no valid point", flush=True)

# McNemar
print("\n" + "=" * 70)
print("PAIRED McNEMAR: 2-stage vs 3-stage at matched ≤0.5 FA/hr")
print("=" * 70)
agg_b, agg_c = 0, 0
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    scores = (info["pos_records"], info["bg_records"])
    pos = info["pos_records"]
    pos_dists = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_ds = sorted({r[0] for r in info["bg_records"] if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_ds) > 200:
        step = max(1, len(bg_ds) // 200)
        for i in range(0, len(bg_ds), step):
            cands_d.append(bg_ds[i])
    cands_d = sorted(set(cands_d))

    best_2 = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = evaluate(scores, (td, tdur, tmar, 0.0, False))
                if fa <= 0.5 and (best_2 is None or det > best_2[0]):
                    best_2 = (det, fa, td, tdur, tmar)

    best_3 = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                for tenr in ENR_CANDS:
                    det, fa = evaluate(scores, (td, tdur, tmar, tenr, True))
                    if fa <= 0.5 and (best_3 is None or det > best_3[0]):
                        best_3 = (det, fa, td, tdur, tmar, tenr)

    if best_2 is None or best_3 is None:
        continue

    det_2 = [1 if (r[0] <= best_2[2] and r[1] <= best_2[3] and r[2] <= best_2[4]) else 0
             for r in pos]
    det_3 = [1 if (r[0] <= best_3[2] and r[1] <= best_3[3] and r[2] <= best_3[4]
                   and r[3] <= best_3[5]) else 0
             for r in pos]

    b = sum(1 for a, bb in zip(det_2, det_3) if a == 1 and bb == 0)
    c = sum(1 for a, bb in zip(det_2, det_3) if a == 0 and bb == 1)
    n = b + c
    chi2 = (abs(b - c) - 1) ** 2 / n if n > 0 else float("nan")
    p_chi = math.erfc(math.sqrt(chi2 / 2.0)) if n > 0 else 1.0
    p_bin = binom_two_sided(b, c)
    print(f"  {spk}: 2-stage={sum(det_2)/len(pos)*100:.1f}%  3-stage={sum(det_3)/len(pos)*100:.1f}%  "
          f"b={b} c={c}  p={p_chi:.4f}  exact-p={p_bin:.4f}", flush=True)
    agg_b += b
    agg_c += c

n_agg = agg_b + agg_c
if n_agg > 0:
    chi2_agg = (abs(agg_b - agg_c) - 1) ** 2 / n_agg
    p_chi_agg = math.erfc(math.sqrt(chi2_agg / 2.0))
    p_bin_agg = binom_two_sided(agg_b, agg_c)
    print(f"\n  AGGREGATE: b={agg_b} c={agg_c}  p={p_chi_agg:.4f}  exact-p={p_bin_agg:.4f}", flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
