#!/usr/bin/env python3
"""Slide 16:9 sul ricalcolo delle pensioni INPS ed ex INPDAP (Studio Legale Solimando), con voce fuori campo.
Riusa lo stile delle slide dell'evento NPL (slide_evento/crea_slide.py) con i colori dei video pensioni.

Uso: python slide_pensioni/crea_slide.py --font-dir DIR --out slide_pensioni/slide
Produce logo, slide_01.png … , slide_pensioni.pdf. Il video con voce si fa poi con slide_evento/video_con_voce.py."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parent / "slide_evento"))
sys.path.insert(0, str(QUI.parent))
import crea_slide as cs  # noqa: E402
from monta_facebook import _disegna_icona  # noqa: E402

cs.BLU = (11, 61, 145)      # #0B3D91, il blu dei video pensioni
cs.BLU2 = (25, 82, 178)
BLU, BLU2, BIANCO, GIALLO, ROSSO = cs.BLU, cs.BLU2, cs.BIANCO, cs.GIALLO, cs.ROSSO
W, H = cs.W, cs.H
font, badge, scrivi, testo_adatto, a_capo, elenco = (cs.font, cs.badge, cs.scrivi, cs.testo_adatto, cs.a_capo,
                                                     cs.elenco)

ANNO = "2007"
EMAIL = "solimandoemilio@libero.it"
LINK = "verifica-pensione-difesa.lovable.app"
URL_QR = "https://verifica-pensione-difesa.lovable.app/?utm_source=video_slide_pensioni"


def crea_logo(fd, dest):
    """Logo testuale bianco: bilancia + STUDIO LEGALE / SOLIMANDO."""
    im = Image.new("RGBA", (1100, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    _disegna_icona(d, "bilancia", 105, 120, 95, BIANCO, GIALLO)
    d.line((225, 25, 225, 205), fill=GIALLO, width=6)
    d.text((255, 30), "STUDIO LEGALE", font=font(fd, "ExtraBold", 58), fill=BIANCO)
    d.text((250, 92), "SOLIMANDO", font=font(fd, "Black", 104), fill=BIANCO)
    im = im.crop(im.getbbox())
    im.save(dest)
    return dest


def slide_copertina(fd, img, logo):
    tela = cs.base_con_immagine(img, logo, 0.58)
    d = ImageDraw.Draw(tela)
    x, larg = 90, int(W * 0.58) - 280
    y = badge(d, (x, 230), "PENSIONI INPS ED EX INPDAP", font(fd, "Black", 46), GIALLO, BLU) + 44
    f, r = testo_adatto(d, "RICALCOLO DELLA PENSIONE", fd, "Black", 128, 90, larg, 2)
    y = scrivi(d, (x, y), r, f, BIANCO, 1.02) + 24
    f2, r2 = testo_adatto(d, f"Sei in pensione dal {ANNO} in poi?", fd, "Black", 72, 54, larg, 2)
    scrivi(d, (x, y), r2, f2, GIALLO)
    return tela


def slide_icona(fd, logo, titolo, voci, icona, nota=None, px=66):
    tela = Image.new("RGB", (W, H), BLU)
    d = ImageDraw.Draw(tela)
    cs.metti_logo(tela, logo, 70, 45, 440)
    d.ellipse((1250, 230, 1810, 790), fill=BLU2)
    _disegna_icona(d, icona, 1530, 510, 200, BIANCO, GIALLO)
    x, larg = 90, 1080
    f, r = testo_adatto(d, titolo, fd, "Black", 112, 78, larg, 2)
    y = scrivi(d, (x, 250), r, f, BIANCO, 1.02) + 40
    y = elenco(d, x, y, voci, fd, px, larg)
    if nota:
        badge(d, (x, y + 10), nota, font(fd, "Black", 48), GIALLO, BLU)
    return tela


def slide_finale(fd, logo, qr_png):
    tela = Image.new("RGB", (W, H), BLU)
    d = ImageDraw.Draw(tela)
    cs.metti_logo(tela, logo, (W - 480) // 2, 40, 480)
    f = font(fd, "Black", 84)
    for k, t in enumerate(("VUOI SAPERE SE RIENTRI", "ANCHE TU?")):
        d.text(((W - d.textlength(t, font=f)) / 2, 200 + k * 92), t, font=f, fill=BIANCO if k == 0 else GIALLO)
    qr = Image.open(qr_png).convert("RGB").resize((330, 330), Image.NEAREST)
    bx, by = 250, 470
    d.rounded_rectangle((bx - 20, by - 20, bx + 350, by + 350), radius=24, fill=BIANCO)
    tela.paste(qr, (bx, by))
    fs, fl = font(fd, "ExtraBold", 46), font(fd, "Black", 50)
    x = 680
    d.text((x, 470), "Scrivi un'email a:", font=fs, fill=BIANCO)
    d.rounded_rectangle((x - 10, 535, x + d.textlength(EMAIL, font=fl) + 30, 620), radius=18, fill=GIALLO)
    d.text((x + 10, 547), EMAIL, font=fl, fill=BLU)
    d.text((x, 650), "oppure inquadra il QR code o vai su:", font=fs, fill=BIANCO)
    fl2 = font(fd, "Black", 46)
    d.rounded_rectangle((x - 10, 715, x + d.textlength(LINK, font=fl2) + 30, 800), radius=18, fill=BIANCO)
    d.text((x + 10, 728), LINK, font=fl2, fill=BLU)
    f3 = font(fd, "ExtraBold", 44)
    t3 = "Sarai contattato secondo la priorità acquisita"
    d.text(((W - d.textlength(t3, font=f3)) / 2, 900), t3, font=f3, fill=GIALLO)
    fa = font(fd, "Bold", 26)
    nota = "Ogni posizione va verificata caso per caso: l'esito dipende dalla singola pensione."
    d.text(((W - d.textlength(nota, font=fa)) / 2, H - 70), nota, font=fa, fill=(201, 214, 240))
    return tela


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fd, out = a.font_dir, Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    logo = QUI / "logo_studio.png"          # logo vero dello Studio, ritagliato senza sfondo
    if not logo.exists():
        logo = crea_logo(fd, QUI / "logo_provvisorio.png")
    import qrcode
    qrcode.make(URL_QR, border=1, box_size=10).save(out / "_qr.png")
    slide = [
        slide_copertina(fd, QUI / "immagini" / "copertina.jpg", logo),
        slide_icona(fd, logo, "CONTROLLIAMO LA TUA PENSIONE",
                    [f"Per chi è in pensione dal {ANNO} in poi", "Pensioni INPS ed ex INPDAP",
                     "Verifichiamo se va ricalcolata"], "lente"),
        slide_icona(fd, logo, "MIGLIAIA DI PENSIONATI",
                    ["In tutta Italia", "Hanno già ottenuto il ricalcolo"], "persone"),
        slide_icona(fd, logo, "COSA HANNO OTTENUTO",
                    ["Un aumento mensile della pensione", "Per tutta la vita", "Più gli arretrati"], "euro",
                    nota="VITA NATURAL DURANTE"),
        slide_finale(fd, logo, out / "_qr.png"),
    ]
    for k, s in enumerate(slide, 1):
        s.save(out / f"slide_{k:02d}.png", optimize=True)
    slide[0].save(out / "slide_pensioni.pdf", save_all=True, append_images=slide[1:], resolution=150)
    print("ok", len(slide), "slide")


if __name__ == "__main__":
    main()
