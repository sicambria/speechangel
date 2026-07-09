"""Leave-one-dysarthric-speaker-out probe + separability root-cause — is the D2 wall DATA or INTRINSIC?

Two measurements, both reuse cached wavlm embeddings (frozen mean-pool per layer):

(1) SEPARABILITY (root cause): genuine (same-word) vs impostor (diff-word) frozen-embedding cosine
    distance distributions, dysarthric vs control. d-prime / ROC-AUC quantifies the overlap that
    dominates D2 FRR. If dysarthric AUC << control AUC, the wall is intrinsic to the disorder's
    within-word variability, not a front-end deficiency.

(2) LOSO learned embedding: for each held-out dysarthric speaker, train the contrastive projection on
    control + the OTHER 2 dysarthric speakers (dev-time, ships frozen, speaker-independent w.r.t. the
    test user -> admissible), evaluate on the held-out dysarthric speaker. Answers: does dysarthric
    TRAINING DATA close D2?  clears 15% -> DATA wall (fundable: collect more dysarthric speakers).
    still short -> intrinsic wall even with in-domain training.

Pre-registered H4 (ONE hypothesis): LOSO-dysarthric-trained learned embedding reaches held-out
dysarthric FRR <= 0.15 @ FAR <= 5%. Honest expectation: improves over control-only but stays short
(3 speakers is tiny); the LOSO delta vs control-only sizes the value of dysarthric data.
"""
import os, sys, json, math
import numpy as np
import torch
import harness as H
from metric_probe import Proj, supcon_loss, train_proj, eval_dys, load_speaker, CACHE, DYS, CTL

torch.manual_seed(0)
np.random.seed(0)


def build_train_speakers(emb, layer, speakers):
    X, y, wid = [], [], {}
    for spk in speakers:
        d = load_speaker(spk)
        if not d:
            continue
        for word, wavs in d["commands"].items():
            if word not in wid:
                wid[word] = len(wid)
            for w in wavs:
                if w in emb:
                    X.append(emb[w][layer])
                    y.append(wid[word])
    return np.stack(X).astype(np.float32), np.array(y), len(wid)


def separability(emb, layer, speakers):
    """genuine vs impostor cosine-distance AUC + d-prime over the given speakers (frozen)."""
    gen, imp = [], []
    for spk in speakers:
        d = load_speaker(spk)
        if not d:
            continue
        # per word: within-word pairs = genuine; cross-word nearest = impostor
        words = {w: [emb[x][layer] for x in wavs if x in emb] for w, wavs in d["commands"].items()}
        words = {w: v for w, v in words.items() if len(v) >= 2}
        allw = list(words)
        for w, vs in words.items():
            for i in range(len(vs)):
                # genuine: nearest OTHER same-word template
                gd = min(1 - float(vs[i] @ vs[j]) for j in range(len(vs)) if j != i)
                gen.append(gd)
                # impostor: nearest template of any OTHER word
                best = math.inf
                for w2 in allw:
                    if w2 == w:
                        continue
                    for v2 in words[w2]:
                        dd = 1 - float(vs[i] @ v2)
                        if dd < best:
                            best = dd
                if math.isfinite(best):
                    imp.append(best)
    g, im = np.array(gen), np.array(imp)
    dprime = (im.mean() - g.mean()) / math.sqrt(0.5 * (g.var() + im.var()) + 1e-12)
    auc = float(np.mean(g[:, None] < im[None, :]))
    return dict(dprime=float(dprime), auc=auc, gen_med=float(np.median(g)),
                imp_med=float(np.median(im)), n_gen=len(g), n_imp=len(im))


def eval_one(proj_emb, spk):
    d = load_speaker(spk)
    wavs = set()
    for lst in d["commands"].values():
        wavs.update(lst)
    wavs.update(d["negatives"])
    fc = {w: proj_emb[w][None, :] for w in wavs}
    rows = H.eval_speaker(d, None, fc)
    r1, hits, n = H.rank1(rows)
    frr, far, npos, nn = H.held_out_global(rows)
    return r1, frr, far, hits, n, round(far * nn), nn


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-base-plus"
    layer = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    din = next(iter(emb.values())).shape[1]

    print(f"=== SEPARABILITY (frozen {model} L{layer}) ===", flush=True)
    for grp, spks in [("dysarthric", DYS), ("control", CTL)]:
        s = separability(emb, layer, spks)
        print(f"  {grp:11s}: AUC={s['auc']:.3f}  d'={s['dprime']:.2f}  "
              f"gen_med={s['gen_med']:.3f} imp_med={s['imp_med']:.3f}  (n_gen={s['n_gen']})", flush=True)

    print(f"\n=== LOSO learned embedding ({model} L{layer}) ===", flush=True)
    hits = pos = fa = neg = 0
    frr_num = 0.0  # pooled held-out FRR@FAR numerator (frr*npos) — NOT 1-rank1
    per = {}
    for test_spk in DYS:
        train_spks = CTL + [s for s in DYS if s != test_spk]
        X, y, nc = build_train_speakers(emb, layer, train_spks)
        g = train_proj(X, y, din, dout=128, epochs=300)
        with torch.no_grad():
            proj = {w: g(torch.from_numpy(emb[w][layer:layer+1].astype(np.float32)))[0].numpy()
                    for w in emb}
        r1, frr, far, h, n, faN, nn = eval_one(proj, test_spk)
        per[test_spk] = (r1, frr, far)
        hits += h; pos += n; fa += faN; neg += nn
        frr_num += frr * n
        print(f"  test {test_spk}: rank1={r1*100:.1f}%  FRR={frr*100:.1f}% @FAR{far*100:.1f}%", flush=True)
    agg_r1 = hits / pos if pos else 0
    agg_frr = frr_num / pos if pos else 0  # true pooled FRR@FAR<=5%
    agg_far = fa / neg if neg else 0
    print(f"\nLOSO dys AGG: rank1={agg_r1*100:.1f}%  FRR~{agg_frr*100:.1f}% @FAR~{agg_far*100:.1f}%", flush=True)
    print(f"H4 D2 (LOSO dys FRR<=15%): {'PASS' if agg_frr<=0.15 else 'FAIL'}", flush=True)
    print(f"H4 D1 (LOSO dys rank1>=75%): {'PASS' if agg_r1>=0.75 else 'FAIL'}", flush=True)
    with open(os.path.join(CACHE, f"loso_{model}_L{layer}.json"), "w") as f:
        json.dump(dict(agg_r1=agg_r1, agg_frr=agg_frr, agg_far=agg_far,
                       per_spk={s: [round(x,3) for x in per[s]] for s in per}), f, indent=2)


if __name__ == "__main__":
    main()
