"""SSL layer + pooling sweep on one speaker set: ONE forward pass per utterance, cache all hidden
layers, then evaluate rank-1 for every (layer, pool) so the expensive forward pass is amortized.

Usage: python sweep_ssl.py <model> <speakers-csv> [pools] [layers]
  e.g. sweep_ssl.py wav2vec2 F01 mean,frames_norm 0,4,6,8,10,12
"""
import sys, time
import numpy as np
import torch
import harness as H

model = sys.argv[1] if len(sys.argv) > 1 else "wav2vec2"
spk_filter = sys.argv[2].split(",") if len(sys.argv) > 2 else ["F01"]
pools = sys.argv[3].split(",") if len(sys.argv) > 3 else ["mean", "frames_norm"]
layers = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else None

from transformers import AutoModel
MODELS = {"wav2vec2": "facebook/wav2vec2-base", "wavlm": "microsoft/wavlm-base-plus",
          "hubert": "facebook/hubert-base-ls960", "xlsr": "facebook/wav2vec2-large-xlsr-53",
          "wavlmlarge": "microsoft/wavlm-large", "xlsr128": "facebook/mms-1b-all"}
mid = MODELS.get(model, model)
print(f"loading {mid} ...", flush=True)
net = AutoModel.from_pretrained(mid, output_hidden_states=True).eval()
torch.set_grad_enabled(False)

corpus = H.scan()
corpus = {k: v for k, v in corpus.items() if k in spk_filter}
all_wavs = set()
for spk, d in corpus.items():
    for w, wavs in d["commands"].items():
        all_wavs.update(wavs)
    all_wavs.update(d["negatives"])
all_wavs = sorted(all_wavs)
MIN_SPEECH = 1520

print(f"forward pass on {len(all_wavs)} wavs (model={model}) ...", flush=True)
t0 = time.time()
# hidden[wav] = list over layers of (T, H) float16 ; None if too short
hidden = {}
n_layers = None
for i, wav in enumerate(all_wavs):
    sp = H.energy_vad_trim(H.read_wav(wav))
    if sp.size < MIN_SPEECH:
        hidden[wav] = None
        continue
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    t = torch.from_numpy(w.astype(np.float32)).unsqueeze(0)
    hs = net(t).hidden_states  # tuple(n_layers+1) of (1,T,H)
    n_layers = len(hs)
    hidden[wav] = [h[0].numpy().astype(np.float16) for h in hs]
    if (i + 1) % 150 == 0:
        print(f"  {i+1}/{len(all_wavs)} ({time.time()-t0:.0f}s)", flush=True)
print(f"forward done {time.time()-t0:.0f}s; layers={n_layers}", flush=True)
if layers is None:
    layers = list(range(n_layers))


def build_cache(layer, pool):
    fc = {}
    for wav, hs in hidden.items():
        if hs is None:
            fc[wav] = np.zeros((0, 1), dtype=np.float32)
            continue
        h = hs[layer].astype(np.float32)
        if pool == "mean":
            v = h.mean(axis=0)
            v = v / (np.linalg.norm(v) + 1e-8)
            fc[wav] = v[None, :]
        elif pool == "frames_norm":
            n = np.linalg.norm(h, axis=1, keepdims=True) + 1e-8
            fc[wav] = h / n
        else:
            fc[wav] = h
    return fc


print(f"\n{'layer':>5} {'pool':>12} " + " ".join(f"{s:>7}" for s in spk_filter) + f" {'AGG':>7} {'AUC':>6}", flush=True)
results = []
for pool in pools:
    for layer in layers:
        fc = build_cache(layer, pool)
        all_rows = []
        per = {}
        for spk, d in corpus.items():
            rows = H.eval_speaker(d, None, fc)
            r1, _, _ = H.rank1(rows)
            per[spk] = r1
            all_rows.extend(rows)
        agg, _, _ = H.rank1(all_rows)
        sep = H.separability(all_rows)
        auc = sep["auc"] if sep else float("nan")
        results.append((layer, pool, agg, auc))
        row = " ".join(f"{per[s]*100:6.1f}%" for s in spk_filter)
        print(f"{layer:>5} {pool:>12} {row} {agg*100:6.1f}% {auc:6.3f}", flush=True)

best = max(results, key=lambda r: r[2])
print(f"\nBEST: layer={best[0]} pool={best[1]} agg-rank1={best[2]*100:.1f}% AUC={best[3]:.3f}", flush=True)
