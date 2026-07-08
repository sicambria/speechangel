"""E2: Noise robustness — DistilHuBERT + dual-cascade at controlled SNR.

Pre-registered H1: DistilHuBERT + dual-cascade at 10 dB SNR retains >=50% of clean detection
(FRR <= 2x clean). SNR-adaptive thresholds + multi-condition enrollment improve to <=1.3x clean.

Protocol: Mix DEMAND noise (kitchen, living room, cafeteria) into TORGO test queries at
20/10/5 dB SNR. Enrollment kept clean. Fidelity: reproduce clean DistilHuBERT baseline first.
McNemar at matched 0.5 FA/hr per SNR.

Usage: python e2_noise_robustness.py [speakers] [bg_minutes]
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F01", "F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
PV = os.path.expanduser("~/picovoice-benchmark")
SNRS = [20, 10, 5]
NOISE_TYPES = ["DKITCHEN", "DLIVING", "PCAFETER"]  # DEMAND dirs

import torch
torch.set_num_threads(4)
from transformers import AutoModel

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


def mix_noise(speech, noise, snr_db):
    """Mix noise at target SNR. Returns noisy speech (same length as speech)."""
    if len(noise) < len(speech):
        noise = np.tile(noise, int(np.ceil(len(speech) / len(noise))))[:len(speech)]
    else:
        offset = np.random.randint(0, max(1, len(noise) - len(speech)))
        noise = noise[offset:offset + len(speech)]
    sp_rms = np.sqrt(np.mean(speech.astype(np.float64) ** 2)) + 1e-10
    ns_rms = np.sqrt(np.mean(noise.astype(np.float64) ** 2)) + 1e-10
    scale = sp_rms / (ns_rms * (10 ** (snr_db / 20.0)))
    return speech + noise * scale


t0 = time.time()

# 1. Load TORGO + noise files
print("Loading TORGO...", flush=True)
all_data = {}
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo") if not spk.startswith("FC") else os.path.expanduser(
        "~/torgo/FCX")
    d = H.scan(root).get(spk)
    if d is None:
        continue
    all_data[spk] = d

print("Loading DEMAND noise...", flush=True)
noise_files = {}
for nt in NOISE_TYPES:
    path = os.path.join(PV, "demand", nt, "ch01.wav")
    if os.path.exists(path):
        noise_files[nt] = read_wav(path)
        print(f"  {nt}: {len(noise_files[nt]) / SR:.1f}s", flush=True)

# 2. Embed clean templates (enrollment always clean)
print("\nEmbedding clean enrollment templates...", flush=True)
spk_info = {}
for spk, d in all_data.items():
    all_tmps = []
    for word, wavs in d["commands"].items():
        for w in wavs:
            x = read_wav(w)
            v, ds, dr = embed_with_dur(x)
            if v is not None:
                all_tmps.append((v, ds, word, w))
    spk_info[spk] = {"all_tmps": all_tmps, "n_pos": len(all_tmps)}
    print(f"  {spk}: {len(all_tmps)} templates", flush=True)

# 3. Background scan (clean LibriSpeech)
print(f"\nScanning LibriSpeech background ({BG_MIN} min)...", flush=True)
bg_files = sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"),
                            recursive=True)) \
    or sorted(glob.glob(os.path.join(PV, "prepared", "librispeech", "*.wav")))
win_samples = int(WIN_S * SR)
hop_samples = int(HOP_S * SR)
bg_vecs, bg_durs, bg_times, bg_sec_total = [], [], [], 0.0
for bf in bg_files:
    if bg_sec_total / 60.0 >= BG_MIN:
        break
    x = read_wav(bf)
    base = bg_sec_total
    for s in range(0, x.size - win_samples + 1, hop_samples):
        v, ds, dr = embed_with_dur(x[s:s + win_samples])
        bg_vecs.append(v)
        bg_durs.append(ds)
        bg_times.append(base + (s + win_samples / 2) / SR)
    bg_sec_total += x.size / SR
bg_hours = bg_sec_total / 3600.0
print(f"  {bg_hours:.2f}h, {len(bg_vecs)} windows ({time.time()-t0:.0f}s)", flush=True)

# 4. Score background against clean templates (reused across SNR conditions)
print("Scoring background against clean templates...", flush=True)
bg_dists = {}
for spk, info in spk_info.items():
    all_tmps = info["all_tmps"]
    dists = []
    durs = []
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        if bv is None:
            dists.append(math.inf)
            durs.append(0.0)
            continue
        best_d, best_dur = math.inf, 0.0
        for tv, tds, tw, twav in all_tmps:
            d = cos_d(bv, tv)
            if d < best_d:
                best_d = d
                best_dur = abs(math.log(max(bds, 1) / max(tds, 1))) if bds > 0 and tds > 0 else 0.0
        dists.append(best_d)
        durs.append(best_dur)
    bg_dists[spk] = (dists, durs)
    print(f"  {spk}: done", flush=True)

# 5. For each SNR: score noisy queries
print(f"\n{'=' * 70}")
print(f"NOISE ROBUSTNESS: DistilHuBERT L2 + dual-cascade at controlled SNR")
print(f"{'=' * 70}")


def eval_cascade(pos_ds, pos_durs, bg_ds, bg_durs, cands_d, dur_cands):
    best = None
    for td in cands_d:
        for tdur in dur_cands:
            det = sum(1 for d, dr in zip(pos_ds, pos_durs) if d <= td and dr <= tdur) / len(pos_ds)
            fa = 0
            last = -1e9
            for d, dr, tc in zip(bg_ds, bg_durs, bg_times):
                if d <= td and dr <= tdur and tc - last > REFRACTORY_S:
                    fa += 1
                    last = tc
                elif d <= td and dr <= tdur:
                    last = tc
            fahr = fa / bg_hours if bg_hours else 0.0
            if fahr <= 0.5 and (best is None or det > best[0]):
                best = (det, fahr, td, tdur)
    return best


DUR_CANDS = np.linspace(0.05, 2.0, 15)

for spk in SPEAKERS:
    if spk not in spk_info:
        continue
    info = spk_info[spk]
    all_tmps = info["all_tmps"]

    # Clean baseline: score clean queries against clean templates (LOO)
    print(f"\n--- {spk} ---", flush=True)
    clean_pos_ds, clean_pos_durs = [], []
    for i, (qv, qds, qw, qwav) in enumerate(all_tmps):
        best_d, best_dur = math.inf, 0.0
        for j, (tv, tds, tw, twav) in enumerate(all_tmps):
            if j == i:
                continue
            d = cos_d(qv, tv)
            if d < best_d:
                best_d = d
                best_dur = abs(math.log(max(qds, 1) / max(tds, 1))) if qds > 0 and tds > 0 else 0.0
        clean_pos_ds.append(best_d)
        clean_pos_durs.append(best_dur)

    bg_ds, bg_durs = bg_dists[spk]
    pos_d = sorted({d for d in clean_pos_ds if math.isfinite(d)})
    bg_d_sorted = sorted({d for d in bg_ds if math.isfinite(d)})
    cands_d = list(pos_d)
    if len(bg_d_sorted) > 200:
        step = max(1, len(bg_d_sorted) // 200)
        for i in range(0, len(bg_d_sorted), step):
            cands_d.append(bg_d_sorted[i])
    cands_d = sorted(set(cands_d))

    result_clean = eval_cascade(clean_pos_ds, clean_pos_durs, bg_ds, bg_durs, cands_d, DUR_CANDS)
    if result_clean:
        print(f"  Clean:        FRR={(1-result_clean[0])*100:.1f}%  det={result_clean[0]*100:.1f}%",
              flush=True)
    else:
        print(f"  Clean:        no valid point", flush=True)

    # Noise conditions
    for snr in SNRS:
        noisy_pos_ds, noisy_pos_durs = [], []
        for i, (qv, qds, qw, qwav) in enumerate(all_tmps):
            # mix noise into the query utterance
            x = read_wav(qwav)
            nt_choice = np.random.choice(NOISE_TYPES)
            noise = noise_files[nt_choice]
            x_noisy = mix_noise(x, noise, snr)
            qv_n, qds_n, _ = embed_with_dur(x_noisy)
            if qv_n is None:
                noisy_pos_ds.append(math.inf)
                noisy_pos_durs.append(0.0)
                continue
            best_d, best_dur = math.inf, 0.0
            for j, (tv, tds, tw, twav) in enumerate(all_tmps):
                if j == i:
                    continue
                d = cos_d(qv_n, tv)
                if d < best_d:
                    best_d = d
                    best_dur = abs(math.log(max(qds_n, 1) / max(tds, 1))) if qds_n > 0 and tds > 0 else 0.0
            noisy_pos_ds.append(best_d)
            noisy_pos_durs.append(best_dur)

        # re-sweep on noisy positives
        pos_d_n = sorted({d for d in noisy_pos_ds if math.isfinite(d)})
        cands_n = list(pos_d_n)
        if len(bg_d_sorted) > 200:
            step = max(1, len(bg_d_sorted) // 200)
            for i in range(0, len(bg_d_sorted), step):
                cands_n.append(bg_d_sorted[i])
        cands_n = sorted(set(cands_n))

        result_noise = eval_cascade(noisy_pos_ds, noisy_pos_durs, bg_ds, bg_durs, cands_n, DUR_CANDS)
        if result_noise and result_clean:
            frr_c = (1 - result_clean[0])
            frr_n = (1 - result_noise[0])
            ratio = frr_n / max(frr_c, 0.001)
            print(f"  SNR={snr:>2}dB:    FRR={frr_n*100:.1f}%  det={result_noise[0]*100:.1f}%  "
                  f"ratio={ratio:.1f}x clean", flush=True)
        elif result_noise:
            print(f"  SNR={snr:>2}dB:    FRR={(1-result_noise[0])*100:.1f}%", flush=True)
        else:
            print(f"  SNR={snr:>2}dB:    no valid point", flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time()-t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
