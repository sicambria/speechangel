"""Extract frame-level (frames_norm, T x 1024) wavlm-large L14 features for TORGO MALE dysarthric
speakers M01..M05 into _ceiling_cache/male_frames_L14.npz.

The female frames are already cached (large_frames_L14.npz); males were only pooled (male_wavlm_large.npz).
P3 (frame-trajectory DTW) needs male frames to test the MODERATE population (M01/M02) — the only severity
cell where the D2 verdict is still live. Mirrors frame_dtw_sep.extract_frames exactly (same VAD, same
per-frame L2 norm, same max_frames cap) so male and female frame features are drawn identically.
"""
import os, sys
import numpy as np
import torch
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
MALE = ["M01", "M02", "M03", "M04", "M05"]
TORGO = os.path.expanduser("~/torgo")
MODEL = "microsoft/wavlm-large"
LAYER = int(sys.argv[1]) if len(sys.argv) > 1 else 14
MAX_FRAMES = 200


def main():
    data = H.scan(TORGO)
    wavs = []
    for spk in MALE:
        d = data.get(spk)
        if not d:
            print(f"  [warn] no data for {spk}", flush=True)
            continue
        for w, lst in d["commands"].items():
            wavs.extend(lst)
        wavs.extend(d["negatives"])  # need negatives too for the D2 impostor set
    wavs = sorted(set(wavs))
    cache = os.path.join(CACHE, f"male_frames_L{LAYER}.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        if all(w in z.files for w in wavs):
            print(f"[cache] {len(wavs)} male frame seqs L{LAYER} already present", flush=True)
            return
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    print(f"loading {MODEL} for male frame extraction ({len(wavs)} wavs, L{LAYER})...", flush=True)
    net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
    out = {}
    for i, wav in enumerate(wavs):
        x = H.read_wav(wav)
        sp = H.energy_vad_trim(x)
        if sp.size < 400:
            sp = x if x.size >= 400 else np.zeros(400, dtype=np.float32)
        wv = (sp - sp.mean()) / (sp.std() + 1e-7)
        hs = net(torch.from_numpy(wv.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
        n = np.linalg.norm(hs, axis=1, keepdims=True) + 1e-8
        f = (hs / n).astype(np.float32)
        if f.shape[0] > MAX_FRAMES:
            idx = np.linspace(0, f.shape[0] - 1, MAX_FRAMES).astype(int)
            f = f[idx]
        out[wav] = f
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(wavs)}", flush=True)
    np.savez(cache, **out)
    print(f"extracted {len(out)} male frame seqs -> {cache}", flush=True)


if __name__ == "__main__":
    main()
