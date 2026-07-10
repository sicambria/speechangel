"""Deployable <=2MB QbE encoder via knowledge distillation — the linchpin build for a shipped >800.

Trains a small log-mel -> conv student to reproduce frozen wavlm-large L14 mean-pool embeddings
(knowledge distillation) on LibriSpeech word-length windows. Log-mel is cheap on-device and the conv
net is <2MB fp32 -> fully admissible (on-device, no GPU at inference, deterministic, 1-shot unchanged,
language-independent — distillation target is a language-agnostic SSL embedding, no ASR/lexicon).

The decisive question: can an ADMISSIBLE (<=2MB) student recover enough of wavlm's QbE quality to hold
D1 (rank-1) and D2 (FRR@FAR, few-shot) at the off-device ceiling? If yes on TYPICAL speech, a shipped
typical-population composite ->800 becomes real (validated, not laundered). Severe dysarthric remains
capped by the AUC-0.70 plateau regardless (measured separately).

Pre-registered H7 (ONE hypothesis): the distilled <=2MB student retains >=90% of wavlm's rank-1 gain
over MFCC on held-out TORGO control (typical) speakers, i.e. student rank1 >= 0.59 + 0.9*(0.88-0.59).

Eval is on TORGO (fully held out from LibriSpeech training). torch CPU. Deterministic seed.
Teacher embeddings + student checkpoint cached under _ceiling_cache/.
"""
import os, sys, glob, math, time, wave, json
import numpy as np
import torch
import torch.nn as nn
import harness as H

CACHE = os.path.join(os.path.dirname(__file__), "_ceiling_cache")
LIBRI = os.path.expanduser("~/picovoice-benchmark/prepared/librispeech")
TORGO = os.path.expanduser("~/torgo")
DYS = ["F01", "F03", "F04"]; CTL = ["FC01", "FC02", "FC03"]
SR = 16000; WIN = int(1.2 * SR); HOP = int(0.6 * SR)
N_MEL = 64
torch.manual_seed(0); np.random.seed(0)


# ---------------- log-mel front-end (cheap, deployable) ----------------
def log_mel(x, sr=SR, n_mel=N_MEL, flen=400, fshift=160):
    if x.size < flen:
        x = np.pad(x, (0, flen - x.size))
    win = np.hanning(flen).astype(np.float32)
    starts = range(0, x.size - flen + 1, fshift)
    frames = np.stack([x[s:s + flen] * win for s in starts])
    nfft = 512
    spec = np.abs(np.fft.rfft(frames, nfft)) ** 2
    # mel filterbank
    def hz2mel(f): return 2595 * np.log10(1 + f / 700)
    def mel2hz(m): return 700 * (10 ** (m / 2595) - 1)
    mpts = np.linspace(hz2mel(20), hz2mel(sr / 2), n_mel + 2)
    bins = np.floor((nfft + 1) * mel2hz(mpts) / sr).astype(int)
    fb = np.zeros((n_mel, nfft // 2 + 1), dtype=np.float32)
    for i in range(1, n_mel + 1):
        l, c, r = bins[i - 1], bins[i], bins[i + 1]
        for j in range(l, c):
            if c > l: fb[i - 1, j] = (j - l) / (c - l)
        for j in range(c, r):
            if r > c: fb[i - 1, j] = (r - j) / (r - c)
    mel = np.log(np.maximum(spec @ fb.T, 1e-6))
    mel = (mel - mel.mean(0, keepdims=True)) / (mel.std(0, keepdims=True) + 1e-5)  # CMVN
    return mel.astype(np.float32)  # (T, n_mel)


# ---------------- student encoder (<2MB) ----------------
class Student(nn.Module):
    def __init__(self, n_mel=N_MEL, d=256, out=1024):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(n_mel, 128, 5, padding=2), nn.ReLU(), nn.BatchNorm1d(128),
            nn.Conv1d(128, 192, 5, padding=2, dilation=1), nn.ReLU(), nn.BatchNorm1d(192),
            nn.Conv1d(192, 192, 3, padding=2, dilation=2), nn.ReLU(), nn.BatchNorm1d(192),
            nn.Conv1d(192, d, 3, padding=1), nn.ReLU(),
        )
        self.proj = nn.Linear(d, out)  # match teacher dim for distillation

    def embed(self, mel):  # mel: (B, T, n_mel) -> (B, d) L2-normed (the deployable QbE vector)
        h = self.conv(mel.transpose(1, 2))            # (B, d, T)
        v = h.mean(-1)                                 # (B, d)
        return v / (v.norm(dim=-1, keepdim=True) + 1e-8)

    def forward(self, mel):                            # distillation head -> teacher space
        v = self.embed(mel)
        z = self.proj(v)
        return z / (z.norm(dim=-1, keepdim=True) + 1e-8)

    def param_mb(self):
        n = sum(p.numel() for p in self.parameters())
        return n, n * 4 / 1e6


def read_wav(p):
    with wave.open(p, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


# ---------------- teacher targets (wavlm-large L14 mean-pool on LibriSpeech windows) ----------------
def build_teacher(n_windows=6000, layer=14):
    cache = os.path.join(CACHE, f"distill_teacher_{n_windows}.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        print(f"  [cache] teacher {z['mel'].shape[0]} windows", flush=True)
        return z["mel"], z["emb"]
    from transformers import AutoModel
    torch.set_num_threads(4); torch.set_grad_enabled(False)
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    files = sorted(glob.glob(os.path.join(LIBRI, "*.wav")))
    mels, embs = [], []
    t0 = time.time()
    for f in files:
        x = read_wav(f)
        for s in range(0, max(1, x.size - WIN + 1), HOP):
            w = x[s:s + WIN]
            if w.size < WIN:
                break
            wn = (w - w.mean()) / (w.std() + 1e-7)
            h = net(torch.from_numpy(wn.astype(np.float32)).unsqueeze(0)).hidden_states[layer][0].numpy()
            v = h.mean(0); v = v / (np.linalg.norm(v) + 1e-8)
            mels.append(log_mel(w)); embs.append(v.astype(np.float32))
            if len(embs) >= n_windows:
                break
        if len(embs) >= n_windows:
            break
    # pad mel to common length
    T = max(m.shape[0] for m in mels)
    mel = np.stack([np.pad(m, ((0, T - m.shape[0]), (0, 0))) for m in mels]).astype(np.float32)
    emb = np.stack(embs).astype(np.float32)
    np.savez(cache, mel=mel, emb=emb)
    print(f"  teacher {emb.shape[0]} windows ({time.time()-t0:.0f}s)", flush=True)
    return mel, emb


def train_student(mel, emb, epochs=60, bs=128, lr=2e-3):
    torch.set_grad_enabled(True)  # re-enable (teacher inference disabled it globally)
    g = Student()
    n, mb = g.param_mb()
    print(f"  student: {n} params = {mb:.2f} MB fp32 ({mb/4:.2f} MB INT8-equiv)", flush=True)
    opt = torch.optim.Adam(g.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    M = torch.from_numpy(mel); E = torch.from_numpy(emb)
    N = mel.shape[0]
    for ep in range(epochs):
        g.train(); perm = torch.randperm(N); tot = 0.0
        for i in range(0, N, bs):
            idx = perm[i:i + bs]
            z = g(M[idx])
            loss = (1 - (z * E[idx]).sum(-1)).mean()  # cosine distillation
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss) * len(idx)
        sched.step()
        if (ep + 1) % 15 == 0:
            print(f"    epoch {ep+1}: cos-dist {tot/N:.4f}", flush=True)
    g.eval()
    return g


# ---------------- TORGO eval (held out) ----------------
def student_embed_torgo(g):
    out = {}
    with torch.no_grad():
        for grp in (DYS + CTL):
            root = TORGO if not grp.startswith("FC") else os.path.join(TORGO, "FCX")
            d = H.scan(root).get(grp)
            if not d:
                continue
            wavs = set()
            for lst in d["commands"].values():
                wavs.update(lst)
            wavs.update(d["negatives"])
            for w in wavs:
                x = H.energy_vad_trim(read_wav(w))
                if x.size < 400:
                    x = read_wav(w)
                m = torch.from_numpy(log_mel(x)).unsqueeze(0)
                out[w] = g.embed(m)[0].numpy().astype(np.float32)
    return out


def eval_group(se, speakers):
    hits = pos = 0; frr_num = 0.0; fa = neg = 0
    for spk in speakers:
        root = TORGO if not spk.startswith("FC") else os.path.join(TORGO, "FCX")
        d = H.scan(root).get(spk)
        if not d:
            continue
        wavs = set()
        for lst in d["commands"].values():
            wavs.update(lst)
        wavs.update(d["negatives"])
        fc = {w: se[w][None, :] for w in wavs}
        rows = H.eval_speaker(d, None, fc)
        r1, h, n = H.rank1(rows)
        frr, far, npos, nn = H.held_out_global(rows)
        hits += h; pos += n; frr_num += frr * npos; fa += round(far * nn); neg += nn
    return (hits / pos if pos else 0), (frr_num / pos if pos else 0), (fa / neg if neg else 0)


def main():
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    print("DEPLOYABLE STUDENT DISTILLATION (log-mel -> conv, distill wavlm-large L14)\n", flush=True)
    mel, emb = build_teacher(nw)
    g = train_student(mel, emb)
    se = student_embed_torgo(g)
    print("\nTORGO eval (held out from training):", flush=True)
    for grp, spks in [("control(typical)", CTL), ("dysarthric", DYS)]:
        r1, frr, far = eval_group(se, spks)
        print(f"  {grp:18s}: rank1={r1*100:.1f}%  D2 FRR={frr*100:.1f}% @FAR{far*100:.1f}%", flush=True)
    torch.save(g.state_dict(), os.path.join(CACHE, "student.pt"))
    ctl_r1 = eval_group(se, CTL)[0]
    target = 0.59 + 0.9 * (0.88 - 0.59)
    print(f"\nH7 (student control rank1 >= {target*100:.1f}%): {'PASS' if ctl_r1>=target else 'FAIL'} ({ctl_r1*100:.1f}%)", flush=True)
    print("(reference: MFCC ctl ~0.77, wavlm-large ctl ~0.88)", flush=True)
    with open(os.path.join(CACHE, "distill_result.json"), "w") as f:
        json.dump(dict(n_windows=nw, ctl_rank1=ctl_r1), f, indent=2)


if __name__ == "__main__":
    main()
