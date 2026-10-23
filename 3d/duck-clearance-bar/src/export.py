"""Meshes, plate layout, Bambu Studio 3MF, STLs and preview images.

3MF format notes (checked against BambuStudio master, src/libslic3r/Format/bbs_3mf.cpp
and src/slic3r/GUI/Plater.cpp):
  * The importer always parses Metadata/model_settings.config. Each
    <object id=N> matches the build-item object id; each <part id=M> matches
    the component's mesh object id; <metadata key="extruder" value="k"/> under a
    part is applied with volume->config.set_deserialize (the part's filament).
  * A file counts as "from Bambu Studio" only when 3D/3dmodel.model carries
    <metadata name="Application">BambuStudio-x.y.z</metadata>. We do not claim
    that. Without it (and without Metadata/project_settings.config) Bambu
    Studio warns "not from Bambu Lab, load geometry data and color data only",
    keeps object/part names and per-part extruders, and recentres the whole
    group on the bed (relative layout kept). Our layout is already centred.
  * Metadata/project_settings.config is optional. If present it is merged over
    FullPrintConfig defaults and loaded as the current printer/filament/process
    presets, so a minimal one would reset the user's P2S settings. Left out.
"""
import io
import json
import math
import os
import zipfile
from datetime import date
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import manifold3d as mf
import trimesh
from PIL import Image, ImageDraw, ImageFont

from design import polys
from render import Canvas, hex2rgb

COLOR_ORDER = ['yellow', 'orange', 'green', 'black']
FILAMENT = {'yellow': 1, 'orange': 2, 'green': 3, 'black': 4}
HEX = {'yellow': '#FFCF42', 'orange': '#F79239', 'green': '#007550', 'black': '#1A1A1A'}
Z = {'yellow': (0.0, 3.0), 'orange': (3.0, 3.2), 'green': (3.0, 3.4), 'black': (3.0, 3.6)}

PLATE = 256.0
EDGE_MARGIN = 5.0
ROW_GAP = 8.0
TOWER = 55.0


# ---------------------------------------------------------------- meshes

def extrude(geom, z0, z1):
    rings = []
    for p in polys(geom):
        rings.append(np.asarray(p.exterior.coords)[:-1])
        for r in p.interiors:
            rings.append(np.asarray(r.coords)[:-1])
    if not rings:
        return None
    cs = mf.CrossSection(rings, mf.FillRule.EvenOdd)
    m = mf.Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    return trimesh.Trimesh(v, f, process=True)


def piece_meshes(piece_cols):
    """piece_cols: list of dict color->geom. Returns list of dict color->Trimesh (sign coords)."""
    out = []
    for d in piece_cols:
        md = {}
        for c in COLOR_ORDER:
            if c in d:
                m = extrude(d[c], *Z[c])
                if m is not None and len(m.faces):
                    md[c] = m
        out.append(md)
    return out


# ---------------------------------------------------------------- plate

def plate_layout(pieces, order=(2, 1, 0)):
    """Rows along X, centred on the plate; the shortest piece sits in the back row
    with the prime-tower area to its right.

    order: piece indices from back (high Y) to front. Returns (offsets, tower_box)
    where offsets[i] maps sign coords of piece i to plate coords (dx, dy).
    """
    bbs = [P.bounds for P in pieces]
    widths = [b[2] - b[0] for b in bbs]
    hts = [b[3] - b[1] for b in bbs]
    total_h = sum(hts) + ROW_GAP * (len(pieces) - 1)
    wmax = max(widths)
    x_left = (PLATE - wmax) / 2
    y_top = (PLATE + total_h) / 2
    offsets = [None] * len(pieces)
    y = y_top
    rows = []
    for i in order:
        b = bbs[i]
        y -= hts[i]
        offsets[i] = (x_left - b[0], y - b[1])
        rows.append((i, y, y + hts[i]))
        y -= ROW_GAP
    # tower area: right of the piece in the back row
    i0, y0, y1 = rows[0]
    right = x_left + widths[i0] + 6.0
    tower = (right, y0, PLATE - EDGE_MARGIN, y1)
    return offsets, tower


# ---------------------------------------------------------------- STL

def write_stls(meshes, offsets, out_dir, prefix='DUCK'):
    paths = []
    for k, c in enumerate(COLOR_ORDER, start=1):
        parts = []
        for md, (dx, dy) in zip(meshes, offsets):
            if c in md:
                m = md[c].copy()
                m.apply_translation((dx, dy, 0))
                parts.append(m)
        if not parts:
            continue
        m = trimesh.util.concatenate(parts)
        path = os.path.join(out_dir, f'{prefix}_{k}_{c}.stl')
        m.export(path)
        paths.append(path)
    zpath = os.path.join(out_dir, 'DUCK_clearance_STLs.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    return paths, zpath


# ---------------------------------------------------------------- 3MF

def _mesh_xml(obj_id, mesh, name):
    v = mesh.vertices
    f = mesh.faces
    out = [f'  <object id="{obj_id}" type="model">\n   <mesh>\n    <vertices>\n']
    out += [f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>\n' for x, y, z in v]
    out.append('    </vertices>\n    <triangles>\n')
    out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in f]
    out.append('    </triangles>\n   </mesh>\n  </object>\n')
    return ''.join(out)


def write_3mf(path, names, meshes, offsets, title, thumbnail_png=None):
    """Bambu Studio 3MF: one object per piece, one part per color with its filament."""
    model = []
    model.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    model.append('<model unit="millimeter" xml:lang="en-US" '
                 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
                 'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n')
    today = date.today().isoformat()
    meta = {
        'Application': 'duck-sign generator (python)',
        'BambuStudio:3mfVersion': '1',
        'Title': title,
        'CreationDate': today,
        'ModificationDate': today,
    }
    for k, v in meta.items():
        model.append(f' <metadata name="{k}">{escape(v)}</metadata>\n')
    model.append(' <resources>\n')
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    build = []
    next_id = 1
    for name, md, (dx, dy) in zip(names, meshes, offsets):
        # object-local frame: XY centre of the piece's bounding box, z from 0
        allv = np.vstack([m.vertices for m in md.values()])
        lo, hi = allv.min(axis=0), allv.max(axis=0)
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        part_ids = []
        for c in COLOR_ORDER:
            if c not in md:
                continue
            m = md[c].copy()
            m.apply_translation((-cx, -cy, 0))
            model.append(_mesh_xml(next_id, m, f'{name} {c}'))
            part_ids.append((next_id, c, len(m.faces)))
            next_id += 1
        obj_id = next_id
        next_id += 1
        model.append(f'  <object id="{obj_id}" type="model">\n   <components>\n')
        for pid, c, _ in part_ids:
            model.append(f'    <component objectid="{pid}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n')
        model.append('   </components>\n  </object>\n')
        px, py = cx + dx, cy + dy
        build.append(f'  <item objectid="{obj_id}" transform="1 0 0 0 1 0 0 0 1 {px:.5f} {py:.5f} 0" printable="1"/>\n')
        # model_settings.config
        cfg.append(f'  <object id="{obj_id}">\n')
        cfg.append(f'    <metadata key="name" value={quoteattr(name)}/>\n')
        cfg.append('    <metadata key="extruder" value="1"/>\n')
        for pid, c, nf in part_ids:
            cfg.append(f'    <part id="{pid}" subtype="normal_part">\n')
            pname = f'{name} - {c} (F{FILAMENT[c]})'
            cfg.append(f'      <metadata key="name" value={quoteattr(pname)}/>\n')
            cfg.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n')
            cfg.append(f'      <metadata key="extruder" value="{FILAMENT[c]}"/>\n')
            cfg.append(f'      <mesh_stat face_count="{nf}" edges_fixed="0" degenerate_facets="0" '
                       'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n')
            cfg.append('    </part>\n')
        cfg.append('  </object>\n')
    model.append(' </resources>\n <build>\n')
    model += build
    model.append(' </build>\n</model>\n')
    cfg.append('</config>\n')

    content_types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                     ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                     ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                     ' <Default Extension="png" ContentType="image/png"/>\n'
                     ' <Default Extension="config" ContentType="text/xml"/>\n'
                     '</Types>')
    rels = ['<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n']
    if thumbnail_png:
        rels.append(' <Relationship Target="/Metadata/plate_1.png" Id="rel-2" '
                    'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n')
    rels.append('</Relationships>')

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', ''.join(rels))
        z.writestr('3D/3dmodel.model', ''.join(model))
        z.writestr('Metadata/model_settings.config', ''.join(cfg))
        if thumbnail_png:
            z.writestr('Metadata/plate_1.png', thumbnail_png)
    return path


# ---------------------------------------------------------------- previews

def _font(size):
    for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
              '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def preview_sign(lay, piece_cols, path, width_px=3000):
    p = lay.p
    m = 4.0
    k = width_px / (lay.L + 2 * m)
    cv = Canvas(-m, -m, lay.L + m, p.H + m, k, bg=(255, 255, 255))
    for d in piece_cols:
        for c in COLOR_ORDER:
            if c in d:
                cv.fill(d[c], hex2rgb(HEX[c]))
    for P in lay.pieces:
        cv.outline(P, (150, 150, 150), 2)
    cv.img.save(path)
    return cv.img


def preview_plate(lay, piece_cols, offsets, tower, path, px=1600):
    import shapely.affinity as aff
    k = px / PLATE
    cv = Canvas(0, 0, PLATE, PLATE, k, bg=(236, 236, 236))
    d = ImageDraw.Draw(cv.img)
    # 10 mm grid
    for g in range(0, int(PLATE) + 1, 10):
        a = cv.to_px([(g, 0), (g, PLATE)])
        b = cv.to_px([(0, g), (PLATE, g)])
        col = (215, 215, 215) if g % 50 else (195, 195, 195)
        d.line(a, fill=col, width=1)
        d.line(b, fill=col, width=1)
    for dc, (dx, dy) in zip(piece_cols, offsets):
        for c in COLOR_ORDER:
            if c in dc:
                cv.fill(aff.translate(dc[c], dx, dy), hex2rgb(HEX[c]))
    for P, (dx, dy) in zip(lay.pieces, offsets):
        cv.outline(aff.translate(P, dx, dy), (90, 90, 90), 2)
    # plate outline and usable-area margin
    cv.line([(0, 0), (PLATE, 0), (PLATE, PLATE), (0, PLATE), (0, 0)], (0, 0, 0), 4)
    m = EDGE_MARGIN
    _dashed(cv, [(m, m), (PLATE - m, m), (PLATE - m, PLATE - m), (m, PLATE - m), (m, m)], (120, 120, 120), 2)
    # prime tower area
    x0, y0, x1, y1 = tower
    cv.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], (200, 40, 40), 4)
    f = _font(int(k * 4.2))
    tx, ty = cv.to_px([(x0 + 2, y1 - 3)])[0]
    d.text((tx, ty), f'Prime tower area\n{x1 - x0:.0f} x {y1 - y0:.0f} mm', fill=(200, 40, 40), font=f)
    f2 = _font(int(k * 5))
    for name, P, (dx, dy) in zip(lay.piece_names, lay.pieces, offsets):
        b = P.bounds
        tx, ty = cv.to_px([(b[0] + dx + 1, b[1] + dy - 1.2)])[0]
        d.text((tx, ty), f'{name}  ({b[2] - b[0]:.1f} mm)', fill=(40, 40, 40), font=f2)
    f3 = _font(int(k * 4.2))
    label = 'Bambu Lab P2S plate 256 x 256 mm, top view (back of plate at top); dashed = 5 mm margin'
    tx, ty = cv.to_px([(7, PLATE - 5.6)])[0]
    bb = d.textbbox((tx, ty), label, font=f3)
    d.rectangle((bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3), fill=(236, 236, 236))
    d.text((tx, ty), label, fill=(40, 40, 40), font=f3)
    cv.img.save(path)
    return cv.img


def _dashed(cv, pts, color, width, dash=4.0):
    d = ImageDraw.Draw(cv.img)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / dash))
        for i in range(0, n, 2):
            a = (x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
            b = (x0 + (x1 - x0) * min(n, i + 1) / n, y0 + (y1 - y0) * min(n, i + 1) / n)
            d.line(cv.to_px([a, b]), fill=color, width=width)
