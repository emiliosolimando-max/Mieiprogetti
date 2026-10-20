#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monta_facebook.py — montaggio automatico di video informativi per il FEED di Facebook (4:5, 1080x1350).

Uso (dalla cartella che contiene input/, immagini/, output/):
  python monta_facebook.py               1) trascrive  2) crea il piano  3) mostra la tabella e SI FERMA
  python monta_facebook.py --render      anteprima 30 s + video completo + controlli + copertina
  python monta_facebook.py --anteprima   solo l'anteprima veloce dei primi 30 s

Opzioni utili:
  --file input/x.mp4   --titolo "..."   --ticker "..."
  --ripianifica        rifà il piano (sovrascrive le correzioni fatte a mano su piano_montaggio.json)
  --ritrascrivi        rifà anche la trascrizione
  --base DIR           cartella di lavoro (predefinita: quella corrente)

Il piano (output/piano_montaggio.json) si può modificare a mano prima del render:
immagini (inizio, durata, file), numeri in evidenza, testo dei sottotitoli ("righe").
"""

# =====================================================================
#  PARAMETRI — per un nuovo video di solito basta cambiare questi
# =====================================================================
FILE_SORGENTE = None   # es. "input/pensioni.mp4"; None = primo video trovato in ./input/
TITOLO = "COME OTTENERE IL RICALCOLO DELLA PENSIONE"
TICKER = ("Come ottenere il ricalcolo della pensione • Chiedi anche tu il ricalcolo • "
          "Segui la pagina per restare aggiornato • Condividi con chi può interessare •")
COLORE_PRINCIPALE = "#0B3D91"      # fascia titolo / ticker
COLORE_EVIDENZIAZIONE = "#FFD400"  # parola pronunciata, numeri in evidenza
FONT_FAMIGLIA = "Montserrat"       # scaricato da Google Fonts se manca
PESO_TITOLO = 800                  # 800 = ExtraBold
PESO_SOTTOTITOLI = 600             # 600 = SemiBold
LINGUA = "it"
MODELLO_WHISPER = "large-v3"
# Alternativa se faster-whisper non riesce a scaricare il modello (es. HuggingFace bloccato):
# cartella di un modello Whisper di sherpa-onnx (github.com/k2-fsa/sherpa-onnx/releases, tag asr-models)
MOTORE_TRASCRIZIONE = "auto"        # "auto" | "faster-whisper" | "sherpa-onnx"
SHERPA_MODELLO = "modelli/sherpa-onnx-whisper-turbo"   # None se non c'è
INQUADRATURA = "auto"              # "auto" | "ritaglio" (crop sul volto) | "sfocato" (sfondo sfocato)

# Cartello finale (lasciare CHIUSURA_TITOLO = "" per non metterlo)
CHIUSURA_TITOLO = "RICALCOLO DELLE PENSIONI"
CHIUSURA_TESTO = "Chiedi anche tu il ricalcolo"
CHIUSURA_DURATA = 4.0     # secondi di cartello
CHIUSURA_CODA = 2.0       # secondi aggiunti in fondo (ultimo fotogramma fermo) per leggerlo con calma
# Se per un concetto non c'è né una foto tua né Pexels, crea una grafica (icona + parola chiave)
GRAFICHE_SE_MANCA_FOTO = True

# Correzioni aggiuntive per i sottotitoli: {"parola o frase minuscola": "Forma Corretta"}
CORREZIONI_EXTRA = {}
# Concetti visivi aggiuntivi: ("nome_concetto", ["parola", "radice.*", "frase di due parole"], "query pexels in inglese")
CONCETTI_EXTRA = []

# ----- avanzati -----
FPS = 30
BITRATE_VIDEO, MAXRATE, BUFSIZE = "9M", "10M", "18M"
PRESET_FINALE = "medium"
LUFS, TRUE_PEAK = -14.0, -1.0
DURATA_ANTEPRIMA = 30
SUB_FONT_PX = 56          # 52–58 px (altezza "em", come in un editor grafico)
SUB_FONT_PX_MIN = 52
SUB_MAX_CARATTERI = 32
TICKER_VELOCITA = 110     # px/s
IMG_INTERVALLO_MIN = 5.0  # secondi minimi tra l'inizio di due immagini (spec: 4–6)
IMG_ANTICIPO = 0.15
IMG_INIZIO_MIN = 1.5      # niente immagini mentre entra il titolo
IMG_DURATA_MIN, IMG_DURATA_MAX = 2.5, 4.0
NUM_DURATA = 2.0

# =====================================================================
#  GEOMETRIA (1080x1350) — non toccare se non cambi formato
# =====================================================================
W, H = 1080, 1350
SAFE = (54, 60, 1026, 1280)                 # x0, y0, x1, y1 (sinistra 54, sopra 60, destra 54, sotto 70)
TITOLO_BOX = (54, 60, 1026, 190)
CARD_W, CARD_H, CARD_CX, CARD_CY = 900, 560, 540, 510   # area y 230–790
CARD_BORDO, CARD_RAGGIO = 6, 24
SUB_ZONA = (960, 1180)
SUB_CY = 1070
TICKER_BOX = (54, 1200, 1026, 1270)

import argparse
import difflib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

BASE = Path.cwd()
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}


# =====================================================================
#  DIPENDENZE
# =====================================================================
def assicura_dipendenze():
    pacchetti = [("faster_whisper", "faster-whisper"), ("pysubs2", "pysubs2"), ("PIL", "Pillow"),
                 ("requests", "requests"), ("cv2", "opencv-python-headless<5"), ("numpy", "numpy"),
                 ("fontTools", "fonttools")]
    mancanti = [pkg for mod, pkg in pacchetti if importlib.util.find_spec(mod) is None]
    if mancanti:
        print(f"→ Installo i pacchetti Python mancanti: {', '.join(mancanti)}")
        cmd = [sys.executable, "-m", "pip", "install", "-q", *mancanti]
        if subprocess.call(cmd) != 0:
            subprocess.check_call(cmd + ["--break-system-packages"])
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("→ ffmpeg non trovato, provo a installarlo…")
        sistema = platform.system()
        if sistema == "Linux" and shutil.which("apt-get"):
            pre = [] if os.geteuid() == 0 else ["sudo"]
            subprocess.call(pre + ["apt-get", "update", "-qq"])
            subprocess.check_call(pre + ["apt-get", "install", "-y", "-qq", "ffmpeg"])
        elif sistema == "Darwin" and shutil.which("brew"):
            subprocess.check_call(["brew", "install", "ffmpeg"])
        elif sistema == "Windows" and shutil.which("winget"):
            subprocess.check_call(["winget", "install", "-e", "--id", "Gyan.FFmpeg"])
        else:
            sys.exit("ffmpeg mancante: installalo (con libass) e rilancia lo script.")
    filtri = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    for f in ("ass", "loudnorm"):
        if not re.search(rf"\s{f}\s", filtri):
            sys.exit(f"Il tuo ffmpeg non ha il filtro '{f}' (serve ffmpeg compilato con libass).")


# =====================================================================
#  UTILITÀ
# =====================================================================
def esegui(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"Comando fallito: {' '.join(map(str, cmd))}\n{r.stderr[-3000:]}")
    return r


def ffprobe(path):
    r = esegui(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(r.stdout)


def info_video(path):
    d = ffprobe(path)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {"w": w, "h": h, "durata": float(d["format"]["duration"]), "audio": a is not None}


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def ass_colore(c):
    r, g, b = hex_rgb(c)
    return f"&H{b:02X}{g:02X}{r:02X}&"


def senza_accenti(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def norm(s):
    """minuscolo, senza accenti/punteggiatura; dopo un apostrofo tiene la parte finale (dell'INPS → inps)."""
    s = senza_accenti(s.lower()).replace("’", "'")
    if "'" in s.strip("'"):
        s = s.strip("'").rsplit("'", 1)[-1]
    return re.sub(r"[^\w%€]+", "", s)


def clamp(x, a, b):
    return max(a, min(b, x))


def ease_out_cubic(p):
    p = clamp(p, 0, 1)
    return 1 - (1 - p) ** 3


def ease_out_back(p, s=1.70158):
    p = clamp(p, 0, 1) - 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def fmt_t(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def r3(x):
    return round(float(x), 3)


# =====================================================================
#  FONT
# =====================================================================
NOMI_PESO = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
             600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def _scarica_font_google(dest_dir, peso):
    import requests
    fam_dir = FONT_FAMIGLIA.lower().replace(" ", "")
    fam_file = FONT_FAMIGLIA.replace(" ", "")
    candidati = []
    for lic in ("ofl", "apache", "ufl"):
        root = f"https://raw.githubusercontent.com/google/fonts/main/{lic}/{fam_dir}"
        candidati += [(f"{root}/{fam_file}%5Bwght%5D.ttf", True),
                      (f"{root}/static/{fam_file}-{NOMI_PESO[peso]}.ttf", False),
                      (f"{root}/{fam_file}-{NOMI_PESO[peso]}.ttf", False)]
    for url, variabile in candidati:
        try:
            r = requests.get(url, timeout=60)
        except Exception:
            continue
        if r.status_code == 200 and len(r.content) > 10000:
            p = dest_dir / ("_vf_" + fam_file + ".ttf" if variabile else f"_st_{fam_file}-{peso}.ttf")
            p.write_bytes(r.content)
            return p
    return None


def _font_di_sistema(peso):
    if not shutil.which("fc-list"):
        return None
    out = subprocess.run(["fc-list", f":family={FONT_FAMIGLIA}", "file", "style", "weight"],
                         capture_output=True, text=True).stdout
    for riga in out.splitlines():
        if NOMI_PESO[peso].lower() in riga.lower().replace(" ", "") and "italic" not in riga.lower():
            return Path(riga.split(":")[0])
    return None


def _istanzia(src, peso, famiglia, dest):
    from fontTools.ttLib import TTFont
    f = TTFont(str(src))
    if "fvar" in f:
        from fontTools.varLib import instancer
        assi = {a.axisTag: (peso if a.axisTag == "wght" else a.defaultValue) for a in f["fvar"].axes}
        f = instancer.instantiateVariableFont(f, assi)
    name = f["name"]
    name.names = [n for n in name.names if n.nameID not in (1, 2, 3, 4, 6, 16, 17, 21, 22)]
    ps = famiglia.replace(" ", "-")
    for pid, eid, lid in ((3, 1, 0x409), (1, 0, 0)):
        name.setName(famiglia, 1, pid, eid, lid)
        name.setName("Regular", 2, pid, eid, lid)
        name.setName(famiglia + " Regular", 3, pid, eid, lid)
        name.setName(famiglia, 4, pid, eid, lid)
        name.setName(ps, 6, pid, eid, lid)
    f["OS/2"].usWeightClass = peso
    f["OS/2"].fsSelection = (f["OS/2"].fsSelection & ~0b100001) | 0b1000000
    f["head"].macStyle = 0
    f.save(str(dest))


def prepara_font():
    d = BASE / "fonts"
    d.mkdir(exist_ok=True)
    out = {}
    for ruolo, peso in (("titolo", PESO_TITOLO), ("sottotitoli", PESO_SOTTOTITOLI)):
        famiglia = f"{FONT_FAMIGLIA} {NOMI_PESO[peso]}"
        dest = d / f"{FONT_FAMIGLIA.replace(' ', '')}-{NOMI_PESO[peso]}.ttf"
        if not dest.exists():
            src = _font_di_sistema(peso) or next(iter(sorted(d.glob("_vf_*.ttf"))), None) \
                or _scarica_font_google(d, peso)
            if src is None:
                sys.exit(f"Non trovo il font {famiglia}: mettine il file .ttf in ./fonts/ e rilancia.")
            print(f"→ Preparo il font {famiglia}")
            _istanzia(src, peso, famiglia, dest)
        from fontTools.ttLib import TTFont
        tt = TTFont(str(dest))
        os2 = tt["OS/2"]
        # libass dimensiona il font sull'altezza (winAscent+winDescent): serve per avere "px veri"
        rapporto_ass = (os2.usWinAscent + os2.usWinDescent) / tt["head"].unitsPerEm
        out[ruolo] = {"path": str(dest), "famiglia": famiglia, "rapporto_ass": rapporto_ass}
    return out


# =====================================================================
#  1) TRASCRIZIONE
# =====================================================================
def trascrivi(src, durata):
    out_json = BASE / "output" / "trascrizione.json"
    wav = BASE / "output" / "_audio_16k.wav"
    print("→ Estraggo l'audio per la trascrizione")
    esegui(["ffmpeg", "-y", "-i", str(src), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    dati = None
    if MOTORE_TRASCRIZIONE in ("auto", "faster-whisper"):
        try:
            dati = _trascrivi_faster_whisper(wav, durata)
        except Exception as e:
            if MOTORE_TRASCRIZIONE == "faster-whisper" or not SHERPA_MODELLO:
                raise
            print(f"   ! faster-whisper non disponibile ({str(e)[:120]}): uso sherpa-onnx")
    if dati is None:
        dati = _trascrivi_sherpa(wav, durata)
    out_json.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    import pysubs2
    srt = pysubs2.SSAFile()
    for s in dati["segmenti"]:
        srt.append(pysubs2.SSAEvent(start=int(s["inizio"] * 1000), end=int(s["fine"] * 1000), text=s["testo"]))
    srt.save(str(BASE / "output" / "trascrizione.srt"))
    wav.unlink(missing_ok=True)
    return dati


def _trascrivi_faster_whisper(wav, durata):
    from faster_whisper import WhisperModel
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda = False
    print(f"→ Trascrivo con faster-whisper {MODELLO_WHISPER} su {'GPU' if cuda else 'CPU'} "
          f"(la prima volta scarica il modello, ~3 GB)…")
    model = WhisperModel(MODELLO_WHISPER, device="cuda" if cuda else "cpu",
                         compute_type="float16" if cuda else "int8")
    prompt = "Notizie: " + ", ".join(sorted({v for v in {**CORREZIONI, **CORREZIONI_EXTRA}.values()
                                               if any(c.isupper() for c in v)})[:40]) + "."
    segmenti, info = model.transcribe(str(wav), language=LINGUA, word_timestamps=True, vad_filter=True,
                                      beam_size=5, initial_prompt=prompt)
    dati = {"lingua": info.language, "modello": MODELLO_WHISPER, "durata": durata, "segmenti": []}
    for s in segmenti:
        parole = [{"w": p.word.strip(), "start": r3(p.start), "end": r3(p.end), "prob": r3(p.probability)}
                  for p in (s.words or []) if p.word.strip()]
        dati["segmenti"].append({"inizio": r3(s.start), "fine": r3(s.end), "testo": s.text.strip(),
                                 "parole": parole})
        print(f"   [{fmt_t(s.start)}] {s.text.strip()}")
    return dati


def _sillabe(w):
    return max(1, len(re.findall(r"[aeiouàèéìòóù]+", w.lower()))) + (0.5 if re.search(r"\d", w) else 0)


def _voce(a, sr=16000):
    """Maschera voce/silenzio a 10 ms e livello in dB."""
    import numpy as np
    hop = sr // 100
    n = len(a) // hop
    rms = np.sqrt(np.mean(a[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    soglia = max(np.percentile(db, 15) + 8, np.percentile(db, 95) - 30)
    voce = np.convolve(db > soglia, np.ones(5) / 5, mode="same") > 0.3
    return voce, db


def _corse(voce, i0, i1, pausa_min=22):
    """Tratti continui di voce fra i0 e i1 separati da pause ≥ pausa_min (×10 ms)."""
    corse, k = [], i0
    while k < i1:
        while k < i1 and not voce[k]:
            k += 1
        if k >= i1:
            break
        a_, sil = k, 0
        while k < i1 and sil < pausa_min:
            sil = sil + 1 if not voce[k] else 0
            k += 1
        corse.append((a_, k - sil))
    return corse


def _pezzi_lunghi(voce, db, max_len=2400):
    """Pezzi fino a ~24 s tagliati nelle pause più lunghe (Whisper lavora meglio con contesto)."""
    import numpy as np
    n = len(voce)
    pezzi, inizio = [], 0
    while inizio < n:
        while inizio < n and not voce[inizio]:
            inizio += 1
        if inizio >= n:
            break
        if n - inizio <= max_len:
            pezzi.append((inizio, n))
            break
        fin = inizio + max_len
        # taglio al centro della pausa più lunga nella seconda metà della finestra
        migliore, k, best_len = None, inizio + max_len // 2, 0
        while k < fin:
            if not voce[k]:
                j = k
                while j < fin and not voce[j]:
                    j += 1
                if j - k > best_len:
                    best_len, migliore = j - k, (k + j) // 2
                k = j
            k += 1
        if migliore is None:
            migliore = inizio + max_len // 2 + int(np.argmin(db[inizio + max_len // 2:fin]))
        pezzi.append((inizio, migliore))
        inizio = migliore
    return pezzi


def _allinea(parole, corse):
    """Assegna le parole ai tratti di voce: i confini fra tratti cadono dove la quota di sillabe pronunciate
    corrisponde alla quota di tempo parlato, preferendo la punteggiatura. Poi distribuisce dentro ogni tratto."""
    pesi = [_sillabe(p) + 0.4 for p in parole]
    n, k = len(parole), len(corse)
    cumw = [0.0]
    for p in pesi:
        cumw.append(cumw[-1] + p)
    durate = [b - a for a, b in corse]
    tot_t = sum(durate)
    cumt, acc = [], 0
    for d_ in durate[:-1]:
        acc += d_
        cumt.append(acc / tot_t)
    inf = float("inf")
    # dp[j][i]: costo migliore mettendo il confine j dopo la parola i
    dp = [[inf] * (n + 1) for _ in range(k)]
    da = [[0] * (n + 1) for _ in range(k)]
    dp[0][0] = 0.0
    for j in range(1, k):
        for i in range(n + 1):
            c = abs(cumw[i] / cumw[-1] - cumt[j - 1])
            if 0 < i < n and re.search(r"[.,;:!?…]$", parole[i - 1]):
                c -= 0.03
            best = min(range(i + 1), key=lambda q: dp[j - 1][q])
            dp[j][i], da[j][i] = dp[j - 1][best] + c, best
    fine = min(range(n + 1), key=lambda i: dp[k - 1][i] if k > 1 else (0 if i == 0 else inf))
    confini = [n]
    i = fine
    for j in range(k - 1, 0, -1):
        confini.append(i)
        i = da[j][i]
    confini = sorted(confini) if k > 1 else [n]
    out, prima = [], 0
    for (a_, b_), c in zip(corse, confini):
        gruppo = list(range(prima, c))
        prima = c
        if not gruppo:
            continue
        tw = sum(pesi[g] for g in gruppo)
        t, durata = a_, b_ - a_
        for g in gruppo:
            dt = durata * pesi[g] / tw
            out.append({"w": parole[g], "start": r3(t / 100), "end": r3((t + dt) / 100), "prob": None})
            t += dt
    return out


def _trascrivi_sherpa(wav, durata):
    """Whisper via sherpa-onnx (onnxruntime). Non dà i tempi delle parole: trascrivo tratti brevi tagliati
    nelle pause e distribuisco le parole sul parlato del tratto in proporzione alle sillabe."""
    import wave
    import numpy as np
    import sherpa_onnx
    d = Path(SHERPA_MODELLO)
    d = d if d.is_absolute() else BASE / d
    enc = sorted(d.glob("*encoder.int8.onnx")) or sorted(d.glob("*encoder.onnx"))
    dec = sorted(d.glob("*decoder.int8.onnx")) or sorted(d.glob("*decoder.onnx"))
    tok = sorted(d.glob("*tokens.txt"))
    print(f"→ Trascrivo con sherpa-onnx ({d.name})")
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=str(enc[0]), decoder=str(dec[0]), tokens=str(tok[0]),
                                                     language=LINGUA, task="transcribe",
                                                     num_threads=os.cpu_count() or 4,
                                                     enable_segment_timestamps=True)
    with wave.open(str(wav)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    voce, db = _voce(a)
    dati = {"lingua": LINGUA, "modello": f"sherpa-onnx {d.name}", "durata": durata, "segmenti": [],
            "nota": "tempi: frasi dai timestamp di Whisper, parole stimate sui tratti di voce (sillabe)"}

    def frasi(i0, i1, livello=0):
        """Frasi con i loro tempi (timestamp di segmento di Whisper); le frasi lunghe vengono ridecodificate."""
        m0 = max(0, i0 - 20)
        st = rec.create_stream()
        st.accept_waveform(16000, a[m0 * 160:min(len(a), (i1 + 20) * 160)])
        rec.decode_stream(st)
        r = st.result
        if not r.segment_texts:
            return [(i0, i1, r.text)]
        out = []
        for t, du, tx in zip(r.segment_timestamps, r.segment_durations, r.segment_texts):
            f0 = max(i0, int(round(m0 + t * 100)))
            f1 = min(i1, int(round(m0 + (t + du) * 100)))
            if f1 - f0 > 550 and livello < 2:
                sotto = frasi(f0, f1, livello + 1)
                if len(sotto) > 1:
                    out += sotto
                    continue
            out.append((f0, f1, tx))
        return out

    def decodifica(i0, i1):
        st = rec.create_stream()
        st.accept_waveform(16000, a[max(0, i0 - 10) * 160:min(len(a), (i1 + 10) * 160)])
        rec.decode_stream(st)
        return st.result.text

    def lettere(t):
        return re.sub(r"[^a-z]", "", senza_accenti(t.lower()))

    def ancora(parole, corse):
        """Assegna ogni parola al tratto di voce in cui il riconoscimento del solo tratto ritrova le sue lettere."""
        unite = []                                     # tratti troppo brevi uniti al vicino
        for c in corse:
            if unite and (c[1] - c[0] < 35 or unite[-1][1] - unite[-1][0] < 35):
                unite[-1] = (unite[-1][0], c[1])
            else:
                unite.append(c)
        if len(unite) < 2:
            return None, unite
        lb, chi = "", []
        for k, (c0, c1) in enumerate(unite):
            t = lettere(decodifica(c0, c1))
            lb += t
            chi += [k] * len(t)
        la, di = "", []
        for i, w in enumerate(parole):
            t = lettere(w)
            la += t
            di += [i] * len(t)
        sm = difflib.SequenceMatcher(None, la, lb, autojunk=False)
        voti = [dict() for _ in parole]
        trovate = 0
        for blk in sm.get_matching_blocks():
            for t in range(blk.size):
                v = voti[di[blk.a + t]]
                k = chi[blk.b + t]
                v[k] = v.get(k, 0) + 1
                trovate += 1
        if not la or trovate < 0.35 * len(la):
            return None, unite
        ass = [max(v, key=v.get) if v else None for v in voti]
        noti = [i for i, x in enumerate(ass) if x is not None]
        for i in range(len(ass)):
            if ass[i] is None:
                prima = max((j for j in noti if j < i), default=None)
                dopo = min((j for j in noti if j > i), default=None)
                ass[i] = ass[prima] if prima is not None else ass[dopo]
        for i in range(1, len(ass)):                   # monotonia, togliendo i salti all'indietro
            ass[i] = max(ass[i], ass[i - 1])
        return ass, unite

    out = []
    for i0, i1 in _pezzi_lunghi(voce, db):
        for f0, f1, tx in frasi(i0, i1):
            parole = re.sub(r"\[[^\]]*\]?", "", tx).split()
            if not parole:
                continue
            corse = _corse(voce, f0, f1, pausa_min=18) or [(f0, f1)]
            ass, unite = ancora(parole, corse)
            if ass is None:
                gruppo = _allinea(parole, _corse(voce, f0, f1) or [(f0, f1)])
            else:
                gruppo = []
                for k, c in enumerate(unite):
                    sel = [w for w, x in zip(parole, ass) if x == k]
                    if sel:
                        gruppo += _allinea(sel, [c])
            out += gruppo
            dati["segmenti"].append({"inizio": gruppo[0]["start"], "fine": gruppo[-1]["end"],
                                     "testo": " ".join(parole), "parole": gruppo})
            print(f"   [{fmt_t(f0 / 100)}–{fmt_t(f1 / 100)}] {' '.join(parole)}"
                  f"{'' if ass is not None else '  (tempi stimati per sillabe)'}")
    return dati


# =====================================================================
#  NORMALIZZAZIONE TESTO (numeri, nomi propri, maiuscole)
# =====================================================================
CORREZIONI = {
    "inps": "INPS", "inail": "INAIL", "isee": "ISEE", "naspi": "NASpI", "imu": "IMU", "irpef": "IRPEF",
    "iva": "IVA", "tfr": "TFR", "pil": "PIL", "istat": "ISTAT", "bce": "BCE", "ue": "UE", "asl": "ASL",
    "spid": "SPID", "pec": "PEC", "caf": "CAF", "tari": "TARI", "rai": "RAI", "covid": "Covid",
    "inpdap": "INPDAP", "ims": "INPS", "imsi": "INPS", "imps": "INPS", "imsdap": "INPDAP", "impdap": "INPDAP",
    "quescenza": "quiescenza", "quiescienza": "quiescenza",
    "carabinieri": "Carabinieri", "carabiniere": "Carabiniere", "ministero": "Ministero",
    "parlamento": "Parlamento", "senato": "Senato", "inps.it": "INPS.it",
    "agenzia delle entrate": "Agenzia delle Entrate", "guardia di finanza": "Guardia di Finanza",
    "polizia di stato": "Polizia di Stato", "polizia locale": "Polizia Locale",
    "unione europea": "Unione Europea", "camera dei deputati": "Camera dei Deputati",
    "legge di bilancio": "Legge di Bilancio", "assegno unico": "Assegno Unico",
    "opzione donna": "Opzione Donna", "ape sociale": "Ape Sociale", "quota cento": "Quota 100",
    "presidente della repubblica": "Presidente della Repubblica",
    "consiglio dei ministri": "Consiglio dei Ministri", "vigili del fuoco": "Vigili del Fuoco",
    "protezione civile": "Protezione Civile", "poste italiane": "Poste Italiane",
    "servizio sanitario nazionale": "Servizio Sanitario Nazionale",
}

_UNITA = {"zero": 0, "uno": 1, "un": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
          "sette": 7, "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13,
          "quattordici": 14, "quindici": 15, "sedici": 16, "diciassette": 17, "diciotto": 18,
          "diciannove": 19}
_DECINE = {"venti": 20, "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60, "settanta": 70,
           "ottanta": 80, "novanta": 90}


def _n99(s):
    if s in _UNITA:
        return _UNITA[s]
    for parola, val in _DECINE.items():
        if s == parola:
            return val
        for base in (parola, parola[:-1]):          # ventuno / ventotto (elisione)
            resto = s[len(base):] if s.startswith(base) else None
            if resto and resto in _UNITA and 1 <= _UNITA[resto] <= 9 and resto not in ("un", "una"):
                return val + _UNITA[resto]
    return None


def _n999(s):
    if s == "":
        return 0
    for pref, mult in [("", 1)] + [(k, v) for k, v in _UNITA.items() if 2 <= v <= 9]:
        for c in ("cento", "cent"):
            if s.startswith(pref + c):
                r = _n99(s[len(pref + c):]) if s[len(pref + c):] else 0
                if r is not None:
                    return mult * 100 + r
    return _n99(s)


def numero_italiano(s):
    """'sessantasette' → 67, 'duemilaventisette' → 2027, 'milleduecento' → 1200; altrimenti None."""
    s = senza_accenti(s.lower())
    if not s.isalpha():
        return None
    if s.startswith("mille"):
        r = _n999(s[5:])
        return 1000 + r if r is not None else None
    i = s.find("mila")
    if i > 0:
        k, r = _n999(s[:i]), _n999(s[i + 4:])
        return k * 1000 + r if k and r is not None else None
    return _n999(s)


def formatta_intero(n, anno_ok=True):
    if anno_ok and 1900 <= n <= 2100:
        return str(n)
    return f"{n:,}".replace(",", ".")


_RE_TOKEN = re.compile(r"^([\"«“‘(\[¿¡]*)(.*?)([\"»”’)\].,;:!?…]*)$", re.S)
UNITA_EURO = ("euro", "€")


def _split(w):
    m = _RE_TOKEN.match(w)
    return m.group(1), m.group(2), m.group(3)


def normalizza_parole(parole):
    """Corregge numeri, nomi propri e maiuscole mantenendo i tempi parola per parola."""
    toks = []
    for p in parole:
        w = p["w"].strip()
        if w:
            pre, core, post = _split(w)
            toks.append({"pre": pre, "core": core, "post": post, "start": p["start"], "end": p["end"]})

    def low(i):
        return norm(toks[i]["core"]) if 0 <= i < len(toks) else ""

    # --- numeri ---
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        c = t["core"]
        n_parola = numero_italiano(c) if c.isalpha() else None
        m_cifre = re.fullmatch(r"(\d+)(?:[.,](\d{1,2}))?(%?)", c.replace(".", "") if re.fullmatch(
            r"\d{1,3}(\.\d{3})+", c) else c)
        if n_parola is None and not m_cifre:
            out.append(t)
            i += 1
            continue
        if m_cifre:
            intero, dec, perc = int(m_cifre.group(1)), m_cifre.group(2), m_cifre.group(3) == "%"
        else:
            intero, dec, perc = n_parola, None, False
        j = i + 1
        if dec is None and not t["post"] and low(j) == "virgola" and j + 1 < len(toks):
            d = toks[j + 1]["core"]
            nd = d if d.isdigit() else (str(numero_italiano(d)) if numero_italiano(d) is not None else None)
            if nd is not None:
                dec, j = nd, j + 2
        if not perc and not toks[j - 1]["post"]:
            if low(j) in ("percento", "%"):
                perc, j = True, j + 1
            elif low(j) == "per" and low(j + 1) == "cento":
                perc, j = True, j + 2
        euro_dopo = low(j) in UNITA_EURO
        if n_parola is not None and c.lower() in ("un", "una", "uno") and dec is None and not perc:
            out.append(t)
            i += 1
            continue
        if n_parola is not None and intero < 10 and dec is None and not perc and not euro_dopo:
            out.append(t)       # "tre anni" resta in lettere, come nei testi giornalistici
            i += 1
            continue
        testo = formatta_intero(intero, anno_ok=not euro_dopo and dec is None)
        if dec is not None:
            testo += "," + dec
        if perc:
            testo += "%"
        out.append({"pre": t["pre"], "core": testo, "post": toks[j - 1]["post"],
                    "start": t["start"], "end": toks[j - 1]["end"]})
        i = j
    toks = out

    # --- correzioni (frasi prima, poi parole singole) ---
    corr = {**CORREZIONI, **{k.lower(): v for k, v in CORREZIONI_EXTRA.items()}}
    frasi = sorted([k for k in corr if " " in k], key=lambda k: -len(k.split()))
    for frase in frasi:
        pf = frase.split()
        nuove = corr[frase].split()
        if len(nuove) != len(pf):
            continue
        for i in range(len(toks) - len(pf) + 1):
            if all(norm(toks[i + k]["core"]) == senza_accenti(pf[k]) for k in range(len(pf))):
                for k in range(len(pf)):
                    core = toks[i + k]["core"]
                    prefisso = core[:core.rfind("'") + 1] if k == 0 and "'" in core else ""
                    toks[i + k]["core"] = prefisso + nuove[k]
    singole = {k: v for k, v in corr.items() if " " not in k}
    for t in toks:
        for k, v in singole.items():
            if k in t["core"].lower():
                t["core"] = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", v, t["core"], flags=re.I)

    # --- maiuscola a inizio frase ---
    inizio = True
    for t in toks:
        c = t["core"]
        if inizio and c and c[0].isalpha() and c[0].islower():
            t["core"] = c[0].upper() + c[1:]
        inizio = bool(re.search(r"[.!?…]$", t["post"]))

    return [{"w": t["pre"] + t["core"] + t["post"], "start": r3(t["start"]), "end": r3(t["end"])}
            for t in toks if (t["pre"] + t["core"] + t["post"]).strip()]


# =====================================================================
#  SOTTOTITOLI: blocchi
# =====================================================================
class Misuratore:
    def __init__(self, font_path, px):
        from PIL import ImageFont
        self.px = px
        self.f = ImageFont.truetype(font_path, px)

    def w(self, s):
        return self.f.getlength(s)


def larghezza_max_sub():
    return (SAFE[2] - SAFE[0]) - 2 * 4 - 2 * 12      # area utile − contorno − respiro


PAROLE_DEBOLI = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con", "su", "per",
                 "tra", "fra", "e", "o", "ma", "che", "del", "dello", "della", "dei", "degli", "delle", "al", "allo",
                 "alla", "ai", "agli", "alle", "dal", "dalla", "dai", "dalle", "nel", "nello", "nella", "nei",
                 "negli", "nelle", "sul", "sulla", "sui", "sulle", "non", "si", "ci", "mi", "ti", "vi", "se",
                 "come", "quando", "anche", "piu", "l", "d", "dell", "all", "nell", "sull", "un'"}


def _debole(w):
    return norm(w) in PAROLE_DEBOLI or w.endswith("'")


def disponi_righe(testi, mis):
    """Restituisce (righe, indice_a_capo) con ≤2 righe, ≤N caratteri e larghezza in pixel valida; None se non ci sta."""
    max_w, max_c = larghezza_max_sub(), SUB_MAX_CARATTERI
    tutto = " ".join(testi)
    if len(tutto) <= max_c and mis.w(tutto) <= max_w:
        return [tutto], len(testi)
    migliore = None
    for k in range(1, len(testi)):
        a, b = " ".join(testi[:k]), " ".join(testi[k:])
        if len(a) <= max_c and len(b) <= max_c and mis.w(a) <= max_w and mis.w(b) <= max_w:
            punteggio = max(mis.w(a), mis.w(b)) - (90 if re.search(r"[,;:.!?]$", a) else 0) \
                + (120 if _debole(testi[k - 1]) else 0) + (25 if mis.w(a) > mis.w(b) * 1.6 else 0)
            if migliore is None or punteggio < migliore[0]:
                migliore = (punteggio, [a, b], k)
    return (migliore[1], migliore[2]) if migliore else None


def _frasi(parole):
    """Divide le parole in frasi (punto/punto interrogativo… o pausa lunga)."""
    frasi, cur = [], []
    for i, p in enumerate(parole):
        cur.append(p)
        succ = parole[i + 1] if i + 1 < len(parole) else None
        if succ is None or re.search(r"[.!?…][\"»”)]*$", p["w"]) or succ["start"] - p["end"] >= 0.6:
            frasi.append(cur)
            cur = []
    return frasi


def _spezza_frase(frase, mis):
    """Programmazione dinamica: divide una frase in blocchi validi (≤2 righe, ≤3 s) il più possibile
    equilibrati, spezzando preferibilmente dopo la punteggiatura e mai dopo articoli/preposizioni."""
    n = len(frase)
    costo = [0.0] + [math.inf] * n
    da = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            dur = frase[j - 1]["end"] - frase[i]["start"]
            if dur > 3.0 and j - i > 1:
                break
            d = disponi_righe([p["w"] for p in frase[i:j]], mis)
            if d is None:
                if j - i > 1:
                    break
                d = ([frase[i]["w"]], 1)
            caratteri = len(" ".join(p["w"] for p in frase[i:j]))
            c = 4.0 + 6.0 * (1 - min(1.0, caratteri / (1.6 * SUB_MAX_CARATTERI))) ** 2
            if dur < 1.0:
                c += 8.0 * (1.0 - dur)
            if j < n:
                c += 0.0 if re.search(r"[,;:]$", frase[j - 1]["w"]) else 2.0
                c += 6.0 if _debole(frase[j - 1]["w"]) else 0.0
            if costo[i] + c < costo[j]:
                costo[j], da[j] = costo[i] + c, i
    tagli, j = [], n
    while j > 0:
        tagli.append((da[j], j))
        j = da[j]
    return [frase[i:j] for i, j in reversed(tagli)]


def _blocco(parole, mis):
    d = disponi_righe([p["w"] for p in parole], mis) or ([" ".join(p["w"] for p in parole)], len(parole))
    return {"inizio": parole[0]["start"], "fine": parole[-1]["end"], "righe": d[0], "a_capo": d[1],
            "parole": list(parole)}


def crea_blocchi(parole, mis, durata_video):
    blocchi = [_blocco(pz, mis) for fr in _frasi(parole) for pz in _spezza_frase(fr, mis)]
    # unisci blocchi troppo corti (<1 s) col vicino, se ci stanno
    i = 0
    while i < len(blocchi):
        b = blocchi[i]
        if b["fine"] - b["inizio"] < 1.0:
            for k in (i + 1, i - 1):
                if 0 <= k < len(blocchi):
                    a, c = sorted((i, k))
                    unite = blocchi[a]["parole"] + blocchi[c]["parole"]
                    if unite[-1]["end"] - unite[0]["start"] <= 3.0 and disponi_righe([p["w"] for p in unite], mis):
                        blocchi[a] = _blocco(unite, mis)
                        del blocchi[c]
                        i = max(0, a - 1)
                        break
            else:
                i += 1
            continue
        i += 1
    # tempi: minimo 1 s, massimo 3 s, niente "buchi" brevi che fanno sfarfallare
    for i, b in enumerate(blocchi):
        prossimo = blocchi[i + 1]["inizio"] if i + 1 < len(blocchi) else durata_video
        if b["fine"] - b["inizio"] < 1.0:
            b["fine"] = min(b["inizio"] + 1.0, prossimo)
        if prossimo - b["fine"] < 0.35:
            b["fine"] = min(prossimo, b["inizio"] + 3.0)
        b["fine"] = max(b["fine"], min(b["parole"][-1]["end"], prossimo))
        b["inizio"], b["fine"] = r3(b["inizio"]), r3(b["fine"])
    return blocchi


# =====================================================================
#  CONCETTI VISIVI
# =====================================================================
# (concetto, inneschi (regex su parola normalizzata; spazio = parole consecutive), query Pexels)
CONCETTI = [
    ("ricalcolo", ["ricalcol\\w*"], "calculator pension documents"),
    ("contributi", ["contribut\\w*", "estratto conto", "versament\\w*"], "documents paperwork desk"),
    ("arretrati", ["arretrat\\w*", "rimbors\\w*"], "euro money banknotes"),
    ("domanda", ["domand[ae]", "richiest[ae]", "istanz[ae]", "ricors[oi]"], "filling application form"),
    ("patronato", ["patronat[oi]", "caf", "consulent[ei]", "avvocat[oi]", "espert[oi]"], "consultant office meeting"),
    ("verifica", ["verific\\w*", "controll\\w*"], "checking documents magnifying glass"),
    ("errori", ["error[ei]", "sbagliat\\w*", "anomali[ae]"], "mistake warning documents"),
    ("scadenza", ["scadenz[ae]", "prescrizion\\w*", "termin[ie] di legge"], "calendar deadline"),
    ("assegno", ["assegn[oi] pensionistic\\w*", "importo", "import[io] della pension\\w*"], "pension money euro"),
    ("busta_paga", ["bust[ae] pag[ah]e?", "stipend\\w*", "salar\\w*", "cedolin\\w*"], "payslip salary money"),
    ("agenzia_entrate", ["agenzia delle entrate", "fisco", "fiscal\\w*", "tass[ae]", "impost[ae]", "irpef",
                         "dichiarazione dei redditi", "730", "cartell[ae] esattorial[ei]"], "tax documents calculator"),
    ("inps", ["inps"], "government office counter queue"),
    ("pensionati", ["pensionat[aeio]", "pensioni", "anzian[io]", "terza eta"], "elderly couple park bench"),
    ("assegno_unico", ["assegno unico", "bonus", "isee"], "family budget euro money"),
    ("carabinieri", ["carabinier[ei]"], "italian police patrol car"),
    ("polizia", ["polizia", "poliziott\\w*", "forze dell'?ordine", "questur\\w*", "arrest\\w*"],
     "police officers patrol"),
    ("guardia_di_finanza", ["guardia di finanza", "evasion\\w*", "evasor\\w*"], "tax police inspection"),
    ("ospedale", ["ospedal\\w*", "pronto soccorso", "sanita", "sanitar\\w*", "ricover\\w*"],
     "hospital corridor doctors"),
    ("medico", ["medic[oi]", "dottor\\w*", "visit[ae] medic\\w*", "pazient\\w*"], "doctor talking patient"),
    ("farmacia", ["farmaci[ae]?", "medicin\\w*", "ricett[ae]"], "pharmacy medicine shelves"),
    ("scuola", ["scuol\\w*", "student\\w*", "alunn\\w*", "insegnant\\w*", "docent\\w*", "class[ei]"],
     "classroom students teacher"),
    ("universita", ["universit\\w*", "ateneo", "laure\\w*"], "university students lecture hall"),
    ("bollette", ["bollett\\w*", "luce", "elettric\\w*", "energi\\w*", "gas"], "electricity bill energy meter"),
    ("carburante", ["benzin\\w*", "carburant\\w*", "gasolio", "diesel", "distributor\\w*"], "gas station fuel pump"),
    ("mutuo", ["mutu[oi]", "affitt\\w*", "immobil\\w*", "propriet\\w* immobiliar\\w*"], "house keys mortgage"),
    ("banca", ["banc[ah]e?", "bancari\\w*", "conto corrente", "bancomat", "prestit\\w*"], "bank building atm"),
    ("lavoro", ["lavorator\\w*", "dipendent\\w*", "occupazion\\w*", "assunzion\\w*", "aziend\\w*"],
     "workers office team"),
    ("disoccupazione", ["disoccupa\\w*", "naspi", "licenzia\\w*", "cassa integrazione"], "job search unemployed"),
    ("governo", ["govern\\w*", "parlament\\w*", "senato", "camera dei deputati", "decret\\w*"],
     "italian parliament rome"),
    ("ministero", ["minister\\w*", "ministr[oi]", "ministra"], "government building rome"),
    ("legge", ["legg[ie]", "manovra", "norm[ae]", "riform\\w*", "gazzetta ufficiale"], "law documents signing"),
    ("famiglia", ["famigli\\w*", "figli", "bambin\\w*", "genitor\\w*", "maternit\\w*"], "family with children"),
    ("auto", ["automobil\\w*", "patent\\w*", "automobilist\\w*", "bollo auto", "autostrad\\w*"],
     "car driving road"),
    ("treno", ["tren[oi]", "ferrovi\\w*", "trasport\\w*", "pendolar\\w*"], "train station platform"),
    ("aereo", ["aere[oi]", "vol[oi]", "aeroport\\w*"], "airport airplane"),
    ("multa", ["mult[ae]", "sanzion\\w*", "contravvenzion\\w*"], "parking ticket fine"),
    ("tribunale", ["tribunal\\w*", "giudic[ei]", "sentenz\\w*", "process[oi]", "cassazione"],
     "courtroom judge gavel"),
    ("soldi", ["sold[oi]", "denaro", "risparmi\\w*", "contanti"], "euro banknotes money"),
    ("spesa", ["supermercat\\w*", "carrello", "prezz[oi]", "spesa alimentare"], "supermarket shopping cart"),
    ("inflazione", ["inflazion\\w*", "rincar\\w*", "caro vita", "carovita"], "inflation rising prices"),
    ("europa", ["europ\\w*", "bruxelles", "ue"], "european union flags"),
    ("maltempo", ["maltempo", "pioggi\\w*", "temporal\\w*", "alluvion\\w*", "allerta meteo"], "rain storm city"),
    ("caldo", ["caldo", "afa", "ondata di calore", "temperatur\\w*"], "heatwave sun city"),
    ("neve", ["neve", "nevicat\\w*", "gelo"], "snow winter street"),
    ("giovani", ["giovan[ie]", "ragazz[ie]"], "young people group"),
    ("truffa", ["truff\\w*", "raggir\\w*", "phishing", "frod\\w*"], "phone scam fraud"),
    ("smartphone", ["smartphone", "cellular\\w*", "telefonin\\w*", "app", "internet", "online", "sms"],
     "smartphone app hands"),
    ("poste", ["post[ae] italian[ae]", "ufficio postale", "poste"], "post office"),
    ("comune", ["comun[ei]", "sindac[oi]", "municipi\\w*"], "town hall italy"),
    ("smart_working", ["smart working", "lavoro agile", "telelavoro"], "remote work laptop home"),
    ("sciopero", ["sciaper\\w*", "scioper\\w*", "sindacat\\w*", "protest\\w*"], "strike protest street"),
    ("vaccino", ["vaccin\\w*"], "vaccine syringe"),
    ("ambiente", ["ambient\\w*", "inquinament\\w*", "clima", "climatic\\w*"], "pollution environment"),
    ("agricoltura", ["agricol\\w*", "agricoltor\\w*", "campagn[ae]"], "farmer field"),
    ("turismo", ["turism\\w*", "turist\\w*", "vacanz\\w*", "spiagg\\w*"], "tourists beach italy"),
    ("elezioni", ["elezion\\w*", "elettor\\w*", "referendum", "urn[ae]"], "election vote ballot box"),
    ("casa", ["cas[ae] popolar\\w*", "abitazion\\w*", "condomin\\w*"], "apartment building homes"),
]


def _inneschi_compilati():
    lista = []
    for nome, inneschi, query in CONCETTI_EXTRA + CONCETTI:
        for inn in inneschi:
            seq = [re.compile(senza_accenti(x.lower()) + r"$") for x in inn.split()]
            lista.append((nome, seq, query, inn))
    lista.sort(key=lambda x: -len(x[1]))   # frasi più lunghe prima
    return lista


def trova_concetti(parole):
    norme = [norm(p["w"]) for p in parole]
    inneschi = _inneschi_compilati()
    trovati, presi = [], set()
    for i in range(len(parole)):
        for nome, seq, query, inn in inneschi:
            if i + len(seq) <= len(parole) and all(seq[k].match(norme[i + k]) for k in range(len(seq))):
                if i not in presi:
                    trovati.append({"t": parole[i]["start"], "i": i, "concetto": nome, "query": query,
                                    "parola": " ".join(parole[i + k]["w"] for k in range(len(seq))).strip(" .,;:!?")})
                    presi.update(range(i, i + len(seq)))
                break
    return trovati


def fine_frase(parole, i):
    for k in range(i, len(parole)):
        if re.search(r"[.!?…][\"»”)]*$", parole[k]["w"]):
            return parole[k]["end"]
        if k + 1 < len(parole) and parole[k + 1]["start"] - parole[k]["end"] > 0.7:
            return parole[k]["end"]
    return parole[-1]["end"]


def scegli_immagini(parole, durata):
    scelte, usati = [], set()
    for c in trova_concetti(parole):
        if c["concetto"] in usati:
            continue
        inizio = max(0.0, c["t"] - IMG_ANTICIPO)
        if inizio < IMG_INIZIO_MIN:
            continue
        if scelte and (inizio - scelte[-1]["inizio"] < IMG_INTERVALLO_MIN
                       or inizio < scelte[-1]["inizio"] + scelte[-1]["durata"] + 0.2):
            continue
        dur = clamp(fine_frase(parole, c["i"]) - inizio + 0.3, IMG_DURATA_MIN, IMG_DURATA_MAX)
        dur = min(dur, durata - inizio - 0.1)
        if dur < IMG_DURATA_MIN:
            continue
        usati.add(c["concetto"])
        scelte.append({"inizio": r3(inizio), "durata": r3(dur), "parola": c["parola"], "t_parola": c["t"],
                       "concetto": c["concetto"], "query": c["query"], "file": None, "fonte": None})
    return scelte


# ---------- sorgenti immagini ----------
def _somiglianza(a, b):
    if not a or not b:
        return 0
    if a == b:
        return 1.0
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()


def cerca_locale(img, usati):
    cartella = BASE / "immagini"
    files = [f for f in cartella.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT] if cartella.exists() else []
    chiavi = {norm(x) for x in re.split(r"[_\s]+", img["concetto"] + " " + img["parola"]) if len(norm(x)) >= 3}
    for nome, inneschi, _q in CONCETTI_EXTRA + CONCETTI:
        if nome == img["concetto"]:
            chiavi |= {norm(re.sub(r"\\w\*|\[.*?\]|[?*\\]", "", x)) for inn in inneschi for x in inn.split()
                       if len(norm(re.sub(r"\\w\*|\[.*?\]|[?*\\]", "", x))) >= 4}
    migliore = (0, None)
    for f in files:
        if str(f) in usati:
            continue
        parti = [norm(x) for x in re.split(r"[\W_]+", f.stem) if len(x) >= 3]
        s = max((_somiglianza(p, k) for p in parti for k in chiavi), default=0)
        if s > migliore[0]:
            migliore = (s, f)
    return migliore[1] if migliore[0] >= 0.8 else None


def _fonti_auto():
    p = BASE / "immagini" / "auto" / "fonti.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def cerca_pexels(img, usati_id):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None, None
    import requests
    from PIL import Image
    try:
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key}, timeout=30,
                         params={"query": img["query"], "orientation": "landscape", "per_page": 20})
        r.raise_for_status()
    except Exception as e:
        print(f"   ! Pexels non raggiungibile per '{img['query']}': {e}")
        return None, None
    for ph in r.json().get("photos", []):
        if ph["id"] in usati_id or ph["width"] < 1200:
            continue
        for chiave in ("large2x", "original"):
            try:
                dati = requests.get(ph["src"][chiave], timeout=60).content
            except Exception:
                continue
            dest = BASE / "immagini" / "auto" / f"{img['concetto']}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(dati)
            try:
                with Image.open(dest) as im:
                    ok = im.width >= 1200
            except Exception:
                ok = False
            if ok:
                usati_id.add(ph["id"])
                fonte = (f"Pexels — foto di {ph.get('photographer', '?')} ({ph.get('url', '')}), "
                         f"licenza Pexels (uso gratuito)")
                fonti = _fonti_auto()
                fonti[dest.name] = fonte
                (dest.parent / "fonti.json").write_text(json.dumps(fonti, ensure_ascii=False, indent=1), "utf-8")
                return dest, fonte
    return None, None


ICONE = {"ricalcolo": "calcolatrice", "contributi": "documento", "arretrati": "euro", "domanda": "documento",
         "patronato": "ufficio", "verifica": "lente", "errori": "attenzione", "scadenza": "calendario", "assegno": "euro",
         "pensionati": "persone", "inps": "ufficio", "busta_paga": "documento", "agenzia_entrate": "documento",
         "soldi": "euro", "assegno_unico": "euro", "legge": "documento", "governo": "ufficio",
         "ministero": "ufficio", "tribunale": "ufficio", "comune": "ufficio", "banca": "euro",
         "famiglia": "persone", "giovani": "persone", "lavoro": "persone", "inflazione": "euro"}


def _disegna_icona(d, tipo, cx, cy, r, col, acc):
    """Icone vettoriali semplici (nessuna dipendenza esterna)."""
    w = max(6, r // 9)
    if tipo == "calcolatrice":
        d.rounded_rectangle((cx - r * .62, cy - r * .85, cx + r * .62, cy + r * .85), radius=r * .12, outline=col, width=w)
        d.rounded_rectangle((cx - r * .45, cy - r * .68, cx + r * .45, cy - r * .32), radius=r * .05, fill=acc)
        for i in range(3):
            for j in range(3):
                x, y = cx - r * .38 + i * r * .38, cy - r * .06 + j * r * .3
                d.rounded_rectangle((x - r * .13, y - r * .1, x + r * .13, y + r * .1), radius=r * .04, fill=col)
    elif tipo == "documento":
        x0, y0, x1, y1 = cx - r * .55, cy - r * .8, cx + r * .55, cy + r * .8
        d.polygon([(x0, y0), (x1 - r * .3, y0), (x1, y0 + r * .3), (x1, y1), (x0, y1)], outline=col, width=w)
        for k in range(4):
            y = y0 + r * .5 + k * r * .25
            d.line((x0 + r * .2, y, x1 - r * .2 - (r * .3 if k == 3 else 0), y), fill=col, width=w)
        d.line((cx + r * .05, cy + r * .62, cx + r * .3, cy + r * .9, cx + r * .85, cy + r * .2), fill=acc, width=w * 2,
               joint="curve")
    elif tipo == "euro":
        d.ellipse((cx - r * .85, cy - r * .85, cx + r * .85, cy + r * .85), outline=col, width=w)
        d.arc((cx - r * .5, cy - r * .55, cx + r * .5, cy + r * .55), 40, 320, fill=acc, width=w * 2)
        for dy in (-.12, .12):
            d.line((cx - r * .62, cy + r * dy, cx + r * .1, cy + r * dy), fill=acc, width=w)
    elif tipo == "calendario":
        d.rounded_rectangle((cx - r * .8, cy - r * .65, cx + r * .8, cy + r * .8), radius=r * .1, outline=col, width=w)
        d.rectangle((cx - r * .8, cy - r * .65, cx + r * .8, cy - r * .3), fill=col)
        for x in (-.4, .4):
            d.line((cx + r * x, cy - r * .85, cx + r * x, cy - r * .5), fill=acc, width=w * 2)
        for i in range(4):
            for j in range(3):
                x, y = cx - r * .55 + i * r * .37, cy - r * .08 + j * r * .28
                d.rectangle((x - r * .1, y - r * .08, x + r * .1, y + r * .08), fill=acc if (i, j) == (2, 1) else col)
    elif tipo == "ufficio":
        d.polygon([(cx - r * .9, cy - r * .35), (cx, cy - r * .9), (cx + r * .9, cy - r * .35)], fill=col)
        for k in range(4):
            x = cx - r * .6 + k * r * .4
            d.rectangle((x - r * .08, cy - r * .25, x + r * .08, cy + r * .55), fill=col)
        d.rectangle((cx - r * .9, cy + r * .62, cx + r * .9, cy + r * .78), fill=acc)
    elif tipo == "lente":
        d.ellipse((cx - r * .7, cy - r * .7, cx + r * .3, cy + r * .3), outline=col, width=w * 2)
        d.line((cx + r * .15, cy + r * .15, cx + r * .75, cy + r * .75), fill=acc, width=w * 3)
    elif tipo == "persone":
        for dx, sc in ((-.38, .8), (.38, .8)):
            hx, hr = cx + r * dx, r * .25 * sc / .8
            d.ellipse((hx - hr, cy - r * .55 - hr, hx + hr, cy - r * .55 + hr), fill=col)
            d.pieslice((hx - r * .42, cy - r * .2, hx + r * .42, cy + r * .9), 180, 360, fill=col)
        d.rectangle((cx - r * .85, cy + r * .38, cx + r * .85, cy + r * .48), fill=acc)
    elif tipo == "attenzione":
        d.polygon([(cx, cy - r * .85), (cx + r * .92, cy + r * .72), (cx - r * .92, cy + r * .72)], outline=col,
                  width=w)
        d.rounded_rectangle((cx - r * .09, cy - r * .35, cx + r * .09, cy + r * .28), radius=r * .05, fill=acc)
        d.ellipse((cx - r * .1, cy + r * .4, cx + r * .1, cy + r * .6), fill=acc)
    else:  # info
        d.ellipse((cx - r * .85, cy - r * .85, cx + r * .85, cy + r * .85), outline=col, width=w)
        d.ellipse((cx - r * .1, cy - r * .55, cx + r * .1, cy - r * .35), fill=acc)
        d.rectangle((cx - r * .09, cy - r * .2, cx + r * .09, cy + r * .55), fill=acc)


def genera_grafica(img):
    """Card grafica (sfondo nel colore principale, icona, parola chiave) quando manca una foto."""
    from PIL import Image, ImageDraw
    gw, gh = 1776, 1096
    col, hl = hex_rgb(COLORE_PRINCIPALE), hex_rgb(COLORE_EVIDENZIAZIONE)
    scuro = tuple(int(c * .45) for c in col)
    g = Image.new("RGB", (gw, gh))
    d = ImageDraw.Draw(g)
    for y in range(gh):
        p = y / gh
        d.line((0, y, gw, y), fill=tuple(int(a * (1 - p) + b * p) for a, b in zip(col, scuro)))
    for k, (x, y, rr) in enumerate(((1500, 120, 260), (1650, 980, 380), (150, 1050, 220))):
        d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=tuple(min(255, c + 40) for c in col), width=6)
    cx, cy, r = 470, gh // 2, 330
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="white")
    _disegna_icona(d, ICONE.get(img["concetto"], "info"), cx, cy, int(r * .72), col, hl)
    ft = str(next((BASE / "fonts").glob(f"*{NOMI_PESO[PESO_TITOLO]}.ttf")))
    testo = re.sub(r"^(l|dell|all|nell|sull|un|d)'|^(il|lo|la|i|gli|le|un|uno|una) ", "", img["parola"],
                   flags=re.I).upper()
    ris = adatta_testo(ft, testo, 860, 520, 190, 70, 3)
    if ris:
        f, righe, passo, top, alt = ris
        y0 = cy - alt / 2 - top
        for k, riga in enumerate(righe):
            d.text((880, y0 + k * passo), riga, font=f, fill="white", anchor="ls")
        d.rounded_rectangle((880, y0 + top + alt + 40, 1100, y0 + top + alt + 62), radius=11, fill=hl)
    dest = BASE / "immagini" / "auto" / f"grafica_{img['concetto']}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    g.save(dest)
    return dest


def risolvi_immagini(immagini):
    usati, usati_id = set(), set()
    fonti_auto = _fonti_auto()
    for img in immagini:
        f = cerca_locale(img, usati)
        if f:
            img["file"], img["fonte"] = str(f.relative_to(BASE)), "cartella ./immagini/ (tua)"
        else:
            cache = BASE / "immagini" / "auto" / f"{img['concetto']}.jpg"
            if cache.exists():
                img["file"], img["fonte"] = str(cache.relative_to(BASE)), fonti_auto.get(cache.name, "immagini/auto")
            else:
                f, fonte = cerca_pexels(img, usati_id)
                if f:
                    img["file"], img["fonte"] = str(f.relative_to(BASE)), fonte
                elif GRAFICHE_SE_MANCA_FOTO:
                    img["file"] = str(genera_grafica(img).relative_to(BASE))
                    img["fonte"] = "grafica generata dallo script (icona + parola chiave)"
        if img["file"]:
            usati.add(str(BASE / img["file"]))
    righe = [f"Crediti immagini — {time.strftime('%d/%m/%Y')}", ""]
    for img in immagini:
        if img["file"]:
            righe.append(f"{fmt_t(img['inizio'])}  {img['concetto']:<20} {img['file']}  —  {img['fonte']}")
    (BASE / "output" / "crediti.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")


# =====================================================================
#  NUMERI IN EVIDENZA
# =====================================================================
UNITA_NUM = {"euro": "EURO", "€": "EURO", "anni": "ANNI", "anno": "ANNO", "mesi": "MESI", "mese": "MESE",
             "giorni": "GIORNI", "giorno": "GIORNO", "ore": "ORE", "settimane": "SETTIMANE",
             "mila": "MILA", "milioni": "MILIONI", "miliardi": "MILIARDI", "punti": "PUNTI",
             "km": "KM", "chilometri": "KM"}
MESI = {"gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"}


def trova_numeri(parole, immagini, durata):
    attive = [(i["inizio"] - 0.2, i["inizio"] + i["durata"] + 0.2) for i in immagini if i["file"]]
    norme = [norm(p["w"]) for p in parole]
    out, visti, fine_prec = [], set(), -99
    for i, p in enumerate(parole):
        core = _split(p["w"])[1]
        m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})+|\d+)(,\d+)?(%|€)?", core)
        if not m:
            continue
        valore, unita = core, ""
        val_int = int(m.group(1).replace(".", ""))
        succ = norme[i + 1] if i + 1 < len(norme) else ""
        if m.group(3) == "%":
            prima = " ".join(norme[max(0, i - 3):i])
            if re.search(r"aument|rincar|crescit|cresc|\bpiu\b|sal[ei]|rialz", prima):
                valore = "+" + valore
            elif re.search(r"\bcal[oi]\b|tagli|riduz|ridott|\bmeno\b|scend|diminu|ribass", prima):
                valore = "−" + valore
        elif m.group(3) == "€":
            valore, unita = m.group(1) + (m.group(2) or ""), "EURO"
        elif succ in UNITA_NUM:
            unita = UNITA_NUM[succ]
            if succ in ("mila", "milioni", "miliardi") and (i + 3 < len(norme) and norme[i + 2] == "di"
                                                            and norme[i + 3] == "euro" or
                                                            i + 2 < len(norme) and norme[i + 2] == "euro"):
                unita += " DI EURO"
        elif succ in MESI:
            unita = succ.upper()
        elif not (m.group(2) is None and 1950 <= val_int <= 2100):
            continue                      # numero senza unità: non lo evidenzio
        testo = (valore + " " + unita).strip()
        inizio = max(0.0, p["start"] - IMG_ANTICIPO)
        fine = inizio + NUM_DURATA
        if testo in visti or inizio < fine_prec + 1.0 or fine > durata:
            continue
        if any(inizio < b and fine > a for a, b in attive):
            continue
        visti.add(testo)
        fine_prec = fine
        out.append({"inizio": r3(inizio), "durata": NUM_DURATA, "valore": valore, "unita": unita,
                    "testo": testo, "t_parola": p["start"]})
    return out


# =====================================================================
#  INQUADRATURA (volto) E FILTRO DI BASE
# =====================================================================
def frame_da_video(src, t, vf, w, h, pix="rgb24"):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", pix, "-"]
    r = subprocess.run(cmd, capture_output=True, cwd=BASE)
    n = w * h * 3
    if len(r.stdout) < n:
        return None
    return np.frombuffer(r.stdout[:n], dtype=np.uint8).reshape(h, w, 3)


def analizza_inquadratura(src, iv):
    import cv2
    asp_src, asp_out = iv["w"] / iv["h"], W / H
    if abs(asp_src - asp_out) < 0.02:
        return {"modalita": "pieno", "motivo": "il video è già 4:5"}
    cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    sw = 960
    sh = int(round(sw * iv["h"] / iv["w"] / 2)) * 2
    campioni, facce, multiple = 24, [], 0
    for k in range(campioni):
        t = iv["durata"] * (k + 0.5) / campioni
        fr = frame_da_video(src, t, f"scale={sw}:{sh}", sw, sh, "bgr24")
        if fr is None:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        det = cascata.detectMultiScale(g, 1.1, 5, minSize=(int(min(sw, sh) * 0.07),) * 2)
        if len(det):
            det = sorted(det, key=lambda d: -d[2] * d[3])
            x, y, w, h = det[0]
            facce.append(((x + w / 2) / sw, (y + h / 2) / sh, w / sw, h / sh))
            if len(det) > 1 and det[1][2] > 0.6 * w:
                multiple += 1
    if asp_src > asp_out:
        frazione = asp_out / asp_src                 # quota di larghezza che resta dopo il ritaglio
        if INQUADRATURA == "sfocato":
            return {"modalita": "sfocato", "motivo": "scelta manuale"}
        if not facce:
            if INQUADRATURA == "ritaglio":
                return {"modalita": "ritaglio", "x": r3((1 - frazione) / 2), "motivo": "manuale, volto non trovato: centro"}
            return {"modalita": "sfocato", "motivo": "nessun volto rilevato"}
        cx = sorted(f[0] for f in facce)
        p5, p95 = cx[int(len(cx) * 0.05)], cx[min(len(cx) - 1, int(len(cx) * 0.95))]
        larg_volto = statistics.median(f[2] for f in facce)
        ingombro = p95 - p5 + larg_volto * 1.6
        motivo = f"volto in {len(facce)}/{campioni} campioni, ingombro {ingombro:.0%} vs ritaglio {frazione:.0%}"
        if INQUADRATURA == "auto":
            if len(facce) < campioni * 0.4:
                return {"modalita": "sfocato", "motivo": "volto poco presente: " + motivo}
            if ingombro > frazione * 0.95:
                return {"modalita": "sfocato", "motivo": "lo speaker si muove troppo: " + motivo}
            if multiple > campioni * 0.3:
                return {"modalita": "sfocato", "motivo": "più persone in scena: " + motivo}
        x = clamp(statistics.median(cx) - frazione / 2, 0, 1 - frazione)
        return {"modalita": "ritaglio", "x": r3(x), "motivo": motivo}
    frazione = asp_src / asp_out                     # sorgente più "alto" del 4:5: ritaglio verticale
    cy = statistics.median(f[1] for f in facce) if facce else None
    y = clamp(cy - 0.38 * frazione, 0, 1 - frazione) if cy is not None else (1 - frazione) * 0.3
    return {"modalita": "ritaglio_v", "y": r3(y), "motivo": f"video verticale, volto in {len(facce)}/{campioni} campioni"}


def filtro_base(iv, inq, ingresso, uscita):
    m = inq["modalita"]
    if m == "pieno":
        return f"{ingresso}scale={W}:{H}:flags=lanczos,setsar=1{uscita}"
    if m == "ritaglio":
        sw = int(round(iv["w"] * H / iv["h"] / 2)) * 2
        x = int(round(inq["x"] * sw))
        return f"{ingresso}scale={sw}:{H}:flags=lanczos,crop={W}:{H}:{min(x, sw - W)}:0,setsar=1{uscita}"
    if m == "ritaglio_v":
        sh = int(round(iv["h"] * W / iv["w"] / 2)) * 2
        y = int(round(inq["y"] * sh))
        return f"{ingresso}scale={W}:{sh}:flags=lanczos,crop={W}:{H}:0:{min(y, sh - H)},setsar=1{uscita}"
    return (f"{ingresso}split=2[bg0][fg0];"
            f"[bg0]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
            f"boxblur=12:2,scale={W}:{H},eq=brightness=-0.07:saturation=0.85[bg1];"
            f"[fg0]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[fg1];"
            f"[bg1][fg1]overlay=(W-w)/2:(H-h)/2{uscita}")


# =====================================================================
#  2) PIANO DI MONTAGGIO
# =====================================================================
def durata_uscita(piano):
    return piano["durata"] + (CHIUSURA_CODA if CHIUSURA_TITOLO else 0.0)


def inizio_chiusura(piano):
    return durata_uscita(piano) - CHIUSURA_DURATA if CHIUSURA_TITOLO else None


def crea_piano(src, iv, trascr, fonts):
    parole = [p for s in trascr["segmenti"] for p in s["parole"]]
    parole = normalizza_parole(parole)
    mis = Misuratore(fonts["sottotitoli"]["path"], SUB_FONT_PX)
    blocchi = crea_blocchi(parole, mis, iv["durata"])
    print("→ Cerco i concetti visivi e le immagini")
    # immagini e numeri devono finire prima del cartello finale
    limite = iv["durata"] + CHIUSURA_CODA - CHIUSURA_DURATA - 0.3 if CHIUSURA_TITOLO else iv["durata"]
    immagini = scegli_immagini(parole, limite)
    risolvi_immagini(immagini)
    numeri = trova_numeri(parole, immagini, limite)
    print("→ Analizzo l'inquadratura (rilevamento volto)")
    inq = analizza_inquadratura(src, iv)
    piano = {
        "sorgente": str(Path(src).relative_to(BASE)) if Path(src).is_relative_to(BASE) else str(src),
        "durata": r3(iv["durata"]), "sorgente_wxh": [iv["w"], iv["h"]], "inquadratura": inq,
        "sottotitoli_px": SUB_FONT_PX, "sottotitoli_max_caratteri": SUB_MAX_CARATTERI,
        "immagini": [{"id": k + 1, **i} for k, i in enumerate(immagini)],
        "numeri": numeri,
        "sottotitoli": [{"inizio": b["inizio"], "fine": b["fine"], "righe": b["righe"],
                         "parole": b["parole"]} for b in blocchi],
    }
    salva_piano(piano)
    esporta_srt(piano, BASE / "output" / "sottotitoli_corretti.srt")
    provino_immagini(piano)
    return piano


def salva_piano(piano):
    (BASE / "output" / "piano_montaggio.json").write_text(json.dumps(piano, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")


def mostra_piano(piano):
    righe = []
    inq = piano["inquadratura"]
    righe.append(f"## Piano di montaggio — {piano['sorgente']} ({fmt_t(piano['durata'])})\n")
    righe.append(f"**Inquadratura:** {inq['modalita']} — {inq['motivo']}\n")
    righe.append(f"**Titolo fisso:** {TITOLO.upper()}  \n**Ticker:** {TICKER}\n")
    if CHIUSURA_TITOLO:
        righe.append(f"**Cartello finale:** da {fmt_t(inizio_chiusura(piano))} a {fmt_t(durata_uscita(piano))} — "
                     f"«{CHIUSURA_TITOLO.upper()}» / «{CHIUSURA_TESTO.upper()}» "
                     f"(+{CHIUSURA_CODA:.0f} s di fotogramma fermo in coda)\n")
    righe.append("### Immagini\n")
    righe.append("| # | Inizio | Durata | Parola chiave | Concetto | File / fonte |")
    righe.append("|---|---|---|---|---|---|")
    for i in piano["immagini"]:
        f = i["file"] or "**MANCANTE** (metti un file in ./immagini/ o imposta PEXELS_API_KEY)"
        fonte = "" if not i["file"] else (" — Pexels" if "Pexels" in (i["fonte"] or "") else
                                          " — grafica generata" if "grafica" in (i["fonte"] or "") else " — tua")
        righe.append(f"| {i['id']} | {fmt_t(i['inizio'])} | {i['durata']:.1f}s | «{i['parola']}» | "
                     f"{i['concetto']} | {f}{fonte} |")
    righe.append("\n### Numeri in evidenza\n")
    righe.append("| Inizio | Testo | Durata |")
    righe.append("|---|---|---|")
    for n in piano["numeri"]:
        righe.append(f"| {fmt_t(n['inizio'])} | **{n['testo']}** | {n['durata']:.1f}s |")
    if not piano["numeri"]:
        righe.append("| — | nessuno | — |")
    subs = piano["sottotitoli"]
    righe.append(f"\n### Sottotitoli: {len(subs)} blocchi (font {piano['sottotitoli_px']} px, "
                 f"max {piano['sottotitoli_max_caratteri']} car./riga)\n")
    righe.append("| Inizio | Fine | Testo |")
    righe.append("|---|---|---|")
    for b in subs:
        righe.append(f"| {fmt_t(b['inizio'])} | {fmt_t(b['fine'])} | {' / '.join(b['righe'])} |")
    testo = "\n".join(righe)
    (BASE / "output" / "piano_montaggio.md").write_text(testo + "\n", encoding="utf-8")
    print("\n" + testo + "\n")


def provino_immagini(piano):
    from PIL import Image, ImageDraw, ImageFont
    imgs = [i for i in piano["immagini"] if i["file"]]
    if not imgs:
        return
    cw, ch, col = 360, 225, 3
    rig = math.ceil(len(imgs) / col)
    tav = Image.new("RGB", (cw * col, (ch + 30) * rig), "white")
    d = ImageDraw.Draw(tav)
    try:
        f = ImageFont.truetype(str(next((BASE / "fonts").glob("*SemiBold.ttf"))), 18)
    except Exception:
        f = ImageFont.load_default()
    for k, i in enumerate(imgs):
        x, y = (k % col) * cw, (k // col) * (ch + 30)
        with Image.open(BASE / i["file"]) as im:
            im = copertura(im.convert("RGB"), cw - 8, ch - 8)
        tav.paste(im, (x + 4, y + 4))
        d.text((x + 6, y + ch + 2), f"{i['id']}. {fmt_t(i['inizio'])} «{i['parola']}»", fill="black", font=f)
    tav.save(BASE / "output" / "anteprima_immagini.jpg", quality=88)


def esporta_srt(piano, dest):
    import pysubs2
    s = pysubs2.SSAFile()
    for b in piano["sottotitoli"]:
        s.append(pysubs2.SSAEvent(start=int(b["inizio"] * 1000), end=int(b["fine"] * 1000),
                                  text="\\N".join(b["righe"])))
    s.save(str(dest), format_="srt")


# =====================================================================
#  ASS (sottotitoli karaoke parola per parola)
# =====================================================================
def genera_ass(piano, fonts, dest):
    import pysubs2
    px = piano["sottotitoli_px"]
    fs = fonts["sottotitoli"]
    subs = pysubs2.SSAFile()
    subs.info.update({"PlayResX": str(W), "PlayResY": str(H), "WrapStyle": "2", "ScaledBorderAndShadow": "yes"})
    subs.styles["Sub"] = pysubs2.SSAStyle(
        fontname=fs["famiglia"], fontsize=round(px * fs["rapporto_ass"], 1),
        primarycolor=pysubs2.Color(255, 255, 255, 0), secondarycolor=pysubs2.Color(255, 255, 255, 0),
        outlinecolor=pysubs2.Color(0, 0, 0, 0), backcolor=pysubs2.Color(0, 0, 0, 110),
        bold=False, outline=4, shadow=2, alignment=pysubs2.Alignment.MIDDLE_CENTER,
        marginl=0, marginr=0, marginv=0)
    hl = ass_colore(COLORE_EVIDENZIAZIONE)
    pos = f"{{\\an5\\pos({W // 2},{SUB_CY})}}"

    def pulisci(s):
        return s.replace("{", "(").replace("}", ")").replace("\\", "/")

    for b in piano["sottotitoli"]:
        parole = b["parole"]
        testi_righe = [r.split() for r in b["righe"]]
        piatte = [w for r in testi_righe for w in r]
        if len(piatte) != len(parole):          # testo modificato a mano con numero di parole diverso
            subs.append(pysubs2.SSAEvent(start=int(b["inizio"] * 1000), end=int(b["fine"] * 1000), style="Sub",
                                         text=pos + "\\N".join(pulisci(r) for r in b["righe"])))
            continue
        a_capo = len(testi_righe[0])
        for k in range(len(parole)):
            t0 = b["inizio"] if k == 0 else max(b["inizio"], parole[k]["start"])
            t1 = b["fine"] if k == len(parole) - 1 else min(b["fine"], parole[k + 1]["start"])
            if t1 - t0 < 0.01:
                continue
            pezzi = []
            for j, w in enumerate(piatte):
                w = pulisci(w)
                pezzi.append((f"{{\\1c{hl}}}{w}{{\\1c&HFFFFFF&}}" if j == k else w)
                             + ("\\N" if j == a_capo - 1 and j < len(piatte) - 1 else " "))
            subs.append(pysubs2.SSAEvent(start=int(round(t0 * 1000)), end=int(round(t1 * 1000)), style="Sub",
                                         text=pos + "".join(pezzi).rstrip()))
    subs.save(str(dest))


def verifica_ass(ass_rel, durata):
    """Renderizza i soli sottotitoli su nero e controlla che restino nell'area utile e nella loro zona."""
    import numpy as np
    fps_c = 3
    cmd = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps_c}:d={durata:.2f}",
           "-vf", f"ass={ass_rel}:fontsdir=fonts,format=gray", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=BASE)
    n, k, problemi, unione = W * H, 0, [], None
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        a = np.frombuffer(buf, dtype=np.uint8).reshape(H, W) > 40
        k += 1
        if not a.any():
            continue
        ys, xs = np.where(a.any(axis=1))[0], np.where(a.any(axis=0))[0]
        bb = (int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1)
        unione = bb if unione is None else (min(unione[0], bb[0]), min(unione[1], bb[1]),
                                            max(unione[2], bb[2]), max(unione[3], bb[3]))
        if bb[0] < SAFE[0] or bb[2] > SAFE[2] or bb[1] < SUB_ZONA[0] - 6 or bb[3] > SUB_ZONA[1] + 6:
            problemi.append(((k - 1) / fps_c, bb))
    p.wait()
    return problemi, unione


# =====================================================================
#  GRAFICA (titolo, card immagini, numeri, ticker) → flusso RGBA per ffmpeg
# =====================================================================
def maschera_arrotondata(w, h, r, ss=4):
    from PIL import Image, ImageDraw
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def copertura(im, w, h):
    from PIL import Image
    sw, sh = im.size
    s = max(w / sw, h / sh)
    nw, nh = max(w, round(sw * s)), max(h, round(sh * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return im.crop((x, y, x + w, y + h))


def con_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a + 0.5)))
    return img


def adatta_testo(font_path, testo, max_w, max_h, px_max, px_min, max_righe, interlinea=1.06):
    """Trova il corpo più grande (px_max→px_min) con cui il testo sta in max_righe nel riquadro."""
    from PIL import ImageFont
    parole = testo.split()
    for px in range(px_max, px_min - 1, -1):
        f = ImageFont.truetype(font_path, px)
        righe, cur = [], ""
        for p in parole:
            prova = (cur + " " + p).strip()
            if f.getlength(prova) <= max_w or not cur:
                cur = prova
            else:
                righe.append(cur)
                cur = p
            if p.endswith(":") and max_righe >= 2:     # "PENSIONI 2027:" / "COSA CAMBIA"
                righe.append(cur)
                cur = ""
        if cur:
            righe.append(cur)
        if len(righe) > max_righe or any(f.getlength(r) > max_w for r in righe):
            continue
        if len(righe) == 2 and not any(r.endswith(":") for r in righe):   # bilancia le due righe
            best = None
            for k in range(1, len(parole)):
                a, b = " ".join(parole[:k]), " ".join(parole[k:])
                m = max(f.getlength(a), f.getlength(b))
                if m <= max_w and (best is None or m < best[0]):
                    best = (m, [a, b])
            righe = best[1] if best else righe
        passo = px * interlinea
        top = f.getbbox(righe[0], anchor="ls")[1]
        bottom = max(f.getbbox(r, anchor="ls")[3] for r in righe)
        altezza = (len(righe) - 1) * passo + bottom - top
        if altezza <= max_h:
            return f, righe, passo, top, altezza
    return None


class Grafica:
    def __init__(self, piano, fonts):
        from PIL import Image, ImageDraw, ImageFilter
        self.Image = Image
        self.piano = piano
        self.col = hex_rgb(COLORE_PRINCIPALE)
        self.hl = hex_rgb(COLORE_EVIDENZIAZIONE)
        ft, fs = fonts["titolo"]["path"], fonts["sottotitoli"]["path"]

        # --- titolo ---
        tw, th = TITOLO_BOX[2] - TITOLO_BOX[0], TITOLO_BOX[3] - TITOLO_BOX[1]
        self.titolo = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        fascia = Image.new("RGBA", (tw, th), (*self.col, 230))
        self.titolo.paste(fascia, (0, 0), maschera_arrotondata(tw, th, 16))
        ris = adatta_testo(ft, TITOLO.upper(), tw - 2 * 28, th - 2 * 12, 62, 44, 2)
        if ris is None:
            ris = adatta_testo(ft, TITOLO.upper(), tw - 2 * 20, th - 2 * 8, 44, 30, 3)
            print("   ! Titolo troppo lungo: ridotto sotto i 44 px. Accorcialo se possibile.")
        f, righe, passo, top, alt = ris
        d = ImageDraw.Draw(self.titolo)
        y0 = (th - alt) / 2 - top
        for k, r in enumerate(righe):
            d.text((tw / 2, y0 + k * passo), r, font=f, fill="white", anchor="ms")
        self.titolo_px = f.size

        # --- ticker ---
        kw, kh = TICKER_BOX[2] - TICKER_BOX[0], TICKER_BOX[3] - TICKER_BOX[1]
        mask_t = maschera_arrotondata(kw, kh, 12)
        self.ticker_fondo = Image.new("RGBA", (kw, kh), (0, 0, 0, 0))
        self.ticker_fondo.paste(Image.new("RGBA", (kw, kh), (*self.col, 230)), (0, 0), mask_t)
        from PIL import ImageFont
        fk = ImageFont.truetype(fs, 34)
        frasi = [x.strip() for x in TICKER.split("•") if x.strip()]
        unita = " • ".join(frasi) + " • "
        self.ticker_u = fk.getlength(unita * 2) - fk.getlength(unita)
        rip = math.ceil((kw + self.ticker_u) / self.ticker_u) + 1
        self.ticker_strip = Image.new("RGBA", (math.ceil(fk.getlength(unita * rip)) + 4, kh), (0, 0, 0, 0))
        ImageDraw.Draw(self.ticker_strip).text((0, kh / 2), unita * rip, font=fk, fill="white", anchor="lm")
        bordi = Image.new("L", (kw, 1), 255)
        for x in range(22):
            v = int(255 * x / 22)
            bordi.putpixel((x, 0), v)
            bordi.putpixel((kw - 1 - x, 0), v)
        from PIL import ImageChops
        self.ticker_mask = ImageChops.multiply(mask_t, bordi.resize((kw, kh)))
        self.ImageChops = ImageChops

        # --- livelli statici ---
        self.statico_senza_titolo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.statico_senza_titolo.alpha_composite(self.ticker_fondo, (TICKER_BOX[0], TICKER_BOX[1]))
        self.statico = self.statico_senza_titolo.copy()
        self.statico.alpha_composite(self.titolo, (TITOLO_BOX[0], TITOLO_BOX[1]))

        # --- card ---
        b = CARD_BORDO
        self.iw, self.ih = CARD_W - 2 * b, CARD_H - 2 * b
        self.mask_card = maschera_arrotondata(CARD_W, CARD_H, CARD_RAGGIO)
        self.mask_inner = maschera_arrotondata(self.iw, self.ih, CARD_RAGGIO - b)
        self.card_bianca = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, 0))
        self.card_bianca.putalpha(self.mask_card)
        self.P = 40
        ombra = Image.new("L", (CARD_W + 2 * self.P, CARD_H + 2 * self.P), 0)
        ombra.paste(self.mask_card.point(lambda v: int(v * 0.55)), (self.P, self.P + 10))
        ombra = ombra.filter(ImageFilter.GaussianBlur(13))
        self.ombra = Image.new("RGBA", ombra.size, (0, 0, 0, 0))
        self.ombra.putalpha(ombra)
        self.sorgenti = {}
        for img in piano["immagini"]:
            if img["file"]:
                with Image.open(BASE / img["file"]) as im:
                    from PIL import ImageOps
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    self.sorgenti[img["id"]] = copertura(im, round(self.iw * 1.06), round(self.ih * 1.06))
        self.immagini = [i for i in piano["immagini"] if i["id"] in self.sorgenti]

        # --- numeri ---
        self.numeri = []
        for n in piano["numeri"]:
            card = self.ombra.copy()
            c = self.card_bianca.copy()
            c.paste(Image.new("RGBA", (self.iw, self.ih), (*self.col, 255)), (b, b), self.mask_inner)
            d = ImageDraw.Draw(c)
            sotto = n["unita"]
            ris = adatta_testo(ft, n["valore"], self.iw - 80, (self.ih - 90) * (0.66 if sotto else 1), 230, 60, 1)
            f, righe, _p, top, alt = ris
            alt2, f2 = 0, None
            if sotto:
                r2 = adatta_testo(ft, sotto, self.iw - 80, 110, 96, 30, 1)
                f2, _r, _p2, top2, alt2 = r2
            spazio = 34 if sotto else 0
            y = b + (self.ih - alt - spazio - alt2) / 2 - top
            d.text((CARD_W / 2, y), righe[0], font=f, fill=(*self.hl, 255), anchor="ms")
            if sotto:
                d.text((CARD_W / 2, y + top + alt + spazio - top2), sotto, font=f2, fill="white", anchor="ms")
            card.alpha_composite(c, (self.P, self.P))
            self.numeri.append((n, card))

        # --- cartello finale ---
        self.chiusura = None
        if CHIUSURA_TITOLO:
            card = self.ombra.copy()
            c = self.card_bianca.copy()
            c.paste(Image.new("RGBA", (self.iw, self.ih), (*self.col, 255)), (b, b), self.mask_inner)
            d = ImageDraw.Draw(c)
            f1, r1, p1, t1, a1 = adatta_testo(ft, CHIUSURA_TITOLO.upper(), self.iw - 90, 250, 92, 40, 2)
            f2, r2, p2, t2, a2 = adatta_testo(ft, CHIUSURA_TESTO.upper(), self.iw - 90, 170, 70, 30, 2)
            spazio = 56
            y = b + (self.ih - a1 - spazio - a2) / 2 - t1
            for k, riga in enumerate(r1):
                d.text((CARD_W / 2, y + k * p1), riga, font=f1, fill="white", anchor="ms")
            ybar = y + t1 + a1 + spazio / 2
            d.rounded_rectangle((CARD_W / 2 - 90, ybar - 5, CARD_W / 2 + 90, ybar + 5), radius=5, fill=(*self.hl, 255))
            y2 = y + t1 + a1 + spazio - t2
            for k, riga in enumerate(r2):
                d.text((CARD_W / 2, y2 + k * p2), riga, font=f2, fill=(*self.hl, 255), anchor="ms")
            card.alpha_composite(c, (self.P, self.P))
            self.chiusura = (inizio_chiusura(piano), card)

        self.soglia = [0] * 17 + [255] * 239
        self.violazioni = []

    # ------------------------------------------------------------------
    def _card_immagine(self, img, tl):
        Image = self.Image
        dur = img["durata"]
        p = ease_out_cubic(tl / 0.35)
        scala = 0.92 + 0.08 * p
        alpha = p * (clamp((dur - tl) / 0.3, 0, 1) if tl > dur - 0.3 else 1)
        src = self.sorgenti[img["id"]]
        kb = 1.0 + 0.05 * clamp(tl / dur, 0, 1)
        sw, sh = src.size
        bw, bh = sw / kb, sh / kb
        box = ((sw - bw) / 2, (sh - bh) / 2, (sw + bw) / 2, (sh + bh) / 2)
        interno = src.resize((self.iw, self.ih), Image.BILINEAR, box=box)
        card = self.card_bianca.copy()
        card.paste(interno, (CARD_BORDO, CARD_BORDO), self.mask_inner)
        tela = self.ombra.copy()
        tela.alpha_composite(card, (self.P, self.P))
        return self._scala_alpha(tela, scala, alpha)

    def _scala_alpha(self, tela, scala, alpha):
        if abs(scala - 1) > 0.002:
            tela = tela.resize((max(1, round(tela.width * scala)), max(1, round(tela.height * scala))),
                               self.Image.BILINEAR)
        return con_alpha(tela, alpha)

    def _incolla_centro(self, frame, tela):
        frame.alpha_composite(tela, (round(CARD_CX - tela.width / 2), round(CARD_CY - tela.height / 2)))

    def frame(self, t, controlla=False):
        if t >= 0.4:
            f = self.statico.copy()
        else:
            f = self.statico_senza_titolo.copy()
            p = ease_out_cubic(t / 0.4)
            f.alpha_composite(con_alpha(self.titolo, p), (TITOLO_BOX[0], TITOLO_BOX[1] - round(60 * (1 - p))))
        # ticker
        kw, kh = TICKER_BOX[2] - TICKER_BOX[0], TICKER_BOX[3] - TICKER_BOX[1]
        off = (t * TICKER_VELOCITA) % self.ticker_u
        testo = self.ticker_strip.transform((kw, kh), self.Image.AFFINE, (1, 0, off, 0, 1, 0), self.Image.BILINEAR)
        testo.putalpha(self.ImageChops.multiply(testo.getchannel("A"), self.ticker_mask))
        f.alpha_composite(testo, (TICKER_BOX[0], TICKER_BOX[1]))
        # immagini
        for img in self.immagini:
            tl = t - img["inizio"]
            if 0 <= tl < img["durata"]:
                self._incolla_centro(f, self._card_immagine(img, tl))
        # numeri
        for n, tela in self.numeri:
            tl = t - n["inizio"]
            if 0 <= tl < n["durata"]:
                scala = 0.6 + 0.4 * ease_out_back(tl / 0.25)
                alpha = clamp(tl / 0.12, 0, 1) * (clamp((n["durata"] - tl) / 0.25, 0, 1))
                self._incolla_centro(f, self._scala_alpha(tela, scala, alpha))
        if self.chiusura and t >= self.chiusura[0]:
            tl = t - self.chiusura[0]
            scala = 0.7 + 0.3 * ease_out_back(tl / 0.35)
            self._incolla_centro(f, self._scala_alpha(self.chiusura[1], scala, clamp(tl / 0.15, 0, 1)))
        if controlla and t >= 0.5:
            bb = f.getchannel("A").point(self.soglia).getbbox()
            if bb and (bb[0] < SAFE[0] or bb[1] < SAFE[1] or bb[2] > SAFE[2] or bb[3] > SAFE[3]):
                self.violazioni.append((r3(t), bb))
        return f


# =====================================================================
#  RENDER
# =====================================================================
def _misura(src, pre=""):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-vn", "-af",
                        f"{pre}loudnorm=I={LUFS}:TP={TRUE_PEAK}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=BASE)
    return json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])


def misura_loudness(src):
    """Loudnorm a due passaggi. Se il guadagno necessario farebbe superare il true peak (loudnorm
    passerebbe in modalità dinamica e resterebbe sotto i -14 LUFS), prima alzo il volume e limito i picchi,
    poi rimisuro: così il secondo passaggio resta lineare e preciso."""
    cache = BASE / "output" / "_loudnorm.json"
    chiave = f"{src}:{os.path.getmtime(BASE / src)}:{LUFS}:{TRUE_PEAK}"
    if cache.exists():
        d = json.loads(cache.read_text())
        if d.get("chiave") == chiave:
            return d
    print("→ Misuro il loudness (passaggio 1 di 2)")
    d = _misura(src)
    d["pre"] = ""
    guadagno = LUFS - float(d["input_i"])
    if float(d["input_tp"]) + guadagno > TRUE_PEAK - 0.5:
        print(f"   picchi troppo alti per un guadagno lineare di {guadagno:+.1f} dB: uso un limitatore")
        limite = 10 ** ((TRUE_PEAK - 2.0) / 20)        # 1 dB di margine per l'encoder AAC
        totale = guadagno
        for _ in range(4):
            pre = f"volume={totale:.2f}dB,alimiter=limit={limite:.4f}:level=false:attack=3:release=60:asc=1,"
            d = _misura(src, pre)
            d["pre"] = pre
            manca = LUFS - float(d["input_i"])
            if abs(manca) <= 0.3 and float(d["input_tp"]) + manca <= TRUE_PEAK - 0.4:
                break
            totale += manca + 0.2
    d["chiave"] = chiave
    cache.write_text(json.dumps(d))
    return d


def filtro_audio(m):
    lra = max(11.0, math.ceil(float(m["input_lra"])) + 1)
    return (f"{m.get('pre', '')}loudnorm=I={LUFS}:TP={TRUE_PEAK}:LRA={lra}:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true:print_format=summary")


def renderizza(piano, fonts, ass_rel, dest, anteprima):
    src = piano["sorgente"]
    iv = info_video(BASE / src)
    durata = min(durata_uscita(piano), DURATA_ANTEPRIMA) if anteprima else durata_uscita(piano)
    coda = durata_uscita(piano) - piano["durata"]
    n_frame = int(round(durata * FPS))
    loud = misura_loudness(src)
    graf = Grafica(piano, fonts)
    # 540x675 ha l'altezza dispari (non ammessa da yuv420p): aggiungo 1 px nero sotto → 540x676
    finale = f",scale={W // 2}:{H // 2}:flags=lanczos,pad={W // 2}:{H // 2 + 1}:0:0" if anteprima else ""
    tpad = f",tpad=stop_mode=clone:stop_duration={coda + 0.5:.2f}" if coda > 0 else ""
    apad = ",apad" if coda > 0 else ""
    fc = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS}{tpad}[v0];" + filtro_base(iv, piano["inquadratura"], "[v0]", "[b]") + ";"
          f"[1:v]setpts=PTS-STARTPTS[o];[b][o]overlay=0:0:format=gbrp:eof_action=pass,"
          f"ass={ass_rel}:fontsdir=fonts{finale},format=yuv420p[v];"
          f"[0:a:0]asetpts=PTS-STARTPTS,{filtro_audio(loud)},aresample=48000{apad}[a]")
    if anteprima:
        venc = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-profile:v", "high"]
    else:
        venc = ["-c:v", "libx264", "-preset", PRESET_FINALE, "-profile:v", "high", "-level", "4.1",
                "-b:v", BITRATE_VIDEO, "-maxrate", MAXRATE, "-bufsize", BUFSIZE, "-g", str(FPS * 2)]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", str(src),
           "-f", "rawvideo", "-pix_fmt", "rgba", "-video_size", f"{W}x{H}", "-framerate", str(FPS),
           "-thread_queue_size", "64", "-i", "-",
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{durata:.3f}",
           *venc, "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", str(dest.relative_to(BASE))]
    log = open(BASE / "output" / ("_ffmpeg_anteprima.log" if anteprima else "_ffmpeg_finale.log"), "w")
    print(f"→ Render {'anteprima 540x676' if anteprima else 'finale 1080x1350'}: {n_frame} fotogrammi")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log, cwd=BASE)
    t0, ultimo = time.time(), -1
    try:
        for k in range(n_frame):
            p.stdin.write(graf.frame(k / FPS, controlla=(k % 5 == 0)).tobytes())
            perc = int(100 * (k + 1) / n_frame)
            if perc // 10 != ultimo:
                ultimo = perc // 10
                v = (k + 1) / max(0.01, time.time() - t0)
                print(f"   {perc:3d}%  ({v:.1f} fps)", flush=True)
        p.stdin.close()
    except BrokenPipeError:
        pass
    rc = p.wait()
    log.close()
    if rc != 0:
        sys.exit(f"ffmpeg ha dato errore, vedi output/{Path(log.name).name}:\n"
                 + Path(log.name).read_text()[-2000:])
    return graf.violazioni


# =====================================================================
#  CONTROLLI FINALI
# =====================================================================
def controlla_risultato(piano, out, trascr, violazioni_grafica):
    from PIL import Image
    print("→ Controllo il risultato")
    report, ok = [], True
    d = ffprobe(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next(s for s in d["streams"] if s["codec_type"] == "audio")
    br = int(d["format"].get("bit_rate", 0)) / 1e6
    vbr = int(v.get("bit_rate", 0)) / 1e6
    attesi = [("risoluzione", f"{v['width']}x{v['height']}", f"{W}x{H}"),
              ("fps", v["r_frame_rate"], f"{FPS}/1"), ("profilo", v.get("profile"), "High"),
              ("pixel", v.get("pix_fmt"), "yuv420p"), ("audio", f"{a['codec_name']} {a['sample_rate']}",
                                                       "aac 48000")]
    for nome, val, att in attesi:
        stato = "ok" if str(val) == att else "ERRORE"
        ok &= stato == "ok"
        report.append(f"{nome:<12} {val}  ({stato})")
    report.append(f"{'bitrate':<12} video {vbr:.1f} Mbps, totale {br:.1f} Mbps")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-vn", "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    li, tp = float(m["input_i"]), float(m["input_tp"])
    report.append(f"{'loudness':<12} {li:.1f} LUFS, true peak {tp:.1f} dBTP  "
                  f"({'ok' if abs(li - LUFS) <= 1.0 and tp <= TRUE_PEAK + 0.3 else 'DA VERIFICARE'})")
    # fotogrammi
    cdir = BASE / "output" / "controllo"
    cdir.mkdir(exist_ok=True)
    tav = Image.new("RGB", (3 * 360, 2 * 450), "black")
    for k in range(6):
        t = durata_uscita(piano) * (k + 0.5) / 6
        fp = cdir / f"fotogramma_{k + 1}.jpg"
        esegui(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(out), "-frames:v", "1",
                "-q:v", "3", str(fp)])
        with Image.open(fp) as im:
            tav.paste(im.resize((360, 450)), ((k % 3) * 360, (k // 3) * 450))
    for i in piano["immagini"]:
        if i["file"]:
            esegui(["ffmpeg", "-y", "-v", "error", "-ss", f"{i['inizio'] + 0.6:.2f}", "-i", str(out),
                    "-frames:v", "1", "-q:v", "4", str(cdir / f"immagine_{i['id']:02d}.jpg")])
    if CHIUSURA_TITOLO:
        esegui(["ffmpeg", "-y", "-v", "error", "-ss", f"{inizio_chiusura(piano) + 1:.2f}", "-i", str(out),
                "-frames:v", "1", "-q:v", "4", str(cdir / "cartello_finale.jpg")])
    tav.save(cdir / "provino_6_fotogrammi.jpg", quality=88)
    report.append(f"{'fotogrammi':<12} output/controllo/provino_6_fotogrammi.jpg")
    # margini
    if violazioni_grafica:
        ok = False
        report.append(f"{'margini':<12} grafica fuori area utile in {len(violazioni_grafica)} campioni, "
                      f"es. t={violazioni_grafica[0][0]}s bbox={violazioni_grafica[0][1]}")
    else:
        report.append(f"{'margini':<12} grafica sempre dentro x {SAFE[0]}–{SAFE[2]}, y {SAFE[1]}–{SAFE[3]} (ok)")
    # sincronizzazione
    scarti = [abs(i["inizio"] - max(0, i["t_parola"] - IMG_ANTICIPO)) for i in piano["immagini"] if i.get("t_parola") is not None]
    scarti += [abs(n["inizio"] - max(0, n["t_parola"] - IMG_ANTICIPO)) for n in piano["numeri"] if n.get("t_parola") is not None]
    if scarti:
        report.append(f"{'sincronia':<12} immagini/numeri: scarto max dalla parola {max(scarti) * 1000:.0f} ms "
                      f"({'ok' if max(scarti) <= 1 / FPS else 'modificato a mano'})")
    sotto1 = [b for b in piano["sottotitoli"] if b["fine"] - b["inizio"] < 0.99]
    sopra3 = [b for b in piano["sottotitoli"] if b["fine"] - b["inizio"] > 3.01]
    report.append(f"{'sottotitoli':<12} {len(piano['sottotitoli'])} blocchi, <1 s: {len(sotto1)}, >3 s: {len(sopra3)}; "
                  f"karaoke sui tempi parola di Whisper")
    testo = "\n".join(report)
    (BASE / "output" / "controllo" / "report.txt").write_text(testo + "\n", encoding="utf-8")
    print("\n" + testo + "\n")
    return ok


# =====================================================================
#  COPERTINA
# =====================================================================
def crea_copertina(piano, fonts, dest):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    print("→ Scelgo il fotogramma migliore per la copertina")
    iv = info_video(BASE / piano["sorgente"])
    if piano["inquadratura"]["modalita"] == "sfocato":
        vf = filtro_base(iv, piano["inquadratura"], "[0:v]", "")
    else:
        vf = filtro_base(iv, piano["inquadratura"], "", "")
    cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    occhi = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    migliore = (-1, None, None)
    for k in range(24):
        t = piano["durata"] * (0.05 + 0.9 * k / 23)
        if piano["inquadratura"]["modalita"] == "sfocato":
            cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", piano["sorgente"], "-frames:v", "1",
                   "-filter_complex", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            buf = subprocess.run(cmd, capture_output=True, cwd=BASE).stdout
            fr = np.frombuffer(buf[:W * H * 3], np.uint8).reshape(H, W, 3) if len(buf) >= W * H * 3 else None
        else:
            fr = frame_da_video(piano["sorgente"], t, vf, W, H)
        if fr is None:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY)
        nitidezza = cv2.Laplacian(g, cv2.CV_64F).var()
        facce = cascata.detectMultiScale(g, 1.1, 5, minSize=(100, 100))
        punteggio = min(nitidezza, 400) / 400
        cy = None
        if len(facce):
            x, y, w, h = max(facce, key=lambda f: f[2] * f[3])
            punteggio += 1.5 + (w * h) / (W * H) * 4
            n_occhi = len(occhi.detectMultiScale(g[y:y + h // 2 + h // 6, x:x + w], 1.1, 6))
            punteggio += 1.0 if n_occhi >= 2 else 0          # occhi aperti
            cy = y + h / 2
        if punteggio > migliore[0]:
            migliore = (punteggio, fr, cy)
    _, fr, cy = migliore
    img = Image.fromarray(fr).convert("RGBA")
    titolo_in_basso = cy is None or cy < H * 0.5
    # sfumatura scura dietro il titolo
    grad = Image.new("L", (1, H))
    for y in range(H):
        p = (y - H * 0.45) / (H * 0.55) if titolo_in_basso else (H * 0.55 - y) / (H * 0.55)
        grad.putpixel((0, y), int(200 * clamp(p, 0, 1) ** 1.3))
    nero = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    nero.putalpha(grad.resize((W, H)))
    img.alpha_composite(nero)
    # titolo grande: prima parte bianca, dopo i ":" nel colore di evidenziazione
    ft = fonts["titolo"]["path"]
    testo = TITOLO.upper()
    bw = SAFE[2] - SAFE[0]
    ris = None
    for max_righe, px_min in ((2, 84), (3, 72), (4, 56)):      # meno righe possibile, ma testo grande
        ris = adatta_testo(ft, testo, bw - 2 * 40, 470, 128, px_min, max_righe, interlinea=1.04)
        if ris:
            break
    f, righe, passo, top, alt = ris
    bh = int(alt + 2 * 44)
    by = SAFE[3] - 40 - bh if titolo_in_basso else SAFE[1] + 30
    pann = Image.new("RGBA", (bw, bh), (*hex_rgb(COLORE_PRINCIPALE), 235))
    img.paste(pann, (SAFE[0], by), maschera_arrotondata(bw, bh, 22))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((SAFE[0] + 40, by - 10, SAFE[0] + 200, by + 4), radius=7, fill=hex_rgb(COLORE_EVIDENZIAZIONE))
    gialla = False
    y0 = by + 44 - top
    for k, r in enumerate(righe):
        # colora in giallo le parole dopo i due punti
        parole = r.split(" ")
        larg = f.getlength(r)
        x = W / 2 - larg / 2
        for j, p in enumerate(parole):
            col = hex_rgb(COLORE_EVIDENZIAZIONE) if gialla else (255, 255, 255)
            d.text((x, y0 + k * passo), p, font=f, fill=col, anchor="ls")
            x += f.getlength(p + " ")
            if p.endswith(":"):
                gialla = True
    img.convert("RGB").save(dest, quality=92)


# =====================================================================
#  MAIN
# =====================================================================
def trova_sorgente(arg):
    if arg or FILE_SORGENTE:
        p = Path(arg or FILE_SORGENTE)
        p = p if p.is_absolute() else BASE / p
        if not p.exists():
            sys.exit(f"File sorgente non trovato: {p}")
        return p
    cand = sorted(f for f in (BASE / "input").glob("*") if f.suffix.lower() in VIDEO_EXT) \
        if (BASE / "input").exists() else []
    if not cand:
        sys.exit("Nessun video in ./input/ — copia lì il file .mp4 e rilancia.")
    return cand[0]


def main():
    global BASE, TITOLO, TICKER
    ap = argparse.ArgumentParser(description="Montaggio automatico per il feed Facebook (4:5)")
    ap.add_argument("--file")
    ap.add_argument("--titolo")
    ap.add_argument("--ticker")
    ap.add_argument("--render", action="store_true", help="anteprima + video completo + controlli + copertina")
    ap.add_argument("--anteprima", action="store_true", help="solo anteprima 30 s")
    ap.add_argument("--ripianifica", action="store_true")
    ap.add_argument("--ritrascrivi", action="store_true")
    ap.add_argument("--base")
    a = ap.parse_args()
    if a.base:
        BASE = Path(a.base).resolve()
    TITOLO = a.titolo or TITOLO
    TICKER = a.ticker or TICKER

    assicura_dipendenze()
    for d in ("input", "immagini", "immagini/auto", "output"):
        (BASE / d).mkdir(parents=True, exist_ok=True)
    fonts = prepara_font()
    src = trova_sorgente(a.file)
    nome = src.stem
    iv = info_video(src)
    if not iv["audio"]:
        sys.exit("Il video non ha una traccia audio: serve il parlato per sottotitoli e immagini.")
    print(f"Sorgente: {src.name}  {iv['w']}x{iv['h']}  {fmt_t(iv['durata'])}")

    f_tr = BASE / "output" / "trascrizione.json"
    trascr = json.loads(f_tr.read_text(encoding="utf-8")) if f_tr.exists() and not a.ritrascrivi else None
    if trascr is None or abs(trascr.get("durata", 0) - iv["durata"]) > 0.5:
        trascr = trascrivi(src, iv["durata"])
    f_piano = BASE / "output" / "piano_montaggio.json"
    piano = json.loads(f_piano.read_text(encoding="utf-8")) if f_piano.exists() else None
    if piano is None or a.ripianifica or a.ritrascrivi or piano.get("sorgente") != str(src.relative_to(BASE)):
        piano = crea_piano(src, iv, trascr, fonts)

    if not (a.render or a.anteprima):
        mostra_piano(piano)
        print("Piano salvato in output/piano_montaggio.json (modificabile) e output/piano_montaggio.md.")
        print("Controlla anche output/anteprima_immagini.jpg. Quando va bene:  python monta_facebook.py --render")
        return

    # sottotitoli: genera ASS e controlla i margini prima di renderizzare (si corregge da solo)
    ass_rel = "output/sottotitoli.ass"
    mis_px = piano["sottotitoli_px"]
    for tentativo in range(6):
        genera_ass(piano, fonts, BASE / ass_rel)
        problemi, unione = verifica_ass(ass_rel, piano["durata"])
        if not problemi:
            print(f"→ Sottotitoli dentro la zona {SUB_ZONA[0]}–{SUB_ZONA[1]} e i margini (ingombro max {unione})")
            break
        print(f"   ! {len(problemi)} campioni di sottotitoli fuori zona (es. t={problemi[0][0]:.1f}s "
              f"bbox={problemi[0][1]}): riduco e ridispongo")
        global SUB_MAX_CARATTERI
        if mis_px - 2 >= SUB_FONT_PX_MIN:
            mis_px -= 2
        else:
            SUB_MAX_CARATTERI -= 2
        parole = [p for b in piano["sottotitoli"] for p in b["parole"]]
        blocchi = crea_blocchi(parole, Misuratore(fonts["sottotitoli"]["path"], mis_px), piano["durata"])
        piano["sottotitoli"] = [{"inizio": b["inizio"], "fine": b["fine"], "righe": b["righe"],
                                 "parole": b["parole"]} for b in blocchi]
        piano["sottotitoli_px"], piano["sottotitoli_max_caratteri"] = mis_px, SUB_MAX_CARATTERI
        salva_piano(piano)

    out_dir = BASE / "output"
    esporta_srt(piano, out_dir / f"{nome}_FACEBOOK_4x5.it_IT.srt")
    anteprima = out_dir / f"{nome}_anteprima_30s.mp4"
    viol = renderizza(piano, fonts, ass_rel, anteprima, anteprima=True)
    print(f"✓ Anteprima: {anteprima.relative_to(BASE)}")
    if not a.render:
        return
    finale = out_dir / f"{nome}_FACEBOOK_4x5.mp4"
    viol = renderizza(piano, fonts, ass_rel, finale, anteprima=False)
    ok = controlla_risultato(piano, finale, trascr, viol)
    copertina = out_dir / f"{nome}_copertina.jpg"
    crea_copertina(piano, fonts, copertina)
    print(f"✓ Video:      {finale.relative_to(BASE)}")
    print(f"✓ Copertina:  {copertina.relative_to(BASE)}")
    print(f"✓ Sottotitoli per Facebook: output/{nome}_FACEBOOK_4x5.it_IT.srt")
    print("✓ Crediti:    output/crediti.txt")
    if not ok:
        print("! Alcuni controlli non sono passati: vedi output/controllo/report.txt")


if __name__ == "__main__":
    main()
