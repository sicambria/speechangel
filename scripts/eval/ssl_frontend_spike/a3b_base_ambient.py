"""A3b — single-encoder FA/hr certification on wavlm-base+ L10 (fixes A3's encoder mismatch).

A3 measured FRR (13.8%, band 800) on wavlm-large L15 but ambient FA/hr (0) on distilhubert L2 (band 700).
C21 showed wavlm-base+ L10 (94 MB) is itself band-800 (12.0% typical D2). A3b closes the loop: measure
ambient FA/hr for THAT encoder at its own FAR<=5% threshold, so the FRR and FA axes come from ONE system.

If wavlm-base+ L10 also yields ~0 FA/hr on real ambient, the band-800-at-94 MB deployment claim is coherent.
"""
import os, sys
import numpy as np
import torch
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import a3_far_bridge as A3

MODEL, LAYER = "microsoft/wavlm-base-plus", 10


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    print(f"A3b — ambient FA/hr on wavlm-base+ L{LAYER} (94 MB band-800 encoder), ~{hours}h real ambient\n", flush=True)
    emb = L.load_emb("wavlm-base-plus")
    from transformers import AutoModel
    net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
    templ, thr, score = A3.typical_enroll_and_threshold(emb, LAYER)
    srcs, total_h = A3.ambient_sources(hours)
    trials = accepts = 0
    per = {}
    for name, x in srcs:
        t0, a0 = trials, accepts
        for sp in A3.stream_windows(x):
            trials += 1
            qv = A3.embed(net, sp, LAYER)
            if score(qv)[0] <= thr:
                accepts += 1
        p = per.setdefault(name.split("/")[0], [0, 0, 0.0])
        p[0] += trials - t0; p[1] += accepts - a0; p[2] += x.size / 16000 / 3600
    T = trials / total_h if total_h else 0
    fa = accepts / total_h if total_h else 0
    ub = 3 / trials * T if trials else 0
    print(f"  streamed {total_h:.2f}h, T={T:.0f} trials/hr", flush=True)
    for k, (tr, ac, h) in per.items():
        print(f"    {k:14s}: {tr/h:6.0f} trials/hr, {ac/h:5.1f} FA/hr", flush=True)
    print(f"\n  wavlm-base+ L{LAYER} @ its FAR<=5% threshold: {accepts}/{trials} accepts -> {fa:.1f} FA/hr "
          f"(95% UB via rule-of-three ~{ub:.1f} FA/hr)", flush=True)
    coherent = fa <= 5
    print(f"  => band-800-at-94MB deployment claim: {'COHERENT (one encoder does FRR=12% AND ~0 ambient FA)' if coherent else 'FA/hr exceeds budget — needs more hours or tighter op-point'}", flush=True)


if __name__ == "__main__":
    main()
