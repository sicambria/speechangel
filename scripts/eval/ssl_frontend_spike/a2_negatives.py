"""A2 — Deployment-real negatives vs the dysarthric wall.

The banked severe-dys "0.70 AUC wall" is measured with TORGO IN-VOCAB OOV singletons as the impostor
set — the hardest possible confusors (same speaker, real words, just not enrolled). But deployment FAs
come from AMBIENT / OTHER-SPEAKER speech, which is a much easier negative distribution (A3 showed real
ambient → ~0 accepts). A2 asks: how much of the 0.70 wall is a HARD-NEGATIVE-SET artifact vs intrinsic?

Rescore the cached severe-dys genuine distances against THREE negative pools and compare separability:
  (1) in-vocab OOV singletons (banked, hardest)
  (2) other-speaker speech (LibriSpeech test-clean, English) + multilingual OOV (CommonVoice)
  (3) real ambient noise (DEMAND)
all embedded with the SAME encoder (wavlm-large L15) and scored min-dist to the dys speaker's enrolled
commands.

PRE-REGISTERED GATE: severe-dys AUC(genuine < impostor) >= 0.85 against the ambient/OOV pool
  -> a large share of the "wall" is a negative-set artifact; §7.2(b) (reject ambient, not confusors) is
     evidence-backed. If AUC stays ~0.70 even vs ambient, the wall is intrinsic to genuine-side scatter.
"""
import os, sys, glob, math, json, wave
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H

LAYER = 15
SR = 16000
PV = os.path.expanduser("~/picovoice-benchmark")
GSC = os.path.expanduser("~/gsc/data")
np.random.seed(1)


def read_any(path, max_s=3.0):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x), n, endpoint=False), np.arange(len(x)), x).astype(np.float32)
    return x[: int(max_s * SR)]


def embed(net, x):
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def build_oov_pool(net, n_each=120):
    """Embed other-speaker (LibriSpeech), multilingual (CommonVoice), and ambient (DEMAND) negatives."""
    pools = {}
    libs = glob.glob(os.path.join(PV, "LibriSpeech", "test-clean", "*", "*", "*.flac"))
    np.random.shuffle(libs)
    pools["other-spk(Libri)"] = [embed(net, read_any(f)) for f in libs[:n_each]]
    cvs = []
    for lang in ["fr", "de", "italian", "dutch", "ar"]:
        cvs += glob.glob(os.path.join(PV, "common-voice", lang, "**", "*.mp3"), recursive=True)[:40]
        cvs += glob.glob(os.path.join(PV, "common-voice", lang, "**", "*.wav"), recursive=True)[:40]
    np.random.shuffle(cvs)
    pools["multiling(CV)"] = [embed(net, read_any(f)) for f in cvs[:n_each] if os.path.getsize(f) > 2000]
    # DEMAND ambient: slice random 2s windows
    dem = glob.glob(os.path.join(PV, "demand", "*", "ch01.wav"))
    amb = []
    for f in dem[:8]:
        x = read_any(f, max_s=30)
        for _ in range(15):
            s = np.random.randint(0, max(1, x.size - 2 * SR))
            amb.append(embed(net, x[s : s + 2 * SR]))
    pools["ambient(DEMAND)"] = amb
    return pools


def dys_genuine_and_invocab(emb, spk):
    """Return (genuine_dists, invocab_impostor_dists, enroll_templates) for one dys speaker,
    few-shot leave-one-out (min-agg), wavlm-large L15."""
    d = L.load_speaker(spk)
    words = {w: [emb[x][LAYER] for x in v if x in emb] for w, v in d["commands"].items()}
    words = {w: v for w, v in words.items() if len(v) >= 2}
    if len(words) < 3:
        return None
    gen = []
    for w, vs in words.items():
        for i, q in enumerate(vs):
            tmpl = [vs[j] for j in range(len(vs)) if j != i]
            gen.append(min(1 - float(q @ t) for t in tmpl))
    enroll = {w: vs for w, vs in words.items()}
    negs = [emb[x][LAYER] for x in d["negatives"] if x in emb]
    inv = [min(min(1 - float(nv @ t) for t in tt) for tt in enroll.values()) for nv in negs]
    return np.array(gen), np.array(inv), enroll


def auc(gen, imp):
    if len(gen) == 0 or len(imp) == 0:
        return None
    return float(np.mean(gen[:, None] < np.array(imp)[None, :]))


def main():
    emb = L.load_emb("wavlm-large")
    from transformers import AutoModel
    print("A2 — dysarthric wall vs deployment-real negatives (wavlm-large L15)\n", flush=True)
    net = AutoModel.from_pretrained("microsoft/wavlm-large", output_hidden_states=True).eval()
    print("  embedding OOV/ambient pools...", flush=True)
    pools = build_oov_pool(net)
    for k, v in pools.items():
        print(f"    {k}: {len(v)} clips", flush=True)
    out = {}
    print(f"\n  {'speaker':>7}  {'in-vocab':>9} {'other-spk':>10} {'multiling':>10} {'ambient':>9}", flush=True)
    for spk in L.DYS:
        r = dys_genuine_and_invocab(emb, spk)
        if r is None:
            print(f"  {spk}: insufficient", flush=True); continue
        gen, inv, enroll = r
        row = {"in-vocab": auc(gen, inv)}
        for name, pool in pools.items():
            imp = [min(min(1 - float(nv @ t) for t in tt) for tt in enroll.values()) for nv in pool]
            row[name] = auc(gen, imp)
        out[spk] = row
        print(f"  {spk:>7}  {row['in-vocab']:9.3f} {row['other-spk(Libri)']:10.3f} "
              f"{row['multiling(CV)']:10.3f} {row['ambient(DEMAND)']:9.3f}", flush=True)
    # dys pooled
    def pooled(key):
        gs, ims = [], []
        for spk in L.DYS:
            r = dys_genuine_and_invocab(emb, spk)
            if r is None:
                continue
            gen, inv, enroll = r
            gs.append(gen)
            if key == "in-vocab":
                ims.append(inv)
            else:
                ims.append(np.array([min(min(1 - float(nv @ t) for t in tt) for tt in enroll.values()) for nv in pools[key]]))
        g = np.concatenate(gs); im = np.concatenate(ims)
        return auc(g, im)
    print("\n  DYS pooled AUC:", flush=True)
    verdict = {}
    for key in ["in-vocab", "other-spk(Libri)", "multiling(CV)", "ambient(DEMAND)"]:
        a = pooled(key)
        verdict[key] = a
        print(f"    {key:16s}: AUC={a:.3f}", flush=True)
    amb_auc = verdict["ambient(DEMAND)"]
    print(f"\n  GATE (dys AUC vs ambient >= 0.85): {'PASS -> wall is largely a hard-negative-set artifact' if amb_auc >= 0.85 else 'FAIL -> wall persists even vs ambient (intrinsic genuine-side scatter)'}", flush=True)
    out["_pooled"] = verdict
    with open(os.path.join(L.CACHE, "a2_negatives.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
