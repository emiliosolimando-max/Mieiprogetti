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
0. Archivia il lavoro precedente: sposta `input/*` e `output/*` in `archivio/<nome video precedente>/`.
1. Copia il video in `input/` (togli eventuali video precedenti) e aggiorna in cima allo script `TITOLO`,
   `TICKER`, `CHIUSURA_TITOLO`, `CHIUSURA_TESTO`. In alternativa usa `--titolo` / `--ticker`.
2. `python monta_facebook.py --ripianifica --ritrascrivi` trascrive, crea il piano e mostra la tabella.
   - In questo ambiente cloud HuggingFace è bloccato: faster-whisper fallisce e lo script passa da solo a
     **sherpa-onnx + Whisper turbo**, che scarica dalle release GitHub di k2-fsa in `modelli/`.
     Il programma che trascrive c'è: non dire mai all'utente che non puoi fare i sottotitoli.
   - **Rileggi la trascrizione** e correggi a mano in `output/trascrizione.json` gli errori evidenti
     (es. "IMS" → INPS, "IMSDAP" → INPDAP, "quescenza" → quiescenza), aggiungi la punteggiatura mancante,
     poi rigenera il piano con `--ripianifica`. Le correzioni ricorrenti vanno in `CORREZIONI` dello script.
3. **Prima del montaggio mostra il testo completo e aspetta l'ok** (l'ha chiesto esplicitamente):
   - prepara `output/trascrizione_parola_per_parola.md` (ogni parola con inizio e fine) e mandalo;
   - segnala le parole dubbie, soprattutto i nomi. Per trovarle trascrivi anche con Whisper "small" e con
     turbo senza timestamp e confronta i tre risultati: dove non coincidono, la parola è dubbia;
   - dopo l'ok rivedi il piano: assicurati che ci siano i numeri chiave (anni, importi, "DAL 2007") e il tema
     principale. Le etichette delle card vanno nel campo `etichetta` del piano (es. "EX INPDAP"), poi
     rigenera le grafiche con `genera_grafica`. L'utente vuole un'immagine per ogni concetto detto.
4. `python monta_facebook.py --render` produce anteprima, video finale, controlli e copertina.
   Guarda `output/controllo/provino_6_fotogrammi.jpg` e `cartello_finale.jpg` prima di consegnare.
5. Consegna con SendUserFile: `output/<nome>_FACEBOOK_4x5.mp4`, `output/<nome>_copertina.jpg`
   (è l'"immagine ferma" del post, cioè la miniatura) e il `.it_IT.srt`. Segnala le parole dubbie.

## Preferenze dell'utente (già impostate nello script; le più recenti valgono di più)
- Formato feed 1080x1350 (4:5). Testo che scorre in basso.
- **Scritta fissa sempre sopra la testa, mai sul viso**: `TITOLO = "OCCHIELLO | testo"`. L'occhiello va in
  giallo (es. "NOVITÀ PENSIONI"), il resto in bianco. Lo script controlla che la scritta non tocchi la testa;
  se servisse, rimpicciolisce un po' il video.
- **Sottotitoli: 1–3 parole alla volta, grandi (84 px), bianchi, ben evidenti** (`SUB_STILE = "parole"`).
  Lo stile precedente, 2 righe con la parola in giallo, si chiama `"frasi"`.
- Immagini quando pronuncia le parole chiave, **accanto alla figura** (`DISPOSIZIONE = "accanto"`):
  lo speaker si sposta di lato al 86% e la card verticale va nello spazio libero. Non devono mai coprire
  il viso. `"sopra_testa"` (card sopra la testa) va bene per i primi piani stretti, dove ai lati non c'è
  spazio. Senza foto (niente Pexels qui) lo script genera grafiche con icona + parola chiave.
- Cartello finale con invito all'azione, più 2 s di fotogramma fermo in coda. In "accanto" è una card larga
  sotto il viso, che compare quando ha finito di parlare. Contatti usati nei video:
  solimandoemilio@libero.it, oppure "scrivi nei commenti".
- Colori: blu #0B3D91 e giallo #FFD400, font Montserrat (ExtraBold per i titoli, SemiBold per i sottotitoli).
- Audio normalizzato a -14 LUFS.
