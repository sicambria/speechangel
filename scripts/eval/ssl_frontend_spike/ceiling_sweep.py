"""CP-1 SSL ceiling sweep — the decisive upper-bound test for the SOTA 800-push.

Pre-registered H1 (EVAL-003, ONE hypothesis): the BEST frozen-SSL front-end config
(model x layer x pool, admissible-agnostic — English-pretrained, off-device, any size)
reaches >= 0.75 AGGREGATE rank-1 on TORGO (dysarthric F01/F03/F04 + control FC01/FC02/FC03).
This is the NECESSARY condition for the shipped D1 domain to reach the 800 band (0.75 rung).

Logic: max-over-configs is a legitimate UPPER BOUND on the admissible frontier. A deployable
<=2MB INT8 student is strictly weaker than this frozen ceiling. Therefore:
  - ceiling max < 0.75  => 800 is UNREACHABLE for D1 under the admissibility filter (selection
    over configs can only inflate, so a failing max is a hard wall). DECISIVE NEGATIVE.
  - ceiling max >= 0.75 => headroom may exist; a distilled student build is justified (but the
    mined config still needs fresh held-out confirmation before it means a product win).

Also reports D2 binding axis: held-out global-threshold FRR @ FAR<=5% (replicates TorgoEval).

Fidelity gate (EVAL-004): the MFCC arm must reproduce the committed D1 ~59.2% / D2 ~75.7%.

Reuses harness.py (identical DTW+fold+scoring as core:eval TorgoEval) and ssl_features.py.
Offline: only uses models already in the HF cache (wavlm-base-plus, wavlm-large, distilhubert).
numpy + torch (CPU). Embeddings cached to .npy so reruns are cheap.
"""
import os, sys, time, json
import numpy as np
import harness as H

TORGO = os.path.expanduser("~/torgo")
CACHE = os.path.expanduser("~/torch-venv") and os.path.join(
    os.path.dirname(__file__), "_ceiling_cache")
os.makedirs(CACHE, exist_ok=True)

DYS = ["F01", "F03", "F04"]
CTL = ["FC01", "FC02", "FC03"]
ALL = DYS + CTL

# (model_id, list_of_layers_to_probe). Layers chosen to span the network; mean-pool per layer.
# Only cached models to stay offline.
MODELS = {
    "wavlm-base-plus": ("microsoft/wavlm-base-plus", list(range(0, 13))),   # 12 layers + embeddings
    "wavlm-large": ("microsoft/wavlm-large", list(range(0, 25))),           # 24 layers
    "distilhubert": ("ntu-spml/distilhubert", list(range(0, 3))),           # 2 layers (small-student proxy)
}


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


def all_wavs(data):
    ws = set()
    for d in data.values():
        for lst in d["commands"].values():
            ws.update(lst)
        ws.update(d["negatives"])
    return sorted(ws)


def embed_all_layers(model_key, wavs):
    """Return {wav: (n_layers, H) mean-pooled + L2-normalised per hidden layer}. Cached to disk."""
    cache_path = os.path.join(CACHE, f"{model_key}.npz")
    if os.path.exists(cache_path):
        z = np.load(cache_path, allow_pickle=True)
        d = {k: z[k] for k in z.files}
        if all(w in d for w in wavs):
            print(f"  [cache hit] {model_key}: {len(d)} embeddings", flush=True)
            return d
    import torch
    from transformers import AutoModel
    torch.set_num_threads(4)
    torch.set_grad_enabled(False)
    mid = MODELS[model_key][0]
    print(f"  loading {mid} ...", flush=True)
    net = AutoModel.from_pretrained(mid, output_hidden_states=True).eval()
    out = {}
    t0 = time.time()
    for i, wav in enumerate(wavs):
        x = H.read_wav(wav)
        sp = H.energy_vad_trim(x)
        if sp.size < 400:
            # keep a zero placeholder so downstream can skip; use tiny fallback = whole clip
            sp = x if x.size >= 400 else np.zeros(400, dtype=np.float32)
        w = (sp - sp.mean()) / (sp.std() + 1e-7)
        t = torch.from_numpy(w.astype(np.float32)).unsqueeze(0)
        hs = net(t).hidden_states  # tuple (n_layers+1) of (1,T,H)
        vecs = []
        for h in hs:
            v = h[0].mean(0).numpy()
            v = v / (np.linalg.norm(v) + 1e-8)
            vecs.append(v.astype(np.float32))
        out[wav] = np.stack(vecs)  # (n_layers, H)
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(wavs)} ({time.time()-t0:.0f}s)", flush=True)
    np.savez(cache_path, **out)
    print(f"  embedded {len(out)} ({time.time()-t0:.0f}s) -> {cache_path}", flush=True)
    return out


def eval_config(emb, data, layer):
    """Aggregate rank-1 and held-out FRR@FAR over the given speakers for one layer."""
    per_spk = {}
    agg_rows_by_spk = {}
    for spk, d in data.items():
        # build feat_cache inline (avoid harness dependency)
        wavs = set()
        for lst in d["commands"].values():
            wavs.update(lst)
        wavs.update(d["negatives"])
        feat_cache = {w: emb[w][layer][None, :] for w in wavs}
        rows = H.eval_speaker(d, None, feat_cache)
        agg_rows_by_spk[spk] = rows
        r1, hits, n = H.rank1(rows)
        frr, far, npos, nneg = H.held_out_global(rows)
        per_spk[spk] = dict(rank1=r1, hits=hits, npos=n, frr=frr, far=far, nneg=nneg)
    return per_spk


def aggregate(per_spk, speakers):
    hits = sum(per_spk[s]["hits"] for s in speakers)
    npos = sum(per_spk[s]["npos"] for s in speakers)
    r1 = hits / npos if npos else 0.0
    # FRR/FAR pooled by counts
    frr_num = sum(per_spk[s]["frr"] * per_spk[s]["npos"] for s in speakers)
    far_num = sum(per_spk[s]["far"] * per_spk[s]["nneg"] for s in speakers)
    nneg = sum(per_spk[s]["nneg"] for s in speakers)
    return dict(rank1=r1, frr=frr_num / npos if npos else 0.0,
                far=far_num / nneg if nneg else 0.0, npos=npos, nneg=nneg)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = {spk: load_speaker(spk) for spk in ALL}
    data = {k: v for k, v in data.items() if v is not None}
    wavs = all_wavs(data)
    print(f"TORGO: {len(data)} speakers, {len(wavs)} wavs", flush=True)

    keys = list(MODELS) if which == "all" else which.split(",")
    results = []
    for mk in keys:
        print(f"\n=== {mk} ===", flush=True)
        emb = embed_all_layers(mk, wavs)
        nlayers = MODELS[mk][1]
        for layer in nlayers:
            per = eval_config(emb, data, layer)
            agg_all = aggregate(per, list(data))
            agg_dys = aggregate(per, [s for s in DYS if s in data])
            agg_ctl = aggregate(per, [s for s in CTL if s in data])
            row = dict(model=mk, layer=layer,
                       r1_all=agg_all["rank1"], r1_dys=agg_dys["rank1"], r1_ctl=agg_ctl["rank1"],
                       frr_all=agg_all["frr"], far_all=agg_all["far"],
                       npos=agg_all["npos"], nneg=agg_all["nneg"])
            results.append(row)
            print(f"  L{layer:2d}  rank1 all={agg_all['rank1']*100:5.1f}%  "
                  f"dys={agg_dys['rank1']*100:5.1f}%  ctl={agg_ctl['rank1']*100:5.1f}%  |  "
                  f"FRR={agg_all['frr']*100:5.1f}% @ FAR={agg_all['far']*100:4.1f}%", flush=True)

    results.sort(key=lambda r: -r["r1_all"])
    print("\n===== TOP CONFIGS BY AGGREGATE RANK-1 =====", flush=True)
    for r in results[:8]:
        print(f"  {r['model']:16s} L{r['layer']:2d}  rank1={r['r1_all']*100:5.1f}%  "
              f"FRR={r['frr_all']*100:5.1f}% @ FAR={r['far_all']*100:4.1f}%", flush=True)
    best = results[0]
    print(f"\nCEILING (max aggregate rank-1): {best['r1_all']*100:.1f}%  "
          f"[{best['model']} L{best['layer']}]", flush=True)
    print(f"H1 (>=75% aggregate rank-1): {'PASS' if best['r1_all'] >= 0.75 else 'FAIL'}", flush=True)
    out_path = os.path.join(CACHE, "ceiling_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
