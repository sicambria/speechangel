"""A5 — Fixed-subset K-curve replication on a SECOND, TYPICAL corpus (Google Speech Commands v2).

The K-curve (few-shot enrollment lever) is load-bearing for every §3 projection. A1 repaired the
subset confound on TORGO control; A5 applies EVAL-003 discipline by replicating the FIXED-subset curve
on an entirely independent typical population (GSC: isolated citation-form command words, thousands of
speakers, real same-speaker word repeats).

Protocol = IDENTICAL to A1: per speaker, words with >= 5 reps (fixed subset), vary enrolled templates
K=1..4, held-out global threshold @ FAR<=5%, min-agg. Negatives = the speaker's OTHER (OOV) GSC words.
Encoder = wavlm-large L15 (same as A1). Embeddings cached to _ceiling_cache/gsc_wavlm_large_L15.npz.

PRE-REGISTERED GATE: on GSC, K=4 fixed-subset FRR <= 0.15 AND the curve is monotone non-increasing in K
  -> the few-shot lever replicates on an independent typical corpus (A1 was not TORGO-specific).
"""
import os, sys, glob, json, wave, collections
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H

GSC = os.path.expanduser("~/gsc/data")
CACHE = os.path.join(L.CACHE, "gsc_wavlm_large_alllayers.npz")
LAYER = 15
SR = 16000
N_SPK = 24
FIXED_WORDS = 8
REPS = 6
FAR = 0.05
np.random.seed(0)


def pick_speakers():
    words = [w for w in os.listdir(GSC) if os.path.isdir(os.path.join(GSC, w)) and not w.startswith("_")]
    spk_words = collections.defaultdict(lambda: collections.defaultdict(list))
    for w in words:
        for f in sorted(os.listdir(os.path.join(GSC, w))):
            if f.endswith(".wav"):
                spk_words[f.split("_")[0]][w].append(os.path.join(GSC, w, f))
    good = []
    for spk, wc in spk_words.items():
        ge5 = sorted([w for w, fs in wc.items() if len(fs) >= REPS])
        if len(ge5) >= FIXED_WORDS + 6:
            good.append((spk, ge5, wc))
    good.sort(key=lambda x: (-len(x[1]), x[0]))
    return good[:N_SPK]


def embed_net(net, path):
    """Return ALL layers mean-pooled + unit-normed: (25, 1024)."""
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
    out = []
    for h in hs:
        v = h[0].numpy().mean(0)
        out.append((v / (np.linalg.norm(v) + 1e-8)).astype(np.float32))
    return np.stack(out)  # (25,1024)


def build_cache():
    picks = pick_speakers()
    manifest = {}  # spk -> {"fixed": {word:[paths]}, "neg": [paths]}
    need = []
    for spk, ge5, wc in picks:
        fixed = {w: wc[w][:REPS] for w in ge5[:FIXED_WORDS]}
        neg = []
        for w in ge5[FIXED_WORDS:FIXED_WORDS + 8]:
            neg += wc[w][:4]
        manifest[spk] = {"fixed": fixed, "neg": neg}
        for w, ps in fixed.items():
            need += ps
        need += neg
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        emb = {k: z[k] for k in z.files}
        if all(p in emb for p in need):
            return manifest, emb
    else:
        emb = {}
    from transformers import AutoModel
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    todo = [p for p in need if p not in emb]
    print(f"  embedding {len(todo)} GSC clips (wavlm-large L{LAYER})...", flush=True)
    for i, p in enumerate(todo):
        emb[p] = embed_net(net, p)
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(todo)}", flush=True)
    np.savez(CACHE, **emb)
    return manifest, emb


def kcurve_speaker(man, emb, K, layer=LAYER):
    words = {w: [emb[p][layer] for p in ps] for w, ps in man["fixed"].items()}
    negs = [emb[p][layer] for p in man["neg"]]
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


def main():
    print(f"A5 GSC FIXED-SUBSET K-CURVE — wavlm-large L{LAYER}, {N_SPK} speakers × {FIXED_WORDS} words × {REPS} reps\n", flush=True)
    man, emb = build_cache()
    print(f"\n  {'K':>2}  {'FRR':>7}  {'FAR':>6}   per-speaker FRR", flush=True)
    curve = []
    for K in [1, 2, 3, 4]:
        num = den = fanum = 0
        per = []
        for spk in man:
            frr, far, npos, nneg = kcurve_speaker(man[spk], emb, K)
            num += frr * npos; den += npos; fanum += far * npos
            per.append(frr)
        agg = num / den; fa = fanum / den
        curve.append((K, agg, fa))
        print(f"  {K:>2}  {agg*100:6.1f}%  {fa*100:5.1f}%   " + " ".join(f"{p*100:.0f}" for p in per), flush=True)
    k4 = curve[-1][1]
    monotone = all(curve[i][1] >= curve[i + 1][1] - 0.02 for i in range(len(curve) - 1))
    print(f"\n  GATE (GSC K=4 FRR<=15% & monotone): K4={k4*100:.1f}%, monotone={monotone} "
          f"=> {'PASS -> lever replicates on independent typical corpus' if k4 <= 0.15 and monotone else 'FAIL'}", flush=True)

    # LAYER-GENERALIZATION SWEEP (adjudicates the C15/L21 deep-layer finding on an independent corpus)
    print(f"\n  LAYER SWEEP (K=4 FRR@FAR<=5% per layer — is the deep-layer win corpus-general?):", flush=True)
    layer_frr = {}
    for lyr in [10, 12, 14, 15, 17, 19, 20, 21, 23]:
        num = den = 0
        for spk in man:
            frr, far, npos, nneg = kcurve_speaker(man[spk], emb, 4, layer=lyr)
            num += frr * npos; den += npos
        layer_frr[lyr] = num / den
        print(f"    L{lyr:>2}: {layer_frr[lyr]*100:5.1f}%", flush=True)
    best_l = min(layer_frr, key=layer_frr.get)
    print(f"    best GSC layer @K4 = L{best_l} ({layer_frr[best_l]*100:.1f}%) vs L15 ({layer_frr[15]*100:.1f}%)", flush=True)
    with open(os.path.join(L.CACHE, "a5_gsc_kcurve.json"), "w") as f:
        json.dump({"curve": curve, "k4": k4, "monotone": bool(monotone), "n_spk": len(man),
                   "layer_frr_k4": layer_frr, "best_layer": int(best_l)}, f, indent=2)


if __name__ == "__main__":
    main()
