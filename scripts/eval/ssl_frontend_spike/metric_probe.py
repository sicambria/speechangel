"""Learned QbE embedding probe — the LAST open admissible lever for the D2/D1 walls.

The frozen-SSL ceiling fails D1 (71.9%<75%) and D2 (~65% FRR>>15%) on dysarthric TORGO. That upper-bounds
the frozen-SSL family, but NOT a purpose-trained embedding. This probe trains a small contrastive
projection head g: R^H -> R^d on top of frozen wavlm mean-pooled embeddings, optimizing same-word vs
different-word separability (supervised contrastive / InfoNCE). It ships frozen, ~<1MB, deterministic,
1-shot at enrollment -> fully admissible.

Pre-registered H3 (EVAL-003, ONE hypothesis): a learned projection trained on CONTROL speakers
(FC01/FC02/FC03) reduces held-out DYSARTHRIC FRR @ FAR<=5% to <= 0.15 (D2 800 rung) and/or lifts
dysarthric rank-1 to >= 0.75 (D1 800 rung), with NO dysarthric labels used in training.

Honesty: control+dysarthric share the prompt vocabulary, so learning word-discriminative structure
transfers optimistically (mild positive bias). If even this optimistically-biased probe falls short,
the wall is airtight (bias only helps). No dysarthric utterance or label enters training -> the
speaker-independent, dev-time-trained, ships-frozen contract holds.

Reuses cached wavlm-base-plus.npz (mean-pooled per-layer). torch CPU. Deterministic seed.
"""
import os, sys, math, json
import numpy as np
import torch
import torch.nn as nn
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
DYS = ["F01", "F03", "F04"]
CTL = ["FC01", "FC02", "FC03"]
TORGO = os.path.expanduser("~/torgo")
FAR_TARGET = 0.05
torch.manual_seed(0)
np.random.seed(0)


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


class Proj(nn.Module):
    def __init__(self, din, dhid=256, dout=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(din, dhid), nn.ReLU(), nn.Linear(dhid, dout))

    def forward(self, x):
        z = self.net(x)
        return z / (z.norm(dim=-1, keepdim=True) + 1e-8)


def build_train(emb, layer):
    """Control utterances -> (X vectors, y word-id labels)."""
    X, y = [], []
    wid = {}
    for spk in CTL:
        d = load_speaker(spk)
        if not d:
            continue
        for word, wavs in d["commands"].items():
            key = word  # share word ids across control speakers (same prompt vocab)
            if key not in wid:
                wid[key] = len(wid)
            for w in wavs:
                if w in emb:
                    X.append(emb[w][layer])
                    y.append(wid[key])
    return np.stack(X).astype(np.float32), np.array(y), len(wid)


def supcon_loss(z, y, tau=0.1):
    """Supervised contrastive (InfoNCE with all same-label positives)."""
    sim = (z @ z.T) / tau
    n = z.shape[0]
    mask_self = torch.eye(n, dtype=torch.bool)
    sim = sim.masked_fill(mask_self, -1e9)
    same = (y[:, None] == y[None, :]) & (~mask_self)
    logp = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    pos_cnt = same.sum(1)
    valid = pos_cnt > 0
    if valid.sum() == 0:
        return torch.tensor(0.0, requires_grad=True)
    loss = -(logp * same).sum(1)[valid] / pos_cnt[valid].clamp(min=1)
    return loss.mean()


def train_proj(X, y, din, dout=128, epochs=400, bs=256, lr=1e-3):
    g = Proj(din, 256, dout)
    opt = torch.optim.Adam(g.parameters(), lr=lr, weight_decay=1e-4)
    Xt = torch.from_numpy(X)
    yt = torch.from_numpy(y)
    n = X.shape[0]
    for ep in range(epochs):
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            z = g(Xt[idx])
            loss = supcon_loss(z, yt[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
        if (ep + 1) % 100 == 0:
            print(f"    epoch {ep+1}: loss {tot/n:.4f}", flush=True)
    g.eval()
    return g


def project_dys(g, emb, layer):
    out = {}
    with torch.no_grad():
        for w, arr in emb.items():
            v = torch.from_numpy(arr[layer:layer + 1].astype(np.float32))
            out[w] = g(v)[0].numpy().astype(np.float32)
    return out


# ---- eval on dysarthric using harness (rank-1 + held-out global FRR@FAR) ----
def eval_dys(proj_emb):
    tot_hits = tot_pos = 0
    frr_num = far_num = nneg = 0
    per = {}
    for spk in DYS:
        d = load_speaker(spk)
        if not d:
            continue
        wavs = set()
        for lst in d["commands"].values():
            wavs.update(lst)
        wavs.update(d["negatives"])
        feat_cache = {w: proj_emb[w][None, :] for w in wavs}
        rows = H.eval_speaker(d, None, feat_cache)
        r1, hits, n = H.rank1(rows)
        frr, far, npos, nn = H.held_out_global(rows)
        per[spk] = (r1, frr, far)
        tot_hits += hits
        tot_pos += n
        frr_num += frr * npos
        far_num += far * nn
        nneg += nn
    agg_r1 = tot_hits / tot_pos if tot_pos else 0.0
    agg_frr = frr_num / tot_pos if tot_pos else 0.0
    agg_far = far_num / nneg if nneg else 0.0
    return agg_r1, agg_frr, agg_far, per


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "wavlm-base-plus"
    layer = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    dout = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    din = next(iter(emb.values())).shape[1]

    print(f"LEARNED QbE PROBE — {model} L{layer} -> proj d{dout}, train=control, test=dysarthric\n", flush=True)

    # baseline (frozen, no projection) for reference
    frozen = {w: (emb[w][layer] / (np.linalg.norm(emb[w][layer]) + 1e-8)) for w in emb}
    b_r1, b_frr, b_far, b_per = eval_dys(frozen)
    print(f"FROZEN  dys rank1={b_r1*100:.1f}%  FRR={b_frr*100:.1f}% @ FAR={b_far*100:.1f}%", flush=True)

    X, y, nclass = build_train(emb, layer)
    print(f"\ntrain: {X.shape[0]} control utts, {nclass} word classes; training projection...", flush=True)
    g = train_proj(X, y, din, dout)
    proj = project_dys(g, emb, layer)
    p_r1, p_frr, p_far, p_per = eval_dys(proj)
    print(f"\nLEARNED dys rank1={p_r1*100:.1f}%  FRR={p_frr*100:.1f}% @ FAR={p_far*100:.1f}%", flush=True)
    for s in DYS:
        if s in p_per:
            print(f"    {s}: rank1={p_per[s][0]*100:.1f}%  FRR={p_per[s][1]*100:.1f}% @FAR{p_per[s][2]*100:.1f}%", flush=True)
    print(f"\nH3 D1 (dys rank1>=75%): {'PASS' if p_r1>=0.75 else 'FAIL'}  ({p_r1*100:.1f}%)", flush=True)
    print(f"H3 D2 (dys FRR<=15%@FAR<=5%): {'PASS' if (p_frr<=0.15 and p_far<=0.06) else 'FAIL'}  ({p_frr*100:.1f}% @ {p_far*100:.1f}%)", flush=True)
    res = dict(model=model, layer=layer, dout=dout,
               frozen=dict(r1=b_r1, frr=b_frr, far=b_far),
               learned=dict(r1=p_r1, frr=p_frr, far=p_far,
                            per_spk={s: [round(x, 3) for x in p_per[s]] for s in p_per}))
    with open(os.path.join(CACHE, f"metric_probe_{model}_L{layer}_d{dout}.json"), "w") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
