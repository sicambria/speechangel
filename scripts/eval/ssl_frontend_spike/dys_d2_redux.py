"""Dysarthric D2 re-score with DEPLOYMENT-REAL negatives (A2 follow-through).

The banked dysarthric D2 (~50% FRR@FAR<=5%) uses same-speaker IN-VOCAB OOV confusors — the hardest
possible negatives. A2 showed dys separability vs real deployment negatives is far higher (AUC 0.99 vs
ambient). This splits D2 into the two distinct questions it was conflating and re-scores each honestly:

  D2-reject  (idle false-accept resistance): FRR@FAR<=5% vs the negatives that actually fire in deployment
             — ambient (DEMAND) and other-speaker speech. This is the metric that sets the running threshold.
  D2-confuse (command substitution among the user's OWN enrolled words): FRR@FAR<=5% vs in-vocab confusors.
             This is a DIFFERENT failure (say wrong command → wrong action), attacked by vocab-distinct
             command selection, NOT by the idle-reject threshold.

Reports both, with ALL-commands and vocab-distinct<=25 command sets, wavlm-large L15, few-shot held-out.
Honest banding: the deployment composite's D2 axis is D2-reject (ambient/other-speaker) with a speaker gate
(D25); in-vocab confusion is scored separately as D14. No laundering — every negative set is reported.
"""
import os, sys, glob, json, wave
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from held_out_d2 import distinct_subset

LAYER = 15; SR = 16000; FAR = 0.05
PV = os.path.expanduser("~/picovoice-benchmark")
AMB_CACHE = os.path.join(L.CACHE, "dys_redux_ambient.npz")
np.random.seed(3)


def band(frr):
    return 900 if frr <= 0.10 else (800 if frr <= 0.15 else (700 if frr <= 0.35 else (600 if frr <= 0.55 else 500)))


def embed_pool(net, paths, maxs=3.0):
    out = []
    for p in paths:
        x, sr = sf.read(p, dtype="float32")
        if x.ndim > 1:
            x = x.mean(1)
        if sr != SR:
            n = int(len(x) * SR / sr); x = np.interp(np.linspace(0, len(x), n, endpoint=False), np.arange(len(x)), x).astype(np.float32)
        x = x[: int(maxs * SR)]
        sp = H.energy_vad_trim(x)
        if sp.size < 1520:
            sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
        w = (sp - sp.mean()) / (sp.std() + 1e-7)
        h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
        v = h.mean(0); out.append((v / (np.linalg.norm(v) + 1e-8)).astype(np.float32))
    return out


def ambient_pool():
    if os.path.exists(AMB_CACHE):
        z = np.load(AMB_CACHE); return [z[k] for k in z.files]
    from transformers import AutoModel
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    dem = glob.glob(os.path.join(PV, "demand", "*", "ch01.wav"))
    paths = []
    for f in dem[:10]:
        paths.append(f)  # embed_pool slices first 3s; use several environments
    print(f"  embedding {len(paths)} DEMAND ambient clips (wavlm-large L{LAYER})...", flush=True)
    pool = embed_pool(net, paths)
    np.savez(AMB_CACHE, *pool)
    return pool


def dys_genuine(emb, spk, distinct):
    d = L.load_speaker(spk)
    if distinct:
        keep = distinct_subset(d, emb, LAYER, 25)
        words = {w: [emb[x][LAYER] for x in d["commands"][w] if x in emb] for w in keep}
    else:
        words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    gen = []
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            gen.append(min(1 - float(q @ t) for t in rest))
    enroll = {w: vs for w, vs in words.items()}
    return np.array(gen), enroll


def imp_dists(enroll, negvecs):
    return np.array([min(min(1 - float(nv @ t) for t in tt) for tt in enroll.values()) for nv in negvecs])


def frr_at_far(gen, imp, far=FAR):
    if len(imp) == 0 or len(gen) == 0:
        return None
    thr = np.sort(imp)[max(0, int(far * len(imp)) - 1)]
    return float((gen > thr).mean())


def main():
    emb = L.load_emb("wavlm-large")
    amb = ambient_pool()
    print(f"\nDYSARTHRIC D2 RE-SCORE (deployment-real negatives) — wavlm-large L{LAYER}\n", flush=True)
    # pooled dys genuine + per-negative-set FRR
    for distinct in [False, True]:
        tag = "vocab-distinct<=25" if distinct else "ALL commands"
        gen_all, inv_all, osw_all, ooov_all, amb_all = [], [], [], [], []
        for spk in L.DYS:
            gen, enroll = dys_genuine(emb, spk, distinct)
            if gen.size == 0:
                continue
            d = L.load_speaker(spk)
            enrolled_words = set(enroll)
            invocab = [emb[x][LAYER] for x in d["negatives"] if x in emb]
            # other-speaker utts split same-word vs OOV (all other TORGO speakers, cached)
            osame, oother = [], []
            for o in [s for s in (L.DYS + L.CTL) if s != spk]:
                od = L.load_speaker(o)
                if not od:
                    continue
                for w, wavs in od["commands"].items():
                    for x in wavs:
                        if x in emb:
                            (osame if w in enrolled_words else oother).append(emb[x][LAYER])
            gen_all.append(gen)
            inv_all.append(imp_dists(enroll, invocab))
            osw_all.append(imp_dists(enroll, osame))
            ooov_all.append(imp_dists(enroll, oother))
            amb_all.append(imp_dists(enroll, amb))
        G = np.concatenate(gen_all)
        sets = {"in-vocab confusor (D2-confuse)": np.concatenate(inv_all),
                "other-spk SAME-word": np.concatenate(osw_all),
                "other-spk OOV": np.concatenate(ooov_all),
                "ambient DEMAND (D2-reject)": np.concatenate(amb_all)}
        print(f"  [{tag}]  (n_genuine={G.size})", flush=True)
        for name, imp in sets.items():
            frr = frr_at_far(G, imp)
            print(f"    vs {name:32s}: FRR@FAR5%={frr*100:5.1f}%  -> band {band(frr)}  (n_imp={imp.size})", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
