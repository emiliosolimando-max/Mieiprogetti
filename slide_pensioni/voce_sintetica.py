#!/usr/bin/env python3
"""Voce fuori campo (Piper "Paola", sherpa-onnx 1.13.8) per le slide pensioni, più lenta per scandire bene.
Uso: python slide_pensioni/voce_sintetica.py --modello DIR/vits-piper-it_IT-paola-medium --out slide_pensioni/voce"""
import argparse
import json
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

LENTEZZA = 1.15   # >1 = più lenta e scandita
TESTI = [
    "Ricalcolo della pensione. Pensioni Inps, ed ex Inpdap. Sei in pensione dal duemiladiciassette in poi?",
    "Se sei in pensione dal duemiladiciassette in poi, possiamo controllare la tua pensione, Inps o ex Inpdap, "
    "per verificare se può essere ricalcolata.",
    "Sono ormai migliaia i pensionati, in tutta Italia, che hanno già ottenuto il ricalcolo.",
    "Hanno ottenuto un aumento mensile della pensione, per tutta la vita, vita natural durante. "
    "E in più, gli arretrati.",
    "Vuoi sapere se anche tu rientri in questa opportunità? Scrivi un'email a: solimando emilio, chiocciola, "
    "libero, punto, it. Oppure, clicca sul link. Sarai contattato secondo la priorità acquisita.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modello", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d, out = Path(a.modello), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(d / "it_IT-paola-medium.onnx"), tokens=str(d / "tokens.txt"),
                                                   data_dir=str(d / "espeak-ng-data"), length_scale=LENTEZZA),
        num_threads=4))
    tts = sherpa_onnx.OfflineTts(cfg)
    durate = []
    for k, t in enumerate(TESTI, 1):
        g = tts.generate(t, sid=0, speed=1.0)
        x = (np.clip(np.array(g.samples), -1, 1) * 32767).astype(np.int16)
        with wave.open(str(out / f"voce_{k:02d}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(g.sample_rate); w.writeframes(x.tobytes())
        durate.append(round(len(x) / g.sample_rate, 2))
    (out / "voce.json").write_text(json.dumps({"testi": TESTI, "durate": durate}, ensure_ascii=False), "utf-8")
    print(durate)


if __name__ == "__main__":
    main()
