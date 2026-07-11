"""T6 — Per-speaker x per-layer FRR map for TYPICAL D2 (the discriminating diagnostic).

Journey (2026-07-11, typical-900): the typical composite is band 800, gated by D2 ALONE
(D5/D3 confound resolved). D2 = 5.6% FRR@FAR<=5% (K5, L12, GSC-19, npos=912 -> 51 false
rejects); band 900 needs <=5% = <=45 -> only ~6 flips separate 800 from 900, carried by a
2-3 speaker hard tail (per-speaker FRR 12-31%) that survives more reps AND per-speaker
thresholding. So an aggregate line-cross is NOT a bankable band-900 event (EVAL-005); the
win must be per-speaker replication.

THIS IS THE FREE DISCRIMINATING FIRST STEP (advisor-prescribed, before committing any lever):
build the per-speaker x per-layer FRR matrix from the all-layers cache already on disk (NO
re-encode). It decides whether the tail deserves a representation lever AT ALL:
  * hard speakers hard at EVERY layer  -> intrinsic -> bank the mild-wall negative fast.
  * hard only at L12/L15               -> layer selection/fusion becomes the pre-registered
                                          hypothesis WITH a mechanism.

Fidelity (EVAL-004): scoring path = a5.kcurve_speaker imported VERBATIM (same held-out
global-threshold @FAR<=5%, min-agg, LOFO folds); only the analysis (loop over layers, per-
speaker breakout, oracle bound) is new. No banking here — this is a diagnostic map. Oracle
"per-speaker best layer" is labelled selection-on-test and is a headroom bound, not a result.
"""
import os, json
import numpy as np
import cand_lib as L
from a5_gsc_kcurve import build_cache, kcurve_speaker

LAYERS = list(range(6, 25))          # skip the known-dead early layers 0-5; 6..24 = 19 layers
KS = [5, 4]                           # 5 = deployment operating point (T2 band); 4 for robustness
DEPLOY_L = 12                         # the population-number layer (a5 best @K4)


def main():
    print("T6 PER-SPEAKER x PER-LAYER FRR MAP — GSC typical D2, wavlm-large\n", flush=True)
    man, emb = build_cache()
    spks = list(man.keys())
    print(f"  {len(spks)} speakers, layers {LAYERS[0]}..{LAYERS[-1]}, K in {KS}\n", flush=True)

    out = {"n_spk": len(spks), "layers": LAYERS, "K": {}}
    for K in KS:
        # matrix[spk][layer] = (frr, far, npos)
        mat = {s: {} for s in spks}
        agg_by_layer = {}
        for lyr in LAYERS:
            num = den = fanum = fden = 0
            for s in spks:
                frr, far, npos, nneg = kcurve_speaker(man[s], emb, K, layer=lyr)
                mat[s][lyr] = (frr, far, npos)
                num += frr * npos; den += npos
                fanum += far * nneg; fden += nneg
            agg_by_layer[lyr] = (num / den, fanum / fden)

        # deployment layer per-speaker FRR, identify the hard tail
        hard = sorted(spks, key=lambda s: -mat[s][DEPLOY_L][0])
        best_single = min(agg_by_layer, key=lambda l: agg_by_layer[l][0])

        # oracle per-speaker best-layer aggregate (SELECTION-ON-TEST upper bound — NOT deployable)
        onum = oden = 0
        oracle_choice = {}
        for s in spks:
            bl = min(LAYERS, key=lambda l: mat[s][l][0])
            oracle_choice[s] = bl
            frr, far, npos = mat[s][bl]
            onum += frr * npos; oden += npos
        oracle_frr = onum / oden

        print(f"  === K={K} ===", flush=True)
        print(f"  aggregate FRR by layer (realized FAR):", flush=True)
        for lyr in LAYERS:
            f, fa = agg_by_layer[lyr]
            mark = " <-DEPLOY" if lyr == DEPLOY_L else (" <-BEST" if lyr == best_single else "")
            print(f"    L{lyr:>2}: FRR {f*100:5.2f}%  FAR {fa*100:4.1f}%{mark}", flush=True)
        print(f"\n  best single deployable layer @K{K}: L{best_single} "
              f"({agg_by_layer[best_single][0]*100:.2f}% FRR, FAR {agg_by_layer[best_single][1]*100:.1f}%) "
              f"vs L{DEPLOY_L} deploy ({agg_by_layer[DEPLOY_L][0]*100:.2f}%)", flush=True)
        print(f"  ORACLE per-speaker-best-layer FRR @K{K}: {oracle_frr*100:.2f}% "
              f"[selection-on-test bound, NOT deployable]\n", flush=True)

        # the hard tail: is each hard speaker hard at EVERY layer, or only at deploy layers?
        print(f"  HARD-SPEAKER x LAYER (top-4 by L{DEPLOY_L} FRR) — FRR% across layers:", flush=True)
        hdr = "    spk        " + " ".join(f"L{l:>2}" for l in LAYERS) + "   min@L"
        print(hdr, flush=True)
        for s in hard[:4]:
            row = " ".join(f"{mat[s][l][0]*100:>3.0f}" for l in LAYERS)
            bl = min(LAYERS, key=lambda l: mat[s][l][0])
            print(f"    {s[:9]:<9}  {row}   {mat[s][bl][0]*100:.0f}@L{bl}", flush=True)

        out["K"][str(K)] = {
            "agg_by_layer": {str(l): agg_by_layer[l] for l in LAYERS},
            "best_single_layer": int(best_single),
            "best_single_frr": agg_by_layer[best_single][0],
            "deploy_layer_frr": agg_by_layer[DEPLOY_L][0],
            "oracle_perspk_frr": oracle_frr,
            "oracle_choice": {s: int(oracle_choice[s]) for s in spks},
            "hard_speakers": [
                {"spk": s, "frr_by_layer": {str(l): mat[s][l][0] for l in LAYERS},
                 "min_layer": int(min(LAYERS, key=lambda l: mat[s][l][0]))}
                for s in hard[:6]
            ],
        }

    with open(os.path.join(L.CACHE, "t6_perspeaker_layer_map.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\n  wrote t6_perspeaker_layer_map.json", flush=True)


if __name__ == "__main__":
    main()
