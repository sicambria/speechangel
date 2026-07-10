"""G1 CONFIRMATION — ONE pre-registered config, paired significance, independent-corpus replication.

The G1 sweep (g1_contraction.py) was exploratory (18 configs; reporting the best r=64 would be
selection-on-test, EVAL-003). This confirms ONE PRE-REGISTERED config chosen BEFORE seeing the sweep
winner: a regularized mid setting, NOT the maximal r.

    PRE-REGISTERED: method=zca, r=32, eps=0.1, wavlm-large L15, vocab-distinct<=25, K=5 fold-held-out.

Three adjudications:
  1. TORGO dysarthric (F01/F03/F04): raw vs zca in-vocab D2 FRR@FAR<=5%, PLUS a paired McNemar on
     per-genuine-item accept/reject at matched FAR (+ exact two-sided binomial on discordants — small n).
  2. TORGO typical control (FC01-03): same, as a 2nd TORGO population.
  3. GSC v2 typical (24 speakers, independent corpus): raw vs zca in-vocab D2 FRR@FAR<=5%.
     A dys-specific effect cannot replicate on typical GSC, but a POSITIVE GSC result shows the lever
     generalizes to typical speech (robustness), and a dys>ctl>gsc gradient is itself informative.

Bank rule: DIRECTIONAL on dys (n=3); the pre-registered config must (a) still beat raw on dys, (b) not
harm typical. A true dysarthric bank still requires the pre-registered UASpeech confirmation (host-gated).
"""
import os, json
import numpy as np
import cand_lib as L
from g1_contraction import fit_transform, frr_at_far, _unit
from held_out_d2 import distinct_subset

LAYER = 15; FAR = 0.05; K = 5
METHOD, R, EPS = "zca", 32, 0.1  # PRE-REGISTERED


def torgo_words(spk, emb):
    d = L.load_speaker(spk)
    if not d:
        return {}, []
    keep = distinct_subset(d, emb, LAYER, 25)
    words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def paired_outcomes(words, negs, method, r, eps):
    """Per-genuine-item accept booleans at ONE POOLED FAR<=5% threshold (all fold-held-out impostor
    distances pooled — stable, and matches g1_contraction's estimator; per-fold thresholds are noisy at
    ~a handful of negatives per fold). Keyed by (word,index) so raw & the transform align item-for-item."""
    gen, imp = {}, []
    for f in range(K):
        train = {w: [vs[j] for j in range(len(vs)) if j % K != f] for w, vs in words.items()}
        train = {w: vs for w, vs in train.items() if len(vs) >= 1}
        if len(train) < 3:
            continue
        T = fit_transform(train, method, r, eps)
        tmpl = {w: [T(v) for v in vs] for w, vs in train.items()}
        for ni, nv in enumerate(negs):
            if ni % K != f:
                continue
            pv = T(nv)
            imp.append(min(min(1 - float(pv @ t) for t in tt) for tt in tmpl.values()))
        for wq, vs in words.items():
            if wq not in tmpl:
                continue
            for j in range(len(vs)):
                if j % K != f:
                    continue
                gen[(wq, j)] = min(1 - float(T(vs[j]) @ t) for t in tmpl[wq])
    if not imp or not gen:
        return {}, float("nan")
    thr = np.sort(imp)[max(0, int(FAR * len(imp)) - 1)]
    acc = {k: bool(d <= thr) for k, d in gen.items()}
    frr = 1.0 - np.mean(list(acc.values()))
    return acc, frr


def mcnemar(acc_raw, acc_new):
    keys = set(acc_raw) & set(acc_new)
    b = sum(1 for k in keys if acc_raw[k] and not acc_new[k])   # raw-accept, new-reject (new hurt)
    c = sum(1 for k in keys if not acc_raw[k] and acc_new[k])   # raw-reject, new-accept (new helped)
    n = b + c
    # exact two-sided binomial p (small n): 2 * P(X <= min(b,c) | Bin(n,0.5))
    from math import comb
    k = min(b, c)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n)) if n else 1.0
    return b, c, n, p


def eval_torgo(emb, spks, label):
    accR, accN = {}, {}
    for spk in spks:
        words, negs = torgo_words(spk, emb)
        if len(words) < 3:
            continue
        aR, _ = paired_outcomes(words, negs, "raw", 0, 0)
        aN, _ = paired_outcomes(words, negs, METHOD, R, EPS)
        for k, v in aR.items():
            accR[(spk, k)] = v
        for k, v in aN.items():
            accN[(spk, k)] = v
    frrR = 1 - np.mean(list(accR.values())); frrN = 1 - np.mean(list(accN.values()))
    b, c, n, p = mcnemar(accR, accN)
    print(f"  [{label}] raw={frrR*100:5.1f}%  zca(r32,eps.1)={frrN*100:5.1f}%  "
          f"(Δ={-(frrN-frrR)*100:+.1f}pp)  McNemar b={b}(hurt) c={c}(helped) p={p:.3f}  n_items={len(accR)}", flush=True)
    return dict(raw=float(frrR), zca=float(frrN), b=b, c=c, p=float(p), n=len(accR))


def eval_gsc():
    from a5_gsc_kcurve import build_cache
    man, gemb = build_cache()
    accR, accN = {}, {}
    for spk, m in man.items():
        words = {w: [gemb[p][LAYER] for p in ps] for w, ps in m["fixed"].items()}
        negs = [gemb[p][LAYER] for p in m["neg"]]
        words = {w: v for w, v in words.items() if len(v) >= 2}
        if len(words) < 3:
            continue
        aR, _ = paired_outcomes(words, negs, "raw", 0, 0)
        aN, _ = paired_outcomes(words, negs, METHOD, R, EPS)
        for k, v in aR.items():
            accR[(spk, k)] = v
        for k, v in aN.items():
            accN[(spk, k)] = v
    frrR = 1 - np.mean(list(accR.values())); frrN = 1 - np.mean(list(accN.values()))
    b, c, n, p = mcnemar(accR, accN)
    print(f"  [GSC typical, {len(man)} spk] raw={frrR*100:5.1f}%  zca={frrN*100:5.1f}%  "
          f"(Δ={-(frrN-frrR)*100:+.1f}pp)  McNemar b={b} c={c} p={p:.4f}  n_items={len(accR)}", flush=True)
    return dict(raw=float(frrR), zca=float(frrN), b=b, c=c, p=float(p), n=len(accR))


def main():
    emb = L.load_emb("wavlm-large")
    print(f"G1 CONFIRMATION — pre-registered {METHOD} r={R} eps={EPS}, in-vocab D2 FRR@FAR<=5% (L{LAYER})\n", flush=True)
    out = {"config": dict(method=METHOD, r=R, eps=EPS)}
    out["dys"] = eval_torgo(emb, L.DYS, "TORGO dysarthric")
    out["ctl"] = eval_torgo(emb, L.CTL, "TORGO typical control")
    print(flush=True)
    out["gsc"] = eval_gsc()
    with open(os.path.join(L.CACHE, "g1_confirm.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
