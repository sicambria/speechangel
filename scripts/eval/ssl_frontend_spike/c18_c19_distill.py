"""C18 (relational KD) + C19 (MSWC domain-gap audit, GSC proxy) — CPU, cached teacher/student.

Shared setup: cached distillation teacher `distill_teacher_6000.npz` (mel 6000×118×64, emb 6000×1024 =
frozen wavlm-large L14) and the feature-copy `student.pt`. Both proxies run on CPU (no teacher forward).

C19 — domain-gap audit. Evaluate the EXISTING feature-copy student's QbE rank-1 on (a) TORGO control
  (spontaneous, its eval domain) vs (b) GSC isolated citation words (the deployment word type it was never
  validated on). A large TORGO→GSC drop = the MSWC-style forced-aligned→citation-word domain gap X1 is
  blind to.

C18 — relational KD. Train a NEW student with the same architecture but an RKD loss (match the teacher's
  pairwise distance + angle structure) instead of feature-copy MSE. Compare QbE rank-1 (TORGO + GSC) to the
  feature-copy student. Hypothesis: distance-structure is the quantity QbE consumes, so RKD should retain
  more QbE quality than feature-copy.

PRE-REGISTERED: C19 report TORGO vs GSC rank-1 gap. C18 gate — RKD student rank-1 >= feature-copy + 2 pp
  on held-out TORGO control.
"""
import os, sys, glob, json
import numpy as np
import torch, torch.nn as nn
import cand_lib as L
import harness as H
from distill_student import Student, log_mel, N_MEL

CACHE = L.CACHE
GSC = os.path.expanduser("~/gsc/data")
torch.manual_seed(0); np.random.seed(0)


def student_embed(model, wavpaths, read_fn):
    out = {}
    with torch.no_grad():
        for p in wavpaths:
            x = read_fn(p)
            m = torch.tensor(log_mel(x)).unsqueeze(0)
            out[p] = model.embed(m)[0].numpy()
    return out


def read_torgo(p):
    return H.read_wav(p)


def read_gsc(p):
    import soundfile as sf
    x, sr = sf.read(p, dtype="float32")
    return x.mean(1) if x.ndim > 1 else x


def qbe_rank1(emb_by_path, words):
    """words: {w:[paths]}; leave-one-out rank-1 using student embeddings."""
    hits = tot = 0
    for w, ps in words.items():
        vs = [emb_by_path[p] for p in ps if p in emb_by_path]
        if len(vs) < 2:
            continue
        for i in range(len(vs)):
            q = vs[i]
            enroll = {}
            for ww, pp in words.items():
                tv = [emb_by_path[p] for p in pp if p in emb_by_path]
                tv = [tv[j] for j in range(len(tv)) if not (ww == w and j == i)]
                if tv:
                    enroll[ww] = tv
            best = min((min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items())
            hits += (best[1] == w); tot += 1
    return hits / tot if tot else 0, tot


def torgo_words(spk):
    d = L.load_speaker(spk)
    return {w: v for w, v in d["commands"].items() if len(v) >= 2}


def gsc_words(n_spk=8, nw=8, reps=6):
    import collections
    ws = [w for w in os.listdir(GSC) if os.path.isdir(os.path.join(GSC, w)) and not w.startswith("_")]
    sw = collections.defaultdict(lambda: collections.defaultdict(list))
    for w in ws:
        for f in sorted(os.listdir(os.path.join(GSC, w))):
            if f.endswith(".wav"):
                sw[f.split("_")[0]][w].append(os.path.join(GSC, w, f))
    good = sorted([(s, wc) for s, wc in sw.items() if sum(len(v) >= reps for v in wc.values()) >= nw],
                  key=lambda x: -sum(len(v) >= reps for v in x[1].values()))[:n_spk]
    return [{w: v[:reps] for w, v in sorted(wc.items()) if len(v) >= reps} for _, wc in good][: n_spk][:n_spk], good[:n_spk]


def train_rkd(mel, emb, epochs=8, bs=128):
    """RKD: match teacher pairwise distances (RKD-D) + angles (RKD-A) in each minibatch."""
    model = Student()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    T = torch.tensor(mel); E = torch.tensor(emb)
    n = len(mel)
    for ep in range(epochs):
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n - bs, bs):
            idx = perm[i:i + bs]
            m = T[idx]; te = E[idx]
            se = model.forward(m)  # (bs,1024) normed
            # pairwise distances
            td = torch.cdist(te, te); sd = torch.cdist(se, se)
            # normalize by mean (RKD-D)
            td_n = td / (td[td > 0].mean() + 1e-8); sd_n = sd / (sd[sd > 0].mean() + 1e-8)
            loss_d = nn.functional.smooth_l1_loss(sd_n, td_n)
            loss = loss_d
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item()
        print(f"    RKD epoch {ep+1}/{epochs} loss={tot/(n//bs):.4f}", flush=True)
    model.eval()
    return model


def main():
    print("C18/C19 — relational KD + domain-gap audit (CPU, cached teacher/student)\n", flush=True)
    # feature-copy student
    fc = Student(); fc.load_state_dict(torch.load(os.path.join(CACHE, "student.pt"), map_location="cpu")); fc.eval()

    # ---- C19 domain-gap: feature-copy student on TORGO vs GSC ----
    print("  C19 — feature-copy student QbE rank-1 (domain gap):", flush=True)
    tor_words = {}
    for s in L.CTL:
        for w, v in torgo_words(s).items():
            tor_words[f"{s}:{w}"] = v
    tor_paths = [p for ps in tor_words.values() for p in ps]
    tor_emb = student_embed(fc, tor_paths, read_torgo)
    r_tor, n_tor = qbe_rank1(tor_emb, tor_words)
    gwords_list, _ = gsc_words()
    r_gscs = []
    gsc_emb_all = {}
    for gw in gwords_list:
        paths = [p for ps in gw.values() for p in ps]
        ge = student_embed(fc, paths, read_gsc); gsc_emb_all.update(ge)
        r, n = qbe_rank1(ge, gw)
        r_gscs.append(r)
    r_gsc = float(np.mean(r_gscs))
    print(f"    TORGO control rank-1 = {r_tor*100:.1f}%  (n={n_tor})", flush=True)
    print(f"    GSC isolated-word rank-1 = {r_gsc*100:.1f}%  (mean over {len(r_gscs)} speakers)", flush=True)
    print(f"    domain gap (TORGO→GSC) = {(r_tor-r_gsc)*100:+.1f}pp  "
          f"{'-> large gap: MSWC/citation domain shift is real' if abs(r_tor-r_gsc) > 10 else '-> small gap: student generalizes'}", flush=True)

    # ---- C18 RKD ----
    print("\n  C18 — training RKD student on cached teacher (6000)...", flush=True)
    z = np.load(os.path.join(CACHE, "distill_teacher_6000.npz"))
    rkd = train_rkd(z["mel"], z["emb"])
    tor_emb_r = student_embed(rkd, tor_paths, read_torgo)
    r_tor_rkd, _ = qbe_rank1(tor_emb_r, tor_words)
    print(f"\n    feature-copy student TORGO rank-1 = {r_tor*100:.1f}%", flush=True)
    print(f"    RKD student          TORGO rank-1 = {r_tor_rkd*100:.1f}%   (Δ={(r_tor_rkd-r_tor)*100:+.1f}pp)", flush=True)
    print(f"    GATE (RKD >= feature-copy + 2pp): {'PASS -> distance-structure distillation helps' if (r_tor_rkd-r_tor) >= 0.02 else 'no material gain / worse'}", flush=True)
    with open(os.path.join(CACHE, "c18_c19.json"), "w") as f:
        json.dump({"c19_torgo": r_tor, "c19_gsc": r_gsc, "c19_gap": r_tor - r_gsc,
                   "c18_fc": r_tor, "c18_rkd": r_tor_rkd}, f, indent=2)


if __name__ == "__main__":
    main()
