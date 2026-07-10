"""C14 — Frozen-feature episodic-head ceiling probe (tests I1's premise, CPU, cached embeddings).

I1 claims a small metric head trained episodically over FROZEN SSL features recovers most of the gain —
i.e. the objective, not encoder capacity, is the gap. C14 tests this on cached GSC-24 wavlm-large L15
embeddings (real speaker-n, so no n=3 over-fit trap like C15): train a projection head (1024→256) with a
prototypical/triplet episodic loss on a TRAIN split of GSC speakers, evaluate held-out D2 FRR@FAR≤5% on
(a) held-out GSC speakers and (b) TORGO control — vs raw-L15 cosine (no head).

PRE-REGISTERED GATE: head improves held-out D2 FRR by ≥2 pp on BOTH held-out GSC AND TORGO control (an
improvement that transfers, not memorized). Else -> frozen-feature head does not recover I1's gain here.
"""
import os, json
import numpy as np
import torch, torch.nn as nn
import cand_lib as L
import a5_gsc_kcurve as A5
from b_single import build_rows

LAYER = 15
torch.manual_seed(0); np.random.seed(0)


class Head(nn.Module):
    def __init__(self, d_in=1024, d=256):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, d), nn.ReLU(), nn.Linear(d, d))

    def forward(self, x):
        z = self.net(x)
        return z / (z.norm(dim=-1, keepdim=True) + 1e-8)


def episodic_train(train_words_per_spk, epochs=30):
    """Prototypical episodes: each episode sample N words from one speaker, split reps support/query."""
    head = Head(); opt = torch.optim.Adam(head.parameters(), lr=1e-3)
    speakers = list(train_words_per_spk)
    for ep in range(epochs):
        tot = 0.0; nb = 0
        rng = np.random.RandomState(ep)
        for spk in speakers:
            words = train_words_per_spk[spk]
            ws = [w for w in words if len(words[w]) >= 4]
            if len(ws) < 4:
                continue
            pick = rng.choice(ws, min(5, len(ws)), replace=False)
            protos, queries, qlab = [], [], []
            for k, w in enumerate(pick):
                vs = words[w]; idx = rng.permutation(len(vs))
                sup = torch.tensor(np.stack([vs[j] for j in idx[:2]]))
                qy = torch.tensor(np.stack([vs[j] for j in idx[2:4]]))
                protos.append(head(sup).mean(0)); queries.append(head(qy)); qlab += [k, k]
            P = torch.stack(protos); Q = torch.cat(queries); y = torch.tensor(qlab)
            logits = -torch.cdist(Q, P)  # (nq, nclass)
            loss = nn.functional.cross_entropy(logits, y)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item(); nb += 1
        if (ep + 1) % 10 == 0:
            print(f"    ep {ep+1}: loss={tot/max(nb,1):.3f}", flush=True)
    head.eval()
    return head


def apply_head(emb_layer_dict, head):
    """emb: {wav:(25,1024)} -> {wav: headed L15 unit vec} wrapper matching build_rows' emb[x][layer]."""
    class Wrap:
        def __init__(self, base, head):
            self.base = base; self.head = head; self._c = {}
        def __contains__(self, k):
            return k in self.base
        def __getitem__(self, k):
            if k not in self._c:
                with torch.no_grad():
                    v = self.head(torch.tensor(self.base[k][LAYER]).unsqueeze(0))[0].numpy()
                # return a (25,1024)-like: only LAYER index is used by build_rows
                arr = np.zeros((25, v.shape[0]), dtype=np.float32); arr[LAYER] = v
                self._c[k] = arr
            return self._c[k]
    return Wrap(emb_layer_dict, head)


def d2_frr(emb_like, spks):
    num = den = 0
    for s in spks:
        r = build_rows(s, emb_like, LAYER, "min")
        if r is None:
            continue
        pr, fp, nr, fn, _ = r
        frr, far, npos, _ = L.held_out_frr_far(pr, nr, fp, fn, L.global_threshold_accept, target=0.05)
        num += frr * npos; den += npos
    return num / den if den else None


def main():
    torch.set_grad_enabled(True)  # a5_gsc_kcurve import disables grad globally; re-enable for head training
    print(f"C14 — frozen-feature episodic head (train on GSC, eval held-out GSC + TORGO), wavlm-large L{LAYER}\n", flush=True)
    # GSC embeddings (all-layer, from A5 cache)
    z = np.load(A5.CACHE, allow_pickle=True); gsc = {k: z[k] for k in z.files}
    man, _ = A5.build_cache()
    spks = list(man)
    train_spk = spks[: len(spks) * 2 // 3]; test_spk = spks[len(spks) * 2 // 3:]
    train_words = {s: {w: [gsc[p][LAYER] for p in ps] for w, ps in man[s]["fixed"].items()} for s in train_spk}
    print(f"  train {len(train_spk)} GSC speakers, held-out {len(test_spk)} GSC speakers + 3 TORGO control", flush=True)

    # baseline raw-L15 (no head) held-out D2 on GSC-test + TORGO
    def gsc_d2(emb_like, spk_subset):
        num = den = 0
        for s in spk_subset:
            words = {w: [emb_like[p] for p in ps] for w, ps in man[s]["fixed"].items()}
            negs = [emb_like[p] for p in man[s]["neg"]]
            pr, fp, nr, fn = [], [], [], []
            for w, vecs in words.items():
                for i, qv in enumerate(vecs):
                    f = i % 5; enroll = {}
                    for ww, vv in words.items():
                        pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                        if ww == w:
                            pool = [vv[j] for j in range(len(vv)) if j != i and (j % 5) != f]
                        if pool:
                            enroll[ww] = pool[:4]
                    if enroll:
                        pr.append((w, L.score_query(qv, enroll, "min"))); fp.append(f)
            for ni, nv in enumerate(negs):
                f = ni % 5; enroll = {}
                for ww, vv in words.items():
                    pool = [vv[j] for j in range(len(vv)) if (j % 5) != f]
                    if pool:
                        enroll[ww] = pool[:4]
                if enroll:
                    nr.append((None, L.score_query(nv, enroll, "min"))); fn.append(f)
            frr, far, npos, _ = L.held_out_frr_far(pr, nr, fp, fn, L.global_threshold_accept, target=0.05)
            num += frr * npos; den += npos
        return num / den if den else None

    # raw layer accessor for GSC (p -> vec)
    raw_gsc = {p: gsc[p][LAYER] for s in man for p in ([q for ps in man[s]["fixed"].values() for q in ps] + man[s]["neg"])}
    base_gsc = gsc_d2(raw_gsc, test_spk)
    base_tor = d2_frr(L.load_emb("wavlm-large"), L.CTL)
    print(f"\n  BASELINE raw-L15: held-out GSC D2={base_gsc*100:.1f}%  TORGO-ctl D2={base_tor*100:.1f}%", flush=True)

    print("  training episodic head...", flush=True)
    head = episodic_train(train_words)
    headed_gsc = {p: head(torch.tensor(v).unsqueeze(0)).detach()[0].numpy() for p, v in raw_gsc.items()}
    h_gsc = gsc_d2(headed_gsc, test_spk)
    h_tor = d2_frr(apply_head(L.load_emb("wavlm-large"), head), L.CTL)
    print(f"  HEADED         : held-out GSC D2={h_gsc*100:.1f}%  TORGO-ctl D2={h_tor*100:.1f}%", flush=True)
    gate = (base_gsc - h_gsc) >= 0.02 and (base_tor - h_tor) >= 0.02
    print(f"\n  GATE (head improves BOTH held-out GSC & TORGO by >=2pp): "
          f"GSC Δ={(base_gsc-h_gsc)*100:+.1f}pp TORGO Δ={(base_tor-h_tor)*100:+.1f}pp "
          f"=> {'PASS -> frozen-feature head recovers gain (I1 premise supported)' if gate else 'FAIL -> head does not transfer (objective is not the gap here)'}", flush=True)
    with open(os.path.join(L.CACHE, "c14_episodic.json"), "w") as f:
        json.dump({"base_gsc": base_gsc, "base_tor": base_tor, "head_gsc": h_gsc, "head_tor": h_tor}, f, indent=2)


if __name__ == "__main__":
    main()
