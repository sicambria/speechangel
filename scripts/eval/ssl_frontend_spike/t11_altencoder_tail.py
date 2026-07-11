"""T11 — Alternate large-encoder wall-confirmer: does a DIFFERENT SSL objective rescue the SAME
2-3 hard typical speakers where wavlm-large fails?

The strongest intrinsic-vs-wavlm-specific test (advisor-gated typical-900 program). wavlm-large is
masked-speech-denoising + gated relative-position; wav2vec2-large-xlsr-53 is contrastive + multilingual
(53 languages) — a genuinely different representation geometry, teacher-scale (315M), cached locally.
If the two hard speakers (98ea0818 never-below-23%@any-wavlm-layer, 2aca1e72 flat 19-29%) are ALSO hard
under xlsr, their tail is a property of the speech, not of wavlm — the wall is representation-general.
If xlsr moves >=2 of them at matched FAR, wavlm is the wrong encoder for the tail and that becomes a
pre-registered lever needing fresh confirmation.

Identical GSC-19/K5 manifest (change-one-variable, EVAL-004); reuses t10 encode+eval. Baseline =
wavlm-large L12/K5 = 5.81%; band 900 = FRR<=5% (DomainBands.kt spec 2). FAR-matched, per-hard-speaker.
"""
import os, sys, json
import numpy as np
import cand_lib as L
from a5_gsc_kcurve import kcurve_speaker
from t10_c3_student import manifest_from_picks, build_student_cache, eval_student

MODEL_ID = "facebook/wav2vec2-large-xlsr-53"
NAME = "xlsr53"
K = 5
DEPLOY_L = 12
HARD = ["98ea0818", "2aca1e72", "c1d39ce8"]


def main():
    man, need = manifest_from_picks()
    print(f"T11 ALT-ENCODER WALL-CONFIRMER — {MODEL_ID} vs wavlm-large 5.81%\n", flush=True)
    print(f"  {len(man)} speakers, {len(need)} clips (identical GSC-19 manifest)\n", flush=True)
    # teacher hard-speaker FRR (from cache) for the side-by-side
    from a5_gsc_kcurve import build_cache
    _, temb = build_cache()
    teach_hard = {h: next((kcurve_speaker(man[s], temb, K, layer=DEPLOY_L)[0]
                           for s in man if s.startswith(h[:8])), None) for h in HARD}

    cache = os.path.join(L.CACHE, f"gsc_{NAME}_alllayers.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True); emb = {k: z[k] for k in z.files}
        if not all(p in emb for p in need):
            emb = build_student_cache(MODEL_ID, need); np.savez(cache, **emb)
    else:
        emb = build_student_cache(MODEL_ID, need); np.savez(cache, **emb)

    (bl, agg, fa, per_spk), per_layer = eval_student(NAME, man, emb)
    band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
    print(f"  {NAME}: best L{bl}  aggregate FRR {agg*100:.2f}%  FAR {fa*100:.1f}%  band {band}  "
          f"(wavlm-large 5.81%)\n", flush=True)
    print(f"  HARD-SPEAKER side-by-side (best xlsr layer L{bl}):", flush=True)
    moved = 0
    hard_rows = {}
    for h in HARD:
        s = next((s for s in man if s.startswith(h[:8])), None)
        xf, tf = per_spk.get(s), teach_hard[h]
        better = xf is not None and tf is not None and xf < tf - 1e-6
        moved += int(better)
        hard_rows[h] = {"xlsr": xf, "wavlm": tf}
        print(f"    {h[:8]}  xlsr {xf*100:>4.0f}%  vs wavlm {tf*100:>4.0f}%  {'BETTER' if better else 'same/worse'}", flush=True)
    verdict = ("xlsr MOVES >=2 hard speakers — wavlm may be wrong encoder for the tail (pre-register + confirm)"
               if moved >= 2 else
               "SAME speakers hard under a different SSL objective — tail is representation-GENERAL (wall)")
    print(f"\n  hard speakers improved: {moved}/3\n  VERDICT: {verdict}", flush=True)
    with open(os.path.join(L.CACHE, "t11_altencoder_tail.json"), "w") as f:
        json.dump({"model": MODEL_ID, "best_layer": bl, "agg_frr": agg, "agg_far": fa, "band": band,
                   "hard": hard_rows, "hard_moved": moved, "verdict": verdict,
                   "per_layer": {str(l): per_layer[l] for l in per_layer}}, f, indent=2)
    print("\n  wrote t11_altencoder_tail.json", flush=True)


if __name__ == "__main__":
    main()
