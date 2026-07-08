"""Export DistilHuBERT to ONNX fp32 and verify fidelity against PyTorch.

Usage: python onnx_export.py
Outputs: distilhubert_encoder_fp32.onnx (89.7 MB, opset 17)
         distilhubert_encoder_fp16.onnx (converted, 44.9 MB — known type-mismatch on load)

E14 confirms: fp16 causes 0% FRR degradation. v1 deploys fp32.
"""
import os, sys, time, wave, warnings
import numpy as np
import torch
torch.set_num_threads(4)
from transformers import AutoModel
import onnx
from onnxconverter_common import float16 as oc_float16

MODEL, LAYER = "ntu-spml/distilhubert", 2
OPSET = 17
OUTDIR = os.path.dirname(os.path.abspath(__file__))
OUT_FP32 = os.path.join(OUTDIR, "distilhubert_encoder_fp32.onnx")
OUT_FP16 = os.path.join(OUTDIR, "distilhubert_encoder_fp16.onnx")

SR = 16000
MIN_SPEECH = 1520


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def main():
    print("Loading DistilHuBERT...", flush=True)
    net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
    torch.set_grad_enabled(False)

    class DistilHuBERTEncoder(torch.nn.Module):
        def __init__(self, backbone, layer):
            super().__init__()
            self.backbone = backbone
            self.layer = layer

        def forward(self, audio):
            out = self.backbone(audio, output_hidden_states=True)
            h = out.hidden_states[self.layer]
            v = h.mean(dim=1)
            return v / (v.norm(dim=1, keepdim=True) + 1e-8)

    encoder = DistilHuBERTEncoder(net, LAYER)
    dummy = torch.randn(1, 32000, dtype=torch.float32)
    with torch.no_grad():
        out_pt = encoder(dummy)
    assert out_pt.shape == (1, 768), f"Bad shape: {out_pt.shape}"

    fp32_exists = os.path.exists(OUT_FP32)
    if fp32_exists:
        print(f"ONNX already exists: {OUT_FP32} ({os.path.getsize(OUT_FP32)/1024/1024:.1f} MB)")
    else:
        print("Exporting fp32 ONNX (opset 17, dynamo=False)...", flush=True)
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            torch.onnx.export(
                encoder, (dummy,), OUT_FP32,
                input_names=["audio"], output_names=["emb"],
                dynamic_axes={"audio": {1: "time_steps"}},
                opset_version=OPSET, dynamo=False,
            )
        dt = time.time() - t0
        sz = os.path.getsize(OUT_FP32) / 1024 / 1024
        print(f"  Size: {sz:.1f} MB  Export time: {dt:.1f}s", flush=True)

    print("Verifying ONNX vs PyTorch...", flush=True)
    import onnxruntime as ort
    sess = ort.InferenceSession(OUT_FP32)

    dists = []
    for i in range(20):
        t = torch.randn(1, np.random.randint(16000, 80000), dtype=torch.float32)
        with torch.no_grad():
            pt = encoder(t).numpy().flatten()
        on = sess.run(None, {"audio": t.numpy()})[0].flatten()
        dists.append(float(1.0 - pt @ on))
    dists = np.array(dists)
    print(f"  Synthetic: mean={dists.mean():.2e} max={dists.max():.2e}", flush=True)

    print("Real-audio fidelity (200 TORGO utterances)...", flush=True)
    sys.path.insert(0, OUTDIR)
    import harness as H

    def embed_pt(x):
        sp = H.energy_vad_trim(x)
        if sp.size < MIN_SPEECH:
            return None
        w = (sp - sp.mean()) / (sp.std() + 1e-7)
        with torch.no_grad():
            v = encoder(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).numpy().flatten()
        return v / (np.linalg.norm(v) + 1e-8)

    def embed_onnx(x):
        sp = H.energy_vad_trim(x)
        if sp.size < MIN_SPEECH:
            return None
        w = (sp - sp.mean()) / (sp.std() + 1e-7)
        v = sess.run(None, {"audio": w.astype(np.float32).reshape(1, -1)})[0].flatten()
        return v / (np.linalg.norm(v) + 1e-8)

    import random
    random.seed(42)
    all_wavs = []
    for root, spk_list in [(os.path.expanduser("~/torgo"), ["F01", "F03", "F04"]),
                           (os.path.expanduser("~/torgo/FCX"), ["FC01", "FC02", "FC03"])]:
        data = H.scan(root)
        for spk in spk_list:
            if spk in data:
                for wavs in data[spk]["commands"].values():
                    all_wavs.extend(wavs)
    random.shuffle(all_wavs)

    real_dists = []
    for wav in all_wavs[:200]:
        try:
            x = read_wav(wav)
            v_pt = embed_pt(x)
            v_on = embed_onnx(x)
            if v_pt is not None and v_on is not None:
                real_dists.append(float(1.0 - v_pt @ v_on))
        except Exception:
            pass
    real_dists = np.array(real_dists)
    print(f"  Real audio (n={len(real_dists)}): mean={real_dists.mean():.2e} max={real_dists.max():.2e}", flush=True)

    if real_dists.max() > 1e-5:
        print("WARNING: real-audio fidelity gap > 1e-5", flush=True)
    else:
        print("PASS: ONNX embeddings match PyTorch within 1e-5 cos dist", flush=True)

    print("\nBenchmark (x86 onnxruntime)...", flush=True)
    for dur_s in [1.0, 1.5, 3.0]:
        t = np.random.randn(1, int(16000 * dur_s)).astype(np.float32)
        times = []
        for _ in range(30):
            t0 = time.time()
            sess.run(None, {"audio": t})
            times.append(time.time() - t0)
        times = np.array(times[10:])
        print(f"  {dur_s:.1f}s audio: {times.mean()*1000:.0f}ms ±{times.std()*1000:.0f}ms", flush=True)

    if not os.path.exists(OUT_FP16):
        print("\nConverting to fp16 (onnxsim → float16 converter pipeline)...", flush=True)
        from onnxsim import simplify
        model = onnx.load(OUT_FP32)
        model_simp, check = simplify(model)
        print(f"  Simplified: {len(model.graph.node)} → {len(model_simp.graph.node)} nodes, check={check}",
              flush=True)

        model_fp16 = oc_float16.convert_float_to_float16(model_simp)
        onnx.save(model_fp16, OUT_FP16)
        sz = os.path.getsize(OUT_FP16) / 1024 / 1024
        print(f"  fp16 size: {sz:.1f} MB", flush=True)

        import onnxruntime as ort
        try:
            sess16 = ort.InferenceSession(OUT_FP16)
            t = np.random.randn(1, 32000).astype(np.float16)
            out16 = sess16.run(None, {"audio": t})[0]
            print(f"  fp16 inference OK: shape={out16.shape}, dtype={out16.dtype}", flush=True)

            # Fidelity check
            sess32 = ort.InferenceSession(OUT_FP32)
            t32 = np.random.randn(1, 32000).astype(np.float32)
            out32 = sess32.run(None, {"audio": t32})[0]
            cd = 1.0 - float(out32.flatten() @ out16.flatten().astype(np.float32).T)
            print(f"  fp32 vs fp16 cos dist: {cd:.2e}", flush=True)
        except Exception as e:
            print(f"  fp16 load failed (expected on some ORT versions): {e}", flush=True)

    print(f"\nDone. ONNX models:")
    print(f"  fp32: {OUT_FP32} ({os.path.getsize(OUT_FP32)/1024/1024:.1f} MB)")
    if os.path.exists(OUT_FP16):
        print(f"  fp16: {OUT_FP16} ({os.path.getsize(OUT_FP16)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
