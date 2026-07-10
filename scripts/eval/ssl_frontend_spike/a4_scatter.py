"""A4 — Severe-dysarthric within-word scatter decomposition.

QUESTION: is the severe-dys within-word embedding scatter (the thing that caps D2 at AUC~0.70)
STRUCTURED/low-rank (a few axes = duration / loudness / categorical variant switching) or ISOTROPIC
(direction-less noise)?
  - structured  => I11 (per-cluster / multimodal enrollment, F28) has a real mechanism to exploit.
  - isotropic   => the wall is honest; I11's expected value drops.

METHOD: per speaker, per word with >=3 reps, residual r = v - centroid(word). Pool residuals per
speaker. Eigen-decompose the residual covariance. Report:
  - participation ratio PR = (sum λ)^2 / sum(λ^2)  (effective rank; low = structured)
  - fraction of residual variance in top-1/2/3 PCs
  - |corr| of PC1..3 scores with utterance DURATION and RMS LOUDNESS (are the top axes interpretable?)
Compare dysarthric vs control (typical) to see if dys is MORE isotropic (honest wall) or comparably
structured.

PRE-REGISTERED GATE: structured iff top-3 PCs explain >=55% of within-word residual variance AND at
least one of PC1..3 has |corr| >= 0.35 with duration or loudness. Else -> wall honest.
"""
import os, sys, json, wave
import numpy as np
import cand_lib as L

LAYER = 15


def wav_dur_rms(path):
    try:
        with wave.open(path, "rb") as w:
            n = w.getnframes(); sr = w.getframerate()
            raw = w.readframes(n)
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        return n / sr, float(np.sqrt((x ** 2).mean()) + 1e-9)
    except Exception:
        return None, None


def speaker_residuals(spk, emb, layer, min_reps=3):
    cmds, _ = L.command_table(spk, emb, layer, min_reps=2)
    R, meta = [], []
    for w, reps in cmds.items():
        if len(reps) < min_reps:
            continue
        V = np.stack([r[1] for r in reps])
        c = V.mean(0)
        for (wav, v, _), rr in zip(reps, V - c):
            R.append(rr); meta.append(wav)
    if len(R) < 10:
        return None, None
    return np.stack(R), meta


def analyze(spk, emb, layer):
    R, meta = speaker_residuals(spk, emb, layer)
    if R is None:
        return None
    # covariance eigenspectrum
    C = np.cov(R.T)
    lam = np.linalg.eigvalsh(C)[::-1]
    lam = np.clip(lam, 0, None)
    tot = lam.sum() + 1e-12
    pr = (lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12)
    top = np.cumsum(lam) / tot
    # PC scores vs duration / loudness
    U, S, Vt = np.linalg.svd(R - R.mean(0), full_matrices=False)
    scores = U[:, :3] * S[:3]  # (n,3)
    durs, rms = [], []
    for m in meta:
        d, r = wav_dur_rms(m)
        durs.append(d); rms.append(r)
    durs = np.array([d if d is not None else np.nan for d in durs])
    rms = np.array([r if r is not None else np.nan for r in rms])
    corrs = {}
    for name, arr in [("dur", durs), ("rms", rms)]:
        cs = []
        ok = ~np.isnan(arr)
        for j in range(3):
            if ok.sum() > 5 and np.std(arr[ok]) > 0 and np.std(scores[ok, j]) > 0:
                cs.append(abs(float(np.corrcoef(arr[ok], scores[ok, j])[0, 1])))
            else:
                cs.append(0.0)
        corrs[name] = cs
    return dict(n=len(R), dim=R.shape[1], pr=float(pr),
                top1=float(top[0]), top2=float(top[1]), top3=float(top[2]),
                corr_dur=corrs["dur"], corr_rms=corrs["rms"])


def main():
    emb = L.load_emb("wavlm-large")
    print(f"A4 WITHIN-WORD SCATTER DECOMPOSITION — wavlm-large L{LAYER}\n", flush=True)
    out = {}
    for grp, spks in [("DYSARTHRIC", L.DYS), ("TYPICAL(control)", L.CTL)]:
        print(f"  {grp}:", flush=True)
        for s in spks:
            a = analyze(s, emb, LAYER)
            if a is None:
                print(f"    {s}: insufficient reps", flush=True); continue
            out[s] = a
            best_corr = max(max(a["corr_dur"]), max(a["corr_rms"]))
            print(f"    {s}: PR={a['pr']:5.1f}/{a['dim']}  top1/2/3={a['top1']*100:.0f}/{a['top2']*100:.0f}/{a['top3']*100:.0f}%"
                  f"  |r|dur={max(a['corr_dur']):.2f} |r|rms={max(a['corr_rms']):.2f}  (n={a['n']})", flush=True)
        print(flush=True)
    # aggregate dys
    dys = [out[s] for s in L.DYS if s in out]
    ctl = [out[s] for s in L.CTL if s in out]
    if dys:
        dtop3 = np.mean([a["top3"] for a in dys])
        dcorr = np.mean([max(max(a["corr_dur"]), max(a["corr_rms"])) for a in dys])
        dpr = np.mean([a["pr"] for a in dys])
        structured = dtop3 >= 0.55 and dcorr >= 0.35
        print(f"  DYS mean: top3={dtop3*100:.0f}%  PR={dpr:.1f}  best|r|={dcorr:.2f}", flush=True)
        if ctl:
            print(f"  CTL mean: top3={np.mean([a['top3'] for a in ctl])*100:.0f}%  PR={np.mean([a['pr'] for a in ctl]):.1f}", flush=True)
        print(f"\n  VERDICT: dys scatter is {'STRUCTURED -> I11/F28 mechanism exists' if structured else 'ISOTROPIC -> wall honest, I11 EV drops'}", flush=True)
        out["_verdict"] = dict(dys_top3=float(dtop3), dys_pr=float(dpr),
                               dys_best_corr=float(dcorr), structured=bool(structured),
                               ctl_top3=float(np.mean([a["top3"] for a in ctl])) if ctl else None,
                               ctl_pr=float(np.mean([a["pr"] for a in ctl])) if ctl else None)
    with open(os.path.join(L.CACHE, "a4_scatter.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
