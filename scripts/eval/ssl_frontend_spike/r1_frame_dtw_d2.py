"""R1 (P3) — FULL frame-trajectory DTW D2 FRR@FAR<=5%, the deferred 'run the full D2 frame-DTW' from
frame_dtw_sep.py, on the binding metric and the MODERATE population.

Deep-research bet P3 (docs/research/2026-07-10-move-d2-wall.md, HIGHEST): multi-exemplar / trajectory
DTW over frozen WavLM frame features (LPM/multi-sample-DTW family) should recover separability that a
single pooled vector destroys — the only dysarthria-validated candidate. frame_dtw_sep.py measured
AUC only (0.672 ~ pooled 0.704, females); this runs the BINDING metric it deferred to.

Advisor lock: the real variable is TRAJECTORY-DTW vs POOLED-COSINE. Both baselines already do
best-of-exemplars (min over templates), so any P3 credit is trajectory-vs-pooling ONLY. Verdict metric =
FRR@FAR<=5% held-out (LOFO), per severity, MODERATE centered. Report raw pos/neg counts.

Pre-registered success: mild+moderate frame-DTW D2 FRR <= pooled-cosine by >=8pp at matched FAR<=5%.
Pre-registered failure: <3pp, or worse than pooled.

Two scorers on the SAME LOFO queries (apples-to-apples):
  pool   WavLM-large L14 mean-pooled cosine (the current shipped scorer)
  fdtw   frame-DTW best-of-exemplars over frames_norm trajectories (P3)

Frames: large_frames_L14.npz (F01/F03/F04) + male_frames_L14.npz (M01..M05). DTW is the cost, so
templates/word capped and negatives subsampled (seeded); positives kept. Deterministic.
"""
import os, sys, math, json, random
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
FAR_TARGET = 0.05
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
FEMALE = ["F01", "F03", "F04"]
MALE = ["M01", "M02", "M03", "M04", "M05"]
MAX_TPL = 3        # templates per command per fold (DTW cost cap)
MAX_NEG = 60       # negatives (impostors) per speaker (seeded subsample)
random.seed(0); np.random.seed(0)


def load_frames():
    z1 = np.load(os.path.join(CACHE, "large_frames_L14.npz"), allow_pickle=True)
    z2p = os.path.join(CACHE, "male_frames_L14.npz")
    frames = {k: z1[k] for k in z1.files}
    if os.path.exists(z2p):
        z2 = np.load(z2p, allow_pickle=True)
        frames.update({k: z2[k] for k in z2.files})
    return frames


def load_pooled():
    zf = np.load(os.path.join(CACHE, "wavlm-large.npz"), allow_pickle=True)
    zm = np.load(os.path.join(CACHE, "male_wavlm_large.npz"), allow_pickle=True)
    emb = {}
    for z in (zf, zm):
        for k in z.files:
            emb[k] = z[k][14].astype(np.float64)
    return emb


def speaker_rows(spk, frames, pooled):
    """Build LOFO rows for one speaker with BOTH scorers on the same wavs.
    Returns list of (fold, truth_or_None, {scorer: (winner_word, dist)})."""
    d = H.scan(TORGO).get(spk)
    if not d:
        return []
    cmds = {w: [wav for wav in lst if wav in frames and wav in pooled]
            for w, lst in d["commands"].items()}
    cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
    negs = [wav for wav in d["negatives"] if wav in frames and wav in pooled]
    random.shuffle(negs); negs = negs[:MAX_NEG]
    words = list(cmds)
    k = 5
    rows = []
    for f in range(k):
        enroll = {}
        pos = []
        for w in words:
            for i, wav in enumerate(cmds[w]):
                (pos.append((w, wav)) if i % k == f else enroll.setdefault(w, []).append(wav))
        enroll = {w: v[:MAX_TPL] for w, v in enroll.items() if v}
        if not enroll:
            continue
        def score_pool(wav):
            qv = pooled[wav]
            best = {w: min(1.0 - float(qv @ pooled[t]) for t in tpls) for w, tpls in enroll.items()}
            w1 = min(best, key=best.get)
            return w1, best[w1]
        def score_fdtw(wav):
            qf = frames[wav]
            best = {w: min(H.dtw_distance(qf, frames[t]) for t in tpls) for w, tpls in enroll.items()}
            w1 = min(best, key=best.get)
            return w1, best[w1]
        for w, wav in pos:
            rows.append((f, w, {"pool": score_pool(wav), "fdtw": score_fdtw(wav)}))
        for wav in negs:
            if hash(wav) % k == f:  # deterministic fold assignment for negatives
                rows.append((f, None, {"pool": score_pool(wav), "fdtw": score_fdtw(wav)}))
    return rows


def d2_from_rows(rows, scorer):
    fold_ids = sorted({r[0] for r in rows})
    acc = pos_n = fa = neg_n = 0
    gen, imp = [], []
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]
        test = [r for r in rows if r[0] == fo]
        neg_tr = [r for r in train if r[1] is None]
        cands = sorted({r[2][scorer][1] for r in train})
        thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            fatr = sum(1 for r in neg_tr if r[2][scorer][1] <= t) / max(1, len(neg_tr))
            if fatr <= FAR_TARGET:
                thr = t
        for r in test:
            w1, dist = r[2][scorer]
            a = dist <= thr
            if r[1] is not None:
                pos_n += 1
                if a and w1 == r[1]:
                    acc += 1
                if w1 == r[1]:
                    gen.append(dist)
            else:
                neg_n += 1
                if a:
                    fa += 1
                imp.append(dist)
    frr = 0.0 if pos_n == 0 else 1.0 - acc / pos_n
    far = 0.0 if neg_n == 0 else fa / neg_n
    g, im = np.array(gen), np.array(imp)
    auc = float(np.mean(g[:, None] < im[None, :])) if g.size and im.size else float("nan")
    return dict(frr=frr, far=far, npos=pos_n, nneg=neg_n, auc=auc)


def main():
    frames = load_frames(); pooled = load_pooled()
    have_male = os.path.exists(os.path.join(CACHE, "male_frames_L14.npz"))
    spks = [s for s in FEMALE + MALE if (have_male or s in FEMALE)]
    print(f"R1 FRAME-DTW D2 — wavlm-large L14, FAR<=5% LOFO. male_frames={have_male}\n"
          f"scorers: pool=mean-cosine  fdtw=frame-trajectory-DTW (both best-of-exemplars)\n", flush=True)
    print(f"{'spk':>4} {'sev':>11} {'npos':>4} {'nneg':>4} | "
          f"{'pool FRR':>9} {'FAR':>5} {'AUC':>5} | {'fdtw FRR':>9} {'FAR':>5} {'AUC':>5} | {'dFRR':>7}",
          flush=True)
    res = {"far_target": FAR_TARGET, "max_tpl": MAX_TPL, "max_neg": MAX_NEG, "per_speaker": {}}
    for s in spks:
        rows = speaker_rows(s, frames, pooled)
        if not rows:
            continue
        p = d2_from_rows(rows, "pool")
        fd = d2_from_rows(rows, "fdtw")
        dfrr = (p["frr"] - fd["frr"]) * 100  # positive = fdtw better
        res["per_speaker"][s] = {"pool": p, "fdtw": fd, "dfrr_pp": dfrr}
        print(f"{s:>4} {SEVERITY[s]:>11} {p['npos']:>4} {p['nneg']:>4} | "
              f"{p['frr']*100:8.1f}% {p['far']*100:4.1f}% {p['auc']:.3f} | "
              f"{fd['frr']*100:8.1f}% {fd['far']*100:4.1f}% {fd['auc']:.3f} | {dfrr:+6.1f}pp", flush=True)

    # Verdict uses only speakers with a VALID D2 (>=1 cached negative). The female frame cache holds
    # command wavs only (no negatives), so females are AUC-context only; males carry the D2 verdict —
    # which is fine because the live population (moderate) is M01/M02.
    valid = [s for s in res["per_speaker"] if res["per_speaker"][s]["pool"]["nneg"] > 0]

    def grp(sevs, scorer, key):
        vals = [res["per_speaker"][s][scorer][key] for s in valid if SEVERITY[s] in sevs]
        return float(np.mean(vals)) if vals else float("nan")
    mm = ["mild", "moderate"]
    p_mm = grp(mm, "pool", "frr"); f_mm = grp(mm, "fdtw", "frr")
    dmm = (p_mm - f_mm) * 100
    banked = dmm >= 8.0
    res["verdict"] = dict(mildmod_pool_frr=p_mm, mildmod_fdtw_frr=f_mm, dfrr_pp=dmm, banked=bool(banked),
                          valid_speakers=valid)
    print(f"\n=== VERDICT (mild+moderate, valid-D2 speakers {valid}, matched FAR<=5%) ===", flush=True)
    print(f"  pooled-cosine FRR={p_mm*100:.1f}%   frame-DTW FRR={f_mm*100:.1f}%   dFRR={dmm:+.1f}pp", flush=True)
    print(f"  => {'BANKED (fdtw >=8pp better)' if banked else 'NOT-BANKED (trajectory does not beat pooling)'}",
          flush=True)
    with open(os.path.join(CACHE, "r1_frame_dtw_d2.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("wrote r1_frame_dtw_d2.json", flush=True)


if __name__ == "__main__":
    main()
