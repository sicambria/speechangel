"""CP-2 dual-cascade verification spike v2 — proper 3D grid search.

Pre-registered H1: A dual-cascade gate — Stage-1 (min_distance ≤ θ1) AND Stage-2
(|log(duration_ratio)| ≤ θ2 AND margin_ratio ≤ θ3) — reduces FRR at matched ≤0.5 FA/hr
by ≥20% relative vs the single-threshold global baseline on WavLM-L12 pooled-cosine.

V2 fixes: proper 3D grid search (distance, dur, margin), consistent output.
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

# --emit=<file>: append structured SOTA-scorecard metrics (D8) for SotaScorecard; not prose. Stripped
# from argv before the positional parse so it composes with `<speakers> <bg_min>`.
_EMIT = None
_argv = []
for _a in sys.argv[1:]:
    if _a.startswith("--emit="):
        _EMIT = _a.split("=", 1)[1]
    else:
        _argv.append(_a)
sys.argv = [sys.argv[0]] + _argv

# ----------------------------------------------------------------- config
SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "microsoft/wavlm-base-plus", 12
PV = os.path.expanduser("~/picovoice-benchmark")

# ----------------------------------------------------------------- torch
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

# =================================================================
# 1. Load TORGO, embed all
# =================================================================
print("Loading & embedding TORGO...", flush=True)
all_data = {}
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo") if not spk.startswith("FC") else os.path.expanduser(
        "~/torgo/FCX")
    d = H.scan(root).get(spk)
    if d is None:
        continue
    all_data[spk] = d

emb_wavs = {}
all_wavs = sorted({w for d in all_data.values() for lst in d["commands"].values() for w in lst})
for wav in all_wavs:
    x = read_wav(wav)
    emb_wavs[wav] = embed_with_dur(x)
n_emb = sum(1 for v in emb_wavs.values() if v[0] is not None)
print(f"  {n_emb}/{len(all_wavs)} embedded ({time.time()-t0:.0f}s)", flush=True)

# =================================================================
# 2. Build per-speaker: all templates, positive features
# =================================================================
print("\nScoring positives...", flush=True)
spk_info = {}
for spk, d in all_data.items():
    # all templates flat
    all_tmps = []
    for word, wavs in d["commands"].items():
        for w in wavs:
            v, ds, dr = emb_wavs.get(w, (None, 0, 0))
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

    # get per-word template durations for bg matching
    word_templates = {}
    for v, tds, tw, twav in all_tmps:
        word_templates.setdefault(tw, []).append((v, tds))

    spk_info[spk] = {
        "all_tmps": all_tmps,
        "word_templates": word_templates,
        "n_pos": n_pos,
        "pos_records": pos_records,
    }
    print(f"  {spk}: {n_pos} positives, "
          f"dur_ratio med={np.median([r[1] for r in pos_records]):.3f}, "
          f"margin_ratio med={np.median([r[2] for r in pos_records]):.3f}",
          flush=True)

# =================================================================
# 3. Background scan with features
# =================================================================
print(f"\nScanning LibriSpeech background ({BG_MIN} min)...", flush=True)
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

# =================================================================
# 4. Per speaker: score background
# =================================================================
print("\nScoring background...", flush=True)
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
    print(f"  {spk}: {len(bg_records)} bg records, "
          f"dur_ratio med={np.median([r[1] for r in bg_records if math.isfinite(r[0])]):.3f}, "
          f"margin_ratio med={np.median([r[2] for r in bg_records if math.isfinite(r[0])]):.3f}",
          flush=True)

# =================================================================
# 5. Single baseline vs dual-cascade (3D grid search)
# =================================================================
print("\n" + "=" * 70)
print("SINGLE BASELINE vs DUAL-CASCADE (3D grid search, matched ≤0.5 FA/hr)")
print("=" * 70)


def evaluate_single(info, thr_d):
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


def evaluate_dual(info, thr_d, thr_dur, thr_margin):
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


DUR_CANDS = np.linspace(0.05, 2.0, 20)
MARGIN_CANDS = np.linspace(0.2, 1.0, 17)

rel_by_spk = {}
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    pos = info["pos_records"]
    bg = info["bg_records"]

    # distance candidates: ALL positive distances + quantile-sampled bg distances
    pos_dists = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_dists_sorted = sorted({r[0] for r in bg if math.isfinite(r[0])})
    cands_d = list(pos_dists)  # critical: every positive distance
    if len(bg_dists_sorted) > 200:
        step = max(1, len(bg_dists_sorted) // 200)
        for i in range(0, len(bg_dists_sorted), step):
            cands_d.append(bg_dists_sorted[i])
    cands_d = sorted(set(cands_d))

    # single-threshold baseline
    best_single = None
    for t in cands_d:
        det, fa = evaluate_single(info, t)
        if fa <= 0.5 and (best_single is None or det > best_single[0]):
            best_single = (det, fa, t)

    # dual-cascade: 3D grid search
    best_dual = None
    best_params = None
    for td in cands_d:
        # prune: if single already achieves close to max detection at this threshold, try it
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = evaluate_dual(info, td, tdur, tmar)
                if fa <= 0.5 and (best_dual is None or det > best_dual[0]):
                    best_dual = (det, fa)
                    best_params = (td, tdur, tmar)

    print(f"\n--- {spk} (n={info['n_pos']}) ---", flush=True)
    if best_single:
        ds, fa_s, ts = best_single
        print(f"  Single:        det={ds*100:.1f}%  FRR={(1-ds)*100:.1f}%  "
              f"FA={fa_s:.2f}/hr  thr_d={ts:.4f}", flush=True)
    else:
        print(f"  Single:        no valid point", flush=True)

    if best_dual:
        dd, fa_d = best_dual
        td, tdur, tmar = best_params
        print(f"  Dual-cascade:  det={dd*100:.1f}%  FRR={(1-dd)*100:.1f}%  "
              f"FA={fa_d:.2f}/hr", flush=True)
        print(f"    params: d<={td:.4f}  |log(dur_ratio)|<={tdur:.3f}  margin<={tmar:.3f}",
              flush=True)
        if best_single and best_dual:
            frr_s = 1 - best_single[0]
            frr_d = 1 - best_dual[0]
            if frr_s > 0.01:
                rel = (frr_s - frr_d) / frr_s * 100
                rel_by_spk[spk] = rel / 100.0
                print(f"  ★ Rel FRR reduction: {rel:+.1f}%  "
                      f"({'WIN >= 20%' if rel >= 20 else 'GAIN < 20%' if rel > 5 else 'TIE'})",
                      flush=True)
    else:
        print(f"  Dual-cascade:  no valid point", flush=True)

if _EMIT:
    # Banked headline = the binding large-vocab speaker (F03), else the strongest measured.
    _spk = "F03" if "F03" in rel_by_spk else (max(rel_by_spk, key=rel_by_spk.get) if rel_by_spk else None)
    if _spk is not None:
        with open(_EMIT, "a") as _f:
            _f.write(f"domain8_value={rel_by_spk[_spk]:.4f}\n")
            _f.write(f"domain8_config=dual-cascade rel FRR reduction, WavLM-base-plus L12, {_spk}, off-device ({BG_MIN}min bg)\n")

# =================================================================
# 6. Per-positive detection vectors for McNemar
# =================================================================
print("\n" + "=" * 70)
print("PAIRED McNEMAR at matched ≤0.5 FA/hr")
print("=" * 70)

agg_b, agg_c, agg_n = 0, 0, 0
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    pos = info["pos_records"]
    bg = info["bg_records"]
    pos_dists = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_dists_sorted = sorted({r[0] for r in bg if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_dists_sorted) > 200:
        step = max(1, len(bg_dists_sorted) // 200)
        for i in range(0, len(bg_dists_sorted), step):
            cands_d.append(bg_dists_sorted[i])
    cands_d = sorted(set(cands_d))

    best_single = None
    for t in cands_d:
        det, fa = evaluate_single(info, t)
        if fa <= 0.5 and (best_single is None or det > best_single[0]):
            best_single = (det, fa, t)

    best_dual = None
    best_params = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            for tmar in MARGIN_CANDS:
                det, fa = evaluate_dual(info, td, tdur, tmar)
                if fa <= 0.5 and (best_dual is None or det > best_dual[0]):
                    best_dual = (det, fa)
                    best_params = (td, tdur, tmar)

    if best_single is None or best_params is None:
        continue

    thr_s = best_single[2]
    td_d, td_dur, td_mar = best_params
    det_single = [1 if r[0] <= thr_s else 0 for r in pos]
    det_dual = [1 if (r[0] <= td_d and r[1] <= td_dur and r[2] <= td_mar) else 0
                for r in pos]

    b = sum(1 for s, d in zip(det_single, det_dual) if s == 1 and d == 0)
    c = sum(1 for s, d in zip(det_single, det_dual) if s == 0 and d == 1)
    n = b + c
    chi2 = (abs(b - c) - 1) ** 2 / n if n > 0 else float("nan")
    p_chi = math.erfc(math.sqrt(chi2 / 2.0)) if n > 0 else 1.0
    p_bin = binom_two_sided(b, c)

    ds = sum(det_single) / len(pos) * 100
    dd = sum(det_dual) / len(pos) * 100
    print(f"  {spk} (n={info['n_pos']}): single={ds:.1f}%  dual={dd:.1f}%  "
          f"discordant b(single-only)={b} c(dual-only)={c}  "
          f"McNemar p={p_chi:.4f}  exact-p={p_bin:.4f}", flush=True)
    agg_b += b
    agg_c += c
    agg_n += info["n_pos"]

n_agg = agg_b + agg_c
chi2_agg = (abs(agg_b - agg_c) - 1) ** 2 / n_agg if n_agg > 0 else float("nan")
p_chi_agg = math.erfc(math.sqrt(chi2_agg / 2.0)) if n_agg > 0 else 1.0
p_bin_agg = binom_two_sided(agg_b, agg_c)
print(f"\n  AGGREGATE (n={agg_n}): discordant b={agg_b} c={agg_c}  "
      f"McNemar p={p_chi_agg:.4f}  exact-p={p_bin_agg:.4f}", flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
