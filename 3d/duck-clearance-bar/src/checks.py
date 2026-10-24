"""Verification of the design and of the written files."""
import itertools
import os
import zipfile

import numpy as np
import manifold3d as mf
import trimesh
from lxml import etree
from shapely.geometry import Polygon, box

from design import polys, union
from export import COLOR_ORDER, FILAMENT, PLATE, EDGE_MARGIN, Z

NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}


def check_2d(lay, piece_cols):
    p = lay.p
    rep = {'keepout': [], 'overlap': [], 'thin': [], 'small': [], 'notes': []}
    rings = lay.parts_raw['rings']
    for i, (P, d) in enumerate(zip(lay.pieces, piece_cols)):
        # hanging holes are required to carry their rings, so the keep-out is
        # measured from the outer outline (sockets included) with holes filled.
        # Exact distances: GEOS simplifies inputs slightly when buffering.
        edge = union(*[Polygon(q.exterior) for q in polys(P)]).exterior
        for c in ('orange', 'green', 'black'):
            g = d.get(c)
            if g is None:
                continue
            nb = g.difference(lay.bars.buffer(1e-3))
            full = g   # with bars, so outlines that merge into a bar count as attached
            for q in polys(nb):
                dist = q.distance(edge)
                if dist < p.edge_keepout - 1e-3:
                    rep['keepout'].append((i + 1, c, round(dist, 4), [round(x, 2) for x in q.bounds]))
            # thin parts: elongated pieces an opening at min_feature removes
            # (small corner trims at sharp tips are expected and ignored)
            r = p.min_feature / 2
            op = full.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
            lost = nb.difference(op.buffer(2e-3))
            thin = []
            for q in polys(lost):
                if q.area < 0.02 or 2 * q.area / q.length < 0.01:
                    continue   # corner trims or numerical hairlines
                mrr = q.minimum_rotated_rectangle
                xs, ys = mrr.exterior.coords.xy
                sides = sorted({round(((xs[k + 1] - xs[k]) ** 2 + (ys[k + 1] - ys[k]) ** 2) ** 0.5, 3) for k in range(4)})
                if sides[-1] > 1.2:
                    thin.append((round(q.area, 3), [round(x, 1) for x in q.bounds]))
            if thin:
                rep['thin'].append((i + 1, c, thin))
            sm = [q for q in polys(g) if q.area < p.min_area]
            if sm:
                rep['small'].append((i + 1, c, len(sm)))
        for a, b in itertools.combinations(('orange', 'green', 'black'), 2):
            if a in d and b in d:
                ov = d[a].intersection(d[b]).area
                if ov > 1e-4:
                    rep['overlap'].append((i + 1, a, b, ov))
    return rep


def min_stroke(geom, lo=0.1, hi=2.0, iters=30):
    """Thinnest stroke: twice the smallest erosion radius that splits or erases a part."""
    n0 = len([q for q in polys(geom) if q.area > 1e-6])
    for _ in range(iters):
        m = (lo + hi) / 2
        e = geom.buffer(-m, quad_segs=32)
        n = len([q for q in polys(e) if q.area > 1e-6])
        if n == n0:
            lo = m
        else:
            hi = m
    return 2 * lo


def bonk_stroke_check(bonk, stroke=1.0):
    """Strokes >= `stroke`: eroding by stroke/2 must not split or erase any glyph part,
    and a `stroke` opening may only trim corner tips (reported: largest trimmed piece)."""
    r = stroke / 2
    n0 = len([q for q in polys(bonk) if q.area > 1e-6])
    n1 = len([q for q in polys(bonk.buffer(-r, quad_segs=32)) if q.area > 1e-6])
    op = bonk.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)
    lost = bonk.difference(op)
    return dict(no_split_at_stroke=(n0 == n1), parts=n0,
                largest_trim_mm2=round(max((q.area for q in polys(lost)), default=0.0), 3))


def frame_gap_check(lay, min_gap=0.6):
    """Yellow gaps inside the duck's black: report any narrower than min_gap."""
    d = lay.parts_raw['duck']
    black = lay.colors['black'].intersection(d['sil'].buffer(0.5))
    closed = black.buffer(min_gap / 2).buffer(-min_gap / 2)
    added = closed.difference(black.buffer(1e-3))
    # ignore the sign's outer area (closing can't add outside the silhouette meaningfully)
    added = added.intersection(d['sil'])
    return [q for q in polys(added) if q.area > 0.02]


def _manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, dtype=np.float32),
                               tri_verts=np.asarray(m.faces, dtype=np.uint32)))


def overlap_volume(a, b):
    try:
        return (_manifold(a) ^ _manifold(b)).volume()
    except Exception:
        return float('nan')


def check_stls(paths):
    out = []
    meshes = {}
    for pth in paths:
        m = trimesh.load(pth, force='mesh')
        comps = m.split(only_watertight=False)
        out.append(dict(file=os.path.basename(pth), watertight=bool(m.is_watertight),
                        volume=float(m.volume), bounds=m.bounds.round(3).tolist(),
                        components=len(comps)))
        meshes[os.path.basename(pth)] = m
    return out, meshes


def parse_3mf(path):
    """Independent 3MF reader: returns objects with parts (vertices, faces, extruder, name)."""
    z = zipfile.ZipFile(path)
    names = z.namelist()
    model = etree.fromstring(z.read('3D/3dmodel.model'))
    cfg = etree.fromstring(z.read('Metadata/model_settings.config'))
    rels = etree.fromstring(z.read('_rels/.rels'))
    ct = etree.fromstring(z.read('[Content_Types].xml'))
    meshes, comps = {}, {}
    for obj in model.find('m:resources', NS).findall('m:object', NS):
        oid = int(obj.get('id'))
        mesh = obj.find('m:mesh', NS)
        if mesh is not None:
            v = np.array([[float(e.get('x')), float(e.get('y')), float(e.get('z'))]
                          for e in mesh.find('m:vertices', NS)])
            f = np.array([[int(e.get('v1')), int(e.get('v2')), int(e.get('v3'))]
                          for e in mesh.find('m:triangles', NS)])
            meshes[oid] = (v, f)
        cs = obj.find('m:components', NS)
        if cs is not None:
            comps[oid] = [(int(c.get('objectid')), c.get('transform')) for c in cs]
    items = [(int(i.get('objectid')), i.get('transform')) for i in model.find('m:build', NS)]

    def mat(t):
        a = [float(x) for x in t.split()]
        M = np.eye(4)
        for col in range(4):
            for row in range(3):
                M[row, col] = a[col * 3 + row]
        return M

    cfg_objs = {}
    for o in cfg.findall('object'):
        oid = int(o.get('id'))
        meta = {m.get('key'): m.get('value') for m in o.findall('metadata')}
        parts = {}
        for pt in o.findall('part'):
            pm = {m.get('key'): m.get('value') for m in pt.findall('metadata')}
            parts[int(pt.get('id'))] = dict(subtype=pt.get('subtype'), **pm)
        cfg_objs[oid] = dict(meta=meta, parts=parts)
    objects = []
    for oid, t in items:
        B = mat(t)
        o = dict(id=oid, name=cfg_objs[oid]['meta'].get('name'), parts=[])
        for pid, ct_ in comps[oid]:
            C = mat(ct_)
            v, f = meshes[pid]
            vh = np.c_[v, np.ones(len(v))] @ (B @ C).T
            pc = cfg_objs[oid]['parts'][pid]
            o['parts'].append(dict(id=pid, name=pc.get('name'), extruder=int(pc.get('extruder')),
                                   mesh=trimesh.Trimesh(vh[:, :3], f, process=True)))
        objects.append(o)
    meta = {m.get('name'): m.text for m in model.findall('m:metadata', NS)}
    return dict(entries=names, objects=objects, metadata=meta,
                rels=[(r.get('Target'), r.get('Type')) for r in rels],
                content_types=[e.get('Extension') for e in ct])


def check_3mf(path, expect_names):
    info = parse_3mf(path)
    rep = dict(entries=info['entries'], metadata=info['metadata'], objects=[])
    allb = []
    for o in info['objects']:
        orep = dict(name=o['name'], parts=[])
        meshes = []
        for pt in o['parts']:
            m = pt['mesh']
            b = m.bounds
            allb.append(b)
            orep['parts'].append(dict(name=pt['name'], extruder=pt['extruder'], watertight=bool(m.is_watertight),
                                      volume=round(float(m.volume), 2), z=(round(b[0][2], 3), round(b[1][2], 3))))
            meshes.append(m)
        allm = trimesh.util.concatenate(meshes)
        bb = allm.bounds
        orep['bbox'] = bb.round(3).tolist()
        orep['length_x'] = round(bb[1][0] - bb[0][0], 3)
        ov = []
        for (i, a), (j, b) in itertools.combinations(enumerate(meshes), 2):
            vol = overlap_volume(a, b)
            ov.append((o['parts'][i]['name'].split(' - ')[-1], o['parts'][j]['name'].split(' - ')[-1], vol))
        orep['overlaps'] = ov
        rep['objects'].append(orep)
    lo = np.min([b[0] for b in allb], axis=0)
    hi = np.max([b[1] for b in allb], axis=0)
    rep['plate_bounds'] = [lo.round(3).tolist(), hi.round(3).tolist()]
    rep['inside_plate_with_margin'] = bool(lo[0] >= EDGE_MARGIN - 1e-6 and lo[1] >= EDGE_MARGIN - 1e-6 and
                                           hi[0] <= PLATE - EDGE_MARGIN + 1e-6 and hi[1] <= PLATE - EDGE_MARGIN + 1e-6)
    rep['names_ok'] = [o['name'] for o in info['objects']] == expect_names
    return rep, info


def object_gaps(info):
    """Minimum XY gap between object bounding boxes (rows are separated in Y)."""
    bbs = []
    for o in info['objects']:
        m = trimesh.util.concatenate([p['mesh'] for p in o['parts']])
        bbs.append(m.bounds)
    gaps = []
    for a, b in itertools.combinations(range(len(bbs)), 2):
        A, B = bbs[a], bbs[b]
        dx = max(0.0, max(A[0][0], B[0][0]) - min(A[1][0], B[1][0]))
        dy = max(0.0, max(A[0][1], B[0][1]) - min(A[1][1], B[1][1]))
        gaps.append(((a + 1, b + 1), round(max(dx, dy), 3)))
    return gaps, bbs


def layer_colors(info, layer_h=0.2, first_layer=0.2):
    """Colors whose parts cover each print layer (by z-range of the part meshes)."""
    zs = []
    parts = [(p['extruder'], p['mesh'].bounds[0][2], p['mesh'].bounds[1][2]) for o in info['objects'] for p in o['parts']]
    top = max(z1 for _, _, z1 in parts)
    z = first_layer
    k = 1
    while z <= top + 1e-6:
        mid = z - layer_h / 2
        cols = sorted({e for e, z0, z1 in parts if z0 < mid < z1})
        zs.append((k, round(z - layer_h, 2), round(z, 2), cols))
        z += layer_h
        k += 1
    return zs


def min_swaps(layers, start=None):
    """Exact minimum number of filament changes over the layer sequence (DP over last color)."""
    from functools import lru_cache
    seq = [tuple(c) for _, _, _, c in layers if c]

    @lru_cache(None)
    def best(i, last):
        if i == len(seq):
            return 0, ()
        cols = seq[i]
        res = None
        for perm in itertools.permutations(cols):
            cost = 0
            prev = last
            for c in perm:
                if prev is not None and c != prev:
                    cost += 1
                prev = c
            sub, order = best(i + 1, perm[-1])
            tot = cost + sub
            if res is None or tot < res[0]:
                res = (tot, (perm,) + order)
        return res

    return best(0, start)


def grams(piece_cols, infill=0.15, walls=2, line_w=0.42, layer_h=0.2, top_layers=5, bottom_layers=3, density=1.24):
    """Rough filament mass per color (PLA)."""
    out = {}
    for c in COLOR_ORDER:
        vol = 0.0
        for d in piece_cols:
            g = d.get(c)
            if g is None:
                continue
            z0, z1 = Z[c]
            h = z1 - z0
            A = g.area
            per = sum(q.length for q in [g.boundary])
            wall_area = min(A, per * walls * line_w)
            solid_h = min(h, (top_layers + bottom_layers) * layer_h)
            core_h = max(0.0, h - solid_h)
            vol += wall_area * h + (A - wall_area) * (solid_h + core_h * infill)
        out[c] = vol * density / 1000.0
    return out
