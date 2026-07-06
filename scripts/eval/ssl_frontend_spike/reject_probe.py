"""Prototype: can score-normalization close the rank-1->FRR gap on the WavLM embedding?

WavLM-L12 mean-pool cosine: rank-1 71.9% but held-out FRR@FAR<=5% = 66.3% (38 pts lost to thresholding).
Test whether adaptive per-query score normalization improves held-out FRR at MATCHED FAR (EVAL-002/003).

Pre-registered H1: per-query cohort z-norm of the command-distance vector (subtract the query's mean
distance-to-all-commands, divide by its std) improves held-out FRR@matched-FAR vs the raw global threshold.
Exploratory (NOT-banked) family: top-2 margin rejection.
"""
import sys, time, math
import numpy as np, torch
import harness as H

SPKS = ["F01", "F03", "F04"]
LAYER, MODEL = 12, "microsoft/wavlm-base-plus"
MIN_SPEECH = 1520
TARGET_FAR = 0.05

corpus = {k: v for k, v in H.scan().items() if k in SPKS}
all_wavs = sorted({w for d in corpus.values() for lst in d["commands"].values() for w in lst}
                  | {w for d in corpus.values() for w in d["negatives"]})
from transformers import AutoModel
net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval(); torch.set_grad_enabled(False)
emb = {}
t0 = time.time()
for wav in all_wavs:
    sp = H.energy_vad_trim(H.read_wav(wav))
    if sp.size < MIN_SPEECH:
        emb[wav] = None; continue
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0); emb[wav] = (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)
print(f"embeddings {time.time()-t0:.0f}s", flush=True)


def cos_dist(a, b):
    return 1.0 - float(a @ b)  # unit vectors


def rows_for(spk_data, k=5):
    """Per query: fold, truth, and dict cmd->min cosine distance over that cmd's enrolled templates."""
    out = []
    for fold in H.folds(spk_data, k):
        enroll = {}
        for word, wav in fold["enroll"]:
            if emb[wav] is not None:
                enroll.setdefault(word, []).append(emb[wav])
        for truth, wav in [(w, x) for w, x in fold["positives"]] + [(None, x) for x in fold["negatives"]]:
            q = emb[wav]
            if q is None:
                continue
            bbc = {c: min(cos_dist(q, t) for t in ts) for c, ts in enroll.items()}
            out.append({"fold": fold["index"], "truth": truth, "bbc": bbc})
    return out


def score_variants(r):
    """Return dict variant-> (winner_cmd, score) where LOWER score = more confident accept."""
    bbc = r["bbc"]
    if not bbc:
        return {"raw": (None, math.inf), "znorm": (None, math.inf), "margin": (None, math.inf)}
    items = sorted(bbc.items(), key=lambda kv: kv[1])
    win, d1 = items[0]
    d2 = items[1][1] if len(items) > 1 else d1 + 1.0
    vals = np.array(list(bbc.values()))
    mu, sd = vals.mean(), vals.std() + 1e-8
    return {
        "raw": (win, d1),
        "znorm": (win, (d1 - mu) / sd),         # per-query cohort z-norm (H1)
        "margin": (win, d1 - (d2 - d1)),        # exploratory: reward a large best-vs-2nd gap
    }


def held_out_frr_far(all_rows, variant, target=TARGET_FAR):
    folds = sorted({r["fold"] for r in all_rows})
    acc = pos = fa = neg = 0
    for f in folds:
        train = [r for r in all_rows if r["fold"] != f]
        # candidate thresholds from train scores; pick largest with train FAR<=target
        tcands = sorted({score_variants(r)[variant][1] for r in train
                         if math.isfinite(score_variants(r)[variant][1])})
        def far_at(thr, rows):
            negs = [r for r in rows if r["truth"] is None]
            if not negs: return 0.0
            f_ = sum(1 for r in negs if (lambda ws: ws[0] is not None and ws[1] <= thr)(score_variants(r)[variant]))
            return f_ / len(negs)
        thr = (tcands[0] - 1) if tcands else 0.0
        for t in tcands:
            if far_at(t, train) <= target:
                thr = t
        for r in [r for r in all_rows if r["fold"] == f]:
            wc, sc = score_variants(r)[variant]
            accepted = wc is not None and sc <= thr
            if r["truth"] is not None:
                pos += 1; acc += (accepted and wc == r["truth"])
            else:
                neg += 1; fa += accepted
    return (1 - acc / pos if pos else 0.0), (fa / neg if neg else 0.0)


all_rows = []
for spk, d in corpus.items():
    all_rows.extend(rows_for(d))
print(f"\n{'variant':>8}  FRR@matchedFAR  (target {TARGET_FAR:.0%})", flush=True)
for v in ["raw", "znorm", "margin"]:
    frr, far = held_out_frr_far(all_rows, v)
    tag = "  <- H1 (pre-registered)" if v == "znorm" else ("  [NOT-banked family]" if v == "margin" else "  (baseline)")
    print(f"{v:>8}  FRR={frr*100:5.1f}%  FAR={far*100:4.1f}%{tag}", flush=True)
