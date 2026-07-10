"""C15 — Learned layer-mix probe (SUPERB-style scalar weights over cached SSL layers).

The report/X1 currently GUESSES which wavlm-large layers to distill from (L15 used; L10+L14 mooted). C15
learns softmax scalar weights over ALL 25 cached layers under a separability objective and asks: does a
learned mix beat the best single layer, and which layers carry the weight? Tells X1 what to distill.

METHOD (cached, no model forward): per control speaker, few-shot leave-one-out genuine pairs + in-vocab
impostor pairs. Layer-mixed embedding v(q) = normalize(sum_l softmax(theta)_l * emb[q][l]). Optimize
theta on TRAIN speakers to maximize a soft-separability (logistic margin) loss; evaluate held-out D2
FRR@FAR<=5% on TEST speaker (leave-one-speaker-out). Compare vs best single layer.

PRE-REGISTERED GATE: learned-mix held-out FRR beats the best-single-layer held-out FRR by >= 2 pp
(typical). Report the top-weighted layers regardless (informative for X1).
"""
import os, json
import numpy as np
import torch
import cand_lib as L

LAYER_GUESS = 15
FAR = 0.05


def speaker_layer_tensors(spk, emb):
    """Return (Q, T_list, N) where Q[i]=(all-layer query (25,1024)), with few-shot leave-one-out enroll
    handled at scoring time. Simpler: return per-word rep stacks + negatives as (n,25,1024)."""
    d = L.load_speaker(spk)
    from held_out_d2 import distinct_subset
    keep = distinct_subset(d, emb, LAYER_GUESS, 25)
    words = {w: np.stack([emb[x] for x in d["commands"][w] if x in emb]) for w in keep}
    words = {w: v for w, v in words.items() if v.shape[0] >= 2}
    negs = np.stack([emb[x] for x in d["negatives"] if x in emb]) if any(x in emb for x in d["negatives"]) else None
    return words, negs


def mixed(vecs_25, theta):
    """vecs_25: (...,25,1024) torch; theta: (25,). Return unit (...,1024)."""
    w = torch.softmax(theta, 0)
    v = (vecs_25 * w[:, None]).sum(-2)
    return v / (v.norm(dim=-1, keepdim=True) + 1e-8)


def genuine_impostor_dists(words, negs, theta):
    """Differentiable genuine (leave-one-out min) + impostor (min over words) distances at mix theta."""
    gen, imp = [], []
    word_t = {w: torch.tensor(v, dtype=torch.float32) for w, v in words.items()}
    mixed_templ = {w: mixed(t, theta) for w, t in word_t.items()}  # (n,1024)
    for w, t in word_t.items():
        mt = mixed_templ[w]
        for i in range(mt.shape[0]):
            q = mt[i]
            rest = torch.cat([mt[:i], mt[i + 1:]], 0)
            gen.append((1 - rest @ q).min())
    if negs is not None:
        nt = mixed(torch.tensor(negs, dtype=torch.float32), theta)  # (m,1024)
        for j in range(nt.shape[0]):
            q = nt[j]
            best = min((1 - mixed_templ[w] @ q).min() for w in mixed_templ)
            imp.append(best)
    return torch.stack(gen), (torch.stack(imp) if imp else None)


def held_out_frr(gen, imp, target=FAR):
    g = np.sort(gen); im = np.sort(imp)
    k = int(target * len(im))
    thr = im[k] if k < len(im) else im[-1] + 1
    return float((g > thr).mean())


def main():
    emb = L.load_emb("wavlm-large")
    torch.manual_seed(0)
    print("C15 — learned layer-mix vs best single layer (typical, wavlm-large 25 layers)\n", flush=True)
    data = {s: speaker_layer_tensors(s, emb) for s in L.CTL}
    data = {s: d for s, d in data.items() if d[1] is not None and len(d[0]) >= 3}

    # best single layer (held-out via leave-one-speaker-out, pick layer minimizing mean test FRR)
    layer_frr = {}
    for Lyr in range(25):
        theta = torch.full((25,), -20.0); theta[Lyr] = 20.0  # ~one-hot
        frrs = []
        for s in data:
            g, im = genuine_impostor_dists(data[s][0], data[s][1], theta)
            frrs.append(held_out_frr(g.detach().numpy(), im.detach().numpy()))
        layer_frr[Lyr] = float(np.mean(frrs))
    best_layer = min(layer_frr, key=layer_frr.get)
    print(f"  best single layer = L{best_layer}: mean FRR={layer_frr[best_layer]*100:.1f}%  (L15={layer_frr[15]*100:.1f}%)", flush=True)

    # learned mix: leave-one-speaker-out
    test_frrs = []
    theta_final = None
    for test in data:
        theta = torch.zeros(25, requires_grad=True)
        opt = torch.optim.Adam([theta], lr=0.2)
        train = [s for s in data if s != test]
        for it in range(150):
            opt.zero_grad()
            loss = 0.0
            for s in train:
                g, im = genuine_impostor_dists(data[s][0], data[s][1], theta)
                # soft separability: want genuine small, impostor large -> logistic margin
                margin = im.mean() - g.mean()
                loss = loss - margin + 0.1 * g.mean()
            loss.backward(); opt.step()
        g, im = genuine_impostor_dists(data[test][0], data[test][1], theta.detach())
        test_frrs.append(held_out_frr(g.numpy(), im.numpy()))
        theta_final = theta.detach()
    mix_frr = float(np.mean(test_frrs))
    w = torch.softmax(theta_final, 0).numpy()
    top = np.argsort(w)[::-1][:5]
    print(f"  learned mix: held-out FRR={mix_frr*100:.1f}%   top layers={[int(l) for l in top]} weights={[round(float(w[l]),2) for l in top]}", flush=True)
    gate = (layer_frr[best_layer] - mix_frr) * 100 >= 2.0
    print(f"\n  GATE (learned mix beats best single layer by >=2pp): "
          f"{layer_frr[best_layer]*100:.1f}% -> {mix_frr*100:.1f}%  => {'PASS' if gate else 'no material gain'}", flush=True)
    with open(os.path.join(L.CACHE, "c15_layermix.json"), "w") as f:
        json.dump({"best_layer": int(best_layer), "best_layer_frr": layer_frr[best_layer],
                   "mix_frr": mix_frr, "top_layers": [int(l) for l in top],
                   "top_weights": [float(w[l]) for l in top], "layer_frr": layer_frr}, f, indent=2)


if __name__ == "__main__":
    main()
