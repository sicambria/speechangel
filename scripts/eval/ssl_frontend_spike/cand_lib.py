"""Shared library for the §13 candidate-experiments campaign.

Loads cached SSL embeddings + TORGO command/negative structure with word+session+speaker metadata,
and provides the banked scoring primitives (few-shot cosine 1-NN, min-over-K aggregation, margin
cross-verify, held-out global threshold @FAR<=target) reused across A/B/E/F experiments.

All experiments import from here so the matcher/protocol is identical across arms (EVAL-003: only the
one variable under test changes).
"""
import os, re, math, glob, json
import numpy as np
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
TORGO = os.path.expanduser("~/torgo")
DYS = ["F01", "F03", "F04"]
CTL = ["FC01", "FC02", "FC03"]
FAR_TARGET = 0.05


# ---------------------------------------------------------------- embeddings

def load_emb(model="wavlm-large"):
    """wav path -> (n_layers, dim) unit-vector array (mean-pooled per layer)."""
    z = np.load(os.path.join(CACHE, f"{model}.npz"), allow_pickle=True)
    return {k: z[k] for k in z.files}


def load_speaker(spk):
    root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
    return H.scan(root).get(spk)


def session_of(wav):
    m = re.search(r"/(Session\d+)/", wav)
    return m.group(1) if m else "Session?"


# ---------------------------------------------------------------- speaker command table with meta

def command_table(spk, emb, layer, min_reps=2):
    """Return {word: [(wav, vec, session)]} for a speaker at a given layer, plus negatives list.
    Only utts present in the embedding cache are kept."""
    d = load_speaker(spk)
    if not d:
        return {}, []
    cmds = {}
    for w, wavs in d["commands"].items():
        reps = [(x, emb[x][layer], session_of(x)) for x in wavs if x in emb]
        if len(reps) >= min_reps:
            cmds[w] = reps
    negs = [(x, emb[x][layer], session_of(x)) for x in d["negatives"] if x in emb]
    return cmds, negs


# ---------------------------------------------------------------- scoring primitives

def cos(a, b):
    return 1.0 - float(a @ b)


def score_query(qv, enroll, agg="min"):
    """enroll = {word: [vec,...]}. Return sorted [(dist, word)] using aggregation `agg` over templates.
    agg in {min, softmin, mean2, mean, median, kofK}."""
    out = []
    for w, vecs in enroll.items():
        ds = sorted(cos(qv, t) for t in vecs)
        if agg == "min":
            s = ds[0]
        elif agg == "mean":
            s = float(np.mean(ds))
        elif agg == "median":
            s = float(np.median(ds))
        elif agg == "mean2":
            s = float(np.mean(ds[:2])) if len(ds) >= 2 else ds[0]
        elif agg == "softmin":
            # temperature-weighted soft-min (logsumexp of -d/T)
            T = 0.05
            arr = np.array(ds)
            s = -T * float(np.log(np.mean(np.exp(-arr / T))))
        else:
            s = ds[0]
        out.append((s, w))
    out.sort()
    return out


def held_out_frr_far(pos_rows, neg_rows, folds_pos, folds_neg, accept_builder, target=FAR_TARGET):
    """Generic leave-one-fold-out evaluator.

    pos_rows[i]=(fold, truth, scored_list); neg_rows[j]=(fold, None, scored_list).
    accept_builder(train_pos, train_neg, target) -> accept_fn(scored_row)->bool with FAR<=target on train.
    Returns aggregate (frr, far, npos, nneg).
    """
    fold_ids = sorted(set(folds_pos) | set(folds_neg))
    acc = pos = fa = neg = 0
    P = list(zip(folds_pos, pos_rows))
    N = list(zip(folds_neg, neg_rows))
    for f in fold_ids:
        tr_p = [r for g, r in P if g != f]
        tr_n = [r for g, r in N if g != f]
        te_p = [r for g, r in P if g == f]
        te_n = [r for g, r in N if g == f]
        # accept_builder consumes bare scored lists (fit the FAR<=target threshold on train negatives)
        accept = accept_builder([s for _, s in tr_p], [s for _, s in tr_n], target)
        for truth, scored in te_p:
            pos += 1
            if scored and accept(scored) and scored[0][1] == truth:
                acc += 1
        for _, scored in te_n:
            neg += 1
            if scored and accept(scored):
                fa += 1
    frr = 0.0 if pos == 0 else 1.0 - acc / pos
    far = 0.0 if neg == 0 else fa / neg
    return frr, far, pos, neg


def global_threshold_accept(train_pos, train_neg, target=FAR_TARGET):
    """Largest d1 threshold s.t. FAR over train negatives <= target. Returns accept_fn(scored)."""
    cands = sorted({s[0][0] for s in train_neg if s} | {s[0][0] for s in train_pos if s})
    thr = (cands[0] - 1.0) if cands else 0.0
    negs = [s for s in train_neg if s]
    for t in cands:
        if not negs:
            thr = t
            continue
        fa = sum(1 for s in negs if s[0][0] <= t) / len(negs)
        if fa <= target:
            thr = t
    return lambda scored, thr=thr: bool(scored) and scored[0][0] <= thr


# ---------------------------------------------------------------- fold assignment (round-robin per word)

def make_folds(cmds, negs, k=5):
    """Round-robin fold ids (matches harness.folds semantics): query i of a word -> fold i%k; each
    query is scored against the OTHER folds' reps of every word (few-shot enroll = leave-fold-out).
    Returns (queries, negatives) where each query = (fold, word, qvec, enroll_dict) lazily built.

    Here we return raw structures; callers build enroll per fold to control aggregation/K.
    """
    # index reps per word
    return cmds, negs, k
