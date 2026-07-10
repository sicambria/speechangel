"""N2 — confusion-aware small-vocab selection (held-out), the fix for F04's centroid-selection failure.

M1 showed: picking the 5 most-centroid-separated words (pair-aware-by-distance) drives the N5 floor to
~5% for F01/F03 but HURTS severe F04 (6%->19.6%) — because max-centroid-distance picks acoustically
extreme words that have high within-word scatter. This selects instead by ESTIMATED PAIRWISE CONFUSION:
the least-mutually-confusable N-word clique, estimated on ENROLLMENT folds and evaluated on the HELD-OUT
fold (no selection-on-test). Confusion is concentrated on identifiable pairs (M1 modal conc 0.64), so it
is designable-around.

Protocol (per speaker, K=5 round-robin folds):
  - estimate pairwise confusion conf(A,B) on the OTHER folds: fraction of A's enroll reps whose nearest
    template among {A,B} is a B-template (symmetrised max(A->B, B->A));
  - greedily pick N words minimising the max pairwise confusion within the chosen set;
  - evaluate the held-out fold's reps of the chosen words: rank-1 floor + FRR@FAR<=5% vs same-speaker OOV.
Compare 3 selection strategies at N=5: random, centroid-distance (max-min), confusion-aware (this).

GATE (feasibility component, exploratory — NOT the banked primary): confusion-aware N5 rank-1 floor <=5%
for ALL dysarthric speakers INCLUDING severe F04 (where centroid selection failed).
"""
import os, json, itertools
import numpy as np
import cand_lib as L

LAYER = 15; FAR = 0.05; K = 5; N = 5


def all_words(spk, emb):
    d = L.load_speaker(spk)
    if not d:
        return {}, []
    words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def _u(v):
    return v / (np.linalg.norm(v) + 1e-8)


def pairwise_confusion(train):
    """conf[(A,B)] estimated on train reps: leave-one-out among {A,B} templates only."""
    ws = list(train)
    conf = {}
    for A in ws:
        for B in ws:
            if A == B:
                continue
            va, vb = train[A], train[B]
            if len(va) < 2 or not vb:
                conf[(A, B)] = 0.0; continue
            wrong = 0
            for i, q in enumerate(va):
                da = min(1 - float(q @ t) for j, t in enumerate(va) if j != i)
                db = min(1 - float(q @ t) for t in vb)
                if db < da:
                    wrong += 1
            conf[(A, B)] = wrong / len(va)
    return conf


def select(train, strategy):
    ws = list(train)
    if len(ws) <= N:
        return set(ws)
    if strategy == "random":
        rng = np.random.RandomState(len(ws)); return set(rng.choice(ws, N, replace=False))
    cents = {w: _u(np.mean(v, 0)) for w, v in train.items()}
    if strategy == "centroid":
        chosen = [ws[0]]
        while len(chosen) < N:
            bw, bd = None, -1
            for w in ws:
                if w in chosen: continue
                md = min(1 - float(cents[w] @ cents[c]) for c in chosen)
                if md > bd: bd, bw = md, w
            chosen.append(bw)
        return set(chosen)
    if strategy == "confusion":
        conf = pairwise_confusion(train)
        def sym(a, b): return max(conf.get((a, b), 0), conf.get((b, a), 0))
        # greedy: start from the word with lowest total confusion, add min-max-confusion word
        tot = {w: sum(sym(w, o) for o in ws if o != w) for w in ws}
        chosen = [min(tot, key=tot.get)]
        while len(chosen) < N:
            bw, bbad = None, 1e9
            for w in ws:
                if w in chosen: continue
                worst = max(sym(w, c) for c in chosen)
                if worst < bbad: bbad, bw = worst, w
            chosen.append(bw)
        return set(chosen)


def eval_speaker(spk, emb, strategy):
    words, negs = all_words(spk, emb)
    if len(words) < N:
        return None
    gen, imp, conf_err, ntot = [], [], 0, 0
    for f in range(K):
        train = {w: [vs[j] for j in range(len(vs)) if j % K != f] for w, vs in words.items()}
        train = {w: v for w, v in train.items() if len(v) >= 1}
        if len(train) < N:
            continue
        keep = select(train, strategy)
        tmpl = {w: train[w] for w in keep if w in train}
        if len(tmpl) < 2:
            continue
        for wq in keep:
            for j in range(len(words[wq])):
                if j % K != f:
                    continue
                q = words[wq][j]
                # rank-1 floor
                best = min(tmpl, key=lambda w: min(1 - float(q @ t) for t in tmpl[w]))
                ntot += 1; conf_err += (best != wq)
                gen.append(min(1 - float(q @ t) for t in tmpl[wq]))
        for ni, nv in enumerate(negs):
            if ni % K != f:
                continue
            imp.append(min(min(1 - float(nv @ t) for t in tt) for tt in tmpl.values()))
    if not gen or not imp:
        return None
    thr = np.sort(imp)[max(0, int(FAR * len(imp)) - 1)]
    frr = float(np.mean([g > thr for g in gen]))
    floor = conf_err / ntot if ntot else float("nan")
    return floor, frr


def main():
    emb = L.load_emb("wavlm-large")
    print(f"N2 — confusion-aware small-vocab (N={N}, held-out) — wavlm-large L{LAYER}\n", flush=True)
    print(f"  {'speaker':8s}  {'strategy':10s}  {'N5 rank1 floor':>15s}  {'FRR@FAR5%':>10s}", flush=True)
    out = {}
    for s in L.DYS:
        for strat in ["random", "centroid", "confusion"]:
            r = eval_speaker(s, emb, strat)
            if r is None:
                continue
            floor, frr = r
            out[f"{s}/{strat}"] = dict(floor=floor, frr=frr)
            flag = "  <== GATE" if (strat == "confusion" and floor <= 0.05) else ""
            print(f"  {s:8s}  {strat:10s}  {floor*100:13.1f}%  {frr*100:9.1f}%{flag}", flush=True)
        print(flush=True)
    # aggregate confusion-aware
    cf = [out[f"{s}/confusion"] for s in L.DYS if f"{s}/confusion" in out]
    if cf:
        print(f"  DYS confusion-aware: mean floor={np.mean([c['floor'] for c in cf])*100:.1f}%  "
              f"mean FRR@FAR5%={np.mean([c['frr'] for c in cf])*100:.1f}%", flush=True)
    with open(os.path.join(L.CACHE, "n2_confusion_aware_vocab.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
