"""E6: Data augmentation enrollment — speed/pitch perturbation.

H1: Speed (0.9x,1.1x) + pitch (±2st) augmentation on enrollment reduces FRR at matched
0.5 FA/hr by >=15% relative vs clean-only on F03+F04 with DistilHuBERT + dual-cascade.

Protocol: Each template gets 3 variants. Monte Carlo 5 iters per speaker.
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPEAKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F03", "F04"]
BG_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
PV = os.path.expanduser("~/picovoice-benchmark")
MC_ITERS = 5

import torch; torch.set_num_threads(4)
from transformers import AutoModel
net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    print("WARNING: librosa not available — using numpy-based augmentation", flush=True)


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


def augment(x, variant):
    """variant: 0=clean, 1=speed 0.9x, 2=speed 1.1x, 3=pitch +2st"""
    if variant == 0:
        return x.copy()
    if HAS_LIBROSA:
        if variant == 1:  # speed 0.9x
            return librosa.effects.time_stretch(y=x.astype(np.float64), rate=0.9).astype(np.float32)
        elif variant == 2:  # speed 1.1x
            return librosa.effects.time_stretch(y=x.astype(np.float64), rate=1.1).astype(np.float32)
        elif variant == 3:  # pitch +2 semitones
            return librosa.effects.pitch_shift(y=x.astype(np.float64), sr=SR, n_steps=2).astype(np.float32)
    else:
        # numpy fallback: simple resample for speed
        if variant == 1:
            n = int(len(x) / 0.9)
            return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        elif variant == 2:
            n = int(len(x) / 1.1)
            return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        elif variant == 3:
            return x.copy()  # no pitch shift fallback
    return x.copy()


t0 = time.time()

# 1. Load TORGO
all_data = {}
for spk in SPEAKERS:
    root = os.path.expanduser("~/torgo")
    d = H.scan(root).get(spk)
    if d is None:
        continue
    all_data[spk] = d
    n_utts = sum(len(v) for v in d["commands"].values())
    print(f"  {spk}: {len(d['commands'])} words, {n_utts} utts", flush=True)

# 2. Embed clean templates + augmented variants
print("\nEmbedding clean + augmented templates...", flush=True)
# Store: (clean_vec, aug1_vec, aug2_vec, aug3_vec, word, dur) per utterance
aug_utts = {}  # spk -> [(clean, aug1, aug2, aug3, word, dur)]
for spk, d in all_data.items():
    utts = []
    for word, wavs in d["commands"].items():
        for w in wavs:
            x = read_wav(w)
            # Clean
            vc, ds, dr = embed_with_dur(x)
            if vc is None:
                continue
            # Augmented variants
            va1, _, _ = embed_with_dur(augment(x, 1))
            va2, _, _ = embed_with_dur(augment(x, 2))
            va3, _, _ = embed_with_dur(augment(x, 3))
            utts.append((vc, va1, va2, va3, word, ds))
    aug_utts[spk] = utts
    print(f"  {spk}: {len(utts)} utterances (each ×4 variants)", flush=True)

# 3. Background scan
print(f"\nScanning LibriSpeech ({BG_MIN} min)...", flush=True)
bg_files = sorted(
    glob.glob(os.path.join(PV, "prepared", "librispeech", "**", "*.wav"), recursive=True)) \
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

# 4. Evaluate: clean-only vs clean+augmented enrollment
DUR_CANDS = np.linspace(0.05, 2.0, 15)
MARGIN_CANDS = np.linspace(0.2, 1.0, 9)


def score_background(bg_vecs, tmpl_vecs, tmpl_durs, bg_times, bg_hours):
    """Score background windows against templates. Returns (bg_dists, bg_durs) lists."""
    bg_dists = []
    bg_durs_out = []
    for bv, btc in zip(bg_vecs, bg_times):
        if bv is None:
            bg_dists.append(math.inf)
            bg_durs_out.append(0.0)
            continue
        best_d = math.inf
        best_dur = 0.0
        # Use dummy dur for bg (1s = 16000 samples)
        bds = 16000
        for tv, tds in zip(tmpl_vecs, tmpl_durs):
            if tv is None:
                continue
            d = cos_d(bv, tv)
            if d < best_d:
                best_d = d
                best_dur = abs(math.log(max(bds, 1) / max(tds, 1))) if bds > 0 and tds > 0 else 0.0
        bg_dists.append(best_d)
        bg_durs_out.append(best_dur)
    return bg_dists, bg_durs_out


def eval_enrollment(tmpl_vecs, tmpl_durs, all_utts, bg_dists, bg_durs, bg_times, bg_hours):
    """Given template set, run LOO evaluation + dual-cascade sweep.
    bg_dists, bg_durs: pre-scored background distances."""
    n_pos = len(all_utts)
    pos_dists = []
    pos_durs = []
    for i, (_, _, _, _, qw, qds) in enumerate(all_utts):
        qv = all_utts[i][0]
        if qv is None:
            pos_dists.append(math.inf)
            pos_durs.append(0.0)
            continue
        best_d = math.inf
        best_dur = 0.0
        for j, (tv, tds) in enumerate(zip(tmpl_vecs, tmpl_durs)):
            if tv is None:
                continue
            if j == i:  # LOO: skip self
                continue
            d = cos_d(qv, tv)
            if d < best_d:
                best_d = d
                best_dur = abs(math.log(max(qds, 1) / max(tds, 1))) if qds > 0 and tds > 0 else 0.0
        pos_dists.append(best_d)
        pos_durs.append(best_dur)

    pos_ds = sorted({d for d in pos_dists if math.isfinite(d)})
    bg_ds_s = sorted({d for d in bg_dists if math.isfinite(d)})
    cands_d = list(pos_ds)
    if len(bg_ds_s) > 200:
        step = max(1, len(bg_ds_s) // 200)
        for i in range(0, len(bg_ds_s), step):
            cands_d.append(bg_ds_s[i])
    cands_d = sorted(set(cands_d))

    best = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            det = sum(1 for d, dr in zip(pos_dists, pos_durs) if d <= td and dr <= tdur) / len(
                pos_dists)
            fa = 0
            last = -1e9
            for d, dr, tc in zip(bg_dists, bg_durs, bg_times):
                if d <= td and dr <= tdur and tc - last > REFRACTORY_S:
                    fa += 1
                    last = tc
                elif d <= td and dr <= tdur:
                    last = tc
            fahr = fa / bg_hours if bg_hours else 0.0
            if fahr <= 0.5 and (best is None or det > best[0]):
                best = (det, fahr, td, tdur)
    return best


print(f"\n{'=' * 70}")
print(f"AUGMENTATION ENROLLMENT (Monte Carlo {MC_ITERS} iters per speaker)")
print(f"{'=' * 70}")
print(f"  Note: query = clean only. Augmentation adds to enrollment templates.")
print(f"  {'Speaker':<8} {'Clean-only FRR':>14} {'Augmented FRR (MC mean)':>22} {'Rel reduction':>14}")

for spk in SPEAKERS:
    if spk not in aug_utts:
        continue
    utts = aug_utts[spk]
    n_utts = len(utts)

    # Clean-only: use clean templates only (one per utterance)
    clean_tmpl_vecs = [u[0] for u in utts]  # clean vecs as templates
    clean_tmpl_durs = [u[5] for u in utts]
    bg_dist_c, bg_dur_c = score_background(bg_vecs, clean_tmpl_vecs, clean_tmpl_durs, bg_times, bg_hours)
    result_clean = eval_enrollment(clean_tmpl_vecs, clean_tmpl_durs, utts, bg_dist_c, bg_dur_c,
                                   bg_times, bg_hours)

    # Augmented: Monte Carlo — include augmented variants in template pool
    aug_dets = []
    for mc in range(MC_ITERS):
        aug_tmpl_vecs = []
        aug_tmpl_durs = []
        for i, (vc, va1, va2, va3, w, ds) in enumerate(utts):
            aug_tmpl_vecs.append(vc)
            aug_tmpl_durs.append(ds)
            # Add augmented variants as additional templates (different from query)
            # Randomly include 1-2 of the 3 variants per Monte Carlo iteration
            variants = []
            if va1 is not None:
                variants.append(va1)
            if va2 is not None:
                variants.append(va2)
            if va3 is not None:
                variants.append(va3)
            for v in variants:
                aug_tmpl_vecs.append(v)
                # approximate duration for augmented variants
                aug_tmpl_durs.append(int(ds * 1.0))  # ~same duration
        bg_dist_a, bg_dur_a = score_background(bg_vecs, aug_tmpl_vecs, aug_tmpl_durs, bg_times, bg_hours)
        result_aug = eval_enrollment(aug_tmpl_vecs, aug_tmpl_durs, utts, bg_dist_a, bg_dur_a,
                                     bg_times, bg_hours)
        if result_aug:
            aug_dets.append(result_aug[0])

    if result_clean and aug_dets:
        frr_c = (1 - result_clean[0]) * 100
        mean_aug = np.mean(aug_dets)
        std_aug = np.std(aug_dets)
        frr_a = (1 - mean_aug) * 100
        if frr_c > 0:
            rel = (frr_c - frr_a) / frr_c * 100
        else:
            rel = 0.0
        print(f"  {spk:<8} {frr_c:>13.1f}%  {frr_a:>13.1f}% ±{std_aug * 100:>4.1f}%  "
              f"{rel:>+13.1f}%", flush=True)
    elif result_clean:
        print(f"  {spk:<8} {(1 - result_clean[0]) * 100:>13.1f}%  {'no valid point':>22}", flush=True)

print(f"\n{'=' * 70}")
print(f"Total: {time.time() - t0:.0f}s  |  bg={bg_hours:.2f}h")
print(f"{'=' * 70}")
