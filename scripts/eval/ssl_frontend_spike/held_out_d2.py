"""Honest held-out D2 for the typical-composite claim — deployment-slice + few-shot + HELD-OUT threshold.

The typical-800 claim must NOT rest on the optimistic in-sample-threshold template-count number (11%).
This measures D2 the committed way: leave-one-fold-out global threshold @FAR<=5% (held-out), on the
<=25-cmd deployment slice (matching D4/D5/D6), with few-shot enrollment (all reps as templates),
wavlm-base-plus clean embeddings. Reports control (typical) + dysarthric honestly.
"""
import os, sys, math
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
CTL = ["FC01", "FC02", "FC03"]; DYS = ["F01", "F03", "F04"]
FAR = 0.05; SLICE = 25


def load(s):
    r = TORGO if not s.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(r).get(s)


def distinct_subset(d, emb, L, cap):
    """greedy max-min-distance command selection using ONLY enrollment-template centroids (no test
    queries) — models the product's teach-time confusable-command rejection. Returns <=cap command set."""
    cents = {}
    for w, lst in d["commands"].items():
        vs = [emb[x][L] for x in lst if x in emb]
        if vs:
            c = np.mean(vs, axis=0); cents[w] = c / (np.linalg.norm(c) + 1e-8)
    words = list(cents)
    if len(words) <= cap:
        return set(words)
    # start from the two most-distant, greedily add the command maximizing min-dist to the chosen set
    chosen = [words[0]]
    while len(chosen) < cap:
        best_w, best_d = None, -1
        for w in words:
            if w in chosen:
                continue
            md = min(1 - float(cents[w] @ cents[c]) for c in chosen)
            if md > best_d:
                best_d, best_w = md, w
        chosen.append(best_w)
    return set(chosen)


def d2_heldout(emb, L, spk, cap=SLICE, seeds=3, distinct=False):
    """avg over `seeds` random <=cap-cmd slices (or 1 distinct subset); leave-one-fold-out held-out."""
    d = load(spk)
    cmds = list(d["commands"])
    frrs = []
    if distinct:
        seeds = 1
    for seed in range(seeds):
        rng = np.random.RandomState(seed)
        if distinct:
            keep = distinct_subset(d, emb, L, cap)
        else:
            keep = set(cmds) if len(cmds) <= cap else set(rng.choice(cmds, cap, replace=False))
        dd = {"commands": {w: v for w, v in d["commands"].items() if w in keep}, "negatives": d["negatives"]}
        # feat_cache = clean embedding per wav
        fc = {}
        for w, lst in dd["commands"].items():
            for x in lst:
                if x in emb:
                    fc[x] = emb[x][L][None, :]
        for x in dd["negatives"]:
            if x in emb:
                fc[x] = emb[x][L][None, :]
        # harness.eval_speaker uses folds() -> enroll = other folds (few-shot), held_out_global = leave-one-fold-out
        rows = H.eval_speaker(dd, None, fc)
        frr, far, npos, nneg = H.held_out_global(rows)
        frrs.append((frr, far, npos))
    frr = np.mean([f[0] for f in frrs]); far = np.mean([f[1] for f in frrs]); npos = frrs[0][2]
    return frr, far, npos


def band(frr):
    return 800 if frr <= 0.15 else (700 if frr <= 0.35 else (600 if frr <= 0.55 else 500))


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-base-plus"
    L = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    distinct = "--distinct" in sys.argv
    tag = "vocab-distinct <=25" if distinct else f"random slice <={SLICE}"
    print(f"HELD-OUT D2 ({tag}, few-shot, leave-one-fold-out) — {model} L{L}\n", flush=True)
    for grp, spks in [("TYPICAL(control)", CTL), ("DYSARTHRIC", DYS)]:
        num = den = 0
        per = []
        for s in spks:
            frr, far, npos = d2_heldout(emb, L, s, distinct=distinct)
            per.append(f"{s}={frr*100:.0f}%@FAR{far*100:.0f}")
            num += frr * npos; den += npos
        agg = num / den if den else 0
        print(f"  {grp}: D2 FRR={agg*100:.1f}%  -> band {band(agg)}   [{'  '.join(per)}]", flush=True)


if __name__ == "__main__":
    main()
