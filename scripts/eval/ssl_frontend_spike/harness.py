"""CP-1 SSL-front-end ceiling spike — front-end-agnostic TORGO harness.

Reproduces the committed `TorgoEval` protocol (speaker-dependent, k=5 round-robin folds,
leave-one-fold-out global-threshold FRR@FAR, threshold-free rank-1) so the ONLY variable across
arms is the per-utterance feature matrix. Baseline arm = MFCC-DTW (numpy). SSL arm plugs a
different feature extractor (see ssl_features.py) into the SAME DTW + fold + scoring code.

numpy + stdlib `wave` only — no torch needed for the baseline arm.
"""
import os, re, wave, glob, math, json, sys
import numpy as np

TORGO_ROOT = os.path.expanduser("~/torgo")
SPEAKER_RE = re.compile(r"^[FM]C?\d\d$")
WORD_RE = re.compile(r"^[a-z][a-z'-]*( [a-z'-]+)?$")

# ---------------------------------------------------------------- corpus (replicates TorgoCorpus)

def normalize(prompt: str):
    t = prompt.strip()
    if not t:
        return None
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return None
    t = re.sub(r'[.,;:!?"]', "", t.lower()).strip()
    if not t or t == "xxx":
        return None
    if "/" in t or "jpg" in t or "input" in t:
        return None
    if len(t.split(" ")) > 2:
        return None
    return t if WORD_RE.match(t) else None


def scan(root=TORGO_ROOT, mic="wav_headMic", min_reps=2):
    """Return {speaker: {'commands': {word:[wavpaths]}, 'negatives': [wavpaths]}}."""
    out = {}
    speakers = sorted(d for d in os.listdir(root)
                      if os.path.isdir(os.path.join(root, d)) and SPEAKER_RE.match(d))
    for spk in speakers:
        spk_dir = os.path.join(root, spk)
        by_word = {}  # preserve insertion order (py3.7+ dict)
        sessions = sorted(d for d in os.listdir(spk_dir)
                          if os.path.isdir(os.path.join(spk_dir, d)) and d.startswith("Session"))
        for ses in sessions:
            pdir = os.path.join(spk_dir, ses, "prompts")
            wdir = os.path.join(spk_dir, ses, mic)
            if not (os.path.isdir(pdir) and os.path.isdir(wdir)):
                continue
            for pf in sorted(glob.glob(os.path.join(pdir, "*.txt"))):
                stem = os.path.splitext(os.path.basename(pf))[0]
                wav = os.path.join(wdir, stem + ".wav")
                if not os.path.isfile(wav):
                    continue
                with open(pf) as fh:
                    word = normalize(fh.read())
                if word is None:
                    continue
                by_word.setdefault(word, []).append(wav)
        commands, negatives = {}, []
        for word, wavs in by_word.items():
            if len(wavs) >= min_reps:
                commands[word] = wavs
            else:
                negatives.extend(wavs)
        if commands:
            out[spk] = {"commands": commands, "negatives": negatives}
    return out


def folds(speaker_data, k=5):
    """Replicate TorgoCorpus.folds: per-word round-robin i%k → positive in fold i%k, enroll in others.
    Returns list of dicts: {'enroll':[(word,wav)], 'positives':[(word,wav)], 'negatives':[wav]}."""
    pos_by_fold = [[] for _ in range(k)]
    enroll_by_fold = [[] for _ in range(k)]
    for word, wavs in speaker_data["commands"].items():
        for i, wav in enumerate(wavs):
            f = i % k
            pos_by_fold[f].append((word, wav))
            for g in range(k):
                if g != f:
                    enroll_by_fold[g].append((word, wav))
    neg_by_fold = [[] for _ in range(k)]
    for i, wav in enumerate(speaker_data["negatives"]):
        neg_by_fold[i % k].append(wav)
    return [{"index": f, "enroll": enroll_by_fold[f],
             "positives": pos_by_fold[f], "negatives": neg_by_fold[f]} for f in range(k)]


# ---------------------------------------------------------------- wav io

def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1 and w.getframerate() == 16000 and w.getsampwidth() == 2, path
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return x


def energy_vad_trim(x, sr=16000, frame_ms=20, shift_ms=10, ratio=3.0, abs_floor=1e-3,
                    min_speech_ms=80, hangover_ms=80, noise_pct=0.10):
    """Replicates core:dsp EnergyVad.trim: RMS-energy VAD, returns the trimmed speech region
    (empty array if silent). Both arms trim identically before feature extraction (the product does)."""
    flen = max(1, sr * frame_ms // 1000)
    shift = max(1, sr * shift_ms // 1000)
    if x.size < flen:
        return x[:0]
    starts = np.arange(0, x.size - flen + 1, shift)
    frames = np.stack([x[s:s + flen] for s in starts])
    energies = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1))
    if energies.size == 0:
        return x[:0]
    order = np.sort(energies)
    noise_floor = order[int(noise_pct * (order.size - 1))]
    thr = max(noise_floor * ratio, abs_floor)
    min_speech_frames = max(1, min_speech_ms // shift_ms)
    hangover_frames = hangover_ms // shift_ms
    first = last = -1
    run = 0
    for i, e in enumerate(energies):
        if e >= thr:
            run += 1
            if run >= min_speech_frames:
                if first < 0:
                    first = max(0, i - run + 1)
                last = i
        else:
            run = 0
    if first < 0:
        return x[:0]
    start_frame = max(0, first - hangover_frames)
    end_frame = last + hangover_frames
    start_sample = start_frame * shift
    end_sample = min(end_frame * shift + flen, x.size)
    return x[start_sample:end_sample]


# ---------------------------------------------------------------- MFCC front-end (numpy)

class MfccFrontEnd:
    name = "mfcc_delta_delta"

    def __init__(self, sr=16000, frame_ms=25, shift_ms=10, n_mel=26, n_mfcc=13,
                 preemph=0.97, low_hz=20.0, lifter=22, delta_order=2, cmn=True):
        self.sr = sr
        self.flen = sr * frame_ms // 1000
        self.fshift = sr * shift_ms // 1000
        self.n_mel = n_mel
        self.n_mfcc = n_mfcc
        self.preemph = preemph
        self.lifter = lifter
        self.delta_order = delta_order
        self.cmn = cmn
        self.nfft = 1 << (self.flen - 1).bit_length()
        self.win = np.hamming(self.flen).astype(np.float32)
        self.mel = self._mel_bank(low_hz, sr / 2.0)
        # Orthonormal DCT-II matrix (n_mfcc x n_mel) — matches Kotlin dct() exactly.
        scale = np.array([math.sqrt(1.0 / n_mel) if k == 0 else math.sqrt(2.0 / n_mel)
                          for k in range(n_mfcc)], dtype=np.float32)
        self.dct = np.array([[math.cos(math.pi * k * (i + 0.5) / n_mel) for i in range(n_mel)]
                             for k in range(n_mfcc)], dtype=np.float32) * scale[:, None]
        self.lift = (1.0 + (lifter / 2.0) * np.sin(np.pi * np.arange(n_mfcc) / lifter)).astype(np.float32)

    def _hz2mel(self, f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def _mel2hz(self, m):
        return 700.0 * (10 ** (m / 2595.0) - 1.0)

    def _mel_bank(self, low, high):
        m_pts = np.linspace(self._hz2mel(low), self._hz2mel(high), self.n_mel + 2)
        f_pts = self._mel2hz(m_pts)
        bins = np.floor((self.nfft + 1) * f_pts / self.sr).astype(int)
        fb = np.zeros((self.n_mel, self.nfft // 2 + 1), dtype=np.float32)
        for i in range(1, self.n_mel + 1):
            l, c, r = bins[i - 1], bins[i], bins[i + 1]
            for j in range(l, c):
                if c > l:
                    fb[i - 1, j] = (j - l) / (c - l)
            for j in range(c, r):
                if r > c:
                    fb[i - 1, j] = (r - j) / (r - c)
        return fb

    def __call__(self, x):
        if x.size < self.flen:
            return np.zeros((0, self.n_mfcc * (self.delta_order + 1)), dtype=np.float32)
        # pre-emphasis
        emph = np.empty_like(x)
        emph[0] = x[0]
        emph[1:] = x[1:] - self.preemph * x[:-1]
        # frames
        starts = range(0, x.size - self.flen + 1, self.fshift)
        frames = np.stack([emph[s:s + self.flen] * self.win for s in starts])  # (T, flen)
        spec = np.abs(np.fft.rfft(frames, self.nfft)) ** 2 / self.nfft  # power spectrum (T, nfft/2+1)
        mel_e = spec @ self.mel.T  # (T, n_mel)
        log_mel = np.log(np.maximum(mel_e, 1e-10))
        mfcc = log_mel @ self.dct.T  # (T, n_mfcc)
        mfcc *= self.lift
        if self.cmn:
            mfcc = mfcc - mfcc.mean(axis=0, keepdims=True)
        feats = [mfcc]
        if self.delta_order >= 1:
            feats.append(_delta(mfcc))
        if self.delta_order >= 2:
            feats.append(_delta(_delta(mfcc)))
        return np.concatenate(feats, axis=1).astype(np.float32)


class LpcFrontEnd:
    """LPC-derived cepstral coefficients (LPCC). Same framing / preemph / Hamming / CMN / Δ+ΔΔ
    pipeline as MfccFrontEnd, so the ONLY difference vs the MFCC arm is spectral-envelope estimation
    (all-pole LPC vs mel filterbank). Slots into the identical DTW+fold+scoring harness."""
    name = "lpcc_delta_delta"

    def __init__(self, sr=16000, frame_ms=25, shift_ms=10, order=16, n_cep=13,
                 preemph=0.97, lifter=22, delta_order=2, cmn=True):
        self.sr = sr
        self.flen = sr * frame_ms // 1000
        self.fshift = sr * shift_ms // 1000
        self.order = order
        self.n_cep = n_cep
        self.preemph = preemph
        self.delta_order = delta_order
        self.cmn = cmn
        self.win = np.hamming(self.flen).astype(np.float32)
        self.lift = (1.0 + (lifter / 2.0) * np.sin(np.pi * np.arange(n_cep) / lifter)).astype(np.float32)

    def _lpcc_of_frame(self, frame):
        # autocorrelation r[0..order]
        r = np.correlate(frame, frame, mode="full")[len(frame) - 1: len(frame) + self.order]
        if r[0] <= 0:
            return np.zeros(self.n_cep, dtype=np.float32)
        r = r + np.concatenate([[1e-6 * r[0]], np.zeros(self.order)])  # tiny ridge for stability
        # Levinson-Durbin
        a = np.zeros(self.order + 1)
        a[0] = 1.0
        e = r[0]
        for i in range(1, self.order + 1):
            acc = r[i] + np.dot(a[1:i], r[i - 1:0:-1]) if i > 1 else r[i]
            k = -acc / e
            a_new = a.copy()
            for j in range(1, i):
                a_new[j] = a[j] + k * a[i - j]
            a_new[i] = k
            a = a_new
            e *= (1.0 - k * k)
            if e <= 0:
                e = 1e-8
        lpc = a[1:]  # a[1..order], model 1 + sum a_m z^-m
        # LPC -> LPCC cepstral recursion
        c = np.zeros(self.n_cep)
        c[0] = np.log(max(e, 1e-8))  # gain/energy term (analogous to MFCC c0)
        for m in range(1, self.n_cep):
            s = 0.0
            for k in range(1, m):
                if k <= self.order:
                    s += (k / m) * c[k] * lpc[m - k - 1] if (m - k - 1) < self.order else 0.0
            am = lpc[m - 1] if (m - 1) < self.order else 0.0
            c[m] = -am - s
        return (c * self.lift).astype(np.float32)

    def __call__(self, x):
        if x.size < self.flen:
            return np.zeros((0, self.n_cep * (self.delta_order + 1)), dtype=np.float32)
        emph = np.empty_like(x)
        emph[0] = x[0]
        emph[1:] = x[1:] - self.preemph * x[:-1]
        starts = range(0, x.size - self.flen + 1, self.fshift)
        cep = np.stack([self._lpcc_of_frame((emph[s:s + self.flen] * self.win).astype(np.float64))
                        for s in starts])
        if self.cmn:
            cep = cep - cep.mean(axis=0, keepdims=True)
        feats = [cep]
        if self.delta_order >= 1:
            feats.append(_delta(cep))
        if self.delta_order >= 2:
            feats.append(_delta(_delta(cep)))
        return np.concatenate(feats, axis=1).astype(np.float32)


def _delta(m):
    # first-order finite difference (next - prev)/2, edge-clamped — matches Kotlin derivative().
    nxt = np.empty_like(m)
    nxt[:-1] = m[1:]
    nxt[-1] = m[-1]
    prv = np.empty_like(m)
    prv[1:] = m[:-1]
    prv[0] = m[0]
    return (nxt - prv) / 2.0


# ---------------------------------------------------------------- DTW (replicates Dtw.distance)

def dtw_distance(a, b, band_ratio=0.1):
    """Length-normalised banded DTW, euclidean local cost, /(n+m) — matches core:matching Dtw."""
    n, m = a.shape[0], b.shape[0]
    if n == 0 or m == 0:
        return math.inf
    band = max(1, int(band_ratio * max(n, m))) if band_ratio > 0 else 10 ** 9
    ratio = m / n
    # local cost via broadcasting only within band per row to save memory/time
    INF = math.inf
    prev = np.full(m + 1, INF)
    curr = np.full(m + 1, INF)
    prev[0] = 0.0
    for i in range(1, n + 1):
        curr[:] = INF
        center = int((i - 1) * ratio)
        j_start = max(1, center - band + 1)
        j_end = min(center + band, m)
        ai = a[i - 1]
        for j in range(j_start, j_end + 1):
            if abs((i - 1) - int((j - 1) / ratio)) > band:
                continue
            d = b[j - 1] - ai
            cost = math.sqrt(float(d @ d))
            best = min(prev[j], curr[j - 1], prev[j - 1])
            if best != INF:
                curr[j] = cost + best
        prev, curr = curr, prev
    acc = prev[m]
    return INF if acc == INF else acc / (n + m)


# ---------------------------------------------------------------- evaluation

LOW_FAR_TARGET = 0.05


def _best_by_command(query_feat, enroll_feats):
    """min DTW to each command over its templates. enroll_feats: {word:[feat,...]}."""
    out = {}
    for word, feats in enroll_feats.items():
        best = math.inf
        for tf in feats:
            d = dtw_distance(query_feat, tf)
            if d < best:
                best = d
        out[word] = best
    return out


def eval_speaker(spk_data, front_end, feat_cache, k=5, band_ratio=0.1):
    """Return per-row records for one speaker: list of dicts
    {fold, truth(or None), best_by_command:{word:dist}, winner, winner_dist}."""
    rows = []
    for fold in folds(spk_data, k):
        if not fold["positives"] and not fold["negatives"]:
            continue
        # enrolled templates for this fold
        enroll = {}
        for word, wav in fold["enroll"]:
            enroll.setdefault(word, []).append(feat_cache[wav])
        # skip empty-feature templates
        enroll = {w: [f for f in fs if f.shape[0] > 0] for w, fs in enroll.items()}
        enroll = {w: fs for w, fs in enroll.items() if fs}
        for word, wav in fold["positives"]:
            qf = feat_cache[wav]
            bbc = _best_by_command(qf, enroll) if qf.shape[0] > 0 else {}
            winner = min(bbc, key=bbc.get) if bbc else None
            rows.append({"fold": fold["index"], "truth": word, "wav": wav,
                         "best_by_command": bbc, "winner": winner,
                         "winner_dist": bbc.get(winner, math.inf) if winner else math.inf})
        for wav in fold["negatives"]:
            qf = feat_cache[wav]
            bbc = _best_by_command(qf, enroll) if qf.shape[0] > 0 else {}
            winner = min(bbc, key=bbc.get) if bbc else None
            rows.append({"fold": fold["index"], "truth": None, "wav": wav,
                         "best_by_command": bbc, "winner": winner,
                         "winner_dist": bbc.get(winner, math.inf) if winner else math.inf})
    return rows


def rank1(rows):
    pos = [r for r in rows if r["truth"] is not None]
    if not pos:
        return 0.0, 0, 0
    hits = sum(1 for r in pos if r["winner"] == r["truth"])
    return hits / len(pos), hits, len(pos)


def _far_of(rows, thr):
    negs = [r for r in rows if r["truth"] is None]
    if not negs:
        return 0.0
    fa = sum(1 for r in negs if r["winner"] is not None and r["winner_dist"] <= thr)
    return fa / len(negs)


def _fit_global(train, target=LOW_FAR_TARGET):
    cands = sorted({d for r in train for d in r["best_by_command"].values() if math.isfinite(d)})
    if not cands:
        return -1.0
    best = cands[0] - 1.0
    for t in cands:
        if _far_of(train, t) <= target:
            best = t
    return best


def held_out_global(rows, target=LOW_FAR_TARGET):
    """Leave-one-fold-out global-threshold FRR/FAR (replicates TorgoEval.heldOut+fitGlobal)."""
    fold_ids = sorted({r["fold"] for r in rows if r["fold"] >= 0})
    acc = pos = fa = neg = 0
    for f in fold_ids:
        thr = _fit_global([r for r in rows if r["fold"] != f], target)
        for r in [r for r in rows if r["fold"] == f]:
            accepted = r["winner"] is not None and r["winner_dist"] <= thr
            if r["truth"] is not None:
                pos += 1
                if accepted and r["winner"] == r["truth"]:
                    acc += 1
            else:
                neg += 1
                if accepted:
                    fa += 1
    frr = 0.0 if pos == 0 else 1.0 - acc / pos
    far = 0.0 if neg == 0 else fa / neg
    return frr, far, pos, neg


def separability(rows):
    """Genuine (truth's own distance) vs impostor (OOV winner distance) — CP-2 first read."""
    genuine = [r["best_by_command"][r["truth"]] for r in rows
               if r["truth"] is not None and r["truth"] in r["best_by_command"]
               and math.isfinite(r["best_by_command"][r["truth"]])]
    impostor = [r["winner_dist"] for r in rows if r["truth"] is None and math.isfinite(r["winner_dist"])]
    g, im = np.array(genuine), np.array(impostor)
    if g.size == 0 or im.size == 0:
        return None
    dprime = (im.mean() - g.mean()) / math.sqrt(0.5 * (g.var() + im.var()) + 1e-12)
    # ROC-AUC: P(genuine dist < impostor dist)
    auc = np.mean(g[:, None] < im[None, :])
    return {"dprime": float(dprime), "auc": float(auc),
            "genuine_med": float(np.median(g)), "impostor_med": float(np.median(im)),
            "n_gen": int(g.size), "n_imp": int(im.size)}
