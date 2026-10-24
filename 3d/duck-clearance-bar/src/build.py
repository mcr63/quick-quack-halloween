#!/usr/bin/env python3
"""Build the DUCK! CLEARANCE sign: 3MF, STLs, previews and a check report.

    python3 src/build.py                       # CLEARANCE 6'-7"
    python3 src/build.py --text "7'-2\""       # another clearance
    python3 src/build.py --feet 7 --inches 2   # same thing, no quotes to escape
    python3 src/build.py --text "6'-7\"" --c 26 --out out

Prints a summary and writes out/build_report.json.
"""
import argparse
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import design  # noqa: E402
import export  # noqa: E402
import checks  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text', default="6'-7\"", help="clearance after CLEARANCE, e.g. 6'-7\"")
    ap.add_argument('--c', type=float, default=design.Params.c, help='CLEARANCE cap height in mm')
    ap.add_argument('--out', default=os.path.join(design.ROOT, 'out'))
    ap.add_argument('--name', default=None, help='3MF base name (default: from the text)')
    ap.add_argument('--feet', type=int, default=None, help="clearance feet, e.g. 7 (instead of --text)")
    ap.add_argument('--inches', type=int, default=0, help="clearance inches, e.g. 2 (with --feet)")
    a = ap.parse_args(argv)
    if a.feet is not None:
        a.text = f"{a.feet}'-{a.inches}\""
    if a.name is None:
        slug = a.text.replace("'", 'ft').replace('"', '').replace('-', '').replace(' ', '')
        a.name = 'DUCK_clearance_' + ''.join(ch for ch in slug if ch.isalnum())
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    p = design.Params(clearance=a.text, c=a.c)
    lay = design.build_layout(p)
    cols = design.piece_colors(lay)
    meshes = export.piece_meshes(cols)
    offsets, tower = export.plate_layout(lay.pieces)

    # previews
    sign_png = os.path.join(a.out, 'preview_sign.png')
    plate_png = os.path.join(a.out, 'preview_plate.png')
    export.preview_sign(lay, cols, sign_png)
    plate_img = export.preview_plate(lay, cols, offsets, tower, plate_png)
    thumb = plate_img.resize((512, 512))
    buf = io.BytesIO()
    thumb.save(buf, format='PNG')

    # files
    stl_paths, zpath = export.write_stls(meshes, offsets, a.out)
    title = f'DUCK! CLEARANCE {a.text}'
    path3mf = os.path.join(a.out, a.name + '.3mf')
    export.write_3mf(path3mf, lay.piece_names, meshes, offsets, title, thumbnail_png=buf.getvalue())

    # checks
    rep = {}
    rep['params'] = {k: getattr(p, k) for k in ('clearance', 'c', 'H', 'top_bar', 'bot_bar')}
    rep['layout'] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in lay.info.items()}
    rep['pieces_2d'] = [dict(name=n, length=round(P.bounds[2] - P.bounds[0], 2),
                             bounds=[round(x, 2) for x in P.bounds]) for n, P in zip(lay.piece_names, lay.pieces)]
    rep['L'] = round(lay.L, 2)
    rep['check_2d'] = checks.check_2d(lay, cols)
    bk = lay.parts_raw['bonk']
    rep['bonk'] = dict(strokes_ge_1mm=checks.bonk_stroke_check(bk), cap_mm=7.0,
                       bounds=[round(x, 2) for x in bk.bounds])
    rep['frame_gaps_lt_0.6'] = len(checks.frame_gap_check(lay))
    stl_rep, _ = checks.check_stls(stl_paths)
    rep['stls'] = stl_rep
    r3, info = checks.check_3mf(path3mf, lay.piece_names)
    rep['3mf'] = r3
    gaps, bbs = checks.object_gaps(info)
    rep['object_gaps'] = gaps
    xs = [b[1][0] for b in bbs]
    rep['tower_box'] = [round(x, 2) for x in tower]
    tw, th = tower[2] - tower[0], tower[3] - tower[1]
    rep['tower_clear_ok'] = bool(tw >= export.TOWER and th >= export.TOWER)
    layers = checks.layer_colors(info)
    rep['layers'] = [l for l in layers if l[1] >= 2.99]
    rep['first_layers'] = f'layers 1-{sum(1 for l in layers if l[2] <= 3.0 + 1e-6)} : {sorted({tuple(l[3]) for l in layers if l[2] <= 3.0 + 1e-6})}'
    sw, order = checks.min_swaps(layers)
    rep['min_swaps'] = sw
    rep['swap_order'] = [list(x) for x in order if len(x) > 1 or True]
    rep['grams'] = {k: round(v, 1) for k, v in checks.grams(cols).items()}
    rep['seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(a.out, 'build_report.json'), 'w') as f:
        json.dump(rep, f, indent=1, default=str)

    # summary
    print(f'{title}  c={p.c} mm  L={lay.L:.1f} mm  ({rep["seconds"]} s)')
    for o in r3['objects']:
        print(f"  {o['name']:<22} {o['length_x']:7.2f} mm  parts: " +
              ', '.join(f"{q['name'].split(' - ')[-1]} z{float(q['z'][0]):.1f}-{float(q['z'][1]):.1f}"
                        f"{'' if q['watertight'] else ' NOT WATERTIGHT'}" for q in o['parts']))
    print('  2D checks:', {k: v for k, v in rep['check_2d'].items() if v})
    print('  plate bounds', r3['plate_bounds'], 'inside margins:', r3['inside_plate_with_margin'])
    print('  object gaps', [(a, float(g)) for a, g in gaps], ' tower area', rep['tower_box'], rep['tower_clear_ok'])
    print('  Bonk!!!', rep['bonk'], ' sub-0.6 mm frame gaps:', rep['frame_gaps_lt_0.6'])
    print('  max part overlap volume (mm^3):',
          max((abs(v) for o in r3['objects'] for _, _, v in o['overlaps']), default=0.0))
    print('  STLs', [(s['file'], s['watertight'], round(s['volume'], 1)) for s in stl_rep])
    print('  raised layers', rep['layers'], ' min swaps', sw)
    print('  grams', rep['grams'])

    # hard limits
    fails = []
    for o in r3['objects']:
        if o['length_x'] > 245.0 + 1e-6:
            fails.append(f"{o['name']} is {o['length_x']} mm long (> 245)")
        for q in o['parts']:
            if not q['watertight']:
                fails.append(f"{q['name']} not watertight")
    if not r3['inside_plate_with_margin']:
        fails.append('pieces leave the 5 mm plate margin')
    if not rep['tower_clear_ok']:
        fails.append('prime tower area smaller than 55 x 55 mm')
    if any(g < 6.0 for _, g in gaps):
        fails.append('pieces closer than 6 mm')
    if any(rep['check_2d'][k] for k in ('keepout', 'overlap', 'thin', 'small')):
        fails.append('2D rule check failed (see build_report.json)')
    if not all(s['watertight'] for s in stl_rep):
        fails.append('an STL is not watertight')
    for f in fails:
        print('  FAIL:', f)
    if not fails:
        print('  all checks passed')
    rep['fails'] = fails
    return rep


if __name__ == '__main__':
    sys.exit(1 if main()['fails'] else 0)
