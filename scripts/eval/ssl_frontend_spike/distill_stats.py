"""#7 — Distillation with a STATS-POOLED teacher (EVAL-008: a different substrate than post-hoc pooling).

The banked negative so far is "post-hoc std/mean⊕std pooling of a FROZEN ≤150 MB encoder does not reach <5%"
(best = distilhubert-L2 std 6.36%, band 800). #7 tests the OTHER substrate: train a ≤150 MB student to MATCH
the mean⊕std teacher (wavlm-large L12 mean⊕std = 4.71%, band 900), instead of bolting std onto a frozen
student. If distillation also lands ≥5%, "composite capped at 800" is an EVAL-008-clean bank (post-hoc AND
distillation fail); if it breaks <5%, the composite reaches band 900 on a deployable config.

Scoping (honest): full SSL-backbone distillation on large data is out of host budget; this distills the
teacher's stats-pooled 2048-d embedding into a TRAINED pooling+projection head on the frozen distilhubert-L2
frames (the deployable 24 MB encoder). That is exactly "the pooling objective baked in" (#7) on the deployable
features — the backbone is frozen, the pooling head is learned toward the teacher. Cross-speaker held-out
(EVAL-006), adjudicated FAR-matched vs post-hoc std (6.36%) and mean (9.32%). Pre-registered null: the
distilled head does not beat post-hoc std on the held-out banding metric (overfits the small cohort, like ASP).
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
STD_BASELINE = 0.0636


def teacher_targets(paths):
    """mean⊕std of wavlm-large L12 frames (the 4.71% teacher representation), L2-normed, 2048-d."""
    fr = FQ.load_frames(12, "wavlm_large")
    return {p: FQ.pool_vec(fr[p], "meanstd") for p in paths}


class DistillHead(nn.Module):
    """Attentive-stats pool over student frames -> linear proj to the teacher's 2048-d, L2-normed."""
    def __init__(self, h, out, att=64):
        super().__init__()
        self.w1 = nn.Linear(h, att); self.w2 = nn.Linear(att, 1)
        self.proj = nn.Linear(2 * h, out)

    def forward(self, frames):
        a = torch.softmax(self.w2(torch.tanh(self.w1(frames))), dim=0)
        mu = (a * frames).sum(0)
        sig = torch.sqrt(torch.clamp((a * frames * frames).sum(0) - mu * mu, min=1e-8))
        v = self.proj(torch.cat([mu, sig]))
        return v / (v.norm() + 1e-8)


def train_fold(fr_all, tgt, train_paths, h, out, steps=500, lr=1e-3, seed=0):
    g = torch.Generator().manual_seed(seed)
    model = DistillHead(h, out); opt = torch.optim.Adam(model.parameters(), lr=lr)
    torch.set_grad_enabled(True)
    P = list(train_paths)
    for step in range(steps):
        idx = torch.randperm(len(P), generator=g)[:32].tolist()
        loss = 0.0
        for j in idx:
            s = model(torch.from_numpy(fr_all[P[j]]))
            t = torch.from_numpy(tgt[P[j]])
            loss = loss + (1.0 - (s @ t))            # cosine distillation to the stats-pooled teacher
        loss = loss / len(idx)
        opt.zero_grad(); loss.backward(); opt.step()
    return model


def embed_all(model, fr_all, paths):
    model.eval()
    with torch.no_grad():
        return {p: model(torch.from_numpy(fr_all[p])).numpy().astype(np.float32) for p in paths}


def run(steps=500):
    man, _ = build_cache()
    fr_all = FQ.load_frames(LAYER, TAG)
    spks = list(man.keys())
    allpaths = [p for s in spks for p in
                ([q for w in man[s]["fixed"] for q in man[s]["fixed"][w]] + list(man[s]["neg"]))]
    tgt = teacher_targets(allpaths)
    h = next(iter(fr_all.values())).shape[1]; out = next(iter(tgt.values())).shape[0]
    order = sorted(spks); folds = [order[i::4] for i in range(4)]
    d_recs, d_neg, per = [], [], {}
    for fi, held in enumerate(folds):
        train_spk = [s for s in spks if s not in held]
        train_paths = [p for s in train_spk for w in man[s]["fixed"] for p in man[s]["fixed"][w]]
        model = train_fold(fr_all, tgt, train_paths, h, out, steps=steps, seed=fi)
        for s in held:
            paths = [p for w in man[s]["fixed"] for p in man[s]["fixed"][w]] + list(man[s]["neg"])
            emb = embed_all(model, fr_all, paths)
            pos, neg = FQ.scored_folds_flat(man[s], emb)
            frr, far, p_, ng, recs, ntop = FQ.heldout_from_scored(pos, neg)
            per[s] = frr; d_recs += recs; d_neg += ntop
        print(f"  fold {fi+1}/4 held-out {len(held)} spk — done", flush=True)

    def arm(mode):
        recs, neg = [], []
        for s in spks:
            sub = {p: FQ.pool_vec(fr_all[p], mode) for w in man[s]["fixed"] for p in man[s]["fixed"][w]}
            sub.update({p: FQ.pool_vec(fr_all[p], mode) for p in man[s]["neg"]})
            pos, ng = FQ.scored_folds_flat(man[s], sub)
            frr, far, p_, n, r, nt = FQ.heldout_from_scored(pos, ng)
            recs += r; neg += nt
        return recs, neg
    s_recs, s_neg = arm("std")
    aggD = 1 - sum(r["correct"] for r in d_recs) / len(d_recs)
    aggS = 1 - sum(r["correct"] for r in s_recs) / len(s_recs)
    band = 900 if aggD <= 0.05 else 800
    print(f"\nDISTILL-STATS held-out — distilhubert L2 -> wavlm-large meanstd teacher, 4-fold, {steps} steps")
    print(f"  distilled  aggregate FRR = {aggD*100:.2f}%  -> band {band}")
    print(f"  post-hoc std aggregate FRR = {aggS*100:.2f}%  (banked deployable baseline 6.36%)")
    print("  --- matched-FAR paired McNemar (A=post-hoc std, B=distilled) ---")
    mc = FQ.matched_mcnemar(s_recs, s_neg, d_recs, d_neg, blabel="distilled")
    out_j = {"distilled_frr": aggD, "std_frr": aggS, "band": band, "per_spk": per, "mcnemar_vs_std": mc,
             "steps": steps}
    with open(os.path.join(CACHE, "distill_stats_distilhubert.json"), "w") as f:
        json.dump(out_j, f, indent=2)
    print("  wrote distill_stats_distilhubert.json")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
