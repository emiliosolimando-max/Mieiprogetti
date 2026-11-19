#!/usr/bin/env python3
"""Slide 16:9 per il video dell'evento NPL gratuito (da proiettare in TV e riprendere).
Caratteri molto spessi (Montserrat Black/ExtraBold), logo Solimando Real Estate, immagini per ogni forma di
investimento, ultima slide con link e QR code alla landing.

Uso: python crea_slide.py --font-dir DIR --img-dir DIR --logo PNG --out DIR
Produce slide_01.png … slide_09.png, slide_evento.pdf e slide_evento_90s.mp4 (10 s per slide)."""
import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
BLU = (10, 26, 79)
BLU2 = (19, 41, 110)
BIANCO = (255, 255, 255)
GIALLO = (255, 212, 0)
ROSSO = (214, 40, 40)
LINK = "evento-immobili-banche.lovable.app"
URL_QR = "https://evento-immobili-banche.lovable.app/?utm_source=video_slide"
DURATA = 10  # secondi per slide (9 slide = 90 s)


def font(dir_, peso, px):
    return ImageFont.truetype(str(Path(dir_) / f"Montserrat-{peso}.ttf"), px)


def copri(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def a_capo(d, testo, f, larghezza):
    righe, cur = [], ""
    for p in testo.split():
        prova = (cur + " " + p).strip()
        if d.textlength(prova, font=f) <= larghezza or not cur:
            cur = prova
        else:
            righe.append(cur)
            cur = p
    righe.append(cur)
    return righe


def testo_adatto(d, testo, fd, peso, px_max, px_min, larghezza, max_righe):
    for px in range(px_max, px_min - 1, -2):
        f = font(fd, peso, px)
        r = a_capo(d, testo, f, larghezza)
        if len(r) <= max_righe:
            return f, r
    f = font(fd, peso, px_min)
    return f, a_capo(d, testo, f, larghezza)


def scrivi(d, xy, righe, f, colore, interlinea=1.08):
    x, y = xy
    for r in righe:
        d.text((x, y), r, font=f, fill=colore)
        y += f.size * interlinea
    return y


def base_con_immagine(img_path, logo, lato_testo=0.54):
    """Sfondo blu a sinistra, immagine a destra sfumata verso il blu."""
    tela = Image.new("RGB", (W, H), BLU)
    xi = int(W * lato_testo) - 140
    foto = copri(Image.open(img_path).convert("RGB"), W - xi, H)
    tela.paste(foto, (xi, 0))
    sfuma = Image.new("L", (W - xi, H), 0)
    ds = ImageDraw.Draw(sfuma)
    for x in range(300):
        ds.line((x, 0, x, H), fill=int(255 * (1 - x / 300) ** 1.4))
    tela.paste(Image.new("RGB", (W - xi, H), BLU), (xi, 0), sfuma)
    metti_logo(tela, logo, 70, 50, 380)
    return tela


def metti_logo(tela, logo, x, y, larghezza):
    lg = Image.open(logo).convert("RGBA")
    lg = lg.resize((larghezza, round(lg.height * larghezza / lg.width)), Image.LANCZOS)
    tela.paste(lg, (x, y), lg)


def badge(d, xy, testo, f, fondo, colore, pad=(26, 12), raggio=14):
    x, y = xy
    w = d.textlength(testo, font=f)
    a = f.getbbox(testo)
    h = a[3] - a[1]
    d.rounded_rectangle((x, y, x + w + 2 * pad[0], y + h + 2 * pad[1] + 8), radius=raggio, fill=fondo)
    d.text((x + pad[0], y + pad[1] - a[1] + 4), testo, font=f, fill=colore)
    return y + h + 2 * pad[1] + 8


def elenco(d, x, y, voci, fd, px, larghezza, colore=BIANCO, punto=GIALLO, passo=1.5):
    f = font(fd, "Black", px)
    for v in voci:
        avviso = v.startswith("!")
        v = v.lstrip("!")
        d.ellipse((x, y + px * 0.28, x + px * 0.5, y + px * 0.78), fill=ROSSO if avviso else punto)
        righe = a_capo(d, v, f, larghezza - px)
        y = scrivi(d, (x + px * 0.9, y), righe, f, GIALLO if avviso else colore) + px * (passo - 1.08)
    return y


def slide_forma(fd, img, logo, numero, titolo, sottotitolo, voci):
    tela = base_con_immagine(img, logo)
    d = ImageDraw.Draw(tela)
    x, larg = 90, int(W * 0.54) - 180
    y = 230
    y = badge(d, (x, y), f"FORMA {numero} DI 4", font(fd, "Black", 40), GIALLO, BLU) + 34
    f, r = testo_adatto(d, titolo, fd, "Black", 118, 80, larg, 2)
    y = scrivi(d, (x, y), r, f, BIANCO, 1.02) + 16
    if sottotitolo:
        f2, r2 = testo_adatto(d, sottotitolo, fd, "ExtraBold", 54, 40, larg, 2)
        y = scrivi(d, (x, y), r2, f2, GIALLO) + 30
    else:
        y += 20
    for px in range(54, 39, -2):               # l'elenco deve restare almeno 70 px sopra il bordo (TV)
        prova = tela.copy()
        if elenco(ImageDraw.Draw(prova), x, y, voci, fd, px, larg) <= H - 70:
            return prova
    return prova


def slide_copertina(fd, img, logo):
    tela = base_con_immagine(img, logo, 0.58)
    d = ImageDraw.Draw(tela)
    x, larg = 90, int(W * 0.58) - 170
    y = badge(d, (x, 220), "EVENTO GRATUITO ONLINE", font(fd, "Black", 46), GIALLO, BLU) + 40
    f, r = testo_adatto(d, "Come acquistare immobili a sconto direttamente dalle banche", fd, "Black", 104, 76, larg, 4)
    y = scrivi(d, (x, y), r, f, BIANCO, 1.03) + 10
    f2, r2 = testo_adatto(d, "prima che vadano in asta", fd, "Black", 84, 60, larg, 1)
    y = scrivi(d, (x, y), r2, f2, GIALLO) + 40
    badge(d, (x, y), "ATTENZIONE: NON È SALDO E STRALCIO", font(fd, "Black", 44), ROSSO, BIANCO)
    return tela


def slide_quattro(fd, imgs, logo):
    tela = Image.new("RGB", (W, H), BLU)
    d = ImageDraw.Draw(tela)
    metti_logo(tela, logo, 70, 50, 380)
    f = font(fd, "Black", 92)
    t = "4 MODI PER INVESTIRE NEGLI IMMOBILI"
    r = a_capo(d, t, f, W - 200)
    y = 190
    for riga in r:
        d.text(((W - d.textlength(riga, font=f)) / 2, y), riga, font=f, fill=BIANCO)
        y += 98
    y += 30
    cw, ch, gap = 410, 520, 40
    x0 = (W - (4 * cw + 3 * gap)) // 2
    voci = [("1", "FLIPPING", imgs[0]), ("2", "ASTA GIUDIZIARIA", imgs[1]),
            ("3", "SALDO E STRALCIO", imgs[2]), ("4", "METODO «BLINDATO»", imgs[3])]
    fn, fl = font(fd, "Black", 58), font(fd, "Black", 42)
    for k, (n, nome, img) in enumerate(voci):
        x = x0 + k * (cw + gap)
        evid = k == 3
        d.rounded_rectangle((x - 6, y - 6, x + cw + 6, y + ch + 6), radius=30, fill=GIALLO if evid else BLU2)
        foto = copri(Image.open(img).convert("RGB"), cw, 300)
        m = Image.new("L", (cw, 300), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, cw, 330), radius=26, fill=255)
        tela.paste(foto, (x, y), m)
        d.rectangle((x, y + 300, x + cw, y + ch), fill=GIALLO if evid else BLU2)
        d.rounded_rectangle((x, y + ch - 40, x + cw, y + ch), radius=26, fill=GIALLO if evid else BLU2)
        col = BLU if evid else BIANCO
        d.ellipse((x + 24, y + 324, x + 104, y + 404), fill=BLU if evid else GIALLO)
        d.text((x + 64, y + 364), n, font=fn, fill=GIALLO if evid else BLU, anchor="mm")
        rr = a_capo(d, nome, fl, cw - 48)
        yy = y + 420
        for riga in rr:
            d.text((x + 24, yy), riga, font=fl, fill=col)
            yy += 48
    return tela


def disegna_monitor(d, cx, cy, s):
    d.rounded_rectangle((cx - s, cy - s * .62, cx + s, cy + s * .5), radius=s * .08, fill=BIANCO)
    d.rounded_rectangle((cx - s * .9, cy - s * .52, cx + s * .9, cy + s * .4), radius=s * .05, fill=BLU2)
    for k, (lw, col) in enumerate(((.7, GIALLO), (1.3, BIANCO), (1.0, BIANCO), (1.2, BIANCO), (.8, BIANCO))):
        yy = cy - s * .38 + k * s * .16
        d.rounded_rectangle((cx - s * .75, yy, cx - s * .75 + s * lw, yy + s * .07), radius=s * .03, fill=col)
    d.rectangle((cx - s * .12, cy + s * .5, cx + s * .12, cy + s * .78), fill=BIANCO)
    d.rounded_rectangle((cx - s * .5, cy + s * .76, cx + s * .5, cy + s * .88), radius=s * .05, fill=BIANCO)
    d.ellipse((cx + s * .45, cy - s * .2, cx + s * .95, cy + s * .3), fill=GIALLO)
    d.ellipse((cx + s * .56, cy - s * .09, cx + s * .84, cy + s * .19), outline=BLU, width=int(s * .06))
    d.line((cx + s * .8, cy + s * .15, cx + s * .98, cy + s * .33), fill=BLU, width=int(s * .08))


def disegna_persone(d, cx, cy, s):
    for dx, sc, col in ((-0.62, .8, BIANCO), (0.62, .8, BIANCO), (0, 1, GIALLO)):
        x = cx + s * dx
        r = s * .26 * sc
        d.ellipse((x - r, cy - s * .55 * sc - r, x + r, cy - s * .55 * sc + r), fill=col)
        d.pieslice((x - s * .48 * sc, cy - s * .18 * sc, x + s * .48 * sc, cy + s * .95 * sc), 180, 360, fill=col)


def slide_icona(fd, logo, titolo, voci, disegno, nota=None):
    tela = Image.new("RGB", (W, H), BLU)
    d = ImageDraw.Draw(tela)
    metti_logo(tela, logo, 70, 50, 380)
    d.ellipse((1250, 220, 1810, 780), fill=BLU2)
    disegno(d, 1530, 500, 230)
    x, larg = 90, 1080
    f, r = testo_adatto(d, titolo, fd, "Black", 112, 80, larg, 2)
    y = scrivi(d, (x, 230), r, f, BIANCO, 1.02) + 40
    y = elenco(d, x, y, voci, fd, 64, larg)
    if nota:
        badge(d, (x, y + 10), nota, font(fd, "Black", 46), GIALLO, BLU)
    return tela


def slide_finale(fd, logo, qr_png):
    tela = Image.new("RGB", (W, H), BLU)
    d = ImageDraw.Draw(tela)
    metti_logo(tela, logo, (W - 420) // 2, 50, 420)
    y = badge(d, (0, 0), " ", font(fd, "Black", 10), BLU, BLU)  # misura fittizia
    fb = font(fd, "Black", 52)
    t = "EVENTO GRATUITO ONLINE"
    wb = d.textlength(t, font=fb) + 52
    badge(d, ((W - wb) / 2, 210), t, fb, GIALLO, BLU)
    f = font(fd, "Black", 118)
    t2 = "REGISTRATI ORA"
    d.text(((W - d.textlength(t2, font=f)) / 2, 315), t2, font=f, fill=BIANCO)
    f3 = font(fd, "ExtraBold", 52)
    t3 = "Su Google Meet · Posti limitati"
    d.text(((W - d.textlength(t3, font=f3)) / 2, 460), t3, font=f3, fill=GIALLO)
    # QR + link
    qr = Image.open(qr_png).convert("RGB").resize((330, 330), Image.NEAREST)
    bx, by = 330, 570
    d.rounded_rectangle((bx - 20, by - 20, bx + 350, by + 350), radius=24, fill=BIANCO)
    tela.paste(qr, (bx, by))
    fl = font(fd, "Black", 50)
    d.text((760, 610), "Inquadra il QR code", font=font(fd, "ExtraBold", 46), fill=BIANCO)
    d.text((760, 680), "oppure vai su:", font=font(fd, "ExtraBold", 46), fill=BIANCO)
    d.rounded_rectangle((750, 760, 760 + d.textlength(LINK, font=fl) + 40, 850), radius=18, fill=BIANCO)
    d.text((780, 774), LINK, font=fl, fill=BLU)
    fa = font(fd, "Bold", 26)
    nota = ("Evento a finalità informative e formative. Le operazioni immobiliari sono attività di investimento "
            "e comportano rischi; i risultati non sono garantiti.")
    rr = a_capo(d, nota, fa, W - 240)
    yy = H - 40 - len(rr) * 32
    for riga in rr:
        d.text(((W - d.textlength(riga, font=fa)) / 2, yy), riga, font=fa, fill=(201, 210, 236))
        yy += 32
    return tela


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-dir", required=True)
    ap.add_argument("--img-dir", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fd, im, out = a.font_dir, Path(a.img_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    import qrcode
    qrcode.make(URL_QR, border=1, box_size=10).save(out / "_qr.png")
    imgs = [im / "flipping.jpg", im / "asta.jpg", im / "saldo_stralcio.jpg", im / "blindato.jpg"]
    slide = [
        slide_copertina(fd, imgs[3], a.logo),
        slide_quattro(fd, imgs, a.logo),
        slide_forma(fd, imgs[0], a.logo, 1, "FLIPPING", "Compri, ristrutturi, rivendi",
                    ["Servono capitali importanti", "Cantiere, tempi e imprevisti", "Il margine dipende dal mercato"]),
        slide_forma(fd, imgs[1], a.logo, 2, "ASTA GIUDIZIARIA", "Partecipi alla vendita del tribunale",
                    ["Tempi lunghi della procedura", "Concorrenza e rilanci", "Immobile spesso da liberare"]),
        slide_forma(fd, imgs[2], a.logo, 3, "SALDO E STRALCIO", "Tratti il debito con la banca",
                    ["La banca non sempre accetta", "Esito incerto", "!NON è il nostro metodo"]),
        slide_forma(fd, imgs[3], a.logo, 4, "IL METODO «BLINDATO»", "Contatti direttamente il creditore",
                    ["Prima che l'immobile vada in asta", "Procedura legale e collaudata", "Immobili a forte sconto"]),
        slide_icona(fd, a.logo, "DOVE SONO QUESTI IMMOBILI?",
                    ["NON su Immobiliare.it o Idealista", "In un GESTIONALE PRIVATO"], disegna_monitor,
                    nota="LO CONDIVIDEREMO ALL'EVENTO"),
        slide_icona(fd, a.logo, "ANCHE SE PARTI DA ZERO",
                    ["Ti supportiamo all'inizio", "Fino a quando diventi autonomo", "Collaborazioni professionali"],
                    disegna_persone),
        slide_finale(fd, a.logo, out / "_qr.png"),
    ]
    files = []
    for k, s in enumerate(slide, 1):
        p = out / f"slide_{k:02d}.png"
        s.save(p, optimize=True)
        files.append(p)
    slide[0].save(out / "slide_evento.pdf", save_all=True, append_images=slide[1:], resolution=150)
    # video: 10 s per slide con dissolvenza di 0,6 s
    n = len(files)
    ins = []
    for p in files:
        ins += ["-loop", "1", "-t", str(DURATA + 0.6), "-i", str(p)]
    fc, prev, off = "", "[0:v]", DURATA
    for k in range(1, n):
        lab = f"[x{k}]"
        fc += f"{prev}[{k}:v]xfade=transition=fade:duration=0.6:offset={off:.2f}{lab};"
        prev, off = lab, off + DURATA
    fc += f"{prev}format=yuv420p,fps=30[v]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", "-t", str(DURATA * n),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart",
                    str(out / "slide_evento_90s.mp4")], check=True)
    print("ok", n, "slide")


if __name__ == "__main__":
    main()
