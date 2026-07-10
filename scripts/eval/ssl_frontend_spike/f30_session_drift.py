"""F30 — Session-drift proxy on TORGO (stand-in for the UASpeech block-drift analysis).

The report never addresses TIME for the dysarthric population. UASpeech (blocks B1/B2/B3) is the intended
corpus but is license-gated. TORGO records each speaker across multiple Sessions -> a proxy for
cross-session drift. Question: is the severe-dys within-word plateau SHORT-TERM variability (within a
session) or SESSION DRIFT (across sessions)? Decides re-enrollment cadence and whether I2's conformal
pool needs recency weighting.

METHOD: per speaker, per word with reps spanning >=2 sessions, compare
  within-session genuine cosine distances  vs  cross-session genuine cosine distances (wavlm-large L15).
If cross >> within -> drift (re-enrollment / recency weighting needed). If ~equal -> short-term variability.

PRE-REGISTERED READ (diagnostic, not pass/fail): report the ratio cross/within per population; flag drift
if dys cross-session median exceeds within-session median by >= 20% AND the gap exceeds the control gap.
"""
import os, json, itertools
import numpy as np
import cand_lib as L

LAYER = 15


def speaker_gaps(spk, emb, layer):
    d = L.load_speaker(spk)
    within, cross = [], []
    n_words = 0
    for w, wavs in d["commands"].items():
        reps = [(x, emb[x][layer], L.session_of(x)) for x in wavs if x in emb]
        sess = {}
        for x, v, s in reps:
            sess.setdefault(s, []).append(v)
        if len([s for s in sess if len(sess[s]) >= 1]) < 2:
            # need multi-session coverage
            if not any(len(v) >= 2 for v in sess.values()):
                continue
        n_words += 1
        # within-session pairs
        for s, vs in sess.items():
            for a, b in itertools.combinations(range(len(vs)), 2):
                within.append(1 - float(vs[a] @ vs[b]))
        # cross-session pairs
        ss = list(sess)
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                for va in sess[ss[i]]:
                    for vb in sess[ss[j]]:
                        cross.append(1 - float(va @ vb))
    return np.array(within), np.array(cross), n_words


def main():
    emb = L.load_emb("wavlm-large")
    print(f"F30 — TORGO session-drift proxy (wavlm-large L{LAYER})\n", flush=True)
    print(f"  {'spk':>5} {'grp':>4}  {'within med':>10} {'cross med':>10}  ratio  {'#words':>6}", flush=True)
    out = {}
    for grp, spks in [("DYS", L.DYS), ("CTL", L.CTL)]:
        for s in spks:
            wi, cr, nw = speaker_gaps(s, emb, LAYER)
            if wi.size < 5 or cr.size < 5:
                print(f"  {s:>5} {grp:>4}  insufficient multi-session coverage", flush=True); continue
            wm, cm = float(np.median(wi)), float(np.median(cr))
            out[s] = dict(grp=grp, within_med=wm, cross_med=cm, ratio=cm / wm, n_words=nw,
                          n_within=int(wi.size), n_cross=int(cr.size))
            print(f"  {s:>5} {grp:>4}  {wm:10.3f} {cm:10.3f}  {cm/wm:5.2f}  {nw:>6}", flush=True)
    dys = [v for v in out.values() if v["grp"] == "DYS"]
    ctl = [v for v in out.values() if v["grp"] == "CTL"]
    if dys:
        dr = np.mean([v["ratio"] for v in dys]); cr_ = np.mean([v["ratio"] for v in ctl]) if ctl else 1.0
        drift = dr >= 1.20 and dr > cr_
        print(f"\n  DYS mean cross/within ratio={dr:.2f}  CTL={cr_:.2f}", flush=True)
        print(f"  READ: {'SESSION DRIFT present -> re-enrollment / recency weighting warranted' if drift else 'plateau is SHORT-TERM variability (drift not dominant); re-enrollment cadence relaxed'}", flush=True)
        out["_read"] = dict(dys_ratio=float(dr), ctl_ratio=float(cr_), drift=bool(drift))
    with open(os.path.join(L.CACHE, "f30_session_drift.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
