"""Palline traforate per il gatto · palline cave Ø55 con un sonaglio dentro.

Uso (dalla cartella del progetto):
    blender -b --factory-startup --python blender/costruisci.py
oppure nel Blender aperto, via MCP: exec(open(r"<progetto>/blender/costruisci.py", encoding="utf-8").read())

Le palline a vite sono due metà: la «madrevite» (sopra, filetto interno con svasatura
all'imbocco) e la «vite» (sotto, collare filettato con cono e spalla che battono sulla
svasatura). Si stampano entrambe con il bordo sul piatto, senza supporti. Il giunto
non sta all'equatore ma SEAM mm sotto, dove la parete della madrevite è più spessa.
La Voronoi è un pezzo unico: il sonaglio si infila durante una pausa di stampa.

Scrive blender/Palline_Traforate.blend, gli STL in stl/ (già orientati per la stampa)
e dati/geometria.json. Coordinate di montaggio: centro della pallina nell'origine.
"""
import bpy, bmesh, math, json, os, random
import numpy as np
from mathutils import Matrix, Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:                                  # exec() dal Blender aperto
    ROOT = r"D:\3D Print\Palline Traforate"
STL = os.path.join(ROOT, "stl")
os.makedirs(STL, exist_ok=True)
os.makedirs(os.path.join(ROOT, "dati"), exist_ok=True)

# --- misure -------------------------------------------------------------
R, WALL = 27.5, 2.4                     # pallina Ø55
RI = R - WALL
SEAM = -2.0                             # quota del giunto (sotto l'equatore)
TH_P, TH_H, TH_L = 2.5, 0.9, 5.0        # filetto: passo, profondità, lunghezza in presa (2 giri)
TM = 24.0                               # raggio esterno del filetto della vite
TH_GAP = 0.35                           # gioco radiale della madrevite
LIP = 0.8                               # bordo piano della madrevite, battuta della spalla
CONE_GAP = 0.3                          # gioco fra cono della vite e svasatura
BORE = 21.6                             # foro del collare (il sonaglio Ø18 ci passa)
BALL_R, BALL_FLAT = 9.0, 1.0            # sonaglio Ø18, con un piano d'appoggio
VOR_FLAT = 1.2                          # Voronoi: piano d'appoggio sul fondo
SEG = 144

R_S = math.sqrt(R * R - SEAM * SEAM)    # raggio esterno al giunto
R_LIP = R_S - LIP                       # inizio della svasatura
FM = TM + TH_GAP                        # raggio esterno della madrevite
CS = R_LIP - FM                         # altezza della svasatura a 45°
Z_TH0 = SEAM + CS                       # inizio del filetto
Z_TH1 = Z_TH0 + TH_L                    # fine della madrevite
Z_COL = Z_TH1 - 0.5                     # cima del collare (non tocca il fondo)
Z_REC = Z_TH1 + 0.3                     # cima della zona filettata nella madrevite (sotto la fine del tagliente)

if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:                                               # nel Blender aperto: svuota senza ricaricare (l'addon MCP resta vivo)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.collections):
        for b in list(blocks):
            blocks.remove(b)
sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = 'MILLIMETERS'


def coll(name, hide=False):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    c.hide_viewport = c.hide_render = hide
    return c


C_STAMPA, C_MONT = coll("PEZZI_STAMPA", True), coll("PALLINE_MONTATE")


def obj_from_bm(bm, name, c):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def boolean(target, tool, op, tolerant=False):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation, m.object, m.solver = op, tool, 'EXACT'
    m.use_hole_tolerant = tolerant
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool)


def lathe(profile, name, c, seg=SEG):
    """Rivoluzione di un profilo chiuso (r, z) attorno a Z; i punti con r = 0 sono poli.
    I punti doppi (fine di un arco = punto successivo) darebbero facce nulle che rompono i booleani."""
    profile = [p for i, p in enumerate(profile) if math.dist(p, profile[i - 1]) > 1e-4]
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((0, 0, z))] * seg)
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))
                          for k in range(seg)])
    for i in range(len(rings)):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        for k in range(seg):
            q = [a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]]
            q = [v for j, v in enumerate(q) if v not in q[:j]]
            if len(q) >= 3:
                bm.faces.new(q)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)


def radial_solid(rfun, z0, z1, name, c, seg=SEG, dz=0.1):
    """Solido chiuso con raggio r(theta, z): filetti."""
    bm = bmesh.new()
    nz = max(2, int(round((z1 - z0) / dz)) + 1)
    rings = []
    for k in range(nz):
        z = z0 + (z1 - z0) * k / (nz - 1)
        rings.append([bm.verts.new((rfun(t, z) * math.cos(t), rfun(t, z) * math.sin(t), z))
                      for t in (2 * math.pi * i / seg for i in range(seg))])
    for k in range(nz - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    cb = bm.verts.new((0, 0, z0)); ct = bm.verts.new((0, 0, z1))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((cb, rings[0][j], rings[0][i]))
        bm.faces.new((ct, rings[-1][i], rings[-1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)


def thread_r(t, z, r_out):
    """Profilo trapezoidale, filetto destro: cresta 0,24 p, fianchi 0,29 p."""
    u = (z - TH_P * t / (2 * math.pi)) % TH_P / TH_P
    crest, flank = 0.24, 0.29
    if u < crest:
        f = 1.0
    elif u < crest + flank:
        f = 1 - (u - crest) / flank
    elif u < 1 - flank:
        f = 0.0
    else:
        f = (u - (1 - flank)) / flank
    return r_out - TH_H + TH_H * f


def sphere_meet(r0, z0, sign):
    """Quota in cui la retta a 45° r = r0 + sign·(z0 - z) incontra la sfera interna."""
    lo, hi = (-RI, z0) if sign > 0 else (z0, RI)
    f = lambda z: r0 + sign * (z0 - z) - math.sqrt(max(RI * RI - z * z, 0))
    for _ in range(60):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (f(lo) > 0):
            lo = mid
        else:
            hi = mid
    return lo


def arc(r, a0, a1, step=1.5):
    n = max(2, int(abs(a1 - a0) / step))
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]


# --- gusci ----------------------------------------------------------------
def madrevite(name):
    """Metà di sopra: sfera da SEAM al polo, svasatura a 45° all'imbocco e filetto interno."""
    a_s = math.degrees(math.asin(SEAM / R))
    a_w = math.degrees(math.asin(Z_REC / RI))
    prof = arc(R, a_s, 89.0) + [(0, R), (0, RI)] + arc(RI, 89.0, a_w)
    # parete piena fino a 0,1 dentro il nocciolo del filetto; la svasatura a 45° la raggiunge e fa da invito
    rn = FM - TH_H - 0.1
    prof += [(rn, Z_REC), (rn, SEAM + R_LIP - rn), (R_LIP, SEAM)]
    o = lathe(prof, name, C_STAMPA)
    # il filetto si scava con un solo booleano: nessuna faccia coincide con il guscio
    boolean(o, radial_solid(lambda t, z: thread_r(t, z, FM), Z_TH0 - 0.5, Z_TH1 + 0.5, "madrevite", C_STAMPA), 'DIFFERENCE')
    # dove il filetto sfiora la svasatura restano schegge minuscole che il booleano dei fori poi apre
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
    bmesh.ops.dissolve_degenerate(bm, dist=0.005, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o


def vite(name):
    """Metà di sotto: sfera dal polo a SEAM, spalla, cono a 45° e collare filettato."""
    a_s = math.degrees(math.asin(SEAM / R))
    zm = sphere_meet(BORE, Z_TH0, 1)                    # svasatura interna del collare verso la sfera
    a_m = math.degrees(math.asin(zm / RI))
    rc = TM - TH_H
    prof = [(0, -R)] + arc(R, -89.0, a_s) + [(R_LIP - CONE_GAP, SEAM), (FM - CONE_GAP, Z_TH0), (rc, Z_TH0),
                                            (rc, Z_COL), (BORE, Z_COL), (BORE, Z_TH0)]
    prof += [(math.sqrt(RI * RI - zm * zm), zm)] + arc(RI, a_m, -89.0) + [(0, -RI)]
    o = lathe(prof, name, C_STAMPA)
    th = radial_solid(lambda t, z: min(thread_r(t, z, TM), rc + 0.15 + (Z_COL - z)), Z_TH0 - 0.2, Z_COL - 0.1, "vite", C_STAMPA)
    core = lathe([(0, Z_TH0 - 1), (rc - 0.4, Z_TH0 - 1), (rc - 0.4, Z_COL + 1), (0, Z_COL + 1)], "anima", C_STAMPA)
    boolean(th, core, 'DIFFERENCE')
    boolean(o, th, 'UNION')
    return o, zm


def sfera_intera(name):
    """Voronoi: guscio unico con un piano d'appoggio sotto."""
    o = lathe([(0, -R)] + arc(R, -89.0, 89.0) + [(0, R), (0, RI)] + arc(RI, 89.0, -89.0) + [(0, -RI)], name, C_STAMPA)
    # le due sfere sono superfici separate: recalc le orienta entrambe verso fuori, la cavità va girata
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.calc_center_median().length < (R + RI) / 2])
    bm.to_mesh(o.data); bm.free()
    cut = lathe([(0, -R - 2), (R, -R - 2), (R, -R + VOR_FLAT), (0, -R + VOR_FLAT)], "piano", C_STAMPA)
    boolean(o, cut, 'DIFFERENCE')
    return o


# --- fori: poligoni sferici (versori) -> taglienti ----------------------
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def sph(phi, th):
    return np.array([math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)])


def chaikin(poly, it=2):
    for _ in range(it):
        nxt = np.roll(poly, -1, axis=0)
        poly = unit(np.stack([0.75 * poly + 0.25 * nxt, 0.25 * poly + 0.75 * nxt], axis=1).reshape(-1, 3))
    return poly


def densify(poly, step=0.8):
    out = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) * R / step)))
        out += [unit(a + (b - a) * t / n) for t in range(n)]
    return np.array(out)


def clip(poly, n, c):
    """Tiene n·p <= c (poligono chiuso di punti 3D)."""
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da, db = n @ a - c, n @ b - c
        if da <= 0:
            out.append(a)
        if (da < 0) != (db < 0) and da != db:
            out.append(a + da / (da - db) * (b - a))
    return np.array(out)


def resample(rail, m):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rail, axis=0), axis=1))]
    t = np.linspace(0, d[-1], m)
    return unit(np.stack([np.interp(t, d, rail[:, k]) for k in range(3)], axis=1))


def latlon_box(p1, p2, ta, tb, bar):
    """Foro fra le latitudini p1-p2 e le longitudini ta-tb, nervature larghe bar mm
    (bar negativo con ta = tb: fessura larga -bar attorno a ta)."""
    def side(p, t, s):
        return t + s * (bar / 2) / (R * math.cos(p))
    ps = np.linspace(p1, p2, max(3, int((p2 - p1) * R / 0.8)))
    def par(p, t0, t1):
        n = max(3, int(abs(t1 - t0) * R * math.cos(p) / 0.8))
        return [sph(p, t) for t in np.linspace(t0, t1, n)]
    pts = par(p1, side(p1, ta, 1), side(p1, tb, -1))
    pts += [sph(p, side(p, tb, -1)) for p in ps[1:-1]]
    pts += par(p2, side(p2, tb, -1), side(p2, ta, 1))
    pts += [sph(p, side(p, ta, 1)) for p in ps[::-1][1:-1]]
    return chaikin(np.array(pts), 2)


def stamp(shape, phi, th, rot=0.0):
    """Sagoma piana (x verso est, y verso nord, in mm) appoggiata sulla sfera nel punto (phi, th)."""
    c = sph(phi, th)
    if abs(phi) > math.radians(89.9):
        e1, e2 = np.array([-math.sin(th), math.cos(th), 0.0]), np.array([-math.cos(th), -math.sin(th), 0.0])
    else:
        e1 = np.array([-math.sin(th), math.cos(th), 0.0]); e2 = np.cross(c, e1)
    cr, sr = math.cos(rot), math.sin(rot)
    pts = [unit(c + ((x * cr - y * sr) * e1 + (x * sr + y * cr) * e2) / R) for x, y in shape]
    return densify(np.array(pts), 0.6)


def ellipse(cx, cy, a, b, rot=0.0, n=28):
    cr, sr = math.cos(rot), math.sin(rot)
    return [(cx + a * math.cos(t) * cr - b * math.sin(t) * sr, cy + a * math.cos(t) * sr + b * math.sin(t) * cr)
            for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def cutters(holes, name):
    """Un tagliente per foro: due binari lungo il bordo, uniti a strisce (corde corte) a r_in e r_out."""
    r_in, r_out = RI - 1.5, R + 4.0
    bm = bmesh.new()
    for poly in holes:
        dd = np.linalg.norm(poly[:, None] - poly[None], axis=2)
        i0, i1 = sorted(np.unravel_index(np.argmax(dd), dd.shape))
        left = poly[i0:i1 + 1]
        right = np.vstack([poly[i0::-1], poly[:i1 - 1:-1]]) if i0 > 0 else np.vstack([poly[:1], poly[:i1 - 1:-1]])
        ln = max(np.linalg.norm(np.diff(left, axis=0), axis=1).sum(), np.linalg.norm(np.diff(right, axis=0), axis=1).sum())
        m = max(4, int(ln * R / 0.8))
        L, Rr = resample(left, m), resample(right, m)
        vi = {}
        def vert(side, k, r):
            key = ('E0' if k == 0 else 'E1' if k == m - 1 else side, k, r)
            if key not in vi:
                vi[key] = bm.verts.new(tuple((L if side == 'L' else Rr)[k] * r))
            return vi[key]
        def face(q):
            q = [v for j, v in enumerate(q) if v not in q[:j]]
            if len(q) >= 3:
                bm.faces.new(q)
        for k in range(m - 1):
            for r in (r_in, r_out):
                face([vert('L', k, r), vert('L', k + 1, r), vert('R', k + 1, r), vert('R', k, r)])
            for s in ('L', 'R'):
                face([vert(s, k, r_in), vert(s, k + 1, r_in), vert(s, k + 1, r_out), vert(s, k, r_out)])
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, C_STAMPA)


def inscribed_d(poly):
    """Diametro del cerchio più grande che sta nel foro (proiezione sul piano tangente)."""
    dd = np.linalg.norm(poly[:, None] - poly[None], axis=2)
    if dd.max() > 0.9:                       # foro lungo (Elica): la proiezione non regge, misura in 3D dai punti medi fra i bordi
        i0, i1 = sorted(np.unravel_index(np.argmax(dd), dd.shape))
        left, right = resample(poly[i0:i1 + 1], 200), resample(np.vstack([poly[i1:], poly[:i0 + 1]])[::-1], 200)
        mids = unit((left + right) / 2)
        dense = densify(poly, 0.3)
        return 2 * R * float(np.linalg.norm(mids[:, None] - dense[None], axis=2).min(1).max())
    c = unit(poly.mean(axis=0))
    e1 = unit(np.cross(c, [0, 0, 1] if abs(c[2]) < 0.9 else [1, 0, 0]))
    e2 = np.cross(c, e1)
    p = poly / (poly @ c)[:, None] * R
    xy = np.stack([p @ e1, p @ e2], axis=1)
    lo, hi = xy.min(0), xy.max(0)
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0], 0.2), np.arange(lo[1], hi[1], 0.2))
    q = np.stack([gx.ravel(), gy.ravel()], axis=1)
    a, b = xy, np.roll(xy, -1, axis=0)
    inside = np.zeros(len(q), bool)
    for (x1, y1), (x2, y2) in zip(a, b):
        cond = (y1 > q[:, 1]) != (y2 > q[:, 1])
        xs = (x2 - x1) * (q[:, 1] - y1) / (y2 - y1 + 1e-12) + x1
        inside ^= cond & (q[:, 0] < xs)
    q = q[inside]
    if not len(q):
        return 0.0
    ab = b - a
    t = np.clip(((q[:, None] - a[None]) * ab[None]).sum(2) / (ab * ab).sum(1)[None], 0, 1)
    d = np.linalg.norm(q[:, None] - (a[None] + t[..., None] * ab[None]), axis=2).min(1)
    return 2 * float(d.max())


def min_strut(holes):
    """Nervatura più sottile: distanza minima fra i bordi di due fori diversi (mm sulla sfera)."""
    best = 99.0
    for i, a in enumerate(holes):
        for b in holes[i + 1:]:
            if np.linalg.norm(a.mean(0) - b.mean(0)) * R > 45:
                continue
            best = min(best, float(np.linalg.norm(a[:, None] - b[None], axis=2).min()) * R)
    return best


# --- i disegni: fori sulla calotta sopra la latitudine phi0 ---------------
def holes_spirale(phi0, n=10, frac=0.55, phi1=math.radians(62), twist=math.radians(90)):
    hw = frac * math.pi / n
    ps = np.linspace(phi0, phi1, 60)
    out = []
    for i in range(n):
        th = [2 * math.pi * i / n + twist * (p - phi0) / (phi1 - phi0) for p in ps]
        left = [sph(p, t - hw) for p, t in zip(ps, th)]
        right = [sph(p, t + hw) for p, t in zip(ps, th)]
        out.append(chaikin(np.array(left + right[::-1]), 3))
    return out


def holes_anelli(phi0, rows=4, rib_lat=2.8, ribs=10, rib_w=3.2, phi_cap=math.radians(72)):
    span = (phi_cap - phi0) * R
    h = (span - (rows - 1) * rib_lat) / rows
    out = []
    for r in range(rows):
        p1 = phi0 + r * (h + rib_lat) / R
        off = (math.pi / ribs) * (r % 2)                        # nervature sfalsate fra le file
        for i in range(ribs):
            out.append(latlon_box(p1, p1 + h / R, off + 2 * math.pi * i / ribs, off + 2 * math.pi * (i + 1) / ribs, rib_w))
    return out


def holes_griglia(phi0, cell=5.5, bar=1.8, pole_r=7.0):
    phi_p = math.acos(pole_r / R)
    out = [chaikin(np.array([sph(phi_p, t) for t in np.linspace(0, 2 * math.pi, 90, endpoint=False)]), 1)]
    span = (phi_p - phi0) * R - bar
    rows = int((span + bar) // cell)
    h = (span - (rows - 1) * bar) / rows
    for r in range(rows):
        p1 = phi0 + r * (h + bar) / R
        p2 = p1 + h / R
        n = int(round(2 * math.pi * R * math.cos((p1 + p2) / 2) / cell))
        for i in range(n):
            out.append(latlon_box(p1, p2, 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n, bar))
    return out


def holes_fessure(phi0, n=6, w=5.5, phi_long=math.radians(70), short=(math.radians(32), math.radians(56))):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        out.append(latlon_box(phi0, phi_long, t, t, -w))
        out.append(latlon_box(short[0], short[1], t + math.pi / n, t + math.pi / n, -w))
    return out


S_PAW = 1.35
PAW = [ellipse(0, -1.6, 4.2, 3.2)] + [ellipse(x, y, 1.3, 1.7, a) for x, y, a in
                                      [(-5.8, 3.0, 0.5), (-2.4, 5.4, 0.15), (2.4, 5.4, -0.15), (5.8, 3.0, -0.5)]]
PAW = [[(x * S_PAW, y * S_PAW) for x, y in part] for part in PAW]


def holes_zampette(phi0, n=5, lat=math.radians(40)):
    """Impronte di zampa: cuscinetto + quattro dita, in fila attorno e una sul polo."""
    out = []
    for i in range(n):
        th = 2 * math.pi * i / n
        for part in PAW:
            out.append(chaikin(stamp(part, lat + (0.06 if i % 2 else -0.06), th, 0.25 if i % 2 else -0.25), 1))
    for part in PAW:
        out.append(chaikin(stamp(part, math.radians(90), 0.0), 1))
    return out


FISH = ([(6.5 * math.cos(t), 3.6 * math.sin(t)) for t in np.linspace(math.radians(-155), math.radians(155), 30)]
        + [(-11.0, 3.8), (-8.6, 0.0), (-11.0, -3.8)])


def holes_pesciolini(phi0):
    """Pesciolini che nuotano in due file opposte e tre bolle verso il polo."""
    out = []
    for i in range(7):
        out.append(chaikin(stamp(FISH, math.radians(30), 2 * math.pi * i / 7, 0.0), 2))
    for i in range(4):
        out.append(chaikin(stamp(FISH, math.radians(57), 2 * math.pi * (i + 0.5) / 4, math.pi), 2))
    for (x, y, r) in [(-3.5, -2.0, 2.4), (2.8, 1.5, 1.9), (-1.0, 5.5, 1.5)]:
        out.append(stamp(ellipse(x, y, r, r), math.radians(90), 0.0))
    return out


def holes_voronoi(spacing=12.0, strut=2.6, seed=11, z_bottom=-R + 5.0):
    """Celle di Voronoi su tutta la sfera (pezzo unico); fondo pieno per l'appoggio."""
    rnd = random.Random(seed)
    sp = spacing / R
    pts = []
    for _ in range(40000):                                    # Poisson disk sulla sfera
        p = unit([rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)])
        if all(np.linalg.norm(p - q) >= sp for q in pts):
            pts.append(p)
    return cells(pts, sp, strut, z_bottom, 3)


def fibonacci(n):
    """n punti quasi equidistanti sulla sfera (spirale aurea)."""
    ga = math.pi * (3 - math.sqrt(5))
    return [unit([math.cos(ga * i) * math.sqrt(1 - z * z), math.sin(ga * i) * math.sqrt(1 - z * z), z])
            for i, z in enumerate(np.linspace(1 - 1 / n, -1 + 1 / n, n))]


def cells(pts, sp, strut, z_bottom, rounding):
    """Celle di Voronoi dei punti, ristrette di mezza nervatura e tagliate sotto z_bottom."""
    sd = math.sin(strut / 2 / R)
    out = []
    for s in pts:
        e1 = unit(np.cross(s, [0, 0, 1] if abs(s[2]) < 0.9 else [1, 0, 0])); e2 = np.cross(s, e1)
        poly = np.array([s + 1.5 * (math.cos(a) * e1 + math.sin(a) * e2) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)])
        for q in pts:
            if q is s or np.linalg.norm(q - s) > 3 * sp:
                continue
            poly = clip(poly, unit(q - s), -sd)
            if len(poly) < 3:
                break
        if len(poly) < 3:
            continue
        poly = densify(chaikin(unit(poly), rounding), 0.6)
        poly = clip(poly, np.array([0, 0, -1.0]), -(z_bottom / R))
        if len(poly) < 6:
            continue
        poly = unit(poly)
        dedup = [poly[0]]
        for p in poly[1:]:
            if np.linalg.norm(p - dedup[-1]) * R > 0.2:
                dedup.append(p)
        poly = chaikin(np.array(dedup), 1)
        if inscribed_d(poly) > 3.0:
            out.append(poly)
    return out


def holes_nido(phi0, n=130, strut=2.0):
    """Nido d'ape: le celle di Voronoi della spirale aurea sono quasi tutte esagoni."""
    pts = fibonacci(n)
    return cells(pts, math.sqrt(4 * math.pi / n) * 1.2, strut, R * math.sin(phi0), 1)


def scatter(phi0, n, half):
    """Centri (phi, th) della spirale aurea sulla calotta, con la sagoma (raggio half mm) tutta sopra phi0."""
    out = []
    for p in fibonacci(n):
        phi = math.asin(max(-1.0, min(1.0, p[2])))
        if phi - half / R >= phi0:
            out.append((phi, math.atan2(p[1], p[0])))
    return out


STAR = [((6.2 if k % 2 == 0 else 2.6) * math.sin(math.pi * k / 5), (6.2 if k % 2 == 0 else 2.6) * math.cos(math.pi * k / 5))
        for k in range(10)]
HEART = [(0.42 * 16 * math.sin(t) ** 3, 0.42 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) + 1.0)
         for t in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
MOUSE = [ellipse(0, -1.5, 4.6, 4.3), ellipse(-6.6, 4.8, 2.6, 2.6), ellipse(6.6, 4.8, 2.6, 2.6)]
BONE = ([[(-9.0, -1.2), (7.0, -1.2), (7.0, 1.2), (-9.0, 1.2)]]                                  # spina
        + [[(15.0, 0.0), (9.0, 3.6), (9.0, -3.6)]]                                              # testa
        + [[(-11.0, 0.0), (-15.5, 3.8), (-15.5, -3.8)]]                                         # coda
        + [[(x - 1.1, s * 3.2), (x + 1.1, s * 3.2), (x + 1.1 + 2.6, s * 8.6), (x - 1.1 + 2.6, s * 8.6)][::s]
           for x in (-6.0, -1.0, 4.0) for s in (1, -1)])                                         # costole inclinate verso la testa


def holes_stelle(phi0, n=44):
    rnd = random.Random(5)
    return [chaikin(stamp(STAR, phi, th, rnd.uniform(-0.6, 0.6)), 1) for phi, th in scatter(phi0, n, 6.6)]


def holes_cuori(phi0, n=32):
    rnd = random.Random(9)
    return [chaikin(stamp(HEART, phi, th, rnd.uniform(-0.35, 0.35)), 1) for phi, th in scatter(phi0, n, 7.0)]


def holes_topolini(phi0, n=24):
    out = []
    for phi, th in scatter(phi0, n, 9.6):
        out += [chaikin(stamp(part, phi, th), 1) for part in MOUSE]
    return out


def holes_lische(phi0, n=4, lat=math.radians(36)):
    """Lische di pesce in giro, testa a est, e una sul polo."""
    out = []
    for phi, th in [(lat, 2 * math.pi * i / n) for i in range(n)] + [(math.radians(90), 0.0)]:
        out += [chaikin(stamp(part, phi, th), 1) for part in BONE]
    return out


PHI_BOTTOM = math.asin((-R + 6.0) / R)              # pezzi unici: calotta piena sul fondo per l'appoggio


def holes_elica(n=12, frac=0.5, phi_top=math.radians(64), twist=math.pi):
    """Fessure che girano di mezzo giro da un polo all'altro, attraverso l'equatore."""
    hw = frac * math.pi / n
    p0 = PHI_BOTTOM + math.radians(4)
    ps = np.linspace(p0, phi_top, 90)
    out = []
    for i in range(n):
        th = [2 * math.pi * i / n + twist * (p - p0) / (phi_top - p0) for p in ps]
        left = [sph(p, t - hw * math.cos(p) ** -0.3) for p, t in zip(ps, th)]
        right = [sph(p, t + hw * math.cos(p) ** -0.3) for p, t in zip(ps, th)]
        out.append(chaikin(np.array(left + right[::-1]), 3))
    return out


def holes_rete(n=16, strut=2.2, phi_top=math.radians(58)):
    """Rombi fra due famiglie di lossodromiche: quadrati nella carta di Mercatore, che si stringono verso i poli."""
    a = math.pi / n
    psi = lambda p: math.log(math.tan(math.pi / 4 + p / 2))
    phi = lambda s: 2 * math.atan(math.exp(s)) - math.pi / 2
    out = []
    for j in range(int(psi(PHI_BOTTOM) / a) - 1, int(psi(phi_top) / a) + 2):
        sc = j * a
        h = a - strut / (math.sqrt(2) * R * math.cos(phi(sc)))   # nervatura costante in mm
        if h <= 0 or phi(sc - h) < PHI_BOTTOM + math.radians(2) or phi(sc + h) > phi_top:
            continue
        for i in range(n):
            tc = 2 * math.pi * i / n + (j % 2) * a
            corners = [(tc + h, sc), (tc, sc + h), (tc - h, sc), (tc, sc - h)]
            pts = []
            for (t0, s0), (t1, s1) in zip(corners, corners[1:] + corners[:1]):
                pts += [sph(phi(s0 + (s1 - s0) * k / 12), t0 + (t1 - t0) * k / 12) for k in range(12)]
            out.append(chaikin(np.array(pts), 2))
    return out


DESIGNS = [  # (numero, disegno, generatore, colore)
    ("P01", "Spirale", holes_spirale, (0.85, 0.12, 0.45)),
    ("P02", "Voronoi", holes_voronoi, (0.80, 0.04, 0.04)),
    ("P03", "Anelli", holes_anelli, (0.80, 0.62, 0.28)),
    ("P04", "Griglia", holes_griglia, (0.10, 0.20, 0.60)),
    ("P05", "Fessure", holes_fessure, (0.40, 0.80, 0.12)),
    ("P06", "Zampette", holes_zampette, (0.95, 0.55, 0.15)),
    ("P07", "Pesciolini", holes_pesciolini, (0.10, 0.65, 0.75)),
    ("P08", "Stelle", holes_stelle, (0.44, 0.28, 0.91)),
    ("P09", "Cuori", holes_cuori, (0.97, 0.51, 0.67)),
    ("P10", "Topolini", holes_topolini, (0.53, 0.56, 0.59)),
    ("P11", "Lische", holes_lische, (0.30, 0.67, 0.97)),
    ("P12", "NidoApe", holes_nido, (1.00, 0.88, 0.40)),
    ("P13", "Elica", holes_elica, (0.95, 0.45, 0.10)),
    ("P14", "Rete", holes_rete, (0.08, 0.55, 0.40)),
]
UNICI = {"Voronoi", "Elica", "Rete"}                 # pezzo unico: il disegno attraversa l'equatore, sonaglio in pausa di stampa


def mat(name, rgb, metal=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = (*rgb, 1)
    for inp in bsdf.inputs:
        if inp.identifier == "Metallic":
            inp.default_value = metal
        elif inp.identifier == "Roughness":
            inp.default_value = 0.35
    return m


def info(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    co = [o.matrix_world @ v.co for v in o.data.vertices]
    mn = [min(c[i] for c in co) for i in range(3)]; mx = [max(c[i] for c in co) for i in range(3)]
    return {"min": [round(a, 2) for a in mn], "max": [round(a, 2) for a in mx],
            "size": [round(b - a, 2) for a, b in zip(mn, mx)], "volume_mm3": round(vol),
            "peso_PETG_g": round(vol * 1.27e-3, 1), "non_manifold_edges": nm}


def gap(a, b, samples=6000):
    """Distanza minima approssimata fra due mesh in posa di montaggio."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new(); bm.from_mesh(b.data)
    tb = BVHTree.FromBMesh(bm); bm.free()
    inv = b.matrix_world.inverted()
    vs = a.data.vertices
    step = max(1, len(vs) // samples)
    return round(min(tb.find_nearest(inv @ (a.matrix_world @ vs[i].co))[3] for i in range(0, len(vs), step)), 2)


geo = {"diametro_mm": 2 * R, "parete_mm": WALL, "sonaglio_d_mm": 2 * BALL_R,
       "giunto": {"quota_mm": SEAM, "passo_mm": TH_P, "profondita_mm": TH_H, "lunghezza_mm": TH_L,
                  "gioco_radiale_mm": TH_GAP, "svasatura_mm": round(CS, 2)},
       "pezzi": {}, "fori": {}}
pieces = {}                                          # nome -> (oggetto, matrice di stampa)
groups = []                                          # (disegno, [(oggetto, matrice di montaggio)], colore)

base = madrevite("tmp_madrevite")
base_v, zm = vite("tmp_vite")
phi_f = math.asin((Z_REC + 1.5) / R)                 # fori della madrevite sopra la sede
phi_m = math.asin((-zm + 1.5) / R)                   # fori della vite sotto la svasatura interna
flip = Matrix.Rotation(math.pi, 4, 'X')

for num, label, gen, rgb in DESIGNS:
    m = mat("M_" + label, rgb, 0.6 if label == "Anelli" else 0.0)
    if label in UNICI:
        o = sfera_intera(f"{num}_{label}")
        holes = gen()
        allh = holes
        boolean(o, cutters(holes, "fori_" + label), 'DIFFERENCE', tolerant=True)
        o.data.materials.clear(); o.data.materials.append(m)   # il booleano lascia uno slot vuoto
        pieces[o.name] = (o, Matrix.Translation((0, 0, R - VOR_FLAT)))
        groups.append((label, [(o, Matrix())], rgb))
    else:
        top = base.copy(); top.data = base.data.copy(); top.name = top.data.name = f"{num}_{label}_Madrevite"
        bot = base_v.copy(); bot.data = base_v.data.copy(); bot.name = bot.data.name = f"{num}_{label}_Vite"
        for o in (top, bot):
            C_STAMPA.objects.link(o)
        ht = gen(phi_f)
        hb = [h * np.array([1, 1, -1]) for h in gen(phi_m)]          # calotta di sotto: stesso disegno specchiato
        allh = ht + hb
        boolean(top, cutters(ht, "fori_su_" + label), 'DIFFERENCE', tolerant=True)
        boolean(bot, cutters(hb, "fori_giu_" + label), 'DIFFERENCE', tolerant=True)
        for o in (top, bot):
            o.data.materials.clear(); o.data.materials.append(m)   # il booleano lascia uno slot vuoto
        pieces[top.name] = (top, Matrix.Translation((0, 0, -SEAM)))
        pieces[bot.name] = (bot, Matrix.Translation((0, 0, Z_COL)) @ flip)
        groups.append((label, [(top, Matrix()), (bot, Matrix.Rotation(math.radians(20), 4, 'Z'))], rgb))
    dmax = max(inscribed_d(h) for h in allh)
    geo["fori"][label] = {"n": len(allh), "max_cerchio_inscritto_mm": round(dmax, 2),
                          "nervatura_min_mm": round(min_strut(allh), 2),
                          "sonaglio_resta_dentro": dmax < 2 * BALL_R - 2}
    print(label, geo["fori"][label])

# giochi del giunto, misurati in posa di montaggio sui pezzi senza fori
geo["giunto"]["distanza_min_mm"] = gap(base_v, base)
for o in (base, base_v):
    bpy.data.objects.remove(o)

# sonaglio: sfera piena con un piano d'appoggio sotto
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=BALL_R)
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -BALL_R + BALL_FLAT),
                       plane_no=(0, 0, 1), clear_inner=True)
bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary])
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, BALL_R - BALL_FLAT))
bball = obj_from_bm(bm, "P15_Sonaglio", C_STAMPA)
bball.data.materials.append(mat("M_Sonaglio", (0.03, 0.03, 0.03)))
pieces[bball.name] = (bball, Matrix())

# Voronoi: pausa di stampa appena sopra la cima del sonaglio, appoggiato sul fondo della cavità
ball_top = -RI + 2 * BALL_R - BALL_FLAT + 0.2
for label in UNICI:
    geo["fori"][label]["pausa_per_sonaglio_mm"] = round(math.ceil((ball_top + 0.8 - (-R + VOR_FLAT)) / 0.2) * 0.2, 1)

# --- palline montate, file da quattro ----------------------------
for i, (label, parts, rgb) in enumerate(groups):
    x, y = ((i % 4) - 1.5) * 70.0, -70.0 * (i // 4)
    for o, mw in parts:
        d = bpy.data.objects.new(f"{label}_{o.name.split('_')[-1]}", o.data)
        d.matrix_world = Matrix.Translation((x, y, R - VOR_FLAT * 0)) @ mw
        C_MONT.objects.link(d)
    d = bpy.data.objects.new(f"{label}_sonaglio", bball.data)
    d.location = (x, y, R - RI + BALL_FLAT - 0.6)
    C_MONT.objects.link(d)

# --- STL in posa di stampa --------------------------------------------------
def write_stl(o, mp, path):
    """STL binario scritto dalla mesh: l'operatore di export col Blender aperto non vede la collezione nascosta."""
    import struct
    me = o.data
    me.calc_loop_triangles()
    with open(path, "wb") as f:
        f.write(b"Palline Traforate".ljust(80, b" "))
        f.write(struct.pack("<I", len(me.loop_triangles)))
        rot = mp.to_3x3()
        for t in me.loop_triangles:
            f.write(struct.pack("<3f", *(rot @ t.normal).normalized()))
            for vi in t.vertices:
                f.write(struct.pack("<3f", *(mp @ me.vertices[vi].co)))
            f.write(b"\0\0")


for n, (o, mp) in pieces.items():
    bm = bmesh.new(); bm.from_mesh(o.data)            # il filetto lascia vertici doppi: chiusa per Blender, aperta per gli slicer
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data); bm.free()
    o.matrix_world = mp
    bpy.context.view_layer.update()
    geo["pezzi"][n] = info(o)
    write_stl(o, mp, os.path.join(STL, n + ".stl"))
    o.matrix_world = Matrix()

with open(os.path.join(ROOT, "dati", "geometria.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, indent=1, ensure_ascii=False)
print("GEOMETRIA", json.dumps(geo))

path = os.path.join(ROOT, "blender", "costruisci.py")
txt = bpy.data.texts.get("costruisci.py") or bpy.data.texts.new("costruisci.py")
txt.from_string(open(path, encoding="utf-8").read())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "Palline_Traforate.blend"))
