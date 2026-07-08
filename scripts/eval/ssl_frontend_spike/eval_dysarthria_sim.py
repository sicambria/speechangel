"""Evaluate DistilHuBERT CP-2 performance across simulated dysarthria severity levels.

Applies the first-principles dysarthria simulator to FC01/FC02/FC03 control speakers
at 5 severity levels (none, mild, moderate, severe, very_severe), then measures
CP-2 FRR using the banked DistilHuBERT + dual-cascade pipeline.

Also runs per-subsystem ablation: isolate each impairment type to identify which
acoustic dimensions most affect recognition accuracy.

Usage: python eval_dysarthria_sim.py [speakers]
"""
import os, sys, math, time, wave
import numpy as np
import torch
torch.set_num_threads(4)
from transformers import AutoModel

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import harness as H
from dysarthria_sim import DysarthriaSimulator

SR = 16000
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
TORGO = os.path.expanduser("~/torgo")
PV = os.path.expanduser("~/picovoice-benchmark")
REF_SEED = 42

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


def embed(x):
    sp = H.energy_vad_trim(x)
    if sp.size < MIN_SPEECH:
        return None
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def embed_with_dur(x):
    sp = H.energy_vad_trim(x)
    dur_sp = sp.size if sp.size >= MIN_SPEECH else 0
    if sp.size < MIN_SPEECH:
        return None, dur_sp, x.size
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32), dur_sp, x.size


def cos_d(a, b):
    return 1.0 - float(a @ b)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def eval_speaker(emb_tuples, bg_vecs, bg_durs, bg_times, bg_hours):
    """CP-2 evaluation: leave-one-out detection at best dual-cascade threshold ≤0.5 FA/hr."""
    tmps = [(v, ds) for (v, ds, dr) in emb_tuples if v is not None]
    if len(tmps) < 3:
        return None

    # Positive scores (leave-one-out)
    pos = []
    for i, (qv, qds) in enumerate(tmps):
        dists = [(cos_d(qv, tv), tds) for j, (tv, tds) in enumerate(tmps) if j != i]
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, tds1 = dists[0]
            dr = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        elif len(dists) == 1:
            d1, tds1 = dists[0]
            dr = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        else:
            d1, dr = math.inf, 0.0
        pos.append((d1, dr))

    if not pos:
        return None

    # Score background against templates
    bg_recs = score_bg(tmps, bg_vecs, bg_durs, bg_times)

    # Grid search dual-cascade
    bg_ds = sorted({r[0] for r in bg_recs if math.isfinite(r[0])})
    cands = bg_ds[:200]
    dur_cands = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    REFRACTORY = 1.0

    best_det, best_frr = 0.0, 1.0
    for thr_d in cands:
        for thr_dur in dur_cands:
            det = sum(1 for r in pos if r[0] <= thr_d and r[1] <= thr_dur) / len(pos)
            fa, last = 0, -1e9
            for r in bg_recs:
                if not math.isfinite(r[0]):
                    continue
                if r[0] <= thr_d and r[1] <= thr_dur and r[3] - last > REFRACTORY:
                    fa += 1
                    last = r[3]
                elif r[0] <= thr_d and r[1] <= thr_dur:
                    last = r[3]
            fahr = fa / bg_hours if bg_hours else 0.0
            if fahr <= 0.5 and det > best_det:
                best_det = det
                best_frr = 1.0 - det

    if best_det == 0.0:
        return None
    return {"FRR": best_frr * 100, "detection": best_det * 100, "n": len(pos)}


def scan_bg(hours=1.0):
    """Quick background scan — collect raw vectors for later scoring."""
    import glob as _glob
    bg_files = sorted(_glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                                 recursive=True))
    ws, hs = int(1.5 * SR), int(0.5 * SR)
    bg_vecs, bg_durs, bg_times, bg_sec = [], [], [], 0.0
    for bf in bg_files:
        if bg_sec / 3600.0 >= hours:
            break
        x = read_wav(bf)
        base = bg_sec
        for s in range(0, len(x) - ws + 1, hs):
            v, ds, dr = embed_with_dur(x[s:s + ws])
            bg_vecs.append(v)
            bg_durs.append(ds)
            bg_times.append(base + (s + ws / 2) / SR)
        bg_sec += len(x) / SR
    return bg_vecs, bg_durs, bg_times, bg_sec / 3600.0


def score_bg(tmps, bg_vecs, bg_durs, bg_times):
    """Score background windows against speaker templates."""
    recs = []
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        if bv is None:
            recs.append((math.inf, 0.0, 0.0, btc))
            continue
        dists = [(cos_d(bv, tv), tds) for tv, tds in tmps]
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, tds1 = dists[0]
            dr = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
        elif len(dists) == 1:
            d1, tds1 = dists[0]
            dr = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
        else:
            d1, dr = math.inf, 0.0
        recs.append((d1, dr, 0.0, btc))
    return recs


def main():
    t0 = time.time()
    speakers = sys.argv[1].split(",") if len(sys.argv) > 1 else ["FC01", "FC02", "FC03"]

    # Load control speakers
    print(f"Loading control speakers: {speakers}", flush=True)
    data = H.scan(TORGO + "/FCX")
    spk_data = {spk: data[spk] for spk in speakers if spk in data}
    print(f"  Found: {list(spk_data.keys())}", flush=True)

    # Scan background
    print(f"Scanning 1h background...", flush=True)
    bg_vecs, bg_durs, bg_times, bg_hours = scan_bg(1.0)
    print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows", flush=True)

    # Severity levels
    severities = ["none", "mild", "moderate", "severe", "very_severe"]

    print(f"\n{'='*70}")
    print(f"SEVERITY SWEEP: CP-2 FRR across 5 severity levels")
    print(f"{'='*70}")

    results = {}
    for sev in severities:
        sim = None if sev == "none" else DysarthriaSimulator(preset=sev)
        sev_results = {}
        for spk in spk_data:
            embeddings = []
            for word, wavs in spk_data[spk]["commands"].items():
                for wav in wavs:
                    x = read_wav(wav)
                    if sim:
                        x = sim.apply(x)
                    emb = embed_with_dur(x)
                    embeddings.append(emb)

            best = eval_speaker(embeddings, bg_vecs, bg_durs, bg_times, bg_hours)
            if best:
                sev_results[spk] = best

        if sev_results:
            frrs = [r["FRR"] for r in sev_results.values()]
            dets = [r["detection"] for r in sev_results.values()]
            ns = [r["n"] for r in sev_results.values()]
            avg_frr = np.mean(frrs)
            results[sev] = sev_results
            print(f"  {sev:15s}: avg FRR={avg_frr:.1f}%  ({', '.join(f'{s}:{v:.0f}%' for s,v in zip(sev_results.keys(),frrs))})  n={sum(ns)}")

    print(f"\n{'='*70}")
    print(f"PER-SUBSYSTEM ABLATION: which impairment affects recognition most?")
    print(f"{'='*70}")

    subsystems = {
        'respiration': dict(respiration=0.7),
        'pitch_mono': dict(pitch_mono=0.8),
        'volume_mono': dict(volume_mono=0.6),
        'breathiness': dict(breathiness=0.7),
        'harshness': dict(harshness=0.6),
        'formant_shift': dict(formant_shift=0.7),
        'spectral_smooth': dict(spectral_smooth=0.7),
        'rate_reduction': dict(rate_reduction=0.5),
        'stress_comp': dict(stress_comp=0.6),
        'hypernasality': dict(hypernasality=0.5),
    }

    ablation = {}
    for sub_name, params in subsystems.items():
        sim = DysarthriaSimulator(**params)
        sub_frrs = []
        for spk in spk_data:
            embeddings = []
            for word, wavs in spk_data[spk]["commands"].items():
                for wav in wavs:
                    x = read_wav(wav)
                    x = sim.apply(x)
                    emb = embed_with_dur(x)
                    embeddings.append(emb)

            best = eval_speaker(embeddings, bg_vecs, bg_durs, bg_times, bg_hours)
            if best:
                sub_frrs.append(best["FRR"])

        if sub_frrs:
            avg = np.mean(sub_frrs)
            ablation[sub_name] = avg
            print(f"  {sub_name:20s}: FRR={avg:.1f}%")

    # Baseline (no impairment) for comparison
    base_frrs = []
    for spk in spk_data:
        embeddings = []
        for word, wavs in spk_data[spk]["commands"].items():
            for wav in wavs:
                emb = embed_with_dur(read_wav(wav))
                embeddings.append(emb)
        best = eval_speaker(embeddings, bg_vecs, bg_durs, bg_times, bg_hours)
        if best:
            base_frrs.append(best["FRR"])
    baseline = np.mean(base_frrs) if base_frrs else 0.0

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"  Baseline (no impairment): {baseline:.1f}% FRR")
    for sev in ["mild", "moderate", "severe", "very_severe"]:
        if sev in results:
            frrs = [r["FRR"] for r in results[sev].values()]
            print(f"  {sev:15s}: {np.mean(frrs):.1f}% FRR  (delta: +{np.mean(frrs)-baseline:.1f}%)")

    print(f"\n  Per-subsystem impact (isolated, high severity):")
    for sub, frr in sorted(ablation.items(), key=lambda x: -x[1]):
        delta = frr - baseline
        print(f"    {sub:20s}: {frr:.1f}%  (+{delta:.1f}% vs baseline)")
    print(f"\n  Total: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
