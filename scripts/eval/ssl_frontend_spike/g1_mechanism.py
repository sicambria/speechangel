"""G1 mechanism disambiguation — is the whitening win SCATTER-gated or a TORGO artifact?

G1 (zca r32 eps.1) helps TORGO dys (+10.6pp p=.004) AND TORGO control (+8.7pp) but HURTS GSC typical
(-5.8pp p<1e-4). Two competing explanations:
  (a) SCATTER-GATED: whitening helps iff within-word scatter dominates. Predicts benefit monotone with
      within-word mean distance: dys(hi) > torgo-ctl(mid) > gsc(lo, already separated -> hurts).
  (b) TORGO ARTIFACT / word-count: helps because TORGO has 25 enrolled words (rich between-word basis)
      or a channel quirk; GSC has only 8 words -> whitening overfits. Predicts: restrict TORGO-ctl to
      8 words -> the win vanishes even though scatter is unchanged.

Measures, per corpus: within-word mean cosine distance (scatter) and G1 Δ. Plus a WORD-COUNT control:
TORGO control restricted to 8 words (GSC-matched) — if G1 still helps there, word-count is not the cause.
"""
import os, numpy as np
import cand_lib as L
from g1_contraction import fit_transform
from held_out_d2 import distinct_subset
from g1_confirm import paired_outcomes, mcnemar

LAYER = 15; K = 5; METHOD, R, EPS = "zca", 32, 0.1


def within_scatter(words):
    ds = []
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            c = np.mean(rest, 0); c = c / (np.linalg.norm(c) + 1e-8)
            ds.append(1 - float(q @ c))
    return float(np.mean(ds)) if ds else float("nan")


def torgo_words(spk, emb, cap):
    d = L.load_speaker(spk)
    keep = distinct_subset(d, emb, LAYER, cap)
    words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def run(label, per_speaker):
    """per_speaker -> list of (words, negs). Aggregate scatter + G1 paired outcome."""
    accR, accN, scat = {}, {}, []
    for si, (words, negs) in enumerate(per_speaker):
        if len(words) < 3:
            continue
        scat.append(within_scatter(words))
        aR, _ = paired_outcomes(words, negs, "raw", 0, 0)
        aN, _ = paired_outcomes(words, negs, METHOD, R, EPS)
        for k, v in aR.items():
            accR[(si, k)] = v
        for k, v in aN.items():
            accN[(si, k)] = v
    frrR = 1 - np.mean(list(accR.values())); frrN = 1 - np.mean(list(accN.values()))
    b, c, n, p = mcnemar(accR, accN)
    print(f"  {label:34s} within={np.mean(scat):.3f}  raw={frrR*100:5.1f}%  zca={frrN*100:5.1f}%  "
          f"Δ={-(frrN-frrR)*100:+5.1f}pp  (b={b} c={c} p={p:.3g})", flush=True)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"G1 MECHANISM — within-word scatter vs G1 Δ (zca r32 eps.1, L{LAYER})\n", flush=True)
    run("TORGO dysarthric (25w)", [torgo_words(s, emb, 25) for s in L.DYS])
    run("TORGO control (25w)", [torgo_words(s, emb, 25) for s in L.CTL])
    run("TORGO control (8w, GSC-matched)", [torgo_words(s, emb, 8) for s in L.CTL])
    # GSC
    from a5_gsc_kcurve import build_cache
    man, gemb = build_cache()
    gsc_ps = []
    for spk, m in man.items():
        words = {w: [gemb[p][LAYER] for p in ps] for w, ps in m["fixed"].items()}
        words = {w: v for w, v in words.items() if len(v) >= 2}
        negs = [gemb[p][LAYER] for p in m["neg"]]
        gsc_ps.append((words, negs))
    run("GSC typical (8w)", gsc_ps)
    print("\n  If Δ tracks `within` (dys>ctl>gsc) and TORGO-8w still helps -> SCATTER-GATED (real).", flush=True)
    print("  If TORGO-8w flips to hurting -> word-count/overfit artifact, NOT scatter.", flush=True)


if __name__ == "__main__":
    main()
