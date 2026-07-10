"""B6 / B7 / B11 — single-attempt decision-layer variants vs the banked 13.8% typical D2.

All share ONE harness: typical (control) held-out global-threshold FRR @ FAR<=5%, vocab-distinct <=25
commands, few-shot enrollment, wavlm-large L15 (the banked typical-D2 configuration = 13.8%). Only the
DECISION RULE changes across arms (EVAL-003: one variable).

  B6  aggregation sweep     : min | softmin | mean2 | mean | median  (min = banked baseline)
  B7  KDE likelihood-ratio  : score = log p_gen(d1) - log p_neg(d1), threshold on the LR
  B11 confusability shaping : per-command threshold offset from enroll-time cross-distance to the
                              nearest other command (confusable commands get a tighter margin)

PRE-REGISTERED GATE: an arm "wins" only if its held-out FRR beats the min-agg baseline by >= 2 pp at
matched FAR<=5%, aggregated over the 3 control speakers. Any winner is EXPLORATORY (needs fresh
confirmation before banking).
"""
import os, sys, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15
FAR = 0.05
K = 5


def build_rows(spk, emb, layer, agg):
    """Held-out rows for a control speaker: vocab-distinct <=25, folds, few-shot enroll, aggregation `agg`.
    Returns (pos_rows, folds_pos, neg_rows, folds_neg) where rows carry the sorted scored list; the
    genuine d1 and neg d1 are recoverable for KDE."""
    d = L.load_speaker(spk)
    keep = distinct_subset(d, emb, layer, 25)
    words = {w: [emb[x][layer] for x in d["commands"][w] if x in emb] for w in keep}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    if len(words) < 3:
        return None
    negs = [emb[x][layer] for x in d["negatives"] if x in emb]
    pos_rows, fp, neg_rows, fn = [], [], [], []
    for w, vecs in words.items():
        for i, qv in enumerate(vecs):
            f = i % K
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j] for j in range(len(vv)) if (j % K) != f]
                if ww == w:
                    pool = [vv[j] for j in range(len(vv)) if j != i and (j % K) != f]
                if pool:
                    enroll[ww] = pool
            if enroll:
                pos_rows.append((w, L.score_query(qv, enroll, agg=agg))); fp.append(f)
    for ni, nv in enumerate(negs):
        f = ni % K
        enroll = {}
        for ww, vv in words.items():
            pool = [vv[j] for j in range(len(vv)) if (j % K) != f]
            if pool:
                enroll[ww] = pool
        if enroll:
            neg_rows.append((None, L.score_query(nv, enroll, agg=agg))); fn.append(f)
    return pos_rows, fp, neg_rows, fn, words


# ----- B7 KDE likelihood-ratio accept builder -----

def kde_1d(samples, bw=None):
    s = np.asarray(samples, dtype=float)
    if s.size < 2:
        return lambda x: 1e-6
    if bw is None:
        bw = 1.06 * (np.std(s) + 1e-6) * s.size ** (-1 / 5)
    bw = max(bw, 1e-3)

    def p(x):
        return float(np.mean(np.exp(-0.5 * ((x - s) / bw) ** 2)) / (bw * np.sqrt(2 * np.pi)) + 1e-9)

    return p


def kde_lr_builder(train_pos, train_neg, target=FAR):
    gen = [s[0][0] for s in train_pos if s]
    neg = [s[0][0] for s in train_neg if s]
    pg, pn = kde_1d(gen), kde_1d(neg)

    def lr(scored):
        d = scored[0][0]
        return np.log(pg(d)) - np.log(pn(d))

    # threshold on LR s.t. FAR<=target on train negs (accept high LR)
    neg_lr = sorted((lr(s) for s in train_neg if s), reverse=True)
    if not neg_lr:
        tau = -1e9
    else:
        k = int(target * len(neg_lr))
        tau = neg_lr[k] if k < len(neg_lr) else neg_lr[-1]
    return lambda scored, tau=tau: bool(scored) and lr(scored) >= tau


def eval_group(spks, emb, layer, arm, agg="min"):
    num = den = fanum = 0
    for s in spks:
        r = build_rows(s, emb, layer, agg)
        if r is None:
            continue
        pos_rows, fp, neg_rows, fn, words = r
        if arm == "B7":
            builder = kde_lr_builder
        elif arm == "B11":
            builder = confusability_builder(words)
        else:
            builder = L.global_threshold_accept
        frr, far, npos, nneg = L.held_out_frr_far(pos_rows, neg_rows, fp, fn, builder, target=FAR)
        num += frr * npos; den += npos; fanum += far * npos
    if den == 0:
        return None
    return num / den, fanum / den, den


# ----- B11 per-command confusability shaping -----

def confusability_builder(words):
    """Per-command threshold = global thr scaled by confusability (nearest other-command centroid dist).
    Confusable command (small cross-dist) -> tighter (smaller) threshold; distinct -> looser."""
    cents = {}
    for w, vs in words.items():
        c = np.mean(vs, 0); cents[w] = c / (np.linalg.norm(c) + 1e-8)
    conf = {}
    ws = list(cents)
    for w in ws:
        others = [1 - float(cents[w] @ cents[o]) for o in ws if o != w]
        conf[w] = min(others) if others else 1.0
    med = np.median(list(conf.values())) + 1e-9

    def builder(train_pos, train_neg, target=FAR):
        # global thr at FAR<=target, then per-word offset by confusability ratio
        base = L.global_threshold_accept(train_pos, train_neg, target)
        # recover base threshold by probing
        cands = sorted({s[0][0] for s in train_neg if s} | {s[0][0] for s in train_pos if s})
        thr = cands[0] - 1 if cands else 0
        negs = [s for s in train_neg if s]
        for t in cands:
            if not negs or sum(1 for s in negs if s[0][0] <= t) / len(negs) <= target:
                thr = t

        def accept(scored, thr=thr):
            if not scored:
                return False
            d1, w1 = scored[0]
            scale = conf.get(w1, med) / med  # <1 confusable -> tighter
            return d1 <= thr * min(scale, 1.0)

        return accept
    return builder


def main():
    emb = L.load_emb("wavlm-large")
    print(f"B6/B7/B11 — typical D2 held-out FRR@FAR<=5%, wavlm-large L{LAYER} (baseline=min=13.8%)\n", flush=True)
    results = {}
    print("  B6 aggregation sweep:", flush=True)
    base = None
    for agg in ["min", "softmin", "mean2", "mean", "median"]:
        r = eval_group(L.CTL, emb, LAYER, "B6", agg=agg)
        if r is None:
            continue
        results[f"B6_{agg}"] = r
        if agg == "min":
            base = r[0]
        tag = "  <-baseline" if agg == "min" else (f"  ({(base-r[0])*100:+.1f}pp)" if base is not None else "")
        print(f"    {agg:8s}: FRR={r[0]*100:5.1f}% @FAR{r[1]*100:4.1f}% (n={r[2]}){tag}", flush=True)
    print("\n  B7 KDE likelihood-ratio:", flush=True)
    r7 = eval_group(L.CTL, emb, LAYER, "B7")
    results["B7"] = r7
    print(f"    KDE-LR   : FRR={r7[0]*100:5.1f}% @FAR{r7[1]*100:4.1f}% (n={r7[2]})  ({(base-r7[0])*100:+.1f}pp)", flush=True)
    print("\n  B11 confusability shaping:", flush=True)
    r11 = eval_group(L.CTL, emb, LAYER, "B11")
    results["B11"] = r11
    print(f"    conf-shape: FRR={r11[0]*100:5.1f}% @FAR{r11[1]*100:4.1f}% (n={r11[2]})  ({(base-r11[0])*100:+.1f}pp)", flush=True)
    # gate
    wins = {k: (base - v[0]) * 100 for k, v in results.items() if v and (base - v[0]) * 100 >= 2.0 and k != "B6_min"}
    print(f"\n  GATE (>=2pp beat over min-baseline {base*100:.1f}%): {wins if wins else 'NO arm beats baseline by >=2pp'}", flush=True)
    with open(os.path.join(L.CACHE, "b_single.json"), "w") as f:
        json.dump({k: list(v) if v else None for k, v in results.items()} | {"baseline": base}, f, indent=2)


if __name__ == "__main__":
    main()
