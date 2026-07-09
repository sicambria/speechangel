"""SSL x frame-level DTW separability — closes the empty EVAL-004 2x2 cell before the D2 verdict.

Every prior D2 number used mean-pool cosine (timing-invariant, discards sequence). The terminal
"D2 walled" claim rests on the temporal matcher not helping. This probe fills the missing cell:
dysarthric genuine (same-word) vs impostor (diff-word) separability using **frame-level DTW** over
frozen wavlm-large frame features.

Decision rule (advisor-gated):
  - dysarthric AUC stays ~0.70 (== mean-pool)  => temporal matcher does not help; D2 wall airtight.
  - dysarthric AUC jumps to ~0.85+             => run the full D2 frame-DTW FRR and reassess.

Mean-pool baseline for reference: dysarthric AUC 0.704 (wavlm-large L14), 0.670 (base L10).

Extracts frames_norm (per-frame L2-normalised, T x H) for DYSARTHRIC wavs at one layer, then
harness.dtw_distance (length-normalised banded euclidean ~ cosine-DTW). Subsampled for tractability
(the DTW is the cost); scoped to dysarthric only. Deterministic seed.
"""
import os, sys, math, random
import numpy as np
import torch
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
DYS = ["F01", "F03", "F04"]
TORGO = os.path.expanduser("~/torgo")
random.seed(0)
np.random.seed(0)
MODEL = "microsoft/wavlm-large"


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


def extract_frames(layer, max_frames=200):
    """{wav: (T,H) frames_norm} for dysarthric commands only, cached per layer."""
    cache = os.path.join(CACHE, f"large_frames_L{layer}.npz")
    wavs = []
    for spk in DYS:
        d = load_speaker(spk)
        if not d:
            continue
        for w, lst in d["commands"].items():
            wavs.extend(lst)
    wavs = sorted(set(wavs))
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        if all(w in z.files for w in wavs):
            print(f"  [cache] {len(wavs)} frame seqs L{layer}", flush=True)
            return {w: z[w] for w in wavs}
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    print(f"  loading {MODEL} for frame extraction...", flush=True)
    net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
    out = {}
    for i, wav in enumerate(wavs):
        x = H.read_wav(wav)
        sp = H.energy_vad_trim(x)
        if sp.size < 400:
            sp = x if x.size >= 400 else np.zeros(400, dtype=np.float32)
        wv = (sp - sp.mean()) / (sp.std() + 1e-7)
        hs = net(torch.from_numpy(wv.astype(np.float32)).unsqueeze(0)).hidden_states[layer][0].numpy()
        n = np.linalg.norm(hs, axis=1, keepdims=True) + 1e-8
        f = (hs / n).astype(np.float32)
        if f.shape[0] > max_frames:  # downsample very long seqs uniformly to cap DTW cost
            idx = np.linspace(0, f.shape[0] - 1, max_frames).astype(int)
            f = f[idx]
        out[wav] = f
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(wavs)}", flush=True)
    np.savez(cache, **out)
    print(f"  extracted {len(out)} -> {cache}", flush=True)
    return out


def separability_dtw(frames, spk, n_query=60, n_imp=25):
    """genuine vs impostor via frame-DTW for one speaker (subsampled)."""
    d = load_speaker(spk)
    words = {w: [x for x in lst if x in frames] for w, lst in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    allw = list(words)
    # build query list: (wav, word) for words with >=2 reps
    queries = [(x, w) for w, v in words.items() for x in v]
    random.shuffle(queries)
    queries = queries[:n_query]
    gen, imp = [], []
    for qwav, qw in queries:
        qf = frames[qwav]
        # genuine: min DTW to other same-word templates
        g = min((H.dtw_distance(qf, frames[t]) for t in words[qw] if t != qwav), default=math.inf)
        if math.isfinite(g):
            gen.append(g)
        # impostor: min DTW to a sample of diff-word templates
        other = [t for w2 in allw if w2 != qw for t in words[w2]]
        random.shuffle(other)
        im = min((H.dtw_distance(qf, frames[t]) for t in other[:n_imp]), default=math.inf)
        if math.isfinite(im):
            imp.append(im)
    return np.array(gen), np.array(imp)


def main():
    layer = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    print(f"=== SSL x FRAME-DTW SEPARABILITY (frozen wavlm-large L{layer}, dysarthric) ===", flush=True)
    frames = extract_frames(layer)
    allg, alli = [], []
    for spk in DYS:
        g, im = separability_dtw(frames, spk)
        if g.size and im.size:
            auc = float(np.mean(g[:, None] < im[None, :]))
            dp = (im.mean() - g.mean()) / math.sqrt(0.5 * (g.var() + im.var()) + 1e-12)
            print(f"  {spk}: frameDTW AUC={auc:.3f} d'={dp:.2f}  gen_med={np.median(g):.4f} "
                  f"imp_med={np.median(im):.4f}  (n_gen={g.size})", flush=True)
            allg.append(g); alli.append(im)
    g = np.concatenate(allg); im = np.concatenate(alli)
    auc = float(np.mean(g[:, None] < im[None, :]))
    dp = (im.mean() - g.mean()) / math.sqrt(0.5 * (g.var() + im.var()) + 1e-12)
    print(f"\nDYSARTHRIC frame-DTW: AUC={auc:.3f}  d'={dp:.2f}  (mean-pool ref AUC=0.704)", flush=True)
    if auc >= 0.82:
        print("=> AUC jumped: run full D2 frame-DTW and reassess.", flush=True)
    else:
        print("=> AUC ~ mean-pool: temporal matcher does NOT lift separability; D2 wall stands.", flush=True)


if __name__ == "__main__":
    main()
