"""F29 — Query-side rate normalization (tests A4's prediction directly).

A4 found the severe-dys within-word scatter is dominated by a DURATION axis (F03 |r|=0.80). SSL
embeddings are rate-sensitive, and severe speakers vary speaking rate hugely. F29 deterministically
time-warps each VAD-trimmed segment to a CANONICAL speech duration (linear resample) BEFORE embedding,
compressing the duration axis. Distinct from enrollment-side tempo augmentation (query + templates both
normalized to the same canonical rate).

A4's falsifiable prediction: rate normalization compresses the duration axis -> lower within-word scatter
-> higher dys separability AUC and lower dys D2 FRR. If it does NOT help, A4's duration-axis mechanism is
not causally exploitable this way.

METHOD: re-embed dys command utts + in-vocab negatives with wavlm-large L15 under
  (baseline) VAD-trim only              vs
  (F29)     VAD-trim + resample speech region to CANON_S seconds.
Compare AUC(genuine<impostor) and held-out FRR@FAR<=5%, few-shot leave-one-out.

PRE-REGISTERED GATE: dys pooled AUC(F29) >= AUC(baseline) + 0.03 (a real compression of the duration axis).
"""
import os, sys, json, glob
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H

LAYER = 15
SR = 16000
CANON_S = 1.0
CACHE_NPZ = os.path.join(L.CACHE, "f29_dys_emb.npz")
np.random.seed(0)


def resample_to(x, target_len):
    if x.size < 2:
        return x
    return np.interp(np.linspace(0, x.size - 1, target_len), np.arange(x.size), x).astype(np.float32)


def embed_variants(net, path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = resample_to(x, int(x.size * SR / sr))
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    outs = {}
    for name, seg in [("base", sp), ("f29", resample_to(sp, int(CANON_S * SR)))]:
        w = (seg - seg.mean()) / (seg.std() + 1e-7)
        h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
        v = h.mean(0)
        outs[name] = (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)
    return outs


def build_cache():
    need = {}
    for spk in L.DYS:
        d = L.load_speaker(spk)
        if not d:
            continue
        for w, wavs in d["commands"].items():
            for x in wavs:
                need[x] = True
        for x in d["negatives"]:
            need[x] = True
    paths = list(need)
    if os.path.exists(CACHE_NPZ):
        z = np.load(CACHE_NPZ, allow_pickle=True)
        cache = {k: z[k].item() for k in z.files}
        if all(p in cache for p in paths):
            return cache
    else:
        cache = {}
    from transformers import AutoModel
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    todo = [p for p in paths if p not in cache]
    print(f"  embedding {len(todo)} dys utts × 2 variants (wavlm-large L{LAYER})...", flush=True)
    for i, p in enumerate(todo):
        try:
            cache[p] = embed_variants(net, p)
        except Exception as e:
            cache[p] = None
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(todo)}", flush=True)
    np.savez(CACHE_NPZ, **{k: np.array(v, dtype=object) for k, v in cache.items()})
    return cache


def eval_variant(cache, variant):
    """Pooled dys AUC + held-out FRR@FAR5%, few-shot leave-one-out, using cache[path][variant]."""
    gen_all, imp_all = [], []
    num = den = 0
    for spk in L.DYS:
        d = L.load_speaker(spk)
        if not d:
            continue
        words = {}
        for w, wavs in d["commands"].items():
            vs = [cache[x][variant] for x in wavs if cache.get(x)]
            if len(vs) >= 2:
                words[w] = vs
        if len(words) < 3:
            continue
        negs = [cache[x][variant] for x in d["negatives"] if cache.get(x)]
        gen = []
        for w, vs in words.items():
            for i, q in enumerate(vs):
                rest = [vs[j] for j in range(len(vs)) if j != i]
                gen.append(min(1 - float(q @ t) for t in rest))
        templ = {w: vs for w, vs in words.items()}
        imp = [min(min(1 - float(nv @ t) for t in tt) for tt in templ.values()) for nv in negs]
        gen_all += gen; imp_all += imp
    g, im = np.array(gen_all), np.array(imp_all)
    auc = float(np.mean(g[:, None] < im[None, :])) if g.size and im.size else None
    # held-out-ish FRR@FAR5% (pooled threshold)
    thr = np.sort(im)[int(0.05 * im.size)] if im.size else 0
    frr = float((g > thr).mean())
    return auc, frr, g.size, im.size


def main():
    print(f"F29 — query-side rate normalization (dys, wavlm-large L{LAYER}, canon={CANON_S}s)\n", flush=True)
    cache = build_cache()
    out = {}
    print(f"  {'variant':>8}  {'AUC':>6}  {'FRR@FAR5%':>10}", flush=True)
    for v in ["base", "f29"]:
        auc, frr, ng, ni = eval_variant(cache, v)
        out[v] = dict(auc=auc, frr=frr, n_gen=ng, n_imp=ni)
        print(f"  {v:>8}  {auc:6.3f}  {frr*100:9.1f}%   (n_gen={ng})", flush=True)
    d = out["f29"]["auc"] - out["base"]["auc"]
    gate = d >= 0.03
    print(f"\n  GATE (F29 AUC >= base + 0.03): base={out['base']['auc']:.3f} -> f29={out['f29']['auc']:.3f} "
          f"(Δ={d:+.3f}) => {'PASS -> A4 duration axis is exploitable' if gate else 'FAIL -> rate-norm does not compress the wall'}", flush=True)
    out["delta_auc"] = d; out["gate"] = bool(gate)
    with open(os.path.join(L.CACHE, "f29_rate_norm.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
