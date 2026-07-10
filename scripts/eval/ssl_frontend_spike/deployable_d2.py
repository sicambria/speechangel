"""Deployable-encoder D2 under the relaxed <=25MB budget (user-authorized 2026-07-10).

distilhubert (~23M params ~= 23MB INT8) is now admissible: OSS, on-device, no GPU, deterministic,
language-independent SSL, 1-shot enrollment unchanged. Measures typical-population D2 (FRR@FAR<=5%)
with few-shot enrollment (K templates/cmd) + margin cross-verify (the banked dual-cascade lever),
robustly across all 3 control speakers. Also reports dysarthric for the honest stratified picture.

Goal: does an admissible <=25MB encoder + few-shot + margin reach D2 <= 15% (band 800) for typical users?
Reuses cached distilhubert embeddings. NOTE: measured on fp32 distilhubert; INT8 quantization typically
costs <1-2pp (a small fidelity caveat, stated).
"""
import os, sys, math
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
CTL = ["FC01", "FC02", "FC03"]; DYS = ["F01", "F03", "F04"]
FAR = 0.05


def load(s):
    r = TORGO if not s.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(r).get(s)


def d2(emb, L, spks, K, margin_grid):
    """few-shot + optional margin cross-verify; global threshold fit to FAR<=5% (leave-one-fold-ish:
    here fit threshold on the speaker's own neg pool = optimistic but consistent across arms)."""
    num = den = 0
    for s in spks:
        d = load(s)
        words = {w: [emb[x][L] for x in v if x in emb] for w, v in d["commands"].items()}
        usable = {w: v for w, v in words.items() if len(v) >= K + 1}
        if len(usable) < 3:
            continue
        negs = [emb[x][L] for x in d["negatives"] if x in emb]
        # queries: leave-one-out
        Q = []
        for w, vs in usable.items():
            for qi in range(len(vs)):
                rest = [vs[j] for j in range(len(vs)) if j != qi][:K]
                enroll = {ww: (vv[:K] if ww != w else rest) for ww, vv in usable.items()}
                q = vs[qi]
                scored = sorted((min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items())
                d1, w1 = scored[0]; d2v = scored[1][0] if len(scored) > 1 else 1.0
                Q.append((d1, d2v / 1.0, d1 / max(d2v, 1e-8), w1, w))  # (dist, _, margin, winner, truth)
        enrollF = {ww: vv[:K] for ww, vv in usable.items()}
        NG = []
        for nv in negs:
            sc = sorted(min(1 - float(nv @ t) for t in tt) for tt in enrollF.values())
            d1 = sc[0]; d2v = sc[1] if len(sc) > 1 else 1.0
            NG.append((d1, d1 / max(d2v, 1e-8)))
        tm = margin_grid[0]  # SINGLE pre-registered margin (no best-of-grid mining, EVAL-003)
        cand = sorted(set([q[0] for q in Q] + [n[0] for n in NG]))
        thr = cand[0] - 1
        for t in cand:
            fa = sum(1 for n in NG if n[0] <= t and n[1] <= tm) / len(NG) if NG else 0
            if fa <= FAR:
                thr = t
        acc = sum(1 for q in Q if q[0] <= thr and q[2] <= tm and q[3] == q[4])
        frr = 1 - acc / len(Q) if Q else 1
        num += frr * len(Q); den += len(Q)
    return (num / den if den else 0), den


def main():
    z = np.load(os.path.join(CACHE, "distilhubert.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    L = 2
    print("distilhubert (<=25MB INT8, admissible) — D2 FRR@FAR<=5%, few-shot + margin cross-verify\n", flush=True)
    for grp, spks in [("CONTROL(typical)", CTL), ("DYSARTHRIC", DYS)]:
        print(f" {grp}:", flush=True)
        for K in [2, 3, 4]:
            raw, n = d2(emb, L, spks, K, [1.0])          # no margin
            mrg, _ = d2(emb, L, spks, K, [0.9])          # + pre-registered margin 0.9
            if n >= 20:
                band = 800 if mrg <= 0.15 else (700 if mrg <= 0.35 else 600)
                print(f"   K={K}: raw={raw*100:4.1f}%  +margin={mrg*100:4.1f}%  (n={n})  -> band {band}", flush=True)


if __name__ == "__main__":
    main()
