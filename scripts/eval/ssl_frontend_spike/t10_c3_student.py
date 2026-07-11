"""T10 — C3 student-fidelity confirm (the PRIMARY deliverable of the typical-900 program).

The typical-800 accuracy claim is measured on the wavlm-large TEACHER (316 MB, deployable behind the
VAD gate per the current-banked CONSTRAINT-001 relaxation — but on-device INT8 latency/size is
device-UNVALIDATED, and D11/D12 are excluded from the composite). The ≤150 MB student is the fallback
if the teacher does not actually deploy. The just-committed layer-route report INFERRED a "1-3pp student
penalty"; the carried A3b/C21 number is ~12% but on GSC-24 (harder speakers) — a cross-corpus confound.

This measures the student penalty APPLES-TO-APPLES: the IDENTICAL GSC-19/K5 manifest the teacher's
5.81% uses (a5.pick_speakers), only the encoder changes (change-one-variable, EVAL-004). For each
deployable ≤150 MB encoder it reports best-layer typical D2 FRR@FAR≤5%, the teacher→student penalty,
and whether the SAME 2-3 hard speakers dominate the student tail (intrinsic-vs-encoder-strength
diagnostic).

Students (all cached locally, no download): distilhubert 24MB, wavlm-base-plus 94MB, hubert-base 95MB,
wav2vec2-base 95MB. Band 900 = FRR<=5%, band 800 = <=15% (DomainBands.kt spec 2). FAR-matched.
"""
import os, sys, json, collections
import numpy as np
import torch, soundfile as sf
torch.set_num_threads(4); torch.set_grad_enabled(False)
import cand_lib as L
import harness as H
from a5_gsc_kcurve import pick_speakers, kcurve_speaker, FIXED_WORDS, REPS, FAR

STUDENTS = {
    "distilhubert":    ("ntu-spml/distilhubert",        24),
    "wavlm-base-plus": ("microsoft/wavlm-base-plus",    94),
    "hubert-base":     ("facebook/hubert-base-ls960",   95),
    "wav2vec2-base":   ("facebook/wav2vec2-base",       95),
}
K = 5


def manifest_from_picks():
    """IDENTICAL manifest construction to a5.build_cache (so the speaker/word set matches the teacher)."""
    picks = pick_speakers()
    man, need = {}, []
    for spk, ge5, wc in picks:
        fixed = {w: wc[w][:REPS] for w in ge5[:FIXED_WORDS]}
        neg = []
        for w in ge5[FIXED_WORDS:FIXED_WORDS + 8]:
            neg += wc[w][:4]
        man[spk] = {"fixed": fixed, "neg": neg}
        for w, ps in fixed.items():
            need += ps
        need += neg
    return man, need


def embed_net(net, path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    sp = H.energy_vad_trim(x)
    if sp.size < 1520:
        sp = x if x.size >= 1520 else np.pad(x, (0, 1520 - x.size))
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    hs = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states
    out = []
    for h in hs:
        v = h[0].numpy().mean(0)
        out.append((v / (np.linalg.norm(v) + 1e-8)).astype(np.float32))
    return np.stack(out)  # (n_layers, dim)


def build_student_cache(model_id, need):
    from transformers import AutoModel
    net = AutoModel.from_pretrained(model_id, output_hidden_states=True).eval()
    emb = {}
    print(f"    embedding {len(need)} clips with {model_id} ...", flush=True)
    for i, p in enumerate(need):
        emb[p] = embed_net(net, p)
        if (i + 1) % 300 == 0:
            print(f"      {i+1}/{len(need)}", flush=True)
    return emb


def eval_student(name, man, emb):
    n_layers = next(iter(emb.values())).shape[0]
    best = None
    per_layer = {}
    for lyr in range(1, n_layers):          # skip layer 0 (conv features)
        num = den = fnum = fden = 0
        per_spk = {}
        for s in man:
            frr, far, np_, nn = kcurve_speaker(man[s], emb, K, layer=lyr)
            num += frr * np_; den += np_; fnum += far * nn; fden += nn
            per_spk[s] = frr
        agg, fa = num / den, fnum / fden
        per_layer[lyr] = (agg, fa)
        if best is None or agg < best[1]:
            best = (lyr, agg, fa, per_spk)
    return best, per_layer


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    man, need = manifest_from_picks()
    print(f"C3 STUDENT-FIDELITY — GSC-19 K{K}, teacher(wavlm-large L12)=5.81% band 800\n", flush=True)
    print(f"  {len(man)} speakers, {len(need)} clips/model (identical manifest)\n", flush=True)
    teacher_hard = ["98ea0818", "2aca1e72", "c1d39ce8"]      # from t6/t8 (prefix match)
    results = {}
    for name, (model_id, mb) in STUDENTS.items():
        if only and name != only:
            continue
        cache = os.path.join(L.CACHE, f"gsc_{name}_alllayers.npz")
        if os.path.exists(cache):
            z = np.load(cache, allow_pickle=True)
            emb = {k: z[k] for k in z.files}
            if not all(p in emb for p in need):
                emb = build_student_cache(model_id, need); np.savez(cache, **emb)
        else:
            emb = build_student_cache(model_id, need); np.savez(cache, **emb)
        (bl, agg, fa, per_spk), per_layer = eval_student(name, man, emb)
        band = 900 if agg <= 0.05 else (800 if agg <= 0.15 else 700)
        # student tail: top-3 hardest speakers, and whether they overlap the teacher's 3
        hard_student = sorted(per_spk, key=lambda s: -per_spk[s])[:3]
        overlap = [s for s in hard_student if any(s.startswith(h[:8]) for h in teacher_hard)]
        pen = agg - 0.0581
        print(f"  {name:>15} ({mb}MB): best L{bl}  FRR {agg*100:.2f}%  FAR {fa*100:.1f}%  band {band}  "
              f"| penalty +{pen*100:.1f}pp  | tail overlap teacher: {len(overlap)}/3", flush=True)
        print(f"      student top-3 hard: " + " ".join(f"{s[:8]}={per_spk[s]*100:.0f}%" for s in hard_student), flush=True)
        results[name] = {"mb": mb, "best_layer": bl, "frr": agg, "far": fa, "band": band,
                         "penalty_pp": pen * 100, "tail_overlap": len(overlap),
                         "hard_student": {s: per_spk[s] for s in hard_student},
                         "per_layer": {str(l): per_layer[l] for l in per_layer}}
        with open(os.path.join(L.CACHE, "t10_c3_student.json"), "w") as f:
            json.dump(results, f, indent=2)
    print("\n  wrote t10_c3_student.json", flush=True)


if __name__ == "__main__":
    main()
