"""#1 (Tier A) — TASK-SUCCESS-WITH-CONFIRM metric for the D2 moderate wall.

The Round-4 verdict: voice-only SINGLE-SHOT verification is tail-capped — moderate FRR@FAR<=5% ~62.7%,
i.e. single-shot task-success = 1-FRR = **37.3%**. This experiment asks the plan's highest-EV question:
does the product become shippable once we stop demanding one-shot accept and instead allow **<=2 attempts
+ a confirm turn** ("did you mean X?")?

PINNED ACCOUNTING (advisor-locked, before running — a confirm turn must NOT swallow errors for free):
  A decision = one command the user is trying to issue. Per attempt at operating threshold tau, the
  recognizer produces (winner w1, score s1). Three cases:
    accept-correct : w1==truth and s1<=tau
    accept-wrong   : w1!=truth and s1<=tau   (an in-vocab confusion)
    reject         : s1>tau
  A confirm turn fires on EVERY accept and is itself imperfect: confirm-error rate p_c (symmetric — the
  user erroneously says "no" to a correct proposal, or "yes" to a wrong one, with prob p_c). So:
    accept-correct -> executes correct w.p. (1-p_c); else user wrongly rejects -> retry
    accept-wrong   -> executes WRONG (task fail + false action) w.p. p_c; else caught -> retry
    reject         -> retry
  Up to K=2 attempts (attempt 2 = an independent rep of the same word). Reported JOINTLY (never a bare %):
    task_success   = P(correct command executed within <=2 attempts)
    mean_turns     = E[utterances + confirm turns] spent per decision   <- the cost the confirm hides
    confirm_rate   = P(>=1 confirm turn fired)
    raw_far        = per-utterance impostor accept rate (the confirm GATE INPUT; matched to the 5% budget)
    residual_far   = executed false action on an impostor decision = 1-(1-raw_far*p_c)^K   <- safety
    cmd_error      = P(WRONG command executed on a genuine decision)                       <- safety
  p_c is swept {0.00, 0.05, 0.10}: p_c=0 is the optimistic (perfect-confirm) bound; p_c=0.10 is a
  plausible dysarthric yes/no confirm-error and exposes the residual FAR the confirm cannot hide.

  Per-attempt outcome probabilities are estimated empirically over the moderate held-out positives /
  negatives (LOFO, pooled wavlm-large L14, same rows as R3). The <=2-attempt combination assumes the two
  attempts are independent draws of the word — an approximation (stated), reasonable since folds are
  disjoint reps. Baseline fidelity: at the A0 threshold, K=1, p_c=0 the task_success must reproduce
  1-FRR(A0)=37.3% moderate.

VERDICT BAR: moderate task_success >= 85% at raw_far<=5%, with mean_turns and residual_far(p_c=.1) reported.
NOT-BANKED regardless (pending UASpeech #24); this quantifies the reframe, it does not bank a lever.
"""
import os, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
LAYER = 14
SEVERITY = {"M03": "mild", "M01": "moderate", "M02": "moderate", "M04": "severe", "M05": "very_severe",
            "F04": "mild", "F03": "moderate", "F01": "severe"}
FEMALE = ["F01", "F03", "F04"]
MALE = ["M01", "M02", "M03", "M04", "M05"]
MODERATE = ["M01", "M02", "F03"]
K_ATTEMPTS = 2
PCS = [0.0, 0.05, 0.10]


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
    """LOFO winner+score rows: (fold, truth_word_or_None, winner_word, score). Lower score = genuine."""
    cmds = data_spk["commands"]; negs = data_spk["negatives"]
    words = list(cmds)
    rows = []
    for f in range(k):
        enroll = {}
        pos = []
        for w in words:
            for i, v in enumerate(cmds[w]):
                (pos.append((w, v)) if i % k == f else enroll.setdefault(w, []).append(v))
        enroll = {w: v for w, v in enroll.items() if v}
        if not enroll:
            continue
        def score(v):
            d = {w: min(1.0 - float(v @ tv) for tv in tvs) for w, tvs in enroll.items()}
            w1 = min(d, key=d.get)
            return w1, d[w1]
        for w, v in pos:
            w1, s = score(v); rows.append((f, w, w1, s))
        for v in negs:
            w1, s = score(v); rows.append((f, None, w1, s))
    return rows


def far_matched_threshold(rows, far_target=0.05):
    """Single global tau at held-out FAR<=target (LOFO), returns per-fold thresholds averaged into one
    operating tau by pooling — we fit ONE tau on all negatives (deployment threshold), report realized."""
    negs = [r[3] for r in rows if r[1] is None]
    if not negs:
        return None
    cands = sorted(set(r[3] for r in rows))
    thr = cands[0] - 1.0
    for t in cands:
        fa = sum(1 for s in negs if s <= t) / len(negs)
        if fa <= far_target:
            thr = t
    return thr


def per_attempt_probs(rows, tau):
    """Empirical per-attempt outcome probabilities at threshold tau (pooled over the given rows)."""
    pos = [r for r in rows if r[1] is not None]
    neg = [r for r in rows if r[1] is None]
    n_pos = len(pos); n_neg = len(neg)
    acc_correct = sum(1 for r in pos if r[3] <= tau and r[2] == r[1]) / max(1, n_pos)
    acc_wrong = sum(1 for r in pos if r[3] <= tau and r[2] != r[1]) / max(1, n_pos)
    reject = 1.0 - acc_correct - acc_wrong
    raw_far = sum(1 for r in neg if r[3] <= tau) / max(1, n_neg)
    return dict(acc_correct=acc_correct, acc_wrong=acc_wrong, reject=reject, raw_far=raw_far,
                n_pos=n_pos, n_neg=n_neg)


def reframe_metrics(p, pc, K=K_ATTEMPTS):
    """Task-success + costs for the <=K-attempt + confirm protocol given per-attempt probs p and
    confirm-error pc. Attempts assumed independent (stated approximation)."""
    ac, aw, rj = p["acc_correct"], p["acc_wrong"], p["reject"]
    # per-attempt terminal outcomes:
    exec_correct = ac * (1 - pc)                 # correct executed
    exec_wrong = aw * pc                         # wrong command executed (task fail + false action)
    retry = ac * pc + aw * (1 - pc) + rj         # confirm bounced OR reject -> another attempt
    # confirm fires on any accept:
    p_confirm_attempt = ac + aw
    # <=K attempts: success if any attempt executes correct before a terminal wrong-execute.
    succ = 0.0; cmderr = 0.0; exp_turns = 0.0; p_reach = 1.0; p_conf_any = 0.0
    for _ in range(K):
        succ += p_reach * exec_correct
        cmderr += p_reach * exec_wrong
        exp_turns += p_reach * (1.0 + p_confirm_attempt)      # 1 utterance + (confirm if accepted)
        p_conf_any += p_reach * p_confirm_attempt
        p_reach *= retry                                       # only retries continue
    raw_far = p["raw_far"]
    residual_far = 1.0 - (1.0 - raw_far * pc) ** K
    return dict(task_success=succ, cmd_error=cmderr, mean_turns=exp_turns,
                confirm_rate=min(1.0, p_conf_any), raw_far=raw_far, residual_far=residual_far)


def main():
    data = load_pooled()
    spks = [s for s in FEMALE + MALE if s in data]
    # aggregate moderate rows across speakers (pooled per-attempt probs for the cell), and per-speaker.
    print(f"#1 TASK-SUCCESS-WITH-CONFIRM — wavlm-large L{LAYER}, <=2 attempts, moderate=live\n", flush=True)
    out = {"layer": LAYER, "K": K_ATTEMPTS, "pcs": PCS, "far_target": 0.05, "per_speaker": {}, "moderate": {}}

    # FIDELITY GATE: at A0 tau, K=1, pc=0, task_success must == 1-FRR(A0).
    fid = []
    for s in MODERATE:
        rows = build_rows(data[s])
        tau = far_matched_threshold(rows)
        p = per_attempt_probs(rows, tau)
        ts1 = reframe_metrics(p, pc=0.0, K=1)["task_success"]
        fid.append(ts1)
        out["per_speaker"][s] = {"tau": tau, "raw_far": p["raw_far"], "acc_correct": p["acc_correct"]}
    fid_mean = float(np.mean(fid))
    print(f"[fidelity] moderate single-shot task_success (K=1,pc=0) = {fid_mean*100:.1f}%  "
          f"(expect ~37.3% = 1-FRR(A0)); per-spk {[f'{x*100:.1f}' for x in fid]}", flush=True)

    # main sweep: pool moderate rows, report task-success at the FAR<=5% operating tau across pc.
    pooled_rows = []
    fold_off = 0
    for s in MODERATE:
        for r in build_rows(data[s]):
            pooled_rows.append((r[0] + fold_off, r[1], r[2], r[3]))
        fold_off += 100
    tau = far_matched_threshold(pooled_rows)
    p = per_attempt_probs(pooled_rows, tau)
    print(f"\n[moderate pooled] tau={tau:.4f}  raw_far={p['raw_far']*100:.1f}%  "
          f"acc_correct={p['acc_correct']*100:.1f}%  acc_wrong={p['acc_wrong']*100:.1f}%  "
          f"reject={p['reject']*100:.1f}%  (npos={p['n_pos']} nneg={p['n_neg']})", flush=True)
    print(f"\n{'pc':>5} {'task_succ':>10} {'mean_turns':>11} {'confirm_rt':>11} "
          f"{'raw_far':>8} {'resid_far':>10} {'cmd_err':>8}", flush=True)
    for pc in PCS:
        for K in (1, 2):
            m = reframe_metrics(p, pc, K=K)
            tag = f"pc={pc:.2f} K={K}"
            print(f"{tag:>10} {m['task_success']*100:9.1f}% {m['mean_turns']:11.2f} "
                  f"{m['confirm_rate']*100:10.1f}% {m['raw_far']*100:7.1f}% "
                  f"{m['residual_far']*100:9.1f}% {m['cmd_error']*100:7.1f}%", flush=True)
            out["moderate"][f"pc{pc}_K{K}"] = m

    # THE REFRAME: the confirm turn lets us RELAX tau (catches the extra false-accepts). Sweep tau and
    # find the operating point maximizing task-success subject to a RESIDUAL-far budget (executed false
    # actions after confirm, at pc=0.10) <=5% and a turn budget mean_turns<=3.0. This is the honest test.
    print(f"\n[tau sweep — the reframe: relax accept threshold, confirm+retry absorbs the extra FAR]", flush=True)
    print(f"{'raw_far':>8} {'ts_K2_pc0':>10} {'ts_K2_pc.1':>11} {'turns':>7} {'resid_far.1':>12} {'cmd_err.1':>10}", flush=True)
    all_neg = sorted(r[3] for r in pooled_rows if r[1] is None)
    frontier = []
    for q in [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70]:
        t = all_neg[min(len(all_neg) - 1, int(q * len(all_neg)))]
        pp = per_attempt_probs(pooled_rows, t)
        m0 = reframe_metrics(pp, pc=0.0, K=2); m1 = reframe_metrics(pp, pc=0.10, K=2)
        row = dict(tau=t, raw_far=pp["raw_far"], ts_pc0=m0["task_success"], ts_pc10=m1["task_success"],
                   mean_turns=m1["mean_turns"], residual_far_pc10=m1["residual_far"], cmd_err_pc10=m1["cmd_error"])
        frontier.append(row)
        print(f"{pp['raw_far']*100:7.1f}% {m0['task_success']*100:9.1f}% {m1['task_success']*100:10.1f}% "
              f"{m1['mean_turns']:7.2f} {m1['residual_far']*100:11.1f}% {m1['cmd_error']*100:9.1f}%", flush=True)
    out["tau_frontier"] = frontier
    # best operating point under the honest budget: residual_far(pc=.1)<=5% AND mean_turns<=3.0
    admissible = [r for r in frontier if r["residual_far_pc10"] <= 0.05 and r["mean_turns"] <= 3.0]
    op = max(admissible, key=lambda r: r["ts_pc10"]) if admissible else None

    # verdict: headline at K=2, pc=0 (bound) and pc=0.10 (charged); raw_far matched to 5%.
    best = reframe_metrics(p, pc=0.0, K=2)
    charged = reframe_metrics(p, pc=0.10, K=2)
    banked = bool(op and op["ts_pc10"] >= 0.85)
    out["verdict"] = dict(fidelity_ts1=fid_mean, tau_far5=tau, moderate_ts_K2_pc0_far5=best["task_success"],
                          moderate_ts_K2_pc10_far5=charged["task_success"],
                          best_op=op, reaches_85=banked, banked=False,
                          note="NOT-BANKED pending UASpeech #24")
    print(f"\n=== VERDICT (#1) ===", flush=True)
    print(f"  at raw_far<=5% (tight): task_success K=2 = {best['task_success']*100:.1f}% (pc=0) / "
          f"{charged['task_success']*100:.1f}% (pc=.10), mean_turns={best['mean_turns']:.2f}", flush=True)
    if op:
        print(f"  best op under residual_far(pc=.1)<=5% & turns<=3: raw_far={op['raw_far']*100:.1f}%  "
              f"task_success={op['ts_pc10']*100:.1f}% (pc=.1) / {op['ts_pc0']*100:.1f}% (pc=0)  "
              f"turns={op['mean_turns']:.2f}  residual_far={op['residual_far_pc10']*100:.1f}%", flush=True)
    print(f"  reaches >=85% task-success under the honest budget? {'YES' if banked else 'NO'}  "
          f"(NOT-BANKED regardless — pending UASpeech #24)", flush=True)
    with open(os.path.join(CACHE, "x1_task_success_confirm.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("wrote x1_task_success_confirm.json", flush=True)


if __name__ == "__main__":
    main()
