"""C21 — Deployable-gap decomposition (large -> base -> distilled), typical D2.

The report cites a 3-18 pp retention gap between the wavlm-large CEILING and the deployable <=25 MB
encoder, but never attributes it. C21 measures the SAME typical-D2 protocol (held-out FRR@FAR<=5%,
vocab-distinct <=25, few-shot, mean-of-best-2 AND min) across the cached encoder ladder to split the gap
into causal shares:
  wavlm-large  (316 MB ceiling, L15)   -- the ceiling
  wavlm-base+  ( 94 MB,        L~10-12) -- capacity drop, same SSL objective
  distilhubert ( 23 MB,        L2)      -- the deployable encoder (distillation)
INT8 quantization (~<1-2 pp, not cached) noted as a residual, not measured here.

PRE-REGISTERED: report each rung's typical-D2 FRR; the large->base delta = capacity share, base->distil
delta = distillation share. No pass/fail — a decomposition.
"""
import os, json
import numpy as np
import cand_lib as L
from b_single import build_rows

FAR = 0.05
LADDER = [("wavlm-large", 15, "316MB ceiling"), ("wavlm-base-plus", 12, "94MB"),
          ("wavlm-base-plus", 10, "94MB alt-layer"), ("distilhubert", 2, "23MB deployable")]


def d2_typical(model, layer, agg):
    emb = L.load_emb(model)
    num = den = fanum = 0
    for s in L.CTL:
        r = build_rows(s, emb, layer, agg)
        if r is None:
            continue
        pr, fp, nr, fn, _ = r
        frr, far, npos, _ = L.held_out_frr_far(pr, nr, fp, fn, L.global_threshold_accept, target=FAR)
        num += frr * npos; den += npos; fanum += far * npos
    return (num / den, fanum / den, den) if den else (None, None, 0)


def main():
    print("C21 — deployable-gap decomposition (typical D2 FRR@FAR<=5%, held-out)\n", flush=True)
    print(f"  {'encoder':>16} {'layer':>5} {'note':>16}  {'min-agg':>8}  {'mean2':>8}", flush=True)
    res = []
    for model, layer, note in LADDER:
        mn = d2_typical(model, layer, "min")
        m2 = d2_typical(model, layer, "mean2")
        if mn[0] is None:
            print(f"  {model:>16} L{layer}: n/a", flush=True); continue
        res.append((model, layer, note, mn[0], m2[0], mn[1]))
        print(f"  {model:>16} {layer:>5} {note:>16}  {mn[0]*100:7.1f}%  {m2[0]*100:7.1f}%  (@FAR{mn[1]*100:.0f})", flush=True)
    # decomposition on min-agg
    large = next((r for r in res if r[0] == "wavlm-large"), None)
    base = next((r for r in res if r[0] == "wavlm-base-plus" and r[1] == 12), None)
    distil = next((r for r in res if r[0] == "distilhubert"), None)
    if large and base and distil:
        cap = (base[3] - large[3]) * 100
        dist = (distil[3] - base[3]) * 100
        print(f"\n  DECOMPOSITION (min-agg): total gap {(distil[3]-large[3])*100:+.1f}pp = "
              f"capacity(large->base) {cap:+.1f}pp + distillation(base->distil) {dist:+.1f}pp "
              f"(+ INT8 residual ~1-2pp, unmeasured)", flush=True)
        with open(os.path.join(L.CACHE, "c21_deployable_gap.json"), "w") as f:
            json.dump({"ladder": [[m, l, n, f1, f2] for m, l, n, f1, f2, _ in res],
                       "capacity_pp": cap, "distillation_pp": dist}, f, indent=2)


if __name__ == "__main__":
    main()
