"""Frame-level QbE-DTW arm for the typical-900 journey (the one untested representation axis).

Change-one-variable vs the mean-pool baseline (EVAL-004): IDENTICAL speakers / words / folds / K /
held-out-global-threshold / FAR machinery as a5.kcurve_speaker + t7.scored_folds; the ONLY change is
the matcher — mean-pool+cosine  →  per-frame-L2-norm + banded length-normalized DTW (frame-QbE-DTW).

Preprocessing is byte-identical to a5.embed_net (VAD-trim, pad-to-1520, zero-mean/unit-var) except
`.mean(0)+L2` is replaced by per-frame L2-norm — so a single-mean-pooled-frame degenerate reproduces
the 5.81% baseline (F0(a), isolates the DP), and the cosine baseline on this speaker set is 5.81%
(F0(b), f0_pin.py, isolates the speaker set).

Modes:
  build [layers]  — encode the a5 manifest clips at the given layers (frames_norm), cache to npz.
  f0a             — degenerate DP check: feed mean-pool vectors as (1,H) frames -> must equal 5.81%.
  e1  [layer]     — full frame-DTW held-out FRR@FAR<=5% + hard-speaker below/wrong split + per-query
                    outcome dump for the matched-FAR McNemar.
"""
import os, sys, json, collections
import numpy as np
import cand_lib as L
import harness as H
from a5_gsc_kcurve import build_cache, kcurve_speaker
from t10_c3_student import manifest_from_picks

CACHE = L.CACHE
LAYERS_DEFAULT = [6, 9, 12, 15]
K = 5
FAR = 0.05


# ---------------------------------------------------------------- frame cache (frames_norm)

MODELS = {"wavlm_large": "microsoft/wavlm-large", "distilhubert": "ntu-spml/distilhubert"}


def frame_path(layer, tag="wavlm_large"):
    return os.path.join(CACHE, f"gsc_{tag}_frames_L{layer}.npz")


def encode_frames(net, path, layers):
    import torch, soundfile as sf
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
    out = {}
    for lyr in layers:
        h = hs[lyr][0].numpy().astype(np.float32)          # (T, H)
        n = np.linalg.norm(h, axis=1, keepdims=True) + 1e-8
        out[lyr] = (h / n).astype(np.float16)              # frames_norm, fp16 to save disk
    return out


def build(layers, tag="wavlm_large"):
    import torch
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    man, need = manifest_from_picks()
    need = list(dict.fromkeys(need))                        # unique, preserve order
    caches = {lyr: (dict(np.load(frame_path(lyr, tag), allow_pickle=True))
                    if os.path.exists(frame_path(lyr, tag)) else {}) for lyr in layers}
    todo = [p for p in need if any(p not in caches[lyr] for lyr in layers)]
    print(f"  frame-encode {len(todo)}/{len(need)} clips @ {tag} layers {layers}", flush=True)
    if todo:
        net = AutoModel.from_pretrained(MODELS[tag], output_hidden_states=True).eval()
        for i, p in enumerate(todo):
            fr = encode_frames(net, p, layers)
            for lyr in layers:
                caches[lyr][p] = fr[lyr]
            if (i + 1) % 100 == 0:
                print(f"    {i+1}/{len(todo)}", flush=True)
                for lyr in layers:
                    np.savez(frame_path(lyr, tag), **caches[lyr])
    for lyr in layers:
        np.savez(frame_path(lyr, tag), **caches[lyr])
    print(f"  wrote {tag} frame caches for layers {layers} ({len(need)} clips each)", flush=True)


def load_frames(layer, tag="wavlm_large"):
    z = np.load(frame_path(layer, tag), allow_pickle=True)
    return {k: z[k].astype(np.float32) for k in z.files}     # (T,H) fp32 for DTW


# ---------------------------------------------------------------- DTW (length-normalized banded)

def dtw_norm(qf, tf, band_ratio=0.1):
    """Banded length-normalized DTW, euclidean local cost on unit frames (== cosine-DTW), /(n+m).
    Matches harness.dtw_distance semantics; cost precomputed via one matmul (unit frames:
    ||qi-tj|| = sqrt(2-2 qi.tj)). For n=m=1 collapses to euclidean(q,t)/2 (monotone in cosine)."""
    n, m = qf.shape[0], tf.shape[0]
    if n == 0 or m == 0:
        return np.inf
    d = 2.0 - 2.0 * (qf @ tf.T)
    np.clip(d, 0.0, None, out=d)
    cost = np.sqrt(d)                                        # (n, m)
    band = max(1, int(band_ratio * max(n, m)))
    ratio = m / n
    INF = np.inf
    prev = np.full(m + 1, INF); prev[0] = 0.0
    curr = np.full(m + 1, INF)
    for i in range(1, n + 1):
        curr[:] = INF
        center = int((i - 1) * ratio)
        j0 = max(1, center - band + 1)
        j1 = min(center + band, m)
        ci = cost[i - 1]
        for j in range(j0, j1 + 1):
            if abs((i - 1) - int((j - 1) / ratio)) > band:
                continue
            best = prev[j]
            if curr[j - 1] < best: best = curr[j - 1]
            if prev[j - 1] < best: best = prev[j - 1]
            if best != INF:
                curr[j] = ci[j - 1] + best
        prev, curr = curr, prev
    acc = prev[m]
    return INF if acc == INF else acc / (n + m)


def speaker_dtw_matrix(man_s, fr, band_ratio=0.1):
    """Precompute DTW[(qpath, tpath)] for every query clip vs every template (pos) clip of a speaker.
    Templates = the speaker's pos clips; queries = pos + neg clips. Memoized, computed once."""
    pos_paths = [p for w in man_s["fixed"] for p in man_s["fixed"][w]]
    query_paths = pos_paths + list(man_s["neg"])
    D = {}
    for qp in query_paths:
        qf = fr[qp]
        for tp in pos_paths:
            if qp == tp:
                continue
            D[(qp, tp)] = dtw_norm(qf, fr[tp], band_ratio)
    return D


# ---------------------------------------------------------------- scoring (mirror t7.scored_folds)

def score_query_frame(qp, enroll_paths, D, agg="min"):
    """enroll_paths = {word:[tpath,...]}. Return sorted [(dist, word)] using min-DTW over templates."""
    out = []
    for w, tps in enroll_paths.items():
        ds = sorted(D[(qp, tp)] for tp in tps if (qp, tp) in D)
        if not ds:
            continue
        out.append((ds[0] if agg == "min" else float(np.mean(ds)), w))
    out.sort()
    return out


def scored_folds_frame(man_s, D, k_enroll=K):
    """EXACT mirror of t7.scored_folds fold/enroll/K/min-agg, but paths+DTW instead of vecs+cosine.
    Rows carry the query wav path (qp) so the two arms pair per-query for McNemar."""
    words = {w: list(ps) for w, ps in man_s["fixed"].items()}
    negs = list(man_s["neg"])
    pos, neg = [], []
    for w, paths in words.items():
        for i, qp in enumerate(paths):
            f = i % 5
            enroll = {}
            for ww, pp in words.items():
                pool = [pp[j] for j in range(len(pp)) if (j % 5) != f]
                if ww == w:
                    pool = [pp[j] for j in range(len(pp)) if j != i and (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:k_enroll]
            if enroll:
                pos.append((f, w, qp, score_query_frame(qp, enroll, D)))
    for ni, np_ in enumerate(negs):
        f = ni % 5
        enroll = {}
        for ww, pp in words.items():
            pool = [pp[j] for j in range(len(pp)) if (j % 5) != f]
            if pool:
                enroll[ww] = pool[:k_enroll]
        if enroll:
            neg.append((f, np_, score_query_frame(np_, enroll, D)))
    return pos, neg


def scored_folds_meanpool(man_s, emb, layer):
    """t7.scored_folds (cosine mean-pool) but carrying qp — the paired baseline arm, same wav keys."""
    words = {w: [(p, emb[p][layer]) for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [(p, emb[p][layer]) for p in man_s["neg"]]
    pos, neg = [], []
    for w, pvs in words.items():
        for i, (qp, qv) in enumerate(pvs):
            f = i % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j][1] for j in range(len(vv)) if (j % 5) != f]
                if ww == w:
                    pool = [vv[j][1] for j in range(len(vv)) if j != i and (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                pos.append((f, w, qp, L.score_query(qv, enroll, "min")))
    for ni, (npth, nv) in enumerate(negs):
        f = ni % 5
        enroll = {}
        for ww, vv in words.items():
            pool = [vv[j][1] for j in range(len(vv)) if (j % 5) != f]
            if pool:
                enroll[ww] = pool[:K]
        if enroll:
            neg.append((f, npth, L.score_query(nv, enroll, "min")))
    return pos, neg


def heldout_from_scored(pos, neg, target=FAR):
    """Leave-one-fold-out FRR/FAR from scored rows (mirror cand_lib.held_out_frr_far), and also return
    per-pos-query records (wav, accepted, correct, top1_dist, top1_word, truth) + neg top1 dists."""
    acc = p = fa = ng = 0
    recs = []
    neg_top1 = []
    for testf in range(5):
        trp = [s for f, w, qp, s in pos if f != testf and s]
        trn = [s for f, npth, s in neg if f != testf and s]
        accept = L.global_threshold_accept(trp, trn, target)
        for f, w, qp, s in pos:
            if f != testf or not s:
                continue
            p += 1
            top1d, top1w = s[0]
            accepted = bool(accept(s))
            correct = accepted and top1w == w
            if correct:
                acc += 1
            recs.append({"wav": qp, "fold": f, "truth": w, "top1w": top1w, "top1d": float(top1d),
                         "accepted": accepted, "correct": correct})
        for f, npth, s in neg:
            if f != testf or not s:
                continue
            ng += 1
            neg_top1.append(float(s[0][0]))
            if accept(s):
                fa += 1
    frr = 0.0 if p == 0 else 1.0 - acc / p
    far = 0.0 if ng == 0 else fa / ng
    return frr, far, p, ng, recs, neg_top1


# ---------------------------------------------------------------- F0(a) degenerate DP check

def f0a():
    """Feed the mean-pool L12 unit vectors as (1,H) single frames -> DTW collapses to local cost,
    ranking == cosine -> must reproduce 5.81%/912 (isolates the DP code, EVAL-004)."""
    man, emb = build_cache()
    spks = list(man.keys())
    num = den = fnum = fden = 0
    for s in spks:
        fr = {}
        for w, ps in man[s]["fixed"].items():
            for pth in ps:
                fr[pth] = emb[pth][12][None, :].astype(np.float32)
        for pth in man[s]["neg"]:
            fr[pth] = emb[pth][12][None, :].astype(np.float32)
        D = speaker_dtw_matrix(man[s], fr)
        pos, neg = scored_folds_frame(man[s], D)
        frr, far, p, ng, _, _ = heldout_from_scored(pos, neg)
        num += frr * p; den += p; fnum += far * ng; fden += ng
    agg, faa = num / den, fnum / fden
    ok = abs(agg - 0.0581) < 0.0005 and den == 912
    print(f"F0(a) degenerate single-mean-frame DTW: FRR {agg*100:.2f}% @ FAR {faa*100:.2f}% npos={den}")
    print(f"  DP {'OK — reproduces 5.81%/912 (DP code faithful)' if ok else 'MISMATCH — DP bug'}")


# ---------------------------------------------------------------- matched-FAR McNemar

def thr_for_far(neg_top1, target):
    """Largest global threshold with realized FAR over pooled negatives <= target (mirrors the
    global_threshold_accept selection rule, but pooled for a matched-operating-point paired test)."""
    if not neg_top1:
        return np.inf
    cands = sorted(set(neg_top1))
    thr = cands[0] - 1.0
    n = len(neg_top1)
    for t in cands:
        if sum(1 for d in neg_top1 if d <= t) / n <= target:
            thr = t
    return thr


def matched_mcnemar(m_recs, m_neg, f_recs, f_neg, targets=(0.02, 0.0389, 0.05, 0.08), blabel="variant"):
    """Re-threshold BOTH arms to a common target FAR on pooled negatives, then McNemar on per-wav
    accept-correct (EVAL-007: verdict at matched realized FAR). Multiple FAR points give a curve
    summary (EVAL-005) so the verdict does not rest on one operating-point extreme. NOTE: these pooled
    single-threshold FRRs are HARSHER than the per-speaker leave-one-fold-out held-out FRR (a global
    cross-speaker threshold); both conventions favor the same arm — the McNemar is the paired verdict."""
    M = {r["wav"]: r for r in m_recs}
    Fh = {r["wav"]: r for r in f_recs}
    keys = [w for w in M if w in Fh]
    rows = []
    for tgt in targets:
        tm, tf = thr_for_far(m_neg, tgt), thr_for_far(f_neg, tgt)
        far_m = float(np.mean([d <= tm for d in m_neg])); far_f = float(np.mean([d <= tf for d in f_neg]))
        Acorr = {w: int(M[w]["top1d"] <= tm and M[w]["top1w"] == M[w]["truth"]) for w in keys}
        Bcorr = {w: int(Fh[w]["top1d"] <= tf and Fh[w]["top1w"] == Fh[w]["truth"]) for w in keys}
        b = sum(1 for w in keys if Acorr[w] == 1 and Bcorr[w] == 0)   # mean-pool right, variant wrong
        c = sum(1 for w in keys if Acorr[w] == 0 and Bcorr[w] == 1)   # mean-pool wrong, variant right
        nn = b + c
        chi2 = (abs(b - c) - 1) ** 2 / nn if nn else float("nan")
        import math
        p = math.erfc(math.sqrt(chi2 / 2.0)) if nn else 1.0
        frr_m = 1 - sum(Acorr.values()) / len(keys)
        frr_f = 1 - sum(Bcorr.values()) / len(keys)
        rows.append({"target_far": tgt, "far_meanpool": far_m, "far_variant": far_f,
                     "frr_meanpool_pooled": frr_m, "frr_variant_pooled": frr_f, "b": b, "c": c,
                     "chi2": float(chi2) if nn else None, "p": float(p)})
        star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  McNemar @FAR≤{tgt*100:.2f}%: mean-pool FRR {frr_m*100:.2f}% (FAR {far_m*100:.2f}%) vs "
              f"{blabel} FRR {frr_f*100:.2f}% (FAR {far_f*100:.2f}%)  b={b} c={c} χ²={chi2:.2f} p={p:.2e} {star}"
              f"  {blabel+' better' if c > b else 'mean-pool better' if b > c else 'tie'}")
    # partial-AUC over the pooled top-1 scores (0-10% FAR): area of FRR-vs-FAR, lower=better (EVAL-005)
    return rows


# ---------------------------------------------------------------- E1 full frame-DTW (both arms, paired)

def e1(layer=12, band_ratio=0.1):
    man, emb = build_cache()
    fr_all = load_frames(layer)
    spks = list(man.keys())
    fn = fd = ffn = ffd = 0; f_per = {}; f_recs = []; f_neg = []
    mn = md = mfn = mfd = 0; m_per = {}; m_recs = []; m_neg = []
    tot_wrong = tot_below = tot_fr = 0
    hard = {"98ea0818", "2aca1e72", "c1d39ce8"}
    for s in spks:
        fr = {p: fr_all[p] for w in man[s]["fixed"] for p in man[s]["fixed"][w]}
        fr.update({p: fr_all[p] for p in man[s]["neg"]})
        D = speaker_dtw_matrix(man[s], fr, band_ratio)
        fpos, fneg = scored_folds_frame(man[s], D)
        frr, far, p, ng, recs, ntop = heldout_from_scored(fpos, fneg)
        fn += frr * p; fd += p; ffn += far * ng; ffd += ng
        f_per[s] = frr; f_recs += recs; f_neg += ntop
        mpos, mneg = scored_folds_meanpool(man[s], emb, 12)
        frrm, farm, pm, ngm, recsm, ntopm = heldout_from_scored(mpos, mneg)
        mn += frrm * pm; md += pm; mfn += farm * ngm; mfd += ngm
        m_per[s] = frrm; m_recs += recsm; m_neg += ntopm
        if any(s.startswith(h) for h in hard):
            nfr = sum(1 for r in recs if not r["correct"])
            nw = sum(1 for r in recs if not r["correct"] and r["top1w"] != r["truth"])
            tot_wrong += nw; tot_below += nfr - nw; tot_fr += nfr
    agg, faa = fn / fd, ffn / ffd
    aggm, faam = mn / md, mfn / mfd
    band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
    print(f"\nE1 FRAME-QbE-DTW  wavlm-large L{layer} K{K} band_ratio={band_ratio}")
    print(f"  frame-DTW  aggregate FRR = {agg*100:.2f}%  @ FAR {faa*100:.2f}%  npos={fd}  -> band {band}")
    print(f"  mean-pool  aggregate FRR = {aggm*100:.2f}%  @ FAR {faam*100:.2f}%  (paired baseline; pin 5.81%)")
    hs = sorted(spks, key=lambda s: -f_per[s])[:5]
    print("  frame-DTW hardest: " + " ".join(f"{s[:8]}={f_per[s]*100:.0f}%" for s in hs))
    for h in ["98ea0818", "2aca1e72", "c1d39ce8", "893705bb"]:
        mk = [s for s in spks if s.startswith(h)]
        if mk:
            print(f"    {h}: frame-DTW {f_per[mk[0]]*100:.0f}%  vs mean-pool {m_per[mk[0]]*100:.0f}%")
    if tot_fr:
        print(f"  hard-speaker FR split (frame-DTW): {tot_fr} FR = {tot_wrong} wrong-word "
              f"({tot_wrong/tot_fr*100:.0f}%) + {tot_below} below-thr ({tot_below/tot_fr*100:.0f}%)"
              f"   (mean-pool baseline: 41% wrong / 59% below)")
    print("  --- matched-FAR paired McNemar (EVAL-007) ---")
    mc = matched_mcnemar(m_recs, m_neg, f_recs, f_neg, blabel="frame-DTW")
    out = {"layer": layer, "band_ratio": band_ratio,
           "frame": {"agg_frr": agg, "agg_far": faa, "band": band, "per_spk": f_per},
           "meanpool": {"agg_frr": aggm, "agg_far": faam, "per_spk": m_per},
           "hard_split": {"n_fr": tot_fr, "n_wrong": tot_wrong, "n_below": tot_below},
           "mcnemar": mc}
    with open(os.path.join(CACHE, f"frame_qbe_e1_L{layer}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"  wrote frame_qbe_e1_L{layer}.json")


# ---------------------------------------------------------------- E4 frame-aware pooling (non-DTW)

def pool_vec(frames, mode):
    """frames: (T,H) frames_norm. Return a single vector for a frame-AWARE pooling, then L2-normed.
    Tests whether keeping more than the mean (temporal distribution / salient frames) helps —
    the non-alignment half of the frame-level axis (attentive/GeM/statistics pooling)."""
    if mode == "mean":
        v = frames.mean(0)
    elif mode == "std":                              # std-alone: is the 2nd moment (not 2× dim) the lever?
        v = frames.std(0)
    elif mode == "meanstd":                          # statistics pooling: mean ⊕ std (within-word scatter)
        v = np.concatenate([frames.mean(0), frames.std(0)])
    elif mode == "max":                              # per-dim max-abs (salient-frame emphasis)
        v = frames[np.argmax(np.abs(frames), axis=0), np.arange(frames.shape[1])]
    elif mode == "gem":                              # generalized mean over |frames| with sign of mean (p=3)
        p = 3.0
        s = np.sign(frames.mean(0))
        v = s * (np.abs(frames) ** p).mean(0) ** (1.0 / p)
    else:
        raise ValueError(mode)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def e4(layer=12):
    """Frame-aware pooling variants at one layer vs mean (all cosine 1-NN, kcurve_flat, K5, FAR-matched).
    'mean' must reproduce ~5.81% (sanity that frames_norm-mean ≈ baseline mean-pool)."""
    from t7_layer_negative import kcurve_flat
    man, _ = build_cache()
    fr_all = load_frames(layer)
    spks = list(man.keys())
    print(f"\nE4 FRAME-AWARE POOLING  wavlm-large L{layer} K{K}  (vs mean-pool baseline 5.81%)")
    res = {}
    for mode in ["mean", "std", "meanstd", "max", "gem"]:
        emb_flat = {p: pool_vec(fr_all[p], mode) for s in spks
                    for p in ([q for w in man[s]["fixed"] for q in man[s]["fixed"][w]] + list(man[s]["neg"]))}
        num = den = fnum = fden = 0
        for s in spks:
            sub = {p: emb_flat[p] for w in man[s]["fixed"] for p in man[s]["fixed"][w]}
            sub.update({p: emb_flat[p] for p in man[s]["neg"]})
            frr, far, p_, ng = kcurve_flat(man[s], sub, K)
            num += frr * p_; den += p_; fnum += far * ng; fden += ng
        agg, faa = num / den, fnum / fden
        band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
        res[mode] = {"frr": agg, "far": faa, "band": band}
        tag = "  <- sanity (frames_norm-mean ≈ baseline)" if mode == "mean" else ""
        print(f"  {mode:>8}: FRR {agg*100:5.2f}%  @ FAR {faa*100:.2f}%  band {band}"
              f"  {'≤baseline' if agg <= 0.0581 else f'+{(agg-0.0581)*100:.1f}pp'}{tag}")
    with open(os.path.join(CACHE, f"frame_qbe_e4_L{layer}.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(f"  wrote frame_qbe_e4_L{layer}.json")


def scored_folds_flat(man_s, emb_flat):
    """scored_folds on a flat {path: vec} dict (one vector per clip), cosine min-agg, carrying qp."""
    words = {w: [(p, emb_flat[p]) for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [(p, emb_flat[p]) for p in man_s["neg"]]
    pos, neg = [], []
    for w, pvs in words.items():
        for i, (qp, qv) in enumerate(pvs):
            f = i % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j][1] for j in range(len(vv)) if (j % 5) != f]
                if ww == w:
                    pool = [vv[j][1] for j in range(len(vv)) if j != i and (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                pos.append((f, w, qp, L.score_query(qv, enroll, "min")))
    for ni, (npth, nv) in enumerate(negs):
        f = ni % 5
        enroll = {}
        for ww, vv in words.items():
            pool = [vv[j][1] for j in range(len(vv)) if (j % 5) != f]
            if pool:
                enroll[ww] = pool[:K]
        if enroll:
            neg.append((f, npth, L.score_query(nv, enroll, "min")))
    return pos, neg


def confirm_pool(mode="meanstd", layer=12, tag="wavlm_large", mp_layer=None):
    """Rigorous paired confirmation of a mined pooling variant vs the SHIPPED mean-pool baseline
    (raw mean-pool: wavlm-large L12 = 5.81% / distilhubert L2 = 9.32%). Matched-FAR McNemar (EVAL-007)
    + hard-speaker below/wrong split + per-fold direction (EVAL-005). tag != wavlm_large is the fresh
    cross-ENCODER confirmation EVAL-003 requires before a mined lever is banked."""
    man, wemb = build_cache()                                     # manifest (clips) — encoder-independent
    if tag == "wavlm_large":
        emb = wemb; mp_layer = mp_layer or 12
    else:
        z = np.load(os.path.join(CACHE, f"gsc_{tag}_alllayers.npz"), allow_pickle=True)
        emb = {k: z[k] for k in z.files}; mp_layer = mp_layer or 2
    fr_all = load_frames(layer, tag)
    spks = list(man.keys())
    emb_flat = {p: pool_vec(fr_all[p], mode) for s in spks
                for p in ([q for w in man[s]["fixed"] for q in man[s]["fixed"][w]] + list(man[s]["neg"]))}
    bn = bd = bfn = bfd = 0; b_per = {}; b_recs = []; b_neg = []      # baseline (shipped mean-pool)
    vn = vd = vfn = vfd = 0; v_per = {}; v_recs = []; v_neg = []      # pooling variant
    tot_wrong = tot_below = tot_fr = 0
    hard = {"98ea0818", "2aca1e72", "c1d39ce8"}
    dir_better = dir_worse = dir_tie = 0
    for s in spks:
        bpos, bneg = scored_folds_meanpool(man[s], emb, mp_layer)
        frrb, farb, pb, ngb, recsb, ntopb = heldout_from_scored(bpos, bneg)
        bn += frrb * pb; bd += pb; bfn += farb * ngb; bfd += ngb; b_per[s] = frrb
        b_recs += recsb; b_neg += ntopb
        sub = {p: emb_flat[p] for w in man[s]["fixed"] for p in man[s]["fixed"][w]}
        sub.update({p: emb_flat[p] for p in man[s]["neg"]})
        vpos, vneg = scored_folds_flat(man[s], sub)
        frrv, farv, pv, ngv, recsv, ntopv = heldout_from_scored(vpos, vneg)
        vn += frrv * pv; vd += pv; vfn += farv * ngv; vfd += ngv; v_per[s] = frrv
        v_recs += recsv; v_neg += ntopv
        if frrv < frrb - 1e-9: dir_better += 1
        elif frrv > frrb + 1e-9: dir_worse += 1
        else: dir_tie += 1
        if any(s.startswith(h) for h in hard):
            nfr = sum(1 for r in recsv if not r["correct"])
            nw = sum(1 for r in recsv if not r["correct"] and r["top1w"] != r["truth"])
            tot_wrong += nw; tot_below += nfr - nw; tot_fr += nfr
    aggb, faab = bn / bd, bfn / bfd
    aggv, faav = vn / vd, vfn / vfd
    band = 900 if aggv <= 0.05 else (800 if aggv <= 0.15 else 700)
    print(f"\nCONFIRM  pool={mode}  {tag} L{layer}  vs shipped mean-pool {tag} L{mp_layer}")
    print(f"  {mode:>8}  held-out FRR = {aggv*100:.2f}%  @ FAR {faav*100:.2f}%  npos={vd}  -> band {band}")
    print(f"  mean-pool held-out FRR = {aggb*100:.2f}%  @ FAR {faab*100:.2f}%")
    print(f"  per-speaker direction ({mode} vs mean-pool): better {dir_better}, worse {dir_worse}, tie {dir_tie} (of 19)")
    for h in ["98ea0818", "2aca1e72", "c1d39ce8", "893705bb"]:
        mk = [s for s in spks if s.startswith(h)]
        if mk:
            print(f"    {h}: {mode} {v_per[mk[0]]*100:.0f}%  vs mean-pool {b_per[mk[0]]*100:.0f}%")
    if tot_fr:
        print(f"  hard-speaker FR split ({mode}): {tot_fr} FR = {tot_wrong} wrong ({tot_wrong/tot_fr*100:.0f}%)"
              f" + {tot_below} below-thr ({tot_below/tot_fr*100:.0f}%)  (baseline 41/59)")
    print("  --- matched-FAR paired McNemar (A=mean-pool, B=%s) ---" % mode)
    mc = matched_mcnemar(b_recs, b_neg, v_recs, v_neg, blabel=mode)
    out = {"mode": mode, "layer": layer,
           "variant": {"agg_frr": aggv, "agg_far": faav, "band": band, "per_spk": v_per},
           "meanpool": {"agg_frr": aggb, "agg_far": faab, "per_spk": b_per},
           "direction": {"better": dir_better, "worse": dir_worse, "tie": dir_tie},
           "hard_split": {"n_fr": tot_fr, "n_wrong": tot_wrong, "n_below": tot_below},
           "tag": tag, "mp_layer": mp_layer, "mcnemar": mc}
    with open(os.path.join(CACHE, f"frame_qbe_confirm_{tag}_{mode}_L{layer}.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"  wrote frame_qbe_confirm_{tag}_{mode}_L{layer}.json")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "e1"
    if mode == "build":
        layers = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else LAYERS_DEFAULT
        build(layers, sys.argv[3] if len(sys.argv) > 3 else "wavlm_large")
    elif mode == "f0a":
        f0a()
    elif mode == "e1":
        e1(int(sys.argv[2]) if len(sys.argv) > 2 else 12,
           float(sys.argv[3]) if len(sys.argv) > 3 else 0.1)
    elif mode == "e4":
        e4(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    elif mode == "confirm":
        confirm_pool(sys.argv[2] if len(sys.argv) > 2 else "meanstd",
                     int(sys.argv[3]) if len(sys.argv) > 3 else 12,
                     sys.argv[4] if len(sys.argv) > 4 else "wavlm_large",
                     int(sys.argv[5]) if len(sys.argv) > 5 else None)
