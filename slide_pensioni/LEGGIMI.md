# Slide ricalcolo pensioni INPS ed ex INPDAP (Studio Legale Solimando)

- `slide/slide_pensioni_con_voce.mp4` – 5 slide 16:9 con voce femminile ("Paola"), 43 s, -14 LUFS.
- `slide/slide_pensioni.pdf` e `slide/slide_01.png` … `slide_05.png` – le slide.
- `logo_studio_bianco.png` – logo testuale (bilancia + STUDIO LEGALE SOLIMANDO), generato dallo script.
- `immagini/copertina.jpg` – foto di copertina generata con Gamma.

Rigenera (anno, email e link sono in cima a `crea_slide.py`; testi della voce in `voce_sintetica.py`):

    python slide_pensioni/crea_slide.py --font-dir <cartella Montserrat-Black/ExtraBold/Bold.ttf> --out slide_pensioni/slide
    python slide_pensioni/voce_sintetica.py --modello <vits-piper-it_IT-paola-medium> --out slide_pensioni/voce
    python slide_evento/video_con_voce.py --slide-dir slide_pensioni/slide --voce-dir slide_pensioni/voce \
        --out slide_pensioni/slide/slide_pensioni_con_voce.mp4
