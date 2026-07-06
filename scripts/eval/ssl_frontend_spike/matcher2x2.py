"""Decompose the win: representation {MFCC, WavLM-L12} x matcher {DTW, statspool-cosine}.

Isolates whether the WavLM win is the representation or the matcher (advisor point #1).
statspool = L2norm([mean(frames); std(frames)]) -> 1-frame vector; euclidean-DTW on unit vecs ranks == cosine 1-NN.
One WavLM forward pass, cached; MFCC frames cheap. WavLM-DTW cell is slow (768-dim) -> optional via DTW_SSL=1.
"""
import os, sys, time
import numpy as np
import torch
import harness as H

SPKS = (sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"])
DTW_SSL = os.environ.get("DTW_SSL", "0") == "1"
LAYER = int(os.environ.get("LAYER", "12"))
MODEL = os.environ.get("MODEL", "microsoft/wavlm-base-plus")
MIN_SPEECH = 1520


def statspool(frames):
    if frames.shape[0] == 0:
        return np.zeros((0, 1), dtype=np.float32)
    v = np.concatenate([frames.mean(0), frames.std(0)])
    v = v / (np.linalg.norm(v) + 1e-8)
    return v[None, :].astype(np.float32)


corpus = {k: v for k, v in H.scan().items() if k in SPKS}
all_wavs = sorted({w for d in corpus.values() for lst in d["commands"].values() for w in lst}
                  | {w for d in corpus.values() for w in d["negatives"]})
print(f"{len(all_wavs)} wavs; speakers={list(corpus)}", flush=True)

from transformers import AutoModel
net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)

mfcc = H.MfccFrontEnd()
t0 = time.time()
mfcc_frames, wavlm_frames = {}, {}
for i, wav in enumerate(all_wavs):
    sp = H.energy_vad_trim(H.read_wav(wav))
    if sp.size < MIN_SPEECH:
        mfcc_frames[wav] = np.zeros((0, 39), dtype=np.float32)
        wavlm_frames[wav] = np.zeros((0, 768), dtype=np.float32)
        continue
    mfcc_frames[wav] = mfcc(sp)
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0]
    wavlm_frames[wav] = hs.numpy().astype(np.float32)
    if (i + 1) % 150 == 0:
        print(f"  {i+1}/{len(all_wavs)} ({time.time()-t0:.0f}s)", flush=True)
print(f"features cached {time.time()-t0:.0f}s", flush=True)


def run_cell(name, frame_map, transform):
    fc = {w: transform(f) for w, f in frame_map.items()}
    rows_all = []
    per = {}
    for spk, d in corpus.items():
        rows = H.eval_speaker(d, None, fc)
        per[spk] = H.rank1(rows)[0]
        rows_all.extend(rows)
    agg = H.rank1(rows_all)[0]
    sep = H.separability(rows_all)
    print(f"{name:>28}  " + " ".join(f"{spk}={per[spk]*100:.1f}%" for spk in corpus) +
          f"  AGG={agg*100:.1f}%  AUC={sep['auc']:.3f}", flush=True)
    return agg


print("\n=== 2x2 decomposition (rank-1) ===", flush=True)
run_cell("MFCC + statspool-cosine", mfcc_frames, statspool)
run_cell("WavLM-L12 + statspool-cosine", wavlm_frames, statspool)
if DTW_SSL:
    # frames_norm for DTW (per-frame L2)
    def fnorm(f):
        if f.shape[0] == 0:
            return f
        return (f / (np.linalg.norm(f, axis=1, keepdims=True) + 1e-8)).astype(np.float32)
    run_cell("WavLM-L12 + DTW(frames_norm)", wavlm_frames, fnorm)
    run_cell("MFCC + DTW", mfcc_frames, lambda f: f)
print("\n(MFCC+DTW reference from results_mfcc.json = 55.4% AGG)", flush=True)
