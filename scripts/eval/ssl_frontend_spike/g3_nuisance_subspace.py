"""G3 (scout) — nuisance-subspace removal for dysarthric within-word variability.

A4 found the severe-dys within-word scatter is STRUCTURED (a low-rank duration/loudness axis). F29 tried to
remove it by warping the audio and FAILED (destroyed discriminative info + artifacts). G3 does it the other
way: estimate the within-word residual subspace IN EMBEDDING SPACE (pooled residuals r = v - centroid(word))
and PROJECT IT OUT before matching. If the nuisance subspace is within-word (not between-word), removing it
contracts genuine scatter while preserving command separation → lower D2 FRR.

Fit the subspace on ENROLLMENT reps only (per speaker, leave-query-out safe: use the other reps' residuals),
project all vectors orthogonal to the top-k residual eigenvectors, re-score D2 FRR@FAR<=5% vs in-vocab
confusors (the binding wall). Sweep k=0 (baseline) .. 8.

GATE (scout): any k reduces dys in-vocab D2 FRR by >= 5 pp vs k=0 without collapsing between-word separation.
"""
import os, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15; FAR = 0.05


def speaker_data(spk, emb, distinct):
    d = L.load_speaker(spk)
    if distinct:
        keep = distinct_subset(d, emb, LAYER, 25)
        words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    else:
        words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def nuisance_basis(words, k):
    """Top-k eigenvectors of the pooled within-word residual covariance."""
    R = []
    for w, vs in words.items():
        V = np.stack(vs); c = V.mean(0)
        R.append(V - c)
    R = np.concatenate(R)
    if k == 0 or len(R) < 2:
        return np.zeros((0, R.shape[1]))
    C = np.cov(R.T)
    val, vec = np.linalg.eigh(C)
    return vec[:, ::-1][:, :k].T  # (k, dim)


def proj_out(v, basis):
    if basis.shape[0] == 0:
        return v / (np.linalg.norm(v) + 1e-8)
    v = v - basis.T @ (basis @ v)
    return v / (np.linalg.norm(v) + 1e-8)


def frr_at_far(gen, imp, far=FAR):
    if not len(gen) or not len(imp):
        return None
    thr = np.sort(imp)[max(0, int(far * len(imp)) - 1)]
    return float((np.array(gen) > thr).mean())


def eval_k(emb, k, distinct, K=5):
    """HONEST fold-based: per speaker, 5 round-robin folds. The nuisance basis + templates are fit on the
    OTHER folds; queries in the held-out fold are projected with that basis and scored against the other
    folds' (projected) templates. The basis never sees the query fold. Impostors scored per fold likewise."""
    gen_all, imp_all = [], []
    for spk in L.DYS:
        words, negs = speaker_data(spk, emb, distinct)
        if len(words) < 3:
            continue
        for f in range(K):
            enroll = {w: [vs[j] for j in range(len(vs)) if j % K != f] for w, vs in words.items()}
            enroll = {w: vs for w, vs in enroll.items() if vs}
            if len(enroll) < 3:
                continue
            B = nuisance_basis(enroll, k)
            pe = {w: [proj_out(v, B) for v in vs] for w, vs in enroll.items()}
            # genuine queries in this fold
            for wq, vs in words.items():
                if wq not in pe:
                    continue
                for j in range(len(vs)):
                    if j % K != f:
                        continue
                    q = proj_out(vs[j], B)
                    gen_all.append(min(1 - float(q @ t) for t in pe[wq]))
            # impostors assigned to this fold
            for ni, nv in enumerate(negs):
                if ni % K != f:
                    continue
                pv = proj_out(nv, B)
                imp_all.append(min(min(1 - float(pv @ t) for t in tt) for tt in pe.values()))
    return frr_at_far(gen_all, imp_all)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"G3 SCOUT — nuisance-subspace removal, dysarthric D2 FRR@FAR<=5% vs in-vocab (wavlm-large L{LAYER})\n", flush=True)
    for distinct in [False, True]:
        tag = "vocab-distinct<=25" if distinct else "ALL commands"
        print(f"  [{tag}]", flush=True)
        base = None
        for k in [0, 1, 2, 3, 4, 6, 8]:
            frr = eval_k(emb, k, distinct)
            if k == 0:
                base = frr
            d = (base - frr) * 100
            print(f"    k={k}: FRR={frr*100:5.1f}%  ({d:+.1f}pp vs k=0)", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
