"""F0(b) — pin the mean-pool teacher baseline on the a5/t8 speaker set BEFORE building the frame arm.

Reuses build_cache + kcurve_speaker VERBATIM (EVAL-004 change-one-variable: nothing new here). Must
print 5.81% FRR @ FAR 3.9%, npos=912 (19 speakers), i.e. reproduce t6/t7/t8 to the decimal — otherwise
the speaker set is wrong and any frame-arm delta is a confound, not a result.
"""
import numpy as np
from a5_gsc_kcurve import build_cache, kcurve_speaker

K, L = 5, 12


def main():
    man, emb = build_cache()
    spks = list(man.keys())
    num = den = fnum = fden = 0
    per = {}
    for s in spks:
        frr, far, npos, nneg = kcurve_speaker(man[s], emb, K, layer=L)
        num += frr * npos; den += npos; fnum += far * nneg; fden += nneg
        per[s] = (frr, npos)
    agg, fa = num / den, fnum / fden
    print(f"F0(b) mean-pool teacher: {len(spks)} speakers, npos={den}, nneg={fden}")
    print(f"  L{L} K{K} aggregate FRR = {agg*100:.2f}%  @ FAR {fa*100:.2f}%")
    hard = sorted(spks, key=lambda s: -per[s][0])[:4]
    print("  hardest: " + " ".join(f"{s[:8]}={per[s][0]*100:.0f}%(n{per[s][1]})" for s in hard))
    ok = abs(agg - 0.0581) < 0.001 and den == 912
    print(f"  PIN {'OK — 5.81%/912 reproduced' if ok else 'MISMATCH — investigate before building frame arm'}")


if __name__ == "__main__":
    main()
