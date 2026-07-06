"""Paired McNemar test (per speaker + aggregate) between two arms' per-utterance rank-1 outcomes."""
import sys, json, math, os

a_arm = sys.argv[1] if len(sys.argv) > 1 else "mfcc"
b_arm = sys.argv[2] if len(sys.argv) > 2 else "ssl_wavlm_12_mean"
A = json.load(open(f"results_{a_arm}.json"))["rows_correct"]
B = json.load(open(f"results_{b_arm}.json"))["rows_correct"]


def norm_chi2_p(chi2):
    # survival of chi2 df=1 = erfc(sqrt(chi2/2))
    return math.erfc(math.sqrt(chi2 / 2.0))


def mcnemar(wavs):
    b = c = 0  # b: A right B wrong ; c: A wrong B right
    for w in wavs:
        if w not in A or w not in B:
            continue
        if A[w] == 1 and B[w] == 0:
            b += 1
        elif A[w] == 0 and B[w] == 1:
            c += 1
    n = b + c
    if n == 0:
        return b, c, float("nan"), 1.0
    chi2 = (abs(b - c) - 1) ** 2 / n  # continuity-corrected
    return b, c, chi2, norm_chi2_p(chi2)


def speaker_of(wav):
    parts = wav.split(os.sep)
    for p in parts:
        if len(p) in (3, 4) and (p[0] in "FM"):
            return p
    return "?"


groups = {}
for w in set(A) & set(B):
    groups.setdefault(speaker_of(w), []).append(w)

print(f"McNemar: A={a_arm}  B={b_arm}   (b=A-right/B-wrong, c=A-wrong/B-right; B better if c>b)")
print(f"{'group':>8} {'n':>5} {'b':>4} {'c':>4} {'chi2':>7} {'p':>10}  A-acc  B-acc")
for g in sorted(groups):
    ws = groups[g]
    b, c, chi2, p = mcnemar(ws)
    aacc = sum(A[w] for w in ws) / len(ws)
    bacc = sum(B[w] for w in ws) / len(ws)
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"{g:>8} {len(ws):>5} {b:>4} {c:>4} {chi2:>7.2f} {p:>10.2e}  {aacc*100:5.1f}% {bacc*100:5.1f}%  {star}")
allw = list(set(A) & set(B))
b, c, chi2, p = mcnemar(allw)
aacc = sum(A[w] for w in allw) / len(allw)
bacc = sum(B[w] for w in allw) / len(allw)
print(f"{'ALL':>8} {len(allw):>5} {b:>4} {c:>4} {chi2:>7.2f} {p:>10.2e}  {aacc*100:5.1f}% {bacc*100:5.1f}%")
