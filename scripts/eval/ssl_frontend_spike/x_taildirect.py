"""Tier-B TAIL-DIRECT sweep (#6, #7, #9, #10, #12) — the program-critical question:
does ANY admissible tail-direct decision/calibration lever clear >=8pp moderate FRR@FAR<=5% (LOFO,
held-out, FAR-matched)? Round-4 prior says no (score maps are monotone-invariant; the tail is set by the
worst confusors). These are the under-explored non-monotone / side-channel levers.

All levers share R3's exact FAR-matched discipline: fit ONE global threshold on TRAIN negatives to
FAR<=5%, evaluate held-out; print REALIZED held-out FAR; a lever with realized FAR>5%+2pp is FAR-INVALID
(its FRR gain is spurious — the R3/EVAL-007 trap). Moderate = M01/M02/F03 (live population).

Levers (each replaces or augments the per-query winner SCORE; winner word = argmin base distance):
  A0     min cosine distance to the winner command's templates (baseline)
  #6maha shrinkage-Mahalanobis distance to the winner command's rep cloud (diag shrink; non-Euclidean)
  #6knn  mean of the 2 nearest rep distances (kNN-density, k=2) instead of the single min
  #9qmf  QMF: base score + a NON-MONOTONE calibration by duration-quality bin (the one P1 sub-lever not
         killed by monotone-invariance; fit offset per duration tercile on train)
  #12dur base score + penalty for |query duration - winner-command enroll-duration median| (side-channel)
  #10pcp per-confusor-pair FAR-matched: center each score by its winner-command train-negative median
         (finer than R3's global; FAR provably controlled by the single downstream global threshold)
#7 (rep-disagreement abstain) is reported separately as an ABSTAIN lever (ΔFRR at abstain<20%), since it
   changes the decision space (3-way), not the score.
NOT-BANKED regardless (pending UASpeech #24).
"""
import os, json, wave
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14
FAR_TARGET = 0.05; FAR_TOL = 0.07
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
FEMALE = ["F01", "F03", "F04"]; MALE = ["M01", "M02", "M03", "M04", "M05"]
MODERATE = ["M01", "M02", "F03"]


def wav_dur(path):
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def load():
    zf = np.load(os.path.join(CACHE, "wavlm-large.npz"), allow_pickle=True)
    zm = np.load(os.path.join(CACHE, "male_wavlm_large.npz"), allow_pickle=True)
    emb = {}
    for z in (zf, zm):
        for k in z.files:
            emb[k] = z[k][LAYER].astype(np.float64)
    data = H.scan(TORGO)
    out = {}
    for spk in MODERATE:
        d = data.get(spk)
        if not d:
            continue
        cmds = {w: [(emb[wav], wav_dur(wav)) for wav in lst if wav in emb] for w, lst in d["commands"].items()}
        cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
        negs = [(emb[wav], wav_dur(wav)) for wav in d["negatives"] if wav in emb]
        out[spk] = {"commands": cmds, "negatives": negs}
    return out


def score_query(enroll, qv, qdur, lever, dur_stats, qmf_off):
    """Return (winner_word, score). Winner = argmin base(min-dist). Score depends on lever."""
    base = {}
    alld = {}
    for w, reps in enroll.items():
        ds = sorted(1.0 - float(qv @ tv) for tv, _ in reps)
        alld[w] = ds
        base[w] = ds[0]
    w1 = min(base, key=base.get)
    if lever == "A0":
        return w1, base[w1]
    if lever == "6maha":
        reps = np.array([tv for tv, _ in enroll[w1]])
        mu = reps.mean(0); var = reps.var(0) + 1e-3
        d = float(np.sum((qv - mu) ** 2 / var)) / len(mu)  # normalized diag-Mahalanobis
        return w1, d
    if lever == "6knn":
        ds = alld[w1]
        return w1, float(np.mean(ds[:2])) if len(ds) >= 2 else ds[0]
    if lever == "9qmf":
        b = 0
        med = dur_stats.get(w1)
        if med is not None:
            b = 0 if qdur < med[0] else (1 if qdur < med[1] else 2)
        return w1, base[w1] + qmf_off.get(b, 0.0)
    if lever == "12dur":
        med = dur_stats.get(w1)
        pen = 0.0 if med is None else 0.3 * abs(qdur - med[2]) / (med[2] + 1e-6)
        return w1, base[w1] + pen
    if lever == "10pcp":
        return w1, base[w1]   # centering applied at threshold stage
    return w1, base[w1]


def eval_lever(data_spk, lever):
    cmds = data_spk["commands"]; negs = data_spk["negatives"]; words = list(cmds); k = 5
    rows = []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        # duration terciles per word from enroll (for qmf/dur)
        dur_stats = {}
        for w, reps in enroll.items():
            dl = sorted(d for _, d in reps)
            if dl:
                q1 = dl[len(dl) // 3]; q2 = dl[2 * len(dl) // 3]
                dur_stats[w] = (q1, q2, float(np.median(dl)))
        # qmf offsets: fit per-tercile mean base-score on enroll positives (train-only), center them
        qmf_off = {}
        if lever == "9qmf":
            bins = {0: [], 1: [], 2: []}
            for w, reps in enroll.items():
                for tv, dd in reps:
                    med = dur_stats.get(w)
                    if med is None:
                        continue
                    b = 0 if dd < med[0] else (1 if dd < med[1] else 2)
                    others = [rv for rv, _ in reps if rv is not tv]
                    if others:
                        bins[b].append(min(1.0 - float(tv @ rv) for rv in others))
            gm = np.mean([x for v in bins.values() for x in v]) if any(bins.values()) else 0.0
            for b in (0, 1, 2):
                qmf_off[b] = (gm - float(np.mean(bins[b]))) if bins[b] else 0.0
        for w, (v, dd) in pos:
            w1, s = score_query(enroll, v, dd, lever, dur_stats, qmf_off)
            rows.append((f, w, w1, s))
        for (v, dd) in negs_fold(negs, f, k):
            w1, s = score_query(enroll, v, dd, lever, dur_stats, qmf_off)
            rows.append((f, None, w1, s))
    return threshold_far_matched(rows, percmd=(lever == "10pcp"))


def negs_fold(negs, f, k):
    return [negs[i] for i in range(len(negs)) if i % k == f]


def threshold_far_matched(rows, percmd=False):
    fold_ids = sorted({r[0] for r in rows})
    acc = pos_n = fa = neg_n = 0
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]; test = [r for r in rows if r[0] == fo]
        neg_tr = [r for r in train if r[1] is None]
        if percmd:
            wn = {}
            for r in neg_tr:
                wn.setdefault(r[2], []).append(r[3])
            gmed = float(np.median([r[3] for r in neg_tr])) if neg_tr else 0.0
            off = {w: (float(np.median(wn[w])) if wn.get(w) else gmed) for w in {r[2] for r in train}}
            cen = lambda r: r[3] - off.get(r[2], gmed)
        else:
            cen = lambda r: r[3]
        cands = sorted({cen(r) for r in train}); thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            if sum(1 for r in neg_tr if cen(r) <= t) / max(1, len(neg_tr)) <= FAR_TARGET:
                thr = t
        for r in test:
            a = cen(r) <= thr
            if r[1] is not None:
                pos_n += 1; acc += int(a and r[2] == r[1])
            else:
                neg_n += 1; fa += int(a)
    return (1 - acc / pos_n if pos_n else 0.0), (fa / neg_n if neg_n else 0.0), pos_n, neg_n


# ---------------------------------------------------------------- #7 rep-disagreement abstain
def eval_abstain7(data_spk, abstain_frac=0.20):
    """Abstain on queries whose winner command has high enrollment within-word scatter. Report FRR on the
    NON-abstained decisions at FAR<=5% (abstained genuine -> confirm turn, not a hard error)."""
    cmds = data_spk["commands"]; negs = data_spk["negatives"]; words = list(cmds); k = 5
    rows = []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        scatter = {}
        for w, reps in enroll.items():
            R = np.array([tv for tv, _ in reps])
            scatter[w] = float(np.mean([1.0 - float(a @ b) for a in R for b in R])) if len(R) > 1 else 0.0
        for w, (v, dd) in pos:
            base = {ww: min(1.0 - float(v @ tv) for tv, _ in reps) for ww, reps in enroll.items()}
            w1 = min(base, key=base.get); rows.append((f, w, w1, base[w1], scatter[w1]))
        for (v, dd) in negs_fold(negs, f, k):
            base = {ww: min(1.0 - float(v @ tv) for tv, _ in reps) for ww, reps in enroll.items()}
            w1 = min(base, key=base.get); rows.append((f, None, w1, base[w1], scatter[w1]))
    # global scatter cutoff to abstain the top abstain_frac of decisions
    sc = sorted(r[4] for r in rows)
    cut = sc[int((1 - abstain_frac) * len(sc))] if sc else 1e9
    kept = [r for r in rows if r[4] < cut]
    frr, far, npos, nneg = threshold_far_matched([(r[0], r[1], r[2], r[3]) for r in kept])
    abst_rate = 1 - len(kept) / len(rows) if rows else 0.0
    return frr, far, npos, nneg, abst_rate


def main():
    data = load()
    levers = ["A0", "6maha", "6knn", "9qmf", "12dur", "10pcp"]
    out = {"layer": LAYER, "far_target": FAR_TARGET, "per_speaker": {}}
    print(f"Tier-B TAIL-DIRECT — wavlm-large L{LAYER}, FAR<=5% LOFO, moderate=live\n", flush=True)
    print(f"{'spk':>4} | " + "  ".join(f"{l:>8}" for l in levers), flush=True)
    for s in MODERATE:
        row = {}
        for l in levers:
            frr, far, npos, nneg = eval_lever(data[s], l)
            row[l] = dict(frr=frr, far=far, npos=npos, nneg=nneg)
        out["per_speaker"][s] = row
        print(f"{s:>4} | " + "  ".join(f"{row[l]['frr']*100:6.1f}%" for l in levers), flush=True)

    def mean(l, key="frr"):
        return float(np.mean([out["per_speaker"][s][l][key] for s in MODERATE]))
    a0 = mean("A0")
    print("\n=== VERDICT (moderate mean FRR, FAR-matched) ===", flush=True)
    best = None
    for l in levers:
        m = mean(l); fr = mean(l, "far"); d = (a0 - m) * 100; valid = fr <= FAR_TOL
        tag = "" if valid else "  <-- FAR-INVALID"
        print(f"  {l:>8}: FRR={m*100:5.1f}%  FAR={fr*100:4.1f}%  dFRR={d:+.1f}pp{tag}", flush=True)
        if l != "A0" and valid and (best is None or m < best[1]):
            best = (l, m)
    dbest = (a0 - best[1]) * 100 if best else 0.0
    out["verdict_scorelevers"] = dict(a0=a0, best=best[0] if best else None, dfrr_pp=dbest,
                                      clears_8pp=bool(dbest >= 8.0))

    # #7 abstain
    print("\n=== #7 rep-disagreement abstain (abstain top-20% scatter; FRR on kept @ FAR<=5%) ===", flush=True)
    a7 = []
    for s in MODERATE:
        frr, far, npos, nneg, ar = eval_abstain7(data[s])
        a7.append((s, frr, far, ar))
        print(f"  {s}: kept-FRR={frr*100:.1f}%  FAR={far*100:.1f}%  abstain={ar*100:.1f}%", flush=True)
    frr7 = float(np.mean([x[1] for x in a7])); ar7 = float(np.mean([x[3] for x in a7]))
    d7 = (a0 - frr7) * 100
    out["verdict_abstain7"] = dict(kept_frr=frr7, abstain=ar7, dfrr_pp=d7, clears_8pp=bool(d7 >= 8.0))
    print(f"  mean kept-FRR={frr7*100:.1f}%  dFRR vs A0={d7:+.1f}pp  abstain={ar7*100:.1f}%", flush=True)

    print(f"\n=== PROGRAM SIGNAL === best score-lever dFRR={dbest:+.1f}pp; #7 abstain dFRR={d7:+.1f}pp  "
          f"=> {'A LEVER CLEARS 8pp (investigate!)' if (dbest>=8 or d7>=8) else 'NO Tier-B lever clears 8pp (wall holds)'}",
          flush=True)
    with open(os.path.join(CACHE, "x_taildirect.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("wrote x_taildirect.json", flush=True)


if __name__ == "__main__":
    main()
