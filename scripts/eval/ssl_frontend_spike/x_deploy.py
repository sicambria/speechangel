"""Tier-D/E DEPLOYMENT levers — #22 K-curve, #21 exemplar selection, #29 vocab co-design, #28 conf-gated.
These do not attack the score-transform wall (Round-4/Tier-B closed that); they inform the deployable
moderate operating point and the product route. All FRR@FAR<=5% LOFO, moderate=M01/M02/F03, realized FAR
printed. NOT-BANKED (pending UASpeech #24).

#22 Dysarthric K-curve: moderate FRR@FAR vs enroll reps K in {1,2,3,4}. UX cost = K utterances at enroll.
#21 Exemplar selection at fixed K=3: first-K vs medoid-K (most central) vs diverse-K. Does WHICH reps you
    keep matter at fixed count? Success: >=5pp vs first-K.
#29 Vocab co-design: FRR on the MOST-separable half of each speaker's commands vs the LEAST-separable half
    (greedy by min inter-centroid distance). A pre-enrollment lever that raises between-command distance —
    NOT subject to the monotone-score-map limit. Success: >=8pp ΔFRR from word choice alone.
#28 Confidence-gated voice: fraction of genuine turns voice can auto-accept at a TIGHT auto-FAR<=1%
    (t_acc), rest fall back to scan/dwell (assumed reliable). Reports voice-used-fraction + blended success.
"""
import os, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14; FAR_TARGET = 0.05
FEMALE = ["F01", "F03", "F04"]; MALE = ["M01", "M02", "M03", "M04", "M05"]
MODERATE = ["M01", "M02", "F03"]


def load():
    zf = np.load(os.path.join(CACHE, "wavlm-large.npz"), allow_pickle=True)
    zm = np.load(os.path.join(CACHE, "male_wavlm_large.npz"), allow_pickle=True)
    emb = {}
    for z in (zf, zm):
        for k in z.files:
            emb[k] = z[k][LAYER].astype(np.float64)
    data = H.scan(TORGO); out = {}
    for spk in MODERATE:
        d = data.get(spk)
        if not d:
            continue
        cmds = {w: [emb[wav] for wav in lst if wav in emb] for w, lst in d["commands"].items()}
        cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
        negs = [emb[wav] for wav in d["negatives"] if wav in emb]
        out[spk] = {"commands": cmds, "negatives": negs}
    return out


def far_matched(rows):
    fold_ids = sorted({r[0] for r in rows}); acc = pos_n = fa = neg_n = 0
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]; test = [r for r in rows if r[0] == fo]
        neg_tr = [r for r in train if r[1] is None]
        cands = sorted({r[3] for r in train}); thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            if sum(1 for r in neg_tr if r[3] <= t) / max(1, len(neg_tr)) <= FAR_TARGET:
                thr = t
        for r in test:
            a = r[3] <= thr
            if r[1] is not None:
                pos_n += 1; acc += int(a and r[2] == r[1])
            else:
                neg_n += 1; fa += int(a)
    return (1 - acc / pos_n if pos_n else 0.0), (fa / neg_n if neg_n else 0.0), pos_n, neg_n


def rows_for(cmds, negs, k=5, enroll_pick=None, words=None):
    """Build LOFO rows. enroll_pick(reps)->subset selects which enroll reps to keep. words filters vocab."""
    words = words or list(cmds); rows = []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: (enroll_pick(v) if enroll_pick else v) for w, v in enroll.items() if v}
        enroll = {w: v for w, v in enroll.items() if len(v) >= 1}
        if not enroll:
            continue
        def score(v):
            d = {w: min(1.0 - float(v @ tv) for tv in tvs) for w, tvs in enroll.items()}
            w1 = min(d, key=d.get); return w1, d[w1]
        for w, v in pos:
            w1, s = score(v); rows.append((f, w, w1, s))
        for i, v in enumerate(negs):
            if i % k == f:
                w1, s = score(v); rows.append((f, None, w1, s))
    return rows


def medoid_k(reps, K):
    R = np.array(reps)
    if len(R) <= K:
        return reps
    D = np.array([[1 - float(a @ b) for b in R] for a in R])
    order = np.argsort(D.sum(1))          # most central first
    return [reps[i] for i in order[:K]]


def diverse_k(reps, K):
    R = np.array(reps)
    if len(R) <= K:
        return reps
    D = np.array([[1 - float(a @ b) for b in R] for a in R])
    chosen = [int(np.argmax(D.sum(1)))]   # start from the outlier
    while len(chosen) < K:
        rest = [i for i in range(len(R)) if i not in chosen]
        nxt = max(rest, key=lambda i: min(D[i][j] for j in chosen))
        chosen.append(nxt)
    return [reps[i] for i in chosen]


def main():
    data = load()
    out = {"layer": LAYER}
    # ---- #22 K-curve
    print("=== #22 Dysarthric K-curve (moderate FRR@FAR<=5% vs enroll reps K) ===", flush=True)
    print(f"{'K':>2} | " + "  ".join(f"{s:>7}" for s in MODERATE) + "   mean_FRR  mean_FAR", flush=True)
    kc = {}
    for K in (1, 2, 3, 4):
        per = {}
        for s in MODERATE:
            rows = rows_for(data[s]["commands"], data[s]["negatives"],
                            enroll_pick=lambda v, K=K: v[:K])
            frr, far, np_, nn_ = far_matched(rows); per[s] = (frr, far)
        mfrr = float(np.mean([per[s][0] for s in MODERATE])); mfar = float(np.mean([per[s][1] for s in MODERATE]))
        kc[K] = dict(mean_frr=mfrr, mean_far=mfar, per={s: per[s][0] for s in MODERATE})
        print(f"{K:>2} | " + "  ".join(f"{per[s][0]*100:6.1f}%" for s in MODERATE) +
              f"   {mfrr*100:6.1f}%  {mfar*100:5.1f}%", flush=True)
    out["kcurve22"] = kc

    # ---- #21 exemplar selection at K=3
    print("\n=== #21 Exemplar selection @ K=3 (first vs medoid vs diverse) ===", flush=True)
    sel = {}
    for name, pick in [("first", lambda v: v[:3]), ("medoid", lambda v: medoid_k(v, 3)),
                       ("diverse", lambda v: diverse_k(v, 3))]:
        vals = []
        for s in MODERATE:
            rows = rows_for(data[s]["commands"], data[s]["negatives"], enroll_pick=pick)
            frr, far, _, _ = far_matched(rows); vals.append((frr, far))
        mfrr = float(np.mean([v[0] for v in vals])); mfar = float(np.mean([v[1] for v in vals]))
        sel[name] = dict(frr=mfrr, far=mfar)
        print(f"  {name:>8}: FRR={mfrr*100:5.1f}%  FAR={mfar*100:4.1f}%", flush=True)
    out["exemplar21"] = sel
    d21 = (sel["first"]["frr"] - min(sel["medoid"]["frr"], sel["diverse"]["frr"])) * 100

    # ---- #29 vocab co-design: most- vs least-separable half of each speaker's commands
    print("\n=== #29 Vocab co-design (most- vs least-separable half by inter-centroid dist) ===", flush=True)
    voc = {}
    for tag in ("most", "least"):
        vals = []
        for s in MODERATE:
            cmds = data[s]["commands"]; words = list(cmds)
            cent = {w: np.mean(cmds[w], 0) for w in words}
            cent = {w: c / (np.linalg.norm(c) + 1e-9) for w, c in cent.items()}
            # each word's nearest-neighbor centroid distance (higher = more separable)
            nnd = {w: min(1 - float(cent[w] @ cent[w2]) for w2 in words if w2 != w) for w in words}
            order = sorted(words, key=lambda w: nnd[w], reverse=(tag == "most"))
            half = order[:max(2, len(words) // 2)]
            rows = rows_for(cmds, data[s]["negatives"], words=half)
            frr, far, _, _ = far_matched(rows); vals.append((frr, far, len(half)))
        mfrr = float(np.mean([v[0] for v in vals])); mfar = float(np.mean([v[1] for v in vals]))
        voc[tag] = dict(frr=mfrr, far=mfar)
        print(f"  {tag:>5}-separable half: FRR={mfrr*100:5.1f}%  FAR={mfar*100:4.1f}%", flush=True)
    d29 = (voc["least"]["frr"] - voc["most"]["frr"]) * 100
    out["vocab29_insample"] = dict(most=voc["most"], least=voc["least"], dfrr_pp=d29)
    print(f"  [in-sample] ΔFRR (least->most separable) = {d29:+.1f}pp  <-- SELECTION-ON-TEST, optimistic", flush=True)

    # #29b HELD-OUT vocab selection: rank shared words by separability on the OTHER moderate speakers,
    # apply the most/least-separable half to the held-out speaker. Removes the in-sample optimism —
    # deployment chooses the vocab by WORD IDENTITY (shared across users), not the target's own reps.
    shared = set.intersection(*[set(data[s]["commands"]) for s in MODERATE])
    print(f"\n=== #29b Vocab co-design HELD-OUT (rank on other speakers; {len(shared)} shared words) ===", flush=True)
    vocb = {}
    for tag in ("most", "least"):
        vals = []
        for s in MODERATE:
            others = [o for o in MODERATE if o != s]
            nnd = {}
            for w in shared:
                ds = []
                for o in others:
                    cmds = data[o]["commands"]
                    cent = {ww: np.mean(cmds[ww], 0) for ww in shared}
                    cent = {ww: c / (np.linalg.norm(c) + 1e-9) for ww, c in cent.items()}
                    ds.append(min(1 - float(cent[w] @ cent[w2]) for w2 in shared if w2 != w))
                nnd[w] = float(np.mean(ds))
            order = sorted(shared, key=lambda w: nnd[w], reverse=(tag == "most"))
            half = order[:max(2, len(shared) // 2)]
            rows = rows_for(data[s]["commands"], data[s]["negatives"], words=half)
            frr, far, _, _ = far_matched(rows); vals.append((frr, far))
        mfrr = float(np.mean([v[0] for v in vals])); mfar = float(np.mean([v[1] for v in vals]))
        vocb[tag] = dict(frr=mfrr, far=mfar)
        print(f"  {tag:>5}-separable (held-out rank): FRR={mfrr*100:5.1f}%  FAR={mfar*100:4.1f}%", flush=True)
    d29b = (vocb["least"]["frr"] - vocb["most"]["frr"]) * 100
    out["vocab29_heldout"] = dict(most=vocb["most"], least=vocb["least"], dfrr_pp=d29b,
                                  clears_8pp=bool(d29b >= 8.0), banked=False)
    print(f"  [held-out] ΔFRR = {d29b:+.1f}pp  => "
          f"{'vocab choice generalizes (>=8pp, NOT-BANKED pending #24)' if d29b>=8 else 'sub-8pp held-out; in-sample gain was optimism'}",
          flush=True)

    # ---- #28 confidence-gated voice: fraction auto-acceptable at tight auto-FAR<=1%
    print("\n=== #28 Confidence-gated voice (voice auto-accept @ auto-FAR<=1%; rest -> scan/dwell) ===", flush=True)
    cg = {}
    for s in MODERATE:
        rows = rows_for(data[s]["commands"], data[s]["negatives"])
        negs = sorted(r[3] for r in rows if r[1] is None)
        t_acc = negs[max(0, int(0.01 * len(negs)) - 1)] if negs else 0.0
        pos = [r for r in rows if r[1] is not None]
        voice_used = sum(1 for r in pos if r[3] <= t_acc) / max(1, len(pos))
        voice_correct = sum(1 for r in pos if r[3] <= t_acc and r[2] == r[1]) / max(1, len(pos))
        cg[s] = dict(voice_used=voice_used, voice_correct=voice_correct, t_acc=float(t_acc))
        print(f"  {s}: voice auto-handles {voice_used*100:.1f}% of turns ({voice_correct*100:.1f}% correctly); "
              f"rest -> fallback", flush=True)
    vused = float(np.mean([cg[s]["voice_used"] for s in MODERATE]))
    out["confgated28"] = dict(per=cg, mean_voice_used=vused)
    print(f"  mean voice-used fraction @ auto-FAR<=1% = {vused*100:.1f}%  (blended task-success ~100% via "
          f"reliable fallback; the metric is how much fast-voice you get)", flush=True)

    with open(os.path.join(CACHE, "x_deploy.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n=== SUMMARY === K-curve K1->K4 FRR {kc[1]['mean_frr']*100:.0f}%->{kc[4]['mean_frr']*100:.0f}%; "
          f"#21 best-selection dFRR={d21:+.1f}pp; #29 vocab dFRR in-sample={d29:+.1f}pp / held-out={d29b:+.1f}pp; "
          f"#28 voice-used={vused*100:.0f}%", flush=True)
    print("wrote x_deploy.json", flush=True)


if __name__ == "__main__":
    main()
