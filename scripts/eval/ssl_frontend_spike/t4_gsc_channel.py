"""T4 — Re-measure the CHANNEL-ROBUSTNESS domains (D5 reverb, D4 noise, D6 bandwidth) on the ROBUST
GSC corpus, resolving the cross-corpus confound (EVAL-004).

The committed typical composite carries D5=81.4% / D4=88.5% / D6=86.9% rank-1 — but ALL of them were
measured on TORGO control n=3 (`typical_composite.py`), the same fragile basis whose D2=13.8% we
already rejected in favour of the robust GSC-19 D2 (~5.6%). We cannot distrust TORGO-n3 for D2 and
simultaneously trust it for D5's 81.4% to crown reverb "the" 800-floor co-blocker. T4 re-measures the
SAME wavlm-large L15 few-shot + multi-condition-enrollment protocol on GSC-19, so D5/D4/D6 sit on the
same corpus basis as D2.

CONFOUND-RESOLUTION METHOD (advisor): cross-corpus ABSOLUTE rank-1 is not comparable (different vocab
size / speaker difficulty). So the confound is resolved by the PAIRED within-GSC clean->condition
degradation on the SAME query items, plus the absolute band. Anchor = GSC clean rank-1 (free, cached
in gsc_wavlm_large_alllayers.npz). Trap: a MILD reverb delta that still lands <85% means the GSC clean
base-rate (vocab/speakers), NOT reverb, is the constraint — do not misattribute.

FIDELITY GATE (EVAL-004): the augmentation fns (add_noise/reverb/bandlimit) and the rank-1 scoring are
IMPORTED VERBATIM from typical_composite.py — same code, new corpus — so the re-impl risk is nil and
the only thing to sanity-check is that GSC clean rank-1 is sane (high) at L15.

Bands (from typical_composite.BANDS): D5/D6 900 needs >=85%, 800 >=75%; D4 900 needs >=80%, 800 >=70%.

Usage:
  python t4_gsc_channel.py --validate-clean   # NO ENCODE: clean rank-1 anchor from cache + logic check
  python t4_gsc_channel.py [--conds reverb250,noise20,band] [--layer 15]   # heavy: augmented encode
Writes _ceiling_cache/t4_gsc_channel.json and checkpoints gsc_channel_L{layer}.npz incrementally.
"""
import os, sys, json, math, argparse
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a5_gsc_kcurve import GSC, REPS, FIXED_WORDS, pick_speakers
from typical_composite import CONDS  # add_noise/reverb/bandlimit + clean, IMPORTED VERBATIM (fidelity)

np.random.seed(0)
ALLLAYERS = os.path.join(L.CACHE, "gsc_wavlm_large_alllayers.npz")
BANDS = {"D1": [(600,.55),(700,.65),(800,.75),(900,.85)], "D4": [(600,.55),(700,.60),(800,.70),(900,.80)],
         "D5": [(700,.65),(800,.75),(900,.85)], "D6": [(700,.65),(800,.75),(900,.85)]}
DOM_COND = {"D1": "clean", "D4": "noise20", "D5": "reverb250", "D6": "band"}
COND_DOM = {c: d for d, c in DOM_COND.items()}


def band(dom, v):
    b = 500
    for sc, th in BANDS[dom]:
        if v >= th:
            b = sc
    return b


def gsc_manifest():
    """The a5/T2 fixed subset: per speaker, 8 fixed words x 6 reps (the query+template pool).
    Rank-1 is threshold-free -> no negatives needed."""
    man = {}
    for spk, ge5, wc in pick_speakers():
        man[spk] = {w: wc[w][:REPS] for w in ge5[:FIXED_WORDS]}
    return man


def all_paths(man):
    return sorted({p for words in man.values() for ps in words.values() for p in ps})


def embed_cond_L(net, path, cond_fn, layer):
    """Apply the condition to the waveform, VAD-trim, encode wavlm-large, return the unit L-vector.
    Matches typical_composite.embed_batch (cond BEFORE trim; L15 mean-pool; unit-norm)."""
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    x = cond_fn(x)
    sp = H.energy_vad_trim(x)
    if sp.size < 400:
        sp = x if x.size >= 400 else np.zeros(400, dtype=np.float32)
    wn = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(wn.astype(np.float32)).unsqueeze(0)).hidden_states[layer][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def load_clean_L(paths, layer):
    """Clean L-vectors from the cached alllayers npz (NO encode)."""
    z = np.load(ALLLAYERS, allow_pickle=True)
    have = {k: z[k] for k in z.files}
    return {p: have[p][layer] for p in paths if p in have}, [p for p in paths if p not in have]


def build_cond_cache(conds, layer):
    """Return {cond: {path: Lvec}}. clean pulled from cache; augmented conds encoded + checkpointed."""
    man = gsc_manifest()
    paths = all_paths(man)
    clean, missing = load_clean_L(paths, layer)
    if missing:
        print(f"  WARN: {len(missing)} clean paths not in alllayers cache (will encode)", flush=True)
    out = {"clean": clean}
    ckpt = os.path.join(L.CACHE, f"gsc_channel_L{layer}.npz")
    saved = {}
    if os.path.exists(ckpt):
        z = np.load(ckpt, allow_pickle=True)
        saved = {k: z[k] for k in z.files}  # keys are "cond|path"
    net = None
    for c in conds:
        if c == "clean":
            continue
        cur = {p: saved[f"{c}|{p}"] for p in paths if f"{c}|{p}" in saved}
        todo = [p for p in paths if p not in cur] + [p for p in missing if c == "clean"]
        if todo:
            if net is None:
                from transformers import AutoModel
                print("  loading wavlm-large...", flush=True)
                net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
            print(f"  encoding {len(todo)} GSC clips under '{c}' (wavlm-large L{layer})...", flush=True)
            for i, p in enumerate(todo):
                cur[p] = embed_cond_L(net, p, CONDS[c], layer)
                if (i + 1) % 100 == 0:
                    for pp, vv in cur.items():
                        saved[f"{c}|{pp}"] = vv
                    np.savez(ckpt, **saved)  # INCREMENTAL checkpoint (avoid 2026-07-11 tail-loss)
                    print(f"    {i+1}/{len(todo)} (checkpointed)", flush=True)
            for pp, vv in cur.items():
                saved[f"{c}|{pp}"] = vv
            np.savez(ckpt, **saved)
        out[c] = cur
    return man, out


def rank1(man, query_cond_emb, enroll_srcs):
    """Leave-one-out rank-1, few-shot + multi-condition enrollment. Matches typical_composite.rank1_fewshot.
    query embedded in query_cond_emb; templates from every dict in enroll_srcs (multi-condition).
    Returns (rank1, per-item hits list [(spk,word,qi,hit)])."""
    hits = tot = 0
    items = []
    for spk, words in man.items():
        wv = {w: [p for p in ps] for w, ps in words.items()}
        for w, ps in wv.items():
            for qi in range(len(ps)):
                qp = ps[qi]
                if qp not in query_cond_emb:
                    continue
                q = query_cond_emb[qp]
                enroll = {}
                for ww, pps in wv.items():
                    tmpl = pps if ww != w else [pps[j] for j in range(len(pps)) if j != qi]
                    enroll[ww] = [src[p] for p in tmpl for src in enroll_srcs if p in src]
                cand = [(min(1 - float(q @ t) for t in tt), ww) for ww, tt in enroll.items() if tt]
                if not cand:
                    continue
                best = min(cand)
                hit = int(best[1] == w)
                hits += hit; tot += 1
                items.append((spk, w, qi, hit))
    return (hits / tot if tot else 0.0), items


def mcnemar(items_a, items_b):
    """Paired per-item McNemar on hit/miss between two conditions (same query items)."""
    ha = {(s, w, qi): h for s, w, qi, h in items_a}
    hb = {(s, w, qi): h for s, w, qi, h in items_b}
    keys = sorted(set(ha) & set(hb))
    b = sum(1 for k in keys if ha[k] == 1 and hb[k] == 0)  # clean hit, cond miss
    c = sum(1 for k in keys if ha[k] == 0 and hb[k] == 1)  # clean miss, cond hit
    n = b + c
    # exact two-sided binomial p (small discordant counts)
    if n == 0:
        p = 1.0
    else:
        from math import comb
        k = min(b, c)
        p = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n))
    return {"n_pairs": len(keys), "clean_only_hit": b, "cond_only_hit": c, "p_exact": p}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-clean", action="store_true", help="NO ENCODE: clean anchor + logic check")
    ap.add_argument("--conds", default="reverb250,noise20,band")
    ap.add_argument("--layer", type=int, default=15)
    a = ap.parse_args()
    layer = a.layer

    if a.validate_clean:
        man = gsc_manifest()
        paths = all_paths(man)
        clean, missing = load_clean_L(paths, layer)
        print(f"T4 VALIDATE-CLEAN — GSC {len(man)} speakers, {len(paths)} fixed clips, "
              f"{len(clean)} in cache, {len(missing)} missing, L{layer}\n", flush=True)
        r1, items = rank1(man, clean, [clean])
        print(f"  GSC CLEAN rank-1 (D1 anchor, multi-cond=clean-only) = {r1*100:.1f}%  -> band {band('D1', r1)}", flush=True)
        print(f"  per-item n={len(items)}; sane check: rank-1 should be high (~0.85-0.95).", flush=True)
        # per-speaker spread
        per = {}
        for s, w, qi, h in items:
            per.setdefault(s, [0, 0])
            per[s][0] += h; per[s][1] += 1
        spread = sorted(round(100 * v[0] / v[1]) for v in per.values())
        print(f"  per-speaker rank-1 (sorted): {spread}", flush=True)
        return

    conds = a.conds.split(",")
    print(f"T4 GSC CHANNEL — wavlm-large L{layer}, conds={conds} (+clean anchor), multi-cond enrollment\n", flush=True)
    man, emb_by_cond = build_cond_cache(["clean"] + conds, layer)
    enroll_srcs = list(emb_by_cond.values())  # multi-condition enrollment (clean + all measured conds)
    results = {}
    clean_r1, clean_items = rank1(man, emb_by_cond["clean"], enroll_srcs)
    results["D1_clean"] = {"rank1": clean_r1, "band": band("D1", clean_r1)}
    print(f"  D1 (clean    ): rank1={clean_r1*100:5.1f}%  -> band {band('D1', clean_r1)}", flush=True)
    for c in conds:
        dom = COND_DOM.get(c, c)
        r1, items = rank1(man, emb_by_cond[c], enroll_srcs)
        mc = mcnemar(clean_items, items)
        b = band(dom, r1)
        results[f"{dom}_{c}"] = {"rank1": r1, "band": b, "paired_vs_clean": mc,
                                 "delta_pp": (clean_r1 - r1) * 100}
        print(f"  {dom} ({c:9s}): rank1={r1*100:5.1f}%  -> band {b}   "
              f"| clean-cond Δ={(clean_r1-r1)*100:+.1f}pp  McNemar p={mc['p_exact']:.3f} "
              f"(clean-only-hit={mc['clean_only_hit']}, cond-only-hit={mc['cond_only_hit']})", flush=True)
    results["_meta"] = {"layer": layer, "n_spk": len(man), "conds": conds}
    with open(os.path.join(L.CACHE, "t4_gsc_channel.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\n  wrote _ceiling_cache/t4_gsc_channel.json", flush=True)


if __name__ == "__main__":
    main()
