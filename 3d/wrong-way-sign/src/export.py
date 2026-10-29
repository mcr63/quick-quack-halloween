"""Meshes, plate layouts, 3MF and STL files, and preview images.

3MF notes (same format as the DUCK! bar, checked there against BambuStudio's
bbs_3mf.cpp): each object has one part per color and each part carries its
filament in Metadata/model_settings.config. We do not claim to be Bambu
Studio, so Studio says the file is "not from Bambu Lab" and loads geometry
and colors only. src/to_bambu.py re-packs these files into native Bambu
projects when one of Matt's own Bambu-saved 3MFs is available as a template.
"""
import json
import math
import os
import zipfile
from datetime import date
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import manifold3d as mf
import shapely.affinity as aff
import trimesh
from PIL import Image, ImageDraw, ImageFont

from design import polys
from render import Canvas, hex2rgb

# AMS order: 1 yellow, 2 orange, 3 white (was green on the DUCK! bar), 4 black
FILAMENT = {'yellow': 1, 'orange': 2, 'white': 3, 'black': 4}
HEX = {'yellow': '#FFCF42', 'orange': '#F79239', 'white': '#FFFFFF', 'black': '#1A1A1A'}
BAMBU_HEX = ['#FFC72C', '#FF7F27', '#FFFFFF', '#161616']    # project filament colors for a native Bambu file
COLOR_ORDER = ['yellow', 'orange', 'white', 'black']

BASE_Z = 3.0
RAISE = {'yellow': 0.4, 'orange': 0.2, 'white': 0.2, 'black': 0.4}   # raised colors; black goes on last, two layers

PLATE = 256.0
EDGE_MARGIN = 5.0
TOWER = 55.0


# ---------------------------------------------------------------- meshes

def _to_trimesh(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    return trimesh.Trimesh(v, f, process=True)


def extrude(geom, z0, z1):
    rings = []
    for p in polys(geom):
        rings.append(np.asarray(p.exterior.coords)[:-1])
        for r in p.interiors:
            rings.append(np.asarray(r.coords)[:-1])
    if not rings:
        return None
    cs = mf.CrossSection(rings, mf.FillRule.EvenOdd)
    return _to_trimesh(mf.Manifold.extrude(cs, z1 - z0).translate((0, 0, z0)))


def z_ranges(part):
    """color -> (z0, z1) for a flat part (base color 0-3 mm, others raised on top)."""
    out = {}
    for c in part.colors:
        out[c] = (0.0, BASE_Z) if c == part.base else (BASE_Z, BASE_Z + RAISE[c])
    return out


def flat_meshes(part):
    zr = z_ranges(part)
    return {c: extrude(g, *zr[c]) for c, g in part.colors.items()}


def receiver_mesh(mp):
    """30 x 30 block, glue face at z=0, square pocket open at the top with a chamfered mouth.
    Centered on x=y=0."""
    w, h, q, c = mp.rec_w, mp.rec_h, mp.pocket, mp.mouth_chamfer
    m = mf.Manifold.cube((w, w, h), center=True).translate((0, 0, h / 2))
    m = m - mf.Manifold.cube((q, q, mp.pocket_depth + 1), center=True).translate((0, 0, mp.rec_floor + (mp.pocket_depth + 1) / 2))
    sq = mf.CrossSection([np.array([(-q / 2, -q / 2), (q / 2, -q / 2), (q / 2, q / 2), (-q / 2, q / 2)])])
    top = (q + 2 * (c + 0.2)) / q        # chamfer cone runs 0.2 mm past the top face
    cone = mf.Manifold.extrude(sq, c + 0.2, 0, 0.0, (top, top)).translate((0, 0, h - c))
    return _to_trimesh(m - cone)


def clip_mesh(mp):
    """The clip profile (design.clip_profile) extruded clip_w along z: prints flat on the bed."""
    from design import clip_profile
    return extrude(clip_profile(mp), 0.0, mp.clip_w)


def clip_in_receiver(mp, clip, x, y, vertical):
    """Place a clip mesh (profile frame) in the receiver at sign-back position (x, y).
    Assembly frame: x right and y up as seen from the front, z = distance behind the sign back.
    vertical=True: pipe runs along y; else along x."""
    m = clip.copy()
    off = mp.rec_floor + mp.r_out + mp.stem + mp.peg_len          # peg end on the pocket floor
    v = m.vertices.copy()
    px, py, pz = v[:, 0], v[:, 1], v[:, 2] - mp.clip_w / 2
    if vertical:
        m.vertices = np.column_stack([x + px, y + pz, py + off])
    else:
        m.vertices = np.column_stack([x + pz, y + px, py + off])
    if m.volume < 0:
        m.invert()
    return m


def assembly(sign, mp, vertical):
    """Meshes of the hung sign seen from the back: sign slab, 4 receivers, 2 clips, pipe."""
    b = sign.outline.bounds
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    from shapely import affinity as aff2
    slab = extrude(aff2.translate(sign.outline, -cx, -cy), -3.4, 0.0)
    rec = receiver_mesh(mp)
    clip = clip_mesh(mp)
    recs, clips = [], []
    for (x, y), nm in zip(mp.rec_pos, mp.rec_names):
        r = rec.copy()
        r.apply_translation((x, y, 0))
        recs.append((nm, r))
        used = (x == 0) if vertical else (y == 0)
        if used:
            clips.append((nm, clip_in_receiver(mp, clip, x, y, vertical)))
    L = 400.0
    r = mp.pipe_od / 2
    pipe = mf.Manifold.cylinder(L, r, r, 128).translate((0, 0, -L / 2))
    pipe = pipe.rotate((-90, 0, 0)) if vertical else pipe.rotate((0, 90, 0))
    pipe = _to_trimesh(pipe.translate((0, 0, mp.pipe_center)))
    return slab, recs, clips, pipe


# ---------------------------------------------------------------- plates

def mounts_plate(mp, gap=12.0):
    """4 receivers in a row, 2 clips in a row behind them, centred on the plate.
    Returns [(name, mesh)] in plate coordinates."""
    rec = receiver_mesh(mp)
    clip = clip_mesh(mp)
    cb = clip.bounds
    cw, ch = cb[1][0] - cb[0][0], cb[1][1] - cb[0][1]
    w = mp.rec_w
    row1 = 4 * w + 3 * gap
    total_h = w + gap + ch
    y0 = (PLATE - total_h) / 2
    out = []
    x = (PLATE - row1) / 2
    for i, nm in enumerate(mp.rec_names):
        m = rec.copy()
        m.apply_translation((x + w / 2, y0 + w / 2, 0))
        out.append((f'Receiver {i + 1} - {nm}', m))
        x += w + gap
    row2 = 2 * cw + gap
    x = (PLATE - row2) / 2
    for i in range(2):
        m = clip.copy()
        m.apply_translation((x - cb[0][0], y0 + w + gap - cb[0][1], 0))
        out.append((f'Clip {i + 1}', m))
        x += cw + gap
    return out


# ---------------------------------------------------------------- plates

def place(meshes, dx, dy):
    out = {}
    for c, m in meshes.items():
        m = m.copy()
        m.apply_translation((dx, dy, 0))
        out[c] = m
    return out


def flat_plate(part, front_margin=8.0):
    """One flat part at the front of the plate, centred in X; the back strip stays clear for the prime tower."""
    b = part.outline.bounds
    w, h = b[2] - b[0], b[3] - b[1]
    dx = (PLATE - w) / 2 - b[0]
    dy = front_margin - b[1]
    tower = (EDGE_MARGIN, front_margin + h + 6.0, PLATE - EDGE_MARGIN, PLATE - EDGE_MARGIN)
    return (dx, dy), tower


def one_plate_mounts(mp, y0, x0=8.0, gap=8.0):
    """Receivers (row 1) and clips (row 2) in the strip behind the sign, from x0, y0.
    Returns ([(name, mesh)], tower_box): the tower box is the clear area to their right."""
    rec = receiver_mesh(mp)
    clip = clip_mesh(mp)
    cb = clip.bounds
    w = mp.rec_w
    out = []
    x = x0
    for i, nm in enumerate(mp.rec_names):
        m = rec.copy()
        m.apply_translation((x + w / 2, y0 + w / 2, 0))
        out.append((f'Receiver {i + 1} - {nm}', m))
        x += w + gap
    x = x0
    for i in range(2):
        m = clip.copy()
        m.apply_translation((x - cb[0][0], y0 + w + gap - cb[0][1], 0))
        out.append((f'Clip {i + 1}', m))
        x += (cb[1][0] - cb[0][0]) + gap
    xmax = max(m.bounds[1][0] for _, m in out)
    tower = (float(xmax + gap), float(y0), PLATE - EDGE_MARGIN, PLATE - EDGE_MARGIN)
    return out, tower


# ---------------------------------------------------------------- STL

def write_stls(entries, out_dir, zip_name):
    """entries: list of (filename, mesh). Writes each STL and a zip of them all."""
    paths = []
    for fn, m in entries:
        p = os.path.join(out_dir, fn)
        m.export(p)
        paths.append(p)
    zpath = os.path.join(out_dir, zip_name)
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    return paths, zpath


# ---------------------------------------------------------------- 3MF

def _mesh_xml(obj_id, mesh):
    out = [f'  <object id="{obj_id}" type="model">\n   <mesh>\n    <vertices>\n']
    out += [f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>\n' for x, y, z in mesh.vertices]
    out.append('    </vertices>\n    <triangles>\n')
    out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in mesh.faces]
    out.append('    </triangles>\n   </mesh>\n  </object>\n')
    return ''.join(out)


def write_3mf(path, objects, title, thumbnail_png=None):
    """objects: list of dict(name, parts={color: mesh in plate coords}).
    One 3MF object per part of the build, one 3MF part per color with its filament."""
    model = ['<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n']
    today = date.today().isoformat()
    for k, v in {'Application': 'wrong-way-sign generator (python)', 'BambuStudio:3mfVersion': '1',
                 'Title': title, 'CreationDate': today, 'ModificationDate': today}.items():
        model.append(f' <metadata name="{k}">{escape(v)}</metadata>\n')
    model.append(' <resources>\n')
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    build = []
    nid = 1
    for ob in objects:
        md = ob['parts']
        allv = np.vstack([m.vertices for m in md.values()])
        lo, hi = allv.min(axis=0), allv.max(axis=0)
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        pids = []
        for c in COLOR_ORDER:
            if c not in md:
                continue
            m = md[c].copy()
            m.apply_translation((-cx, -cy, 0))
            model.append(_mesh_xml(nid, m))
            pids.append((nid, c, len(m.faces)))
            nid += 1
        oid = nid
        nid += 1
        model.append(f'  <object id="{oid}" type="model">\n   <components>\n')
        for pid, _, _ in pids:
            model.append(f'    <component objectid="{pid}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n')
        model.append('   </components>\n  </object>\n')
        build.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {cx:.5f} {cy:.5f} 0" printable="1"/>\n')
        cfg.append(f'  <object id="{oid}">\n    <metadata key="name" value={quoteattr(ob["name"])}/>\n'
                   f'    <metadata key="extruder" value="{FILAMENT[pids[0][1]]}"/>\n')
        for pid, c, nf in pids:
            pname = f'{ob["name"]} - {c} (F{FILAMENT[c]})'
            cfg.append(f'    <part id="{pid}" subtype="normal_part">\n'
                       f'      <metadata key="name" value={quoteattr(pname)}/>\n'
                       '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                       f'      <metadata key="extruder" value="{FILAMENT[c]}"/>\n'
                       f'      <mesh_stat face_count="{nf}" edges_fixed="0" degenerate_facets="0" '
                       'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n    </part>\n')
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
                     ' <Default Extension="config" ContentType="text/xml"/>\n</Types>')
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


def _paint(cv, part, dx=0.0, dy=0.0):
    order = [part.base] + [c for c in COLOR_ORDER if c in part.colors and c != part.base]
    for c in order:
        cv.fill(aff.translate(part.colors[c], dx, dy), hex2rgb(HEX[c]))


def preview_sign(sign, path, width_px=2400, bg=(255, 255, 255)):
    """The finished sign, face on."""
    m = 8.0
    b = sign.outline.bounds
    k = width_px / (b[2] - b[0] + 2 * m)
    cv = Canvas(b[0] - m, b[1] - m, b[2] + m, b[3] + m, k, bg=bg)
    _paint(cv, sign)
    cv.img.save(path)
    return cv.img


def _plate_canvas(px):
    k = px / PLATE
    cv = Canvas(0, 0, PLATE, PLATE, k, bg=(236, 236, 236))
    d = ImageDraw.Draw(cv.img)
    for g in range(0, int(PLATE) + 1, 10):
        col = (215, 215, 215) if g % 50 else (195, 195, 195)
        d.line(cv.to_px([(g, 0), (g, PLATE)]), fill=col, width=1)
        d.line(cv.to_px([(0, g), (PLATE, g)]), fill=col, width=1)
    return cv, d, k


def _plate_frame(cv, d, k, title, tower=None):
    cv.line([(0, 0), (PLATE, 0), (PLATE, PLATE), (0, PLATE), (0, 0)], (0, 0, 0), 4)
    m = EDGE_MARGIN
    _dashed(cv, [(m, m), (PLATE - m, m), (PLATE - m, PLATE - m), (m, PLATE - m), (m, m)], (120, 120, 120), 2)
    if tower:
        x0, y0, x1, y1 = tower
        cv.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], (200, 40, 40), 4)
        f = _font(int(k * 4.5))
        tx, ty = cv.to_px([(x0 + 3, y1 - 3)])[0]
        d.text((tx, ty), f'Clear for the prime tower: {x1 - x0:.0f} x {y1 - y0:.0f} mm', fill=(200, 40, 40), font=f)
    f3 = _font(int(k * 4.2))
    tx, ty = cv.to_px([(7, 4.6)])[0]
    d.text((tx, ty), title + '  |  P2S plate 256 x 256 mm, top view; dashed = 5 mm margin', fill=(40, 40, 40), font=f3)


def preview_flat_plate(part, offset, tower, path, title, px=1600):
    cv, d, k = _plate_canvas(px)
    _paint(cv, part, *offset)
    cv.outline(aff.translate(part.outline, *offset), (90, 90, 90), 2)
    _plate_frame(cv, d, k, title, tower)
    b = part.outline.bounds
    f2 = _font(int(k * 5))
    tx, ty = cv.to_px([(b[0] + offset[0] + 1, b[3] + offset[1] + 7)])[0]
    d.text((tx, ty), f'{part.name}  ({b[2] - b[0]:.0f} x {b[3] - b[1]:.0f} mm)', fill=(40, 40, 40), font=f2)
    cv.img.save(path)
    return cv.img


def preview_mounts_plate(mp, parts, path, title, px=1600):
    """Top view of the mounts plate (footprints)."""
    cv, d, k = _plate_canvas(px)
    _draw_mounts(cv, d, k, mp, parts, HEX['black'])
    _plate_frame(cv, d, k, title)
    cv.img.save(path)
    return cv.img


def preview_one_plate(sign, offset, mp, parts, tower, path, title, px=1600):
    """The one-plate layout: sign at the front, mount parts (orange) and prime tower behind."""
    cv, d, k = _plate_canvas(px)
    _paint(cv, sign, *offset)
    cv.outline(aff.translate(sign.outline, *offset), (90, 90, 90), 2)
    _draw_mounts(cv, d, k, mp, parts, HEX['orange'], outline=True)
    _plate_frame(cv, d, k, title, tower)
    f2 = _font(int(k * 4.2))
    tx, ty = cv.to_px([(tower[0] + 3, tower[1] + 40)])[0]
    d.text((tx, ty), 'Print by layer:\nlayers 1-15 orange only,\nsign colors in layers 16-17,\nmounts finish in orange.',
           fill=(40, 40, 40), font=f2)
    cv.img.save(path)
    return cv.img


def _draw_mounts(cv, d, k, mp, parts, color, outline=False):
    from shapely.geometry import box
    from design import clip_profile
    f2 = _font(int(k * 4.2))
    prof = clip_profile(mp)
    for name, m in parts:
        b = m.bounds
        if name.startswith('Receiver'):
            x0, y0, x1, y1 = b[0][0], b[0][1], b[1][0], b[1][1]
            g = box(x0, y0, x1, y1)
            cv.fill(g, hex2rgb(color))
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            q = mp.pocket / 2
            dark = tuple(int(v * 0.6) for v in hex2rgb(color)) if color != HEX['black'] else (95, 95, 95)
            cv.fill(box(cx - q, cy - q, cx + q, cy + q), dark)
        else:
            from shapely import affinity as aff2
            pb = prof.bounds
            g = aff2.translate(prof, b[0][0] - pb[0], b[0][1] - pb[1])
            cv.fill(g, hex2rgb(color))
        if outline:
            cv.outline(g, (90, 90, 90), 2)
        tx, ty = cv.to_px([(b[0][0], b[1][1] + 6)])[0]
        d.text((tx, ty), name.split(' - ')[0], fill=(40, 40, 40), font=f2)


def preview_assembly(sign, mp, path, px_per_mm=4.0):
    """Back of the sign with the 4 receivers, for a vertical and a horizontal pipe, plus a
    cross-section through a receiver, clip and pipe."""
    from shapely.geometry import box, Point
    from shapely import affinity as aff2
    from design import clip_profile
    b = sign.outline.bounds
    W, H = b[2] - b[0], b[3] - b[1]
    k = px_per_mm
    pad = 30
    panel_w, panel_h = int((W + 2 * pad) * k), int((H + 2 * pad + 12) * k)
    sec_w = int(110 * k)
    img = Image.new('RGB', (2 * panel_w + sec_w, panel_h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    f = _font(int(4.5 * k))
    back = aff2.translate(sign.outline, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)
    r = mp.pipe_od / 2
    cb = clip_profile(mp).bounds
    for i, vertical in enumerate((True, False)):
        cv = Canvas(-W / 2 - pad, -H / 2 - pad, W / 2 + pad, H / 2 + pad + 12, k)
        cv.fill(back, (233, 180, 140))
        cv.outline(back, (120, 90, 60), 2)
        pipe = box(-r, -H / 2 - pad, r, H / 2 + pad) if vertical else box(-W / 2 - pad, -r, W / 2 + pad, r)
        for (x, y) in mp.rec_pos:
            cv.fill(box(x - mp.rec_w / 2, y - mp.rec_w / 2, x + mp.rec_w / 2, y + mp.rec_w / 2), hex2rgb(HEX['black']))
        cv.fill(pipe, (200, 200, 205))
        cv.outline(pipe, (110, 110, 120), 2)
        for (x, y) in mp.rec_pos:
            if (x == 0) if vertical else (y == 0):
                hw, hl = (cb[2] - cb[0]) / 2, mp.clip_w / 2
                clipbox = box(x - hw, y - hl, x + hw, y + hl) if vertical else box(x - hl, y - hw, x + hl, y + hw)
                cv.fill(clipbox, (60, 60, 60))
        cv.img.paste(cv.img)
        ImageDraw.Draw(cv.img).text((10, 6), ('Vertical pipe: top and bottom receivers' if vertical
                                             else 'Horizontal pipe: left and right receivers') + ' (back view)',
                                    fill=(30, 30, 30), font=f)
        img.paste(cv.img, (i * panel_w, 0))
    # cross-section through a used receiver, across the pipe
    zc = mp.pipe_center
    cv = Canvas(-30, -12, 30, zc + r + 12, k * 1.6)
    cv.fill(box(-30, -3.4, 30, 0), (233, 180, 140))                    # sign
    w, q = mp.rec_w / 2, mp.pocket / 2
    cv.fill(box(-w, 0, w, mp.rec_h).difference(box(-q, mp.rec_floor, q, mp.rec_h + 1)), hex2rgb(HEX['black']))
    off = mp.rec_floor + mp.r_out + mp.stem + mp.peg_len
    cv.fill(aff2.translate(clip_profile(mp), 0, off), (85, 85, 85))
    cv.outline(Point(0, zc).buffer(r, quad_segs=64), (90, 90, 200), 3)
    ImageDraw.Draw(cv.img).text((8, 6), 'Section across the pipe', fill=(30, 30, 30), font=f)
    ImageDraw.Draw(cv.img).text((8, 6 + int(5.5 * k)), f'pipe {zc - r:.0f} mm off the receivers' if False else
                                f'pipe center {zc:.1f} mm behind the sign', fill=(30, 30, 30), font=f)
    sec = cv.img.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_TOP_BOTTOM)
    img.paste(sec, (2 * panel_w, max(0, (panel_h - sec.size[1]) // 2)))
    img.save(path)
    return img


def _dashed(cv, pts, color, width, dash=4.0):
    d = ImageDraw.Draw(cv.img)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / dash))
        for i in range(0, n, 2):
            a = (x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
            b = (x0 + (x1 - x0) * min(n, i + 1) / n, y0 + (y1 - y0) * min(n, i + 1) / n)
            d.line(cv.to_px([a, b]), fill=color, width=width)
