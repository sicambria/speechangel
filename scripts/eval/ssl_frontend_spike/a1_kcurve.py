"""A1 — Fixed-subset K-curve (repairs the §2 K-curve subset confound).

CONFOUND: the banked K-curve measured each K on "words with >= K+1 reps", so the *word set shifts
with K*. Part of the K=4 improvement could be easier words surviving the >=5-rep filter, not the
few-shot aggregation lever itself.

FIX: hold the word set FIXED (words with >= 5 reps) across K=1..4; vary ONLY the number of enrolled
templates. One encoder, held-out global threshold @ FAR<=5% (the banked D2 protocol). Also recompute
the VARIABLE-subset curve (>= K+1 reps) on the same run so the confound magnitude is visible.

PRE-REGISTERED GATE (EVAL-003, one hypothesis): on the FIXED subset, K=4 held-out FRR@FAR<=5% stays
<= 0.15 for the typical (control) population AND the fixed-vs-variable gap at K<=2 is < 5 pp.
  - PASS  => the structural few-shot lever is real, not a word-selection artifact. §3 projections hold.
  - FAIL  => the drop shrinks materially on the fixed subset; every §3 projection that leans on the
             K-curve must re-base.
"""
import os, sys, json
import numpy as np
import cand_lib as L
import harness as H

FAR = L.FAR_TARGET


def kcurve_frr(spk, emb, layer, K, min_reps, k=5, agg="min"):
    """Held-out global-threshold FRR@FAR<=5% for a speaker, using words with >= min_reps reps and
    capping enrolled templates per word to K. Returns (frr, far, npos, n_words)."""
    cmds, negs = L.command_table(spk, emb, layer, min_reps=2)
    words = {w: reps for w, reps in cmds.items() if len(reps) >= min_reps}
    if len(words) < 3:
        return None
    # round-robin folds over each word's reps
    pos_rows, folds_pos = [], []
    neg_rows, folds_neg = [], []
    # precompute per-word rep vectors and their fold ids
    word_reps = {w: [r[1] for r in reps] for w, reps in words.items()}
    for w, vecs in word_reps.items():
        for i, qv in enumerate(vecs):
            f = i % k
            # enroll: up to K reps of every word drawn from OTHER folds
            enroll = {}
            for ww, vv in word_reps.items():
                pool = [vv[j] for j in range(len(vv)) if (j % k) != f]
                if ww == w:
                    pool = [vv[j] for j in range(len(vv)) if j != i and (j % k) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if not enroll:
                continue
            pos_rows.append((w, L.score_query(qv, enroll, agg=agg)))
            folds_pos.append(f)
    # negatives scored against the full (K-capped) enroll of each fold's complement
    for ni, (nw, nv, _) in enumerate(negs):
        f = ni % k
        enroll = {}
        for ww, vv in word_reps.items():
            pool = [vv[j] for j in range(len(vv)) if (j % k) != f]
            if pool:
                enroll[ww] = pool[:K]
        if enroll:
            neg_rows.append((None, L.score_query(nv, enroll, agg=agg)))
            folds_neg.append(f)
    frr, far, npos, nneg = L.held_out_frr_far(
        pos_rows, neg_rows, folds_pos, folds_neg, L.global_threshold_accept, target=FAR)
    return frr, far, npos, len(words)


def agg_group(spks, emb, layer, K, min_reps):
    num = den = fanum = 0
    nwords = []
    for s in spks:
        r = kcurve_frr(s, emb, layer, K, min_reps)
        if r is None:
            continue
        frr, far, npos, nw = r
        num += frr * npos
        den += npos
        fanum += far * npos
        nwords.append(nw)
    if den == 0:
        return None
    return num / den, fanum / den, den, int(np.mean(nwords)) if nwords else 0


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-large"
    layer = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    emb = L.load_emb(model)
    print(f"A1 FIXED-SUBSET K-CURVE — {model} L{layer}, held-out FRR@FAR<=5%\n", flush=True)
    out = {"model": model, "layer": layer, "groups": {}}
    for grp, spks in [("TYPICAL(control)", L.CTL), ("DYSARTHRIC", L.DYS)]:
        print(f"  {grp}:", flush=True)
        print(f"    {'K':>2}  {'FIXED(>=5rep)':>16}  {'VARIABLE(>=K+1)':>18}   gap", flush=True)
        rows = []
        for K in [1, 2, 3, 4]:
            fixed = agg_group(spks, emb, layer, K, min_reps=5)
            var = agg_group(spks, emb, layer, K, min_reps=K + 1)
            if fixed is None or var is None:
                continue
            gap = (var[0] - fixed[0]) * 100
            print(f"    {K:>2}  {fixed[0]*100:6.1f}% @FAR{fixed[1]*100:3.0f} n={fixed[2]:<4}"
                  f"  {var[0]*100:6.1f}% @FAR{var[1]*100:3.0f} n={var[2]:<4}  {gap:+5.1f}pp"
                  f"  [fixed words={fixed[3]}, var words={var[3]}]", flush=True)
            rows.append(dict(K=K, fixed_frr=fixed[0], fixed_far=fixed[1], fixed_n=fixed[2],
                             fixed_words=fixed[3], var_frr=var[0], var_far=var[1], var_words=var[3]))
        out["groups"][grp] = rows
        print(flush=True)
    # gate
    typ = out["groups"].get("TYPICAL(control)", [])
    k4 = next((r for r in typ if r["K"] == 4), None)
    k2 = next((r for r in typ if r["K"] == 2), None)
    if k4 and k2:
        gap2 = abs(k2["var_frr"] - k2["fixed_frr"]) * 100
        pass_gate = k4["fixed_frr"] <= 0.15 and gap2 < 5.0
        print(f"GATE: fixed K=4 FRR={k4['fixed_frr']*100:.1f}% (<=15%?) & K=2 fixed-vs-var gap={gap2:.1f}pp (<5?)"
              f"  => {'PASS' if pass_gate else 'FAIL'}", flush=True)
        out["gate"] = dict(k4_fixed_frr=k4["fixed_frr"], k2_gap_pp=gap2, pass_=pass_gate)
    with open(os.path.join(L.CACHE, f"a1_kcurve_{model}_L{layer}.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
