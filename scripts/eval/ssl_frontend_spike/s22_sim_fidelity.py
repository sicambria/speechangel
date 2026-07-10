"""S22 — two-sided, non-circular FIDELITY GATE for the dysarthric simulator.

Reuses the existing waveform-domain first-principles simulator (`dysarthria_sim.py`, 10 articulatory
subsystems, seeded/reproducible). Applies it to TORGO CONTROL speakers (same recording channel as real
dysarthric — cleanest comparison), re-embeds the degraded audio with wavlm-large L15, and asks whether
synthetic-dysarthric reproduces REAL dysarthric structure.

NON-CIRCULAR protocol (advisor): CALIBRATE severity on the DECISION-LEVEL metric (in-vocab D2 FRR@FAR<=5%
should land in real-TORGO's 50-57% band), THEN INDEPENDENTLY VERIFY the embedding GEOMETRY that G1 exploits
(within-word scatter ~2.5x clean, fisher ~1.0) EMERGES — do NOT tune severity on fisher/scatter. If the
geometry does not emerge at the severity that matches D2, the simulator is NOT a valid proxy for the
in-vocab wall and must not be used to (in)validate contraction levers.

Real targets (from L26/re-score, wavlm-large L15, vocab-distinct): D2 FRR 50-57%, within-word ~0.044,
fisher ~1.04, rank-1 confusion ~15-20%.
"""
import os, sys, json, time
import numpy as np
import harness as H
import cand_lib as L
from held_out_d2 import distinct_subset
from dysarthria_sim import DysarthriaSimulator

LAYER = 15; FAR = 0.05; SR = 16000
CACHE = os.path.join(L.CACHE, "s22_sim_emb.npz")
PRESETS = ["clean", "moderate", "severe", "very_severe"]


def embed_batch(net, torch, wavs_and_sev):
    """wavs_and_sev = [(wav, preset)]. Returns {(wav,preset): vec L15}. Degrade -> VAD -> wavlm L15."""
    out = {}
    sims = {p: (None if p == "clean" else DysarthriaSimulator(preset=p)) for p in PRESETS}
    t0 = time.time()
    for i, (wav, preset) in enumerate(wavs_and_sev):
        x = H.read_wav(wav)
        if sims[preset] is not None:
            x = sims[preset].apply(x)
        sp = H.energy_vad_trim(x)
        if sp.size < 1520:
            sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
        w = (sp - sp.mean()) / (sp.std() + 1e-7)
        h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
        v = h.mean(0); out[f"{wav}|{preset}"] = (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)
        if (i + 1) % 200 == 0:
            print(f"    embedded {i+1}/{len(wavs_and_sev)} ({time.time()-t0:.0f}s)", flush=True)
    return out


def build_emb():
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        return {k: z[k] for k in z.files}
    import torch
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    print("  loading wavlm-large + degrading control speakers ...", flush=True)
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    clean = L.load_emb("wavlm-large")  # to pick the distinct<=25 subset consistently
    jobs = []
    for spk in L.CTL:
        d = L.load_speaker(spk)
        keep = distinct_subset(d, clean, LAYER, 25)
        for w in keep:
            for x in d["commands"][w]:
                for p in PRESETS:
                    jobs.append((x, p))
        for x in d["negatives"][:60]:
            for p in PRESETS:
                jobs.append((x, p))
    print(f"  {len(jobs)} degrade+embed jobs ...", flush=True)
    emb = embed_batch(net, torch, jobs)
    np.savez(CACHE, **emb)
    return emb


def within_and_fisher(words):
    within, cents = [], {}
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            c = np.mean(rest, 0); c = c / (np.linalg.norm(c) + 1e-8)
            within.append(1 - float(q @ c))
        c = np.mean(vs, 0); cents[w] = c / (np.linalg.norm(c) + 1e-8)
    ws = list(cents)
    bm = [min(1 - float(cents[w] @ cents[o]) for o in ws if o != w) for w in ws if len(ws) > 1]
    conf = tot = 0
    for wq, vs in words.items():
        for i, q in enumerate(vs):
            best = min(words, key=lambda w: min(1 - float(q @ t) for j, t in enumerate(words[w]) if not (w == wq and j == i)) if [t for j, t in enumerate(words[w]) if not (w == wq and j == i)] else 1e9)
            tot += 1; conf += (best != wq)
    wi = float(np.mean(within)); bmm = float(np.mean(bm))
    return wi, bmm / wi if wi else float("nan"), conf / tot if tot else float("nan")


def d2_frr(words, negs):
    gen = []
    for w, vs in words.items():
        for i, q in enumerate(vs):
            rest = [vs[j] for j in range(len(vs)) if j != i]
            gen.append(min(1 - float(q @ t) for t in rest))
    imp = [min(min(1 - float(nv @ t) for t in vs) for vs in words.values()) for nv in negs]
    if not imp:
        return float("nan")
    thr = np.sort(imp)[max(0, int(FAR * len(imp)) - 1)]
    return float(np.mean([g > thr for g in gen]))


def geom_for(emb, preset):
    wi_all, fi_all, cf_all, frr_all = [], [], [], []
    for spk in L.CTL:
        d = L.load_speaker(spk)
        clean = L.load_emb("wavlm-large")
        keep = distinct_subset(d, clean, LAYER, 25)
        words = {w: [emb[f"{x}|{preset}"] for x in d["commands"][w] if f"{x}|{preset}" in emb] for w in keep}
        words = {w: v for w, v in words.items() if len(v) >= 2}
        negs = [emb[f"{x}|{preset}"] for x in d["negatives"][:60] if f"{x}|{preset}" in emb]
        if len(words) < 3:
            continue
        wi, fi, cf = within_and_fisher(words)
        wi_all.append(wi); fi_all.append(fi); cf_all.append(cf); frr_all.append(d2_frr(words, negs))
    return np.mean(wi_all), np.mean(fi_all), np.mean(cf_all), np.mean(frr_all)


def main():
    emb = build_emb()
    print(f"\nS22 FIDELITY GATE — synthetic-dys (degraded TORGO control) vs REAL dys (wavlm-large L{LAYER})\n", flush=True)
    print("  REAL dysarthric targets: D2 FRR 50-57%, within ~0.044, fisher ~1.04, rank1conf ~15-20%\n", flush=True)
    print(f"  {'preset':12s}  {'within':>8s}  {'fisher':>7s}  {'rank1conf':>10s}  {'D2 FRR@FAR5%':>13s}", flush=True)
    out = {}
    for p in PRESETS:
        wi, fi, cf, frr = geom_for(emb, p)
        out[p] = dict(within=float(wi), fisher=float(fi), rank1conf=float(cf), d2_frr=float(frr))
        print(f"  {p:12s}  {wi:8.3f}  {fi:7.2f}  {cf*100:9.1f}%  {frr*100:12.1f}%", flush=True)
    # verdict: which preset matches D2 band, and does geometry emerge there?
    print("\n  CALIBRATION: preset whose D2 FRR in [0.50,0.57], then check geometry (within~2.5x clean, fisher~1.0):", flush=True)
    clean_within = out["clean"]["within"]
    for p in PRESETS:
        o = out[p]
        d2_ok = 0.45 <= o["d2_frr"] <= 0.60
        scatter_ratio = o["within"] / clean_within if clean_within else float("nan")
        geom_ok = scatter_ratio >= 2.0 and o["fisher"] <= 1.3
        if d2_ok:
            print(f"    {p}: D2={o['d2_frr']*100:.0f}% (in band) | scatter x{scatter_ratio:.1f} clean, fisher {o['fisher']:.2f} "
                  f"=> geometry {'EMERGES -> VALID PROXY' if geom_ok else 'does NOT emerge -> proxy INVALID for the wall'}", flush=True)
    with open(os.path.join(L.CACHE, "s22_sim_fidelity.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
