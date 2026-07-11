"""T8 — Vocab-co-design DIAGNOSTIC: do the typical hard speakers fail on SPECIFIC confusable word
pairs (→ vocab co-design, the only lever with a banked cross-speaker positive: dysarthric +5.4pp
held-out) or DIFFUSELY (→ the tail is a genuine representation wall, alt-encoder/verifier are
exploratory wall-confirmers)?

Advisor-gated (2026-07-11 typical-900 program): this diagnostic PICKS the band-900 primary hypothesis
BEFORE it is pre-registered. It does not itself attempt a win.

For each hard speaker at the deploy layer L12, K=5 (the T2/T6 operating point), classify every genuine
query's held-out outcome:
  * accept-correct           — accepted AND top-1 word == truth
  * reject WRONG-WORD (w->x) — top-1 is a DIFFERENT word x (a confusion pair; co-design can drop/replace)
  * reject BELOW-THRESHOLD   — top-1 IS the truth but distance > accept threshold (diffuse hardness)
Then report per-word FRR, the dominant confusion pairs, and two concentration metrics:
  - frac of false-rejects that are WRONG-WORD (vs below-threshold)   [high → co-design-addressable]
  - frac of false-rejects on the speaker's top-2 hardest words        [high → concentrated]

Fidelity (EVAL-004): reuses `t7.scored_folds` (== a5.kcurve_speaker fold/enroll/K/min-agg) and
`cand_lib.global_threshold_accept` verbatim; per-speaker L12/K5 FRR reproduces t6/t7. FAR-matched.
"""
import os, json, collections
import numpy as np
import cand_lib as L
from a5_gsc_kcurve import build_cache, kcurve_speaker
from t7_layer_negative import scored_folds

DEPLOY_L = 12
K = 5
FAR = 0.05


def classify_speaker(man_s, emb):
    pos, neg = scored_folds(man_s, emb, DEPLOY_L)
    per_word = collections.Counter()       # word -> FR count
    per_word_n = collections.Counter()     # word -> total queries
    confus = collections.Counter()         # (truth, top1) -> count  (wrong-word rejects)
    n_wrong = n_below = n_fr = 0
    for testf in range(5):
        trp = [s for f, w, s in pos if f != testf and s]
        trn = [s for f, s in neg if f != testf and s]
        accept = L.global_threshold_accept(trp, trn, FAR)
        for f, w, s in pos:
            if f != testf or not s:
                continue
            per_word_n[w] += 1
            top1d, top1w = s[0]
            accepted = accept(s)
            if accepted and top1w == w:
                continue                    # accept-correct
            n_fr += 1
            per_word[w] += 1
            if top1w != w:
                n_wrong += 1
                confus[(w, top1w)] += 1     # genuine w lost to competitor top1w
            else:
                n_below += 1                # correct word, below threshold
    return per_word, per_word_n, confus, n_fr, n_wrong, n_below


def main():
    print("T8 VOCAB-CODESIGN DIAGNOSTIC — typical hard speakers, L%d K%d\n" % (DEPLOY_L, K), flush=True)
    man, emb = build_cache()
    # hard speakers = top-3 by L12 FRR (t6: 98ea0818, 2aca1e72, c1d39ce8)
    frr_L12 = {s: kcurve_speaker(man[s], emb, K, layer=DEPLOY_L)[0] for s in man}
    hard = sorted(man, key=lambda s: -frr_L12[s])[:3]
    print(f"  hard speakers (L12 FRR): " + ", ".join(f"{s[:9]}={frr_L12[s]*100:.0f}%" for s in hard) + "\n", flush=True)

    out = {}
    tot_wrong = tot_below = tot_fr = 0
    for s in hard:
        pw, pwn, conf, n_fr, n_wrong, n_below = classify_speaker(man[s], emb)
        tot_wrong += n_wrong; tot_below += n_below; tot_fr += n_fr
        words_by_fr = sorted(pw, key=lambda w: -pw[w])
        top2_fr = sum(pw[w] for w in words_by_fr[:2])
        conc_top2 = top2_fr / n_fr if n_fr else 0
        frac_wrong = n_wrong / n_fr if n_fr else 0
        print(f"  {s[:9]}  FR={n_fr}  (wrong-word {n_wrong}, below-thr {n_below})  "
              f"wrong-frac={frac_wrong*100:.0f}%  top2-word-conc={conc_top2*100:.0f}%", flush=True)
        print(f"      per-word FRR: " + " ".join(f"{w}:{pw[w]}/{pwn[w]}" for w in words_by_fr if pw[w]), flush=True)
        if conf:
            top_pairs = conf.most_common(4)
            print(f"      top confusions (truth->competitor): "
                  + " ".join(f"{a}->{b}:{c}" for (a, b), c in top_pairs), flush=True)
        out[s] = {"n_fr": n_fr, "n_wrong": n_wrong, "n_below": n_below,
                  "frac_wrong": frac_wrong, "conc_top2": conc_top2,
                  "per_word_fr": dict(pw), "per_word_n": dict(pwn),
                  "confusions": {f"{a}->{b}": c for (a, b), c in conf.items()}}

    agg_frac_wrong = tot_wrong / tot_fr if tot_fr else 0
    print(f"\n  AGGREGATE over hard speakers: {tot_fr} FR = {tot_wrong} wrong-word ({agg_frac_wrong*100:.0f}%) "
          f"+ {tot_below} below-threshold ({(1-agg_frac_wrong)*100:.0f}%)", flush=True)
    verdict = ("CONFUSABLE-PAIRS → vocab co-design is the band-900 primary"
               if agg_frac_wrong >= 0.5 else
               "DIFFUSE (below-threshold dominates) → wall-kill framing; alt-encoder/verifier exploratory")
    print(f"  FORK VERDICT: {verdict}", flush=True)
    out["_verdict"] = {"agg_frac_wrong": agg_frac_wrong, "fork": verdict}
    with open(os.path.join(L.CACHE, "t8_vocab_diag.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\n  wrote t8_vocab_diag.json", flush=True)


if __name__ == "__main__":
    main()
