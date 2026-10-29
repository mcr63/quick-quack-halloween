"""Verification of the written files (adapted from the DUCK! bar's checks.py)."""
import itertools
import os
import zipfile

import numpy as np
import manifold3d as mf
import trimesh
from lxml import etree
from shapely.geometry import box

from export import PLATE, EDGE_MARGIN, TOWER

NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}


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


def check_plate(path, tower=None):
    """Reload a plate 3MF and check meshes, overlaps, plate margins, gaps and the tower area."""
    info = parse_3mf(path)
    rep = dict(file=os.path.basename(path), entries=info['entries'], objects=[])
    allb, obbs = [], []
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
        obbs.append(bb)
        orep['size'] = (bb[1] - bb[0]).round(2).tolist()
        orep['overlaps'] = [(o['parts'][i]['name'].split(' - ')[-1], o['parts'][j]['name'].split(' - ')[-1],
                             round(overlap_volume(a, b), 6))
                            for (i, a), (j, b) in itertools.combinations(enumerate(meshes), 2)]
        rep['objects'].append(orep)
    lo = np.min([b[0] for b in allb], axis=0)
    hi = np.max([b[1] for b in allb], axis=0)
    rep['plate_bounds'] = [lo.round(3).tolist(), hi.round(3).tolist()]
    rep['inside_plate_with_margin'] = bool(lo[0] >= EDGE_MARGIN - 1e-6 and lo[1] >= EDGE_MARGIN - 1e-6 and
                                           hi[0] <= PLATE - EDGE_MARGIN + 1e-6 and hi[1] <= PLATE - EDGE_MARGIN + 1e-6
                                           and lo[2] >= -1e-6)
    gaps = []
    for (a, A), (b, B) in itertools.combinations(enumerate(obbs), 2):
        dx = max(0.0, max(A[0][0], B[0][0]) - min(A[1][0], B[1][0]))
        dy = max(0.0, max(A[0][1], B[0][1]) - min(A[1][1], B[1][1]))
        gaps.append(((a + 1, b + 1), round(max(dx, dy), 3)))
    rep['object_gaps'] = gaps
    if tower:
        tb = box(*tower)
        hit = [o['name'] for o, bb in zip(info['objects'], obbs)
               if box(bb[0][0], bb[0][1], bb[1][0], bb[1][1]).intersects(tb)]
        rep['tower_box'] = [round(x, 2) for x in tower]
        rep['tower_clear_ok'] = bool(not hit and tower[2] - tower[0] >= TOWER and tower[3] - tower[1] >= TOWER)
    layers = layer_colors(info)
    rep['raised_layers'] = [l for l in layers if l[1] >= 2.99]
    rep['first_layers'] = sorted({tuple(l[3]) for l in layers if l[2] <= 3.0 + 1e-6})
    sw, _ = min_swaps(layers)
    rep['min_swaps'] = sw
    return rep, info


def grams_mesh(m, infill=0.15, shell=0.85, density=1.24):
    """Rough PLA mass: a ~0.85 mm solid shell (walls, top, bottom) plus sparse infill inside."""
    V = float(m.volume)
    solid = min(V, float(m.area) * shell)
    return (solid + infill * (V - solid)) * density / 1000.0


def grams_flat(geom_area, perimeter, h, infill=0.15, walls=2, line_w=0.42, layer_h=0.2,
               top_layers=5, bottom_layers=3, density=1.24):
    wall_area = min(geom_area, perimeter * walls * line_w)
    solid_h = min(h, (top_layers + bottom_layers) * layer_h)
    core_h = max(0.0, h - solid_h)
    vol = wall_area * h + (geom_area - wall_area) * (solid_h + core_h * infill)
    return vol * density / 1000.0
