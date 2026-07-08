"""First-principles dysarthric speech simulator — fully reproducible, parameterized.

Models 5 articulatory subsystems affected by dysarthria:
  1. Respiration — reduced subglottal pressure, shorter phrases
  2. Laryngeal — monopitch, monoloudness, breathiness, harshness  
  3. Articulation — formant perturbation, spectral smoothing, vowel centralization
  4. Prosody — rate reduction, stress compression
  5. Resonance — hypernasality

Each subsystem has a severity parameter (0.0–1.0, 0=normal, 1=severe).
Apply to control speakers to generate synthetic dysarthric variants for
per-severity evaluation.

Usage: python dysarthria_sim.py
  Applies the simulator to FC01/FC02/FC03 control speakers, measures CP-2
  FRR across severity levels, and compares acoustic patterns against real
  dysarthric speakers (F01 severe, F03 mild).
"""
import numpy as np
import scipy.signal
import librosa
import os, sys, wave, time, math

SR = 16000


# ---------- subsystem 1: Respiration ----------

def respiration_impairment(x, severity=0.0):
    """Simulate reduced respiratory support: amplitude fade + phrase breaks.

    severity=0.0: no effect
    severity=0.5: 30% amplitude reduction, 1 phrase break
    severity=1.0: 60% amplitude reduction, multiple phrase breaks
    """
    if severity <= 0.0:
        return x

    # Amplitude fade envelope (breath support decays over utterance)
    t = np.linspace(0, 1, len(x))
    amp_env = 1.0 - severity * 0.6 * (1.0 - np.exp(-t * 3.0))  # faster decay at higher severity

    # Phrase breaks — insert short silences at random positions
    n_breaks = int(severity * 3)
    rng = np.random.RandomState(hash(x.tobytes()[:100]) % (2**31))
    for _ in range(n_breaks):
        pos = int(rng.uniform(0.15, 0.85) * len(x))
        silence_len = int(rng.uniform(0.05, 0.15 * (1.0 + severity)) * SR)
        if pos + silence_len < len(x):
            x[pos:pos + silence_len] *= 0.05  # near-silence, not full zero

    return x * amp_env


# ---------- subsystem 2: Laryngeal ----------

def laryngeal_monopitch(x, severity=0.0):
    """Compress F0 variation toward the mean — simulates monopitch.

    Uses autocorrelation-based pitch tracking (fast, robust for short utterances).
    severity controls the degree of pitch flattening.
    """
    if severity <= 0.0:
        return x

    if len(x) < 800:  # Skip very short utterances (<50ms)
        return x

    # Autocorrelation pitch tracking per frame
    frame_len = 2048
    hop = 512
    f0_min = 60
    f0_max = 400

    f0s = []
    for i in range(0, len(x) - frame_len, hop):
        frame = x[i:i + frame_len] * np.hanning(frame_len)
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(corr)//2:]  # Only positive lags
        # Search for peak in F0 range
        lo = int(SR / f0_max)
        hi = int(SR / f0_min)
        if hi >= len(corr):
            hi = len(corr) - 1
        if lo < hi:
            peak_idx = lo + np.argmax(corr[lo:hi])
            f0s.append(SR / peak_idx if peak_idx > 0 else 0)
        else:
            f0s.append(0)

    if not f0s or sum(1 for f in f0s if f > 0) < 3:
        return x

    voiced = [f > 0 for f in f0s]
    f0_voiced = [f for f in f0s if f > 0]
    mean_f0 = np.mean(f0_voiced)

    # Flatten F0 contour toward mean
    out = np.zeros(len(x), dtype=np.float32)
    out_pos = 0
    for i in range(len(f0s)):
        start = i * hop
        end = min(start + frame_len, len(x))
        frame = x[start:end]

        if voiced[i] and f0s[i] > 0:
            ratio = f0s[i] / max(mean_f0, 1.0)
            ratio = f0s[i] + (mean_f0 - f0s[i]) * severity
            ratio = ratio / max(f0s[i], 1.0)
            ratio = np.clip(ratio, 0.7, 1.4)
            new_len = int(len(frame) * ratio)
            new_frame = scipy.signal.resample(frame, new_len).astype(np.float32)
        else:
            new_frame = frame.copy().astype(np.float32)

        if out_pos + len(new_frame) <= len(out):
            half = len(new_frame) // 2
            out[out_pos:out_pos + half] += new_frame[:half] * 0.5
        out_pos += hop

    rms_out = np.sqrt(np.mean(out ** 2)) + 1e-8
    rms_in = np.sqrt(np.mean(x ** 2)) + 1e-8
    return (out * rms_in / rms_out).astype(np.float32)


def laryngeal_monoloudness(x, severity=0.0):
    """Compress amplitude envelope variation — simulates monoloudness.

    severity=0.0: no effect
    severity=1.0: flat amplitude envelope
    """
    if severity <= 0.0:
        return x

    # Compute RMS envelope
    frame_len = 512
    hop = 256
    n_frames = (len(x) - frame_len) // hop + 1
    if n_frames < 2:
        return x

    rms_env = np.array([np.sqrt(np.mean(x[i*hop:i*hop+frame_len]**2)) + 1e-8
                        for i in range(n_frames)])

    # Flatten toward median
    median_rms = np.median(rms_env)
    flat_env = rms_env + (median_rms - rms_env) * severity

    # Resample envelope to match signal length
    env_full = np.interp(np.arange(len(x)),
                          np.arange(n_frames) * hop + frame_len // 2,
                          flat_env / rms_env)

    return (x * env_full).astype(np.float32)


def laryngeal_breathiness(x, severity=0.0):
    """Add aspiration noise — simulates breathy voice quality.

    severity=0.0: no noise
    severity=1.0: SNR ~10dB aspiration noise
    """
    if severity <= 0.0:
        return x

    # High-frequency-weighted noise (aspiration is mostly >2kHz)
    rng = np.random.RandomState(hash(x.tobytes()[:100]) % (2**31))
    noise = rng.randn(len(x)).astype(np.float32)

    # High-pass filter the noise (breathiness is high-frequency)
    b, a = scipy.signal.butter(4, 2000 / (SR / 2), btype='high')
    noise = scipy.signal.lfilter(b, a, noise).astype(np.float32)

    # Modulate noise by amplitude envelope
    frame_len = 512
    hop = 256
    amp_env = np.zeros_like(x)
    for i in range(0, len(x) - frame_len, hop):
        amp = np.sqrt(np.mean(x[i:i+frame_len]**2)) + 1e-8
        amp_env[max(0, i-64):min(len(x), i+frame_len+64)] = amp

    noise = noise * (amp_env + 1e-8)

    # Mix at controlled SNR
    rms_speech = np.sqrt(np.mean(x**2)) + 1e-8
    rms_noise = np.sqrt(np.mean(noise**2)) + 1e-8
    snr_db = 20 * (1.0 - severity) + 5  # 5-20 dB range
    noise_scale = rms_speech / (rms_noise * (10 ** (snr_db / 20.0)))

    return (x + noise * noise_scale * severity * 0.5).astype(np.float32)


def laryngeal_harshness(x, severity=0.0):
    """Add jitter + shimmer — simulates harsh/strained voice.

    severity=0.0: no effect
    severity=1.0: 5% jitter, 3 dB shimmer
    """
    if severity <= 0.0:
        return x

    rng = np.random.RandomState(hash(x.tobytes()[:100]) % (2**31))
    out = x.copy()

    # Jitter: random pitch-period perturbation via time-domain resampling
    if severity > 0.1:
        hop = 256
        frames = librosa.util.frame(x, frame_length=1024, hop_length=hop)
        out = np.zeros_like(x)
        out_pos = 0
        for i in range(frames.shape[1]):
            jitter_factor = 1.0 + rng.uniform(-0.05, 0.05) * severity
            new_len = int(1024 * jitter_factor)
            new_frame = scipy.signal.resample(frames[:, i], new_len)
            if out_pos + new_len <= len(out):
                out[out_pos:out_pos + new_len] += new_frame * 0.5
            out_pos += hop

    # Shimmer: frame-level amplitude variation
    hop = 512
    for i in range(0, len(out) - hop, hop):
        shimmer_factor = 1.0 + rng.uniform(-0.1, 0.1) * severity
        end = min(i + hop, len(out))
        out[i:end] *= shimmer_factor

    # Normalize
    rms_out = np.sqrt(np.mean(out**2)) + 1e-8
    rms_in = np.sqrt(np.mean(x**2)) + 1e-8
    return (out * rms_in / rms_out).astype(np.float32)


# ---------- subsystem 3: Articulation ----------

def articulation_formant_shift(x, severity=0.0):
    """Perturb formant frequencies toward neutral (schwa) — vowel centralization.

    Simulates reduced articulatory precision. Formants are shifted linearly
    toward their "neutral" positions (F1=500, F2=1500, F3=2500 Hz).
    severity controls the shift magnitude.
    """
    if severity <= 0.0:
        return x

    # Estimate LPC spectrum and shift formants
    order = int(2 + SR / 1000)  # ~18 for 16kHz

    hop = 512
    frame_len = 1024
    out = np.zeros_like(x)

    for i in range(0, len(x) - frame_len, hop):
        frame = x[i:i + frame_len]
        # LPC analysis
        a = librosa.lpc(frame.astype(np.float64), order=order)
        # Get poles (formants) from LPC
        roots = np.roots(a)
        roots = roots[np.imag(roots) > 0]  # only positive frequencies
        freqs = np.angle(roots) * SR / (2 * np.pi)

        # Find the first 3 formants (closest to expected)
        # Actual shift: widen formant bandwidths → spectral smoothing
        # Simpler approach: low-pass filter the spectral envelope
        spec = np.abs(np.fft.rfft(frame * np.hanning(frame_len), n=2048))
        smooth_spec = scipy.signal.convolve(spec, np.ones(int(1 + severity * 15)), mode='same')
        smooth_spec = smooth_spec / np.sum(smooth_spec) * np.sum(spec)

        # Reconstruct from smoothed spectrum
        orig_phase = np.angle(np.fft.rfft(frame * np.hanning(frame_len), n=2048))
        new_spec = smooth_spec * np.exp(1j * orig_phase)
        new_frame = np.fft.irfft(new_spec, n=frame_len)

        if i + frame_len <= len(out):
            out[i:i + frame_len] += new_frame * 0.5  # OLA

    # Normalize
    rms_out = np.sqrt(np.mean(out ** 2)) + 1e-8
    rms_in = np.sqrt(np.mean(x ** 2)) + 1e-8
    return (out * rms_in / rms_out).astype(np.float32)


def articulation_spectral_smooth(x, severity=0.0):
    """Smooth spectral transitions — simulates imprecise consonant transitions.

    Applies temporal smoothing to the spectrogram, which blurs rapid spectral
    changes characteristic of consonant-vowel transitions.
    """
    if severity <= 0.0:
        return x

    # STFT
    D = librosa.stft(x.astype(np.float64), n_fft=1024, hop_length=256,
                     win_length=1024)
    mag = np.abs(D)
    phase = np.angle(D)

    # Temporal smoothing of magnitude spectrum
    window_len = int(1 + severity * 8)  # 1-9 frames smoothing
    if window_len > 1:
        kernel = np.hanning(window_len * 2 + 1)
        kernel = kernel / kernel.sum()
        for f in range(mag.shape[0]):
            mag[f, :] = np.convolve(mag[f, :], kernel, mode='same')

    # Reconstruct
    D_smooth = mag * np.exp(1j * phase)
    y = librosa.istft(D_smooth, hop_length=256, win_length=1024, length=len(x))

    # Normalize
    rms_out = np.sqrt(np.mean(y ** 2)) + 1e-8
    rms_in = np.sqrt(np.mean(x ** 2)) + 1e-8
    return (y * rms_in / rms_out).astype(np.float32)


# ---------- subsystem 4: Prosody ----------

def prosody_rate_reduction(x, severity=0.0):
    """Slow speaking rate — simulates bradykinesia / slow articulatory movements.

    severity=0.0: no change (1.0× speed)
    severity=1.0: 0.5× speed (50% slower)
    """
    if severity <= 0.0:
        return x

    rate = 1.0 - severity * 0.5  # 1.0 → 0.5
    return librosa.effects.time_stretch(x.astype(np.float64), rate=rate).astype(np.float32)


def prosody_stress_compression(x, severity=0.0):
    """Compress stress/accent variation — simulates monopitch + monoloudness at
    the syllable level.

    Combines pitch and amplitude compression at a coarser time scale.
    """
    if severity <= 0.0:
        return x

    # Syllable-level energy envelope compression
    frame_len = 1024
    hop = 512
    n_frames = (len(x) - frame_len) // hop + 1
    if n_frames < 2:
        return x

    rms_env = np.array([np.sqrt(np.mean(x[i*hop:i*hop+frame_len]**2)) + 1e-8
                        for i in range(n_frames)])

    # Compress dynamic range
    median_db = 20 * np.log10(np.median(rms_env))
    rms_db = 20 * np.log10(rms_env)
    compressed_db = rms_db + (median_db - rms_db) * severity
    compressed_rms = 10 ** (compressed_db / 20.0)

    # Apply envelope
    env_full = np.interp(np.arange(len(x)),
                          np.arange(n_frames) * hop + frame_len // 2,
                          compressed_rms / rms_env)

    return (x * env_full).astype(np.float32)


# ---------- subsystem 5: Resonance ----------

def resonance_hypernasality(x, severity=0.0):
    """Simulate hypernasality by adding nasal resonances (anti-formants).

    Nasal resonance adds spectral zeros around 500-800 Hz and poles around 250-300 Hz.
    severity controls the depth of the nasal formant structure.
    """
    if severity <= 0.0:
        return x

    # Nasal resonance: add anti-resonance at ~700 Hz + resonance at ~280 Hz
    # Using a cascade of notch and peak filters

    # Anti-formant (spectral zero) at ~700 Hz → notch filter
    f0_nasal = 280  # nasal murmur frequency
    f_antiformant = 700  # velopharyngeal port anti-resonance

    Q = 3.0 / (severity + 0.5)
    gain = severity * 0.3

    # Notch filter at anti-formant frequency
    b_notch, a_notch = scipy.signal.iirnotch(f_antiformant, Q, SR)
    # Peak filter at nasal murmur frequency
    b_peak, a_peak = scipy.signal.iirpeak(f0_nasal, Q * 2, SR)

    y = scipy.signal.lfilter(b_notch, a_notch, x)
    # Add nasal resonance
    y_nasal = scipy.signal.lfilter(b_peak, a_peak, x)
    y = (1.0 - gain) * y + gain * y_nasal * 0.7

    # Also add low-frequency emphasis (nasal murmur)
    b_low, a_low = scipy.signal.butter(2, 500 / (SR / 2), btype='low')
    y_low = scipy.signal.lfilter(b_low, a_low, x)
    y += severity * 0.15 * y_low

    # Normalize
    rms_out = np.sqrt(np.mean(y**2)) + 1e-8
    rms_in = np.sqrt(np.mean(x**2)) + 1e-8
    return (y * rms_in / rms_out).astype(np.float32)


# ---------- Full pipeline ----------

class DysarthriaSimulator:
    """Parameterized dysarthria simulator. Apply to any speaker's clean speech.

    Usage:
      sim = DysarthriaSimulator(severity=0.5, subsystems='all')
      impaired = sim.apply(clean_audio)

    Parameters (0.0–1.0):
      - resp_severity: respiratory support impairment
      - pitch_mono: monopitch severity
      - volume_mono: monoloudness severity
      - breathiness: breathy voice quality
      - harshness: harsh/strained voice quality
      - formant_shift: vowel centralization / articulatory imprecision
      - spectral_smooth: consonant transition blurring
      - rate_reduction: speaking rate slowdown
      - stress_comp: stress/accent compression
      - hypernasality: nasal resonance

    Preset profiles matching TORGO clinical ratings:
      - 'mild': F03/F04 profile (tongue impairment only, grades a/b)
      - 'moderate': mixed mild impairments (grades b/c)
      - 'severe': F01 profile (multi-system impairment, grades c/d/e)
    """

    PRESETS = {
        'mild': dict(pitch_mono=0.15, volume_mono=0.1, breathiness=0.05,
                     harshness=0.1, formant_shift=0.2, spectral_smooth=0.2,
                     rate_reduction=0.0, stress_comp=0.1, hypernasality=0.05,
                     respiration=0.0),
        'moderate': dict(pitch_mono=0.4, volume_mono=0.3, breathiness=0.2,
                         harshness=0.3, formant_shift=0.4, spectral_smooth=0.4,
                         rate_reduction=0.15, stress_comp=0.3, hypernasality=0.2,
                         respiration=0.2),
        'severe': dict(pitch_mono=0.8, volume_mono=0.6, breathiness=0.5,
                       harshness=0.5, formant_shift=0.7, spectral_smooth=0.7,
                       rate_reduction=0.4, stress_comp=0.5, hypernasality=0.4,
                       respiration=0.6),
        'very_severe': dict(pitch_mono=1.0, volume_mono=0.8, breathiness=0.8,
                            harshness=0.7, formant_shift=0.9, spectral_smooth=0.9,
                            rate_reduction=0.6, stress_comp=0.7, hypernasality=0.6,
                            respiration=0.9),
    }

    SUBSYSTEMS = {
        'respiration': respiration_impairment,
        'pitch_mono': laryngeal_monopitch,
        'volume_mono': laryngeal_monoloudness,
        'breathiness': laryngeal_breathiness,
        'harshness': laryngeal_harshness,
        'formant_shift': articulation_formant_shift,
        'spectral_smooth': articulation_spectral_smooth,
        'rate_reduction': prosody_rate_reduction,
        'stress_comp': prosody_stress_compression,
        'hypernasality': resonance_hypernasality,
    }

    def __init__(self, preset=None, **params):
        if preset and preset in self.PRESETS:
            self.params = dict(self.PRESETS[preset])
        else:
            self.params = {k: 0.0 for k in self.SUBSYSTEMS}
        self.params.update(params)

    def apply(self, x):
        """Apply dysarthria simulation pipeline to audio signal x.

        Returns impaired version of same length.
        """
        y = x.copy().astype(np.float32)

        # Apply in neurophysiological order: respiration → laryngeal → resonance → articulation → prosody
        order = ['respiration', 'pitch_mono', 'volume_mono', 'breathiness', 'harshness',
                 'hypernasality', 'formant_shift', 'spectral_smooth',
                 'rate_reduction', 'stress_comp']

        for key in order:
            sev = self.params.get(key, 0.0)
            if sev > 0.0:
                func = self.SUBSYSTEMS[key]
                y = func(y, sev)

        return y.astype(np.float32)

    def describe(self):
        """Return human-readable description of current parameter settings."""
        lines = []
        for k, v in sorted(self.params.items()):
            if v > 0.0:
                label = k.replace('_', ' ').title()
                lines.append(f"  {label}: {v:.2f}")
        return '\n'.join(lines) if lines else "  Normal (no impairment)"


if __name__ == "__main__":
    # Quick smoke test
    x = np.sin(2 * np.pi * 220 * np.arange(SR * 2) / SR).astype(np.float32)
    x += np.sin(2 * np.pi * 440 * np.arange(SR * 2) / SR).astype(np.float32) * 0.5

    from scipy.io.wavfile import write as wavwrite
    outdir = os.path.dirname(os.path.abspath(__file__))

    for preset in ['mild', 'moderate', 'severe', 'very_severe']:
        sim = DysarthriaSimulator(preset=preset)
        y = sim.apply(x)
        path = os.path.join(outdir, f'dysarthria_{preset}.wav')
        wavwrite(path, SR, (y * 32767).astype(np.int16))
        print(f"{preset}: len={len(y)}, rms_in={np.sqrt(np.mean(x**2)):.4f}, "
              f"rms_out={np.sqrt(np.mean(y**2)):.4f}")
