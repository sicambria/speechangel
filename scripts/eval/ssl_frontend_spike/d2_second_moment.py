"""#21/#22 — Second-moment (std / mean⊕std) pooling on the DYSARTHRIC D2 tail (TORGO).

Wall-CHARACTERIZATION, not a wall-break bet (frame-pooling report §7 lever #5). The parameter-free second
moment BROKE the typical mean-pooled wall (teacher 5.81→4.71, student 9.32→6.36). Does it touch the
dysarthric AUC~0.65 information-theoretic wall — or confirm the two tails are DIFFERENT (typical = recoverable
hard-voice info the mean discards; dysarthric = corrupted within-word scatter the std cannot rescue)?

Both outcomes are bankable-as-characterization; a NULL sharpens the information-theoretic bank. All positives
NOT-BANKED until UASpeech (#28) regardless. EVAL-006: males carry the D2 verdict (moderate = M01/M02, the
live population); females are cross-gender AUC context (their frame cache has command wavs only, no negatives).

Reuses r1_frame_dtw_d2's LOFO rows + d2_from_rows (identical folds/K/MAX_TPL/MAX_NEG/threshold machinery).
Scorers: mean = r1's shipped mean-pooled cosine (exact baseline) ; std / meanstd = frame-pooling of frames_norm.
Pre-registered: mild+moderate second-moment FRR ≤ mean by ≥8pp @ matched FAR = WALL BREACH; <3pp / worse = NULL
(characterization). Matched-FAR McNemar on the males adjudicates.
"""
import os, sys, json, random
import numpy as np
import harness as H
import frame_qbe as FQ
from r1_frame_dtw_d2 import (CACHE, TORGO, FAR_TARGET, SEVERITY, FEMALE, MALE, MAX_TPL, MAX_NEG,
                             load_frames, load_pooled, d2_from_rows)

random.seed(0); np.random.seed(0)


def pooled_vec(frames_wav, mode):
    return FQ.pool_vec(frames_wav.astype(np.float32), mode)


def speaker_rows(spk, frames, pooled, modes):
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
    # precompute pooled vectors per wav for the moment scorers
    allwavs = {wav for v in cmds.values() for wav in v} | set(negs)
    vec = {mode: {wav: pooled_vec(frames[wav], mode) for wav in allwavs} for mode in modes if mode != "mean"}
    rows = []
    for f in range(k):
        enroll, pos = {}, []
        for w in words:
            for i, wav in enumerate(cmds[w]):
                (pos.append((w, wav)) if i % k == f else enroll.setdefault(w, []).append(wav))
        enroll = {w: v[:MAX_TPL] for w, v in enroll.items() if v}
        if not enroll:
            continue

        def score(wav, mode):
            if mode == "mean":
                qv = pooled[wav]
                best = {w: min(1.0 - float(qv @ pooled[t]) for t in tpls) for w, tpls in enroll.items()}
            else:
                qv = vec[mode][wav]
                best = {w: min(1.0 - float(qv @ vec[mode][t]) for t in tpls) for w, tpls in enroll.items()}
            w1 = min(best, key=best.get)
            return w1, best[w1]
        for w, wav in pos:
            rows.append((f, w, {m: score(wav, m) for m in modes}))
        for wav in negs:
            if hash(wav) % k == f:
                rows.append((f, None, {m: score(wav, m) for m in modes}))
    return rows


def matched_mcnemar_torgo(rows, a="mean", b="meanstd", targets=(0.02, 0.05, 0.08)):
    """Re-threshold BOTH scorers to a common pooled FAR on the negatives, McNemar on accept-correct."""
    negs = [r for r in rows if r[1] is None]
    pos = [r for r in rows if r[1] is not None]
    out = []
    for tgt in targets:
        def thr(sc):
            cands = sorted({r[2][sc][1] for r in negs})
            t = (cands[0] - 1.0) if cands else 0.0
            for c in cands:
                if sum(1 for r in negs if r[2][sc][1] <= c) / max(1, len(negs)) <= tgt:
                    t = c
            return t
        ta, tb = thr(a), thr(b)
        fa = np.mean([r[2][a][1] <= ta for r in negs]) if negs else 0
        fb = np.mean([r[2][b][1] <= tb for r in negs]) if negs else 0
        A = [int(r[2][a][1] <= ta and r[2][a][0] == r[1]) for r in pos]
        B = [int(r[2][b][1] <= tb and r[2][b][0] == r[1]) for r in pos]
        nb = sum(1 for i in range(len(pos)) if A[i] == 1 and B[i] == 0)
        nc = sum(1 for i in range(len(pos)) if A[i] == 0 and B[i] == 1)
        import math
        chi2 = (abs(nb - nc) - 1) ** 2 / (nb + nc) if (nb + nc) else float("nan")
        p = math.erfc(math.sqrt(chi2 / 2.0)) if (nb + nc) else 1.0
        out.append(dict(target_far=tgt, far_a=float(fa), far_b=float(fb), b=nb, c=nc,
                        frr_a=1 - np.mean(A), frr_b=1 - np.mean(B), p=float(p)))
    return out


def main():
    modes = ["mean", "std", "meanstd"]
    frames = load_frames(); pooled = load_pooled()
    have_male = os.path.exists(os.path.join(CACHE, "male_frames_L14.npz"))
    spks = [s for s in FEMALE + MALE if (have_male or s in FEMALE)]
    print(f"#21 SECOND-MOMENT on DYSARTHRIC D2 — wavlm-large L14, FAR<=5% LOFO. male_frames={have_male}")
    print(f"  scorers: mean=shipped mean-cosine  std/meanstd=frame second-moment pooling\n")
    hdr = f"{'spk':>4} {'sev':>11} {'npos':>4} {'nneg':>4} |"
    for m in modes:
        hdr += f" {m+' FRR':>10} {'FAR':>5} {'AUC':>5} |"
    print(hdr)
    res = {"per_speaker": {}, "modes": modes}
    all_rows = {}
    for s in spks:
        rows = speaker_rows(s, frames, pooled, modes)
        if not rows:
            continue
        all_rows[s] = rows
        line = f"{s:>4} {SEVERITY[s]:>11}"
        res["per_speaker"][s] = {}
        for m in modes:
            r = d2_from_rows(rows, m)
            res["per_speaker"][s][m] = r
            if m == modes[0]:
                line += f" {r['npos']:>4} {r['nneg']:>4} |"
            line += f" {r['frr']*100:9.1f}% {r['far']*100:4.1f}% {r['auc']:.3f} |"
        print(line, flush=True)

    valid = [s for s in res["per_speaker"] if res["per_speaker"][s]["mean"]["nneg"] > 0]  # males (D2)
    def grp(sevs, m):
        vals = [res["per_speaker"][s][m]["frr"] for s in valid if SEVERITY[s] in sevs]
        return float(np.mean(vals)) if vals else float("nan")
    mm = ["mild", "moderate"]
    print(f"\n=== VERDICT (mild+moderate, valid-D2 speakers {valid}, matched FAR<=5%) ===")
    base = grp(mm, "mean")
    for m in ["std", "meanstd"]:
        v = grp(mm, m); d = (base - v) * 100
        verdict = "WALL BREACH (>=8pp)" if d >= 8 else ("directional" if d >= 3 else "NULL (characterization)")
        print(f"  mean {base*100:.1f}%  vs {m} {v*100:.1f}%   dFRR={d:+.1f}pp  => {verdict}")
    # pooled matched-FAR McNemar over ALL male rows (mean vs meanstd, mean vs std)
    male_rows = [r for s in valid for r in all_rows[s]]
    res["mcnemar_mean_vs_meanstd"] = matched_mcnemar_torgo(male_rows, "mean", "meanstd")
    res["mcnemar_mean_vs_std"] = matched_mcnemar_torgo(male_rows, "mean", "std")
    print("\n  matched-FAR McNemar (males pooled), mean vs meanstd:")
    for row in res["mcnemar_mean_vs_meanstd"]:
        star = "***" if row["p"] < 0.001 else "**" if row["p"] < 0.01 else "*" if row["p"] < 0.05 else "ns"
        better = "meanstd" if row["c"] > row["b"] else "mean" if row["b"] > row["c"] else "tie"
        print(f"    @FAR≤{row['target_far']*100:.0f}%: mean FRR {row['frr_a']*100:.1f}% vs meanstd "
              f"{row['frr_b']*100:.1f}%  b={row['b']} c={row['c']} p={row['p']:.2e} {star} {better}")
    res["verdict"] = {"base_mean_frr": base, "std_frr": grp(mm, "std"), "meanstd_frr": grp(mm, "meanstd"),
                      "valid_speakers": valid, "banked": False,
                      "note": "characterization only; NOT-BANKED pending UASpeech regardless"}
    with open(os.path.join(CACHE, "d2_second_moment.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("\nwrote d2_second_moment.json")


if __name__ == "__main__":
    main()
