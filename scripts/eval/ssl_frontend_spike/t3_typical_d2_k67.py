"""T3 — Typical D2 800->900: does the K-curve cross 5% at a deployable rep count?

T1/T2 left typical D2 at K5/L12/enriched-neg = 5.6% FRR @ FAR 4.2% (band 800, 0.6pp short), curve
still monotone-dropping (K4->K5 = -1.9pp). T3 extends the curve to K6/K7 on the GSC speakers that have
>=8 same-speaker reps for >=8 command words, holding the vocab FIXED at 8 commands (identical protocol
to T1/T2, enriched negatives) so the ONLY variable across the curve is K -> no vocab-size confound.

Rep budget: 6->8 reps is still a set-once enrollment with no UX downside (CONSTRAINT-001 / few-shot is
the one robustly-replicated lever). This is the honest test of whether typical D2 reaches band 900.

PRE-REGISTERED (H_D2c): on the fixed-8-command protocol, typical D2 FRR@FAR<=5% (held-out global
threshold, L12, min-agg) crosses band 900 (<=5%) at K<=7 real enrollment reps, monotone, realized
FAR<=5%, on the qualifying GSC speakers (n>=8).
  SUCCESS: agg FRR <= 5.0% at some K<=7 AND realized FAR <= 5.0% AND monotone. Report per-speaker.
Adjudicated on FRR@matched-FAR (EVAL-007); AUC diagnostic only. NOT-BANKED pending a fresh
pre-registered confirmation on a graded/independent cohort (per program discipline).
"""
import os, json, collections
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a5_gsc_kcurve import GSC, embed_net

BEST_L = 12
FIXED_WORDS = 8
REPS = 8            # command reps available (K up to 7)
NEG_REPS = 6
ALLLAYERS = os.path.join(L.CACHE, "gsc_wavlm_large_alllayers.npz")


def pick_highrep():
    words = [w for w in os.listdir(GSC) if os.path.isdir(os.path.join(GSC, w)) and not w.startswith("_")]
    sw = collections.defaultdict(lambda: collections.defaultdict(list))
    for w in words:
        for f in sorted(os.listdir(os.path.join(GSC, w))):
            if f.endswith(".wav"):
                sw[f.split("_")[0]][w].append(os.path.join(GSC, w, f))
    picks = []
    for spk, wc in sw.items():
        hi = sorted([w for w, fs in wc.items() if len(fs) >= REPS])
        negw = sorted([w for w, fs in wc.items() if w not in hi and len(fs) >= 4])
        if len(hi) >= FIXED_WORDS and len(negw) >= 6:
            picks.append((spk, hi[:FIXED_WORDS], negw, wc))
    picks.sort(key=lambda x: x[0])
    return picks


def build():
    picks = pick_highrep()
    man = {}; need = []
    for spk, hi, negw, wc in picks:
        fixed = {w: wc[w][:REPS] for w in hi}
        neg = []
        for w in negw:
            neg += wc[w][:NEG_REPS]
        man[spk] = {"fixed": fixed, "neg": neg}
        for ps in fixed.values():
            need += ps
        need += neg
    z = np.load(ALLLAYERS, allow_pickle=True) if os.path.exists(ALLLAYERS) else None
    emb = {k: z[k] for k in z.files} if z is not None else {}
    todo = [p for p in need if p not in emb]
    if todo:
        from transformers import AutoModel
        net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
        print(f"  embedding {len(todo)} new GSC clips...", flush=True)
        for i, p in enumerate(todo):
            emb[p] = embed_net(net, p)
            if (i + 1) % 100 == 0:
                print(f"    {i+1}/{len(todo)}", flush=True)
        np.savez(ALLLAYERS, **emb)
    return man, emb


def kcurve(man_s, emb, K, layer):
    words = {w: [emb[p][layer] for p in ps] for w, ps in man_s["fixed"].items()}
    negs = [emb[p][layer] for p in man_s["neg"]]
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
    return L.held_out_frr_far(pos_rows, neg_rows, fp, fn, L.global_threshold_accept, target=0.05)


def main():
    print("T3 TYPICAL D2 K6/K7 — fixed-8-command, enriched-neg, L%d\n" % BEST_L, flush=True)
    man, emb = build()
    print(f"  {len(man)} speakers (>=8 reps x 8 fixed commands)\n", flush=True)
    print(f"  {'K':>2}  {'FRR':>7}  {'FAR':>6}   band   per-speaker FRR", flush=True)
    curve = []
    for K in [1, 2, 3, 4, 5, 6, 7]:
        num = den = fanum = fdenom = 0
        per = []
        for spk in man:
            frr, far, npos, nn = kcurve(man[spk], emb, K, BEST_L)
            num += frr * npos; den += npos
            fanum += far * nn; fdenom += nn
            per.append(frr)
        agg = num / den; fa = fanum / fdenom
        band = 900 if (agg <= 0.05 and fa <= 0.05) else (800 if agg <= 0.15 else 700)
        curve.append({"K": K, "frr": agg, "far": fa, "band": band, "npos": den})
        print(f"  {K:>2}  {agg*100:6.1f}%  {fa*100:5.1f}%   {band}   "
              + " ".join(f"{p*100:.0f}" for p in per), flush=True)
    crossed = next((c["K"] for c in curve if c["frr"] <= 0.05 and c["far"] <= 0.05), None)
    monotone = all(curve[i]["frr"] >= curve[i + 1]["frr"] - 0.02 for i in range(len(curve) - 1))
    print(f"\n  band-900 crossed at K={crossed} (monotone={monotone})" if crossed
          else f"\n  band-900 NOT reached (best {min(c['frr'] for c in curve)*100:.1f}%), monotone={monotone}", flush=True)
    with open(os.path.join(L.CACHE, "t3_typical_d2_k67.json"), "w") as f:
        json.dump({"curve": curve, "layer": BEST_L, "n_spk": len(man),
                   "band900_K": crossed, "monotone": bool(monotone)}, f, indent=2)


if __name__ == "__main__":
    main()
