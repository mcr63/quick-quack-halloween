#!/usr/bin/env python3
"""Build the WRONG WAY sign and its snap-on pipe mount (4 receivers, 2 clips):
2 plate 3MFs, STLs (one per color per part) in a zip, previews, a manifest
for re-packing into native Bambu projects, and a check report.

    python3 src/build.py
    python3 src/build.py --out out --sign-cap-max 30

Prints a summary and writes out/build_report.json. Exit code 1 if a check fails.
"""
import argparse
import io
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import design  # noqa: E402
import export as E  # noqa: E402
import checks  # noqa: E402

PREFIX = 'WRONG_WAY'


def thumb(img):
    buf = io.BytesIO()
    img.resize((512, 512)).save(buf, format='PNG')
    return buf.getvalue()


def outline_report(g, stroke):
    """The outline is `stroke` wide, but it also fills the acute notch tips of letters like W
    and N, and those taper to a point. Those tips are fine: each is small and attached to the
    full-width outline. Anything else thinner than `stroke` fails."""
    r = stroke / 2
    body = g.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    thin = design.thin_parts(g, stroke)
    bad = [q for q in design.polys(thin) if q.area > 1.0 or q.distance(body) > 0.01]
    return dict(width_mm=stroke, notch_tips=len(design.polys(thin)) - len(bad),
                largest_tip_mm2=round(max((q.area for q in design.polys(thin)), default=0.0), 2),
                other_thin_mm2=round(sum(q.area for q in bad), 3), ok=not bad)


def stroke_report(g, stroke):
    """Thinnest stroke (erosion split test) and whether any elongated feature is thinner than `stroke`."""
    t = design.thin_parts(g, stroke)
    return dict(min_stroke_mm=round(design.min_stroke(g), 2), thinner_than_stroke_mm2=round(t.area, 3),
                ok=bool(t.area < 0.05))


def orange_gap_report(sign):
    """Orange left between outlined letters or inside counters narrower than the outline
    width: closing the black+yellow ink by just under that width must add nothing."""
    ink = design.union(sign.text, sign.text_outline)
    r = sign.p.text_outline / 2 - 0.02
    added = design.drop_small(ink.buffer(r, quad_segs=16).buffer(-r, quad_segs=16).difference(ink.buffer(1e-3)), 0.01)
    # what closing adds at sharp inside corners is a tiny fillet (well under 0.1 mm2); a real
    # sliver between letters would be long and much bigger
    pieces = design.polys(added)
    biggest = max((q.area for q in pieces), default=0.0)
    return dict(corner_fillets=len(pieces), largest_mm2=round(biggest, 3), ok=bool(biggest < 0.1))


def mount_report(sign, mp):
    """Clash check of the hung sign on a vertical and a horizontal pipe: overlap volumes
    between pipe, sign, receivers and clips (all must be ~0), and clearances."""
    out = {}
    for vertical in (True, False):
        slab, recs, clips, pipe = E.assembly(sign, mp, vertical)
        ov = {}
        ov['pipe-sign'] = checks.overlap_volume(pipe, slab)
        for nm, r in recs:
            ov[f'pipe-receiver {nm}'] = checks.overlap_volume(pipe, r)
        for cn, c in clips:
            ov[f'pipe-clip {cn}'] = checks.overlap_volume(pipe, c)
            ov[f'clip {cn}-sign'] = checks.overlap_volume(c, slab)
            for nm, r in recs:
                ov[f'clip {cn}-receiver {nm}'] = checks.overlap_volume(c, r)
        ov = {k: round(abs(v), 4) for k, v in ov.items()}
        zc, r = mp.pipe_center, mp.pipe_od / 2
        pipe_xy = 0.0
        unused = [(x, y) for x, y in mp.rec_pos if not ((x == 0) if vertical else (y == 0))]
        # distance in the sign plane from the pipe edge to the unused receivers
        side = min((abs(x) if vertical else abs(y)) - mp.rec_w / 2 for x, y in unused) - r
        out['vertical' if vertical else 'horizontal'] = dict(
            clips=[c for c, _ in clips], max_overlap_mm3=max(ov.values()), overlaps=ov,
            pipe_to_receiver_tops_mm=round(zc - r - mp.rec_h, 2),
            pipe_to_sign_mm=round(zc - r, 2),
            pipe_edge_to_unused_receivers_mm=round(side, 2),
            ok=bool(max(ov.values()) < 1e-3 and zc - r - mp.rec_h > 1.0))
    out['snap'] = dict(bore=mp.bore, pipe_od=mp.pipe_od, mouth=mp.mouth, spread_needed_mm=round(mp.pipe_od - mp.mouth, 2),
                       peg=mp.peg, pocket=mp.pocket, fit_per_side_mm=round((mp.pocket - mp.peg) / 2, 3))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(design.ROOT, 'out'))
    ap.add_argument('--sign-cap-max', type=float, default=design.Params.sign_cap_max,
                    help='largest WRONG / WAY cap height to try, mm (the build uses the largest that fits)')
    a = ap.parse_args(argv)
    out = a.out
    os.makedirs(out, exist_ok=True)
    t0 = time.time()

    p = design.Params(sign_cap_max=a.sign_cap_max)
    mp = design.MountParams()
    sign = design.Sign(p)

    # ------------------------------------------------ meshes and plates
    (sdx, sdy), tower_a = E.flat_plate(sign)
    sign_m = E.place(E.flat_meshes(sign), sdx, sdy)
    mount_parts = E.mounts_plate(mp)

    plates = [
        dict(key='A', file=f'{PREFIX}_A_sign.3mf', title='WRONG WAY sign', tower=tower_a, seq='by object',
             objects=[dict(name=sign.name, parts=sign_m)]),
        dict(key='B', file=f'{PREFIX}_B_mounts.3mf', title='Pipe mount: 4 receivers, 2 clips', tower=None, seq='by layer',
             objects=[dict(name=n, parts={'black': m}) for n, m in mount_parts]),
    ]

    # ------------------------------------------------ previews
    E.preview_sign(sign, os.path.join(out, 'preview_sign.png'))
    E.preview_assembly(sign, mp, os.path.join(out, 'preview_assembly.png'))
    imgs = {
        'A': E.preview_flat_plate(sign, (sdx, sdy), tower_a, os.path.join(out, 'preview_plate_A.png'),
                                  'Plate A: sign (' + ', '.join(c for c in E.COLOR_ORDER if c in sign.colors) + ')'),
        'B': E.preview_mounts_plate(mp, mount_parts, os.path.join(out, 'preview_plate_B.png'),
                                    'Plate B: 4 receivers, 2 clips (black)'),
    }

    # ------------------------------------------------ files
    stl_entries = []
    manifest = dict(note='Re-pack with src/to_bambu.py --template <a Bambu-saved P2S 3MF>. Filament slots '
                         '1 yellow, 2 orange, 3 white, 4 black. Coordinates are plate mm.',
                    filament_slots={str(v): k for k, v in E.FILAMENT.items()},
                    filament_hex=E.BAMBU_HEX, plates=[])
    for pl in plates:
        path = os.path.join(out, pl['file'])
        E.write_3mf(path, pl['objects'], pl['title'], thumbnail_png=thumb(imgs[pl['key']]))
        mobjs = []
        for k, ob in enumerate(pl['objects'], 1):
            parts = []
            for c in E.COLOR_ORDER:
                if c not in ob['parts']:
                    continue
                if pl['key'] in ('B', 'one') and ob['name'] != sign.name:
                    tag = ob['name'].split(' - ')[0].replace(' ', '').lower()
                    fn = f"{pl['key']}_{tag}_{E.FILAMENT[c]}_{c}.stl"
                else:
                    fn = f"{pl['key']}_sign_{E.FILAMENT[c]}_{c}.stl"
                stl_entries.append((fn, ob['parts'][c]))
                parts.append(dict(color=c, filament=E.FILAMENT[c], stl=fn))
            mobjs.append(dict(name=ob['name'], parts=parts))
        t = pl['tower']
        manifest['plates'].append(dict(
            plate=pl['key'], file=pl['file'], bambu_file=pl['file'].replace('.3mf', '_bambu.3mf'),
            title=pl['title'], print_sequence=pl['seq'], objects=mobjs,
            tower_box=[round(x, 2) for x in t] if t else None,
            wipe_tower_xy=[round(t[0] + 10, 1), round(t[1] + 8, 1)] if t else None))
    stl_paths, zpath = E.write_stls(stl_entries, out, f'{PREFIX}_STLs.zip')
    with open(os.path.join(out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)

    # ------------------------------------------------ checks
    rep = dict(params=p.__dict__, mount=mp.__dict__ | dict(rec_h=mp.rec_h, pipe_center=mp.pipe_center))
    rep['font'] = os.path.basename(design.FONT)
    d = sign.duck
    rep['sign'] = dict(size=[p.sign_w, p.sign_h], cap_mm=sign.cap, text_bounds=[round(x, 1) for x in sign.text.bounds],
                       text=stroke_report(sign.text, 1.0), border=stroke_report(sign.border, 1.0),
                       duck_bounds=[round(x, 1) for x in d['sil'].bounds],
                       duck_size=[round(d['sil'].bounds[2] - d['sil'].bounds[0], 1), round(d['sil'].bounds[3] - d['sil'].bounds[1], 1)],
                       text_to_duck_mm=round(sign.text.distance(d['sil']), 2),
                       outline_to_duck_mm=round(sign.text_outline.distance(d['sil']), 2),
                       outline_to_border_mm=round(sign.text_outline.distance(sign.border), 2),
                       outline=outline_report(sign.text_outline, p.text_outline - 0.05),
                       orange_between_letters=orange_gap_report(sign),
                       duck_black=stroke_report(d['black'], p.duck_stroke),
                       duck_white=stroke_report(d['white'], p.duck_stroke),
                       duck_yellow=stroke_report(d['yellow'], p.duck_stroke),
                       duck_smallest_island_mm2=round(min(q.area for c in ('black', 'white', 'yellow') for q in design.polys(d[c])), 2))
    rep['sign']['text_shift_mm'] = sign.text_shift
    rep['plates'] = []
    for pl in plates:
        r, _ = checks.check_plate(os.path.join(out, pl['file']), pl['tower'])
        r['print_sequence'] = pl['seq']
        rep['plates'].append(r)
    stl_rep, _ = checks.check_stls(stl_paths)
    rep['stls'] = stl_rep

    # grams per color (PLA, 15% infill), before purge
    g = {}

    def add(c, v):
        g[c] = g.get(c, 0.0) + v
    for part in (sign,):
        zr = E.z_ranges(part)
        for c, geom in part.colors.items():
            add(c, checks.grams_flat(geom.area, geom.boundary.length, zr[c][1] - zr[c][0]))
    mount_g = sum(checks.grams_mesh(m) for _, m in mount_parts)
    add('black', mount_g)
    rep['grams_mount_parts'] = {n: round(checks.grams_mesh(m), 1) for n, m in mount_parts}
    rep['grams'] = {c: round(v, 1) for c, v in g.items()}
    rep['grams_per_plate'] = {
        'A': {c: round(checks.grams_flat(geom.area, geom.boundary.length, E.z_ranges(sign)[c][1] - E.z_ranges(sign)[c][0]), 1)
              for c, geom in sign.colors.items()},
        'B': {'black': round(mount_g, 1)},
    }
    rep['mount'] = mount_report(sign, mp)
    rep['seconds'] = round(time.time() - t0, 1)

    # ------------------------------------------------ summary and hard limits
    fails = []
    print(f'WRONG WAY build ({rep["seconds"]} s), font {rep["font"]}')
    for r in rep['plates']:
        print(f"  {r['file']}: bounds {r['plate_bounds']} margins ok {r['inside_plate_with_margin']}"
              f"  swaps {r['min_swaps']}  tower {r.get('tower_box')} {r.get('tower_clear_ok', '-')}")
        for o in r['objects']:
            print(f"    {o['name']:<26} {o['size']}  " + ', '.join(
                f"{q['name'].split(' - ')[-1]} z{q['z'][0]:.1f}-{q['z'][1]:.1f}{'' if q['watertight'] else ' NOT WATERTIGHT'}"
                for q in o['parts']))
            for q in o['parts']:
                if not q['watertight']:
                    fails.append(f"{q['name']} not watertight")
            for a_, b_, v in o['overlaps']:
                if abs(v) > 1e-3:
                    fails.append(f"{o['name']}: {a_} and {b_} overlap {v} mm3")
        if not r['inside_plate_with_margin']:
            fails.append(f"{r['file']}: parts leave the 5 mm plate margin")
        if r.get('tower_clear_ok') is False:
            fails.append(f"{r['file']}: prime tower area blocked or smaller than 55 x 55 mm")
        if any(gap < 6.0 for _, gap in r['object_gaps']):
            fails.append(f"{r['file']}: parts closer than 6 mm")
        print('    raised layers:', [(l[0], l[1], l[2], l[3]) for l in r['raised_layers']])
    for part in ('sign',):
        for k, v in rep[part].items():
            if isinstance(v, dict) and 'ok' in v:
                print(f'  {part} {k}: {v}')
                if not v['ok']:
                    fails.append(f'{part} {k} has features thinner than the limit')
    for o in ('vertical', 'horizontal'):
        m = rep['mount'][o]
        print(f"  mount {o}: clips {m['clips']}, max overlap {m['max_overlap_mm3']} mm3, pipe {m['pipe_to_receiver_tops_mm']} mm "
              f"over receivers, {m['pipe_to_sign_mm']} mm off the sign, {m['pipe_edge_to_unused_receivers_mm']} mm from unused receivers")
        if not m['ok']:
            fails.append(f'mount clash ({o} pipe)')
    for k in ('outline_to_duck_mm', 'outline_to_border_mm'):
        if rep['sign'][k] < p.outline_clear - 1e-3:
            fails.append(f'sign {k} = {rep["sign"][k]} (< {p.outline_clear})')
    print(f"  outline to duck {rep['sign']['outline_to_duck_mm']} mm, to border {rep['sign']['outline_to_border_mm']} mm")
    print(f"  sign cap {sign.cap} mm, duck {rep['sign']['duck_size']} mm, text to duck {rep['sign']['text_to_duck_mm']} mm,"
          f" text block {sign.text_shift:+.1f} mm from center")
    if not all(s['watertight'] for s in stl_rep):
        fails.append('an STL is not watertight')
    print('  STLs', [(s['file'], s['watertight']) for s in stl_rep])
    print('  grams', rep['grams'], ' per plate', rep['grams_per_plate'])
    for f in fails:
        print('  FAIL:', f)
    if not fails:
        print('  all checks passed')
    rep['fails'] = fails
    with open(os.path.join(out, 'build_report.json'), 'w') as f:
        json.dump(rep, f, indent=1, default=str)
    return rep


if __name__ == '__main__':
    sys.exit(1 if main()['fails'] else 0)
