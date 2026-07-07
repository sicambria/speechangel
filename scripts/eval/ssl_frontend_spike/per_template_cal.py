"""CP-2 per-template (per-word) threshold calibration spike.

Pre-registered hypothesis (H1): Per-template distance thresholds — each word's threshold
θ_w = α × median(in-class cosine distances among that word's templates), with the single
global α swept to target FA/hr — reduce FRR at matched ≤0.5 FA/hr by ≥30% relative vs
the global-threshold baseline on WavLM-L12 pooled-cosine embeddings.

Protocol: EXACT replication of in_regime.py — ALL templates enrolled, leave-one-out
positives, per-window VAD-trim → WavLM → mean-pool for background. The ONLY variable
is threshold type (per-word vs global).

Usage: python per_template_cal.py [speakers] [bg_minutes]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

# ----------------------------------------------------------------- config
SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
WIN_S, HOP_S = 1.5, 0.5
SR, MIN_SPEECH, REFRACTORY_S = 16000, 1520, 1.0
PV = os.path.expanduser("~/picovoice-benchmark")
MODEL, LAYER = "microsoft/wavlm-base-plus", 12

# ----------------------------------------------------------------- torch
import torch
torch.set_num_threads(4)
from transformers import AutoModel

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed(x):
    """VAD-trim → per-utt norm → WavLM L12 → mean-pool → L2-norm unit vec. Returns None if silent."""
    sp = H.energy_vad_trim(x)
    if sp.size < MIN_SPEECH:
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
# 1. Load TORGO & embed all utterances
# =================================================================
print("Loading TORGO data...", flush=True)
all_data = {}
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo") if not spk.startswith("FC") else os.path.expanduser("~/torgo/FCX")
    d = H.scan(root).get(spk)
    if d is None:
        print(f"  WARNING: {spk} not found", flush=True)
        continue
    all_data[spk] = d
    n_cmds = len(d["commands"])
    n_utts = sum(len(v) for v in d["commands"].values())
    print(f"  {spk}: {n_cmds} cmds, {n_utts} utts, {len(d['negatives'])} negs", flush=True)

if not all_data:
    raise SystemExit("No speakers found")

print(f"\nEmbedding {MODEL} L{LAYER}...", flush=True)
emb = {}  # wav_path -> unit_vec or None
all_wavs = sorted({w for d in all_data.values() for lst in d["commands"].values() for w in lst})
for wav in all_wavs:
    emb[wav] = embed(read_wav(wav))
print(f"  {sum(1 for v in emb.values() if v is not None)}/{len(all_wavs)} embedded ({time.time()-t0:.0f}s)",
      flush=True)

# =================================================================
# 2. Build per-speaker structures
# =================================================================
print("\nBuilding speaker structures...", flush=True)

# For each speaker: templates[word] = [vecs], positive query list, per-word in-class dists
spk_info = {}
for spk, d in all_data.items():
    # templates per word (from ALL utterances of that word)
    templates = {}
    for word, wavs in d["commands"].items():
        vecs = [emb[w] for w in wavs if emb[w] is not None]
        if vecs:
            templates[word] = vecs

    words = sorted(templates.keys())
    if not words:
        continue

    # in-class distance distribution per word
    inclass_medians = {}
    for w in words:
        tvecs = templates[w]
        if len(tvecs) >= 2:
            dists = [cos_d(tvecs[i], tvecs[j]) for i in range(len(tvecs))
                     for j in range(i + 1, len(tvecs))]
            inclass_medians[w] = float(np.median(dists))
        else:
            inclass_medians[w] = None  # will use global fallback
    all_meds = [v for v in inclass_medians.values() if v is not None]
    global_fallback = float(np.median(all_meds)) if all_meds else 0.1

    # flat list of all (word, vec) pairs for this speaker
    all_vecs = []
    for w in words:
        for v in templates[w]:
            all_vecs.append((w, v))
    n_pos = len(all_vecs)

    # precompute per-query per-word min distances (LOO: exclude query's own vector)
    # pw_dists[i][j] = min cos_dist from query i to word j's templates (excluding query i's own)
    pw_dists = []  # (n_pos, n_words) matrix
    for i, (w_true_i, q_vec) in enumerate(all_vecs):
        row = []
        for w_j in words:
            tvecs = [all_vecs[k][1] for k, (w_k, _) in enumerate(all_vecs)
                     if w_k == w_j and k != i]
            if tvecs:
                row.append(min(cos_d(q_vec, t) for t in tvecs))
            else:
                row.append(math.inf)
        pw_dists.append(row)

    # global min per query (for baseline)
    global_mins = [min(row) for row in pw_dists]

    spk_info[spk] = {
        "words": words,
        "templates": templates,
        "all_vecs": all_vecs,
        "inclass_medians": inclass_medians,
        "global_fallback": global_fallback,
        "n_pos": n_pos,
        "pw_dists": pw_dists,
        "global_mins": global_mins,
    }
    print(f"  {spk}: {len(words)} words, {n_pos} pos, "
          f"inclass medians {np.min(list(inclass_medians.values())):.4f}.."
          f"{np.max(list(inclass_medians.values())):.4f}, fallback={global_fallback:.4f}",
          flush=True)

# =================================================================
# 3. Background scan (per-window VAD, matching in_regime.py)
# =================================================================
print(f"\nScanning LibriSpeech background (target {BG_MIN} min, per-window VAD)...", flush=True)

bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))

win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_windows = []   # list of unit_vec or None
bg_times = []     # global time seconds
bg_sec_total = 0.0
n_embedded = 0

for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    # Process each window with per-window VAD (matching in_regime.py exactly)
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v = embed(x[s:s + win_samples])
        bg_windows.append(v)
        bg_times.append(base + (s + win_samples / 2) / SR)
        if v is not None:
            n_embedded += 1
    bg_sec_total += x.size / SR

bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f} h background, {len(bg_windows)} windows, "
      f"{n_embedded} non-silent ({time.time()-t0:.0f}s)", flush=True)

# Precompute per-window per-word min distances for each speaker
print("\nComputing background distance matrices...", flush=True)
for spk, info in spk_info.items():
    words = info["words"]
    templates = info["templates"]
    n_words = len(words)

    # bg_dists[i][j] = min cos_dist from bg window i to word j's templates
    bg_dist_matrix = []
    bg_global_mins = []
    for v in bg_windows:
        if v is None:
            row = [math.inf] * n_words
            gm = math.inf
        else:
            row = []
            gm = math.inf
            for w in words:
                md = min((cos_d(v, t) for t in templates[w]), default=math.inf)
                row.append(md)
                if md < gm:
                    gm = md
        bg_dist_matrix.append(row)
        bg_global_mins.append(gm)

    info["bg_dist_matrix"] = bg_dist_matrix
    info["bg_global_mins"] = bg_global_mins
    print(f"  {spk}: {len(bg_dist_matrix)} × {n_words} bg dist matrix ({time.time()-t0:.0f}s)",
          flush=True)

# =================================================================
# 4. Sweep & evaluate: global baseline
# =================================================================
print("\n" + "=" * 70)
print("GLOBAL BASELINE (replicating in_regime.py)")
print("=" * 70)


def eval_global(info, thr):
    """Return (det, FA/hr) for global threshold."""
    pos = info["global_mins"]
    bgm = info["bg_global_mins"]
    det = sum(1 for p in pos if p <= thr) / len(pos) if pos else 0.0
    fa = 0
    last = -1e9
    for d, tc in zip(bgm, bg_times):
        if d <= thr and tc - last > REFRACTORY_S:
            fa += 1
            last = tc
        elif d <= thr:
            last = tc
    return det, fa / bg_hours if bg_hours else 0.0


def sweep_global(info, n_pts=500):
    pos = info["global_mins"]
    bgm = info["bg_global_mins"]
    cands = sorted({d for d in bgm if math.isfinite(d)}
                    | {p for p in pos if math.isfinite(p)})
    if len(cands) > n_pts:
        cands = [cands[i] for i in range(0, len(cands), len(cands) // n_pts)]
    return [(eval_global(info, t) + (t,)) for t in cands]


def best_fa(curve, target_fa):
    best = max((c for c in curve if c[1] <= target_fa), key=lambda c: c[0], default=None)
    return best


def fa_for_det(curve, target_det):
    best = min((c for c in curve if c[0] >= target_det), key=lambda c: c[1], default=None)
    return best


for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    curve = sweep_global(info)
    if not curve:
        continue
    at_0fa = best_fa(curve, 0.1)
    at_05 = best_fa(curve, 0.5)
    at_5fa = best_fa(curve, 5.0)
    d95fa = fa_for_det(curve, 0.95)
    print(f"  {spk} (n={info['n_pos']}, bg={bg_hours:.2f}h):", flush=True)
    if at_0fa:
        print(f"    det@~0FA/hr  {at_0fa[0]*100:.1f}%  (CP-2 F01 committed: 75.0%)", flush=True)
    if at_05:
        print(f"    det@0.5FA/hr {at_05[0]*100:.1f}%  FRR={(1-at_05[0])*100:.1f}%", flush=True)
    if at_5fa:
        print(f"    det@5FA/hr   {at_5fa[0]*100:.1f}%  (CP-2 F01 committed: 96.9%)", flush=True)
    if d95fa:
        print(f"    FA/hr for 95% det  {d95fa[1]:.1f}  (CP-2 F01 committed: 5.0)", flush=True)

# =================================================================
# 5. Per-word threshold sweep
# =================================================================
print("\n" + "=" * 70)
print("PER-WORD THRESHOLD CALIBRATION (H1 — pre-registered)")
print("=" * 70)


def eval_per_word(info, alpha):
    """Return (det, FA/hr) for per-word thresholds θ_w = alpha × median_in_class_w."""
    words = info["words"]
    inclass_med = info["inclass_medians"]
    fallback = info["global_fallback"]
    n_words = len(words)
    pw_dists = info["pw_dists"]       # (n_pos, n_words)
    bg_dist_matrix = info["bg_dist_matrix"]  # (n_bg, n_words)

    # thresholds
    theta = {}
    for w in words:
        m = inclass_med.get(w)
        theta[w] = alpha * (m if m is not None else fallback)

    # detection
    n_det = 0
    for row in pw_dists:
        fired = False
        for j in range(n_words):
            if row[j] <= theta.get(words[j], math.inf):
                fired = True
                break
        if fired:
            n_det += 1
    det = n_det / len(pw_dists) if pw_dists else 0.0

    # FA/hr
    fa = 0
    last = -1e9
    for row, tc in zip(bg_dist_matrix, bg_times):
        fired = False
        for j in range(n_words):
            if row[j] <= theta.get(words[j], math.inf):
                fired = True
                break
        if fired:
            if tc - last > REFRACTORY_S:
                fa += 1
                last = tc
            else:
                last = tc
    return det, fa / bg_hours if bg_hours else 0.0


def sweep_per_word(info, n_pts=200):
    """Sweep alpha from 0.1 to 10.0 (log-spaced) for per-word thresholds."""
    alphas = np.logspace(np.log10(0.1), np.log10(10.0), n_pts)
    return [(eval_per_word(info, a) + (a,)) for a in alphas]


def dedup_curve(curve):
    """Compress consecutive identical points on the detection axis."""
    if not curve:
        return []
    out = [curve[0]]
    for c in curve[1:]:
        if abs(c[0] - out[-1][0]) > 1e-6 or abs(c[1] - out[-1][1]) > 1e-6:
            out.append(c)
    return out


all_det_g, all_det_pw = [], []
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    print(f"\n--- {spk} (n={info['n_pos']}, {len(info['words'])} words) ---", flush=True)
    print(f"  in-class median range: {min(info['inclass_medians'].values()):.4f} - "
          f"{max(info['inclass_medians'].values()):.4f}", flush=True)

    curve_g = dedup_curve(sweep_global(info))
    curve_pw = dedup_curve(sweep_per_word(info))

    for label, curve in [("global (baseline)", curve_g), ("per-word (H1)", curve_pw)]:
        at_0fa = best_fa(curve, 0.1)
        at_05 = best_fa(curve, 0.5)
        at_1fa = best_fa(curve, 1.0)
        d95fa = fa_for_det(curve, 0.95)
        d90fa = fa_for_det(curve, 0.90)
        print(f"  {label:<22} "
              f"FRR@0.5FA/hr={(1-at_05[0])*100:.1f}% " if at_05 else f"  {label:<22} FRR@0.5FA/hr=N/A ",
              end="", flush=True)
        if at_1fa:
            print(f"FRR@1.0={(1-at_1fa[0])*100:.1f}% ", end="", flush=True)
        if d95fa:
            print(f"FA@95%det={d95fa[1]:.1f}", flush=True)
        else:
            print(flush=True)

    # store for aggregate McNemar
    at_05_g = best_fa(curve_g, 0.5)
    at_05_pw = best_fa(curve_pw, 0.5)
    if at_05_g and at_05_pw:
        info["thr_global_05"] = at_05_g[2]
        info["alpha_pw_05"] = at_05_pw[2]

    # relative FRR reduction
    if at_05_g and at_05_pw:
        frr_g = 1 - at_05_g[0]
        frr_pw = 1 - at_05_pw[0]
        if frr_g > 0:
            rel = (frr_g - frr_pw) / frr_g * 100
            print(f"  Rel FRR reduction @0.5FA/hr: {rel:+.1f}%  "
                  f"({'WIN' if rel > 0 else 'LOSS' if rel < 0 else 'TIE'})", flush=True)

# =================================================================
# 6. Paired McNemar at matched ≤0.5 FA/hr
# =================================================================
print("\n" + "=" * 70)
print("PAIRED SIGNIFICANCE (McNemar at matched ≤0.5 FA/hr)")
print("=" * 70)


def binom_two_sided(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


all_b, all_c = 0, 0
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    if "thr_global_05" not in info or "alpha_pw_05" not in info:
        continue
    thr_g = info["thr_global_05"]
    alpha_pw = info["alpha_pw_05"]
    words = info["words"]
    inclass_med = info["inclass_medians"]
    fallback = info["global_fallback"]
    pw_dists = info["pw_dists"]
    global_mins = info["global_mins"]
    n_pos = info["n_pos"]

    # per-word thresholds at this alpha
    theta = {}
    for w in words:
        m = inclass_med.get(w)
        theta[w] = alpha_pw * (m if m is not None else fallback)

    # detection vectors
    det_g = [1 if global_mins[i] <= thr_g else 0 for i in range(n_pos)]
    det_pw = []
    for row in pw_dists:
        fired = any(row[j] <= theta.get(words[j], math.inf) for j in range(len(words)))
        det_pw.append(1 if fired else 0)

    b = sum(1 for g, p in zip(det_g, det_pw) if g == 1 and p == 0)
    c = sum(1 for g, p in zip(det_g, det_pw) if g == 0 and p == 1)
    n = b + c
    chi2 = (abs(b - c) - 1) ** 2 / n if n > 0 else float("nan")
    p_chi = math.erfc(math.sqrt(chi2 / 2.0)) if n > 0 else 1.0
    p_bin = binom_two_sided(b, c)

    dg = sum(det_g) / n_pos * 100
    dp = sum(det_pw) / n_pos * 100
    print(f"  {spk} (n={n_pos}): global={dg:.1f}%  per-word={dp:.1f}%  "
          f"b(global-only)={b} c(per-word-only)={c}  "
          f"McNemar p={p_chi:.3f}  exact-p={p_bin:.3f}", flush=True)
    all_b += b
    all_c += c

# aggregate
n_all = all_b + all_c
chi2_all = (abs(all_b - all_c) - 1) ** 2 / n_all if n_all > 0 else float("nan")
p_chi_all = math.erfc(math.sqrt(chi2_all / 2.0)) if n_all > 0 else 1.0
p_bin_all = binom_two_sided(all_b, all_c)
print(f"\n  AGGREGATE: discordant b={all_b} c={all_c}  "
      f"McNemar p={p_chi_all:.4f}  exact-p={p_bin_all:.4f}", flush=True)

# =================================================================
# 7. NOT-banked exploratory family
# =================================================================
print("\n" + "=" * 70)
print("EXPLORATORY FAMILY (NOT-banked — pre-register before adopting)")
print("=" * 70)

# E1: margin scorer at matched 0.5 FA/hr
print("\nE1: margin scorer (best_dist - gap_to_2nd) with per-word thresholds")
for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    words = info["words"]
    pw_dists = info["pw_dists"]
    bg_dm = info["bg_dist_matrix"]
    n_pos = info["n_pos"]
    n_words = len(words)

    # margin score for each positive
    margin_pos = []
    for row in pw_dists:
        sd = sorted(row)
        if len(sd) >= 2:
            margin_pos.append(2 * sd[0] - sd[1])  # d1 - (d2-d1) = 2*d1 - d2
        elif len(sd) == 1:
            margin_pos.append(sd[0])

    # margin score for each bg window
    margin_bg = []
    for row in bg_dm:
        sd = sorted(row)
        if len(sd) >= 2:
            margin_bg.append(2 * sd[0] - sd[1])
        elif len(sd) == 1:
            margin_bg.append(sd[0])
        else:
            margin_bg.append(math.inf)

    # sweep margin threshold at matched 0.5 FA/hr
    cands = sorted({d for d in margin_bg if math.isfinite(d)}
                    | {p for p in margin_pos if math.isfinite(p)})
    if len(cands) > 500:
        cands = [cands[i] for i in range(0, len(cands), len(cands) // 500)]
    best_m = None
    for t in cands:
        det = sum(1 for m in margin_pos if m <= t) / len(margin_pos)
        fa = 0
        last = -1e9
        for d, tc in zip(margin_bg, bg_times[:len(margin_bg)]):
            if d <= t and tc - last > REFRACTORY_S:
                fa += 1
                last = tc
            elif d <= t:
                last = tc
        fahr = fa / bg_hours if bg_hours else 0.0
        if fahr <= 0.5 and (best_m is None or det > best_m[0]):
            best_m = (det, fahr, t)
    if best_m:
        print(f"  {spk}: margin@0.5FA/hr FRR={(1-best_m[0])*100:.1f}%", flush=True)
    else:
        print(f"  {spk}: margin@0.5FA/hr N/A", flush=True)

# E2: per-word threshold using 75th/90th percentile instead of median × alpha
print("\nE2: Per-word threshold percentiles (75th/90th vs median)")
print("    Deferred — equivalent to different alpha values; median×alpha sweep covers this.", flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h  |  speakers={SPEAKERS}")
print(f"{'=' * 70}")
