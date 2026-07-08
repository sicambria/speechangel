"""N+7: Vocabulary-optimized enrollment spike.

Pre-registered H1: Reducing F03's vocabulary from 77 to the k=15 most acoustically-distinct
commands (by pairwise WavLM cosine confusion) brings FRR at <=0.5 FA/hr from 25.4% to <=10%
(>=60% relative reduction), proving vocabulary confusion is the binding constraint.

Protocol: Compute pairwise cosine confusion matrix from WavLM templates, greedy max-min
diversity selection, re-run dual-cascade on optimized vs random subsets.

Usage: python vocab_opt_spike.py [bg_minutes] [k]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

BG_MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 60
K = int(sys.argv[2]) if len(sys.argv) > 2 else 15
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "microsoft/wavlm-base-plus", 12
PV = os.path.expanduser("~/picovoice-benchmark")
MC_RANDOM = 5

import torch
torch.set_num_threads(4)
from transformers import AutoModel

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed(x):
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


def select_diverse(words, vecs_by_word, k, rng=None):
    """Greedy max-min diversity: pick k words maximizing min pairwise cosine distance."""
    if rng is None:
        rng = np.random.RandomState(42)
    # mean template per word
    centroids = {}
    for w in words:
        vs = vecs_by_word[w]
        if vs:
            centroids[w] = np.mean(vs, axis=0)
            centroids[w] /= (np.linalg.norm(centroids[w]) + 1e-8)
    if len(centroids) <= k:
        return list(centroids.keys())
    # start with the word farthest from the centroid of all centroids
    all_mean = np.mean(list(centroids.values()), axis=0)
    all_mean /= (np.linalg.norm(all_mean) + 1e-8)
    dists = {w: cos_d(c, all_mean) for w, c in centroids.items()}
    chosen = [max(dists, key=dists.get)]
    while len(chosen) < k:
        # pick the word with max min-distance to any chosen word
        best_w, best_d = None, -1.0
        for w in centroids:
            if w in chosen:
                continue
            min_d = min(cos_d(centroids[w], centroids[c]) for c in chosen)
            if min_d > best_d:
                best_d = min_d
                best_w = w
        chosen.append(best_w)
    return chosen


def evaluate_subset(words_subset, vecs_by_word_subset, bg_records, bg_hours):
    """Run full dual-cascade on a subset of words. vecs_by_word_subset = {word: [unit_vec, ...]}.
    Returns best (det, FA/hr, thr_d, thr_dur) at <=0.5 FA/hr."""
    all_tmps = []
    DUR_DEFAULT = 16000
    for w in words_subset:
        for v in vecs_by_word_subset.get(w, []):
            all_tmps.append((v, DUR_DEFAULT, w))

    if len(all_tmps) < 2:
        return None

    # positive records (LOO)
    pos_records = []
    for i, (qv, qds, qw) in enumerate(all_tmps):
        dists = []
        for j, (tv, tds, tw) in enumerate(all_tmps):
            if j == i:
                continue
            dists.append((cos_d(qv, tv), j, tw, tds))
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 1:
            d1, idx1, w1, tds1 = dists[0]
            dur_ratio = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
            pos_records.append((d1, dur_ratio))
        else:
            pos_records.append((math.inf, 0.0))

    # sweep distance + duration
    pos_dists = sorted({r[0] for r in pos_records if math.isfinite(r[0])})
    bg_dists_sorted = sorted({r[0] for r in bg_records if math.isfinite(r[0])})
    cands_d = list(pos_dists)
    if len(bg_dists_sorted) > 200:
        step = max(1, len(bg_dists_sorted) // 200)
        for i in range(0, len(bg_dists_sorted), step):
            cands_d.append(bg_dists_sorted[i])
    cands_d = sorted(set(cands_d))
    dur_cands = np.linspace(0.05, 2.0, 15)

    best = None
    for td in cands_d:
        for tdur in dur_cands:
            det = sum(1 for r in pos_records if r[0] <= td and r[1] <= tdur) / len(pos_records)
            fa = 0
            last = -1e9
            for r in bg_records:
                if r[0] <= td and r[1] <= tdur and r[3] - last > REFRACTORY_S:
                    fa += 1
                    last = r[3]
                elif r[0] <= td and r[1] <= tdur:
                    last = r[3]
            fahr = fa / bg_hours if bg_hours else 0.0
            if fahr <= 0.5 and (best is None or det > best[0]):
                best = (det, fahr, td, tdur)
    return best


t0 = time.time()

# 1. Load F03, embed all with duration
print("Loading F03 with duration...", flush=True)
root = os.path.expanduser("~/torgo")
d = H.scan(root).get("F03")
if d is None:
    raise SystemExit("F03 not found")

emb_info = {}
all_wavs = sorted([w for lst in d["commands"].values() for w in lst])
for wav in all_wavs:
    x = read_wav(wav)
    emb_info[wav] = embed(x)
print(f"  {sum(1 for v in emb_info.values() if v[0] is not None)}/{len(all_wavs)} embedded ({time.time()-t0:.0f}s)",
      flush=True)

# 2. Build per-word vecs
vecs_by_word = {}
for word, wavs in d["commands"].items():
    vs = []
    for w in wavs:
        v, ds, dr = emb_info.get(w, (None, 0, 0))
        if v is not None:
            vs.append((v, ds, dr))
    if vs:
        # normalize and average for centroid
        vecs_only = [vi[0] for vi in vs]
        vecs_by_word[word] = vecs_only

all_words = sorted(vecs_by_word.keys())
print(f"  {len(all_words)} words, {sum(len(v) for v in vecs_by_word.values())} utts", flush=True)

# 3. Background scan (reuse same bg as other scripts)
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
        v, ds, dr = embed(x[s:s + win_samples])
        bg_vecs.append(v)
        bg_durs.append(ds)
        bg_times.append(base + (s + win_samples / 2) / SR)
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows ({time.time()-t0:.0f}s)", flush=True)

# Precompute bg distances with default template duration
print("Precomputing bg distance matrix...", flush=True)
TEMPLATE_DUR = 16000  # ~1s default
bg_records_all = []
for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
    if bv is None:
        bg_records_all.append((math.inf, 0.0, None, btc))
        continue
    best_d, best_dur, best_w = math.inf, 0.0, None
    for w in all_words:
        for tv in vecs_by_word[w]:
            d = cos_d(bv, tv)
            d = cos_d(bv, tv)
            # estimate duration for bg — use mean template duration for this word
            tds = 16000  # approx 1s template (rough, not used in dur filter for bg scoring)
            if d < best_d:
                best_d = d
                best_w = w
                best_dur = abs(math.log(max(bds, 1) / max(tds, 1))) if bds > 0 and tds > 0 else 0.0
    bg_records_all.append((best_d, best_dur, best_w, btc))
print(f"  {len(bg_records_all)} bg records ({time.time()-t0:.0f}s)", flush=True)

# 4. Diversity selection
diverse_words = select_diverse(all_words, vecs_by_word, K)
print(f"\nOptimized {K} words (max-min cosine diversity):", flush=True)
for i, w in enumerate(diverse_words):
    if i < 10:
        print(f"  {w}", end="", flush=True)
print(f"\n  ... ({len(diverse_words)} total)", flush=True)

# 5. Evaluate optimized subset
result_opt = evaluate_subset(diverse_words, vecs_by_word, bg_records_all, bg_hours)
print(f"\nOptimized-{K}:", flush=True)
if result_opt:
    det, fa, td, tdur = result_opt
    print(f"  FRR={(1-det)*100:.1f}%  det={det*100:.1f}%  @FA={fa:.2f}/hr  "
          f"d<={td:.4f}  dur<={tdur:.3f}", flush=True)
else:
    print(f"  no valid point", flush=True)

# 6. Random subsets for comparison
print(f"\nRandom-{K} subsets (MC={MC_RANDOM}):", flush=True)
random_dets = []
for mc in range(MC_RANDOM):
    rng = np.random.RandomState(100 + mc)
    rnd = sorted(rng.choice(all_words, K, replace=False).tolist())
    result_rnd = evaluate_subset(rnd, vecs_by_word, bg_records_all, bg_hours)
    if result_rnd:
        random_dets.append(result_rnd[0])
        print(f"  MC{mc}: FRR={(1-result_rnd[0])*100:.1f}%", flush=True)

# 7. All-77 baseline
print(f"\nAll-77 baseline:", flush=True)
result_all = evaluate_subset(all_words, vecs_by_word, bg_records_all, bg_hours)
if result_all:
    det, fa, td, tdur = result_all
    print(f"  FRR={(1-det)*100:.1f}%  det={det*100:.1f}%  @FA={fa:.2f}/hr", flush=True)

# 8. Summary
print(f"\n{'=' * 70}")
print(f"SUMMARY: Vocabulary size vs FRR @0.5FA/hr (F03, WavLM-L12, dual-cascade)")
print(f"{'=' * 70}")
if result_all:
    print(f"  All-77:           FRR={(1-result_all[0])*100:.1f}%")
if result_opt:
    print(f"  Optimized-{K}:    FRR={(1-result_opt[0])*100:.1f}%")
if random_dets:
    mean_r = np.mean(random_dets)
    std_r = np.std(random_dets)
    print(f"  Random-{K} (MC):    FRR={(1-mean_r)*100:.1f}%  std={std_r*100:.1f}%")
    if result_opt:
        frr_opt = (1 - result_opt[0]) * 100
        frr_rnd = (1 - mean_r) * 100
        if frr_rnd > 0:
            rel_vs_random = (frr_rnd - frr_opt) / frr_rnd * 100
            print(f"  Optimized vs Random: {rel_vs_random:+.1f}% rel FRR")
        if result_all:
            frr_all = (1 - result_all[0]) * 100
            if frr_all > 0:
                rel_vs_all = (frr_all - frr_opt) / frr_all * 100
                print(f"  Optimized vs All-77: {rel_vs_all:+.1f}% rel FRR")

print(f"\nTotal: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
