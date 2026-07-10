"""R2 (P2) — trainable BACKEND on frozen pooled WavLM embeddings vs cosine, for the D2 wall.

Deep-research bet P2 (docs/research/2026-07-10-move-d2-wall.md): a discriminative backend
(LDA->WCCN, two-covariance PLDA) that shrinks within-word covariance should lift genuine/impostor
separability where frozen-SSL+cosine cannot — IF dysarthric embeddings have not pre-shrunk within-word
covariance. This is the SAME family (learn a linear transform of the embedding) as the two levers that
already died on this problem: G1 (per-user whitening, refuted on held-out males p=0.63) and G3
(nuisance-subspace, leakage artifact). So the pre-registered KILL criterion is strict.

VERDICT METRIC (advisor-locked): FRR @ FAR<=5%, held-out (LOFO folds), PER SEVERITY. AUC secondary.

Pre-registered success (moves the wall): backend gives >=8pp D2 FRR reduction on MODERATE severity,
AND the gain is PRESERVED under cross-gender transfer (train females -> test held-out males).
Pre-registered KILL: <3pp gain on moderate, OR gain vanishes / reverses under cross-gender transfer
(== the G1 artifact). Any positive that fails the transfer test is marked NOT-BANKED.

Backends trained LEAVE-ONE-SPEAKER-OUT on (speaker,word) classes (within-class = within-word repetition
scatter, the measured root cause). Two training regimes:
  loso   : train on all OTHER dysarthric speakers (mixed gender) — standard generalization.
  xgender: train on all speakers of the OTHER gender only — the strict G1-style transfer guard.

Reuses cached pooled embeddings (wavlm-large.npz females, male_wavlm_large.npz males), harness.folds,
and the d2_ceiling A0 global-threshold LOFO protocol. Deterministic.
"""
import os, sys, math, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14
FAR_TARGET = 0.05

# Round-3 empirical severity grading (docs/testing/2026-07-10_dysarthric-round3-results.md)
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
GENDER = {s: ("M" if s.startswith("M") else "F") for s in SEVERITY}
FEMALE = ["F01", "F03", "F04"]
MALE = ["M01", "M02", "M03", "M04", "M05"]


def load_pooled():
    """{spk: {'commands': {word:[vec]}, 'negatives': [vec]}} at LAYER, unit-norm pooled."""
    zf = np.load(os.path.join(CACHE, "wavlm-large.npz"), allow_pickle=True)
    zm = np.load(os.path.join(CACHE, "male_wavlm_large.npz"), allow_pickle=True)
    emb = {}
    for z in (zf, zm):
        for k in z.files:
            emb[k] = z[k][LAYER].astype(np.float64)
    data = H.scan(TORGO)
    out = {}
    for spk in FEMALE + MALE:
        d = data.get(spk)
        if not d:
            continue
        cmds = {w: [emb[wav] for wav in lst if wav in emb] for w, lst in d["commands"].items()}
        cmds = {w: v for w, v in cmds.items() if len(v) >= 2}
        negs = [emb[wav] for wav in d["negatives"] if wav in emb]
        out[spk] = {"commands": cmds, "negatives": negs}
    return out


# ------------------------------------------------------------------ backends (linear transforms)

def _l2(x):
    return x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-9)


def fit_lda_wccn(X, y, lda_dim=150):
    """LDA -> WCCN pipeline over (speaker,word) classes. Returns transform fn v->v'."""
    classes = {}
    for xi, yi in zip(X, y):
        classes.setdefault(yi, []).append(xi)
    classes = {c: np.array(v) for c, v in classes.items() if len(v) >= 2}
    if len(classes) < 3:
        return lambda v: _l2(v)
    mu = X.mean(0)
    d = X.shape[1]
    Sw = np.zeros((d, d)); Sb = np.zeros((d, d))
    for c, V in classes.items():
        cm = V.mean(0)
        Sw += (V - cm).T @ (V - cm)
        Sb += len(V) * np.outer(cm - mu, cm - mu)
    Sw /= max(1, len(X)); Sb /= max(1, len(classes))
    Sw += 1e-3 * np.eye(d)
    # LDA: top eigenvectors of Sw^-1 Sb
    evals, evecs = np.linalg.eig(np.linalg.solve(Sw, Sb))
    order = np.argsort(-evals.real)
    W_lda = evecs[:, order[:lda_dim]].real  # (d, lda_dim)
    Xl = X @ W_lda
    # WCCN in LDA space: within-class covariance -> whiten
    cov = np.zeros((W_lda.shape[1],) * 2)
    for c, V in classes.items():
        Vl = (V @ W_lda)
        cm = Vl.mean(0)
        cov += (Vl - cm).T @ (Vl - cm)
    cov /= max(1, len(X))
    cov += 1e-3 * np.eye(cov.shape[0])
    L = np.linalg.cholesky(np.linalg.inv(cov))  # cov^-1 = L L^T
    W = W_lda @ L  # combined (d, lda_dim)
    return lambda v: _l2(np.atleast_2d(v) @ W).reshape(v.shape[:-1] + (W.shape[1],)) if v.ndim > 1 \
        else _l2((v @ W))


def build_train(data, train_spks):
    X, y = [], []
    for s in train_spks:
        for w, vecs in data[s]["commands"].items():
            for v in vecs:
                X.append(v); y.append(f"{s}::{w}")
    return np.array(X), np.array(y)


# ------------------------------------------------------------------ D2 eval (A0 global threshold LOFO)

def d2_speaker(data_spk, transform):
    """LOFO global-threshold FRR @ FAR<=5% for one speaker in transformed space.
    Returns (frr, far, npos, nneg, genuine_scores, impostor_scores). Score = cosine distance (1-dot)."""
    cmds = {w: [transform(v) for v in vecs] for w, vecs in data_spk["commands"].items()}
    negs = [transform(v) for v in data_spk["negatives"]]
    # emulate harness.folds on the command structure (round-robin per word)
    words = list(cmds)
    k = 5
    # rows: (fold, truth_or_None, sorted[(dist,word)])
    def nn_rows(enroll, qv):
        out = []
        for w, tvs in enroll.items():
            best = min(1.0 - float(qv @ tv) for tv in tvs)
            out.append((best, w))
        out.sort()
        return out
    rows = []
    for f in range(k):
        enroll = {}
        pos = []
        for w in words:
            reps = cmds[w]
            for i, v in enumerate(reps):
                if i % k == f:
                    pos.append((w, v))
                else:
                    enroll.setdefault(w, []).append(v)
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        for w, v in pos:
            rows.append((f, w, nn_rows(enroll, v)))
        for i, v in enumerate(negs):
            if i % k == f:
                rows.append((f, None, nn_rows(enroll, v)))
    # LOFO threshold fit to FAR<=5% on train folds
    fold_ids = sorted({r[0] for r in rows})
    acc = pos_n = fa = neg_n = 0
    gen_all, imp_all = [], []
    for fo in fold_ids:
        train = [r for r in rows if r[0] != fo]
        test = [r for r in rows if r[0] == fo]
        negs_tr = [r for r in train if r[1] is None]
        cands = sorted({r[2][0][0] for r in train if r[2]})
        thr = (cands[0] - 1.0) if cands else 0.0
        for t in cands:
            fa_tr = sum(1 for r in negs_tr if r[2] and r[2][0][0] <= t) / max(1, len(negs_tr))
            if fa_tr <= FAR_TARGET:
                thr = t
        for r in test:
            accepted = bool(r[2]) and r[2][0][0] <= thr
            if r[1] is not None:
                pos_n += 1
                if accepted and r[2][0][1] == r[1]:
                    acc += 1
                if r[2] and r[1] == r[2][0][1]:
                    gen_all.append(r[2][0][0])
            else:
                neg_n += 1
                if accepted:
                    fa += 1
                if r[2]:
                    imp_all.append(r[2][0][0])
    frr = 0.0 if pos_n == 0 else 1.0 - acc / pos_n
    far = 0.0 if neg_n == 0 else fa / neg_n
    return frr, far, pos_n, neg_n, np.array(gen_all), np.array(imp_all)


def auc_of(g, im):
    if g.size == 0 or im.size == 0:
        return float("nan")
    return float(np.mean(g[:, None] < im[None, :]))


def main():
    data = load_pooled()
    spks = [s for s in FEMALE + MALE if s in data]
    print(f"R2 BACKEND D2 — wavlm-large L{LAYER}, pooled, FAR<=5% LOFO. speakers={spks}\n", flush=True)

    # ---- baseline: cosine (identity transform) ----
    base = {}
    print(f"{'spk':>4} {'sev':>11} {'gen':>3} | {'cosine FRR':>10} {'FAR':>5} {'AUC':>5}", flush=True)
    for s in spks:
        frr, far, npos, nneg, g, im = d2_speaker(data[s], lambda v: v)
        base[s] = dict(frr=frr, far=far, npos=npos, nneg=nneg, auc=auc_of(g, im))
        print(f"{s:>4} {SEVERITY[s]:>11} {GENDER[s]:>3} | {frr*100:9.1f}% {far*100:4.1f}% {base[s]['auc']:.3f}",
              flush=True)

    results = {"layer": LAYER, "far_target": FAR_TARGET, "baseline": base, "regimes": {}}

    # ---- backend, two training regimes ----
    for regime in ["loso", "xgender"]:
        print(f"\n--- backend=LDA+WCCN  regime={regime} ---", flush=True)
        print(f"{'spk':>4} {'sev':>11} {'gen':>3} | {'backend FRR':>11} {'FAR':>5} {'AUC':>5} | "
              f"{'dFRR':>7} {'dAUC':>6}", flush=True)
        reg = {}
        for s in spks:
            if regime == "loso":
                train_spks = [t for t in spks if t != s]
            else:  # xgender: train only on the OTHER gender
                train_spks = [t for t in spks if GENDER[t] != GENDER[s]]
            if len(train_spks) < 2:
                continue
            X, y = build_train(data, train_spks)
            tf = fit_lda_wccn(X, y)
            frr, far, npos, nneg, g, im = d2_speaker(data[s], tf)
            dfrr = (base[s]["frr"] - frr) * 100  # positive = improvement (FRR down)
            dauc = auc_of(g, im) - base[s]["auc"]
            reg[s] = dict(frr=frr, far=far, npos=npos, nneg=nneg, auc=auc_of(g, im),
                          dfrr_pp=dfrr, dauc=dauc)
            print(f"{s:>4} {SEVERITY[s]:>11} {GENDER[s]:>3} | {frr*100:10.1f}% {far*100:4.1f}% "
                  f"{reg[s]['auc']:.3f} | {dfrr:+6.1f}pp {dauc:+.3f}", flush=True)
        results["regimes"][regime] = reg

    # ---- verdict: moderate severity, transfer preservation ----
    def sev_mean(reg, sev, key):
        vals = [reg[s][key] for s in reg if SEVERITY[s] == sev]
        return float(np.mean(vals)) if vals else float("nan")
    print("\n=== VERDICT (moderate severity) ===", flush=True)
    for regime in ["loso", "xgender"]:
        reg = results["regimes"][regime]
        m = sev_mean(reg, "moderate", "dfrr_pp")
        print(f"  {regime:>7}: moderate mean dFRR = {m:+.1f}pp  "
              f"(per-spk: {[(s, round(reg[s]['dfrr_pp'],1)) for s in reg if SEVERITY[s]=='moderate']})",
              flush=True)
    mod_loso = sev_mean(results["regimes"]["loso"], "moderate", "dfrr_pp")
    mod_xg = sev_mean(results["regimes"]["xgender"], "moderate", "dfrr_pp")
    banked = (mod_loso >= 8.0 and mod_xg >= 8.0)
    killed = (mod_loso < 3.0 or mod_xg < 3.0)
    results["verdict"] = dict(moderate_dfrr_loso=mod_loso, moderate_dfrr_xgender=mod_xg,
                              banked=bool(banked), killed=bool(killed))
    print(f"\n  PRE-REGISTERED: banked(>=8pp both)={banked}  killed(<3pp either)={killed}", flush=True)
    print(f"  => {'BANKED' if banked else ('KILLED — same family as G1/G3' if killed else 'NOT-BANKED (partial)')}",
          flush=True)

    with open(os.path.join(CACHE, "r2_backend_d2.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote r2_backend_d2.json", flush=True)


if __name__ == "__main__":
    main()
