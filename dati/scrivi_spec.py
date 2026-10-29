"""Scrive dati/guida_spec.json dalle misure di dati/geometria.json (lanciare dopo blender/costruisci.py)."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
geo = json.load(open(os.path.join(root, "dati", "geometria.json"), encoding="utf-8"))
R, SEAM = 27.5, geo["giunto"]["quota_mm"]
P = geo["pezzi"]; F = geo["fori"]
def n(x, d=1): return f"{x:.{d}f}".replace(".", ",")
designs = [("P01","Spirale","#d6336c"),("P02","Voronoi","#c92a2a"),("P03","Anelli","#c8a04a"),("P04","Griglia","#3b5bdb"),
           ("P05","Fessure","#74b816"),("P06","Zampette","#f08c00"),("P07","Pesciolini","#1c9aa8"),
           ("P08","Stelle","#7048e8"),("P09","Cuori","#f783ac"),("P10","Topolini","#868e96"),("P11","Lische","#4dabf7"),
           ("P12","NidoApe","#ffd43b"),("P13","Elica","#f76707"),("P14","Rete","#0ca678")]
UNICI = {"Voronoi", "Elica", "Rete"}
pos = {}
for i, (num, lab, c) in enumerate(designs):
    pos[lab] = (((i % 4) - 1.5) * 70.0, -70.0 * (i // 4))
desc = {
 "Spirale": "Dieci fessure a spirale per metà, larghe circa 6 mm, che girano di 90° dal giunto verso il polo.",
 "Voronoi": "Pezzo unico a celle di Voronoi, come quella rossa della foto: niente vite, il sonaglio entra durante una pausa di stampa.",
 "Anelli": "Quattro file di finestre orizzontali per metà, con le nervature sfalsate di fila in fila: l'effetto a fasce della pallina dorata.",
 "Griglia": "Una rete di finestrelle quasi quadrate (lato circa 4 mm, nervature da 1,8) e un foro Ø14 su ciascun polo, da cui il gatto vede il sonaglio.",
 "Fessure": "Sei fessure lunghe a meridiano e sei corte in mezzo, larghe 5,5 mm: la pallina verde.",
 "Zampette": "Impronte di zampa di gatto: un cuscinetto e quattro dita, cinque impronte in giro più una sul polo, su entrambe le metà.",
 "Pesciolini": "Sagome di pesce che nuotano in due file opposte, con tre bolle sul polo.",
 "Stelle": "Stelle a cinque punte sparse e ruotate a caso.",
 "Cuori": "Cuori disposti sulla spirale aurea, tutti con la punta verso il giunto.",
 "Topolini": "Teste di topolino: una testa tonda e due orecchie, ognuna un foro a sé.",
 "Lische": "Lische di pesce: spina, testa, coda e tre coppie di costole; quattro in giro e una sul polo.",
 "NidoApe": "Nido d'ape: le celle della spirale aurea vengono quasi tutte esagoni.",
 "Elica": "Pezzo unico: dodici fessure che si avvolgono di mezzo giro da un polo all'altro, attraverso l'equatore. Una vite le spezzerebbe.",
 "Rete": "Pezzo unico: rombi fra due famiglie di lossodromiche che si incrociano, sempre più piccoli verso i poli. Una vite taglierebbe la rete a metà.",
}
parts = []
for num, lab, c in designs:
    x, y = pos[lab]
    if lab in UNICI:
        k = f"{num}_{lab}"; p = P[k]
        parts.append({"id": num, "label": lab + " (pezzo unico)", "group": lab, "file": f"stl/{k}.stl", "print": "unici",
                      "mode": "mesh", "max_triangles": 10000,
                      "assembled_bounds": [[x + p["min"][0], x + p["max"][0]], [y + p["min"][1], y + p["max"][1]], [1.2, 1.2 + p["size"][2]]],
                      "note_html": f"<p>{desc[lab]} {F[lab]['n']} fori, nervature di almeno {n(F[lab]['nervatura_min_mm'])} mm, foro più largo {n(F[lab]['max_cerchio_inscritto_mm'])} mm. Sul fondo un piano d'appoggio e una calotta piena per l'adesione. Pausa per il sonaglio a {n(F[lab]['pausa_per_sonaglio_mm'])} mm. {n(p['peso_PETG_g'])} g di PETG.</p>"})
        continue
    m, v = P[f"{num}_{lab}_Madrevite"], P[f"{num}_{lab}_Vite"]
    parts.append({"id": num + "A", "label": lab + " · madrevite", "group": lab, "file": f"stl/{num}_{lab}_Madrevite.stl",
                  "print": "meta", "mode": "mesh", "max_triangles": 7000,
                  "assembled_bounds": [[x - 27.5, x + 27.5], [y - 27.5, y + 27.5], [R + SEAM, R + SEAM + m["size"][2]]],
                  "note_html": f"<p>La metà di sopra, con il filetto interno e la svasatura all'imbocco. {desc[lab]} {n(m['peso_PETG_g'])} g.</p>"})
    parts.append({"id": num + "B", "label": lab + " · vite", "group": lab, "file": f"stl/{num}_{lab}_Vite.stl",
                  "print": "meta", "mode": "mesh", "max_triangles": 7000,
                  "matrix": [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
                  "assembled_bounds": [[x + v["min"][0], x + v["max"][0]], [y + v["min"][1], y + v["max"][1]], [0, v["size"][2]]],
                  "note_html": f"<p>La metà di sotto, con il collare filettato, il cono a 45° e la spalla che batte sulla madrevite. Si stampa capovolta, collare sul piatto. {n(v['peso_PETG_g'])} g.</p>"})
order = ["Zampette", "Voronoi"] + [l for _, l, _ in designs if l not in ("Zampette", "Voronoi")]
NB = len(designs)
z0 = 2.4 + 1.0 - 0.6
base = pos["Zampette"]
inst = [[pos[l][0] - base[0], pos[l][1] - base[1], 0] for l in order]
SON = "P15"
big = max(F, key=lambda k: F[k]["max_cerchio_inscritto_mm"])
parts.append({"id": SON, "label": "Sonaglio", "group": "Sonaglio", "file": f"stl/{SON}_Sonaglio.stl", "print": "sonaglio",
              "quantity": NB, "mode": "mesh", "max_triangles": 1200,
              "assembled_bounds": [[base[0] - 9, base[0] + 9], [base[1] - 9, base[1] + 9], [z0, z0 + 17]], "instances": inst,
              "note_html": f"<p>Pallina piena Ø18 con un piano d'appoggio: una per ogni pallina. È più grande di tutti i fori (il più largo è nella {big}, Ø{n(F[big]['max_cerchio_inscritto_mm'])}), quindi non esce. {n(P[SON + '_Sonaglio']['peso_PETG_g'])} g.</p>"})

groups = {lab: {"color": c} for _, lab, c in designs}
groups["Sonaglio"] = {"color": "#495057"}

# sezione del giunto, scala 6 px/mm, metà destra della pallina attorno al giunto
S, X0, Z0 = 14.0, 10.0, 115.0
def pt(r, z): return f"{X0 + (r - 19.5) * S:.1f},{Z0 - (z - SEAM) * S:.1f}"
import math
RI, FM, TM, TH = 25.1, 24.35, 24.0, 0.9
RS = math.sqrt(R * R - SEAM * SEAM); RL = RS - 0.8; CS = RL - FM
ZT0, ZT1 = SEAM + CS, SEAM + CS + 5.0
rn = FM - TH - 0.1
top = [pt(RS, SEAM)] + [pt(R * math.cos(a), R * math.sin(a)) for a in [math.asin(SEAM / R) + k * 0.02 for k in range(1, 12)]]
zt = math.asin((ZT1 + 0.3 + 6) / RI)
fem = top + [pt(RI * math.cos(a), RI * math.sin(a)) for a in [zt - k * 0.02 for k in range(0, 8)]] + [pt(rn, ZT1 + 0.3), pt(rn, SEAM + RL - rn), pt(RL, SEAM)]
ZC = ZT1 - 0.5
male = [pt(RS, SEAM), pt(RL - 0.3, SEAM), pt(FM - 0.3, ZT0), pt(TM - TH, ZT0), pt(TM - TH, ZC), pt(21.6, ZC), pt(21.6, ZT0), pt(23.9, SEAM - 2.0),
        pt(math.sqrt(RI * RI - 49), -7), pt(math.sqrt(R * R - 49), -7)]
teeth_m = " ".join(f"M{pt(TM - TH, ZT0 + 0.3 + k * 2.5)} L{pt(TM, ZT0 + 0.9 + k * 2.5)} L{pt(TM, ZT0 + 1.5 + k * 2.5)} L{pt(TM - TH, ZT0 + 2.1 + k * 2.5)}" for k in range(2))
svg = (f"<svg viewBox='0 0 380 230' xmlns='http://www.w3.org/2000/svg' font-size='11' font-family='sans-serif'>"
       f"<polygon points='{' '.join(fem)}' fill='#f08c00' opacity='.85'/>"
       f"<polygon points='{' '.join(male)}' fill='#c2410c' opacity='.8'/>"
       f"<path d='{teeth_m}' fill='none' stroke='#c2410c' stroke-width='2'/>"
       f"<line x1='0' y1='{Z0}' x2='380' y2='{Z0}' stroke='#888' stroke-dasharray='4 3'/>"
       f"<text x='200' y='30'>madrevite (sopra)</text><text x='200' y='46'>filetto interno Ø{n(2 * FM)}</text>"
       f"<text x='200' y='150'>vite (sotto)</text><text x='200' y='166'>collare Ø{n(2 * TM)} · passo 2,5</text>"
       f"<text x='200' y='182'>profondità 0,9 · 2 giri</text><text x='200' y='198'>gioco radiale 0,35</text>"
       f"<text x='200' y='{Z0 - 6}'>giunto, {n(-SEAM)} mm sotto l'equatore</text>"
       f"<text x='200' y='214'>svasatura 45° · battuta 0,8 mm</text></svg>")

pausa = n(F["Voronoi"]["pausa_per_sonaglio_mm"])
ids_all = [p["id"] for p in parts] + [f"{SON}·{k}" for k in range(2, NB + 1)]
NV = NB - len(UNICI)
spec = {
 "root": "..", "output": "guida.html", "title": "Palline Traforate · Guida",
 "theme": {"accent": "#e8590c", "viewer_bg": "#1f1b18"},
 "header": {
  "eyebrow": "Palline Traforate · giochi per il gatto · PETG",
  "h1": "Quattordici palline, un sonaglio ciascuna.",
  "intro_html": f"<b>Palline cave Ø55 mm con un sonaglio dentro, da far rotolare al gatto.</b> Cinque motivi vengono dalla foto di riferimento (spirale, Voronoi, anelli, griglia, fessure), gli altri sono nuovi: <b>Zampette</b>, <b>Pesciolini</b>, <b>Stelle</b>, <b>Cuori</b>, <b>Topolini</b>, <b>Lische</b>, <b>Nido d'ape</b>, <b>Elica</b> e <b>Rete</b>. {NV} palline sono due metà che si <b>avvitano</b> (collare filettato e madrevite); Voronoi, Elica e Rete sono un <b>pezzo unico</b>, perché il disegno attraversa l'equatore, e il sonaglio si infila durante una pausa di stampa. Il sonaglio Ø18 è più grande di ogni foro, quindi resta dentro.",
  "facts": [{"value": "Ø55 mm", "label": "pallina"}, {"value": "Ø18 mm", "label": "sonaglio, più grande di ogni foro"},
            {"value": "2 giri", "label": "filetto passo 2,5"}, {"value": "20–30 g", "label": "PETG per pallina"}]},
 "camera": {"yaw": -0.3, "pitch": 0.75},
 "caption": "Le quattordici palline montate, in file da quattro. In fondo i motivi della foto, davanti quelli nuovi.",
 "model_note_html": "<span class='badge'>Quote del modello</span><p>Sfera Ø55, parete 2,4 mm. Il giunto sta 2 mm sotto l'equatore, dove la parete della madrevite resta spessa attorno al filetto. Fori a partire da 7 mm sopra il giunto (madrevite) e 4,5 mm sotto (vite): la fascia attorno al giunto è piena.</p>",
 "groups": groups,
 "parts": parts,
 "steps_section": {"eyebrow": "01 / Montaggio", "h2": "Sonaglio dentro, poi si avvita.",
  "intro_html": f"Le {NV} palline a vite si montano tutte allo stesso modo: nei passaggi c'è la Zampette come esempio. Niente colla e niente attrezzi, così si apre per lavarla o cambiare il sonaglio.",
  "start_html": "<h3>Prima prova un filetto.</h3><p>Stampa una sola coppia e avvitala: deve entrare a mano per due giri e fermarsi quando il bordo della madrevite tocca la spalla. Se è dura o lasca, vedi la nota nella sezione Stampa prima di stampare le altre.</p>"},
 "steps": [
  {"title": "Metti il sonaglio nella vite", "short": "dall'alto", "text": "Appoggia la metà P06B con il collare in alto e lascia cadere dentro il sonaglio P15: il foro del collare è Ø43,2, passa largo.",
   "parts": ["P06B", SON], "built": ["P06B", SON], "moving": [SON], "dir": [0, 0, 1], "travel": 45},
  {"title": "Avvita la madrevite", "short": "2 giri · senso orario", "text": "Appoggia P06A sul collare, gira un poco all'indietro finché senti il filetto scattare in sede, poi avvita in senso orario per circa due giri. Si ferma quando il bordo piano tocca la spalla: non serve stringere.",
   "parts": ["P06A", "P06B"], "built": ["P06A", "P06B", SON], "moving": ["P06A"], "dir": [0, 0, 1], "travel": 30},
  {"title": "Voronoi, Elica, Rete: sonaglio in stampa", "short": f"pausa a {pausa} mm", "text": f"P02, P13 e P14 non si aprono. Nello slicer aggiungi una pausa al primo strato sopra {pausa} mm; quando la stampante si ferma, lascia cadere il sonaglio sul fondo della cavità (rotola al centro) e fai ripartire la stampa. A quella quota la testina passa già sopra il sonaglio.",
   "parts": ["P02", SON + "·2"], "built": ["P02", SON + "·2"]},
  {"title": "Controllo", "short": "prima di darla al gatto", "text": "Scuoti ogni pallina: il sonaglio deve correre libero. Togli fili e sbavature dai bordi dei fori e controlla che le due metà siano avvitate fino in fondo.",
   "parts": ids_all}
 ],
 "print": {"eyebrow": "03 / Stampa", "h2": f"{2 * NV} mezze sfere, tre palline intere, {NB} sonagli.",
  "common_html": "<b>Profilo comune:</b> Kobra S1, ugello 0,4 mm, PETG, strato 0,20 mm. Sono parametri che <b>propongo io, da verificare</b>: nessuna pallina è ancora stata stampata. STL in millimetri, scala 100%, già appoggiati a Z = 0 e orientati per la stampa.",
  "profiles": [
   {"key": "meta", "title": "Metà a vite (P..A / P..B)", "rows": [["Orientamento", "bordo sul piatto (la vite capovolta, collare sul piatto)"], ["Pareti", "6 (parete tutta piena)"], ["Supporti", "no"], ["Compensazione zampa d'elefante", "0,15 mm"], ["Ingombro", "55 × 55 × 30–32 mm"]],
    "why": "Col bordo in basso ogni metà è una cupola: le pareti salgono rientrando, il cielo vicino al polo si chiude a piccoli cerchi e sopra i fori c'è al massimo un arco di pochi millimetri. Il filetto ha i fianchi a circa 50° e l'imbocco a 45°, quindi niente supporti. La parete è 2,4 mm: con 6 pareti diventa tutta perimetro, più robusta ai morsi e alle unghie. Sulla vite il filetto parte dal piatto: la compensazione evita che il primo giro si allarghi e indurisca l'avvitamento.",
    "summary": "bordo sul piatto · 6 pareti · senza supporti"},
   {"key": "unici", "title": "P02, P13, P14 · pezzi unici", "rows": [["Orientamento", "piano d'appoggio sul piatto"], ["Pareti", "6"], ["Supporti", "ad albero, solo dal piatto"], ["Pausa", f"al primo strato sopra {pausa} mm, per il sonaglio"], ["Ingombro", "55 × 55 × 53,8 mm"]],
    "why": "Una sfera intera ha sotto una calotta che sporge oltre i 45°: servono supporti, ma solo da fuori, perché dentro non si potrebbero togliere. Fori e fessure della metà alta si chiudono ad arco e stanno su da sole. Il fondo è pieno per 5 mm, così la pallina aderisce bene. La pausa va appena sopra la cima del sonaglio appoggiato sul fondo.",
    "summary": f"supporti ad albero dal piatto · pausa a {pausa} mm"},
   {"key": "sonaglio", "title": "P15 · sonaglio", "rows": [["Orientamento", "piano sul piatto"], ["Pareti", "3"], ["Riempimento", "40%"], ["Supporti", "no"], ["Copie", str(NB)]],
    "why": "Più pesante suona meglio. Il piano d'appoggio è Ø8: la sfera sopra sporge un poco ma così piccola si stampa senza supporti, e i segni non si vedono perché sta dentro.",
    "summary": f"40% · {NB} copie"}],
  "note_html": "Il filetto ha 0,35 mm di gioco sul raggio. Se è troppo duro o troppo lasco cambia <code>TH_GAP</code> in <code>blender/costruisci.py</code> e rigenera. Diametro, parete e sonaglio sono in cima allo stesso script (<code>R</code>, <code>WALL</code>, <code>BALL_R</code>): lo script controlla da solo che il sonaglio resti più grande di ogni foro e lo scrive in <code>dati/geometria.json</code>."},
 "notes": {"eyebrow": "04 / Il giunto", "h2": "Collare, madrevite, battuta.", "nav": "Giunto",
  "cards": [{"title": "Sezione del giunto", "html": "<p>La vite ha un collare filettato con sotto un cono a 45° e una spalla; la madrevite ha la svasatura a 45° che fa da invito e un bordo piano largo 0,8 mm che batte sulla spalla. Il filetto è trapezoidale, destro, e la vite non tocca il fondo: l'avvitamento si ferma sulla battuta.</p>" + svg},
            {"title": "Il gatto", "html": "<p>Il sonaglio non esce da nessun foro e le nervature più sottili sono di 1,8 mm (Griglia, Lische). Controlla le palline ogni tanto: se una nervatura si crepa o il gatto la mastica, buttala, perché una pallina rotta può avere spigoli taglienti. I fori vanno da 5 a 15 mm: le unghie non restano agganciate.</p>"}]},
 "files": {"h2": "I file.", "intro_html": "Gli STL sono in <code>stl/</code>; la scena e lo script che li genera in <code>blender/</code>.",
  "links": [{"label": "README", "href": "README.md"}, {"label": "Scena Blender", "href": "blender/Palline_Traforate.blend"},
            {"label": "Script di costruzione", "href": "blender/costruisci.py"}, {"label": "Misure e controlli", "href": "dati/geometria.json"},
            {"label": "Foto di riferimento", "href": "originale/riferimento_palline.jpg"}]},
 "footer_html": "Guida offline: aprire questo file dalla cartella del progetto."
}
json.dump(spec, open(os.path.join(root, "dati", "guida_spec.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok", len(parts))
