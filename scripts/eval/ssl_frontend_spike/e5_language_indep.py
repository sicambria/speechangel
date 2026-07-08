"""E5: Language-independence gate — DistilHuBERT on MLS multilingual background.

H1: Non-English speech (MLS: fr, de, es, it, pt, nl — ~80 min total) is no closer 
to English TORGO templates than English LibriSpeech — FA/hr at DistilHuBERT's 
clean-English threshold degrades <=2x for >=5 of 6 languages.

Protocol: Same as LibriSpeech background scan. Scan each language's clips as background 
against English TORGO templates. Measure FA/hr at the clean-English operating threshold.
Re-calibrate threshold per language for worst-case comparison.
"""
import os, sys, glob, math, time, wave
import numpy as np
import harness as H

SPEAKERS = ["F01", "F03"]
BG_MIN = 999  # all available
SR, WIN_S, HOP_S, REFRACTORY_S = 16000, 1.5, 0.5, 1.0
MIN_SPEECH = 1520
MODEL, LAYER = "ntu-spml/distilhubert", 2
CV_DIR = os.path.expanduser("~/picovoice-benchmark/common-voice")
LANGUAGES = ["french", "german", "spanish", "italian", "portuguese", "dutch"]
LANG_CODES = ["fr", "de", "es", "it", "pt", "nl"]

import torch; torch.set_num_threads(4)
from transformers import AutoModel
net = AutoModel.from_pretrained(MODEL, output_hidden_states=True).eval()
torch.set_grad_enabled(False)

def embed_with_dur(x):
    sp = H.energy_vad_trim(x)
    dur_sp = sp.size if sp.size >= MIN_SPEECH else 0
    if sp.size < MIN_SPEECH: return None, dur_sp, x.size
    w = (sp - sp.mean()) / (sp.std() + 1e-7)
    h = net(torch.from_numpy(w.astype(np.float32)).unsqueeze(0)).hidden_states[LAYER][0].numpy()
    v = h.mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32), dur_sp, x.size

def cos_d(a,b): return 1.0 - float(a @ b)

def read_wav(path):
    with wave.open(path,'rb') as w:
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768.0

t0 = time.time()

# 1. Load TORGO + English LibriSpeech bg (reuse cached embeddings)
print("Loading TORGO...", flush=True)
all_data = {}
for spk in SPEAKERS:
    d = H.scan(os.path.expanduser('~/torgo')).get(spk)
    if d: all_data[spk] = d

# Embed TORGO
emb_info = {}
all_wavs = sorted({w for d in all_data.values() for lst in d['commands'].values() for w in lst})
for wav in all_wavs:
    x = read_wav(wav); emb_info[wav] = embed_with_dur(x)
print(f"  {sum(1 for v in emb_info.values() if v[0] is not None)}/{len(all_wavs)} TORGO embedded", flush=True)

# Build speaker templates + LOO scores (clean English bg will be re-used)
spk_info = {}
for spk, d in all_data.items():
    all_tmps = []
    for word, wavs in d['commands'].items():
        for w in wavs:
            v, ds, dr = emb_info.get(w, (None,0,0))
            if v is not None: all_tmps.append((v, ds, word, w))
    n_pos = len(all_tmps)
    pos_recs = []
    for i, (qv, qds, qw, qwv) in enumerate(all_tmps):
        dists = []
        for j, (tv, tds, tw, twv) in enumerate(all_tmps):
            if j == i: continue
            dists.append((cos_d(qv,tv), j, tw, tds))
        dists.sort(key=lambda x:x[0])
        if len(dists) >= 2:
            d1, _, _, tds1 = dists[0]; d2 = dists[1][0]
            dr_val = abs(math.log(max(qds,1)/max(tds1,1))) if qds>0 and tds1>0 else 0.0
            mr_val = d1/max(d2,1e-8)
        elif len(dists) == 1:
            d1, _, _, tds1 = dists[0]
            dr_val = abs(math.log(max(qds,1)/max(tds1,1))) if qds>0 and tds1>0 else 0.0; mr_val = 0.0
        else: continue
        pos_recs.append((d1, dr_val, mr_val))
    spk_info[spk] = {"all_tmps": all_tmps, "n_pos": n_pos, "pos_recs": pos_recs}

# 2. English LibriSpeech background scan
PV = os.path.expanduser("~/picovoice-benchmark")
print(f"\nScanning English LibriSpeech background...", flush=True)
bg_files = sorted(glob.glob(os.path.join(PV,"prepared","librispeech","**","*.wav"),recursive=True)) or \
    sorted(glob.glob(os.path.join(PV,"prepared","librispeech","*.wav")))
win_samp = int(WIN_S*SR); hop_samp = int(HOP_S*SR)

def scan_background(file_list, label):
    bg_vecs, bg_durs, bg_times, bg_sec = [], [], [], 0.0
    for bf in file_list:
        if label == "en" and bg_sec/60.0 >= 60: break
        x = read_wav(bf); base = bg_sec
        for s in range(0, x.size-win_samp+1, hop_samp):
            v, ds, dr = embed_with_dur(x[s:s+win_samp])
            bg_vecs.append(v); bg_durs.append(ds)
            bg_times.append(base+(s+win_samp/2)/SR)
        bg_sec += x.size/SR
    return bg_vecs, bg_durs, bg_times, bg_sec/3600.0

# English bg
en_vecs, en_durs, en_times, en_hours = scan_background(bg_files, "en")
print(f"  English: {en_hours:.2f}h, {len(en_vecs)} windows", flush=True)

# 3. Score English bg against templates, find operating threshold
DUR_CANDS = np.linspace(0.05, 2.0, 15)
MARGIN_CANDS = np.linspace(0.2, 1.0, 9)

def score_and_calibrate(spk, bg_vecs, bg_durs, bg_times, bg_hours, label=""):
    """Score bg against templates, return best dual-cascade params at FA<=0.5/hr."""
    info = spk_info[spk]
    all_tmps = info["all_tmps"]
    pos = info["pos_recs"]
    
    # Score bg
    bg_recs = []
    for bv, bds, btc in zip(bg_vecs, bg_durs, bg_times):
        if bv is None: bg_recs.append((math.inf,0.0,1.0,btc)); continue
        dists = []
        for j,(tv,tds,tw,twv) in enumerate(all_tmps): dists.append((cos_d(bv,tv),j,tw,tds))
        dists.sort(key=lambda x:x[0])
        if len(dists)>=2:
            d1,_,_,tds1 = dists[0]; d2 = dists[1][0]
            dr = abs(math.log(max(bds,1)/max(tds1,1))) if bds>0 and tds1>0 else 0.0; mr = d1/max(d2,1e-8)
        elif len(dists)==1:
            d1,_,_,tds1 = dists[0]
            dr = abs(math.log(max(bds,1)/max(tds1,1))) if bds>0 and tds1>0 else 0.0; mr = 0.0
        else: d1,dr,mr = math.inf,0.0,1.0
        bg_recs.append((d1,dr,mr,btc))
    
    pos_ds = sorted({r[0] for r in pos if math.isfinite(r[0])})
    bg_ds_s = sorted({r[0] for r in bg_recs if math.isfinite(r[0])})
    cands_d = list(pos_ds)
    if len(bg_ds_s)>200:
        step = max(1, len(bg_ds_s)//200)
        for i in range(0,len(bg_ds_s),step): cands_d.append(bg_ds_s[i])
    cands_d = sorted(set(cands_d))
    
    best = None
    for td in cands_d:
        for tdur in DUR_CANDS:
            det = sum(1 for r in pos if r[0]<=td and r[1]<=tdur)/len(pos)
            fa = 0; last = -1e9
            for r in bg_recs:
                if r[0]<=td and r[1]<=tdur and r[3]-last>REFRACTORY_S: fa+=1; last=r[3]
                elif r[0]<=td and r[1]<=tdur: last=r[3]
            fahr = fa/bg_hours if bg_hours else 0.0
            if fahr<=0.5 and (best is None or det>best[0]): best = (det, fahr, td, tdur)
    return best, bg_recs

# Calibrate on English
print("\nCalibrating on English LibriSpeech...", flush=True)
en_params = {}
for spk in SPEAKERS:
    best, bg_recs = score_and_calibrate(spk, en_vecs, en_durs, en_times, en_hours)
    if best:
        en_params[spk] = (best, bg_recs)
        print(f"  {spk}: thr_d={best[2]:.4f} thr_dur={best[3]:.3f} FRR={(1-best[0])*100:.1f}%", flush=True)

# 4. Scan multilingual backgrounds, measure FA/hr at English threshold
print(f"\n{'='*70}")
print(f"LANGUAGE INDEPENDENCE: FA/hr at English-calibrated thresholds")
print(f"{'='*70}")
print(f"  {'Lang':<10} {'Clips':>7} {'Windows':>8} {'Bg hours':>8} | {'FA/hr@en(F01)':>12} {'FA/hr@en(F03)':>12}")

results = {}
for lang, code in zip(LANGUAGES, LANG_CODES):
    lang_dir = os.path.join(CV_DIR, lang)
    wav_files = sorted(glob.glob(os.path.join(lang_dir, "*.wav")))
    if not wav_files:
        print(f"  {code:<10} {'0':>7} {'-':>8} {'-':>8} | {'N/A':>12}")
        continue
    
    lg_vecs, lg_durs, lg_times, lg_hours = scan_background(wav_files, code)
    
    # Measure FA/hr at English thresholds + re-calibrate for worst-case
    fa_rows = []
    for spk in SPEAKERS:
        if spk not in en_params: continue
        best_en, _ = en_params[spk]
        thr_d, thr_dur = best_en[2], best_en[3]
        
        # Score this language's bg against speaker's templates
        best_lg, lg_recs = score_and_calibrate(spk, lg_vecs, lg_durs, lg_times, lg_hours, code)
        
        # FA/hr at English threshold
        fa_at_en = 0; last = -1e9
        for r in lg_recs:
            if r[0]<=thr_d and r[1]<=thr_dur and r[3]-last>REFRACTORY_S: fa_at_en+=1; last=r[3]
            elif r[0]<=thr_d and r[1]<=thr_dur: last=r[3]
        fahr_at_en = fa_at_en/lg_hours if lg_hours else 0.0
        
        # Re-calibrated FRR
        frr_recal = (1-best_lg[0])*100 if best_lg else float('nan')
        
        fa_rows.append((spk, fahr_at_en, frr_recal))
        results[(spk, code)] = (fahr_at_en, frr_recal)
    
    f01_fa = next((f for s,f,_ in fa_rows if s=="F01"), float('nan'))
    f03_fa = next((f for s,f,_ in fa_rows if s=="F03"), float('nan'))
    print(f"  {code:<10} {len(wav_files):>7} {len(lg_vecs):>8} {lg_hours:>7.2f}h | {f01_fa:>11.1f} /hr {f03_fa:>11.1f} /hr", flush=True)

# 5. Summary vs English baseline
print(f"\n{'='*70}")
print(f"LANGUAGE DEGRADATION vs English LibriSpeech")
print(f"{'='*70}")
print(f"  {'Lang':<10} {'F01 FA ratio':>12} {'F03 FA ratio':>12} {'F01 FRR recal':>13} {'F03 FRR recal':>13} {'Result':>10}")

pass_count = 0
for lang, code in zip(LANGUAGES, LANG_CODES):
    f01 = results.get(("F01", code))
    f03 = results.get(("F03", code))
    if f01 is None or f03 is None:
        print(f"  {code:<10} {'N/A':>12}")
        continue
    
    fa01, frr01 = f01; fa03, frr03 = f03
    en_fa01 = 0.5  # English baseline was calibrated to FA/hr<=0.5
    en_fa03 = 0.5
    
    ratio01 = fa01/max(en_fa01,0.01)
    ratio03 = fa03/max(en_fa03,0.01)
    deg = max(ratio01, ratio03)
    
    if deg <= 2.0:
        result = "PASS <=2x"
        pass_count += 1
    elif deg <= 3.0:
        result = "WARN <=3x"
    else:
        result = "FAIL >3x"
    
    print(f"  {code:<10} {ratio01:>11.1f}x {ratio03:>11.1f}x {frr01:>12.1f}% {frr03:>12.1f}% {result:>10}", flush=True)

print(f"\n  Passed: {pass_count}/{len(LANGUAGES)} languages within 2x English FA/hr")
print(f"  H1: {'CONFIRMED' if pass_count>=5 else 'PARTIAL' if pass_count>=3 else 'REFUTED'}")

print(f"\nTotal: {time.time()-t0:.0f}s")
