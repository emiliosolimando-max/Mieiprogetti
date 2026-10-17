"""Genera un video animato con bande colorate e scritte.

Uso:
    python3 genera_video.py [output.mp4]

Richiede Pillow, numpy e ffmpeg nel PATH.
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 30
DURATA = 15  # secondi

FONT_DIR = "/usr/share/fonts/opentype/inter/"
FONT_BLACK = FONT_DIR + "Inter-Black.otf"
FONT_BOLD = FONT_DIR + "Inter-Bold.otf"
FONT_MEDIUM = FONT_DIR + "Inter-Medium.otf"

SFONDO = (14, 17, 28)
BANDE = [
    (230, 57, 70),
    (244, 162, 97),
    (233, 196, 106),
    (42, 157, 143),
    (38, 70, 83),
]
BIANCO = (255, 255, 255)

# Scene: (inizio, fine) in secondi
SCENA_TITOLO = (0.0, 5.0)
SCENA_DIAGONALI = (5.0, 10.0)
SCENA_FINALE = (10.0, 15.0)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 3 * x * x - 2 * x * x * x


def font(path, size, _cache={}):
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


def testo_centrato(draw, testo, f, y, colore=BIANCO, alpha=1.0, dx=0):
    if alpha <= 0:
        return
    bbox = draw.textbbox((0, 0), testo, font=f)
    w = bbox[2] - bbox[0]
    x = (W - w) / 2 - bbox[0] + dx
    c = tuple(int(SFONDO[i] + (colore[i] - SFONDO[i]) * alpha) for i in range(3))
    draw.text((x, y), testo, font=f, fill=c)


def scena_titolo(t):
    """Bande orizzontali che entrano da sinistra, poi compare il titolo."""
    img = Image.new("RGB", (W, H), SFONDO)
    d = ImageDraw.Draw(img)
    altezza = H / len(BANDE)
    for i, col in enumerate(BANDE):
        p = ease_out((t - i * 0.15) / 0.9)
        # le bande pari entrano da sinistra, le dispari da destra
        if i % 2 == 0:
            x0, x1 = -W + p * W, p * W
        else:
            x0, x1 = W - p * W, 2 * W - p * W
        d.rectangle([x0, i * altezza, x1, (i + 1) * altezza], fill=col)

    # banda scura centrale per il titolo
    pb = ease_out((t - 1.4) / 0.7)
    if pb > 0:
        meta = 120 * pb
        d.rectangle([0, H / 2 - meta, W, H / 2 + meta], fill=SFONDO)
        d.rectangle([0, H / 2 - meta, W, H / 2 - meta + 6], fill=BIANCO)
        d.rectangle([0, H / 2 + meta - 6, W, H / 2 + meta], fill=BIANCO)

    a = ease_out((t - 1.9) / 0.6)
    testo_centrato(d, "BENVENUTI", font(FONT_BLACK, 120), H / 2 - 95,
                   alpha=a, dx=(1 - a) * -80)
    a2 = ease_out((t - 2.5) / 0.6)
    testo_centrato(d, "un video con bande e scritte", font(FONT_MEDIUM, 36),
                   H / 2 + 45, colore=BANDE[2], alpha=a2, dx=(1 - a2) * 80)

    # uscita: le bande scorrono via verso l'alto
    uscita = ease_in_out((t - 4.4) / 0.6)
    if uscita > 0:
        arr = np.array(img)
        shift = int(uscita * H)
        arr = np.roll(arr, -shift, axis=0)
        arr[H - shift:] = SFONDO
        img = Image.fromarray(arr)
    return img


def scena_diagonali(t):
    """Strisce diagonali in movimento con scritte su bande 'sottopancia'."""
    img = Image.new("RGB", (W, H), SFONDO)
    d = ImageDraw.Draw(img)
    larghezza = 90
    offset = (t * 160) % (larghezza * len(BANDE))
    entrata = ease_out(t / 0.6)
    n = int((W + H) / larghezza) + len(BANDE) + 2
    for k in range(-len(BANDE), n):
        col = BANDE[k % len(BANDE)]
        x = k * larghezza + offset - H
        # strisce a 45 gradi, attenuate verso lo sfondo
        c = tuple(int(SFONDO[i] + (col[i] - SFONDO[i]) * 0.35 * entrata)
                  for i in range(3))
        d.polygon([(x, H), (x + larghezza, H),
                   (x + larghezza + H, 0), (x + H, 0)], fill=c)

    righe = [
        ("COLORI", BANDE[0], 0.5),
        ("MOVIMENTO", BANDE[3], 1.1),
        ("PAROLE", BANDE[1], 1.7),
    ]
    f = font(FONT_BLACK, 84)
    for idx, (parola, col, inizio) in enumerate(righe):
        p = ease_out((t - inizio) / 0.6)
        if p <= 0:
            continue
        y = 150 + idx * 150
        bbox = d.textbbox((0, 0), parola, font=f)
        tw = bbox[2] - bbox[0]
        pad = 40
        bw = (tw + 2 * pad) * p
        x0 = (W - tw) / 2 - pad
        d.rectangle([x0, y, x0 + bw, y + 120], fill=col)
        a = ease_out((t - inizio - 0.3) / 0.4)
        if a > 0:
            d.text(((W - tw) / 2 - bbox[0], y + 60 - (bbox[1] + bbox[3]) / 2),
                   parola, font=f, fill=SFONDO if a > 0.5 else col)

    # ticker in basso
    pt = ease_out((t - 2.2) / 0.5)
    if pt > 0:
        y0 = H - 60 * pt
        d.rectangle([0, y0, W, H], fill=BIANCO)
        frase = "  •  BANDE  •  SCRITTE  •  ANIMAZIONE  •  VIDEO" * 4
        ft = font(FONT_BOLD, 28)
        x = W - (t - 2.2) * 260
        d.text((x, y0 + 14), frase, font=ft, fill=SFONDO)

    uscita = ease_in_out((t - 4.4) / 0.6)
    if uscita > 0:
        d.rectangle([0, 0, W * uscita, H], fill=BANDE[4])
    return img


def scena_finale(t):
    """Bande verticali che si aprono come un sipario sul messaggio finale."""
    img = Image.new("RGB", (W, H), BANDE[4])
    d = ImageDraw.Draw(img)
    n = 10
    bw = W / n
    for i in range(n):
        p = ease_in_out((t - 0.2 - abs(i - (n - 1) / 2) * 0.08) / 0.8)
        h = H * (1 - p)
        col = BANDE[i % len(BANDE)]
        if h < 1:
            continue
        if i % 2 == 0:
            d.rectangle([i * bw, 0, (i + 1) * bw, h], fill=col)
        else:
            d.rectangle([i * bw, H - h, (i + 1) * bw, H], fill=col)

    a = ease_out((t - 1.4) / 0.7)
    testo_centrato(d, "GRAZIE", font(FONT_BLACK, 150), H / 2 - 130,
                   alpha=a)
    a2 = ease_out((t - 2.0) / 0.6)
    if a2 > 0:
        lw = 400 * a2
        d.rectangle([(W - lw) / 2, H / 2 + 50, (W + lw) / 2, H / 2 + 58],
                    fill=BANDE[2])
    a3 = ease_out((t - 2.4) / 0.6)
    testo_centrato(d, "per la visione", font(FONT_MEDIUM, 40), H / 2 + 80,
                   alpha=a3)

    # dissolvenza al nero finale
    nero = ease_in_out((t - 4.3) / 0.7)
    if nero > 0:
        arr = (np.array(img) * (1 - nero)).astype(np.uint8)
        img = Image.fromarray(arr)
    return img


def frame(t):
    for (inizio, fine), fn in (
        (SCENA_TITOLO, scena_titolo),
        (SCENA_DIAGONALI, scena_diagonali),
        (SCENA_FINALE, scena_finale),
    ):
        if inizio <= t < fine:
            return fn(t - inizio)
    return Image.new("RGB", (W, H), (0, 0, 0))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "video_bande_scritte.mp4"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-movflags", "+faststart", out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(DURATA * FPS):
        proc.stdin.write(frame(n / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"Video salvato in {out}")


if __name__ == "__main__":
    main()
