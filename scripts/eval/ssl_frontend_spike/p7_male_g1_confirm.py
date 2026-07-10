"""P7 — G1 confirmation on REAL held-out MALE dysarthric speakers (the banking step Round-2 lacked).

G1 (per-user within-word whitening) was a DIRECTIONAL positive in Round-2 on n=3 FEMALE TORGO (+10.6pp,
p=0.004), un-bankable for lack of a 2nd dysarthric population. Real male TORGO (M01-M05, P6) is that
population. G1 is PER-USER (each speaker fits their own transform), so the confirmation is: does the
Round-2 PRE-REGISTERED config (zca, r=32, eps=0.1 — chosen and fixed BEFORE seeing any male data) replicate
UNCHANGED on the held-out male speakers, adjudicated by paired McNemar at matched FAR?

Bank rule: if male in-vocab D2 FRR drops significantly (paired) at the frozen config, G1's dysarthric
benefit is confirmed to generalize across speakers -> BANKED as a speaker-general dysarthric lever (scope:
TORGO channel; band, not the whole composite). If it reverses/nulls, G1 stays female-TORGO-specific.
"""
import os, json
import numpy as np
import harness as H
import cand_lib as L
from held_out_d2 import distinct_subset
from g1_contraction import fit_transform
from g1_confirm import mcnemar

TORGO = os.path.expanduser("~/torgo")
LAYER = 15; FAR = 0.05; K = 5
METHOD, R, EPS = "zca", 32, 0.1  # FROZEN from Round-2, pre-registered
MALECACHE = os.path.join(L.CACHE, "male_wavlm_large.npz")
MALE = ["M01", "M02", "M03", "M04", "M05"]


def male_words(spk, emb):
    d = H.scan(TORGO).get(spk)
    if not d:
        return {}, []
    keep = distinct_subset(d, emb, LAYER, 25)
    words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    return words, negs


def paired_outcomes(words, negs, method, r, eps):
    gen, imp = {}, []
    for f in range(K):
        train = {w: [vs[j] for j in range(len(vs)) if j % K != f] for w, vs in words.items()}
        train = {w: vs for w, vs in train.items() if len(vs) >= 1}
        if len(train) < 3:
            continue
        T = fit_transform(train, method, r, eps)
        tmpl = {w: [T(v) for v in vs] for w, vs in train.items()}
        for ni, nv in enumerate(negs):
            if ni % K != f:
                continue
            pv = T(nv)
            imp.append(min(min(1 - float(pv @ t) for t in tt) for tt in tmpl.values()))
        for wq, vs in words.items():
            if wq not in tmpl:
                continue
            for j in range(len(vs)):
                if j % K != f:
                    continue
                gen[(wq, j)] = min(1 - float(T(vs[j]) @ t) for t in tmpl[wq])
    if not imp or not gen:
        return {}
    thr = np.sort(imp)[max(0, int(FAR * len(imp)) - 1)]
    return {k: bool(d <= thr) for k, d in gen.items()}


def main():
    if not os.path.exists(MALECACHE):
        print("  male embeddings not built yet (run p6_male_embed.py first)."); return
    z = np.load(MALECACHE, allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    print(f"P7 — G1 (FROZEN {METHOD} r{R} eps{EPS}) on REAL held-out MALE dysarthric — in-vocab D2 FRR@FAR<=5%\n", flush=True)
    accR, accN = {}, {}
    out = {}
    for spk in MALE:
        words, negs = male_words(spk, emb)
        if len(words) < 3:
            print(f"  {spk}: <3 words, skip", flush=True); continue
        aR = paired_outcomes(words, negs, "raw", 0, 0)
        aN = paired_outcomes(words, negs, METHOD, R, EPS)
        if not aR or not aN:
            print(f"  {spk}: insufficient folds", flush=True); continue
        fR = 1 - np.mean(list(aR.values())); fN = 1 - np.mean(list(aN.values()))
        b, c, n, p = mcnemar(aR, aN)
        out[spk] = dict(raw=float(fR), g1=float(fN), b=b, c=c, p=float(p), n=len(aR))
        print(f"  {spk}: raw={fR*100:5.1f}%  G1={fN*100:5.1f}%  (Δ={-(fN-fR)*100:+.1f}pp)  "
              f"McNemar b={b} c={c} p={p:.3f}  n={len(aR)}", flush=True)
        for k, v in aR.items():
            accR[(spk, k)] = v
        for k, v in aN.items():
            accN[(spk, k)] = v
    if accR:
        fR = 1 - np.mean(list(accR.values())); fN = 1 - np.mean(list(accN.values()))
        b, c, n, p = mcnemar(accR, accN)
        print(f"\n  POOLED MALE: raw={fR*100:.1f}%  G1={fN*100:.1f}%  (Δ={-(fN-fR)*100:+.1f}pp)  "
              f"McNemar b={b}(hurt) c={c}(helped) p={p:.4f}  n_items={len(accR)}", flush=True)
        print(f"  Round-2 FEMALE (ref): raw 55.3% -> G1 44.7%, +10.6pp, p=0.004", flush=True)
        verdict = "CONFIRMED (speaker-general dysarthric lever)" if (fN < fR and p < 0.05) else \
                  ("null (underpowered/no effect)" if p >= 0.05 else "REVERSED (female-specific)")
        print(f"  => G1 on real held-out male dysarthric: {verdict}", flush=True)
        out["_pooled"] = dict(raw=float(fR), g1=float(fN), b=b, c=c, p=float(p), n=len(accR), verdict=verdict)
    with open(os.path.join(L.CACHE, "p7_male_g1_confirm.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
