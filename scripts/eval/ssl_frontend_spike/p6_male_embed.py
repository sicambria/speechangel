"""P6 — embed REAL TORGO male dysarthric speakers (M01..M05) and re-establish the dysarthric baseline.

The banking blocker in Rounds 1-2 was n=3 female TORGO dysarthric. TORGO male (M.tar.bz2) is now on host.
This embeds the male speakers with wavlm-large (all layers, VAD-trim, mean-pool, L2-norm — IDENTICAL to
the committed F/FC pipeline in ceiling_sweep.embed_all_layers, so numbers are directly comparable) and
re-measures the dysarthric in-vocab wall on real MALE speakers:
  within-word scatter, fisher (nearest-between/within), in-vocab D2 FRR@FAR<=5% (vs same-speaker OOV),
  threshold-free rank-1 confusion.
This extends n=3 -> n=up-to-8 REAL dysarthric speakers and gives the genuine held-out 2nd population that
Round-2 lacked (fit a lever on F -> confirm on M). Cache: _ceiling_cache/male_wavlm_large.npz.

Fidelity note: male controls (MC) not downloaded — the in-vocab D2 uses same-speaker OOV negatives, so MC
is not needed here. Scope caveat: M is still TORGO (channel), so this confirms speaker-generalization, not
channel-independence.
"""
import os, sys, time, glob
import numpy as np
import harness as H
import cand_lib as L
from held_out_d2 import distinct_subset

TORGO = os.path.expanduser("~/torgo")
LAYER = 15; FAR = 0.05
CACHE = os.path.join(L.CACHE, "male_wavlm_large.npz")
MALE = ["M01", "M02", "M03", "M04", "M05"]


def _u(v):
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def scan_male():
    data = {}
    for m in MALE:
        root = os.path.join(TORGO, m)
        if not os.path.isdir(root):
            continue
        # scan expects speaker dirs UNDER root; point scan at ~/torgo and filter
        d = H.scan(TORGO).get(m)
        if d and d["commands"]:
            data[m] = d
    return data


def build_emb(data):
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        emb = {k: z[k] for k in z.files}
        need = set()
        for d in data.values():
            for lst in d["commands"].values():
                need.update(lst)
            need.update(d["negatives"])
        if need <= set(emb):
            print(f"  [cache hit] {len(emb)} male embeddings", flush=True)
            return emb
    import torch
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    print("  loading wavlm-large ...", flush=True)
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    wavs = set()
    for d in data.values():
        for lst in d["commands"].values():
            wavs.update(lst)
        wavs.update(d["negatives"])
    wavs = sorted(wavs)
    print(f"  embedding {len(wavs)} male wavs (wavlm-large all layers) ...", flush=True)
    out = {}
    t0 = time.time()
    MAXS = 4.0  # cap: TORGO male set includes long SENTENCE prompts -> wavlm activation OOM. Commands are short.
    for i, wav in enumerate(wavs):
        try:
            x = H.read_wav(wav)
            sp = H.energy_vad_trim(x)
            sp = sp[: int(MAXS * 16000)]
            if sp.size < 1520:
                sp = x[: int(MAXS * 16000)] if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
            w = (sp - sp.mean()) / (sp.std() + 1e-7)
            hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
            out[wav] = np.stack([_u(h[0].mean(0).numpy()) for h in hs])
        except Exception as e:
            print(f"    skip {os.path.basename(wav)}: {type(e).__name__}", flush=True)
            continue
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(wavs)} ({time.time()-t0:.0f}s)", flush=True)
    np.savez(CACHE, **out)
    print(f"  embedded {len(out)} ({time.time()-t0:.0f}s)", flush=True)
    return out


def geom(emb, d, distinct=True):
    if distinct:
        keep = distinct_subset(d, emb, LAYER, 25)
        words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    else:
        words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    if len(words) < 3:
        return None
    within, cents = [], {}
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            c = np.mean(rest, 0); c = c / (np.linalg.norm(c) + 1e-8)
            within.append(1 - float(q @ c))
        c = np.mean(vs, 0); cents[w] = c / (np.linalg.norm(c) + 1e-8)
    ws = list(cents)
    bm = [min(1 - float(cents[w] @ cents[o]) for o in ws if o != w) for w in ws]
    conf = tot = 0
    gen = []
    for wq, vs in words.items():
        for i, q in enumerate(vs):
            best = min(words, key=lambda w: (min(1 - float(q @ t) for j, t in enumerate(words[w]) if not (w == wq and j == i)) if [1 for j in range(len(words[w])) if not (w == wq and j == i)] else 1e9))
            tot += 1; conf += (best != wq)
            rest = [vs[j] for j in range(len(vs)) if j != i]
            gen.append(min(1 - float(q @ t) for t in rest))
    imp = [min(min(1 - float(nv @ t) for t in vs) for vs in words.values()) for nv in negs]
    frr = float("nan")
    if imp:
        thr = np.sort(imp)[max(0, int(FAR * len(imp)) - 1)]
        frr = float(np.mean([g > thr for g in gen]))
    wi = float(np.mean(within))
    return dict(within=wi, fisher=float(np.mean(bm)) / wi, rank1conf=conf / tot, d2_frr=frr, nwords=len(ws))


def main():
    data = scan_male()
    print(f"P6 — REAL male dysarthric baseline. Speakers found: {list(data)}\n", flush=True)
    if not data:
        print("  no male speakers with commands found — check extraction.", flush=True); return
    emb = build_emb(data)
    print(f"\n  {'spk':5s}  {'nwords':>6s}  {'within':>7s}  {'fisher':>7s}  {'rank1conf':>9s}  {'D2 FRR@FAR5%':>12s}", flush=True)
    import json
    out = {}
    for m, d in data.items():
        g = geom(emb, d)
        if not g:
            print(f"  {m}: insufficient", flush=True); continue
        out[m] = g
        print(f"  {m:5s}  {g['nwords']:6d}  {g['within']:7.3f}  {g['fisher']:7.2f}  {g['rank1conf']*100:8.1f}%  {g['d2_frr']*100:11.1f}%", flush=True)
    if out:
        print(f"\n  REAL female dys (ref): within~0.044 fisher~1.04 rank1conf~15-20% D2~50-57%", flush=True)
        print(f"  MALE mean: within={np.mean([o['within'] for o in out.values()]):.3f} "
              f"fisher={np.mean([o['fisher'] for o in out.values()]):.2f} "
              f"D2={np.mean([o['d2_frr'] for o in out.values()])*100:.1f}%", flush=True)
    with open(os.path.join(L.CACHE, "p6_male_baseline.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
