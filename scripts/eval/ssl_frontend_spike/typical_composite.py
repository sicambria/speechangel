"""Full typical-population composite under an on-device SSL encoder + few-shot enrollment.

User authorized relaxing the artificial size/enrollment constraints (2026-07-10, per CONSTRAINT-001).
Validates the composite for the TYPICAL-speech population (control FC01/FC02/FC03) with a wavlm-large
on-device SSL encoder (~316MB INT8, run per-utterance behind the VAD gate — feasible on a 2026 sub-300
EUR phone), few-shot + multi-condition enrollment, across the encoder-dependent composite domains:

  D1 rank-1 (clean), D4 noise@20dB, D5 reverb rt60~250ms, D6 telephone band 300-3400Hz  [rank-1]
  D2 = carried from held_out_d2.py --distinct (held-out deployment-slice + few-shot + vocab-distinct):
       control 13.8% -> band 800 ; dysarthric ~50-55% -> band 600 (disorder-capped, AUC~0.70).

Conditions applied to raw audio then re-embedded (the honest way — the encoder sees degraded audio).
Reports each domain's band; the composite is the min. Dysarthric shown alongside (disorder-capped).
"""
import os, sys, math, wave
import numpy as np
import torch
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
CTL = ["FC01", "FC02", "FC03"]; DYS = ["F01", "F03", "F04"]
SR = 16000; LAYER = 15
MODEL = "microsoft/wavlm-large"
np.random.seed(0)


def load(s):
    r = TORGO if not s.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(r).get(s)


def read(p):
    with wave.open(p, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


# ---- conditions (match core:eval AudioAugment intent) ----
def add_noise(x, snr_db=20):
    p = (x ** 2).mean() + 1e-9
    n = np.random.randn(x.size).astype(np.float32)
    n *= math.sqrt(p / (10 ** (snr_db / 10)) / (n.var() + 1e-9))
    return x + n


def reverb(x, rt60=0.25):
    # simple exponential-decay RIR
    L = int(rt60 * SR)
    t = np.arange(L)
    rir = (np.random.randn(L) * np.exp(-6.9 * t / L)).astype(np.float32)
    rir[0] = 1.0
    y = np.convolve(x, rir)[:x.size]
    return y / (np.abs(y).max() + 1e-9) * (np.abs(x).max() + 1e-9)


def bandlimit(x, lo=300, hi=3400):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=x.size).astype(np.float32)


CONDS = {"clean": lambda x: x, "noise20": add_noise, "reverb250": reverb, "band": bandlimit}


def embed_batch(net, wavs, cond):
    out = {}
    with torch.no_grad():
        for w in wavs:
            x = read(w)
            x = cond(x)
            sp = H.energy_vad_trim(x)
            if sp.size < 400:
                sp = x if x.size >= 400 else np.zeros(400, dtype=np.float32)
            wn = (sp - sp.mean()) / (sp.std() + 1e-7)
            h = net(torch.from_numpy(wn.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
            v = h.mean(0); out[w] = (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)
    return out


def rank1_fewshot(emb, spks, K=99, enroll_embs=None):
    """leave-one-out rank-1, few-shot, threshold-free. query embedded with `emb` (test condition);
    templates enrolled from `enroll_embs` = list of condition-dicts (multi-condition enrollment) if given,
    else clean `emb`. Multi-condition enrollment = train/test channel match (the banked D5/D4/D6 lever)."""
    enroll_srcs = enroll_embs if enroll_embs is not None else [emb]
    hits = tot = 0
    for s in spks:
        d = load(s)
        words = {w: [x for x in v if x in emb] for w, v in d["commands"].items()}
        words = {w: v for w, v in words.items() if len(v) >= 2}
        for w, vs in words.items():
            for qi in range(len(vs)):
                q = emb[vs[qi]]
                enroll = {}
                for ww, vv in words.items():
                    tmpl_wavs = vv if ww != w else [vv[j] for j in range(len(vv)) if j != qi]
                    enroll[ww] = [src[x] for x in tmpl_wavs[:K] for src in enroll_srcs if x in src]
                best = min((min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items() if tt)
                hits += (best[1] == w); tot += 1
    return hits / tot if tot else 0


BANDS = {"D1": [(600,.55),(700,.65),(800,.75),(900,.85)], "D4": [(600,.55),(700,.60),(800,.70),(900,.80)],
         "D5": [(700,.65),(800,.75),(900,.85)], "D6": [(700,.65),(800,.75),(900,.85)]}
DOM_COND = {"D1": "clean", "D4": "noise20", "D5": "reverb250", "D6": "band"}


def band(dom, v):
    b = 500
    for sc, th in BANDS[dom]:
        if v >= th: b = sc
    return b


def main():
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    print(f"Loading {MODEL} (on-device SSL encoder)...", flush=True)
    net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
    for grp, spks in [("TYPICAL(control)", CTL), ("DYSARTHRIC", DYS)]:
        wavs = sorted({x for s in spks for v in load(s)["commands"].values() for x in v})
        print(f"\n=== {grp} ({len(wavs)} utts) — wavlm-large L{LAYER}, few-shot + multi-condition enrollment ===", flush=True)
        # embed all utts under every condition once (reused for multi-condition enrollment)
        emb_by_cond = {c: embed_batch(net, wavs, fn) for c, fn in CONDS.items()}
        enroll_srcs = list(emb_by_cond.values())  # multi-condition enrollment (clean+noise+reverb+band)
        bands = []
        for dom, cname in DOM_COND.items():
            emb = emb_by_cond[cname]  # query in the test condition
            r1 = rank1_fewshot(emb, spks, enroll_embs=enroll_srcs)
            b = band(dom, r1)
            bands.append(b)
            print(f"  {dom} ({cname:9s}): rank1={r1*100:5.1f}%  -> band {b}", flush=True)
        # D2 = held-out deployment-slice + few-shot + vocab-distinct FRR@FAR<=5% (held_out_d2.py --distinct):
        #   control 13.8% -> band 800 (wavlm-large L15) ; dysarthric ~50-55% -> band 600 (disorder-capped)
        d2 = (800 if grp.startswith("TYP") else 600)
        print(f"  D2 (held-out distinct FRR@FAR): band {d2}  [held_out_d2.py --distinct]", flush=True)
        print(f"  D13 enrollment: ~950 ; D3 ambient: ~800 (dual-cascade, off-encoder)", flush=True)
        allb = bands + [d2, 950, 800]
        print(f"  >>> {grp} composite (min over encoder-dependent + D2/D3/D13) = {min(allb)}", flush=True)


if __name__ == "__main__":
    main()
