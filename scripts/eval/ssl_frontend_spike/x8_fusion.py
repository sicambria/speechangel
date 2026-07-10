"""#8 (Tier B) — SCORE FUSION (pooled-cosine + frame-DTW), FAR-matched.

The one qualitatively-different Tier-B lever: even if no single scorer moves the tail, COMPLEMENTARY errors
between pooled-cosine and frame-trajectory-DTW might thin it. N1 stacked pool+backend+fdtw but landed
+3.16pp at FAR=9.1% (FAR-INVALID). This runs the fusion under the strict FAR-matched global-threshold
discipline and reuses r1's exact dual-scorer LOFO rows (same wavs, apples-to-apples).

Fusion: per fold, z-normalize each scorer's distance by the TRAIN distribution (pos+neg), fuse = mean of
z-scores; ONE global threshold fit on TRAIN fused scores to FAR<=5%; evaluate held-out; print realized FAR.
Winner word for an accept = the pooled-cosine winner (the shipped decision); fusion only re-scores.
SUCCESS: >=5pp moderate ΔFRR vs pool @ matched FAR. KILL: <1pp or FAR-invalid. NOT-BANKED (pending #24).
Moderate D2 carried by M01/M02 (male frame cache has negatives; F03 female cache has command wavs only).
"""
import os, json
import numpy as np
import r1_frame_dtw_d2 as R1

CACHE = R1.CACHE
SEVERITY = R1.SEVERITY
MODERATE_MALE = ["M01", "M02"]


def zfuse_rows(rows):
    """FAR-matched LOFO FRR for pool, fdtw, and the z-score fusion. Returns dict per scorer."""
    fold_ids = sorted({r[0] for r in rows})
    res = {}
    for name in ("pool", "fdtw", "fuse"):
        acc = pos_n = fa = neg_n = 0
        for fo in fold_ids:
            train = [r for r in rows if r[0] != fo]; test = [r for r in rows if r[0] == fo]
            neg_tr = [r for r in train if r[1] is None]
            # z-stats per scorer from TRAIN (pos+neg)
            def zstat(sc):
                v = np.array([r[2][sc][1] for r in train])
                return float(v.mean()), float(v.std() + 1e-9)
            zp = zstat("pool"); zf = zstat("fdtw")
            def val(r):
                if name == "pool":
                    return r[2]["pool"][1]
                if name == "fdtw":
                    return r[2]["fdtw"][1]
                zpv = (r[2]["pool"][1] - zp[0]) / zp[1]
                zfv = (r[2]["fdtw"][1] - zf[0]) / zf[1]
                return 0.5 * (zpv + zfv)
            cands = sorted({val(r) for r in train}); thr = (cands[0] - 1.0) if cands else 0.0
            for t in cands:
                if sum(1 for r in neg_tr if val(r) <= t) / max(1, len(neg_tr)) <= R1.FAR_TARGET:
                    thr = t
            for r in test:
                w1 = r[2]["pool"][0]  # decision word = pooled winner
                a = val(r) <= thr
                if r[1] is not None:
                    pos_n += 1; acc += int(a and w1 == r[1])
                else:
                    neg_n += 1; fa += int(a)
        res[name] = dict(frr=(1 - acc / pos_n if pos_n else 0.0), far=(fa / neg_n if neg_n else 0.0),
                         npos=pos_n, nneg=neg_n)
    return res


def main():
    frames = R1.load_frames(); pooled = R1.load_pooled()
    print("#8 SCORE FUSION (pool + frame-DTW), FAR-matched LOFO, moderate=M01/M02\n", flush=True)
    print(f"{'spk':>4} {'sev':>9} | {'pool FRR':>9} {'fdtw FRR':>9} {'fuse FRR':>9} {'fuse FAR':>9} {'dFRR':>7}", flush=True)
    out = {"far_target": R1.FAR_TARGET, "per_speaker": {}}
    for s in MODERATE_MALE:
        rows = R1.speaker_rows(s, frames, pooled)
        if not rows:
            continue
        r = zfuse_rows(rows)
        d = (r["pool"]["frr"] - r["fuse"]["frr"]) * 100
        out["per_speaker"][s] = r
        print(f"{s:>4} {SEVERITY[s]:>9} | {r['pool']['frr']*100:8.1f}% {r['fdtw']['frr']*100:8.1f}% "
              f"{r['fuse']['frr']*100:8.1f}% {r['fuse']['far']*100:8.1f}% {d:+6.1f}pp", flush=True)
    pool_m = float(np.mean([out["per_speaker"][s]["pool"]["frr"] for s in out["per_speaker"]]))
    fuse_m = float(np.mean([out["per_speaker"][s]["fuse"]["frr"] for s in out["per_speaker"]]))
    fuse_far = float(np.mean([out["per_speaker"][s]["fuse"]["far"] for s in out["per_speaker"]]))
    d = (pool_m - fuse_m) * 100
    valid = fuse_far <= 0.07
    out["verdict"] = dict(pool_frr=pool_m, fuse_frr=fuse_m, fuse_far=fuse_far, dfrr_pp=d,
                          far_valid=bool(valid), clears_5pp=bool(d >= 5 and valid), banked=False)
    print(f"\n=== VERDICT (#8) === moderate pool FRR={pool_m*100:.1f}% -> fuse FRR={fuse_m*100:.1f}% "
          f"@ FAR={fuse_far*100:.1f}%  dFRR={d:+.1f}pp  "
          f"=> {'FAR-INVALID' if not valid else ('clears 5pp' if d>=5 else 'NULL/NOT-BANKED')}", flush=True)
    with open(os.path.join(CACHE, "x8_fusion.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("wrote x8_fusion.json", flush=True)


if __name__ == "__main__":
    main()
