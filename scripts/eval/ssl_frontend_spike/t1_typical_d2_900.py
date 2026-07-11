"""T1 — Typical D2 800->900 probe: how far below 5% FRR@FAR<=5% can few-shot enrollment drive
TYPICAL-population D2, and what is the residual gap / curve shape?

Context (population-split journey, 2026-07-11): the dysarthric voice-only D2 wall is a confirmed
information-theoretic negative. The typical composite sits at band 800, binding on typical-D2
(GSC-24 K4 = 7.5-8.2% FRR@FAR<=5%, a5_gsc_kcurve). Band 900 needs <=5%. This maps the K-curve at
the best layer (L12, per a5) and reports the pooled genuine/impostor AUC as the low-variance
summary (EVAL-005/007), reusing the a5 cache (no new embedding) so K in {1..5}.

PRE-REGISTERED HYPOTHESIS (H_D2): typical D2 FRR@FAR<=5% (GSC, held-out global threshold, L12,
min-agg) reaches band 900 (<=5%) at K<=5 real enrollment reps, monotone across the >=19 GSC speakers.
  - SUCCESS: aggregate FRR <= 5% at some K<=5, realized held-out FAR <= 5%+2pp, monotone.
  - Else: report the K where it crosses (or that it plateaus above 5%), realized FAR, pooled AUC,
    and per-speaker spread -> quantifies the residual gap for the next lever.
Adjudicated on FRR@matched-FAR (EVAL-007), NOT on AUC (AUC is the diagnostic only). NOT-BANKED
until a fresh pre-registered confirmation; GSC-24 n~19 is the robust typical corpus (not TORGO n=3).
"""
import os, json
import numpy as np
import cand_lib as L
import harness as H
from a5_gsc_kcurve import build_cache, kcurve_speaker, FAR

BEST_L = 12  # a5 layer sweep: L12 best @K4 (7.46%)


def pooled_auc(man, emb, K, layer):
    """Unbiased genuine-vs-impostor AUC diagnostic (all-genuine top-1-correct distance vs
    impostor top-1 distance), pooled over speakers. Lower distance = more genuine, so AUC is
    computed on NEGATED distances (higher score = accept)."""
    g, imp = [], []
    for spk in man:
        man_s = man[spk]
        words = {w: [emb[p][layer] for p in ps] for w, ps in man_s["fixed"].items()}
        negs = [emb[p][layer] for p in man_s["neg"]]
        for w, vecs in words.items():
            for i, qv in enumerate(vecs):
                f = i % 5
                enroll = {}
                for ww, vv in words.items():
                    pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                    if ww == w:
                        pool = [vv[j] for j in range(len(vv)) if j != i and (j % 5) != f]
                    if pool:
                        enroll[ww] = pool[:K]
                if not enroll:
                    continue
                scored = L.score_query(qv, enroll, "min")
                if scored and scored[0][1] == w:      # only genuine-correct enter the genuine set
                    g.append(-scored[0][0])
        for ni, nv in enumerate(negs):
            f = ni % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                scored = L.score_query(nv, enroll, "min")
                if scored:
                    imp.append(-scored[0][0])
    g, imp = np.array(g), np.array(imp)
    # Mann-Whitney AUC
    allv = np.concatenate([g, imp])
    order = allv.argsort()
    ranks = np.empty(len(allv)); ranks[order] = np.arange(1, len(allv) + 1)
    r_g = ranks[:len(g)].sum()
    auc = (r_g - len(g) * (len(g) + 1) / 2) / (len(g) * len(imp))
    return auc, len(g), len(imp)


def main():
    print("T1 TYPICAL D2 800->900 PROBE — GSC wavlm-large, best layer L%d\n" % BEST_L, flush=True)
    man, emb = build_cache()
    print(f"  {len(man)} speakers (fixed 8 words x <=6 reps + 8 OOV negatives)\n", flush=True)
    print(f"  {'K':>2}  {'FRR':>7}  {'FAR':>6}  {'AUC':>6}   band   per-speaker FRR", flush=True)
    curve = []
    for K in [1, 2, 3, 4, 5]:
        num = den = fanum = 0
        per = []
        for spk in man:
            frr, far, npos, nneg = kcurve_speaker(man[spk], emb, K, layer=BEST_L)
            num += frr * npos; den += npos; fanum += far * npos
            per.append(frr)
        agg = num / den; fa = fanum / den
        auc, ng, ni = pooled_auc(man, emb, K, BEST_L)
        band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else (700 if agg <= 0.35 else 600))
        curve.append({"K": K, "frr": agg, "far": fa, "auc": auc, "band": band, "npos": den})
        print(f"  {K:>2}  {agg*100:6.1f}%  {fa*100:5.1f}%  {auc:.3f}   {band}   "
              + " ".join(f"{p*100:.0f}" for p in per), flush=True)
    best = min(curve, key=lambda c: c["frr"])
    crossed = next((c["K"] for c in curve if c["frr"] <= 0.05), None)
    print(f"\n  best: K={best['K']} FRR={best['frr']*100:.1f}% @FAR{best['far']*100:.1f}% (AUC {best['auc']:.3f})", flush=True)
    print(f"  band-900 (<=5% FRR@FAR<=5%) crossed at K={crossed}"
          if crossed else f"  band-900 NOT reached by K<=5 (best {best['frr']*100:.1f}%); residual gap {max(0,best['frr']-0.05)*100:.1f}pp", flush=True)
    with open(os.path.join(L.CACHE, "t1_typical_d2_900.json"), "w") as f:
        json.dump({"curve": curve, "best_layer": BEST_L, "n_spk": len(man),
                   "band900_K": crossed}, f, indent=2)


if __name__ == "__main__":
    main()
