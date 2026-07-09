"""Learned nonlinear pairwise VERIFIER — the most expressive untried admissible D2 lever.

Every prior D2 result scores a (query, template) pair by COSINE DISTANCE of embeddings (a fixed
bilinear function). This tests a strictly larger hypothesis class: a small MLP that takes the pair
interaction features [q*t, |q-t|] and outputs a learned same/different score. If dysarthric same-word
vs different-word pairs are separable by ANY function of the embeddings, this finds it; cosine is one
special case. Ships frozen, <1MB, deterministic, 1-shot enrollment unchanged -> admissible.

This directly validates (not assumes) the load-bearing claim "AUC ~0.70 is representation-and-decision
invariant." If the learned verifier's dysarthric AUC jumps past ~0.80, the D2 wall is softer than the
cosine measurements implied and I reassess. If it caps at ~0.70, the wall is confirmed at the strongest
admissible decision function.

Pre-registered H6 (ONE hypothesis): a LOSO-trained pairwise verifier (train control+2 dys, test
held-out dys) reaches held-out dysarthric FRR <= 0.15 @ FAR <= 5% and/or genuine/impostor AUC >= 0.80.

Reuses cached wavlm-large mean-pool embeddings. torch CPU, deterministic seed.
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
torch.manual_seed(0); np.random.seed(0)


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


class Verifier(nn.Module):
    def __init__(self, d, h=256):
        super().__init__()
        # input = [q*t, |q-t|] -> 2d ; genuine score (higher = more same)
        self.net = nn.Sequential(nn.Linear(2 * d, h), nn.ReLU(), nn.Linear(h, h), nn.ReLU(),
                                 nn.Linear(h, 1))

    def pair_feat(self, q, t):
        return torch.cat([q * t, (q - t).abs()], dim=-1)

    def forward(self, q, t):
        return self.net(self.pair_feat(q, t)).squeeze(-1)


def emb_words(emb, layer, spk):
    d = load_speaker(spk)
    return {w: [emb[x][layer] for x in wavs if x in emb] for w, wavs in d["commands"].items()}


def build_pairs(emb, layer, speakers, n_imp_per_gen=2):
    """genuine (same-word) + impostor (diff-word) pairs across speakers."""
    Q, T, Y = [], [], []
    for spk in speakers:
        words = emb_words(emb, layer, spk)
        words = {w: v for w, v in words.items() if len(v) >= 2}
        allw = list(words)
        for w, vs in words.items():
            for i in range(len(vs)):
                for j in range(len(vs)):
                    if i == j:
                        continue
                    Q.append(vs[i]); T.append(vs[j]); Y.append(1.0)
                # impostor pairs
                others = [w2 for w2 in allw if w2 != w]
                np.random.shuffle(others)
                for w2 in others[: n_imp_per_gen * max(1, len(vs) - 1)]:
                    T2 = words[w2][np.random.randint(len(words[w2]))]
                    Q.append(vs[i]); T.append(T2); Y.append(0.0)
    return (np.stack(Q).astype(np.float32), np.stack(T).astype(np.float32),
            np.array(Y, dtype=np.float32))


def train_verifier(Q, T, Y, d, epochs=120, bs=512, lr=1e-3):
    g = Verifier(d)
    opt = torch.optim.Adam(g.parameters(), lr=lr, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss()
    Qt, Tt, Yt = torch.from_numpy(Q), torch.from_numpy(T), torch.from_numpy(Y)
    n = Q.shape[0]
    for ep in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            s = g(Qt[idx], Tt[idx])
            loss = lossf(s, Yt[idx])
            opt.zero_grad(); loss.backward(); opt.step()
    g.eval()
    return g


def eval_speaker_verifier(g, emb, layer, spk, k=5):
    """held-out folds; command score = MAX verifier logit over that command's templates."""
    d = load_speaker(spk)
    rows = []
    with torch.no_grad():
        for fold in H.folds(d, k):
            enroll = {}
            for w, wav in fold["enroll"]:
                enroll.setdefault(w, []).append(emb[wav][layer])
            def score(qwav):
                q = torch.from_numpy(emb[qwav][layer][None, :])
                best = []
                for w, vs in enroll.items():
                    tt = torch.from_numpy(np.stack(vs))
                    ss = g(q.expand(len(vs), -1), tt)
                    best.append((float(ss.max()), w))
                best.sort(key=lambda x: -x[0])  # higher = more genuine
                return best
            for w, wav in fold["positives"]:
                rows.append((fold["index"], w, score(wav)))
            for wav in fold["negatives"]:
                rows.append((fold["index"], None, score(wav)))
    # rank-1
    pos = [r for r in rows if r[1] is not None]
    r1 = sum(1 for r in pos if r[2] and r[2][0][1] == r[1]) / len(pos) if pos else 0
    # held-out FRR@FAR<=5% on the top score (higher accepts)
    fids = sorted({r[0] for r in rows})
    acc = p = fa = ne = 0
    genuine_top, impostor_top = [], []
    for f in fids:
        tr = [r for r in rows if r[0] != f]; te = [r for r in rows if r[0] == f]
        cs = sorted({r[2][0][0] for r in tr if r[2]}, reverse=True)
        thr = cs[0] + 1 if cs else 0
        negs = [r for r in tr if r[1] is None]
        for t in cs:
            far = sum(1 for r in negs if r[2] and r[2][0][0] >= t) / len(negs) if negs else 0
            if far <= FAR_TARGET:
                thr = t
        for r in te:
            ok = bool(r[2]) and r[2][0][0] >= thr
            if r[1] is not None:
                p += 1
                if ok and r[2][0][1] == r[1]:
                    acc += 1
                genuine_top.append(r[2][0][0])
            else:
                ne += 1
                if ok:
                    fa += 1
                impostor_top.append(r[2][0][0])
    frr = 1 - acc / p if p else 0
    far = fa / ne if ne else 0
    g_, im_ = np.array(genuine_top), np.array(impostor_top)
    auc = float(np.mean(g_[:, None] > im_[None, :])) if g_.size and im_.size else 0
    return r1, frr, far, auc, p, ne


def main():
    model = "wavlm-large"
    layer = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    d = next(iter(emb.values())).shape[1]
    print(f"LEARNED PAIRWISE VERIFIER (LOSO) — {model} L{layer}\n", flush=True)
    tot = dict(r1n=0, frn=0, p=0, fa=0, ne=0)
    allg = []
    for test_spk in DYS:
        train = CTL + [s for s in DYS if s != test_spk]
        Q, T, Y = build_pairs(emb, layer, train)
        g = train_verifier(Q, T, Y, d)
        r1, frr, far, auc, p, ne = eval_speaker_verifier(g, emb, layer, test_spk)
        print(f"  test {test_spk}: rank1={r1*100:.1f}%  FRR={frr*100:.1f}% @FAR{far*100:.1f}%  AUC={auc:.3f}", flush=True)
        tot["r1n"] += round(r1 * p); tot["frn"] += round((1 - frr) * p) if False else 0
        tot["p"] += p; tot["fa"] += round(far * ne); tot["ne"] += ne
        tot.setdefault("frr_num", 0); tot["frr_num"] += frr * p
        allg.append(auc)
    agg_frr = tot["frr_num"] / tot["p"] if tot["p"] else 0
    agg_far = tot["fa"] / tot["ne"] if tot["ne"] else 0
    print(f"\nDYS AGG: FRR={agg_frr*100:.1f}% @FAR{agg_far*100:.1f}%  mean per-spk AUC={np.mean(allg):.3f}", flush=True)
    print(f"H6 D2 (FRR<=15%): {'PASS' if agg_frr<=0.15 else 'FAIL'}   AUC>=0.80: {'YES' if np.mean(allg)>=0.80 else 'NO'}", flush=True)
    print(f"(cosine-embedding reference: AUC ~0.70, FRR ~55%)", flush=True)
    with open(os.path.join(CACHE, f"verifier_d2_{model}_L{layer}.json"), "w") as f:
        json.dump(dict(agg_frr=agg_frr, agg_far=agg_far, mean_auc=float(np.mean(allg))), f, indent=2)


if __name__ == "__main__":
    main()
