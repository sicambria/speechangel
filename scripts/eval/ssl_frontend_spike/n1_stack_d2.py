"""N1 (Round-3 primary DoD, never run) — the best-admissible STACK for band 900, FAR-matched, per severity.

Round-3 over900-plan N1: 'band 900 reachable only as a per-severity STACK, not one lever.' P1/P2/P3 each
failed alone (Round-4). N1 tests the composition: LDA+WCCN backend (P2) -> S-norm scoring (P1) ->
FAR-matched per-command centering (P1), LOSO-trained, per severity. If the stack does not beat the A0
baseline at matched FAR<=5%, band 900 is unreachable by any admissible composition and the program pivots
to P5 (reframe).

Verdict metric: FRR@FAR<=5% held-out LOFO, per severity. Reuses r2/r3 machinery.
Pre-registered: stack beats A0 by >=8pp on moderate at matched FAR => band-900 track live. Else CONFIRMED
unreachable.

FAR caveat: both arms use per-command centering, which on n=8 overfits and does NOT hold held-out FAR<=5%
(realized ~8-12%). A looser FAR gives OPTIMISTIC FRR, so 'unreachable' is a CONSERVATIVE bound — even helped
by inflated FAR the stack lands band 500-600 on every severity. (For a clean FAR<=5% baseline see d2_ceiling
A0 / r3 A0 at ~4.9% FAR.)
"""
import os, json
import numpy as np
import harness as H
from r2_backend_d2 import load_pooled, fit_lda_wccn, build_train, SEVERITY, FEMALE, MALE, FAR_TARGET
from r3_scorenorm_d2 import cohort_stats, norm_scores, raw_scores

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")


def stack_speaker(data, s, spks, use_backend=True, use_snorm=True):
    """LOFO FRR@FAR<=5% for speaker s under the full stack, FAR-matched (per-command centering + one
    global threshold on centered S-normed score in the backend-transformed space)."""
    # backend transform trained LOSO on all other speakers
    if use_backend:
        X, y = build_train(data, [t for t in spks if t != s])
        tf = fit_lda_wccn(X, y)
    else:
        tf = lambda v: v / (np.linalg.norm(v) + 1e-9)
    cmds = {w: [tf(v) for v in vecs] for w, vecs in data[s]["commands"].items()}
    negs = [tf(v) for v in data[s]["negatives"]]
    words = list(cmds); k = 5
    rows = []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        zstats = cohort_stats(enroll)
        def score(v):
            raw = raw_scores(enroll, v)
            ns = norm_scores(raw, zstats, "snorm" if use_snorm else "raw")
            w1 = min(ns, key=ns.get)
            return w1, ns[w1]
        for w, v in pos:
            w1, sc = score(v); rows.append((f, w, w1, sc))
        for i, v in enumerate(negs):
            if i % k == f:
                w1, sc = score(v); rows.append((f, None, w1, sc))
    # FAR-matched per-command centering + one global threshold
    fold_ids = sorted({r[0] for r in rows})
    acc = pos_n = fa = neg_n = 0
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]; test = [r for r in rows if r[0] == fo]
        neg_tr = [r for r in train if r[1] is None]
        wn = {}
        for r in neg_tr:
            wn.setdefault(r[2], []).append(r[3])
        gmed = float(np.median([r[3] for r in neg_tr])) if neg_tr else 0.0
        off = {w: (float(np.median(wn[w])) if wn.get(w) else gmed) for w in {r[2] for r in train}}
        cen = lambda r: r[3] - off.get(r[2], gmed)
        cands = sorted({cen(r) for r in train}); thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            if sum(1 for r in neg_tr if cen(r) <= t) / max(1, len(neg_tr)) <= FAR_TARGET:
                thr = t
        for r in test:
            a = cen(r) <= thr
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


def band(frr):
    return 700 if frr <= 0.30 else (600 if frr <= 0.45 else 500)


def main():
    data = load_pooled()
    spks = [s for s in FEMALE + MALE if s in data]
    print("N1 STACK D2 — backend(LDA+WCCN) + S-norm + FAR-matched per-command centering, per severity\n",
          flush=True)
    print(f"{'spk':>4} {'sev':>11} | {'A0 FRR':>7} {'A0 FAR':>6} | {'STACK FRR':>9} {'FAR':>5} | "
          f"{'dFRR':>6} {'band':>5}", flush=True)
    res = {"per_speaker": {}}
    for s in spks:
        a_frr, a_far, _, _ = stack_speaker(data, s, spks, use_backend=False, use_snorm=False)
        s_frr, s_far, npos, nneg = stack_speaker(data, s, spks, use_backend=True, use_snorm=True)
        d = (a_frr - s_frr) * 100
        res["per_speaker"][s] = dict(a0_frr=a_frr, a0_far=a_far, stack_frr=s_frr, stack_far=s_far,
                                     dfrr_pp=d, band=band(s_frr), npos=npos, nneg=nneg)
        print(f"{s:>4} {SEVERITY[s]:>11} | {a_frr*100:6.1f}% {a_far*100:5.1f}% | "
              f"{s_frr*100:8.1f}% {s_far*100:4.1f}% | {d:+5.1f}pp {band(s_frr):>5}", flush=True)
    mod = [s for s in spks if SEVERITY[s] == "moderate"]
    md = float(np.mean([res["per_speaker"][s]["dfrr_pp"] for s in mod]))
    mfar = float(np.mean([res["per_speaker"][s]["stack_far"] for s in mod]))
    live = md >= 8.0 and mfar <= FAR_TARGET + 0.02
    res["verdict"] = dict(moderate_stack_dfrr=md, moderate_stack_far=mfar, band900_live=bool(live))
    print(f"\n=== N1 VERDICT === moderate stack dFRR={md:+.1f}pp @ FAR={mfar*100:.1f}%  "
          f"=> band-900 track {'LIVE' if live else 'CONFIRMED UNREACHABLE (pivot to P5)'}", flush=True)
    with open(os.path.join(CACHE, "n1_stack_d2.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("wrote n1_stack_d2.json", flush=True)


if __name__ == "__main__":
    main()
