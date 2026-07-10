"""C21b — cross-corpus confirmation of the base+ L10 deployment layer (advisor catch).

C21/A3b's "band-800-at-94 MB" headline uses wavlm-base+ **L10** (12.0% typical D2) — but that is a single
layer pick on n=3 TORGO-control speakers, and L12 = 17.2% (band 700) on the same 3 speakers. This is the
SAME methodology as the C15/L21 finding we REFUTED on GSC-24. So confirm base+ L10 on GSC-24 the same way:
re-embed the A5 GSC-24 manifest with wavlm-base-plus (all 13 layers) and sweep K=4 held-out FRR@FAR≤5%.

  - if L10 keeps its edge over L12 on GSC-24 -> C21/A3b band-800-at-94MB confirmed.
  - if flat/reversed -> base+ is band-700; on-device band-800 falls back to wavlm-large 316 MB (still
    CONSTRAINT-001-admissible). Downgrade the ⭐.
"""
import os, json
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
import a5_gsc_kcurve as A5

CACHE = os.path.join(L.CACHE, "gsc_basePlus_alllayers.npz")
MODEL = "microsoft/wavlm-base-plus"
SR = 16000; FAR = 0.05


def embed_net(net, path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
    return np.stack([(h[0].numpy().mean(0) / (np.linalg.norm(h[0].numpy().mean(0)) + 1e-8)).astype(np.float32) for h in hs])


def main():
    man, _ = A5.build_cache()  # reuse the SAME 24-speaker GSC manifest (large cache already built)
    need = []
    for s in man:
        for ps in man[s]["fixed"].values():
            need += ps
        need += man[s]["neg"]
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); emb = {k: z[k] for k in z.files}
    else:
        emb = {}
    todo = [p for p in need if p not in emb]
    if todo:
        from transformers import AutoModel
        net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
        print(f"C21b — embedding {len(todo)} GSC clips with wavlm-base-plus (all layers)...", flush=True)
        for i, p in enumerate(todo):
            emb[p] = embed_net(net, p)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(todo)}", flush=True)
        np.savez(CACHE, **emb)

    print(f"\nC21b — base+ layer sweep on GSC-24 (K=4 held-out FRR@FAR<=5%):", flush=True)
    layer_frr = {}
    for lyr in range(13):
        num = den = 0
        for spk in man:
            frr, far, npos, nneg = A5.kcurve_speaker(man[spk], emb, 4, layer=lyr)
            num += frr * npos; den += npos
        layer_frr[lyr] = num / den
        mark = "  <- deployment pick (L10)" if lyr == 10 else ("  (L12)" if lyr == 12 else "")
        print(f"  L{lyr:>2}: {layer_frr[lyr]*100:5.1f}%{mark}", flush=True)
    best = min(layer_frr, key=layer_frr.get)
    l10, l12 = layer_frr[10], layer_frr[12]
    print(f"\n  base+ best GSC layer = L{best} ({layer_frr[best]*100:.1f}%)", flush=True)
    print(f"  L10={l10*100:.1f}%  L12={l12*100:.1f}%  (TORGO-n3 had L10=12.0 << L12=17.2)", flush=True)
    verdict = "CONFIRMED (L10 keeps its edge cross-corpus)" if l10 <= l12 + 0.005 else "REFUTED (L10 edge was an n=3 artifact -> downgrade 94MB claim to band-700; on-device band-800 = wavlm-large 316MB)"
    print(f"  VERDICT: {verdict}", flush=True)
    with open(os.path.join(L.CACHE, "c21b_base_layers.json"), "w") as f:
        json.dump({"gsc_layer_frr_k4": layer_frr, "l10": l10, "l12": l12, "best": int(best)}, f, indent=2)


if __name__ == "__main__":
    main()
