"""R3 (P1 / the deferred R-series) — SCORE-domain normalization + per-command adaptive thresholds for D2.

Deep-research bet P1 (docs/research/2026-07-10-move-d2-wall.md) and Round-3 plan R16-R20 (per-command /
per-user adaptive thresholds, T-norm/Z-norm/AS-norm) — the single most-direct untried attack on a
fixed-AUC-at-fixed-FAR wall. Unlike P2 (which raises central AUC but, as measured, NOT the FAR<=5% tail),
score normalization + per-command thresholds reshape the *operating point per command*, so it is the lever
most likely to move the binding tail metric if anything can.

VERDICT METRIC (advisor-locked): FRR @ FAR<=5%, held-out (LOFO), PER SEVERITY. AUC is separability-invariant
under monotone score maps, so it is not the target here.

Levers (each fit LOFO; cohort stats from ENROLL folds only — no leakage):
  A0        global threshold (baseline)
  percmd    per-command adaptive threshold (5% FAR budget allocated per command) [= d2_ceiling A2 idea]
  snorm     AS/S-norm: 0.5*(Z-norm[per-command impostor cohort] + T-norm[per-query cohort]), global thr
  snorm+pc  S-norm scores + per-command adaptive threshold

Pre-registered success: >=5pp D2 FRR reduction on MODERATE severity over A0 (moderate = M01/M02/F03).
Pre-registered failure: <1pp. Cohort = the user's OTHER-command templates (on-device, deterministic).
Reuses cached pooled wavlm-large L14 embeddings. Deterministic.
"""
import os, math, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14
FAR_TARGET = 0.05
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
FEMALE = ["F01", "F03", "F04"]
MALE = ["M01", "M02", "M03", "M04", "M05"]


def load_pooled():
    zf = np.load(os.path.join(CACHE, "wavlm-large.npz"), allow_pickle=True)
    zm = np.load(os.path.join(CACHE, "male_wavlm_large.npz"), allow_pickle=True)
    emb = {}
    for z in (zf, zm):
        for k in z.files:
            emb[k] = z[k][LAYER].astype(np.float64)
    data = H.scan(TORGO)
    out = {}
    for spk in FEMALE + MALE:
        d = data.get(spk)
        if not d:
            continue
        cmds = {w: [emb[wav] for wav in lst if wav in emb] for w, lst in d["commands"].items()}
        cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
        negs = [emb[wav] for wav in d["negatives"] if wav in emb]
        out[spk] = {"commands": cmds, "negatives": negs}
    return out


def raw_scores(enroll, qv):
    """{word: min cosine distance to that word's templates}."""
    return {w: min(1.0 - float(qv @ tv) for tv in tvs) for w, tvs in enroll.items()}


def cohort_stats(enroll):
    """Per-command Z-norm cohort: distances from each word's templates to OTHER-word templates.
    Returns {word: (mu, sd)} (impostor-cohort score distribution for that command)."""
    stats = {}
    all_other = {w: [tv for w2, tvs in enroll.items() if w2 != w for tv in tvs] for w in enroll}
    for w, tvs in enroll.items():
        ds = [1.0 - float(a @ b) for a in tvs for b in all_other[w]]
        if ds:
            stats[w] = (float(np.mean(ds)), float(np.std(ds) + 1e-6))
        else:
            stats[w] = (0.0, 1.0)
    return stats


def norm_scores(raw, zstats, mode):
    """Apply score normalization. raw={word:dist}. Lower = more genuine."""
    if mode == "raw":
        return raw
    zn = {}
    for w, d in raw.items():
        mu, sd = zstats.get(w, (0.0, 1.0))
        zn[w] = (d - mu) / sd
    if mode == "znorm":
        return zn
    # t-norm: normalize each score by the per-query distribution over all commands
    vals = np.array(list(raw.values()))
    mq, sq = float(vals.mean()), float(vals.std() + 1e-6)
    tn = {w: (d - mq) / sq for w, d in raw.items()}
    if mode == "tnorm":
        return tn
    # snorm = average of z and t
    return {w: 0.5 * (zn[w] + tn[w]) for w in raw}


def eval_lever(data_spk, lever):
    """LOFO FRR@FAR<=5% for one speaker under a normalization+threshold lever.

    Levers:
      A0        raw score, single global threshold (FAR-valid baseline)
      percmd    per-command INDEPENDENT 5%-FAR budget (NOT FAR-matched — kept only to expose the
                held-out global-FAR blow-out that makes its FRR 'gain' spurious)
      pcfm      FAR-MATCHED per-command: center each score by its winner-command's train-negative
                median offset, then ONE global threshold on the centered score fit to global FAR<=5%.
                Single 1-D threshold => global held-out FAR is provably controlled.
      snorm     AS/S-norm (z+t), single global threshold
    """
    cmds = data_spk["commands"]; negs = data_spk["negatives"]
    words = list(cmds)
    k = 5
    mode = "snorm" if lever.startswith("snorm") else "raw"
    percmd = lever.endswith("pc") or lever == "percmd"
    pcfm = lever == "pcfm"
    # build rows with normalized winner scores
    rows = []
    for f in range(k):
        enroll = {}
        pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        zstats = cohort_stats(enroll)
        def score(v):
            raw = raw_scores(enroll, v)
            ns = norm_scores(raw, zstats, mode)
            w1 = min(ns, key=ns.get)
            return w1, ns[w1]
        for w, v in pos:
            w1, s = score(v)
            rows.append((f, w, w1, s))
        for i, v in enumerate(negs):
            if i % k == f:
                w1, s = score(v)
                rows.append((f, None, w1, s))
    # threshold fit LOFO
    fold_ids = sorted({r[0] for r in rows})
    acc = pos_n = fa = neg_n = 0
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]
        test = [r for r in rows if r[0] == fo]
        neg_tr = [r for r in train if r[1] is None]
        if pcfm:
            # FAR-matched per-command: offset each score by its winner-command train-negative median,
            # then ONE global threshold on the centered score -> global FAR provably controlled.
            word_off = {}
            wn = {}
            for r in neg_tr:
                wn.setdefault(r[2], []).append(r[3])
            gmed = float(np.median([r[3] for r in neg_tr])) if neg_tr else 0.0
            for w in {r[2] for r in train}:
                word_off[w] = float(np.median(wn[w])) if wn.get(w) else gmed
            cen = lambda r: r[3] - word_off.get(r[2], gmed)
            cands = sorted({cen(r) for r in train})
            thr = (cands[0] - 1.0) if cands else 0.0
            for t in cands:
                fatr = sum(1 for r in neg_tr if cen(r) <= t) / max(1, len(neg_tr))
                if fatr <= FAR_TARGET:
                    thr = t
            accept = lambda r, thr=thr: cen(r) <= thr
        elif percmd:
            # per-command threshold: for each winner-command, largest score s.t. per-command FAR<=budget
            word_negs = {}
            for r in neg_tr:
                word_negs.setdefault(r[2], []).append(r[3])
            thr_w = {}
            wset = {r[2] for r in train}
            for w in wset:
                nd = sorted(word_negs.get(w, []))
                if not nd:
                    thr_w[w] = 1e9
                else:
                    kb = int(FAR_TARGET * len(nd))
                    thr_w[w] = nd[kb - 1] if kb >= 1 else (nd[0] - 1e-6)
            accept = lambda r: r[3] <= thr_w.get(r[2], -1e9)
        else:
            cands = sorted({r[3] for r in train})
            thr = (cands[0] - 1.0) if cands else 0.0
            for t in cands:
                fatr = sum(1 for r in neg_tr if r[3] <= t) / max(1, len(neg_tr))
                if fatr <= FAR_TARGET:
                    thr = t
            accept = lambda r, thr=thr: r[3] <= thr
        for r in test:
            a = accept(r)
            if r[1] is not None:
                pos_n += 1
                if a and r[2] == r[1]:
                    acc += 1
            else:
                neg_n += 1
                if a:
                    fa += 1
    frr = 0.0 if pos_n == 0 else 1.0 - acc / pos_n
    far = 0.0 if neg_n == 0 else fa / neg_n
    return frr, far, pos_n, neg_n


def main():
    data = load_pooled()
    spks = [s for s in FEMALE + MALE if s in data]
    levers = ["A0", "percmd", "pcfm", "snorm"]
    print(f"R3 SCORE-NORM D2 — wavlm-large L{LAYER}, FAR<=5% LOFO. moderate=live population\n", flush=True)
    print(f"{'spk':>4} {'sev':>11} | " + "  ".join(f"{l:>9}" for l in levers), flush=True)
    res = {"layer": LAYER, "far_target": FAR_TARGET, "levers": levers, "per_speaker": {}}
    for s in spks:
        row = {}
        for l in levers:
            frr, far, npos, nneg = eval_lever(data[s], l)
            row[l] = dict(frr=frr, far=far, npos=npos, nneg=nneg)
        res["per_speaker"][s] = row
        cells = "  ".join(f"{row[l]['frr']*100:8.1f}%" for l in levers)
        print(f"{s:>4} {SEVERITY[s]:>11} | {cells}", flush=True)

    # verdict on moderate
    def sev_mean(lever):
        vals = [res["per_speaker"][s][lever]["frr"] for s in spks if SEVERITY[s] == "moderate"]
        return float(np.mean(vals)) if vals else float("nan")
    def sev_far(lever):
        vals = [res["per_speaker"][s][lever]["far"] for s in spks if SEVERITY[s] == "moderate"]
        return float(np.mean(vals)) if vals else float("nan")
    # A lever is FAR-VALID only if its realized held-out FAR stays <= target + small tolerance.
    FAR_TOL = FAR_TARGET + 0.02
    print("\n=== VERDICT (moderate mean FRR, FAR-matched) ===", flush=True)
    a0 = sev_mean("A0")
    best = None
    for l in levers:
        m = sev_mean(l); fr = sev_far(l); d = (a0 - m) * 100
        valid = fr <= FAR_TOL
        tag = "" if valid else "  <-- FAR-INVALID (blown budget); FRR gain spurious"
        print(f"  {l:>9}: FRR={m*100:5.1f}%  FAR={fr*100:4.1f}%  dFRR={d:+.1f}pp{tag}", flush=True)
        if l != "A0" and valid and (best is None or m < best[1]):
            best = (l, m)
    if best is None:
        dbest, blabel = 0.0, "none"
    else:
        dbest, blabel = (a0 - best[1]) * 100, best[0]
    banked = dbest >= 5.0
    res["verdict"] = dict(moderate_a0=a0, best_far_valid_lever=blabel, moderate_best=(best[1] if best else a0),
                          dfrr_pp=dbest, banked=bool(banked), far_tol=FAR_TOL)
    print(f"\n  best FAR-VALID lever={blabel}  moderate dFRR={dbest:+.1f}pp  "
          f"=> {'BANKED (>=5pp)' if banked else ('NULL (<1pp)' if dbest < 1 else 'DIRECTIONAL (<5pp, NOT-BANKED)')}",
          flush=True)
    with open(os.path.join(CACHE, "r3_scorenorm_d2.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("wrote r3_scorenorm_d2.json", flush=True)


if __name__ == "__main__":
    main()
