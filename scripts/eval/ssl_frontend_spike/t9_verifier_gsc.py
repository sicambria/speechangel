"""T9 — Learned pairwise VERIFIER on TYPICAL GSC (the most expressive admissible decision function).

Every typical-D2 number scores a (query, template) pair by COSINE distance (a fixed bilinear form).
The verifier tests a strictly larger hypothesis class: a small MLP on the pair interaction features
[q*t, |q-t|] → same/different logit (cosine is one special case). It was the decisive "wall vs soft"
test for dysarthric (capped at AUC ~0.70 → wall confirmed). It has NEVER been run on the typical tail.

The t8 diagnostic found the typical hard-speaker failures are DIFFUSE / below-threshold-dominated
(59% genuine-word-ranked-#1-but-too-far) → a representation/decision problem, not a vocab one. If the
strongest admissible decision function on the SAME pooled embeddings cannot move the tail, "intrinsic"
is near-confirmed for the layer/pooled-cosine representation.

Protocol: LOSO over the 19 GSC speakers — train the verifier on the OTHER 18 speakers' genuine
(same-word) + impostor (diff-word) pairs, evaluate the held-out speaker with the SAME a5 folds/K/manifest
as the cosine baseline (fold=i%5, enroll=other folds, K=5, min→max-agg over words). Verdict (EVAL-005/007):
FRR@FAR<=5% held-out, and does it move >=2 of the 3 hard speakers (98ea0818/2aca1e72/c1d39ce8) in
direction at matched FAR? Baseline = cosine L12/K5 = 5.81%. Reuses verifier_d2's Verifier + train loop.
"""
import os, json
import numpy as np
import torch
import cand_lib as L
from a5_gsc_kcurve import build_cache, kcurve_speaker
from verifier_d2 import Verifier, train_verifier

torch.manual_seed(0); np.random.seed(0)
torch.set_grad_enabled(True)   # a5_gsc_kcurve disables grad at import; re-enable for verifier training
DEPLOY_L = 12
K = 5
FAR = 0.05
HARD = ["98ea0818", "2aca1e72", "c1d39ce8"]


def build_pairs_gsc(man, emb, speakers, n_imp_per_gen=2):
    Q, T, Y = [], [], []
    for spk in speakers:
        words = {w: [emb[p][DEPLOY_L] for p in ps] for w, ps in man[spk]["fixed"].items()}
        allw = list(words)
        for w, vs in words.items():
            for i in range(len(vs)):
                for j in range(len(vs)):
                    if i != j:
                        Q.append(vs[i]); T.append(vs[j]); Y.append(1.0)
                others = [w2 for w2 in allw if w2 != w]
                np.random.shuffle(others)
                for w2 in others[: n_imp_per_gen * max(1, len(vs) - 1)]:
                    tt = words[w2][np.random.randint(len(words[w2]))]
                    Q.append(vs[i]); T.append(tt); Y.append(0.0)
    return (np.stack(Q).astype(np.float32), np.stack(T).astype(np.float32),
            np.array(Y, dtype=np.float32))


def eval_speaker(g, man_s, emb):
    """Same folds/K/manifest as a5.kcurve_speaker, but score = MAX verifier logit over templates
    (higher = more genuine). Held-out global threshold @FAR<=5% (per-speaker)."""
    words = {w: [emb[p][DEPLOY_L] for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [emb[p][DEPLOY_L] for p in man_s["neg"]]

    def score(qv, enroll):
        q = torch.from_numpy(qv[None, :])
        best = []
        for w, vs in enroll.items():
            tt = torch.from_numpy(np.stack(vs))
            ss = g(q.expand(len(vs), -1), tt)
            best.append((float(ss.max()), w))
        best.sort(key=lambda x: -x[0])
        return best

    pos_rows, fp, neg_rows, fn = [], [], [], []
    with torch.no_grad():
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
                if enroll:
                    pos_rows.append((w, score(qv, enroll))); fp.append(f)
        for ni, nv in enumerate(negs):
            f = ni % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                neg_rows.append((None, score(nv, enroll))); fn.append(f)

    # held-out global threshold @FAR<=5% on TOP logit (higher = accept). Mirror held_out_frr_far but >=.
    fold_ids = sorted(set(fp) | set(fn))
    acc = pos = fa = neg = 0
    P = list(zip(fp, pos_rows)); N = list(zip(fn, neg_rows))
    for f in fold_ids:
        trn = [s for g2, (_, s) in N if g2 != f]
        cands = sorted({s[0][0] for s in trn if s}, reverse=True)
        thr = (cands[0] + 1.0) if cands else 0.0
        for t in cands:
            far = sum(1 for s in trn if s and s[0][0] >= t) / len(trn) if trn else 0
            if far <= FAR:
                thr = t
        for g2, (truth, s) in P:
            if g2 == f:
                pos += 1
                if s and s[0][0] >= thr and s[0][1] == truth:
                    acc += 1
        for g2, (_, s) in N:
            if g2 == f:
                neg += 1
                if s and s[0][0] >= thr:
                    fa += 1
    return (1 - acc / pos if pos else 0.0), (fa / neg if neg else 0.0), pos


def main():
    print("T9 LEARNED VERIFIER on TYPICAL GSC (LOSO) — L%d K%d, baseline cosine 5.81%%\n" % (DEPLOY_L, K), flush=True)
    man, emb = build_cache()
    spks = list(man.keys())
    d = next(iter(emb.values())).shape[1]
    cos_frr = {s: kcurve_speaker(man[s], emb, K, layer=DEPLOY_L)[0] for s in spks}

    num = den = fnum = 0
    per = {}
    for ti, test in enumerate(spks):
        train = [s for s in spks if s != test]
        Q, T, Y = build_pairs_gsc(man, emb, train)
        g = train_verifier(Q, T, Y, d, epochs=100)
        frr, far, npos = eval_speaker(g, man[test], emb)
        per[test] = (frr, far, cos_frr[test])
        num += frr * npos; den += npos; fnum += far * npos
        tag = " <HARD" if any(test.startswith(h[:8]) for h in HARD) else ""
        print(f"  [{ti+1:>2}/{len(spks)}] {test[:9]}  verifier FRR {frr*100:>4.0f}%  (cosine {cos_frr[test]*100:>3.0f}%)  FAR {far*100:>3.0f}%{tag}", flush=True)
    agg, fa = num / den, fnum / den
    # hard-speaker movement
    moved = [h for h in HARD for s in spks if s.startswith(h[:8]) and per[s][0] < per[s][2] - 1e-6]
    print(f"\n  AGGREGATE verifier FRR {agg*100:.2f}% @FAR {fa*100:.1f}%  (cosine baseline 5.81%)", flush=True)
    print(f"  hard speakers improved vs cosine: {len(moved)}/3  "
          f"({', '.join(h[:8] for h in moved) if moved else 'none'})", flush=True)
    verdict = ("MOVES the tail (>=2 hard + agg<=5%) — candidate, needs fresh confirm"
               if len(moved) >= 2 and agg <= 0.05 else
               "does NOT move the tail — wall-confirmer (most expressive admissible fn caps at cosine)")
    print(f"  VERDICT: {verdict}", flush=True)
    with open(os.path.join(L.CACHE, "t9_verifier_gsc.json"), "w") as f:
        json.dump({"agg_frr": agg, "agg_far": fa, "baseline": 0.0581,
                   "hard_moved": len(moved),
                   "per_speaker": {s: {"verifier": per[s][0], "far": per[s][1], "cosine": per[s][2]} for s in spks},
                   "verdict": verdict}, f, indent=2)
    print("\n  wrote t9_verifier_gsc.json", flush=True)


if __name__ == "__main__":
    main()
