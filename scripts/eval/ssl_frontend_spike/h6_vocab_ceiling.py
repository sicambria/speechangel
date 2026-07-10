"""H6 (upper bound) — what is the ceiling of vocabulary co-design for the dysarthric in-vocab wall?

L26 predicts LIMITED headroom for dysarthric (distinct selection lifted dys fisher only 1.04->1.17 vs
control 2.28->4.02). H6 measures the achievable in-vocab D2 FRR@FAR<=5% as a function of vocabulary size
N, comparing a RANDOM N-word set vs a teach-time DISTINCT N-word set (greedy max-min centroid — what the
product actually does at enrollment). The distinct curve is the UPPER BOUND of pure vocabulary co-design
(no representation change). Reported for dysarthric vs typical control; characterization, no bank.

Uses the committed held_out_d2 scorer (leave-one-fold-out global threshold @FAR<=5%, few-shot) so the
numbers are fidelity-comparable to the banked composite. wavlm-large L15.
"""
import os, numpy as np
import held_out_d2 as HD

HD.SLICE = 25  # unused path; we pass cap explicitly
CTL = HD.CTL; DYS = HD.DYS
LAYER = 15


def main():
    z = np.load(os.path.join(HD.CACHE, "wavlm-large.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    print(f"H6 — vocabulary-size ceiling, in-vocab D2 FRR@FAR<=5% (wavlm-large L{LAYER})\n", flush=True)
    print(f"  {'N':>3}  {'mode':8s}  {'DYS':>18s}   {'CTL':>18s}", flush=True)
    for cap in [5, 8, 12, 20]:
        for distinct in [False, True]:
            mode = "distinct" if distinct else "random"
            cells = {}
            for grp, spks in [("DYS", DYS), ("CTL", CTL)]:
                num = den = 0
                for s in spks:
                    frr, far, npos = HD.d2_heldout(emb, LAYER, s, cap=cap, distinct=distinct)
                    num += frr * npos; den += npos
                cells[grp] = num / den if den else float("nan")
            print(f"  {cap:>3}  {mode:8s}  {cells['DYS']*100:6.1f}% (band {HD.band(cells['DYS'])})   "
                  f"{cells['CTL']*100:6.1f}% (band {HD.band(cells['CTL'])})", flush=True)
        print(flush=True)
    print("  Interpretation: distinct-vs-random gap = achievable vocab co-design headroom.", flush=True)


if __name__ == "__main__":
    main()
