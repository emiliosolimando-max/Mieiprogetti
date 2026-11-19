# Slide evento NPL gratuito (Solimando Real Estate)

- `slide/slide_evento.pdf` – le 9 slide 16:9 (1920x1080), da proiettare in TV.
- `slide/slide_evento_90s.mp4` – le stesse slide in video, 10 secondi ciascuna (90 secondi in tutto).
- `slide/slide_01.png` … `slide_09.png` – le singole slide.
- `immagini/` – le 4 foto generate con Gamma (flipping, asta giudiziaria, saldo e stralcio, metodo "blindato").

Per rigenerarle: `python slide_evento/crea_slide.py --font-dir <cartella con Montserrat-Black/ExtraBold/Bold.ttf>
--img-dir slide_evento/immagini --logo docs/evento/logo-bianco.png --out slide_evento/slide`
