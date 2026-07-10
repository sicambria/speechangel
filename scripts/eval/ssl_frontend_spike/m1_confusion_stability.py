"""M1 (gating diagnostic) — is dysarthric in-vocab confusion SYSTEMATIC or RANDOM across repeats?

Decides whether >900 (FRR<=10%) is reachable at all. Band 900 is BELOW the full-vocab rank-1 confusion
floor (15.6%, L26), so single-shot full-vocab is impossible; multi-attempt (SPRT) is the only escape. But
multi-attempt only helps if confusions are INDEPENDENT across a word's repeats (floor^k shrinks). If a
user's "command A" systematically lands on "B" EVERY time, repetition cannot help and >900 is unreachable.

Measures (wavlm-large L15, leave-one-out 1-NN over words, per speaker, aggregated):
  (1) MODAL-CONFUSOR CONCENTRATION: over each source word's misclassified reps, the fraction going to the
      single most-common wrong target. ~1.0 => systematic (same confusor each time, multi-attempt useless);
      ~1/(#words) => random (multi-attempt helps).
  (2) N=5 RANK-1 FLOOR: threshold-free rank-1 confusion at the proposed small operating vocab (random
      5-word subsets, resampled). If >10%, single-shot band 900 is impossible even at small vocab.
  (3) MULTI-ATTEMPT FLOOR: majority-vote top-1 over k in-{1,3,5} independent repeats at N=5. If the floor
      collapses with k => confusions are random => small-vocab + SPRT can reach 900. If it stays => blocked.

No bank — this is the feasibility gate for the whole >900 campaign. F-only (M speakers download pending).
"""
import os, json, itertools
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15
RNG = np.random.RandomState(0)


def words_of(spk, emb, cap=None):
    d = L.load_speaker(spk)
    if not d:
        return {}
    items = d["commands"].items()
    words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in items}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    if cap and len(words) > cap:
        keep = set(RNG.choice(list(words), cap, replace=False))
        words = {w: v for w, v in words.items() if w in keep}
    return words


def loo_pred(q, wq, words):
    """leave-one-out nearest-template word for query q (rep of wq)."""
    best_w, best_d = None, 1e9
    for w, vs in words.items():
        pool = [vs[j] for j in range(len(vs))]  # caller removes q by identity
        dmin = min(1 - float(q @ t) for t in pool) if pool else 1e9
        if dmin < best_d:
            best_d, best_w = dmin, w
    return best_w


def confusion_events(words):
    """Return list of (source_word, pred_word) for each genuine rep (leave-one-out)."""
    ev = []
    for wq, vs in words.items():
        for i, q in enumerate(vs):
            loo = {w: ([vs[j] for j in range(len(vs)) if j != i] if w == wq else v)
                   for w, v in words.items()}
            loo = {w: p for w, p in loo.items() if p}
            best_w, best_d = None, 1e9
            for w, pool in loo.items():
                dmin = min(1 - float(q @ t) for t in pool)
                if dmin < best_d:
                    best_d, best_w = dmin, w
            ev.append((wq, best_w))
    return ev


def modal_concentration(ev):
    from collections import defaultdict, Counter
    wrong = defaultdict(list)
    for src, pred in ev:
        if pred != src:
            wrong[src].append(pred)
    fracs = []
    for src, preds in wrong.items():
        if len(preds) >= 2:
            c = Counter(preds).most_common(1)[0][1]
            fracs.append(c / len(preds))
    err = sum(1 for s, p in ev if s != p) / len(ev) if ev else float("nan")
    return (np.mean(fracs) if fracs else float("nan"), err, len(fracs))


def n5_floor(spk, emb, seeds=8):
    fl = []
    for sd in range(seeds):
        RNG.seed(100 + sd)
        w = words_of(spk, emb, cap=5)
        if len(w) < 2:
            continue
        ev = confusion_events(w)
        fl.append(sum(1 for s, p in ev if s != p) / len(ev))
    return np.mean(fl) if fl else float("nan")


def multiattempt_floor(spk, emb, ks=(1, 2, 3), seeds=8):
    """majority-vote top-1 over k independent reps at N=5, FIXED enroll/query split (no template
    starvation): each word's first ceil(r/2) reps are permanent templates; attempts sampled from the
    held-out query reps. Requires >=2 query reps for k=2, >=3 for k=3 (TORGO is rep-poor -> nan common)."""
    from collections import Counter
    out = {k: [] for k in ks}
    for sd in range(seeds):
        RNG.seed(200 + sd)
        words = words_of(spk, emb, cap=5)
        if len(words) < 2:
            continue
        enroll, query = {}, {}
        for w, vs in words.items():
            ne = max(1, (len(vs) + 1) // 2)
            enroll[w] = vs[:ne]; query[w] = vs[ne:]
        for k in ks:
            wrong = tot = 0
            for wq, qs in query.items():
                if len(qs) < k:
                    continue
                for _ in range(6):
                    idx = RNG.choice(len(qs), size=k, replace=False)
                    preds = []
                    for i in idx:
                        bw, bd = None, 1e9
                        for w, pool in enroll.items():
                            dm = min(1 - float(qs[i] @ t) for t in pool)
                            if dm < bd:
                                bd, bw = dm, w
                        preds.append(bw)
                    vote = Counter(preds).most_common(1)[0][0]
                    tot += 1
                    if vote != wq:
                        wrong += 1
            if tot:
                out[k].append(wrong / tot)
    return {k: (np.mean(v) if v else float("nan")) for k, v in out.items()}


def n5_pairaware_floor(spk, emb, seeds=8):
    """N=5 rank-1 floor when the 5 words are chosen to AVOID mutual systematic confusion: greedily pick
    words whose centroids are maximally separated (proxy for non-confusable). Decisive feasibility number
    — if <=10%, small-vocab + confusable-pair-aware design reaches band 900 by construction."""
    fl = []
    for sd in range(seeds):
        RNG.seed(300 + sd)
        allw = words_of(spk, emb, cap=None)
        if len(allw) < 5:
            continue
        cents = {w: _u(np.mean(v, 0)) for w, v in allw.items()}
        ws = list(cents)
        start = RNG.choice(ws)
        chosen = [start]
        while len(chosen) < 5:
            bw, bd = None, -1
            for w in ws:
                if w in chosen:
                    continue
                md = min(1 - float(cents[w] @ cents[c]) for c in chosen)
                if md > bd:
                    bd, bw = md, w
            chosen.append(bw)
        sub = {w: allw[w] for w in chosen}
        ev = confusion_events(sub)
        fl.append(sum(1 for s, p in ev if s != p) / len(ev))
    return np.mean(fl) if fl else float("nan")


def _u(v):
    return v / (np.linalg.norm(v) + 1e-8)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"M1 CONFUSION-STABILITY GATE — wavlm-large L{LAYER}, dysarthric F-only (M pending)\n", flush=True)
    out = {}
    print("  (1) MODAL-CONFUSOR CONCENTRATION (full vocab)  [~1=systematic; low=random]", flush=True)
    for grp, spks in [("DYS", L.DYS), ("CTL", L.CTL)]:
        for s in spks:
            words = words_of(s, emb)
            if len(words) < 3:
                continue
            ev = confusion_events(words)
            conc, err, nsrc = modal_concentration(ev)
            baseline = 1.0 / (len(words) - 1)
            out[f"{s}"] = dict(modal_conc=conc, rank1err=err, nwords=len(words), random_baseline=baseline)
            print(f"    {s}[{grp}]: modal_conc={conc:.2f}  (random~{baseline:.2f})  rank1err={err*100:.1f}%  "
                  f"nwords={len(words)}  n_confused_src={nsrc}", flush=True)
    print("\n  (2) N=5 RANK-1 FLOOR (threshold-free)  [>10% => single-shot band-900 impossible]", flush=True)
    for s in L.DYS:
        f5 = n5_floor(s, emb); fp = n5_pairaware_floor(s, emb)
        out.setdefault(s, {})["n5_floor"] = float(f5); out[s]["n5_pairaware"] = float(fp)
        print(f"    {s}: N5 random={f5*100:4.1f}%   N5 pair-aware(non-confusable 5)={fp*100:4.1f}%", flush=True)
    print("\n  (3) MULTI-ATTEMPT MAJORITY-VOTE FLOOR at N=5 (fixed enroll/query split)", flush=True)
    for s in L.DYS:
        ma = multiattempt_floor(s, emb)
        out.setdefault(s, {})["multiattempt"] = {str(k): float(v) for k, v in ma.items()}
        def f(x): return f"{x*100:.1f}%" if x == x else "n/a"
        print(f"    {s}: k=1 {f(ma[1])}  ->  k=2 {f(ma[2])}  ->  k=3 {f(ma[3])}", flush=True)
    dys_conc = np.nanmean([out[s]["modal_conc"] for s in L.DYS if "modal_conc" in out.get(s, {})])
    dys_base = np.nanmean([out[s]["random_baseline"] for s in L.DYS if "random_baseline" in out.get(s, {})])
    print(f"\n  VERDICT INPUT: DYS mean modal_conc={dys_conc:.2f} vs random {dys_base:.2f}  "
          f"=> confusion is {'SYSTEMATIC (multi-attempt blocked)' if dys_conc > 2*dys_base else 'RANDOM-ish (multi-attempt can help)'}", flush=True)
    with open(os.path.join(L.CACHE, "m1_confusion_stability.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
