"""B10 / B8 / B9 — sequential 2-attempt protocols at matched TASK-level FAR.

A "task" = the user says a command; the system may ask for one retry. We simulate:
  genuine task  : a1 = rep i of word w, a2 = a different rep j of w; enroll = the OTHER reps (few-shot).
  impostor task : a1 = OOV negative n1, a2 = negative n2; enroll = all reps.
Accept(genuine)  = a correct-winner accept within the protocol's attempt budget.
Accept(impostor) = any accept within the budget = a false accept (task-level FA).

Threshold(s) fit so each protocol's TASK-level FAR <= 5% (the banked per-trial budget, now spent over
the whole task — a strictly fairer bar than letting 2 attempts double the FA budget). Compare task-FRR.

  P1  single attempt (reference)          — no retry
  B10 margin-zone retry                   — retry ONLY if a1 is a near-miss d1 in (theta, theta+delta];
                                            sweep delta to maximize task-FRR reduction s.t. task-FAR<=5%
  B8  first-attempt-as-template retry     — margin-zone retry, but add a1's vector as a temporary extra
                                            template for a1's winning word before scoring a2 (exploits
                                            attempt correlation as signal)
  B9  SPRT sequential                     — accumulate log-LR(d) across a1,a2 with Wald bounds; decide
                                            accept/reject/continue by construction

Baseline P1 = the banked 13.8% typical D2. EXPLORATORY (EVAL-003): any winner needs fresh confirmation.
"""
import os, sys, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset
from b_single import kde_1d

LAYER = 15
FARBUD = 0.05
np.random.seed(0)


def speaker_tasks(spk, emb, layer):
    """Build genuine + impostor 2-attempt tasks. Each task carries the raw query vecs + the fold-safe
    enroll dict (word->list[vec]) so protocols can re-score with modified templates (B8)."""
    d = L.load_speaker(spk)
    keep = distinct_subset(d, emb, layer, 25)
    words = {w: [emb[x][layer] for x in d["commands"][w] if x in emb] for w in keep}
    words = {w: v for w, v in words.items() if len(v) >= 3}
    if len(words) < 3:
        return None
    negs = [emb[x][layer] for x in d["negatives"] if x in emb]
    gtasks = []
    for w, vs in words.items():
        idx = list(range(len(vs)))
        rng = np.random.RandomState(hash(w) % 2**31)
        rng.shuffle(idx)
        # pair reps: (idx0,idx1),(idx2,idx3)...
        for a in range(0, len(idx) - 1, 2):
            i, j = idx[a], idx[a + 1]
            enroll = {ww: ([vv[t] for t in range(len(vv)) if not (ww == w and t in (i, j))])
                      for ww, vv in words.items()}
            enroll = {ww: vv for ww, vv in enroll.items() if vv}
            gtasks.append((w, vs[i], vs[j], enroll))
    itasks = []
    enroll_all = {ww: vv for ww, vv in words.items()}
    for a in range(0, len(negs) - 1, 2):
        itasks.append((None, negs[a], negs[a + 1], enroll_all))
    return gtasks, itasks, words


def score(qv, enroll):
    return sorted((min(1 - float(qv @ t) for t in tt), ww) for ww, tt in enroll.items())


def run_protocol(gtasks, itasks, proto, theta, delta=0.0, lr_fns=None, wald=None):
    """Return (task_frr, task_far)."""
    def genuine_ok(w, a1, a2, enroll):
        s1 = score(a1, enroll); d1, w1 = s1[0]
        if proto == "P1":
            return d1 <= theta and w1 == w
        if d1 <= theta:                      # immediate accept
            return w1 == w
        if proto in ("B10", "B8"):
            if not (theta < d1 <= theta + delta):
                return False                 # hard reject, no retry
            en2 = enroll
            if proto == "B8":
                en2 = {**enroll, w1: enroll.get(w1, []) + [a1]}  # add attempt-1 as template
            s2 = score(a2, en2); d2, w2 = s2[0]
            return d2 <= theta and w2 == w
        if proto == "B9":
            pg, pn = lr_fns
            A, B = wald
            llr = np.log(pg(d1)) - np.log(pn(d1))
            if llr >= A:
                return w1 == w
            if llr <= B:
                return False
            s2 = score(a2, enroll); d2, w2 = s2[0]
            llr += np.log(pg(d2)) - np.log(pn(d2))
            return llr >= A and w2 == w
        return False

    def impostor_fa(_, a1, a2, enroll):
        s1 = score(a1, enroll); d1, w1 = s1[0]
        if proto == "P1":
            return d1 <= theta
        if d1 <= theta:
            return True
        if proto in ("B10", "B8"):
            if not (theta < d1 <= theta + delta):
                return False
            en2 = enroll
            if proto == "B8":
                en2 = {**enroll, w1: enroll.get(w1, []) + [a1]}
            s2 = score(a2, en2); d2, w2 = s2[0]
            return d2 <= theta
        if proto == "B9":
            pg, pn = lr_fns
            A, B = wald
            llr = np.log(pg(d1)) - np.log(pn(d1))
            if llr >= A:
                return True
            if llr <= B:
                return False
            s2 = score(a2, enroll); d2, w2 = s2[0]
            llr += np.log(pg(d2)) - np.log(pn(d2))
            return llr >= A
        return False

    gf = np.mean([not genuine_ok(*t) for t in gtasks]) if gtasks else 1.0
    ff = np.mean([impostor_fa(*t) for t in itasks]) if itasks else 0.0
    return gf, ff


def fit_theta(gtasks, itasks, proto, delta=0.0, lr_fns=None, budget=FARBUD):
    """Largest theta s.t. task-FAR <= budget for this protocol."""
    cand = sorted(set(np.linspace(0.0, 1.0, 60)))
    best = cand[0]
    for th in cand:
        if proto == "B9":
            wald = (np.log((1 - 0.05) / budget), np.log(0.05 / (1 - budget)))
            _, ff = run_protocol(gtasks, itasks, proto, th, delta, lr_fns, wald)
        else:
            _, ff = run_protocol(gtasks, itasks, proto, th, delta, lr_fns)
        if ff <= budget:
            best = th
    return best


def eval_group(spks, emb, layer):
    agg = {}
    per_delta = {}
    for s in spks:
        r = speaker_tasks(s, emb, layer)
        if r is None:
            continue
        gt, it, words = r
        # LR densities for B9 from this speaker's genuine/impostor nearest dists
        gd = [score(a1, en)[0][0] for (_, a1, _, en) in gt]
        idn = [score(a1, en)[0][0] for (_, a1, _, en) in it]
        pg, pn = kde_1d(gd), kde_1d(idn)
        n_g, n_i = len(gt), len(it)
        for proto in ["P1", "B10", "B8", "B9"]:
            if proto in ("B10", "B8"):
                # sweep delta, pick the one minimizing task-FRR at task-FAR<=budget
                best = None
                for delta in [0.05, 0.10, 0.15, 0.20, 0.30]:
                    th = fit_theta(gt, it, proto, delta)
                    fr, fa = run_protocol(gt, it, proto, th, delta)
                    if fa <= FARBUD and (best is None or fr < best[0]):
                        best = (fr, fa, delta)
                if best is None:
                    th = fit_theta(gt, it, proto, 0.10)
                    best = run_protocol(gt, it, proto, th, 0.10) + (0.10,)
                fr, fa, dz = best
                per_delta.setdefault(proto, []).append(dz)
            elif proto == "B9":
                th = fit_theta(gt, it, proto, lr_fns=(pg, pn))
                wald = (np.log((1 - 0.05) / FARBUD), np.log(0.05 / (1 - FARBUD)))
                fr, fa = run_protocol(gt, it, proto, th, 0.0, (pg, pn), wald)
            else:
                th = fit_theta(gt, it, proto)
                fr, fa = run_protocol(gt, it, proto, th)
            a = agg.setdefault(proto, [0.0, 0.0, 0, 0])
            a[0] += fr * n_g; a[1] += fa * n_i; a[2] += n_g; a[3] += n_i
    out = {}
    for proto, (frn, fan, ng, ni) in agg.items():
        out[proto] = (frn / ng if ng else None, fan / ni if ni else None, ng, ni)
    return out, per_delta


def main():
    emb = L.load_emb("wavlm-large")
    print(f"B10/B8/B9 — sequential 2-attempt, typical, wavlm-large L{LAYER}, matched task-FAR<=5%\n", flush=True)
    out, per_delta = eval_group(L.CTL, emb, LAYER)
    base = out.get("P1", (None,))[0]
    names = {"P1": "single (ref)", "B10": "margin-zone retry", "B8": "B8 a1-as-template", "B9": "B9 SPRT"}
    for proto in ["P1", "B10", "B8", "B9"]:
        if proto not in out:
            continue
        fr, fa, ng, ni = out[proto]
        dz = f"  delta~{np.mean(per_delta[proto]):.2f}" if proto in per_delta and per_delta[proto] else ""
        delta_pp = f"  ({(base-fr)*100:+.1f}pp)" if base is not None and proto != "P1" else "  <-baseline"
        print(f"    {names[proto]:20s}: task-FRR={fr*100:5.1f}%  task-FAR={fa*100:4.1f}%  (n_g={ng},n_i={ni}){delta_pp}{dz}", flush=True)
    wins = {p: (base - out[p][0]) * 100 for p in out if p != "P1" and out[p][0] is not None and (base - out[p][0]) * 100 >= 2.0}
    print(f"\n  GATE (>=2pp task-FRR beat over single-attempt {base*100:.1f}% at matched task-FAR): {wins if wins else 'none'}", flush=True)
    with open(os.path.join(L.CACHE, "b_seq.json"), "w") as f:
        json.dump({p: list(v) for p, v in out.items()} | {"baseline": base}, f, indent=2)


if __name__ == "__main__":
    main()
