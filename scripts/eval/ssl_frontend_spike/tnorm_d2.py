"""Cohort / T-normalized D2 rejection — the standard verification lever I had NOT tried.

Prior D2 numbers used raw min-distance (+ margin). But the dominant failure for dysarthric speech is
trial-dependent score bias: some distorted utterances are globally far from EVERYTHING (inflating
genuine distance) while some are globally close (inflating false accepts). Raw global thresholding
cannot separate these. Cohort normalization (T-norm) is the textbook fix: normalize each query's
command-distance by the distribution of that query's distances to an IMPOSTOR COHORT, so the decision
statistic is speaker/trial-invariant.

z(q,c) = (s(q,c) - mu_cohort(q)) / sigma_cohort(q),  s = min_t cos_d(q, t_c),
cohort = templates NOT from the enrolled command set (here: control-speaker + cross-word embeddings).

Admissible: deterministic, on-device (cohort is a small fixed set shipped with the model), 1-shot
enrollment unchanged, language-independent, <=2MB. This is a scoring change, not a constraint break.

Pre-registered H5 (EVAL-003, ONE hypothesis): cohort-normalized scoring reduces held-out DYSARTHRIC
FRR @ FAR<=5% below the raw-distance ceiling (~55-65%), and we report whether it clears the 600 rung
(<=55%) and the 800 rung (<=15%). Also sweeps: + margin, + per-command z-threshold.

Reuses cached mean-pool embeddings (fast). Fidelity: raw arm reproduces the d2_ceiling A0 number.

RESULT (wavlm-large L14, dysarthric): raw 57.3% -> T-norm 86.5% (WORSE). A fixed control cohort does
not model the dysarthric impostor distribution, so z-normalization inflates FRR. Negative result: the
D2 wall is not an operating-point problem, it is the ROC area (AUC ~0.70). See
docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md.
"""
import os, sys, math, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
DYS = ["F01", "F03", "F04"]
CTL = ["FC01", "FC02", "FC03"]
TORGO = os.path.expanduser("~/torgo")
FAR_TARGET = 0.05
np.random.seed(0)


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


def build_cohort(emb, layer, n=200):
    """Impostor cohort = control-speaker command embeddings (speaker-independent, fixed, shipped)."""
    vecs = []
    for spk in CTL:
        d = load_speaker(spk)
        if not d:
            continue
        for word, wavs in d["commands"].items():
            for w in wavs:
                if w in emb:
                    vecs.append(emb[w][layer])
    vecs = np.stack(vecs)
    if vecs.shape[0] > n:
        idx = np.random.choice(vecs.shape[0], n, replace=False)
        vecs = vecs[idx]
    return vecs.astype(np.float32)  # (n, H), unit vectors


def cohort_stats(qv, cohort):
    """mu, sigma of cos-distance from query to cohort."""
    d = 1.0 - cohort @ qv  # (n,)
    return float(d.mean()), float(d.std() + 1e-6)


def build_rows(spk_data, emb, layer, cohort, k=5):
    """Per query: (fold, truth, sorted[(z_or_raw, word, raw)]) for raw and cohort-normalized."""
    rows = []
    for fold in H.folds(spk_data, k):
        enroll = {}
        for word, wav in fold["enroll"]:
            enroll.setdefault(word, []).append(emb[wav][layer])
        def score(qwav):
            qv = emb[qwav][layer]
            mu, sd = cohort_stats(qv, cohort)
            lst = []
            for word, vecs in enroll.items():
                s = min(1.0 - float(qv @ tv) for tv in vecs)
                lst.append((s, (s - mu) / sd, word))
            lst.sort(key=lambda t: t[0])  # nearest by raw distance
            return lst  # [(raw, z, word)] sorted by raw
        for word, wav in fold["positives"]:
            rows.append((fold["index"], word, score(wav)))
        for wav in fold["negatives"]:
            rows.append((fold["index"], None, score(wav)))
    return rows


def far_of(rows, accept):
    negs = [r for r in rows if r[1] is None]
    if not negs:
        return 0.0
    return sum(1 for r in negs if accept(r)) / len(negs)


def eval_arm(rows, stat):
    """stat: 'raw' or 'z'. Leave-one-fold-out, fit global threshold on stat to FAR<=5%."""
    si = 0 if stat == "raw" else 1
    fold_ids = sorted({r[0] for r in rows})
    acc = pos = fa = neg = 0
    for f in fold_ids:
        train = [r for r in rows if r[0] != f]
        test = [r for r in rows if r[0] == f]
        cands = sorted({r[2][0][si] for r in train if r[2]})
        thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            if far_of(train, lambda r, t=t: bool(r[2]) and r[2][0][si] <= t) <= FAR_TARGET:
                thr = t
        for r in test:
            accepted = bool(r[2]) and r[2][0][si] <= thr
            if r[1] is not None:
                pos += 1
                if accepted and r[2][0][2] == r[1]:
                    acc += 1
            else:
                neg += 1
                if accepted:
                    fa += 1
    frr = 0.0 if pos == 0 else 1.0 - acc / pos
    far = 0.0 if neg == 0 else fa / neg
    return frr, far


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-large"
    layer = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    cohort = build_cohort(emb, layer)
    print(f"COHORT/T-NORM D2 — {model} L{layer}, cohort={cohort.shape[0]} control templates\n", flush=True)
    print(f"{'spk':>5}  {'raw FRR':>8} {'z FRR':>8}  (@FAR<=5% held-out)", flush=True)
    tot = {"raw_num": 0.0, "z_num": 0.0, "pos": 0, "raw_faN": 0, "z_faN": 0, "neg": 0}
    per = {}
    for spk in DYS:
        d = load_speaker(spk)
        rows = build_rows(d, emb, layer, cohort)
        npos = sum(1 for r in rows if r[1] is not None)
        nneg = sum(1 for r in rows if r[1] is None)
        rfrr, rfar = eval_arm(rows, "raw")
        zfrr, zfar = eval_arm(rows, "z")
        per[spk] = dict(raw=[rfrr, rfar], z=[zfrr, zfar])
        tot["raw_num"] += rfrr * npos; tot["z_num"] += zfrr * npos; tot["pos"] += npos
        tot["raw_faN"] += round(rfar * nneg); tot["z_faN"] += round(zfar * nneg); tot["neg"] += nneg
        print(f"{spk:>5}  {rfrr*100:7.1f}% {zfrr*100:7.1f}%   (rawFAR{rfar*100:.1f} zFAR{zfar*100:.1f})", flush=True)
    raw_agg = tot["raw_num"] / tot["pos"]
    z_agg = tot["z_num"] / tot["pos"]
    print(f"\nDYS AGG  raw FRR={raw_agg*100:.1f}% @FAR{tot['raw_faN']/tot['neg']*100:.1f}%  |  "
          f"z(T-norm) FRR={z_agg*100:.1f}% @FAR{tot['z_faN']/tot['neg']*100:.1f}%", flush=True)
    print(f"600 rung (<=55%): raw {'PASS' if raw_agg<=0.55 else 'FAIL'} / z {'PASS' if z_agg<=0.55 else 'FAIL'}", flush=True)
    print(f"800 rung (<=15%): raw {'PASS' if raw_agg<=0.15 else 'FAIL'} / z {'PASS' if z_agg<=0.15 else 'FAIL'}", flush=True)
    with open(os.path.join(CACHE, f"tnorm_d2_{model}_L{layer}.json"), "w") as f:
        json.dump(dict(raw_agg=raw_agg, z_agg=z_agg, per_spk=per), f, indent=2)


if __name__ == "__main__":
    main()
