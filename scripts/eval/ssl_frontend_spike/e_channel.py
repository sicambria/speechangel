"""E26 + E27 — channel (D5/D4) decomposition and K-budget allocation (typical population).

D5 (reverb) binds the typical composite (§6). Two questions, one embedding pass (control speakers,
wavlm-large L15, re-embed degraded audio the honest way — encoder sees the degradation):

E26 — D5 loss decomposition. Rank-1 under RT60 ∈ {0.15, 0.30, 0.60}s with (a) clean-only enrollment vs
  (b) reverb-augmented enrollment. If reverb-aug closes most of the gap -> the loss is train/test channel
  MISMATCH (cheap enrollment-augmentation fix). If a residual persists -> intrinsic reverberant smearing
  (needs I10 dereverb).

E27 — K-budget allocation factorial at FIXED K=4 (the product's real rep budget, D13): allocate the 4
  templates as {4 clean} vs {2 clean+2 reverb} vs {2 clean+2 noisy} vs {1 clean+1 reverb+1 noisy+1 band},
  evaluate rank-1 on a mixed adverse test (reverb+noise). Multi-condition enrollment is banked as additive;
  the ALLOCATION tradeoff at fixed budget is the unmeasured product decision.

PRE-REGISTERED reads: E26 — reverb-aug recovers >=50% of the clean→RT60-0.6 gap ⇒ mismatch-dominated.
E27 — report best allocation; flag if a mixed allocation beats {4 clean} on the adverse test by >=3 pp.
"""
import os, sys, json, math, wave
import numpy as np
import torch
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H

LAYER = 15
SR = 16000
CACHE = os.path.join(L.CACHE, "e_channel_emb.npz")
np.random.seed(0)


def read(p):
    with wave.open(p, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def add_noise(x, snr=15):
    p = (x ** 2).mean() + 1e-9
    n = np.random.randn(x.size).astype(np.float32)
    n *= math.sqrt(p / (10 ** (snr / 10)) / (n.var() + 1e-9))
    return x + n


def reverb(x, rt60):
    Ln = int(rt60 * SR); t = np.arange(Ln)
    rir = (np.random.randn(Ln) * np.exp(-6.9 * t / Ln)).astype(np.float32); rir[0] = 1.0
    y = np.convolve(x, rir)[: x.size]
    return y / (np.abs(y).max() + 1e-9) * (np.abs(x).max() + 1e-9)


def bandlimit(x, lo=300, hi=3400):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(x.size, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=x.size).astype(np.float32)


CONDS = {"clean": lambda x: x, "rev15": lambda x: reverb(x, 0.15), "rev30": lambda x: reverb(x, 0.30),
         "rev60": lambda x: reverb(x, 0.60), "noise": lambda x: add_noise(x, 15), "band": bandlimit}


def embed_cond(net, x, cond):
    xc = CONDS[cond](x)
    sp = H.energy_vad_trim(xc)
    if sp.size < 1520:
        sp = xc if xc.size >= 1520 else np.pad(xc, (0, 1520 - xc.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def build_cache():
    wavs = sorted({x for s in L.CTL for v in L.load_speaker(s)["commands"].values() for x in v})
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        cache = {k: z[k].item() for k in z.files}
        if all(w in cache for w in wavs):
            return cache, wavs
    else:
        cache = {}
    from transformers import AutoModel
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    todo = [w for w in wavs if w not in cache]
    print(f"  embedding {len(todo)} utts × {len(CONDS)} conditions...", flush=True)
    for i, wv in enumerate(todo):
        x = read(wv)
        cache[wv] = {c: embed_cond(net, x, c) for c in CONDS}
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(todo)}", flush=True)
    np.savez(CACHE, **{k: np.array(v, dtype=object) for k, v in cache.items()})
    return cache, wavs


def rank1(cache, spks, query_cond, enroll_conds, K=99):
    hits = tot = 0
    for s in spks:
        d = L.load_speaker(s)
        words = {w: [x for x in v if x in cache] for w, v in d["commands"].items()}
        words = {w: v for w, v in words.items() if len(v) >= 2}
        for w, vs in words.items():
            for qi in range(len(vs)):
                q = cache[vs[qi]][query_cond]
                enroll = {}
                for ww, vv in words.items():
                    tw = vv if ww != w else [vv[j] for j in range(len(vv)) if j != qi]
                    embs = []
                    for x in tw[:K]:
                        for c in enroll_conds:
                            embs.append(cache[x][c])
                    if embs:
                        enroll[ww] = embs
                best = min((min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items() if tt)
                hits += (best[1] == w); tot += 1
    return hits / tot if tot else 0


def rank1_alloc(cache, spks, query_cond, alloc):
    """K=4 allocation: alloc = list of 4 conditions to draw templates from (per template slot)."""
    hits = tot = 0
    for s in spks:
        d = L.load_speaker(s)
        words = {w: [x for x in v if x in cache] for w, v in d["commands"].items()}
        words = {w: v for w, v in words.items() if len(v) >= 5}
        for w, vs in words.items():
            for qi in range(len(vs)):
                q = cache[vs[qi]][query_cond]
                enroll = {}
                for ww, vv in words.items():
                    pool = vv if ww != w else [vv[j] for j in range(len(vv)) if j != qi]
                    if len(pool) < 4:
                        continue
                    enroll[ww] = [cache[pool[k]][alloc[k]] for k in range(4)]
                if len(enroll) < 3:
                    continue
                best = min((min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items())
                hits += (best[1] == w); tot += 1
    return hits / tot if tot else 0


def main():
    print(f"E26/E27 — channel decomposition + K-budget allocation (typical, wavlm-large L{LAYER})\n", flush=True)
    cache, wavs = build_cache()
    # E26: D5 loss decomposition
    print("  E26 — reverb rank-1: clean-enroll vs reverb-augmented-enroll", flush=True)
    clean_r1 = rank1(cache, L.CTL, "clean", ["clean"])
    print(f"    clean query / clean enroll (ceiling): {clean_r1*100:.1f}%", flush=True)
    e26 = {}
    for rc in ["rev15", "rev30", "rev60"]:
        base = rank1(cache, L.CTL, rc, ["clean"])
        aug = rank1(cache, L.CTL, rc, ["clean", rc])
        gap = clean_r1 - base
        recov = (aug - base) / gap if gap > 1e-6 else 0
        e26[rc] = dict(clean_enroll=base, aug_enroll=aug, gap=gap, recovery=recov)
        print(f"    {rc}: clean-enroll={base*100:5.1f}%  +reverb-aug={aug*100:5.1f}%  "
              f"(gap {gap*100:.1f}pp, aug recovers {recov*100:.0f}%)", flush=True)
    md = np.mean([e26[r]["recovery"] for r in e26])
    print(f"    => reverb loss is {'MISMATCH-dominated (enrollment-aug fixes it)' if md >= 0.5 else 'INTRINSIC smearing (needs dereverb I10)'}", flush=True)
    # E27: K-budget allocation on a mixed adverse test (rev30 query)
    print("\n  E27 — fixed K=4 allocation, adverse test (rev30 query):", flush=True)
    allocs = {"4clean": ["clean"] * 4, "2c+2rev": ["clean", "clean", "rev30", "rev60"],
              "2c+2noisy": ["clean", "clean", "noise", "noise"],
              "1c+rev+noise+band": ["clean", "rev30", "noise", "band"]}
    e27 = {}
    for name, al in allocs.items():
        r = rank1_alloc(cache, L.CTL, "rev30", al)
        e27[name] = r
        print(f"    {name:20s}: rank1={r*100:5.1f}%", flush=True)
    best = max(e27, key=e27.get)
    print(f"    best allocation = {best} ({e27[best]*100:.1f}%) vs 4clean ({e27['4clean']*100:.1f}%) "
          f"[Δ={(e27[best]-e27['4clean'])*100:+.1f}pp]", flush=True)

    # C17 — asymmetric: clean support vs matched-noisy support, both with NOISY query (deployment mismatch)
    print("\n  C17 — asymmetric clean-support / noisy-query (noisy query):", flush=True)
    c17_clean = rank1(cache, L.CTL, "noise", ["clean"])           # clean enroll, noisy query (mismatch)
    c17_matched = rank1(cache, L.CTL, "noise", ["clean", "noise"])  # + noisy templates (matched)
    print(f"    clean-support   / noisy-query: rank1={c17_clean*100:.1f}%", flush=True)
    print(f"    +noisy-support  / noisy-query: rank1={c17_matched*100:.1f}%  (Δ={(c17_matched-c17_clean)*100:+.1f}pp)", flush=True)
    print(f"    => asymmetric (clean-support+noisy-query) episodes {'help materially' if (c17_matched-c17_clean) >= 0.03 else 'give little here'} for the D4/D5 domains", flush=True)
    with open(os.path.join(L.CACHE, "e_channel.json"), "w") as f:
        json.dump({"clean_r1": clean_r1, "e26": e26, "e27": e27,
                   "c17_clean_support": c17_clean, "c17_matched_support": c17_matched}, f, indent=2)


if __name__ == "__main__":
    main()
