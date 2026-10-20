# Video per Facebook — come lavorare in questo progetto

L'utente pubblica video informativi (pensioni, previdenza…) sul **feed di Facebook**. Li gira da solo, in selfie
verticale, e parla in camera. Parla italiano e preferisce spiegazioni semplici, non tecniche.
Quando manda un video vuole il montaggio completo senza dover rispiegare nulla.

## Cosa mi darà a ogni video
- il file video (allegato);
- il **titolo** (es. "Come ottenere il ricalcolo della pensione");
- a volte il testo del **cartello finale** (es. "Ricalcolo delle pensioni – Chiedi anche tu il ricalcolo")
  e/o del **testo che scorre** (ticker). Se non li dà, ricavali dal titolo con lo stesso stile.

## Procedura (script `monta_facebook.py`)
1. Copia il video in `input/` (togli eventuali video precedenti) e aggiorna in cima allo script `TITOLO`,
   `TICKER`, `CHIUSURA_TITOLO`, `CHIUSURA_TESTO`. In alternativa usa `--titolo` / `--ticker`.
2. `python monta_facebook.py --ripianifica --ritrascrivi` trascrive, crea il piano e mostra la tabella.
   - In questo ambiente cloud HuggingFace è bloccato: faster-whisper fallisce e lo script passa da solo a
     **sherpa-onnx + Whisper turbo**, che scarica dalle release GitHub di k2-fsa in `modelli/`.
     Il programma che trascrive c'è: non dire mai all'utente che non puoi fare i sottotitoli.
   - **Rileggi la trascrizione** e correggi a mano in `output/trascrizione.json` gli errori evidenti
     (es. "IMS" → INPS, "IMSDAP" → INPDAP, "quescenza" → quiescenza), aggiungi la punteggiatura mancante,
     poi rigenera il piano con `--ripianifica`. Le correzioni ricorrenti vanno in `CORREZIONI` dello script.
3. Mostra il piano in breve (immagini, numeri, sottotitoli). L'utente di solito risponde "procedi":
   in quel caso renderizza subito, senza altre domande.
4. `python monta_facebook.py --render` produce anteprima, video finale, controlli e copertina.
   Guarda `output/controllo/provino_6_fotogrammi.jpg` e `cartello_finale.jpg` prima di consegnare.
5. Consegna con SendUserFile: `output/<nome>_FACEBOOK_4x5.mp4`, `output/<nome>_copertina.jpg`
   (è l'"immagine ferma" del post, cioè la miniatura) e il `.it_IT.srt`. Segnala le parole dubbie.

## Preferenze dell'utente (già impostate nello script)
- Formato feed 1080x1350 (4:5). Titolo fisso in alto per tutto il video, testo che scorre in basso.
- Sottotitoli di quello che dice, con la parola pronunciata evidenziata in giallo (karaoke).
- Immagini che compaiono quando pronuncia le parole chiave. **Non devono mai coprire il viso**:
  `DISPOSIZIONE = "sopra_testa"`. Quando compare una card, il video dello speaker si rimpicciolisce e
  scende sopra uno sfondo sfocato, e la card va sopra la testa. Senza foto (niente Pexels qui) lo script
  genera grafiche con icona + parola chiave.
- Cartello finale con invito all'azione, più 2 s di fotogramma fermo in coda.
- Colori: blu #0B3D91 e giallo #FFD400, font Montserrat (ExtraBold per i titoli, SemiBold per i sottotitoli).
- Audio normalizzato a -14 LUFS.
