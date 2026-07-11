"""T7 — MEASURED negative for the typical-D2 layer route (bank-strengthening).

The t6 map showed: (1) single-layer selection is closed (L12 best, 5.81%); (2) the 2 hardest
speakers are walled at EVERY layer (98ea0818 never <23%, 2aca1e72 flat 19-29%); (3) an ORACLE
per-speaker-best-layer hits 4.06% (band 900) but that is min-over-19-layers on 48 test
queries/speaker — mostly minimum-of-noise (it harvests isolated dips at globally-WORST layers,
e.g. c1d39ce8 12%@L24 where the aggregate is 9%).

This harness converts the argued negative into a MEASURED one, all from the cache (no re-encode):
  (A) DE-NOISED ORACLE — recompute per-speaker-best-layer capped to the SMOOTH mid-band
      (exclude the globally-worst layers). If even this optimistic, test-picked bound stays
      band 800, no deployable lever can clear 900 (a-fortiori).
  (B) DEPLOYABLE per-speaker layer selection (held-out): layer chosen on TRAIN folds by
      genuine/impostor d', threshold fit on train negs, evaluated on the held-out fold. The
      real deployable number (<= the de-noised oracle by construction).
  (C) FUSION sanity: mean-cosine over mid-band and over all layers vs L12 — confirms fusion
      BLENDS (drags single-peak speakers down), does not beat L12, with a number not a claim.
  (D) DATA-ARTIFACT probe: clipping / RMS / duration of the 3-4 hard speakers' clips — if one
      hard speaker is a data artifact, the true D2 is BETTER than 5.8% (still not 900).

Fidelity (EVAL-004): scoring/threshold primitives (score_query, global_threshold_accept,
held_out_frr_far) reused VERBATIM from cand_lib; folds/K/agg identical to a5.kcurve_speaker.
Adjudicated on FRR@matched-FAR (EVAL-007); band 900 = FRR<=5% (DomainBands.kt spec 2). Baseline
= L12 5.81% (t1/t6 K5). NOT a banking of any positive — this measures that the route is closed.
"""
import os, json
import numpy as np
import soundfile as sf
import cand_lib as L
import harness as H
from a5_gsc_kcurve import build_cache, kcurve_speaker

LAYERS = list(range(6, 25))
K = 5
DEPLOY_L = 12
FAR = 0.05


def scored_folds(man_s, emb, layer):
    """Mirror a5.kcurve_speaker's fold/enroll/K/min-agg EXACTLY, but return per-query scored rows
    with fold ids so we can pick a layer on train folds and evaluate a held-out fold."""
    words = {w: [emb[p][layer] for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [emb[p][layer] for p in man_s["neg"]]
    pos, neg = [], []
    for w, vecs in words.items():
        for i, qv in enumerate(vecs):
            f = i % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                if ww == w:
                    pool = [vv[j] for j in range(len(vv)) if j != i and (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                pos.append((f, w, L.score_query(qv, enroll, "min")))
    for ni, nv in enumerate(negs):
        f = ni % 5
        enroll = {}
        for ww, vv in words.items():
            pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
            if pool:
                enroll[ww] = pool[:K]
        if enroll:
            neg.append((f, L.score_query(nv, enroll, "min")))
    return pos, neg


def dprime_sep(g, imp):
    """Separation of genuine (small dist) vs impostor (large dist). Higher = better."""
    g, imp = np.asarray(g), np.asarray(imp)
    if len(g) == 0 or len(imp) == 0:
        return -1e9
    return float((imp.mean() - g.mean()) / np.sqrt(0.5 * (g.var() + imp.var()) + 1e-9))


def kcurve_flat(man_s, emb_flat, K=K):
    """kcurve_speaker for a FLAT emb dict (emb_flat[p] = one vector, e.g. a fused embedding)."""
    words = {w: [emb_flat[p] for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [emb_flat[p] for p in man_s["neg"]]
    pos_rows, fp, neg_rows, fn = [], [], [], []
    for w, vecs in words.items():
        for i, qv in enumerate(vecs):
            f = i % 5
            enroll = {}
            for ww, vv in words.items():
                pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                if ww == w:
                    pool = [vv[j] for j in range(len(vv)) if j != i and (j % 5) != f]
                if pool:
                    enroll[ww] = pool[:K]
            if enroll:
                pos_rows.append((w, L.score_query(qv, enroll, "min"))); fp.append(f)
    for ni, nv in enumerate(negs):
        f = ni % 5
        enroll = {}
        for ww, vv in words.items():
            pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
            if pool:
                enroll[ww] = pool[:K]
        if enroll:
            neg_rows.append((None, L.score_query(nv, enroll, "min"))); fn.append(f)
    return L.held_out_frr_far(pos_rows, neg_rows, fp, fn, L.global_threshold_accept, target=FAR)


def fused(emb, paths, layer_set):
    out = {}
    for p in paths:
        v = np.concatenate([emb[p][l] for l in layer_set])
        out[p] = (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)
    return out


def audio_stats(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    clip = float(np.mean(np.abs(x) > 0.98)) if x.size else 0.0
    rms = float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0
    sp = H.energy_vad_trim(x)
    return {"dur_s": x.size / sr, "peak": peak, "clip_frac": clip,
            "rms_dbfs": 20 * np.log10(rms + 1e-9), "voiced_frac": sp.size / max(1, x.size)}


def main():
    print("T7 MEASURED NEGATIVE — typical-D2 layer route is closed\n", flush=True)
    man, emb = build_cache()
    spks = list(man.keys())
    npos_tot = sum(len(ps) for s in spks for ps in man[s]["fixed"].values())
    print(f"  {len(spks)} speakers, npos={npos_tot}, baseline L{DEPLOY_L} K{K} = 5.81% (band 800)\n", flush=True)

    # per-speaker per-layer FRR (recompute; cheap) + aggregate FAR
    mat = {s: {} for s in spks}
    agg = {}
    for lyr in LAYERS:
        num = den = fnum = fden = 0
        for s in spks:
            frr, far, np_, nn = kcurve_speaker(man[s], emb, K, layer=lyr)
            mat[s][lyr] = (frr, np_)
            num += frr * np_; den += np_; fnum += far * nn; fden += nn
        agg[lyr] = (num / den, fnum / fden)
    worst_layers = sorted(LAYERS, key=lambda l: -agg[l][0])[:4]   # globally-worst 4 layers
    smooth = [l for l in LAYERS if l not in worst_layers]
    print(f"  globally-worst layers (excluded from de-noised oracle): {worst_layers}", flush=True)

    # (A) de-noised oracle: per-speaker best layer restricted to the smooth set
    def oracle(layer_pool):
        num = den = 0
        for s in spks:
            bl = min(layer_pool, key=lambda l: mat[s][l][0])
            frr, np_ = mat[s][bl]
            num += frr * np_; den += np_
        return num / den
    full_oracle = oracle(LAYERS)
    denoised = oracle(smooth)
    print(f"\n  (A) ORACLE per-speaker-best-layer  [selection-on-test upper bounds]:", flush=True)
    print(f"        full (all 19 layers):  {full_oracle*100:.2f}%  band {900 if full_oracle<=.05 else 800}", flush=True)
    print(f"        de-noised (smooth set): {denoised*100:.2f}%  band {900 if denoised<=.05 else 800}"
          f"   <- even the de-noised optimistic bound", flush=True)

    # (B) deployable per-speaker layer selection (held-out): layer picked on TRAIN folds by d'
    sf_scored = {s: {l: scored_folds(man[s], emb, l) for l in smooth} for s in spks}
    acc = pos = fa = neg = 0
    picks = {}
    for s in spks:
        for testf in range(5):
            best_l, best_dp = DEPLOY_L, -1e9
            for l in smooth:
                P, N = sf_scored[s][l]
                g = [sc[0][0] for f, w, sc in P if f != testf and sc and sc[0][1] == w]
                im = [sc[0][0] for f, sc in N if f != testf and sc]
                dp = dprime_sep(g, im)
                if dp > best_dp:
                    best_dp, best_l = dp, l
            picks.setdefault(s, []).append(best_l)
            P, N = sf_scored[s][best_l]
            trp = [sc for f, w, sc in P if f != testf and sc]
            trn = [sc for f, sc in N if f != testf and sc]
            accept = L.global_threshold_accept(trp, trn, FAR)
            for f, w, sc in P:
                if f == testf and sc:
                    pos += 1
                    if accept(sc) and sc[0][1] == w:
                        acc += 1
            for f, sc in N:
                if f == testf and sc:
                    neg += 1
                    if accept(sc):
                        fa += 1
    dep_frr, dep_far = 1 - acc / pos, fa / neg
    print(f"\n  (B) DEPLOYABLE per-speaker layer (held-out, layer picked on train d'):", flush=True)
    print(f"        FRR {dep_frr*100:.2f}%  FAR {dep_far*100:.1f}%  band {900 if dep_frr<=.05 and dep_far<=.07 else 800}"
          f"   <- the real deployable number", flush=True)

    # (C) fusion sanity — mean-cosine over layer sets vs L12
    print(f"\n  (C) FUSION sanity (mean-cosine over layer set) vs L{DEPLOY_L} 5.81%:", flush=True)
    allpaths = [p for s in spks for ps in man[s]["fixed"].values() for p in ps] + \
               [p for s in spks for p in man[s]["neg"]]
    for name, ls in [("mid L9-16", list(range(9, 17))), ("all L6-24", LAYERS)]:
        ef = fused(emb, set(allpaths), ls)
        num = den = fnum = fden = 0
        for s in spks:
            frr, far, np_, nn = kcurve_flat(man[s], {p: ef[p] for ps in man[s]["fixed"].values() for p in ps}
                                            | {p: ef[p] for p in man[s]["neg"]}, K)
            num += frr * np_; den += np_; fnum += far * nn; fden += nn
        print(f"        fuse {name:>9}: FRR {num/den*100:.2f}%  FAR {fnum/fden*100:.1f}%"
              f"   {'(worse than L12)' if num/den > 0.0581 else '(<= L12)'}", flush=True)

    # (D) data-artifact probe on the hard speakers
    hard = sorted(spks, key=lambda s: -mat[s][DEPLOY_L][0])[:4]
    print(f"\n  (D) DATA-ARTIFACT probe (hard speakers, mean over their fixed-word clips):", flush=True)
    art = {}
    for s in hard:
        ps = [p for w in man[s]["fixed"] for p in man[s]["fixed"][w]]
        st = [audio_stats(p) for p in ps]
        art[s] = {k: float(np.mean([d[k] for d in st])) for k in st[0]}
        art[s]["n"] = len(ps); art[s]["frr_L12"] = mat[s][DEPLOY_L][0]
        print(f"        {s[:9]}  FRR@L12 {mat[s][DEPLOY_L][0]*100:>3.0f}%  "
              f"dur {art[s]['dur_s']:.2f}s  peak {art[s]['peak']:.2f}  clip {art[s]['clip_frac']*100:.1f}%  "
              f"rms {art[s]['rms_dbfs']:.0f}dBFS  voiced {art[s]['voiced_frac']*100:.0f}%", flush=True)

    with open(os.path.join(L.CACHE, "t7_layer_negative.json"), "w") as f:
        json.dump({"baseline_L12": agg[DEPLOY_L][0], "worst_layers": worst_layers,
                   "oracle_full": full_oracle, "oracle_denoised": denoised,
                   "deployable_perspk": {"frr": dep_frr, "far": dep_far},
                   "picks_mode": {s: max(set(v), key=v.count) for s, v in picks.items()},
                   "artifacts": art}, f, indent=2)
    print("\n  wrote t7_layer_negative.json", flush=True)


if __name__ == "__main__":
    main()
