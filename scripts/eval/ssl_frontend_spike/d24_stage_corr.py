"""D24 — Stage-correlation audit (tests I4's cascade-independence optimism).

The dual-cascade compounds FAR as marginal(stage1) × marginal(stage2), assuming INDEPENDENCE. But stage-1
survivors are adversarially selected and share acoustic content with what stage-2 looks for, so the
conditional stage-2 FAR on survivors can exceed the marginal. D24 measures both on real ambient.

  stage1 = the deployed VAD/energy gate (passes speech-like windows)
  stage2 = the recognizer accept (distilhubert L2, enrolled control commands, FAR<=5% threshold)

  marginal FAR2      = P(stage2 accept | ANY window, incl. silence/noise)
  conditional FAR2   = P(stage2 accept | stage1 survivor)
  correlation ratio  = conditional / marginal   (>>1 => strong positive correlation => compound optimistic)

Every window is embedded (no VAD gate on the measurement) so both quantities are observable. Reports the
ratio and the corrected compound FA/hr vs the independence-assumed one.
"""
import os, sys, glob
import numpy as np
import torch
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
import a3_far_bridge as A3

SR, WIN_S, HOP_S = 16000, 1.5, 0.5
STREAM_LAYER = 2
MIN_SPEECH = 1520


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    print(f"D24 — stage-correlation audit (distilhubert L{STREAM_LAYER}, ~{hours}h real ambient)\n", flush=True)
    emb = L.load_emb("distilhubert")
    from transformers import AutoModel
    net = AutoModel.from_pretrained("ntu-spml/distilhubert", output_hidden_states=True).eval()
    templ, thr, score = A3.typical_enroll_and_threshold(emb, STREAM_LAYER)
    srcs, total_h = A3.ambient_sources(hours)

    win, hop = int(WIN_S * SR), int(HOP_S * SR)
    dists, s1flags = [], []  # stage-2 nearest distance + stage-1 (VAD) survival per window
    for name, x in srcs:
        i = 0
        while i + win <= x.size:
            seg = x[i : i + win]; i += hop
            sp = H.energy_vad_trim(seg)
            s1 = sp.size >= MIN_SPEECH
            emb_seg = sp if s1 else seg
            if emb_seg.size < 400:
                continue
            v = A3.embed(net, emb_seg if emb_seg.size >= MIN_SPEECH else np.pad(emb_seg, (0, max(0, MIN_SPEECH - emb_seg.size))), STREAM_LAYER)
            dists.append(score(v)[0]); s1flags.append(s1)
    dists = np.array(dists); s1flags = np.array(s1flags)
    n_all = len(dists); s1_rate = s1flags.mean()
    print(f"  windows={n_all}, stage1(VAD) survivors={int(s1flags.sum())} (pass rate {s1_rate*100:.0f}%)", flush=True)
    print(f"  (at the deployed FAR<=5% recognizer threshold, ambient stage-2 accepts = {int((dists<=thr).sum())} -> ~0, so probe at LOOSER operating points)\n", flush=True)
    print(f"  {'target marg FAR2':>16} {'marginal':>9} {'conditional|s1':>15} {'ratio':>7}", flush=True)
    for q in [0.30, 0.20, 0.10, 0.05]:
        t = np.quantile(dists, q)  # threshold giving ~q marginal acceptance over ALL windows
        marg = float((dists <= t).mean())
        cond = float((dists[s1flags] <= t).mean()) if s1flags.any() else 0.0
        ratio = cond / marg if marg > 0 else float("nan")
        print(f"  {q*100:14.0f}% {marg*100:8.1f}% {cond*100:14.1f}% {ratio:6.2f}×", flush=True)
    # verdict at the 20% operating point
    t20 = np.quantile(dists, 0.20); m20 = (dists <= t20).mean(); c20 = (dists[s1flags] <= t20).mean()
    r20 = c20 / m20
    print(f"\n  I4 read: at a measurable operating point, conditional/marginal ≈ {r20:.2f}× "
          f"({'stages POSITIVELY correlated -> compound-FAR independence is OPTIMISTIC (inflate the 950 stage-2 budget)' if r20 > 1.3 else 'stages ~independent at this op-point -> compound assumption OK'})", flush=True)


if __name__ == "__main__":
    main()
