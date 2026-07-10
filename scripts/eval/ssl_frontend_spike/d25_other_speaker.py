"""D25 — Other-speaker false-accept measurement (is a personal-VAD / speaker gate even needed?).

The recognizer is speaker-dependent by construction (enrolled on the user's own reps). D25 quantifies how
much rejection that actually buys: at a user's FAR<=5% threshold (fit on the user's OWN in-vocab
confusors), how often does ANOTHER speaker trigger a false accept — especially when saying the SAME
command word (the hardest other-speaker case)?

  self-OOV       : the banked in-vocab confusor FA (reference, = 5% by construction)
  other-same-word: another speaker says one of the user's enrolled command words  <- the real threat
  other-OOV      : another speaker says a different word

If other-same-word FA is already low, speaker-dependence is INHERENT to encoder+enrollment (no extra
speaker gate needed). If high, a personal-VAD gate (I-series) earns its complexity.

Cached wavlm-large L15. Pre-registered read (diagnostic): report the three FA rates per user population.
"""
import os, json
import numpy as np
import cand_lib as L
from held_out_d2 import distinct_subset

LAYER = 15
FAR = 0.05


def user_thresholds_and_fa(user, emb, layer, others):
    d = L.load_speaker(user)
    keep = distinct_subset(d, emb, layer, 25)
    templ = {}
    enrolled_words = set()
    for w in keep:
        vs = [emb[x][layer] for x in d["commands"][w] if x in emb]
        if vs:
            templ[w] = vs; enrolled_words.add(w)
    if len(templ) < 3:
        return None
    self_neg = [emb[x][layer] for x in d["negatives"] if x in emb]

    def nn(v):
        return min(min(1 - float(v @ t) for t in tt) for tt in templ.values())

    self_d = sorted(nn(v) for v in self_neg)
    thr = self_d[int(FAR * len(self_d)) - 1] if len(self_d) >= 20 else self_d[0]
    # other-speaker utts split by same-word vs OOV
    osame, oother = [], []
    for o in others:
        od = L.load_speaker(o)
        if not od:
            continue
        for w, wavs in od["commands"].items():
            for x in wavs:
                if x not in emb:
                    continue
                (osame if w in enrolled_words else oother).append(emb[x][layer])
    def fa(pool):
        return float(np.mean([nn(v) <= thr for v in pool])) if pool else None
    return dict(thr=float(thr), self_far=FAR, other_same=fa(osame), other_oov=fa(oother),
                n_same=len(osame), n_oov=len(oother))


def main():
    emb = L.load_emb("wavlm-large")
    print(f"D25 — other-speaker FA at the user's FAR<=5% threshold (wavlm-large L{LAYER})\n", flush=True)
    print(f"  {'user':>6} {'grp':>4}  {'other-same-word FA':>18} {'other-OOV FA':>13}", flush=True)
    out = {}
    for grp, spks in [("CTL", L.CTL), ("DYS", L.DYS)]:
        for u in spks:
            others = [s for s in (L.CTL + L.DYS) if s != u]
            r = user_thresholds_and_fa(u, emb, LAYER, others)
            if r is None:
                print(f"  {u:>6} {grp:>4}  insufficient", flush=True); continue
            out[u] = dict(grp=grp, **r)
            os_ = f"{r['other_same']*100:.1f}%" if r['other_same'] is not None else "n/a"
            oo_ = f"{r['other_oov']*100:.1f}%" if r['other_oov'] is not None else "n/a"
            print(f"  {u:>6} {grp:>4}  {os_:>18} {oo_:>13}  (n_same={r['n_same']})", flush=True)
    same = [v['other_same'] for v in out.values() if v.get('other_same') is not None]
    oov = [v['other_oov'] for v in out.values() if v.get('other_oov') is not None]
    if same:
        ms, mo = float(np.mean(same)), float(np.mean(oov))
        print(f"\n  MEAN: other-same-word FA={ms*100:.1f}%  other-OOV FA={mo*100:.1f}%  (self-OOV=5.0% by construction)", flush=True)
        print(f"  READ: {'other-same-word FA is HIGH -> a personal-VAD/speaker gate earns its complexity' if ms > 0.10 else 'other-same-word FA is LOW -> speaker-dependence is inherent to encoder+enrollment; no extra speaker gate needed'}", flush=True)
        out["_read"] = dict(other_same_mean=ms, other_oov_mean=mo)
    with open(os.path.join(L.CACHE, "d25_other_speaker.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
