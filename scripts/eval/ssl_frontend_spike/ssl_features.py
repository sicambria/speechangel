"""Frozen self-supervised speech encoder front-end for the CP-1 ceiling spike.

Returns a per-utterance feature matrix (T', D) that drops into the SAME DTW+fold+scoring harness as
MFCC. Input audio is already VAD-trimmed by the caller (both arms trim identically).

pool modes:
  frames      -> raw hidden states (T', H), euclidean-DTW over the sequence
  frames_norm -> per-frame L2-normalised (T', H), so euclidean-DTW ~ cosine-DTW
  mean        -> mean-pool + L2-normalise, returned as (1, H); euclidean on unit vectors ranks == cosine 1-NN

A ceiling/diagnostic probe: these encoders are English-pretrained and ~95M params, NOT a shippable
artifact (see the spike plan). A win localizes the bottleneck to the front-end; it is not "ship WavLM".
"""
import numpy as np
import torch

_MODELS = {
    "wav2vec2": "facebook/wav2vec2-base",
    "wav2vec2xlsr": "facebook/wav2vec2-large-xlsr-53",
    "wavlm": "microsoft/wavlm-base-plus",
    "hubert": "facebook/hubert-base-ls960",
    "distilhubert": "ntu-spml/distilhubert",  # ~23M, 2 transformer layers — small-encoder retention probe
}


class SslFrontEnd:
    def __init__(self, model="wav2vec2", layer=8, pool="mean", device="cpu"):
        from transformers import AutoModel
        self.model_id = _MODELS.get(model, model)
        self.layer = layer
        self.pool = pool
        self.device = device
        self.name = f"ssl:{model}:L{layer}:{pool}"
        self.model = AutoModel.from_pretrained(self.model_id, output_hidden_states=True).to(device).eval()
        torch.set_grad_enabled(False)

    def __call__(self, x):
        # x: float32 waveform 16kHz, already VAD-trimmed
        if x.size < 400:  # < 25ms → too short (matches min-frames intent)
            return np.zeros((0, 1), dtype=np.float32)
        # per-utterance zero-mean unit-var normalisation (what the wav2vec2 processor does)
        w = (x - x.mean()) / (x.std() + 1e-7)
        t = torch.from_numpy(w.astype(np.float32)).unsqueeze(0).to(self.device)
        out = self.model(t)
        hs = out.hidden_states[self.layer][0]  # (T', H)
        hs = hs.cpu().numpy().astype(np.float32)
        if hs.shape[0] == 0:
            return np.zeros((0, hs.shape[1] if hs.ndim == 2 else 1), dtype=np.float32)
        if self.pool == "mean":
            v = hs.mean(axis=0)
            v = v / (np.linalg.norm(v) + 1e-8)
            return v[None, :].astype(np.float32)
        if self.pool == "frames_norm":
            n = np.linalg.norm(hs, axis=1, keepdims=True) + 1e-8
            return (hs / n).astype(np.float32)
        return hs  # frames (raw)
