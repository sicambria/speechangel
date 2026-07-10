"""G1 (PRIMARY, pre-registered) — per-user within-word contraction (whitening / LDA).

L26 shows the dysarthric in-vocab wall IS the within-word scatter (dys within-word cosine ~0.04-0.05 vs
control ~0.015; fisher ~1.0). G1 fits a PER-USER linear transform on the user's own words that contracts
within-word scatter relative to between-word, then scores cosine in the transformed space.

Two transforms:
  ZCA   : whiten by the pooled within-word covariance  T = (Sw + eps*I)^(-1/2)   (contract within-word)
  LDA   : generalized eigvecs of Sb w.r.t. Sw, keep top-d, scale by eig      (contract within, expand between)

HONESTY (the G3 lesson — a fixed-basis nuisance projection leaked and reversed under honest folds):
  per speaker, K=5 round-robin folds. The transform AND the templates are fit on the OTHER folds only;
  the held-out fold's genuine queries + the same-speaker in-vocab OOV negatives (fold-partitioned) are
  transformed with that fold's T and scored. T never sees the query fold. Regularized (Sw is rank-poor
  at dim 1024 with few reps) via PCA-to-r then shrinkage.

PRE-REGISTERED GATE: dysarthric in-vocab D2 FRR@FAR<=5% (vocab-distinct<=25) drops >= 5 pp vs raw (k=0),
  honestly (fold-held-out), aggregated over F01/F03/F04. Report control (typical) as a no-harm check.
  n=3 dysarthric => DIRECTIONAL only; a positive result triggers a pre-registered UASpeech confirmation.
"""
import os, sys, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15; FAR = 0.05; K = 5


def speaker_data(spk, emb, distinct):
    d = L.load_speaker(spk)
    if not d:
        return {}, []
    if distinct:
        keep = distinct_subset(d, emb, LAYER, 25)
        words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    else:
        words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def fit_transform(words, method, r, eps):
    """Fit contraction transform from training words {w:[vecs]}. Returns callable v-> transformed unit vec."""
    if method == "raw":
        return lambda v: v / (np.linalg.norm(v) + 1e-8)
    # PCA to r dims (stabilize) on all training vectors
    X = np.concatenate([np.stack(vs) for vs in words.values()])
    mu = X.mean(0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    r = min(r, Vt.shape[0])
    P = Vt[:r]  # (r, dim)
    # within/between scatter in PCA space
    def to_p(v):
        return (v - mu) @ P.T
    Sw = np.zeros((r, r)); Sb = np.zeros((r, r)); gm = np.zeros(r); nw = 0
    cents = []
    for w, vs in words.items():
        Y = np.stack([to_p(v) for v in vs]); c = Y.mean(0); cents.append(c)
        Sw += (Y - c).T @ (Y - c)
        gm += c; nw += 1
    gm /= max(nw, 1)
    for c in cents:
        d = (c - gm)[:, None]; Sb += d @ d.T
    Sw = Sw / max(1, sum(len(v) for v in words.values())) + eps * np.eye(r)
    if method == "zca":
        val, vec = np.linalg.eigh(Sw)
        val = np.clip(val, 1e-8, None)
        W = vec @ np.diag(val ** -0.5) @ vec.T  # (r,r)
        return lambda v: _unit(W @ to_p(v))
    if method == "lda":
        # generalized eig Sb w.r.t Sw: whiten by Sw then PCA of Sb
        val, vec = np.linalg.eigh(Sw)
        val = np.clip(val, 1e-8, None)
        Wh = vec @ np.diag(val ** -0.5) @ vec.T
        Sb_w = Wh @ Sb @ Wh.T
        bv, bvec = np.linalg.eigh(Sb_w)
        A = (Wh.T @ bvec[:, ::-1]).T  # rows = discriminant directions, most-separating first
        return lambda v: _unit(A @ (Wh @ to_p(v)))
    raise ValueError(method)


def _unit(v):
    return v / (np.linalg.norm(v) + 1e-8)


def frr_at_far(gen, imp, far=FAR):
    if not len(gen) or not len(imp):
        return None
    thr = np.sort(imp)[max(0, int(far * len(imp)) - 1)]
    return float((np.array(gen) > thr).mean())


def eval_transform(emb, method, r, eps, spks, distinct=True):
    gen_all, imp_all = [], []
    for spk in spks:
        words, negs = speaker_data(spk, emb, distinct)
        if len(words) < 3:
            continue
        for f in range(K):
            train = {w: [vs[j] for j in range(len(vs)) if j % K != f] for w, vs in words.items()}
            train = {w: vs for w, vs in train.items() if len(vs) >= 1}
            if len(train) < 3:
                continue
            T = fit_transform(train, method, r, eps)
            tmpl = {w: [T(v) for v in vs] for w, vs in train.items()}
            for wq, vs in words.items():
                if wq not in tmpl:
                    continue
                for j in range(len(vs)):
                    if j % K != f:
                        continue
                    q = T(vs[j])
                    gen_all.append(min(1 - float(q @ t) for t in tmpl[wq]))
            for ni, nv in enumerate(negs):
                if ni % K != f:
                    continue
                pv = T(nv)
                imp_all.append(min(min(1 - float(pv @ t) for t in tt) for tt in tmpl.values()))
    return frr_at_far(gen_all, imp_all), len(gen_all)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"G1 — per-user within-word contraction, in-vocab D2 FRR@FAR<=5% vocab-distinct (wavlm-large L{LAYER})\n", flush=True)
    out = {}
    for grp, spks in [("DYSARTHRIC", L.DYS), ("TYPICAL(control)", L.CTL)]:
        print(f"  {grp}:", flush=True)
        base, _ = eval_transform(emb, "raw", 0, 0, spks)
        print(f"    raw            : FRR={base*100:5.1f}%  (baseline)", flush=True)
        out[f"{grp}/raw"] = base
        for method in ["zca", "lda"]:
            for r in [16, 32, 64]:
                for eps in [1e-2, 1e-1, 3e-1]:
                    frr, n = eval_transform(emb, method, r, eps, spks)
                    d = (base - frr) * 100
                    flag = "  <== GATE" if (grp.startswith("DYS") and d >= 5) else ""
                    print(f"    {method} r={r:<3d} eps={eps:<4g}: FRR={frr*100:5.1f}%  ({d:+.1f}pp){flag}", flush=True)
                    out[f"{grp}/{method}/r{r}/eps{eps}"] = frr
        print(flush=True)
    with open(os.path.join(L.CACHE, "g1_contraction.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
