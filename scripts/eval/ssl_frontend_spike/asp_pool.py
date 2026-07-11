"""#11 Attentive Statistics Pooling (ASP) — the SOTA of the frame-pooling axis, LEARNED.

Different rigor bucket than the parameter-free std/mean⊕std lever (frame_qbe.py): ASP adds a trained
attention head, so it needs (a) DISJOINT-speaker training — a held-out eval speaker's data never touches
its own ASP head — and (b) a pre-registered NULL, because in a tiny-training few-shot regime a learned
pooling head can OVERFIT and lose to parameter-free mean⊕std (advisor, 2026-07-11 plan gate).

Protocol (EVAL-006 cross-speaker held-out): 4-fold over the 19 GSC eval speakers. For each fold, train
the ASP head (attention over frozen distilhubert-L2 frames) on the OTHER ~14 speakers with a prototypical
word loss, freeze, then compute the held-out speakers' ASP embeddings and score them with the IDENTICAL
within-speaker 5-fold few-shot cosine-1-NN protocol used for std/mean (frame_qbe.scored_folds_flat).
Pool all held-out pos/neg → one held-out FRR@FAR≤5% over all 912, directly comparable + McNemar-adjudicable
vs the shipped mean-pool AND vs the banked parameter-free std-alone (distilhubert L2 = 6.36%).

ASP head: e_t = w2·tanh(W1 h_t) ; α = softmax(e) ; μ~=Σα_t h_t ; σ~=sqrt(Σα_t h_t² − μ~²) ; [μ~‖σ~]→L2.
Deployability: the head is ~H·A params (A=64 → ~50k, <200 kB), frozen at ship (deterministic, Play-policy).
"""
import os, sys, json
import numpy as np
import torch, torch.nn as nn
import cand_lib as L
import frame_qbe as FQ
from a5_gsc_kcurve import build_cache

CACHE = L.CACHE
torch.set_num_threads(4)
TAG, LAYER, MP_LAYER, K = "distilhubert", 2, 2, 5
STD_BASELINE = 0.0636   # banked parameter-free std-alone on this student (frame_qbe confirm)


class ASP(nn.Module):
    def __init__(self, h, att=64):
        super().__init__()
        self.w1 = nn.Linear(h, att)
        self.w2 = nn.Linear(att, 1)

    def forward(self, frames):                       # frames: (T,H) tensor
        e = self.w2(torch.tanh(self.w1(frames)))     # (T,1)
        a = torch.softmax(e, dim=0)                   # (T,1) attention weights
        mu = (a * frames).sum(0)                      # (H,)
        var = (a * frames * frames).sum(0) - mu * mu
        sig = torch.sqrt(torch.clamp(var, min=1e-8))
        v = torch.cat([mu, sig])                      # (2H,)
        return v / (v.norm() + 1e-8)


def embed_all(model, fr_all, paths):
    model.eval()
    with torch.no_grad():
        return {p: model(torch.from_numpy(fr_all[p])).numpy().astype(np.float32) for p in paths}


def train_fold(fr_all, train_clips, h, steps=400, lr=1e-3, seed=0):
    """train_clips: list of (path, word). Prototypical word loss over training speakers only."""
    g = torch.Generator().manual_seed(seed)
    words = sorted({w for _, w in train_clips})
    by_word = {w: [p for p, ww in train_clips if ww == w] for w in words}
    by_word = {w: ps for w, ps in by_word.items() if len(ps) >= 6}
    words = list(by_word)
    model = ASP(h)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    torch.set_grad_enabled(True)                     # a5.build_cache disables grad globally
    for step in range(steps):
        nw = min(6, len(words))
        wsel = [words[i] for i in torch.randperm(len(words), generator=g)[:nw]]
        proto, q_emb, q_lab = [], [], []
        for wi, w in enumerate(wsel):
            ps = by_word[w]
            idx = torch.randperm(len(ps), generator=g)[:6].tolist()
            sup, qry = idx[:3], idx[3:6]
            se = torch.stack([model(torch.from_numpy(fr_all[ps[j]])) for j in sup]).mean(0)
            proto.append(se / (se.norm() + 1e-8))
            for j in qry:
                q_emb.append(model(torch.from_numpy(fr_all[ps[j]]))); q_lab.append(wi)
        P = torch.stack(proto)                        # (nw, 2H)
        Q = torch.stack(q_emb)                        # (nq, 2H)
        logits = (Q @ P.T) * 10.0                     # cosine (already unit) scaled
        loss = nn.functional.cross_entropy(logits, torch.tensor(q_lab))
        opt.zero_grad(); loss.backward(); opt.step()
    return model


def run(steps=400):
    man, wemb = build_cache()
    fr_all = FQ.load_frames(LAYER, TAG)
    z = np.load(os.path.join(CACHE, f"gsc_{TAG}_alllayers.npz"), allow_pickle=True)
    emb_mp = {k: z[k] for k in z.files}
    spks = list(man.keys())
    h = next(iter(fr_all.values())).shape[1]
    # 4 speaker folds (disjoint held-out)
    order = sorted(spks)
    folds = [order[i::4] for i in range(4)]
    a_recs, a_neg = [], []                            # ASP held-out records (all speakers)
    per = {}
    for fi, held in enumerate(folds):
        train_spk = [s for s in spks if s not in held]
        train_clips = [(p, w) for s in train_spk for w, ps in man[s]["fixed"].items() for p in ps]
        model = train_fold(fr_all, train_clips, h, steps=steps, seed=fi)
        for s in held:
            paths = [p for w in man[s]["fixed"] for p in man[s]["fixed"][w]] + list(man[s]["neg"])
            emb = embed_all(model, fr_all, paths)
            pos, neg = FQ.scored_folds_flat(man[s], emb)
            frr, far, p_, ng, recs, ntop = FQ.heldout_from_scored(pos, neg)
            per[s] = frr; a_recs += recs; a_neg += ntop
        print(f"  fold {fi+1}/4 held-out {len(held)} spk trained on {len(train_spk)} — done", flush=True)
    # baseline arms (shipped mean-pool + banked std-alone), same held-out machinery, all speakers
    def arm(mode):
        recs, neg = [], []
        for s in spks:
            if mode == "mean":
                pos, ng = FQ.scored_folds_meanpool(man[s], emb_mp, MP_LAYER)
            else:
                sub = {p: FQ.pool_vec(fr_all[p], mode) for w in man[s]["fixed"]
                       for p in man[s]["fixed"][w]}
                sub.update({p: FQ.pool_vec(fr_all[p], mode) for p in man[s]["neg"]})
                pos, ng = FQ.scored_folds_flat(man[s], sub)
            frr, far, p_, n, r, nt = FQ.heldout_from_scored(pos, ng)
            recs += r; neg += nt
        return recs, neg
    m_recs, m_neg = arm("mean")
    s_recs, s_neg = arm("std")
    aggA = 1 - sum(r["correct"] for r in a_recs) / len(a_recs)
    aggM = 1 - sum(r["correct"] for r in m_recs) / len(m_recs)
    aggS = 1 - sum(r["correct"] for r in s_recs) / len(s_recs)
    # held-out per-speaker FRR@FAR is folded into recs; report the pooled-threshold McNemar (matched FAR)
    print(f"\nASP (learned) held-out — distilhubert L2 K{K}, 4-fold cross-speaker, {steps} steps/fold")
    print(f"  ASP        aggregate (accept-correct) FRR ~ {aggA*100:.2f}%")
    print(f"  mean-pool  aggregate FRR ~ {aggM*100:.2f}%   std-alone aggregate FRR ~ {aggS*100:.2f}%")
    print("  --- matched-FAR paired McNemar (A=mean-pool, B=ASP) ---")
    mcm = FQ.matched_mcnemar(m_recs, m_neg, a_recs, a_neg, blabel="ASP")
    print("  --- matched-FAR paired McNemar (A=std-alone, B=ASP) — the pre-registered contest ---")
    mcs = FQ.matched_mcnemar(s_recs, s_neg, a_recs, a_neg, blabel="ASP")
    out = {"asp_frr": aggA, "mean_frr": aggM, "std_frr": aggS, "std_baseline": STD_BASELINE,
           "per_spk": per, "mcnemar_vs_mean": mcm, "mcnemar_vs_std": mcs, "steps": steps}
    with open(os.path.join(CACHE, "asp_pool_distilhubert_L2.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("  wrote asp_pool_distilhubert_L2.json")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
