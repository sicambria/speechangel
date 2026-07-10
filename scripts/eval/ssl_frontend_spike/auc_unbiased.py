"""Unbiased (all-genuine) AUC check — does P2/P3 actually raise central separability, or was the
0.70->0.9 'rise' an estimator artifact of collecting genuine scores only on winner-correct trials?

harness.separability defines genuine = distance to the query's TRUTH word (regardless of winner);
r1/r2 mistakenly collected genuine only when winner==truth, excluding the ~70% hard genuine trials
(dysarthric rank-1 ~24%). This recomputes the all-genuine AUC for pooled-cosine baseline, the LDA+WCCN
backend (loso), and frame-DTW, on the moderate live population + all speakers. Deterministic.
"""
import os, math, json
import numpy as np
import harness as H
from r2_backend_d2 import load_pooled, fit_lda_wccn, build_train, SEVERITY, FEMALE, MALE
from r1_frame_dtw_d2 import load_frames

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")


def unbiased_auc_pooled(data_spk, transform):
    """all-genuine AUC: genuine = dist to TRUTH word; impostor = nearest-command dist for negatives."""
    cmds = {w: [transform(v) for v in vecs] for w, vecs in data_spk["commands"].items()}
    negs = [transform(v) for v in data_spk["negatives"]]
    words = list(cmds); k = 5
    gen, imp = [], []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        for w, v in pos:
            if w in enroll:
                gen.append(min(1.0 - float(v @ tv) for tv in enroll[w]))  # dist to TRUTH word
        for i, v in enumerate(negs):
            if i % k == f:
                imp.append(min(min(1.0 - float(v @ tv) for tv in tvs) for tvs in enroll.values()))
    g, im = np.array(gen), np.array(imp)
    return float(np.mean(g[:, None] < im[None, :])) if g.size and im.size else float("nan"), g.size, im.size


def unbiased_auc_fdtw(spk, frames):
    d = H.scan(TORGO).get(spk)
    cmds = {w: [x for x in lst if x in frames] for w, lst in d["commands"].items()}
    cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
    negs = [x for x in d["negatives"] if x in frames]
    import random; random.seed(0); random.shuffle(negs); negs = negs[:60]
    words = list(cmds); k = 5
    gen, imp = [], []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, wav in enumerate(cmds[w]):
                (pos.append((w, wav)) if i % k == f else enroll.setdefault(w, []).append(wav))
        enroll = {w: v[:3] for w, v in enroll.items() if v}
        if not enroll:
            continue
        for w, wav in pos:
            if w in enroll:
                gen.append(min(H.dtw_distance(frames[wav], frames[t]) for t in enroll[w]))
        for i, wav in enumerate(negs):
            if i % k == f:
                imp.append(min(min(H.dtw_distance(frames[wav], frames[t]) for t in tpls)
                               for tpls in enroll.values()))
    g, im = np.array(gen), np.array(imp)
    return float(np.mean(g[:, None] < im[None, :])) if g.size and im.size else float("nan"), g.size, im.size


def main():
    data = load_pooled()
    spks = [s for s in FEMALE + MALE if s in data]
    frames = load_frames()
    have_fdtw = os.path.exists(os.path.join(CACHE, "male_frames_L14.npz"))
    print("UNBIASED (all-genuine) AUC — pooled baseline vs LDA+WCCN backend vs frame-DTW\n", flush=True)
    print(f"{'spk':>4} {'sev':>11} | {'pool AUC':>8} | {'backend AUC':>11} | {'fdtw AUC':>8}", flush=True)
    res = {"per_speaker": {}}
    for s in spks:
        pa, ng, ni = unbiased_auc_pooled(data[s], lambda v: v)
        X, y = build_train(data, [t for t in spks if t != s])
        tf = fit_lda_wccn(X, y)
        ba, _, _ = unbiased_auc_pooled(data[s], tf)
        fa = float("nan")
        if have_fdtw and s.startswith("M"):  # males have frame+negatives cached (females: no negs)
            fa, _, _ = unbiased_auc_fdtw(s, frames)
        res["per_speaker"][s] = dict(pool=pa, backend=ba, fdtw=fa, ngen=ng, nimp=ni)
        print(f"{s:>4} {SEVERITY[s]:>11} | {pa:8.3f} | {ba:11.3f} | "
              f"{(f'{fa:.3f}' if fa==fa else '   n/a'):>8}", flush=True)
    mod = [s for s in spks if SEVERITY[s] == "moderate"]
    for key in ["pool", "backend", "fdtw"]:
        vals = [res["per_speaker"][s][key] for s in mod if res["per_speaker"][s][key] == res["per_speaker"][s][key]]
        if vals:
            print(f"  moderate mean {key:>7} unbiased AUC = {np.mean(vals):.3f}", flush=True)
    with open(os.path.join(CACHE, "auc_unbiased.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("wrote auc_unbiased.json", flush=True)


if __name__ == "__main__":
    main()
