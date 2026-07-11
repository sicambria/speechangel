"""T12 — Enrollment augmentation: does speed-perturbed template diversity close the below-threshold tail?

The t8 diagnostic found 59% of typical hard-speaker false-rejects are BELOW-THRESHOLD (genuine word
ranked #1 but its min-distance to the enrolled templates exceeds the accept threshold) — intrinsic
within-word scatter, NOT vocab confusion. The standard fix for exactly that failure mode is more
template diversity: augment each enrolled template with speed-perturbed copies so a genuine query has a
closer template to match (lower min-distance). It is the natural extension of the one robustly-banked
lever (few-shot enrollment), fully admissible (deterministic, on-device: generate perturbations at
enroll time), and — with the alt-encoder/verifier/vocab axes closed — the last untested representation
lever on the wavlm-large TEACHER (the shipping encoder, baseline 5.81%).

Design: for each enrolled template, add speed-perturbed copies (factors 0.9, 1.1 = ±10% Kaldi-style),
encoded with wavlm-large L12; queries stay ORIGINAL. Enroll pool per word = K reps × (orig + 2 aug).
Held-out FRR@FAR<=5% (LOFO), FAR-matched (impostors score against the same expanded pool, so the
threshold is re-fit). Pre-registered kill (EVAL-005/007): moves aggregate <=5% AND >=2 of the 3 hard
speakers (98ea0818/2aca1e72/c1d39ce8) improve in direction at matched FAR. Baseline = 5.81% (t6 L12/K5).
Reuses a5 manifest + cand_lib threshold primitives verbatim (EVAL-004).
"""
import os, sys, json
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a5_gsc_kcurve import build_cache

DEPLOY_L = 12
K = 5
FAR = 0.05
FACTORS = [0.9, 1.1]
HARD = ["98ea0818", "2aca1e72", "c1d39ce8"]
AUG_CACHE = os.path.join(L.CACHE, "gsc_wavlm_large_aug_L12.npz")


def speed_perturb(x, factor):
    n = max(1520, int(round(len(x) / factor)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def embed_L12(net, wav):
    sp = H.energy_vad_trim(wav)
    if sp.size < 1520:
        sp = wav if wav.size >= 1520 else np.pad(wav, (0, 1520 - wav.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
    v = hs[DEPLOY_L][0].numpy().mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def build_aug_cache(man):
    enroll_paths = sorted({p for s in man for ps in man[s]["fixed"].values() for p in ps})
    if os.path.exists(AUG_CACHE):
        z = np.load(AUG_CACHE, allow_pickle=True)
        aug = {k: z[k] for k in z.files}
        if all(f"{p}|{fac}" in aug for p in enroll_paths for fac in FACTORS):
            return aug
    from transformers import AutoModel
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    aug = {}
    print(f"  encoding {len(enroll_paths)*len(FACTORS)} perturbed enroll templates (wavlm-large L{DEPLOY_L})...", flush=True)
    for i, p in enumerate(enroll_paths):
        x, sr = sf.read(p, dtype="float32")
        if x.ndim > 1:
            x = x.mean(1)
        for fac in FACTORS:
            aug[f"{p}|{fac}"] = embed_L12(net, speed_perturb(x, fac))
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(enroll_paths)}", flush=True)
    np.savez(AUG_CACHE, **aug)
    return aug


def kcurve_aug(man_s, emb, aug):
    """a5.kcurve_speaker with the enroll pool EXPANDED by each template's speed-perturbed copies."""
    fixed = man_s["fixed"]
    words = {w: [emb[p][DEPLOY_L] for p in ps] for w, ps in fixed.items()}
    words_aug = {w: [[aug[f"{p}|{fac}"] for fac in FACTORS] for p in ps] for w, ps in fixed.items()}
    negs = [emb[p][DEPLOY_L] for p in man_s["neg"]]

    def enroll_for(f, skip_w=None, skip_i=None):
        en = {}
        for ww, vv in words.items():
            idxs = [j for j in range(len(vv)) if (j % 5) != f and not (ww == skip_w and j == skip_i)]
            pool = []
            for j in idxs[:K]:
                pool.append(vv[j]); pool.extend(words_aug[ww][j])
            if pool:
                en[ww] = pool
        return en

    pos_rows, fp, neg_rows, fn = [], [], [], []
    for w, vecs in words.items():
        for i, qv in enumerate(vecs):
            f = i % 5
            en = enroll_for(f, w, i)
            if en:
                pos_rows.append((w, L.score_query(qv, en, "min"))); fp.append(f)
    for ni, nv in enumerate(negs):
        f = ni % 5
        en = enroll_for(f)
        if en:
            neg_rows.append((None, L.score_query(nv, en, "min"))); fn.append(f)
    return L.held_out_frr_far(pos_rows, neg_rows, fp, fn, L.global_threshold_accept, target=FAR)


def main():
    print("T12 ENROLLMENT AUGMENTATION (speed +/-10%%) — wavlm-large L%d, baseline 5.81%%\n" % DEPLOY_L, flush=True)
    man, emb = build_cache()
    aug = build_aug_cache(man)
    # baseline (no aug) per-speaker for the side-by-side
    from a5_gsc_kcurve import kcurve_speaker
    base = {s: kcurve_speaker(man[s], emb, K, layer=DEPLOY_L)[0] for s in man}

    num = den = fnum = fden = 0
    per = {}
    for s in man:
        frr, far, npos, nneg = kcurve_aug(man[s], emb, aug)
        per[s] = (frr, base[s])
        num += frr * npos; den += npos; fnum += far * nneg; fden += nneg
    agg, fa = num / den, fnum / fden
    band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
    moved = [h for h in HARD for s in man if s.startswith(h[:8]) and per[s][0] < per[s][1] - 1e-6]
    print(f"  aggregate FRR {agg*100:.2f}% @FAR {fa*100:.1f}%  band {band}  (baseline 5.81%)\n", flush=True)
    print(f"  hard-speaker side-by-side (aug vs baseline):", flush=True)
    for h in HARD:
        s = next((s for s in man if s.startswith(h[:8])), None)
        a, b = per[s]
        print(f"    {h[:8]}  aug {a*100:>4.0f}%  vs base {b*100:>4.0f}%  {'BETTER' if a < b-1e-6 else 'same/worse'}", flush=True)
    verdict = ("MOVES the tail (>=2 hard + agg<=5%) — candidate lever, needs fresh pre-registered confirm"
               if len(moved) >= 2 and agg <= 0.05 else
               f"does NOT reach band 900 (agg {agg*100:.1f}%, {len(moved)}/3 hard improved) — augmentation on the "
               "mean-pooled embedding does not close the below-threshold tail")
    print(f"\n  hard improved: {len(moved)}/3\n  VERDICT: {verdict}", flush=True)
    with open(os.path.join(L.CACHE, "t12_aug_enroll.json"), "w") as f:
        json.dump({"agg_frr": agg, "agg_far": fa, "band": band, "baseline": 0.0581,
                   "hard_moved": len(moved), "factors": FACTORS,
                   "per_speaker": {s: {"aug": per[s][0], "base": per[s][1]} for s in man},
                   "verdict": verdict}, f, indent=2)
    print("\n  wrote t12_aug_enroll.json", flush=True)


if __name__ == "__main__":
    main()
