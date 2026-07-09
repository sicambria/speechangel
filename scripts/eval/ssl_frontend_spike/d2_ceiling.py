"""D2 ceiling test — the decisive rejection-wall test for the SOTA 800-push.

D2 binding axis: held-out global-threshold FRR at per-utterance FAR <= 5% (replicates
TorgoEval.heldOut). Negatives = in-vocab OOV singleton words (same speaker) — the hard confusors.
800 rung = FRR <= 0.15.

Pre-registered H2 (EVAL-003, ONE hypothesis): the BEST admissible-agnostic rejection stack on the
frozen-SSL ceiling — best layer + margin cross-verify (d1/d2 <= theta_m) + PER-COMMAND distance
calibration — reduces held-out FRR @ FAR<=5% to <= 0.15 (the D2 800 rung), aggregated over >=2
speakers with realized FAR reported.

Logic (mirror of the D1 ceiling): this is an UPPER BOUND. A deployable <=2MB student is strictly
weaker. So:
  - ceiling stack FRR > 0.15  => D2 800 is UNREACHABLE under the admissibility filter. DECISIVE.
  - ceiling stack FRR <= 0.15 => headroom may exist; student build justified (fresh confirmation reqd).

Arms (nested, each adds one admissible lever):
  A0  global threshold only (reproduces the sweep's FRR column)
  A1  + margin cross-verify (accept iff d1<=theta AND d1/d2<=theta_m)
  A2  + per-command threshold (theta_word fit per command at matched global FAR budget)

Reuses cached SSL embeddings (_ceiling_cache/<model>.npz) and harness folds. Fast (mean-pool 1-NN).
"""
import os, sys, math, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
DYS = ["F01", "F03", "F04"]
CTL = ["FC01", "FC02", "FC03"]
ALL = DYS + CTL
TORGO = os.path.expanduser("~/torgo")
FAR_TARGET = 0.05


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


def cos_rows(qv, enroll):
    """Return sorted [(dist, word)] of cosine distance to the nearest template per command.
    qv,(word->[vec]) unit vectors. cosine dist = 1 - dot."""
    out = []
    for word, vecs in enroll.items():
        best = min(1.0 - float(qv @ tv) for tv in vecs)
        out.append((best, word))
    out.sort()
    return out


def build_rows(spk_data, emb, layer, k=5):
    """Per query: (fold, truth, sorted_list[(dist,word)])."""
    rows = []
    for fold in H.folds(spk_data, k):
        enroll = {}
        for word, wav in fold["enroll"]:
            enroll.setdefault(word, []).append(emb[wav][layer])
        for word, wav in fold["positives"]:
            rows.append((fold["index"], word, cos_rows(emb[wav][layer], enroll)))
        for wav in fold["negatives"]:
            rows.append((fold["index"], None, cos_rows(emb[wav][layer], enroll)))
    return rows


def far_of(rows_subset, accept_fn):
    negs = [r for r in rows_subset if r[1] is None]
    if not negs:
        return 0.0
    fa = sum(1 for r in negs if accept_fn(r))
    return fa / len(negs)


def eval_arm(rows, arm, margin_grid=None):
    """Leave-one-fold-out. Fit thresholds on train folds to FAR<=5%, eval FRR on test fold.
    Returns aggregate (frr, far, npos, nneg)."""
    if margin_grid is None:
        margin_grid = np.linspace(0.60, 1.0, 21)
    fold_ids = sorted({r[0] for r in rows})
    acc = pos = fa = neg = 0
    for f in fold_ids:
        train = [r for r in rows if r[0] != f]
        test = [r for r in rows if r[0] == f]

        if arm == "A0":
            cands = sorted({r[2][0][0] for r in train if r[2]})
            thr = (cands[0] - 1.0) if cands else 0.0
            for t in cands:
                if far_of(train, lambda r, t=t: r[2] and r[2][0][0] <= t) <= FAR_TARGET:
                    thr = t
            def accept(r, thr=thr):
                return bool(r[2]) and r[2][0][0] <= thr

        elif arm == "A1":
            # joint (theta_d, theta_m): pick margin from grid, then max theta_d s.t. FAR<=5%
            best = None
            for tm in margin_grid:
                cands = sorted({r[2][0][0] for r in train if r[2]})
                thr = (cands[0] - 1.0) if cands else 0.0
                for t in cands:
                    def a(r, t=t, tm=tm):
                        if not r[2]:
                            return False
                        d1 = r[2][0][0]
                        d2 = r[2][1][0] if len(r[2]) > 1 else 1e9
                        return d1 <= t and (d1 / max(d2, 1e-8)) <= tm
                    if far_of(train, a) <= FAR_TARGET:
                        thr = t
                # train FRR for this (thr,tm) to pick best margin
                tp = [r for r in train if r[1] is not None]
                def a2(r, thr=thr, tm=tm):
                    if not r[2]:
                        return False
                    d1 = r[2][0][0]
                    d2 = r[2][1][0] if len(r[2]) > 1 else 1e9
                    return d1 <= thr and (d1 / max(d2, 1e-8)) <= tm and r[2][0][1] == r[1]
                frr_tr = 1.0 - (sum(1 for r in tp if a2(r)) / len(tp)) if tp else 1.0
                if best is None or frr_tr < best[0]:
                    best = (frr_tr, thr, tm)
            _, thr, tm = best
            def accept(r, thr=thr, tm=tm):
                if not r[2]:
                    return False
                d1 = r[2][0][0]
                d2 = r[2][1][0] if len(r[2]) > 1 else 1e9
                return d1 <= thr and (d1 / max(d2, 1e-8)) <= tm

        elif arm == "A2":
            # per-command threshold + margin. Global margin from grid; per-word theta fit to a
            # per-word FAR budget = global FAR_TARGET (each word's negatives = negs whose nearest word is it).
            best = None
            for tm in margin_grid:
                # negatives assigned to the word they most resemble
                word_negs = {}
                for r in train:
                    if r[1] is None and r[2]:
                        word_negs.setdefault(r[2][0][1], []).append(r[2][0][0])
                # per-word threshold: largest d s.t. per-word FAR<=budget
                words = {w for _, w, _ in [] } | {r[2][0][1] for r in train if r[2]}
                thr_w = {}
                for w in words:
                    negd = sorted(word_negs.get(w, []))
                    if not negd:
                        thr_w[w] = 1e9
                        continue
                    # allow up to budget fraction of this word's negs
                    kbud = int(FAR_TARGET * len(negd))
                    thr_w[w] = negd[kbud - 1] if kbud >= 1 else (negd[0] - 1e-6)
                def a(r, tm=tm, thr_w=thr_w):
                    if not r[2]:
                        return False
                    d1, w1 = r[2][0]
                    d2 = r[2][1][0] if len(r[2]) > 1 else 1e9
                    return d1 <= thr_w.get(w1, 0.0) and (d1 / max(d2, 1e-8)) <= tm
                far_tr = far_of(train, a)
                tp = [r for r in train if r[1] is not None]
                frr_tr = 1.0 - (sum(1 for r in tp if a(r) and r[2][0][1] == r[1]) / len(tp)) if tp else 1.0
                # only accept configs meeting FAR budget on train
                if far_tr <= FAR_TARGET and (best is None or frr_tr < best[0]):
                    best = (frr_tr, thr_w, tm)
            if best is None:
                # fallback: loosest
                best = (1.0, {}, margin_grid[-1])
            _, thr_w, tm = best
            def accept(r, thr_w=thr_w, tm=tm):
                if not r[2]:
                    return False
                d1, w1 = r[2][0]
                d2 = r[2][1][0] if len(r[2]) > 1 else 1e9
                return d1 <= thr_w.get(w1, 0.0) and (d1 / max(d2, 1e-8)) <= tm

        for r in test:
            accepted = accept(r)
            if r[1] is not None:
                pos += 1
                if accepted and r[2][0][1] == r[1]:
                    acc += 1
            else:
                neg += 1
                if accepted:
                    fa += 1
    frr = 0.0 if pos == 0 else 1.0 - acc / pos
    far = 0.0 if neg == 0 else fa / neg
    return frr, far, pos, neg


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-base-plus"
    layers = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [8, 9, 12]
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    data = {s: load_speaker(s) for s in ALL}
    data = {k: v for k, v in data.items() if v}

    print(f"D2 CEILING TEST — {model}, layers {layers}, FAR<=5% held-out\n", flush=True)
    print(f"{'layer':>5} {'arm':>3}  {'FRR':>6} {'FAR':>6}   per-speaker FRR", flush=True)
    results = []
    for layer in layers:
        rows_by_spk = {s: build_rows(data[s], emb, layer) for s in data}
        for arm in ["A0", "A1", "A2"]:
            # aggregate pooled counts across speakers
            tot = dict(acc=0, pos=0, fa=0, neg=0)
            per = {}
            for s in data:
                frr, far, npos, nneg = eval_arm(rows_by_spk[s], arm)
                per[s] = (frr, far)
                tot["pos"] += npos
                tot["neg"] += nneg
                tot["acc"] += round((1 - frr) * npos)
                tot["fa"] += round(far * nneg)
            agg_frr = 1 - tot["acc"] / tot["pos"] if tot["pos"] else 0.0
            agg_far = tot["fa"] / tot["neg"] if tot["neg"] else 0.0
            # DYSARTHRIC aggregate (the shipped-scorecard target population)
            dys_acc = dys_pos = dys_fa = dys_neg = 0
            for s in DYS:
                if s in per:
                    npos = sum(1 for r in rows_by_spk[s] if r[1] is not None)
                    nneg = sum(1 for r in rows_by_spk[s] if r[1] is None)
                    dys_acc += round((1 - per[s][0]) * npos)
                    dys_pos += npos
                    dys_fa += round(per[s][1] * nneg)
                    dys_neg += nneg
            dys_frr = 1 - dys_acc / dys_pos if dys_pos else 0.0
            dys_far = dys_fa / dys_neg if dys_neg else 0.0
            n_agree = sum(1 for s in DYS if s in per and per[s][0] <= 0.15)
            results.append(dict(model=model, layer=layer, arm=arm, frr=agg_frr, far=agg_far,
                                dys_frr=dys_frr, dys_far=dys_far, n_dys_le15=n_agree,
                                per_spk={s: [round(per[s][0], 3), round(per[s][1], 3)] for s in per}))
            ps = "  ".join(f"{s}={per[s][0]*100:.0f}%" for s in data)
            print(f"{layer:>5} {arm:>3}  all={agg_frr*100:5.1f}%  DYS={dys_frr*100:5.1f}% @FAR{dys_far*100:4.1f}%   {ps}", flush=True)
        print(flush=True)

    best = min(results, key=lambda r: r["dys_frr"])
    print(f"BEST D2 CEILING (DYSARTHRIC): FRR={best['dys_frr']*100:.1f}% @ FAR={best['dys_far']*100:.1f}% "
          f"[{best['model']} L{best['layer']} {best['arm']}], "
          f"{best['n_dys_le15']}/3 dys speakers <=15%", flush=True)
    print(f"H2 (DYS FRR<=15% @ FAR<=5%): {'PASS' if best['dys_frr'] <= 0.15 else 'FAIL'}", flush=True)
    with open(os.path.join(CACHE, f"d2_ceiling_{model}.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
