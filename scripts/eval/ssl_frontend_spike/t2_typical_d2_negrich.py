"""T2 — Typical D2 800->900: recover the FAR headroom with a deployment-realistic negative set.

T1 found K5/L12 = 5.8% FRR @ realized FAR 3.8% (band-900 missed by 0.8pp). The realized FAR is
1.2pp UNDER the 5% budget because the held-out global threshold is fit on only ~25 negatives/fold
(8 OOV words x 4 reps). In deployment the accept threshold is calibrated on a LARGE negative corpus
(ambient + OOV), so the conservative small-sample threshold is a protocol artifact, not the true
operating point. T2 expands the per-speaker negative-calibration pool to ALL of the speaker's
remaining OOV words (>=4 reps each), re-embeds the new negative clips, and re-measures.

This is a PROTOCOL FIX (bigger, more realistic negative set for the SAME held-out threshold rule),
NOT a lever mined from test outcomes -> no selection-on-test.

PRE-REGISTERED (H_D2b): with the enriched negative calibration set, typical D2 at K5/L12 reaches
band 900 (<=5% FRR) at realized held-out FAR <= 5%, monotone across the 19 GSC speakers.
  SUCCESS: agg FRR <= 5.0% AND realized FAR <= 5.0% at K5. Else report FRR/FAR/AUC + residual gap.
Adjudicated on FRR@matched-FAR (EVAL-007). NOT-BANKED pending a fresh confirm; GSC n~19 robust corpus.
"""
import os, json, collections
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a5_gsc_kcurve import GSC, LAYER, REPS, FIXED_WORDS, N_SPK, pick_speakers, embed_net

BEST_L = 12
NEG_REPS = 6            # up to 6 reps per OOV negative word (was 4)
ALLLAYERS = os.path.join(L.CACHE, "gsc_wavlm_large_alllayers.npz")


def build_negrich():
    picks = pick_speakers()
    manifest = {}
    need = []
    for spk, ge5, wc in picks:
        fixed = {w: wc[w][:REPS] for w in ge5[:FIXED_WORDS]}
        # ENRICHED negatives: every remaining word the speaker has with >=4 reps, up to NEG_REPS each
        neg = []
        for w in ge5[FIXED_WORDS:]:                      # all remaining >=REPS-rep words
            neg += wc[w][:NEG_REPS]
        for w, fs in wc.items():                          # plus any 4-5 rep OOV words not already used
            if w not in ge5[:FIXED_WORDS] and w not in ge5[FIXED_WORDS:] and len(fs) >= 4:
                neg += fs[:NEG_REPS]
        manifest[spk] = {"fixed": fixed, "neg": neg}
        for ps in fixed.values():
            need += ps
        need += neg
    z = np.load(ALLLAYERS, allow_pickle=True) if os.path.exists(ALLLAYERS) else None
    emb = {k: z[k] for k in z.files} if z is not None else {}
    todo = [p for p in need if p not in emb]
    if todo:
        from transformers import AutoModel
        net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
        print(f"  embedding {len(todo)} new (mostly negative) GSC clips...", flush=True)
        for i, p in enumerate(todo):
            emb[p] = embed_net(net, p)
            if (i + 1) % 100 == 0:
                print(f"    {i+1}/{len(todo)}", flush=True)
        np.savez(ALLLAYERS, **emb)
    return manifest, emb


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
    print("T2 TYPICAL D2 800->900 — enriched negative calibration set, L%d\n" % BEST_L, flush=True)
    man, emb = build_negrich()
    nneg = np.mean([len(man[s]["neg"]) for s in man])
    print(f"  {len(man)} speakers | mean negatives/speaker = {nneg:.0f} (was 32)\n", flush=True)
    print(f"  {'K':>2}  {'FRR':>7}  {'FAR':>6}   band   per-speaker FRR", flush=True)
    curve = []
    for K in [1, 2, 3, 4, 5]:
        num = den = fanum = fdenom = 0
        per = []
        for spk in man:
            frr, far, npos, nn = kcurve(man[spk], emb, K, BEST_L)
            num += frr * npos; den += npos
            fanum += far * nn; fdenom += nn
            per.append(frr)
        agg = num / den; fa = fanum / fdenom
        band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
        curve.append({"K": K, "frr": agg, "far": fa, "band": band, "npos": den, "nneg": fdenom})
        print(f"  {K:>2}  {agg*100:6.1f}%  {fa*100:5.1f}%   {band}   "
              + " ".join(f"{p*100:.0f}" for p in per), flush=True)
    k5 = curve[-1]
    ok = k5["frr"] <= 0.05 and k5["far"] <= 0.05
    print(f"\n  K5: FRR={k5['frr']*100:.1f}% @FAR {k5['far']*100:.1f}%  =>  "
          f"{'BAND 900 (H_D2b SUCCESS, NOT-banked pending confirm)' if ok else 'still band 800 (residual %.1fpp)' % (max(0,k5['frr']-0.05)*100)}", flush=True)
    with open(os.path.join(L.CACHE, "t2_typical_d2_negrich.json"), "w") as f:
        json.dump({"curve": curve, "layer": BEST_L, "n_spk": len(man), "mean_neg": float(nneg)}, f, indent=2)


if __name__ == "__main__":
    main()
