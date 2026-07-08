"""Multi-session enrollment measurement: F03 3-session cross-session robustness.

F03 has 3 sessions with 7-day gaps:
- S1: 25-Jul-08, APAS capture, 176 unique words
- S2: 01-Aug-08, EMA capture, 142 unique words  
- S3: 01-Aug-08, EMA capture, 166 unique words

Sessions use different capture systems (APAS vs EMA) — an excellent test of recording-condition
robustness. Only 4 words overlap across all 3 sessions, 12-19 between pair-wise.

Hypothesis: DistilHuBERT embeddings are session-robust. Within-session and cross-session
cosine distances for the same word are statistically indistinguishable at p<0.05.

Usage: python multi_session.py
"""
import os, sys, re, glob, math, wave
import numpy as np
import torch
torch.set_num_threads(4)
from transformers import AutoModel

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
import harness as H

SR = 16000
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
TORGO = os.path.expanduser("~/torgo")

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


def cos_d(a, b):
    return 1.0 - float(a @ b)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def scan_sessions(spk_dir):
    """Scan TORGO per-session, preserving session boundaries. Returns {session_num: {word: [wav_paths]}}."""
    sessions = {}
    for ses_dir in sorted(glob.glob(os.path.join(spk_dir, "Session*"))):
        ses_num = int(re.search(r"Session(\d+)", ses_dir).group(1))
        prompt_dir = os.path.join(ses_dir, "prompts")
        wav_dir = os.path.join(ses_dir, "wav_headMic")
        if not os.path.isdir(wav_dir):
            wav_dir = os.path.join(ses_dir, "wav_arrayMic")
        if not os.path.isdir(wav_dir) or not os.path.isdir(prompt_dir):
            continue

        by_word = {}
        for pf in sorted(glob.glob(os.path.join(prompt_dir, "*.txt"))):
            basename = os.path.splitext(os.path.basename(pf))[0]
            wav_path = os.path.join(wav_dir, basename + ".wav")
            if not os.path.exists(wav_path):
                continue
            with open(pf, "r") as f:
                word = f.read().strip()
            word = H.normalize(word)
            if word is None:
                continue
            by_word.setdefault(word, []).append(wav_path)
        by_word = {w: v for w, v in by_word.items() if len(v) >= 2}
        sessions[ses_num] = by_word

    return sessions


def main():
    spk_dir = os.path.join(TORGO, "F03")
    print(f"Scanning sessions for F03...", flush=True)
    sessions = scan_sessions(spk_dir)
    print(f"Sessions: {sorted(sessions.keys())}")
    for ses, words in sessions.items():
        n_utterances = sum(len(v) for v in words.values())
        print(f"  S{ses}: {len(words)} words, {n_utterances} utterances")

    # Overlap analysis
    ses_nums = sorted(sessions.keys())
    all_words = {s: set(sessions[s].keys()) for s in ses_nums}
    for i, a in enumerate(ses_nums):
        for b in ses_nums[i + 1:]:
            overlap = all_words[a] & all_words[b]
            print(f"  S{a} ∩ S{b}: {len(overlap)} words")
    if len(ses_nums) >= 3:
        triple = all_words[ses_nums[0]] & all_words[ses_nums[1]] & all_words[ses_nums[2]]
        print(f"  S{ses_nums[0]} ∩ S{ses_nums[1]} ∩ S{ses_nums[2]}: {len(triple)} words")

    # Embed all utterances
    print("\nEmbedding all utterances...", flush=True)
    emb = {}  # wav_path -> embedding
    for ses in ses_nums:
        for word, wavs in sessions[ses].items():
            for wav in wavs:
                if wav not in emb:
                    x = read_wav(wav)
                    emb[wav] = embed(x)

    n_ok = sum(1 for v in emb.values() if v is not None)
    print(f"  {n_ok}/{len(emb)} embedded", flush=True)

    # 1. Within-session vs cross-session cosine distances
    print("\n" + "=" * 70)
    print("COSINE DISTANCES: within-session vs cross-session (same word)")
    print("=" * 70)

    within, cross = [], []
    for word in all_words[1]:  # Use S1 words (most words)
        for ses_a in ses_nums:
            for ses_b in ses_nums:
                if word not in sessions[ses_a] or word not in sessions[ses_b]:
                    continue
                wavs_a = [w for w in sessions[ses_a][word] if emb.get(w) is not None]
                wavs_b = [w for w in sessions[ses_b][word] if emb.get(w) is not None]
                if len(wavs_a) < 1 or len(wavs_b) < 1:
                    continue

                for wa in wavs_a:
                    for wb in wavs_b:
                        if wa == wb:
                            continue
                        cd = cos_d(emb[wa], emb[wb])
                        if ses_a == ses_b:
                            within.append(cd)
                        else:
                            cross.append(cd)

    within = np.array(within)
    cross = np.array(cross)
    ratio = cross.mean() / within.mean() if within.mean() > 0 else float('inf')

    print(f"  Within-session: mean={within.mean():.4f} std={within.std():.4f} n={len(within)}")
    print(f"  Cross-session:  mean={cross.mean():.4f} std={cross.std():.4f} n={len(cross)}")
    print(f"  Cross/Within ratio: {ratio:.2f}×")

    # Paired comparison: for each word, average within-ses cos dist vs cross-ses cos dist
    word_deltas = []
    for word in all_words[1]:
        within_d = []; cross_d = []
        for ses_a in ses_nums:
            for ses_b in ses_nums:
                if word not in sessions[ses_a] or word not in sessions[ses_b]:
                    continue
                wavs_a = [w for w in sessions[ses_a][word] if emb.get(w) is not None]
                wavs_b = [w for w in sessions[ses_b][word] if emb.get(w) is not None]
                if len(wavs_a) < 1 or len(wavs_b) < 1:
                    continue
                for wa in wavs_a:
                    for wb in wavs_b:
                        if wa == wb:
                            continue
                        cd = cos_d(emb[wa], emb[wb])
                        if ses_a == ses_b:
                            within_d.append(cd)
                        else:
                            cross_d.append(cd)
        if within_d and cross_d:
            word_deltas.append(np.mean(cross_d) - np.mean(within_d))

    word_deltas = np.array(word_deltas)
    n_pos = (word_deltas > 0).sum()
    n_neg = (word_deltas < 0).sum()
    from scipy.stats import wilcoxon
    stat, p = wilcoxon(word_deltas) if len(word_deltas) > 5 else (0, 1.0)
    print(f"\n  Per-word delta (cross - within): mean_delta={word_deltas.mean():.4f}")
    print(f"  Discordant pairs: cross>{within} = {n_pos}, cross<{within} = {n_neg}")
    print(f"  Wilcoxon p={p:.4f}")
    if p < 0.05:
        print(f"  SIGNIFICANT: cross-session distances differ from within-session", flush=True)
    else:
        print(f"  NOT SIGNIFICANT: cross-session distances ≈ within-session", flush=True)

    # 2. Multi-session enrollment: train on N sessions, test on held-out session
    print("\n" + "=" * 70)
    print("MULTI-SESSION ENROLLMENT: train on {1,2} sessions, test on held-out")
    print("=" * 70)

    # Use words that appear in at least 2 sessions
    applicable_words = {}
    for word in all_words[1] | all_words[2] | all_words[3]:
        apps = [s for s in ses_nums if word in sessions[s] and len([w for w in sessions[s][word] if emb.get(w) is not None]) >= 2]
        if len(apps) >= 2:
            applicable_words[word] = apps

    print(f"  Words with >=2 reps in >=2 sessions: {len(applicable_words)}")

    for train_sessions in [[1], [2], [3], [1, 2], [2, 3], [1, 3], [1, 2, 3]]:
        test_sessions = [s for s in ses_nums if s not in train_sessions]
        if not test_sessions:
            continue

        # For each word, make templates from train sessions, query from test session
        pos_dists = []
        for word, apps in applicable_words.items():
            # Check if word appears in at least one train session and one test session
            train_ses_for_word = [s for s in train_sessions if s in apps]
            test_ses_for_word = [s for s in test_sessions if s in apps]
            if not train_ses_for_word or not test_ses_for_word:
                continue

            # Build prototype from train sessions
            prototypes = []
            for s in train_ses_for_word:
                for wav in sessions[s][word]:
                    if emb.get(wav) is not None:
                        prototypes.append(emb[wav])
            if not prototypes:
                continue
            proto = np.mean(prototypes, axis=0)
            proto = proto / (np.linalg.norm(proto) + 1e-8)

            # Test on held-out session
            for s in test_ses_for_word:
                for wav in sessions[s][word]:
                    if emb.get(wav) is not None:
                        cd = cos_d(emb[wav], proto)
                        pos_dists.append(cd)

        if pos_dists:
            pos_dists = np.array(pos_dists)
            print(f"  Train S{','.join(map(str,train_sessions))}: "
                  f"n={len(pos_dists)}  mean_dist={pos_dists.mean():.4f}  "
                  f"median={np.median(pos_dists):.4f}", flush=True)

    # 3. Cross-system (APAS vs EMA) comparison
    print("\n" + "=" * 70)
    print("CAPTURE SYSTEM: APAS (S1) vs EMA (S2, S3)")
    print("=" * 70)

    apas_words = all_words[1]
    ema_words = all_words[2] | all_words[3]
    sys_overlap = apas_words & ema_words

    apas_to_emas = []
    ema_to_ema = []
    for word in sys_overlap:
        apas_wavs = [w for w in sessions[1][word] if emb.get(w) is not None]
        ema_wavs = [w for w in (sessions[2].get(word, []) + sessions[3].get(word, [])) if emb.get(w) is not None]

        if apas_wavs and ema_wavs:
            for aw in apas_wavs:
                for ew in ema_wavs:
                    if aw != ew:
                        cd = cos_d(emb[aw], emb[ew])
                        apas_to_emas.append(cd)

        # EMA to EMA (S2 vs S3, both EMA)
        s2_wavs = [w for w in sessions[2].get(word, []) if emb.get(w) is not None]
        s3_wavs = [w for w in sessions[3].get(word, []) if emb.get(w) is not None]
        if s2_wavs and s3_wavs:
            for s2w in s2_wavs:
                for s3w in s3_wavs:
                    if s2w != s3w:
                        cd = cos_d(emb[s2w], emb[s3w])
                        ema_to_ema.append(cd)

    apas_to_emas = np.array(apas_to_emas)
    ema_to_ema = np.array(ema_to_ema)
    if len(apas_to_emas) and len(ema_to_ema):
        print(f"  APAS→EMA (diff system): mean={apas_to_emas.mean():.4f} n={len(apas_to_emas)}")
        print(f"  EMA→EMA (same system):  mean={ema_to_ema.mean():.4f} n={len(ema_to_ema)}")
        ratio = apas_to_emas.mean() / ema_to_ema.mean() if ema_to_ema.mean() > 0 else float('inf')
        print(f"  System-change ratio: {ratio:.2f}×")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: F03 3-session cross-session robustness")
    print("=" * 70)
    print(f"  Cross/within distance ratio: {cross.mean() / within.mean() if within.mean() > 0 else float('inf'):.2f}×")
    if p < 0.05:
        print(f"  Wilcoxon p={p:.4f} — cross-session IS statistically different from within-session")
    else:
        print(f"  Wilcoxon p={p:.4f} — cross-session NOT statistically distinguishable from within-session")


if __name__ == "__main__":
    main()
