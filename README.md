# Palline Traforate

Quattordici palline cave Ø55 mm per il gatto, ognuna con un sonaglio Ø18 dentro (più grande di ogni foro, quindi non esce). Cinque motivi vengono dalla foto di riferimento, gli altri sono nuovi. Apri **guida.html** per la vista 3D, il montaggio e la lista di stampa.

**Guida di stampa e montaggio:** https://maxeo.github.io/3dprint-guide/palline/guida.html

## Contenuto

- `guida.html`: istruzioni, parametri di stampa e vista 3D interattiva
- `stl/`: i pezzi da stampare, già orientati per la stampa
  - undici palline a vite, due metà ciascuna: `P..A` = `<motivo>_Madrevite` (sopra, filetto interno e svasatura a 45°) e `P..B` = `<motivo>_Vite` (sotto, collare filettato, cono e spalla; si stampa capovolta)
    - dalla foto: `P01_Spirale`, `P03_Anelli`, `P04_Griglia` (foro Ø14 sui poli), `P05_Fessure`
    - nuovi: `P06_Zampette` (impronte di zampa), `P07_Pesciolini`, `P08_Stelle`, `P09_Cuori`, `P10_Topolini`, `P11_Lische` (spine di pesce), `P12_NidoApe` (esagoni sulla spirale aurea)
  - tre palline in un pezzo unico, perché il disegno attraversa l'equatore: `P02_Voronoi` (dalla foto), `P13_Elica` (12 fessure che girano di mezzo giro da polo a polo), `P14_Rete` (rombi fra lossodromiche incrociate). Il sonaglio si infila durante una pausa di stampa: quota in `dati/geometria.json`
  - `P15_Sonaglio`: da stampare 14 volte
- Giunto: filetto trapezoidale passo 2,5, profondità 0,9, due giri, 0,35 mm di gioco radiale; sta 2 mm sotto l'equatore e si ferma su una battuta piana da 0,8 mm
- `blender/Palline_Traforate.blend`: le palline montate (`PALLINE_MONTATE`) e i pezzi in posa di stampa (`PEZZI_STAMPA`, nascosta)
- `blender/costruisci.py`: genera .blend, STL e `dati/geometria.json`; controlla che ogni pezzo sia chiuso, che il sonaglio resti più grande del foro più largo e la nervatura più sottile
- `dati/`: `geometria.json` (ingombri, pesi, fori, giunto), `scrivi_spec.py` (scrive lo spec dalle misure) e `guida_spec.json` (sorgente della guida)
- `originale/`: la foto di riferimento

Rigenerare i pezzi e la guida:

```
blender -b --factory-startup --python blender/costruisci.py
python dati/scrivi_spec.py
python ~/.claude/skills/guida-stampa-3d/scripts/build_guide.py dati/guida_spec.json
```

Lo script gira anche nel Blender aperto via MCP (`exec(open(r"<progetto>\blender\costruisci.py", encoding="utf-8").read())`), ma ci mette circa 3 minuti: oltre il timeout dell'MCP. Meglio lanciarlo headless e poi aprire il .blend.

## Note

- Nessuna pallina è ancora stata stampata: il gioco del filetto (`TH_GAP`) e i parametri di stampa della guida sono da provare. Conviene stampare prima una sola coppia.
- Le metà a vite si stampano senza supporti; i tre pezzi unici vogliono supporti ad albero solo dal piatto.
