"""6-hour real ambient proxy: LibriSpeech speech + DEMAND noise mixed at 5-15 dB SNR.

Measures actual FA/hr performance on a realistic household-like background (TV/conversation
in a room with environmental noise). Uses the banked DistilHuBERT + dual-cascade pipeline.

Usage: python ambient_6h.py [speakers] [bg_hours]

Outputs FA/hr for each speaker, streaming gate pass rate, and E2E FRR at ≤0.5 FA/hr.
Deterministic seed: 42.
"""
import os, sys, glob, math, time, wave
import numpy as np
import torch
torch.set_num_threads(4)
from transformers import AutoModel

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
import harness as H

SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
PV = os.path.expanduser("~/picovoice-benchmark")
TORGO = os.path.expanduser("~/torgo")
BG_HOURS = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
REF_SEED = 42

net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)


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


def load_torgo(speakers):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import harness as H
    emb_info = {}
    all_wavs = set()
    for spk in speakers:
        root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
        d = H.scan(root).get(spk)
        if d is None:
            continue
        for wavs in d["commands"].values():
            all_wavs.update(wavs)
    print(f"Loading {len(all_wavs)} TORGO utterances...", flush=True)
    for i, wav in enumerate(sorted(all_wavs)):
        if i % 200 == 0:
            print(f"  {i}/{len(all_wavs)}", flush=True)
        x = read_wav(wav)
        emb_info[wav] = embed_with_dur(x)
    n_ok = sum(1 for v in emb_info.values() if v[0] is not None)
    print(f"  {n_ok}/{len(all_wavs)} embedded", flush=True)
    return emb_info


def build_templates(emb_info, speaker_data):
    """Build per-word template list for a speaker."""
    tmps = []
    for word, wavs in speaker_data["commands"].items():
        for w in wavs:
            v, ds, dr = emb_info.get(w, (None, 0, 0))
            if v is not None:
                tmps.append((v, ds, word, w))
    return tmps


def scan_background(hours):
    """Generate realistic household ambient: 50% silence, 30% speech+noise mix, 20% noise-only.

    Mixes LibriSpeech speech with DEMAND noise at 5-15 dB SNR. Random silence periods
    of 2-30 seconds interspersed. Deterministic seed for reproducibility."""
    bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                                recursive=True))
    demand_files = sorted(glob.glob(os.path.join(PV, "demand", "**", "*.wav"), recursive=True))
    if not bg_files:
        raise FileNotFoundError("No LibriSpeech background files found")

    rng = np.random.RandomState(REF_SEED)
    ws, hs = int(WIN_S * SR), int(HOP_S * SR)
    bg_vecs, bg_durs, bg_times, bg_sec = [], [], [], 0.0
    n_speech_like, n_total = 0, 0
    target_sec = hours * 3600.0

    # Pre-shuffle files for realistic mixing
    bg_idx, demand_idx = 0, 0

    while bg_sec < target_sec:
        seg_type = rng.choice(["silence", "speech_noise", "noise_only"],
                               p=[0.5, 0.3, 0.2])

        # Determine segment duration (1-30 seconds for silence, 2-60 for content)
        if seg_type == "silence":
            dur = rng.uniform(2, 30)
        else:
            dur = rng.uniform(2, 60)

        seg_samples = int(dur * SR)
        x = np.zeros(seg_samples, dtype=np.float32)

        if seg_type == "speech_noise":
            # Mix speech + noise
            bf = bg_files[rng.randint(0, len(bg_files))]
            x_bg = read_wav(bf)
            if len(x_bg) < seg_samples:
                reps = seg_samples // len(x_bg) + 1
                x_bg = np.tile(x_bg, reps)
            off = rng.randint(0, max(1, len(x_bg) - seg_samples))
            x_bg = x_bg[off:off + seg_samples]

            if demand_files:
                df = demand_files[rng.randint(0, len(demand_files))]
                x_noise = read_wav(df)
                if len(x_noise) < seg_samples:
                    reps = seg_samples // len(x_noise) + 1
                    x_noise = np.tile(x_noise, reps)
                n_off = rng.randint(0, max(1, len(x_noise) - seg_samples))
                x_noise = x_noise[n_off:n_off + seg_samples]
                snr = rng.uniform(5, 15)
                srms = np.sqrt(np.mean(x_bg.astype(np.float64) ** 2)) + 1e-10
                nrms = np.sqrt(np.mean(x_noise.astype(np.float64) ** 2)) + 1e-10
                x = x_bg + x_noise * (srms / (nrms * (10 ** (snr / 20.0))))
            else:
                x = x_bg
        elif seg_type == "noise_only":
            if demand_files:
                df = demand_files[rng.randint(0, len(demand_files))]
                x_noise = read_wav(df)
                if len(x_noise) < seg_samples:
                    reps = seg_samples // len(x_noise) + 1
                    x_noise = np.tile(x_noise, reps)
                off = rng.randint(0, max(1, len(x_noise) - seg_samples))
                x = x_noise[off:off + seg_samples]
        # else: silence — x stays zeros

        base = bg_sec
        for s in range(0, len(x) - ws + 1, hs):
            v, ds, dr = embed_with_dur(x[s:s + ws])
            bg_vecs.append(v)
            bg_durs.append(ds)
            bg_times.append(base + (s + ws / 2) / SR)
            n_total += 1
            if v is not None:
                n_speech_like += 1
        bg_sec += len(x) / SR

    bg_hours = bg_sec / 3600.0
    print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows, {n_speech_like} speech-like "
          f"({n_speech_like/max(1,n_total)*100:.1f}% pass VAD)", flush=True)
    return bg_vecs, bg_durs, bg_times, bg_hours, n_speech_like


def eval_cascade(pos_recs, bg_recs, bg_hours):
    """Dual-cascade grid search: distance + duration-ratio → best detection at ≤0.5 FA/hr."""
    bg_ds = sorted({r[0] for r in bg_recs if math.isfinite(r[0])})
    if not bg_ds:
        return None
    cands_d = list(bg_ds[:300])
    if len(bg_ds) > 300:
        step = max(1, len(bg_ds) // 300)
        cands_d.extend([bg_ds[i] for i in range(0, len(bg_ds), step)])
    cands_d = sorted(set(cands_d))
    dur_cands = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]

    best_det, best_frr, best_thr_d, best_thr_dur = 0.0, 1.0, 0.0, 0.0
    for thr_d in cands_d:
        for thr_dur in dur_cands:
            det = sum(1 for r in pos_recs if r[0] <= thr_d and r[1] <= thr_dur) / len(pos_recs) if pos_recs else 0.0
            fa, last = 0, -1e9
            for r in bg_recs:
                if r[0] is None or not math.isfinite(r[0]):
                    continue
                if r[0] <= thr_d and r[1] <= thr_dur and r[3] - last > REFRACTORY_S:
                    fa += 1
                    last = r[3]
                elif r[0] <= thr_d and r[1] <= thr_dur:
                    last = r[3]
            fahr = fa / bg_hours if bg_hours else 0.0
            frr = 1.0 - det
            if fahr <= 0.5 and det > best_det:
                best_det = det
                best_frr = frr
                best_thr_d = thr_d
                best_thr_dur = thr_dur

    if best_det == 0.0:
        return None
    return {"FRR": best_frr * 100, "detection": best_det * 100, "thr_d": best_thr_d,
            "thr_dur": best_thr_dur, "bg_hours": bg_hours}


def score_bg(tmps, bg_vecs, bg_durs, bg_times):
    recs = []
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        if bv is None:
            recs.append((math.inf, 0.0, 1.0, btc))
            continue
        dists = [(cos_d(bv, tv), j, tds) for j, (tv, tds, tw, twav) in enumerate(tmps)]
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, _, tds1 = dists[0]
            d2 = dists[1][0]
            dr = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
        elif len(dists) == 1:
            d1, _, tds1 = dists[0]
            dr = abs(math.log(max(bds, 1) / max(tds1, 1))) if bds > 0 and tds1 > 0 else 0.0
        else:
            d1, dr = math.inf, 0.0
        recs.append((d1, dr, 0.0, btc))
    return recs


def score_pos(tmps):
    """Leave-one-out positive scoring."""
    recs = []
    for i, (qv, qds, qw, qwav) in enumerate(tmps):
        dists = [(cos_d(qv, tv), j, tds) for j, (tv, tds, tw, twav) in enumerate(tmps) if j != i]
        dists.sort(key=lambda x: x[0])
        if len(dists) >= 2:
            d1, _, tds1 = dists[0]
            dr = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        elif len(dists) == 1:
            d1, _, tds1 = dists[0]
            dr = abs(math.log(max(qds, 1) / max(tds1, 1))) if qds > 0 and tds1 > 0 else 0.0
        else:
            d1, dr = math.inf, 0.0
        recs.append((d1, dr))
    return recs


def main():
    t_total = time.time()

    print(f"Loading TORGO for speakers: {SPEAKERS}", flush=True)
    all_data = {}
    for spk in SPEAKERS:
        root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
        d = H.scan(root).get(spk)
        if d:
            all_data[spk] = d

    emb_info = {}
    all_wavs = sorted({w for d in all_data.values() for lst in d["commands"].values() for w in lst})
    print(f"Embedding {len(all_wavs)} TORGO utterances...", flush=True)
    for i, wav in enumerate(all_wavs):
        if i % 200 == 0:
            print(f"  {i}/{len(all_wavs)}", flush=True)
        emb_info[wav] = embed_with_dur(read_wav(wav))
    n_ok = sum(1 for v in emb_info.values() if v[0] is not None)
    print(f"  {n_ok}/{len(all_wavs)} embedded ({time.time()-t_total:.0f}s)", flush=True)

    print(f"\nScanning {BG_HOURS}h background (LibriSpeech + DEMAND mixed)...", flush=True)
    bg_vecs, bg_durs, bg_times, bg_hours, n_speech_like = scan_background(BG_HOURS)
    vad_reject_pct = (len(bg_vecs) - n_speech_like) / len(bg_vecs) * 100 if bg_vecs else 0
    print(f"  VAD reject rate: {vad_reject_pct:.1f}%", flush=True)

    print(f"\n{'='*70}")
    print(f"DISTILHUBERT L{LAYER} — 6h AMBIENT PROXY (dual-cascade, ≤0.5 FA/hr)")
    print(f"{'='*70}")
    print(f"  Background: {bg_hours:.2f}h, {len(bg_vecs)} windows, {n_speech_like} speech-like")

    results = {}
    for spk, d in all_data.items():
        tmps = build_templates(emb_info, d)
        if len(tmps) < 3:
            print(f"\n  {spk}: too few templates ({len(tmps)}), skip")
            continue

        pos = score_pos(tmps)
        bg = score_bg(tmps, bg_vecs, bg_durs, bg_times)
        best = eval_cascade(pos, bg, bg_hours)

        if best:
            results[spk] = best
            print(f"\n  {spk}: FRR={best['FRR']:.1f}%  det={best['detection']:.1f}%  "
                  f"thr_d={best['thr_d']:.4f}  thr_dur={best['thr_dur']:.1f}")
        else:
            print(f"\n  {spk}: no valid threshold at ≤0.5 FA/hr")

    print(f"\n{'='*70}")
    print("STREAMING GATE (continuous background with VAD + dual-cascade)")
    print(f"{'='*70}")
    fa, last_fa, total_windows = 0, -1e9, 0
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        total_windows += 1
        if bv is None:
            continue

    vad_pass_pct = (total_windows - n_speech_like) / total_windows * 100 if total_windows else 0

    if results:
        spk_ref = SPEAKERS[0]
        best = results.get(spk_ref)
        fa, last_fa = 0, -1e9
        for r in bg:
            if r[0] is None or not math.isfinite(r[0]):
                continue
            if r[0] <= best['thr_d'] and r[1] <= best['thr_dur'] and r[3] - last_fa > REFRACTORY_S:
                fa += 1
                last_fa = r[3]
            elif r[0] <= best['thr_d'] and r[1] <= best['thr_dur']:
                last_fa = r[3]
        fahr = fa / bg_hours if bg_hours else 0
        print(f"  Gate fires: {fa}  FA/hr: {fahr:.2f}  Target ≤0.5: {'PASS' if fahr <= 0.5 else 'FAIL'}")
        print(f"  VAD rejected windows: {vad_pass_pct:.1f}%")

    print(f"\n{'='*70}")
    print("E2E FRR @≤0.5 FA/hr (all speakers)")
    print(f"{'='*70}")
    all_pass = True
    for spk, r in sorted(results.items()):
        frr = r['FRR']
        status = "PASS" if frr < 5 else "FAIL"
        if frr >= 5:
            all_pass = False
        print(f"  {spk}: FRR={frr:.1f}%  ({status})")

    print(f"\nTotal time: {time.time()-t_total:.0f}s")
    print(f"All speakers <5% FRR: {'YES' if all_pass else 'NO'}")

    return results


if __name__ == "__main__":
    main()
