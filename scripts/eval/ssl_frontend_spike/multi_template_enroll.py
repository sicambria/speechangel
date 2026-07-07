"""CP-2 multi-template enrollment spike v2 — fold-based, fixed test set per fold.

Pre-registered H1: Using N ≥ 2 templates per word (from different sessions when available)
vs N=1 reduces FRR at matched ≤0.5 FA/hr by ≥20% relative.

Protocol: k=5 folds (matching harness.folds). For each fold:
  - Test set = fold f (FIXED)
  - Enrollment pool = folds ≠ f
  - For each N ∈ {1, 3, all_from_pool}, randomly select N templates per word from enrollment pool
  - Measure detection at matched ≤0.5 FA/hr
  - Average across folds and Monte Carlo iterations

This keeps the SAME test queries for all N within each fold — only enrollment varies.

Usage: python multi_template_enroll.py [speakers] [bg_minutes] [mc_iters] [k_folds]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

# ----------------------------------------------------------------- config
SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
MC_ITERS = int(sys.argv[3]) if len(sys.argv) > 3 else 5
K_FOLDS = int(sys.argv[4]) if len(sys.argv) > 4 else 5
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MODEL, LAYER = "microsoft/wavlm-base-plus", 12
PV = os.path.expanduser("~/picovoice-benchmark")

# ----------------------------------------------------------------- torch
import torch
torch.set_num_threads(4)
from transformers import AutoModel

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed(x):
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        return None
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def cos_d(a, b):
    return 1.0 - float(a @ b)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


t0 = time.time()

# =================================================================
# 1. Load TORGO, embed all, create k-folds per speaker
# =================================================================
print("Loading TORGO...", flush=True)
import re

speaker_folds = {}  # spk -> [(fold_idx, {word: [(test_wavs), (enroll_pool_wavs)]})]
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo") if not spk.startswith("FC") else os.path.expanduser(
        "~/torgo/FCX")
    d = H.scan(root).get(spk)
    if d is None:
        continue
    folds_list = H.folds(d, K_FOLDS)
    # embed all wavs
    emb_cache = {}
    all_wav_paths = set()
    for fold in folds_list:
        for _, wav in fold["enroll"]:
            all_wav_paths.add(wav)
        for _, wav in fold["positives"]:
            all_wav_paths.add(wav)
    for wav in all_wav_paths:
        emb_cache[wav] = embed(read_wav(wav))

    # group by fold: test set = positives in fold, enrollment pool = enroll entries
    # also extract session info for session-aware selection
    fold_data = []
    for fi, fold in enumerate(folds_list):
        # test queries: (word, vec)
        test_queries = []
        for word, wav in fold["positives"]:
            v = emb_cache.get(wav)
            if v is not None:
                test_queries.append((word, v))

        # enrollment pool: per-word list of (vec, session)
        enroll_pool = {}  # word -> [(vec, session), ...]
        for word, wav in fold["enroll"]:
            v = emb_cache.get(wav)
            if v is None:
                continue
            m = re.search(r'Session(\d+)', wav)
            ses = int(m.group(1)) if m else 0
            enroll_pool.setdefault(word, []).append((v, ses))

        if test_queries and enroll_pool:
            fold_data.append((fi, test_queries, enroll_pool))
    speaker_folds[spk] = fold_data
    n_folds = len(fold_data)
    n_words = len(set(w for fold in fold_data for w in fold[2].keys()))
    total_utts = sum(len(v) for fold in fold_data for v in fold[2].values())
    total_test = sum(len(fold[1]) for fold in fold_data)
    print(f"  {spk}: {n_words} words, {total_utts} enrollment utts, "
          f"{total_test} test queries, {n_folds}/{K_FOLDS} valid folds", flush=True)

# =================================================================
# 2. Background scan
# =================================================================
print(f"\nScanning LibriSpeech ({BG_MIN} min)...", flush=True)
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))

win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_vecs, bg_times, bg_sec_total = [], [], 0.0
for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v = embed(x[s:s + win_samples])
        bg_vecs.append(v)
        bg_times.append(base + (s + win_samples / 2) / SR)
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h bg, {len(bg_vecs)} windows ({time.time()-t0:.0f}s)", flush=True)

# =================================================================
# 3. Per-fold, per-N: measure detection at matched 0.5 FA/hr
# =================================================================
N_TEMPLATES = [1, 2, 3, 0]  # 0 = all from pool


def select_n(enroll_pool, n, rng):
    """Select n templates per word from enroll_pool.
    Prefers different sessions when n >= 2 and multiple sessions available.
    Returns {word: [vecs]}."""
    selected = {}
    for word, candidates in enroll_pool.items():
        if n == 0 or n >= len(candidates):
            selected[word] = [v for v, _ in candidates]
            continue
        # group by session
        by_ses = {}
        for v, ses in candidates:
            by_ses.setdefault(ses, []).append(v)
        sessions = sorted(by_ses.keys())
        # shuffle within each session
        for ses in sessions:
            rng.shuffle(by_ses[ses])
        chosen = []
        # first: one from each session
        for ses in sessions:
            if len(chosen) < n and by_ses[ses]:
                chosen.append(by_ses[ses].pop(0))
        # then: round-robin over sessions for remaining
        si = 0
        while len(chosen) < n:
            ses = sessions[si % len(sessions)]
            if by_ses[ses]:
                chosen.append(by_ses[ses].pop(0))
            si += 1
        selected[word] = chosen[:n]
    return selected


def eval_selection(selected, test_queries):
    """Given per-word selected templates, compute:
    - pos_scores: for each test query, min dist to ANY selected template
    - bg_mins: for each bg window, min dist to ANY selected template"""
    # flatten templates
    all_templates = []
    for word, vecs in selected.items():
        all_templates.extend(vecs)

    pos_scores = []
    for word, qv in test_queries:
        best = min((cos_d(qv, t) for t in all_templates), default=math.inf)
        pos_scores.append(best)

    bg_mins = []
    for bv in bg_vecs:
        if bv is None:
            bg_mins.append(math.inf)
        else:
            bg_mins.append(min((cos_d(bv, t) for t in all_templates), default=math.inf))

    return pos_scores, bg_mins


def det_at_target_fa(pos_scores, bg_mins, target_fa=0.5, n_pts=500):
    """Max detection with FA/hr ≤ target_fa. Returns (det, fa, thr) or None."""
    cands = sorted({d for d in bg_mins if math.isfinite(d)}
                    | {p for p in pos_scores if math.isfinite(p)})
    if len(cands) > n_pts:
        cands = [cands[i] for i in range(0, len(cands), len(cands) // n_pts)]
    best = None
    for t in cands:
        det = sum(1 for p in pos_scores if p <= t) / len(pos_scores) if pos_scores else 0.0
        fa = 0
        last = -1e9
        for d, tc in zip(bg_mins, bg_times):
            if d <= t and tc - last > REFRACTORY_S:
                fa += 1
                last = tc
            elif d <= t:
                last = tc
        fahr = fa / bg_hours if bg_hours else 0.0
        if fahr <= target_fa and (best is None or det > best[0]):
            best = (det, fahr, t)
    return best


print("\n" + "=" * 70)
print(f"MULTI-TEMPLATE ENROLLMENT (k={K_FOLDS}-fold, {MC_ITERS} MC iters, 0.5 FA/hr)")
print("=" * 70)

for spk in SPEAKERS:
    if spk not in speaker_folds or not speaker_folds[spk]:
        continue
    folds = speaker_folds[spk]
    n_folds = len(folds)
    total_test = sum(len(f[1]) for f in folds)
    n_sessions = max(len({ses for f in folds for pool in f[2].values()
                          for _, ses in pool}), 1)
    print(f"\n--- {spk}: {n_folds} folds, {total_test} total test queries, "
          f"{n_sessions} sessions ---", flush=True)
    print(f"  {'N':>6}  {'det@0.5FA/hr':>14}  {'FRR':>8}  {'n_test':>7}  {'n_templ':>7}", flush=True)

    for n in N_TEMPLATES:
        label = "all" if n == 0 else f"N={n}"
        dets = []
        for mc in range(MC_ITERS):
            seed = 42 + mc * 100 + n * 10000
            rng = np.random.RandomState(seed)
            fold_dets = []
            for fi, test_queries, enroll_pool in folds:
                selected = select_n(enroll_pool, n, rng)
                pos, bg = eval_selection(selected, test_queries)
                best = det_at_target_fa(pos, bg, 0.5)
                if best:
                    fold_dets.append(best[0])
            if fold_dets:
                dets.append(sum(fold_dets) / len(fold_dets))  # mean across folds

        if dets:
            mean_det = np.mean(dets)
            std_det = np.std(dets)
            mean_frr = (1 - mean_det) * 100
            # average n_templates and n_test
            avg_templ = np.mean([sum(len(s) for s in select_n(pool, n, np.random.RandomState(0)).values())
                                 for _, _, pool in folds])
            avg_test = total_test / n_folds
            print(f"  {label:>6}  {mean_det*100:>13.1f}%  {mean_frr:>7.1f}%  "
                  f"{avg_test:>7.0f}  {avg_templ:>7.0f}", flush=True)
        else:
            print(f"  {label:>6}  {'no valid point':>14}", flush=True)

    # baseline: all_from_pool vs N=1 comparison
    all_results = []
    n1_results = []
    for mc in range(MC_ITERS):
        seed = 42 + mc * 100
        rng = np.random.RandomState(seed)
        fold_dets_all = []
        fold_dets_n1 = []
        for fi, test_queries, enroll_pool in folds:
            sel_all = select_n(enroll_pool, 0, rng)
            pos_a, bg_a = eval_selection(sel_all, test_queries)
            best_a = det_at_target_fa(pos_a, bg_a, 0.5)
            if best_a:
                fold_dets_all.append(best_a[0])
            sel_1 = select_n(enroll_pool, 1, rng)
            pos_1, bg_1 = eval_selection(sel_1, test_queries)
            best_1 = det_at_target_fa(pos_1, bg_1, 0.5)
            if best_1:
                fold_dets_n1.append(best_1[0])
        if fold_dets_all:
            all_results.append(sum(fold_dets_all) / len(fold_dets_all))
        if fold_dets_n1:
            n1_results.append(sum(fold_dets_n1) / len(fold_dets_n1))

    if all_results and n1_results:
        da = np.mean(all_results)
        d1 = np.mean(n1_results)
        effect = da - d1
        frr_a = (1 - da) * 100
        frr_1 = (1 - d1) * 100
        if frr_1 > 0:
            rel = (frr_1 - frr_a) / frr_1 * 100
        else:
            rel = 0.0
        print(f"  {'★ all vs N=1':<6}  {'Δ = ' + ('+' if effect > 0 else '') + f'{effect*100:.1f}%':>14}  "
              f"{'rel FRR ' + ('+' if rel > 0 else '') + f'{rel:.1f}%':>8}  "
              f"{'direction: ' + ('MORE→BETTER' if rel > 5 else 'MORE→WORSE' if rel < -5 else 'TIE'):>7}",
              flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
