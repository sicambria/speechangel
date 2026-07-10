"""L26 (reframed) — within-word vs nearest-between-word variance decomposition (dysarthric in-vocab wall).

Cohabitant-rejection is OUT OF SCOPE (product threat-model decision 2026-07-10: mainstream-assistant
model). So the binding wall is IN-VOCAB COMMAND CONFUSION only: the user says command A and it lands
closer to command B's templates than to A's. This diagnostic decides whether ANY lever (H6 vocab
co-design, G1/G2 within-word contraction) has headroom, by decomposing the geometry that governs it.

Per speaker (wavlm-large L15), words with >=2 reps:
  within   = mean genuine leave-one-out distance (a rep to the centroid of its word's OTHER reps)
  betw_min = mean over words of the distance to the NEAREST OTHER word centroid (the confusor that bites)
  fisher   = betw_min / within   (>1 => separable in principle; <=1 => confusion unavoidable)
  rank1err = fraction of genuine queries whose nearest template belongs to a DIFFERENT word
             (leave-one-out, threshold-free) — the irreducible in-vocab confusion floor.
Reported for ALL commands and the vocab-distinct<=25 subset, dysarthric vs control (typical) contrast.

No gate/bank — this bounds the achievable D2 for H6/G1/G2 and is honest characterization only.
"""
import os, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15


def speaker_words(spk, emb, distinct):
    d = L.load_speaker(spk)
    if not d:
        return {}
    if distinct:
        keep = distinct_subset(d, emb, LAYER, 25)
        words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    else:
        words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    return {w: v for w, v in words.items() if len(v) >= 2}


def decomp(words):
    # leave-one-out within-word distances
    within = []
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            c = np.mean(rest, axis=0); c = c / (np.linalg.norm(c) + 1e-8)
            within.append(1 - float(q @ c))
    # full-word centroids
    cents = {}
    for w, vs in words.items():
        c = np.mean(vs, axis=0); cents[w] = c / (np.linalg.norm(c) + 1e-8)
    ws = list(cents)
    betw_min = []
    for w in ws:
        others = [1 - float(cents[w] @ cents[o]) for o in ws if o != w]
        if others:
            betw_min.append(min(others))
    # threshold-free rank-1 in-vocab confusion (leave-one-out templates)
    conf = tot = 0
    for wq, vs in words.items():
        for i, q in enumerate(vs):
            best_w, best_d = None, 1e9
            for w, tvs in words.items():
                pool = [tvs[j] for j in range(len(tvs)) if not (w == wq and j == i)]
                if not pool:
                    continue
                dmin = min(1 - float(q @ t) for t in pool)
                if dmin < best_d:
                    best_d, best_w = dmin, w
            tot += 1
            if best_w != wq:
                conf += 1
    return (np.mean(within) if within else float("nan"),
            np.mean(betw_min) if betw_min else float("nan"),
            conf / tot if tot else float("nan"), len(ws), tot)


def main():
    emb = L.load_emb("wavlm-large")
    print(f"L26 — within/between-word decomposition, in-vocab confusion floor (wavlm-large L{LAYER})\n", flush=True)
    out = {}
    for distinct in [False, True]:
        tag = "vocab-distinct<=25" if distinct else "ALL commands"
        print(f"  [{tag}]", flush=True)
        for grp, spks in [("DYSARTHRIC", L.DYS), ("TYPICAL(control)", L.CTL)]:
            for s in spks:
                words = speaker_words(s, emb, distinct)
                if len(words) < 2:
                    print(f"    {s}: <2 words", flush=True); continue
                wi, bm, r1, nw, nq = decomp(words)
                fisher = bm / wi if wi else float("nan")
                out[f"{s}/{tag}"] = dict(within=wi, betw_min=bm, fisher=fisher, rank1err=r1, nwords=nw, nq=nq)
                print(f"    {s:5s}[{grp[:3]}]: within={wi:.3f} betwMin={bm:.3f} fisher={fisher:.2f} "
                      f"rank1conf={r1*100:4.1f}%  (nwords={nw}, nq={nq})", flush=True)
        # aggregate dys
        dk = [f"{s}/{tag}" for s in L.DYS if f"{s}/{tag}" in out]
        ck = [f"{s}/{tag}" for s in L.CTL if f"{s}/{tag}" in out]
        if dk:
            dr = np.mean([out[k]["rank1err"] for k in dk]); df = np.mean([out[k]["fisher"] for k in dk])
            cr = np.mean([out[k]["rank1err"] for k in ck]); cf = np.mean([out[k]["fisher"] for k in ck])
            print(f"    => DYS mean: fisher={df:.2f} rank1conf={dr*100:.1f}%   |   "
                  f"CTL mean: fisher={cf:.2f} rank1conf={cr*100:.1f}%", flush=True)
        print(flush=True)
    with open(os.path.join(L.CACHE, "l26_variance_decomp.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
