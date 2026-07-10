"""F28 — Multimodal (per-variant) enrollment for severe-dysarthric speakers.

HYPOTHESIS: a severe speaker's repeated productions of one word form 2-3 stable *categorical* variants
(variant-switching), not pure isotropic noise. If so, clustering the reps and enrolling per-cluster
centroids + per-cluster thresholds beats a single flat template set.

A4 predicted the scatter is CONTINUOUS (a duration/loudness axis), not discrete clusters — so F28 is the
falsification test: if discrete-variant enrollment does NOT beat the flat baseline, A4's continuous read
is corroborated and F29 (continuous rate/gain normalization) is the right lever, not clustering.

METHOD: per dys word (>=4 reps), KMeans k=2 on the rep embeddings; enroll templates =
  (A) baseline flat: all reps (min-agg over reps)
  (B) F28 per-variant: the 2 cluster centroids (min-agg over centroids)
Score held-out queries; measure separability AUC(genuine<impostor) with in-vocab OOV negatives.

PRE-REGISTERED GATE: dys AUC(per-variant) >= 0.75 AND >= flat AUC + 0.03 -> discrete variants exist and
are exploitable. Else -> corroborates A4's continuous read; F28 is a dead-end, defer to F29.
"""
import os, json
import numpy as np
import cand_lib as L

LAYER = 15
np.random.seed(0)


def kmeans2(X, iters=25):
    if len(X) < 4:
        return None
    rng = np.random.RandomState(0)
    c = X[rng.choice(len(X), 2, replace=False)].copy()
    for _ in range(iters):
        d = np.stack([1 - X @ c[k] for k in range(2)], 1)
        a = d.argmin(1)
        if a.min() == a.max():
            break
        for k in range(2):
            if (a == k).any():
                m = X[a == k].mean(0); c[k] = m / (np.linalg.norm(m) + 1e-8)
    return c, a


def eval_speaker(spk, emb, layer):
    cmds, negs = L.command_table(spk, emb, layer, min_reps=2)
    words = {w: [r[1] for r in reps] for w, reps in cmds.items() if len(reps) >= 4}
    if len(words) < 3:
        return None
    neg_v = [r[1] for r in negs]
    gen_flat, gen_var = [], []
    # leave-one-out genuine
    for w, vs in words.items():
        V = np.stack(vs)
        for i in range(len(vs)):
            q = vs[i]
            rest = np.stack([vs[j] for j in range(len(vs)) if j != i])
            gen_flat.append(min(1 - float(q @ t) for t in rest))
            km = kmeans2(rest)
            cents = km[0] if km else rest
            gen_var.append(min(1 - float(q @ c) for c in cents))
    # impostors: nearest over ALL words' templates
    flat_templ = {w: np.stack(vs) for w, vs in words.items()}
    var_templ = {}
    for w, vs in words.items():
        km = kmeans2(np.stack(vs)); var_templ[w] = km[0] if km else np.stack(vs)
    imp_flat = [min(min(1 - float(nv @ t) for t in tt) for tt in flat_templ.values()) for nv in neg_v]
    imp_var = [min(min(1 - float(nv @ c) for c in cc) for cc in var_templ.values()) for nv in neg_v]

    def auc(g, im):
        g, im = np.array(g), np.array(im)
        return float(np.mean(g[:, None] < im[None, :])) if len(g) and len(im) else None
    return auc(gen_flat, imp_flat), auc(gen_var, imp_var), len(gen_flat)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"F28 — multimodal (per-variant) enrollment, dys, wavlm-large L{LAYER}\n", flush=True)
    print(f"  {'spk':>5}  {'flat AUC':>9}  {'per-variant AUC':>15}   Δ", flush=True)
    gf, gv, n = 0, 0, 0
    rows = {}
    for spk in L.DYS:
        r = eval_speaker(spk, emb, LAYER)
        if r is None:
            print(f"  {spk}: insufficient", flush=True); continue
        af, av, k = r
        rows[spk] = (af, av, k)
        gf += af * k; gv += av * k; n += k
        print(f"  {spk:>5}  {af:9.3f}  {av:15.3f}   {(av-af):+.3f}", flush=True)
    if n:
        AF, AV = gf / n, gv / n
        gate = AV >= 0.75 and AV >= AF + 0.03
        print(f"\n  DYS pooled: flat={AF:.3f}  per-variant={AV:.3f}  Δ={AV-AF:+.3f}", flush=True)
        print(f"  GATE (per-variant AUC>=0.75 & >=flat+0.03): {'PASS -> discrete variants exploitable' if gate else 'FAIL -> corroborates A4 continuous read; defer to F29'}", flush=True)
        with open(os.path.join(L.CACHE, "f28_multimodal.json"), "w") as f:
            json.dump({"pooled_flat": AF, "pooled_var": AV, "rows": rows, "gate": bool(gate)}, f, indent=2)


if __name__ == "__main__":
    main()
