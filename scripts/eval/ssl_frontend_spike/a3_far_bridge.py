"""A3 — FAR%/trial -> FA/hr bridge (repairs the §2 D2 operating-point mismatch).

The banked D2 (typical 13.8%) is FRR @ FAR<=5% *per trial* against TORGO in-vocab OOV singletons.
The bands-doc deployment target is <=5 FA/hr on real ambient. Those are DIFFERENT operating points.
A3 restates 13.8% at the deployment operating point.

Three measured parts:
  1. TRIGGER RATE  T = VAD-gated windows/hour on real ambient (DEMAND noise + LibriSpeech speech,
     deployed hop/refractory). This is "windows/hour at the deployed hop".
  2. AMBIENT FA/hr at the banked threshold: enroll a typical speaker (wavlm-large L15, few-shot,
     vocab-distinct), fix the threshold at FAR<=5% on in-vocab confusors (the banked point), stream
     ambient, count accepts -> the ACTUAL FA/hr that "13.8% @ FAR5%/trial" corresponds to.
  3. RESTATEMENT: typical-D2 FRR-vs-FAR curve (cached) -> the FRR at the tighter per-trial FAR that
     yields <=5 FA/hr and <=0.5 FA/hr, given T.

PRE-REGISTERED framing (not a pass/fail gate — a translation): report T, the implied FA/hr at
FAR=5%/trial, and the FRR at the FAR budget that meets <=5 FA/hr. Honest if FA/hr >> 5.
"""
import os, sys, glob, math, wave, json
import numpy as np
import torch
import soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H

SR, WIN_S, HOP_S, REFRACTORY_S, MIN_SPEECH = 16000, 1.5, 0.5, 1.0, 1520
PV = os.path.expanduser("~/picovoice-benchmark")
LAYER = 15                       # wavlm-large ceiling layer (for the cached FRR-vs-FAR restatement)
STREAM_MODEL, STREAM_LAYER = "ntu-spml/distilhubert", 2   # the DEPLOYABLE encoder (fast) for FA/hr
np.random.seed(42)


def read_any(path, max_s=None):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:  # linear resample
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x), n, endpoint=False), np.arange(len(x)), x).astype(np.float32)
    if max_s:
        x = x[: int(max_s * SR)]
    return x


def stream_windows(x):
    """Yield VAD-passed (trimmed) speech windows with deployed hop + refractory."""
    win, hop, refr = int(WIN_S * SR), int(HOP_S * SR), int(REFRACTORY_S * SR)
    i = 0
    last_fire = -10 ** 9
    while i + win <= x.size:
        if i - last_fire < refr:
            i += hop
            continue
        seg = x[i : i + win]
        sp = H.energy_vad_trim(seg)
        if sp.size >= MIN_SPEECH:
            yield sp
            last_fire = i
        i += hop


def ambient_sources(hours_cap):
    """Return list of (name, wav_array) real-ambient sources up to ~hours_cap total."""
    srcs = []
    total = 0.0
    # DEMAND noise environments (real ambient, non-speech)
    for env in sorted(glob.glob(os.path.join(PV, "demand", "*", "ch01.wav"))):
        name = "DEMAND/" + env.split("/demand/")[1].split("/")[0]
        x = read_any(env)
        srcs.append((name, x)); total += x.size / SR / 3600
        if total >= hours_cap * 0.6:
            break
    # LibriSpeech test-clean (speech ambient = TV/other-speaker)
    flacs = sorted(glob.glob(os.path.join(PV, "LibriSpeech", "test-clean", "*", "*", "*.flac")))
    np.random.shuffle(flacs)
    li = 0
    while total < hours_cap and li < len(flacs):
        x = read_any(flacs[li]); li += 1
        srcs.append(("LibriSpeech", x)); total += x.size / SR / 3600
    return srcs, total


def embed(net, sp, layer):
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[layer][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


def typical_enroll_and_threshold(emb, layer):
    """Enroll all control speakers' vocab-distinct <=25 few-shot at the DEPLOYABLE encoder layer;
    return (templates, thr@FAR5%, score_fn). Threshold fit on in-vocab OOV singleton confusors."""
    from held_out_d2 import distinct_subset
    templ = {}
    negs = []
    for spk in L.CTL:
        d = L.load_speaker(spk)
        keep = distinct_subset(d, emb, layer, 25)
        for w in keep:
            vs = [emb[x][layer] for x in d["commands"][w] if x in emb]
            if vs:
                templ.setdefault(f"{spk}:{w}", []).extend(vs)
        negs.extend(emb[x][layer] for x in d["negatives"] if x in emb)

    def score(qv):
        return min((min(1 - float(qv @ t) for t in tt), w) for w, tt in templ.items())

    neg_d = sorted(score(nv)[0] for nv in negs)
    thr = neg_d[int(0.05 * len(neg_d)) - 1] if len(neg_d) >= 20 else neg_d[0]
    return templ, thr, score


def d2_frr_at_far(emb, far_targets):
    """Typical (control) held-out D2 FRR at each FAR target (vocab-distinct, few-shot, min-agg).
    Uses cand_lib.held_out_frr_far with an EXPLICIT target (avoids the held_out_d2 default-arg bug)."""
    from b_single import build_rows
    out = {}
    for far in far_targets:
        num = den = 0
        for s in L.CTL:
            r = build_rows(s, emb, LAYER, "min")
            if r is None:
                continue
            pr, fp, nr, fn, _ = r
            frr, _, npos, _ = L.held_out_frr_far(pr, nr, fp, fn, L.global_threshold_accept, target=far)
            num += frr * npos; den += npos
        out[far] = num / den if den else None
    return out


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    print(f"A3 FAR->FA/hr BRIDGE — wavlm-large L{LAYER}, ~{hours}h real ambient\n", flush=True)
    emb = L.load_emb("wavlm-large")

    # PART 3 (cheap, cached): FRR-vs-FAR curve on typical D2
    fars = [0.05, 0.02, 0.01, 0.005, 0.002]
    print("  [3] Typical D2 FRR-vs-FAR (held-out, vocab-distinct, few-shot):", flush=True)
    frr_curve = d2_frr_at_far(emb, fars)
    for f in fars:
        v = frr_curve[f]
        print(f"      FAR<={f*100:4.1f}%/trial -> D2 FRR={v*100:5.1f}%" if v is not None else f"      FAR{f}: n/a", flush=True)

    # PART 1+2: stream ambient with the DEPLOYABLE encoder (distilhubert L2 = the banked deployment path)
    print(f"\n  [1] Trigger rate + [2] ambient FA/hr (streaming real ambient, distilhubert L{STREAM_LAYER})...", flush=True)
    from transformers import AutoModel
    net = AutoModel.from_pretrained(STREAM_MODEL, output_hidden_states=True).eval()
    stream_emb = L.load_emb("distilhubert")
    templ, thr, score = typical_enroll_and_threshold(stream_emb, STREAM_LAYER)
    srcs, total_h = ambient_sources(hours)
    trials = 0; accepts = 0
    per_src = {}
    for name, x in srcs:
        t0 = trials; a0 = accepts
        for sp in stream_windows(x):
            trials += 1
            qv = embed(net, sp, STREAM_LAYER)
            d1, w1 = score(qv)
            if d1 <= thr:
                accepts += 1
        ps = per_src.setdefault(name.split("/")[0], [0, 0, 0.0])
        ps[0] += trials - t0; ps[1] += accepts - a0; ps[2] += x.size / SR / 3600
    T = trials / total_h if total_h else 0
    fa_hr_at5 = accepts / total_h if total_h else 0
    print(f"      streamed {total_h:.2f}h, trials={trials} -> T={T:.0f} trials/hr", flush=True)
    for k, (tr, ac, h) in per_src.items():
        print(f"        {k:14s}: {tr/ h:6.0f} trials/hr, {ac/h:6.1f} FA/hr  ({h:.2f}h)", flush=True)
    print(f"\n  [2] BANKED point (thr@FAR5%/trial) on real ambient: {fa_hr_at5:.1f} FA/hr", flush=True)

    # bridge arithmetic
    print(f"\n  BRIDGE:", flush=True)
    print(f"      At FAR=5%/trial the ambient FA/hr = {fa_hr_at5:.1f} (measured).", flush=True)
    for budget in [5.0, 0.5]:
        req_far = budget / T if T else 0
        # nearest swept FAR >= required
        best = None
        for f in sorted(fars):
            if f <= req_far:
                best = f
        frr_at = frr_curve.get(best) if best else None
        print(f"      For <={budget} FA/hr: need FAR<={req_far*100:.3f}%/trial "
              f"-> typical D2 FRR ~ {frr_at*100:.1f}% (@FAR{best*100:.2f}%)" if frr_at is not None
              else f"      For <={budget} FA/hr: need FAR<={req_far*100:.3f}%/trial (below swept grid)", flush=True)
    out = dict(hours=total_h, trials=trials, T_per_hr=T, fa_hr_at_far5=fa_hr_at5,
               frr_curve={str(k): v for k, v in frr_curve.items()}, per_src=per_src)
    with open(os.path.join(L.CACHE, "a3_far_bridge.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
