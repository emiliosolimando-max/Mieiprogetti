#!/usr/bin/env python3
"""Video delle slide con voce fuori campo: ogni slide resta sullo schermo quanto il suo commento più una pausa.
Uso: python video_con_voce.py --slide-dir DIR --voce-dir DIR --out FILE.mp4
La cartella voce contiene voce_01.wav … voce_09.wav (una per slide)."""
import argparse
import json
import subprocess
import wave
from pathlib import Path

ATTACCO = 0.6      # secondi tra l'arrivo della slide e l'inizio della voce
CODA = 1.2         # pausa dopo la fine della frase
DURATA_MIN = 6.5
DISSOLVENZA = 0.5


def durata_wav(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slide-dir", required=True)
    ap.add_argument("--voce-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    slide = sorted(Path(a.slide_dir).glob("slide_[0-9][0-9].png"))
    voci = sorted(Path(a.voce_dir).glob("voce_[0-9][0-9].wav"))
    assert len(slide) == len(voci), (len(slide), len(voci))
    durate = [max(DURATA_MIN, ATTACCO + durata_wav(v) + CODA) for v in voci]
    inizi = [sum(durate[:k]) for k in range(len(durate))]
    totale = sum(durate)

    ins = []
    for p, d in zip(slide, durate):
        ins += ["-loop", "1", "-t", f"{d + DISSOLVENZA:.2f}", "-i", str(p)]
    for v in voci:
        ins += ["-i", str(v)]
    n = len(slide)
    fc, prev = "", "[0:v]"
    for k in range(1, n):
        lab = f"[x{k}]"
        fc += f"{prev}[{k}:v]xfade=transition=fade:duration={DISSOLVENZA}:offset={inizi[k]:.2f}{lab};"
        prev = lab
    fc += f"{prev}format=yuv420p,fps=30[v];"
    audio = []
    for k in range(n):
        ms = int((inizi[k] + ATTACCO) * 1000)
        fc += f"[{n + k}:a]aresample=48000,adelay={ms}|{ms}[a{k}];"
        audio.append(f"[a{k}]")
    fc += (f"{''.join(audio)}amix=inputs={n}:normalize=0,apad,atrim=0:{totale:.2f},"
           f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-t", f"{totale:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", a.out],
                   check=True)
    print(json.dumps({"durate": [round(d, 2) for d in durate], "totale": round(totale, 2)}))


if __name__ == "__main__":
    main()
