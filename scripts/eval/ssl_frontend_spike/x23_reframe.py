"""#2 (SPRT / sequential multi-attempt) + #3 (abstain+confirm, conformal reject) — Tier A reframe.

Both build on the same LOFO winner+score rows as #1 (pooled wavlm-large L14, moderate = M01/M02/F03).
Adjudicated by SIMULATION (seeded) so the decision-FAR is exact and the sequential dependence is honest —
no independence-formula shortcut. Every verdict prints realized held-out **decision-FAR**.

--------------------------------------------------------------------------------------------------------
#2 SPRT / k-consistent multi-attempt.  The user repeats the command; accept the first command that
   collects k accept-votes within M attempts (an accept-vote = that command is the winner with score<=tau).
   FAR IS PER-DECISION (advisor lock): an impostor "decision" = M independent impostor utterances; it is a
   false-accept iff any command reaches k votes within M. Because an impostor must fool the SAME command k
   times, k>1 lets us RELAX tau (per-utterance) while keeping decision-FAR<=5%. We sweep tau per (k,M) to
   the tau whose realized decision-FAR<=5%, then report effective FRR and mean turns.
   SUCCESS BAR: moderate effective FRR<=15% at <=2.0 mean turns, decision-FAR<=5%.

#3 Abstain+confirm (conformal reject at the confusor tail).  Three outcomes per single utterance via two
   thresholds t_acc<t_rej: score<=t_acc -> ACCEPT (execute); t_acc<score<=t_rej -> ABSTAIN ("did you mean
   W1?" confirm turn, resolved by the user at confirm-error pc); score>t_rej -> REJECT (retry/failure).
   t_rej is the conformal accept boundary set to decision-FAR<=5% on held-out negatives; t_acc is set so
   the auto-accept region itself keeps a tight FAR (<=1%). ABSTAIN converts a confusion into a confirm turn.
   SUCCESS BAR: moderate task_success>=85% with abstain-rate<20%, decision-FAR<=5%.

NOT-BANKED regardless (pending UASpeech #24). Real TORGO only.
"""
import os, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
FEMALE = ["F01", "F03", "F04"]; MALE = ["M01", "M02", "M03", "M04", "M05"]
MODERATE = ["M01", "M02", "F03"]
RNG = np.random.default_rng(20260711)
N_SIM = 4000


def load_pooled():
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


def build_rows(data_spk, k=5):
    """LOFO rows: genuine {word:[(winner,score)]} and impostor [(winner,score)]. Lower score=genuine."""
    cmds = data_spk["commands"]; negs = data_spk["negatives"]
    words = list(cmds)
    gen = {w: [] for w in words}; imp = []
    for f in range(k):
        enroll = {}; pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        def score(v):
            d = {w: min(1.0 - float(v @ tv) for tv in tvs) for w, tvs in enroll.items()}
            w1 = min(d, key=d.get); return w1, d[w1]
        for w, v in pos:
            w1, s = score(v); gen[w].append((w1, s))
        for v in negs:
            w1, s = score(v); imp.append((w1, s))
    return {w: v for w, v in gen.items() if v}, imp


def pool_moderate(data):
    gen = {}; imp = []
    for s in MODERATE:
        g, i = build_rows(data[s])
        for w, lst in g.items():
            gen[f"{s}:{w}"] = lst
        imp.extend(i)
    return gen, imp


# ---------------------------------------------------------------- #2 SPRT / k-consistent
def sim_sprt(gen, imp, tau, k, M):
    """Simulate the k-of-M-consistent protocol. Returns (eff_frr, decision_far, mean_turns)."""
    words = list(gen)
    # genuine decisions: pick a word, draw up to M reps of it
    frr_n = frr_fail = 0; turns_sum = 0.0
    for _ in range(N_SIM):
        w = words[RNG.integers(len(words))]
        lst = gen[w]
        votes = {}; accepted = False; t = 0
        for t in range(1, M + 1):
            wn, s = lst[RNG.integers(len(lst))]
            if s <= tau:
                votes[wn] = votes.get(wn, 0) + 1
                if votes[wn] >= k:
                    accepted = (wn == w.split(":")[-1] or wn == w)  # correct command reached k
                    break
        frr_n += 1; turns_sum += t
        if not accepted:
            frr_fail += 1
    eff_frr = frr_fail / frr_n; mean_turns = turns_sum / frr_n
    # impostor decisions: M independent impostor utterances; FA iff any command reaches k votes
    fa_n = fa = 0
    for _ in range(N_SIM):
        votes = {}; hit = False
        for t in range(M):
            wn, s = imp[RNG.integers(len(imp))]
            if s <= tau:
                votes[wn] = votes.get(wn, 0) + 1
                if votes[wn] >= k:
                    hit = True; break
        fa_n += 1; fa += int(hit)
    return eff_frr, fa / fa_n, mean_turns


def far_matched_tau_sprt(gen, imp, k, M, far_target=0.05):
    """Find the most permissive tau (highest) with realized decision-FAR<=target for (k,M)."""
    cand = np.quantile([s for _, s in imp], np.linspace(0.005, 0.6, 40))
    best = None
    for t in cand:
        _, far, _ = sim_sprt(gen, imp, t, k, M)
        if far <= far_target:
            best = t  # keep raising tau while FAR valid
    if best is None:
        best = cand[0]
    return float(best)


# ---------------------------------------------------------------- #3 abstain+confirm
def sim_abstain(gen, imp, t_acc, t_rej, pc, M=2):
    """Three-way per-utterance with abstain->confirm. Up to M attempts. Returns dict of metrics."""
    words = list(gen)
    succ = cmderr = 0; abst_turns = 0; turns_sum = 0.0; conf_any = 0
    for _ in range(N_SIM):
        w = words[RNG.integers(len(words))]; truth = w.split(":")[-1]
        lst = gen[w]; done = False; t = 0; used_confirm = False
        for t in range(1, M + 1):
            wn, s = lst[RNG.integers(len(lst))]
            if s <= t_acc:                       # auto-accept
                if wn == truth:
                    succ += 1; done = True
                else:
                    cmderr += 1; done = True     # wrong auto-executed
                break
            elif s <= t_rej:                     # abstain -> confirm turn
                used_confirm = True
                if wn == truth:
                    if RNG.random() > pc:
                        succ += 1; done = True; break     # user confirms yes
                    # else user erroneously rejects -> retry
                else:
                    if RNG.random() < pc:
                        cmderr += 1; done = True; break   # user erroneously confirms wrong
                    # else user says no -> retry
            # else reject -> retry
        turns_sum += t + (1 if used_confirm else 0)
        conf_any += int(used_confirm)
    n = N_SIM
    # impostor decision-FAR (M utterances): executes if any auto-accept, or abstain-confirmed-yes at pc
    fa = 0
    for _ in range(n):
        hit = False
        for t in range(M):
            wn, s = imp[RNG.integers(len(imp))]
            if s <= t_acc:
                hit = True; break
            elif s <= t_rej:
                if RNG.random() < pc:   # user erroneously confirms the impostor
                    hit = True; break
        fa += int(hit)
    return dict(task_success=succ / n, cmd_error=cmderr / n, abstain_rate=conf_any / n,
                mean_turns=turns_sum / n, decision_far=fa / n)


def main():
    data = load_pooled()
    gen, imp = pool_moderate(data)
    npos = sum(len(v) for v in gen.values()); nneg = len(imp)
    out = {"layer": LAYER, "n_pos": npos, "n_neg": nneg, "n_sim": N_SIM}
    print(f"#2/#3 REFRAME — moderate pooled, npos={npos} nneg={nneg}, wavlm-large L{LAYER}\n", flush=True)

    # ---- #2 SPRT
    print("=== #2 SPRT / k-consistent (decision-FAR<=5%, tau swept per (k,M)) ===", flush=True)
    print(f"{'k':>2} {'M':>2} {'tau':>7} {'eff_FRR':>8} {'dec_FAR':>8} {'mean_turns':>11}", flush=True)
    sprt = []
    for k, M in [(1, 1), (1, 2), (2, 2), (2, 3), (3, 3), (2, 4), (3, 4), (3, 5)]:
        tau = far_matched_tau_sprt(gen, imp, k, M)
        frr, far, turns = sim_sprt(gen, imp, tau, k, M)
        sprt.append(dict(k=k, M=M, tau=tau, eff_frr=frr, dec_far=far, mean_turns=turns))
        print(f"{k:>2} {M:>2} {tau:7.4f} {frr*100:7.1f}% {far*100:7.1f}% {turns:11.2f}", flush=True)
    out["sprt"] = sprt
    # best under <=2.0 mean turns
    adm = [r for r in sprt if r["mean_turns"] <= 2.0 and r["dec_far"] <= 0.05]
    best_sprt = min(adm, key=lambda r: r["eff_frr"]) if adm else None
    sprt_ok = bool(best_sprt and best_sprt["eff_frr"] <= 0.15)
    if best_sprt:
        print(f"  best @ <=2.0 turns: k={best_sprt['k']} M={best_sprt['M']} eff_FRR={best_sprt['eff_frr']*100:.1f}% "
              f"turns={best_sprt['mean_turns']:.2f} dec_FAR={best_sprt['dec_far']*100:.1f}%  "
              f"=> {'meets <=15%' if sprt_ok else 'MISSES <=15%'}", flush=True)

    # ---- #3 abstain+confirm. t_acc @ auto-accept-FAR<=1% (tight, executes without confirm). t_rej is the
    # RELAXED confirm boundary: the abstain band [t_acc,t_rej] goes through a confirm turn, so its impostor
    # leak is gated by pc. Sweep t_rej to the most permissive point with DECISION-FAR(pc=.1)<=5%.
    print("\n=== #3 abstain+confirm (t_acc @ auto-FAR<=1%; t_rej RELAXED to decision-FAR(pc=.1)<=5%) ===", flush=True)
    all_neg = sorted(s for _, s in imp)
    t_acc = all_neg[min(len(all_neg) - 1, int(0.01 * len(all_neg)))]
    # choose t_rej: most permissive quantile keeping decision_far(pc=.1)<=5%
    t_rej = t_acc
    for q in np.linspace(0.05, 0.7, 30):
        cand = all_neg[min(len(all_neg) - 1, int(q * len(all_neg)))]
        if sim_abstain(gen, imp, t_acc, cand, 0.10, M=2)["decision_far"] <= 0.05:
            t_rej = cand
    print(f"  t_acc={t_acc:.4f} t_rej={t_rej:.4f}", flush=True)
    print(f"{'pc':>5} {'task_succ':>10} {'abstain':>8} {'turns':>7} {'dec_FAR':>8} {'cmd_err':>8}", flush=True)
    abst = {}
    for pc in [0.0, 0.05, 0.10]:
        m = sim_abstain(gen, imp, t_acc, t_rej, pc, M=2)
        abst[f"pc{pc}"] = m
        print(f"{pc:>5.2f} {m['task_success']*100:9.1f}% {m['abstain_rate']*100:7.1f}% "
              f"{m['mean_turns']:7.2f} {m['decision_far']*100:7.1f}% {m['cmd_error']*100:7.1f}%", flush=True)
    out["abstain"] = abst
    out["abstain_thresholds"] = dict(t_acc=float(t_acc), t_rej=float(t_rej))
    m10 = abst["pc0.1"]
    abst_ok = bool(m10["task_success"] >= 0.85 and m10["abstain_rate"] < 0.20 and m10["decision_far"] <= 0.05)

    out["verdict"] = dict(sprt_best=best_sprt, sprt_meets_15=sprt_ok,
                          abstain_pc10=m10, abstain_meets_85=abst_ok, banked=False,
                          note="NOT-BANKED pending UASpeech #24")
    print(f"\n=== VERDICT === #2 SPRT meets eff-FRR<=15%@<=2turns? {'YES' if sprt_ok else 'NO'} | "
          f"#3 abstain meets ts>=85% & abstain<20% (pc=.1)? {'YES' if abst_ok else 'NO'}  "
          f"(both NOT-BANKED — pending UASpeech #24)", flush=True)
    with open(os.path.join(CACHE, "x23_reframe.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("wrote x23_reframe.json", flush=True)


if __name__ == "__main__":
    main()
