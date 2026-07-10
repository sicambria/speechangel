"""B13 — Conformal validity engineering (cached negative-side coverage).

I2's rejection guarantee relies on conformal calibration: pick a threshold at the alpha-quantile of a
calibration negative pool so held-out negative FAR <= alpha. Two documented threats:
  (a) EXCHANGEABILITY — a naive i.i.d. quantile is only valid if calibration & test negatives are
      exchangeable. Block structure (correlated negatives) can break coverage.
  (b) CONTAMINATION — if user/genuine speech leaks into the negative calibration pool, the quantile is
      pulled and the realized FAR exceeds alpha.

This cached version uses the control speakers' IN-VOCAB confusor negatives (a real negative distribution)
to test both, at target alpha=5%:
  (a) i.i.d. split vs BLOCK split (calibrate on some words' negatives, test on held-out words' negatives)
      -> does block structure inflate realized FAR above alpha?
  (b) inject a fraction of genuine scores into the calibration pool -> realized-FAR drift.
The ambient-stream / temporal-drift pieces (c) need the A3 streamer and are noted partial.

PRE-REGISTERED read (diagnostic): report realized held-out FAR under i.i.d. vs block calibration, and the
FAR inflation per % contamination. Flag exchangeability risk if block realized-FAR > 1.5×alpha.
"""
import os, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15
ALPHA = 0.05
np.random.seed(0)


def speaker_neg_scores(spk, emb, layer):
    """Nearest-command cosine distance for each in-vocab confusor negative, tagged by the word it hits.
    Also genuine nearest-distances (for contamination injection)."""
    d = L.load_speaker(spk)
    keep = distinct_subset(d, emb, layer, 25)
    templ = {w: [emb[x][layer] for x in d["commands"][w] if x in emb] for w in keep}
    templ = {w: v for w, v in templ.items() if v}
    if len(templ) < 4:
        return None
    def nn(v):
        best = min((min(1 - float(v @ t) for t in tt), w) for w, tt in templ.items())
        return best
    negs = []
    for x in d["negatives"]:
        if x in emb:
            dist, w = nn(emb[x][layer]); negs.append((dist, w))
    gen = []
    for w, tt in templ.items():
        for i in range(len(tt)):
            rest = [tt[j] for j in range(len(tt)) if j != i]
            if rest:
                gen.append(min(1 - float(tt[i] @ r) for r in rest))
    return negs, gen, list(templ)


def realized_far(cal_dists, test_dists, alpha):
    q = np.quantile(cal_dists, alpha) if len(cal_dists) else 0
    return float(np.mean(np.array(test_dists) <= q))


def main():
    emb = L.load_emb("wavlm-large")
    print(f"B13 — conformal negative-side validity (wavlm-large L{LAYER}, target alpha={ALPHA})\n", flush=True)
    iid_fars, block_fars = [], []
    contam = {c: [] for c in [0.0, 0.05, 0.10, 0.20]}
    for spk in L.CTL:
        r = speaker_neg_scores(spk, emb, LAYER)
        if r is None:
            continue
        negs, gen, words = r
        dists = np.array([d for d, _ in negs])
        tags = [w for _, w in negs]
        # (a-iid) random 50/50
        idx = np.random.permutation(len(dists))
        half = len(idx) // 2
        iid_fars.append(realized_far(dists[idx[:half]], dists[idx[half:]], ALPHA))
        # (a-block) calibrate on half the WORDS' negatives, test on the other half's
        wset = list(dict.fromkeys(tags))
        np.random.shuffle(wset)
        calw = set(wset[: len(wset) // 2])
        cal = [dists[i] for i in range(len(dists)) if tags[i] in calw]
        tst = [dists[i] for i in range(len(dists)) if tags[i] not in calw]
        if cal and tst:
            block_fars.append(realized_far(cal, tst, ALPHA))
        # (b) contamination: inject genuine into calibration pool
        for c in contam:
            n_inj = int(c * len(dists))
            inj = np.array(list(dists) + list(np.random.choice(gen, n_inj, replace=True))) if n_inj else dists
            contam[c].append(realized_far(inj, dists, ALPHA))
    print(f"  (a) EXCHANGEABILITY (target FAR={ALPHA*100:.0f}%):", flush=True)
    print(f"      i.i.d. split : realized FAR = {np.mean(iid_fars)*100:.1f}%", flush=True)
    print(f"      BLOCK split  : realized FAR = {np.mean(block_fars)*100:.1f}%  "
          f"({'RISK — coverage broken' if np.mean(block_fars) > 1.5*ALPHA else 'ok'})", flush=True)
    print(f"  (b) CONTAMINATION (genuine leaked into calibration pool):", flush=True)
    for c in sorted(contam):
        print(f"      {int(c*100):>3}% contamination -> realized FAR = {np.mean(contam[c])*100:.1f}%", flush=True)
    print(f"  (c) temporal coverage-drift (day-1→day-7): needs the A3 ambient streamer over time — PARTIAL/queued.", flush=True)
    out = dict(iid_far=float(np.mean(iid_fars)), block_far=float(np.mean(block_fars)),
               contamination={str(c): float(np.mean(v)) for c, v in contam.items()})
    with open(os.path.join(L.CACHE, "b13_conformal.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
