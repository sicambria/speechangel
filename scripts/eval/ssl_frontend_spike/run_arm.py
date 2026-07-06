"""Run one front-end arm over TORGO speakers and emit rank-1 / held-out FRR-FAR / separability.

Usage: python run_arm.py <arm> [speakers csv] [max_utts_per_speaker]
  arm = mfcc | ssl:<model>:<layer>:<pool>
Saves per-row correctness (wav->hit) to results_<arm>.json for cross-arm McNemar.
"""
import sys, os, time, json
import numpy as np
import harness as H

arm = sys.argv[1] if len(sys.argv) > 1 else "mfcc"
spk_filter = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None
max_utts = int(sys.argv[3]) if len(sys.argv) > 3 else 0

if arm == "mfcc":
    fe = H.MfccFrontEnd()
    fe_name = fe.name
elif arm == "lpc":
    fe = H.LpcFrontEnd()
    fe_name = fe.name
elif arm.startswith("ssl:"):
    import ssl_features
    _, model, layer, pool = arm.split(":")
    fe = ssl_features.SslFrontEnd(model=model, layer=int(layer), pool=pool)
    fe_name = fe.name
else:
    raise SystemExit("unknown arm " + arm)

t0 = time.time()
corpus = H.scan(os.environ.get("TORGO_ROOT", H.TORGO_ROOT))
if spk_filter:
    corpus = {k: v for k, v in corpus.items() if k in spk_filter}
print(f"[{arm}] speakers: {list(corpus.keys())}", flush=True)

# collect all wavs, cache features once
all_wavs = set()
for spk, d in corpus.items():
    for w, wavs in d["commands"].items():
        all_wavs.update(wavs)
    all_wavs.update(d["negatives"])
all_wavs = sorted(all_wavs)
print(f"[{arm}] caching features for {len(all_wavs)} wavs ...", flush=True)
# Min trimmed-speech length ≡ Evaluator.minSpeechFrames=8 MFCC frames: (8-1)*160+400 = 1520 samples.
# Gate on raw speech length (front-end-agnostic) so the pooled SSL arm (1 frame by design) isn't dropped.
MIN_SPEECH_SAMPLES = 1520
feat_cache = {}
for i, wav in enumerate(all_wavs):
    speech = H.energy_vad_trim(H.read_wav(wav))  # VAD-trim BOTH arms identically (the product trims)
    if speech.size >= MIN_SPEECH_SAMPLES:
        feat_cache[wav] = fe(speech)
    else:
        feat_cache[wav] = np.zeros((0, 1), dtype=np.float32)  # too short → enrollment fail / empty query
    if (i + 1) % 200 == 0:
        print(f"   {i+1}/{len(all_wavs)}  ({time.time()-t0:.0f}s)", flush=True)
print(f"[{arm}] feature cache done in {time.time()-t0:.0f}s; dim={next(iter(feat_cache.values())).shape}", flush=True)

results = {"arm": arm, "fe": fe_name, "per_speaker": {}, "rows_correct": {}}
all_rows = []
for spk, d in sorted(corpus.items()):
    ts = time.time()
    rows = H.eval_speaker(d, fe, feat_cache)
    r1, hits, npos = H.rank1(rows)
    frr, far, pos, neg = H.held_out_global(rows)
    sep = H.separability(rows)
    ncmd = len(d["commands"])
    results["per_speaker"][spk] = {
        "commands": ncmd, "positives": npos, "rank1": r1, "rank1_hits": hits,
        "frr_ho": frr, "far_ho": far, "neg": neg, "sep": sep}
    for r in rows:
        if r["truth"] is not None:
            results["rows_correct"][r["wav"]] = int(r["winner"] == r["truth"])
    all_rows.extend(rows)
    print(f"[{arm}] {spk}: cmds={ncmd} pos={npos} rank1={r1*100:.1f}% "
          f"FRR_HO={frr*100:.1f}%@FAR{far*100:.1f}% "
          f"sep(d'={sep['dprime']:.2f},AUC={sep['auc']:.3f}) ({time.time()-ts:.0f}s)", flush=True)

# aggregate rank-1 (pool all positives)
r1a, hitsa, nposa = H.rank1(all_rows)
frra, fara, posa, nega = H.held_out_global(all_rows)
sepa = H.separability(all_rows)
results["aggregate"] = {"rank1": r1a, "positives": nposa, "frr_ho": frra, "far_ho": fara, "sep": sepa}
print(f"[{arm}] AGGREGATE rank1={r1a*100:.1f}% (n={nposa}) FRR_HO={frra*100:.1f}%@FAR{fara*100:.1f}% "
      f"sep(d'={sepa['dprime']:.2f},AUC={sepa['auc']:.3f})", flush=True)

out = f"results_{arm.replace(':','_')}.json"
with open(out, "w") as f:
    json.dump(results, f, indent=1)
print(f"[{arm}] saved {out}  total {time.time()-t0:.0f}s", flush=True)
