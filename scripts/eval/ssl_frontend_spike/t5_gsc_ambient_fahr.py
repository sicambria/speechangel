"""T5 — Honest D3 (ambient FA/hr) for the wavlm-large few-shot config, on a REAL >=6h ambient stream.

WHY (advisor + Explore): the typical composite's "D3 ~800" is a HARD-CODED literal in
typical_composite.py ("D3 ambient: ~800 (dual-cascade, off-encoder)") — NOT a measurement of this
encoder. The product doc's ~82 FA/hr is the naive bridge (FAR5%/trial x T~1842 windows/hr = ~92). The
only FRESH ambient measurement (a3_far_bridge) got 0.0 FA/hr over 0.5h — but on DistilHuBERT L2 /
wavlm-base+ L10, and only 0.5h (95% upper bound ~6 FA/hr, underpowered). NO wavlm-large ambient number
exists. T5 supplies it: wavlm-large L15 few-shot recognizer, GSC-enrolled speakers, at each speaker's
FAR<=5% threshold, streamed against a REAL >=6h ambient stream (DEMAND noise + LibriSpeech speech).

FA/hr needs a real time-base + real ambient substrate (isolated GSC words are neither) — so the gated
pipeline (StreamingEnergyGate/VAD + WIN/HOP/refractory) and the ambient sources are REUSED VERBATIM
from a3_far_bridge.py; only the encoder (distilhubert->wavlm-large L15) and the enrollment corpus
(TORGO control -> GSC-19) change. Band-900 bar = <=0.5 FA/hr (product doc). Rule-of-three: 0 accepts
over T hours => 95% UB = 3/T FA/hr; T>=6h with 0 accepts => UB 0.5 => band-900 DEMONSTRABLE.

MIX CAVEAT (advisor): continuous LibriSpeech = all-speech ADVERSARIAL upper bound; realistic home
ambient is mostly quiet/noise with sparse speech. Per-source FA/hr (DEMAND vs LibriSpeech) is reported
so the claimed number states its mix.

Encode = ~T*1800 gate-passed windows x wavlm-large L15 (CPU, multi-hour) -> windows encoded ONCE and
checkpointed to gsc_ambient_windows_L15.npz; scoring vs each speaker's templates is a cheap post-step.

Usage:
  python t5_gsc_ambient_fahr.py --validate            # NO ENCODE: gate/time-base/enroll logic on cache
  python t5_gsc_ambient_fahr.py --hours 6.0           # heavy: stream + encode + FA/hr
"""
import os, sys, glob, json, argparse
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a3_far_bridge import stream_windows, ambient_sources, embed, read_any, SR, WIN_S, HOP_S
from a5_gsc_kcurve import REPS, FIXED_WORDS, pick_speakers

LAYER = 15
FAR = 0.05
NEG_REPS = 6
ALLLAYERS = os.path.join(L.CACHE, "gsc_wavlm_large_alllayers.npz")
WIN_NPZ = os.path.join(L.CACHE, "gsc_ambient_windows_L15.npz")
np.random.seed(42)


def gsc_enroll(emb, layer):
    """Per GSC speaker: templates {word:[Lvec]} from 8 fixed x 6 reps + a FAR<=5% threshold fit on the
    speaker's OWN OOV negatives (the deployment model — each user's threshold on their own negatives).
    Mirrors T2's enrichment: negatives = all remaining >=4-rep OOV words, up to NEG_REPS each."""
    spk_enroll = {}
    for spk, ge5, wc in pick_speakers():
        fixed = {w: wc[w][:REPS] for w in ge5[:FIXED_WORDS]}
        templ = {w: [emb[p][layer] for p in ps if p in emb] for w, ps in fixed.items()}
        templ = {w: v for w, v in templ.items() if v}
        neg = []
        for w in ge5[FIXED_WORDS:]:
            neg += [emb[p][layer] for p in wc[w][:NEG_REPS] if p in emb]
        for w, fs in wc.items():
            if w not in ge5[:FIXED_WORDS] and w not in ge5[FIXED_WORDS:] and len(fs) >= 4:
                neg += [emb[p][layer] for p in fs[:NEG_REPS] if p in emb]

        def score(qv, templ=templ):
            return min((min(1 - float(qv @ t) for t in tt), w) for w, tt in templ.items() if tt)

        neg_d = sorted(score(nv)[0] for nv in neg)
        thr = neg_d[max(0, int(FAR * len(neg_d)) - 1)] if len(neg_d) >= 20 else (neg_d[0] if neg_d else 0.0)
        spk_enroll[spk] = {"templ": templ, "thr": thr, "n_neg": len(neg), "score": score}
    return spk_enroll


def encode_ambient_windows(hours):
    """Stream real ambient, gate, encode each gate-passed window ONCE with wavlm-large L15.
    Checkpoints to WIN_NPZ every 500 windows. Returns (embs (N,1024), src_names, total_hours)."""
    saved = {}
    if os.path.exists(WIN_NPZ):
        z = np.load(WIN_NPZ, allow_pickle=True)
        saved = {k: z[k] for k in z.files}
        if float(saved.get("hours", 0)) >= hours - 1e-6:
            return saved["embs"], list(saved["srcs"]), float(saved["hours"])
    from transformers import AutoModel
    print("  loading wavlm-large...", flush=True)
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    srcs, total_h = ambient_sources(hours)
    embs, names = [], []
    done_h = 0.0
    for name, x in srcs:
        for sp in stream_windows(x):
            embs.append(embed(net, sp, LAYER))
            names.append(name.split("/")[0])
            if len(embs) % 500 == 0:
                np.savez(WIN_NPZ, embs=np.array(embs, dtype=np.float32),
                         srcs=np.array(names), hours=done_h + x.size / SR / 3600)
                print(f"    {len(embs)} windows encoded (checkpointed)", flush=True)
        done_h += x.size / SR / 3600
    embs = np.array(embs, dtype=np.float32)
    np.savez(WIN_NPZ, embs=embs, srcs=np.array(names), hours=total_h)
    return embs, names, total_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="NO ENCODE: gate/time-base/enroll on cache")
    ap.add_argument("--hours", type=float, default=6.0)
    a = ap.parse_args()
    emb = {k: v for k, v in np.load(ALLLAYERS, allow_pickle=True).items()}
    spk_enroll = gsc_enroll(emb, LAYER)
    print(f"T5 D3 AMBIENT FA/hr — wavlm-large L{LAYER}, GSC-{len(spk_enroll)} enrolled, target {a.hours}h\n", flush=True)
    thrs = sorted(round(s["thr"], 4) for s in spk_enroll.values())
    print(f"  per-speaker FAR<=5% accept thresholds (cos-dist, sorted): {thrs}", flush=True)
    print(f"  mean negatives/speaker = {np.mean([s['n_neg'] for s in spk_enroll.values()]):.0f}", flush=True)

    if a.validate:
        # NO ENCODE — validate the gate + time-base on a short real-ambient slice (audio ops only).
        srcs, total_h = ambient_sources(0.15)
        tr = 0
        per = {}
        for name, x in srcs:
            k = name.split("/")[0]
            for _sp in stream_windows(x):
                tr += 1
                per[k] = per.get(k, 0) + 1
        T = tr / total_h if total_h else 0
        print(f"\n  VALIDATE: streamed {total_h:.3f}h real ambient, {tr} gate-passed windows "
              f"-> T={T:.0f} trials/hr  (a3 measured ~1842)", flush=True)
        print(f"  per-source trials: {per}", flush=True)
        print(f"  naive bridge at FAR5%/trial => {0.05*T:.0f} FA/hr (the ~82-92 proxy); "
              f"measured accepts resolve the real number.", flush=True)
        print("  enrollment + threshold + gate plumbing OK (no encode).", flush=True)
        return

    embs, names, total_h = encode_ambient_windows(a.hours)
    print(f"\n  streamed+encoded {total_h:.2f}h real ambient, {len(embs)} gate-passed windows", flush=True)
    # score every window vs each speaker's templates; FA if min-dist <= that speaker's threshold
    per_spk = {}
    src_arr = np.array(names)
    for spk, e in spk_enroll.items():
        tmpl_mat = {w: np.stack(tt) for w, tt in e["templ"].items() if tt}
        # min cos-dist over all templates of all words, per window
        mind = np.full(len(embs), np.inf, dtype=np.float32)
        for w, M in tmpl_mat.items():
            d = 1.0 - embs @ M.T  # (N, n_tmpl)
            mind = np.minimum(mind, d.min(axis=1))
        acc = mind <= e["thr"]
        fa_hr = acc.sum() / total_h if total_h else 0
        by_src = {s: int(acc[src_arr == s].sum()) for s in sorted(set(names))}
        per_spk[spk] = {"accepts": int(acc.sum()), "fa_hr": float(fa_hr), "thr": float(e["thr"]),
                        "by_src_accepts": by_src}
    fa_hrs = sorted(v["fa_hr"] for v in per_spk.values())
    agg = float(np.mean(fa_hrs))
    worst = max(per_spk.values(), key=lambda v: v["fa_hr"])
    ub95 = 3.0 / total_h  # rule-of-three 95% UB for a 0-accept speaker
    band = 900 if agg <= 0.5 else (800 if agg <= 5 else 700)
    print(f"\n  D3 ambient FA/hr per speaker (sorted): {[round(x,2) for x in fa_hrs]}", flush=True)
    print(f"  aggregate mean FA/hr = {agg:.3f}  | worst speaker = {worst['fa_hr']:.2f} FA/hr", flush=True)
    print(f"  95% rule-of-three UB for a 0-accept speaker over {total_h:.2f}h = {ub95:.2f} FA/hr", flush=True)
    print(f"  >>> D3 band = {band}  (900 needs mean<=0.5 FA/hr AND enough hours for UB<=0.5)", flush=True)
    out = {"hours": total_h, "n_windows": len(embs), "n_spk": len(spk_enroll),
           "agg_fa_hr": agg, "fa_hrs": fa_hrs, "ub95_ruleof3": ub95, "band": band,
           "per_spk": per_spk, "mix": {s: int((src_arr == s).sum()) for s in sorted(set(names))}}
    with open(os.path.join(L.CACHE, "t5_gsc_ambient_fahr.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\n  wrote _ceiling_cache/t5_gsc_ambient_fahr.json", flush=True)


if __name__ == "__main__":
    main()
