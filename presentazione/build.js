const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");
const { applyTheme } = require("/root/.claude/skills/synced/10f8318e-da67-4282-aa61-83bfde479403_d82f60da-daab-4460-b425-e7be7c049f01/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || "Claude_Code_guida.pptx";

const THEME = {
  name: "Claude Code Guida",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1F1E1D", lt1: "FFFFFF", dk2: "4A4740", lt2: "F2F0EB",
    accent1: "C96442", accent2: "2A6F6B", accent3: "D9A441",
    accent4: "5B4E8C", accent5: "8A8578", accent6: "9E3B2A",
    hlink: "2A6F6B", folHlink: "5B4E8C",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "Claude Code – Guida semplice";
pres.author = "Emilio Solimando";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

const W = 13.333, M = 0.6, CW = W - 2 * M;

// ---------- Layouts ----------
pres.defineSlideMaster({
  title: "TITOLO",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.2, w: CW, h: 1.6,
      fontFace: THEME.headFontFace, fontSize: 54, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 },
      text: "Titolo" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.0, w: CW, h: 1.2,
      fontFace: THEME.bodyFontFace, fontSize: 22, color: C.accent3, valign: "top", margin: 0 },
      text: "Sottotitolo" } },
  ],
});

pres.defineSlideMaster({
  title: "SEZIONE",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.6, w: CW, h: 1.3,
      fontFace: THEME.headFontFace, fontSize: 48, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 },
      text: "Sezione" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.05, w: CW, h: 0.9,
      fontFace: THEME.bodyFontFace, fontSize: 22, color: C.background1, valign: "top", margin: 0 },
      text: "Descrizione" } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENUTO",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.7, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.4, w: CW, h: 0.9,
      fontFace: THEME.headFontFace, fontSize: 36, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 },
      text: "Titolo" } },
    { text: { text: "Claude Code · Guida semplice", options: { x: M, y: 6.95, w: 6, h: 0.35,
      fontSize: 10, color: C.accent5, margin: 0, valign: "middle" } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 6.95, w: 0.6, h: 0.35, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------- Icons ----------
const iconCache = {};
async function icon(name, hex = "FFFFFF") {
  const key = name + hex;
  if (iconCache[key]) return iconCache[key];
  const Comp = fa[name];
  if (!Comp) throw new Error("Icona mancante: " + name);
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return (iconCache[key] = "image/png;base64," + buf.toString("base64"));
}

let objN = 0;
const nm = (s) => `${s}-${++objN}`;

async function iconCircle(slide, name, x, y, d, fill = C.accent1) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: nm("cerchio") });
  const p = d * 0.25;
  slide.addImage({ data: await icon(name), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: nm("icona") });
}

function numCircle(slide, n, x, y, d, fill = C.accent1) {
  slide.addText(String(n), { x, y, w: d, h: d, shape: pres.shapes.OVAL, fill: { color: fill },
    color: C.background1, fontSize: 20, bold: true, align: "center", valign: "middle", margin: 0,
    isTextBox: true, objectName: nm("numero") });
}

function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { type: "none" }, objectName: nm("scheda") });
}

function txt(slide, text, opts) {
  slide.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: "top", color: C.text1, fontSize: 14 }, opts,
    { objectName: nm(opts.objectName || "testo") }));
}

function bullets(items, size = 14, color = C.text1) {
  return items.map((t, i) => ({ text: t, options: { bullet: true, fontSize: size, color, paraSpaceAfter: 6,
    breakLine: i < items.length - 1 } }));
}

// Grid of icon cards: items = [{icon, title, text}]
async function iconGrid(slide, items, cols, y0, rowH, fill, big = false) {
  const gap = 0.3;
  const cw = (CW - gap * (cols - 1)) / cols;
  for (let i = 0; i < items.length; i++) {
    const r = Math.floor(i / cols), c = i % cols;
    const x = M + c * (cw + gap), y = y0 + r * (rowH + gap);
    card(slide, x, y, cw, rowH);
    const p = big ? 0.35 : 0.25, d = big ? 0.85 : 0.6, ty = big ? 1.45 : 1.0;
    await iconCircle(slide, items[i].icon, x + p, y + p, d, items[i].color || fill || C.accent1);
    txt(slide, items[i].title, { x: x + p, y: y + ty, w: cw - 2 * p, h: big ? 0.8 : 0.4, fontSize: big ? 20 : 17, bold: true,
      valign: big ? "bottom" : "top" });
    const by = ty + (big ? 0.95 : 0.42);
    txt(slide, items[i].text, { x: x + p, y: y + by, w: cw - 2 * p, h: rowH - by - 0.15, fontSize: big ? 16 : 14, color: C.text2 });
  }
}

function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENUTO", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

function divider(title, sub, section, notes) {
  pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: "SEZIONE", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  s.addText(sub, { placeholder: "body" });
  if (notes) s.addNotes(notes);
  return s;
}

(async () => {
  // ===== Apertura =====
  pres.addSection({ title: "Apertura" });
  let s = pres.addSlide({ masterName: "TITOLO", sectionTitle: "Apertura" });
  s.addText("Claude Code", { placeholder: "title" });
  s.addText("Guida semplice, passo passo, a tutto quello che puoi fare", { placeholder: "body" });
  await iconCircle(s, "FaCode", M, 1.0, 0.9, C.accent1);

  // Chat vs Code
  s = content("Due modi di usare Claude", "Apertura");
  const half = (CW - 0.4) / 2;
  const cols2 = [
    { icon: "FaComments", fill: C.accent2, title: "Claude (la chat)",
      sub: "L'amico seduto al tavolo con te: parla, spiega, scrive.",
      items: ["Domande e spiegazioni", "Email, testi e traduzioni", "Idee, consigli e riassunti"],
      rule: "Usala quando vuoi una risposta da leggere" },
    { icon: "FaLaptopCode", fill: C.accent1, title: "Claude Code",
      sub: "Lo stesso amico, ma con le mani e un computer.",
      items: ["Crea e modifica file", "Avvia programmi e controlla che funzionino", "Salva tutto su GitHub"],
      rule: "Usalo quando vuoi un file o una cosa che funziona" },
  ];
  for (let i = 0; i < 2; i++) {
    const x = M + i * (half + 0.4), y = 1.6, h = 5.0, c = cols2[i];
    card(s, x, y, half, h);
    await iconCircle(s, c.icon, x + 0.4, y + 0.4, 0.8, c.fill);
    txt(s, c.title, { x: x + 1.4, y: y + 0.45, w: half - 1.8, h: 0.7, fontSize: 24, bold: true, valign: "middle",
      fontFace: THEME.headFontFace });
    txt(s, c.sub, { x: x + 0.4, y: y + 1.45, w: half - 0.8, h: 0.6, fontSize: 16, italic: true, color: C.text2 });
    txt(s, bullets(c.items, 16), { x: x + 0.4, y: y + 2.2, w: half - 0.8, h: 1.6 });
    s.addText(c.rule, { x: x + 0.4, y: y + 3.95, w: half - 0.8, h: 0.7, fill: { color: c.fill }, color: C.background1,
      fontSize: 16, bold: true, align: "center", valign: "middle", margin: 0.1, isTextBox: true,
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.1, objectName: nm("regola") });
  }

  // Dove si apre
  s = content("Dove puoi aprire Claude Code", "Apertura");
  await iconGrid(s, [
    { icon: "FaCloud", title: "Web e app", text: "claude.ai/code dal browser o dal telefono. Lavora su un computer nella nuvola." },
    { icon: "FaDesktop", title: "App desktop", text: "L'app Claude per Mac e Windows, con il tuo computer a portata di mano." },
    { icon: "FaTerminal", title: "Terminale", text: "La finestra dei comandi: scrivi claude e premi Invio." },
    { icon: "FaPenToSquare", title: "Editor di codice", text: "Dentro VS Code e JetBrains, accanto ai tuoi file." },
  ], 4, 1.6, 3.9, C.accent1, true);
  txt(s, "È sempre lo stesso Claude: cambia solo la porta da cui entri.", { x: M, y: 5.95, w: CW, h: 0.5,
    fontSize: 18, italic: true, color: C.accent1 });

  // ===== Iniziare =====
  divider("1 · Si comincia", "Il primo progetto, passo dopo passo", "Iniziare");

  s = content("Il primo progetto in 6 passi", "Iniziare");
  const steps = [
    ["Apri claude.ai/code", "Dal browser o dall'app Claude sul telefono."],
    ["Collega GitHub", "È l'armadio online dove si salvano i tuoi progetti."],
    ["Scegli il progetto", "Seleziona il repository (per esempio Mieiprogetti)."],
    ["Scrivi cosa vuoi", "In italiano, come parleresti a una persona."],
    ["Guarda e approva", "Claude mostra cosa fa e chiede il permesso per le cose importanti."],
    ["Ricevi il risultato", "File pronti, salvati su GitHub in un ramo dedicato."],
  ];
  {
    const gap = 0.3, cw = (CW - 2 * gap) / 3, rh = 2.3;
    steps.forEach(([t, d], i) => {
      const r = Math.floor(i / 3), c = i % 3, x = M + c * (cw + gap), y = 1.6 + r * (rh + gap);
      card(s, x, y, cw, rh);
      numCircle(s, i + 1, x + 0.3, y + 0.3, 0.6);
      txt(s, t, { x: x + 1.1, y: y + 0.3, w: cw - 1.4, h: 0.6, fontSize: 18, bold: true, valign: "middle" });
      txt(s, d, { x: x + 0.3, y: y + 1.15, w: cw - 0.6, h: rh - 1.3, fontSize: 15, color: C.text2 });
    });
  }

  s = content("Come chiedere bene", "Iniziare");
  {
    const y = 1.6, h = 2.4;
    card(s, M, y, half, h);
    await iconCircle(s, "FaXmark", M + 0.3, y + 0.3, 0.6, C.accent6);
    txt(s, "Richiesta vaga", { x: M + 1.1, y: y + 0.3, w: half - 1.4, h: 0.6, fontSize: 18, bold: true, valign: "middle" });
    txt(s, "«Fammi un video»", { x: M + 0.3, y: y + 1.15, w: half - 0.6, h: 1.0, fontSize: 22, italic: true, color: C.text2 });
    const x2 = M + half + 0.4;
    card(s, x2, y, half, h);
    await iconCircle(s, "FaCheck", x2 + 0.3, y + 0.3, 0.6, C.accent2);
    txt(s, "Richiesta chiara", { x: x2 + 1.1, y: y + 0.3, w: half - 1.4, h: 0.6, fontSize: 18, bold: true, valign: "middle" });
    txt(s, "«Fammi un video verticale per Instagram, 10 secondi, colori blu e oro, con scritto: Pizzeria da Emilio – aperti la domenica»",
      { x: x2 + 0.3, y: y + 1.05, w: half - 0.6, h: 1.25, fontSize: 16, italic: true, color: C.text2 });
    const tips = [
      ["FaBullseye", "Dì scopo e formato", "A chi serve, dove lo userai, quanto è lungo."],
      ["FaPaperclip", "Dai materiale", "Testi, foto, file o un esempio che ti piace."],
      ["FaArrowsRotate", "Correggi a piccoli passi", "«Scritta più grande», «togli il rosso»."],
    ];
    const tw = (CW - 0.6) / 3;
    for (let i = 0; i < 3; i++) {
      const x = M + i * (tw + 0.3), yy = 4.35;
      await iconCircle(s, tips[i][0], x, yy, 0.55, C.accent1);
      txt(s, tips[i][1], { x: x + 0.75, y: yy, w: tw - 0.75, h: 0.55, fontSize: 17, bold: true, valign: "middle" });
      txt(s, tips[i][2], { x: x + 0.75, y: yy + 0.65, w: tw - 0.75, h: 1.1, fontSize: 14, color: C.text2 });
    }
  }

  // ===== Progetti =====
  divider("2 · Cosa puoi creare", "Tipi di progetti adatti a Claude Code", "Progetti");

  s = content("Progetti che puoi fare", "Progetti");
  await iconGrid(s, [
    { icon: "FaFilm", title: "Video e animazioni", text: "Bande, scritte, intro e video per i social." },
    { icon: "FaGlobe", title: "Siti web", text: "Pagine personali, vetrine, portfolio." },
    { icon: "FaMobileScreen", title: "App e programmi", text: "Strumenti, giochi, piccoli gestionali." },
    { icon: "FaFileWord", title: "Documenti Office", text: "Word, Excel, PowerPoint e PDF." },
    { icon: "FaChartColumn", title: "Grafici e dati", text: "Analisi di tabelle, report, dashboard." },
    { icon: "FaGears", title: "Automazioni", text: "Lavori ripetitivi fatti dal computer." },
    { icon: "FaBug", title: "Correggere errori", text: "Trova e ripara i problemi nel codice." },
    { icon: "FaMagnifyingGlass", title: "Ricerche", text: "Cerca sul web e ti prepara un riassunto." },
  ], 4, 1.55, 2.45);

  // ===== Funzionalità =====
  divider("3 · Le funzionalità", "Tutti gli strumenti, uno alla volta", "Funzionalità");

  s = content("Permessi: chi decide cosa", "Funzionalità");
  {
    const rows = [
      ["FaHand", "Normale", "Chiede il permesso prima di ogni azione importante. La più sicura per iniziare."],
      ["FaPenToSquare", "Accetta modifiche", "Modifica i file senza chiedere ogni volta, ma chiede per il resto."],
      ["FaMap", "Piano (Plan)", "Prima ti mostra il piano di lavoro, tu approvi, poi lo esegue."],
      ["FaRobot", "Automatica", "Lavora da solo e si ferma solo davanti alle azioni rischiose."],
    ];
    const rh = 1.05;
    for (let i = 0; i < rows.length; i++) {
      const y = 1.55 + i * (rh + 0.2);
      card(s, M, y, CW, rh);
      await iconCircle(s, rows[i][0], M + 0.25, y + 0.2, 0.65, C.accent1);
      txt(s, rows[i][1], { x: M + 1.15, y: y + 0.2, w: 3.0, h: 0.65, fontSize: 18, bold: true, valign: "middle" });
      txt(s, rows[i][2], { x: M + 4.2, y: y + 0.2, w: CW - 4.5, h: 0.65, fontSize: 16, color: C.text2, valign: "middle" });
    }
    txt(s, "Nel terminale cambi modalità con Maiusc+Tab. Per fermare Claude in qualsiasi momento: Esc o il pulsante Stop.",
      { x: M, y: 6.45, w: CW, h: 0.4, fontSize: 14, italic: true, color: C.accent1 });
  }

  s = content("Gli agenti: aiutanti dell'aiutante", "Funzionalità");
  await iconGrid(s, [
    { icon: "FaMagnifyingGlass", title: "Explore", text: "Cerca velocemente dove si trova una cosa tra tanti file." },
    { icon: "FaMap", title: "Plan", text: "Disegna il progetto prima di costruirlo." },
    { icon: "FaToolbox", title: "Generale", text: "Fa un lavoro lungo in sottofondo mentre Claude fa altro." },
    { icon: "FaBook", title: "Guida", text: "Risponde alle domande su come usare Claude Code." },
  ], 4, 1.6, 3.6, C.accent4, true);
  txt(s, [
    { text: "Come si usano: ", options: { bold: true } },
    { text: "scrivi «usa un agente per…». Più agenti possono lavorare insieme su parti diverse dello stesso lavoro." },
  ], { x: M, y: 5.6, w: CW, h: 0.8, fontSize: 17 });

  s = content("Le skill: ricette pronte", "Funzionalità");
  {
    const groups = [
      { icon: "FaFileLines", title: "Per i documenti", fill: C.accent2,
        items: ["PDF: leggere, unire, compilare moduli", "Word e Docs: lettere, contratti, guide",
                "Excel: tabelle, formule, pulizia dati", "PowerPoint: presentazioni come questa",
                "Grafici: visualizzazioni chiare"] },
      { icon: "FaCode", title: "Per i progetti", fill: C.accent1,
        items: ["/code-review: cerca errori nel codice", "/security-review: controlla la sicurezza",
                "/simplify: rende il codice più pulito", "/init: crea il file CLAUDE.md",
                "/loop: ripete un compito a intervalli"] },
    ];
    for (let i = 0; i < 2; i++) {
      const x = M + i * (half + 0.4), y = 1.55, h = 4.3, g = groups[i];
      card(s, x, y, half, h);
      await iconCircle(s, g.icon, x + 0.35, y + 0.35, 0.65, g.fill);
      txt(s, g.title, { x: x + 1.2, y: y + 0.35, w: half - 1.5, h: 0.65, fontSize: 20, bold: true, valign: "middle" });
      txt(s, bullets(g.items, 16), { x: x + 0.35, y: y + 1.3, w: half - 0.7, h: 2.8 });
    }
    txt(s, "Si richiamano scrivendo / e il nome. Spesso Claude le usa da solo quando servono. Puoi anche creare le tue skill.",
      { x: M, y: 6.1, w: CW, h: 0.6, fontSize: 15, italic: true, color: C.accent1 });
  }

  s = content("Connettori: le porte verso i tuoi servizi", "Funzionalità");
  {
    const items = [
      ["FaEnvelope", "Gmail", "Cercare email, leggere, preparare bozze."],
      ["FaCalendarDays", "Google Calendar", "Vedere impegni, creare eventi, orari liberi."],
      ["FaGithub", "GitHub", "Progetti, pull request e revisioni."],
      ["FaWandMagicSparkles", "Base44", "Creare app complete partendo da una descrizione."],
      ["FaCommentSms", "Bird", "Email, SMS e WhatsApp verso i clienti."],
      ["FaFileLines", "Claude Docs", "Documenti condivisi da leggere e commentare."],
    ];
    const gap = 0.3, cw = (CW - 2 * gap) / 3, rh = 1.95;
    for (let i = 0; i < items.length; i++) {
      const r = Math.floor(i / 3), c = i % 3, x = M + c * (cw + gap), y = 1.55 + r * (rh + gap);
      card(s, x, y, cw, rh);
      await iconCircle(s, items[i][0], x + 0.3, y + 0.3, 0.6, C.accent2);
      txt(s, items[i][1], { x: x + 1.1, y: y + 0.3, w: cw - 1.4, h: 0.6, fontSize: 18, bold: true, valign: "middle" });
      txt(s, items[i][2], { x: x + 0.3, y: y + 1.05, w: cw - 0.6, h: 0.8, fontSize: 15, color: C.text2 });
    }
    txt(s, "Questi sono quelli collegati al tuo account. Prima di inviare, pubblicare o cancellare, Claude ti chiede conferma.",
      { x: M, y: 6.25, w: CW, h: 0.5, fontSize: 14, italic: true, color: C.accent1 });
  }

  s = content("GitHub: salvare e condividere il lavoro", "Funzionalità");
  {
    const flow = [
      ["Branch", "Un ramo: la tua copia di lavoro"],
      ["Commit", "Una foto delle modifiche"],
      ["Push", "Invia la foto su GitHub"],
      ["Pull request", "Proposta da controllare"],
      ["Merge", "Unione al progetto principale"],
    ];
    const bw = 2.05, gap = (CW - 5 * bw) / 4, y = 1.9;
    flow.forEach(([t, d], i) => {
      const x = M + i * (bw + gap);
      card(s, x, y, bw, 2.3);
      numCircle(s, i + 1, x + (bw - 0.6) / 2, y + 0.25, 0.6, C.accent1);
      txt(s, t, { x: x + 0.15, y: y + 1.0, w: bw - 0.3, h: 0.45, fontSize: 18, bold: true, align: "center" });
      txt(s, d, { x: x + 0.15, y: y + 1.5, w: bw - 0.3, h: 0.75, fontSize: 14, color: C.text2, align: "center" });
      if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + (gap - 0.3) / 2, y: y + 1.0, w: 0.3, h: 0.3,
        fill: { color: C.accent5 }, line: { type: "none" }, objectName: nm("freccia") });
    });
    card(s, M, 4.6, CW, 1.6);
    await iconCircle(s, "FaEye", M + 0.35, 4.95, 0.8, C.accent2);
    txt(s, [
      { text: "Claude può sorvegliare una pull request", options: { bold: true, fontSize: 18, breakLine: true } },
      { text: "Se i test falliscono li corregge, risponde ai commenti dei revisori e ti avvisa quando è tutto pronto.",
        options: { fontSize: 15, color: C.text2 } },
    ], { x: M + 1.45, y: 4.85, w: CW - 1.8, h: 1.1, valign: "middle" });
  }

  s = content("Attività programmate e ripetute", "Funzionalità");
  await iconGrid(s, [
    { icon: "FaBell", title: "Promemoria", text: "«Ricordamelo tra 2 ore»: Claude riprende il lavoro all'ora giusta." },
    { icon: "FaCalendarDays", title: "Attività programmate", text: "«Ogni lunedì alle 9 fammi il riassunto delle email»." },
    { icon: "FaArrowsRotate", title: "/loop", text: "«Controlla ogni 5 minuti se il lavoro è finito»." },
  ], 3, 1.6, 3.4, C.accent3, true);
  txt(s, "Funzionano anche quando non sei davanti allo schermo: trovi il risultato al tuo ritorno.",
    { x: M, y: 5.5, w: CW, h: 0.5, fontSize: 18, italic: true, color: C.accent1 });

  s = content("Artifact, file e memoria del progetto", "Funzionalità");
  await iconGrid(s, [
    { icon: "FaShareNodes", title: "Artifact", text: "Pagine web private su claude.ai: dashboard, mini-app, report. Le condividi con un link." },
    { icon: "FaPaperPlane", title: "File in chat", text: "Video, PowerPoint, Excel e immagini ti arrivano qui, pronti da scaricare." },
    { icon: "FaBrain", title: "CLAUDE.md", text: "Il quaderno delle regole del progetto: Claude lo legge ogni volta che inizia." },
  ], 3, 1.6, 4.2, C.accent4, true);

  s = content("Comandi utili da ricordare", "Funzionalità");
  {
    const rows = [
      ["/help", "Mostra l'aiuto e tutti i comandi"],
      ["/clear", "Ricomincia con una conversazione pulita"],
      ["/compact", "Riassume la conversazione per liberare spazio"],
      ["/model", "Cambia il modello di Claude"],
      ["/init", "Crea il file CLAUDE.md del progetto"],
      ["/config", "Apre le impostazioni"],
      ["/resume", "Riprende una sessione precedente"],
      ["/fast", "Attiva o disattiva la modalità veloce"],
      ["Esc", "Interrompe Claude mentre lavora"],
    ];
    const hdr = { bold: true, color: C.background1, fill: { color: C.text1 }, fontSize: 15 };
    const data = [[{ text: "Comando", options: hdr }, { text: "A cosa serve", options: hdr }]];
    rows.forEach(([a, b], i) => {
      const f = { color: i % 2 ? C.background1 : C.background2 };
      data.push([{ text: a, options: { bold: true, color: C.accent1, fontFace: "Courier New", fill: f } },
                 { text: b, options: { color: C.text1, fill: f } }]);
    });
    s.addTable(data, { x: M, y: 1.5, w: CW, colW: [2.6, CW - 2.6], rowH: 0.48, fontSize: 15, valign: "middle",
      margin: [0, 0.15, 0, 0.15], border: { type: "none" }, objectName: nm("tabella") });
  }

  s = content("Limiti e sicurezza", "Funzionalità");
  await iconGrid(s, [
    { icon: "FaCloud", title: "Computer temporaneo", text: "Nel web la lavagna viene cancellata: per questo si salva tutto su GitHub." },
    { icon: "FaLock", title: "Solo ciò che colleghi", text: "Non entra nel tuo PC o telefono se non glielo permetti." },
    { icon: "FaShieldHalved", title: "Chiede conferma", text: "Prima di inviare, cancellare o pubblicare aspetta il tuo sì." },
    { icon: "FaTriangleExclamation", title: "Può sbagliare", text: "Guarda sempre il risultato e chiedi le correzioni." },
  ], 4, 1.6, 4.4, C.accent6, true);

  // ===== Chiusura =====
  pres.addSection({ title: "Chiusura" });
  s = pres.addSlide({ masterName: "TITOLO", sectionTitle: "Chiusura" });
  s.addText([{ text: "Chat = parlare", options: { breakLine: true } }, { text: "Claude Code = costruire" }], { placeholder: "title" });
  s.addText("Prossimo passo: scegli un'idea e chiedila a Claude Code", { placeholder: "body" });
  await iconCircle(s, "FaRocket", M, 1.0, 0.9, C.accent1);

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("Creato", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
