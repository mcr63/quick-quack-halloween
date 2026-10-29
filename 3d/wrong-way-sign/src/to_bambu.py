#!/usr/bin/env python3
"""Re-pack the plate 3MFs in out/ as native Bambu Studio projects.

Bambu Studio only treats a 3MF as its own project (no "not from Bambu Lab"
warning) when it carries Bambu's full project settings. We can't write those
from scratch with confidence, so this script copies them from a 3MF that
Bambu Studio itself saved for the P2S (for example
~/Documents/Quick Quack/duck-clearance-bar/DUCK_clearance_6ft7_bambu.3mf) and
swaps in our objects, filament colors, prime-tower spot and print sequence.
Same method as the HONK sign files (checked there: every part landed exactly
where Bambu Studio put it).

    python3 src/to_bambu.py --template path/to/Bambu_saved.3mf
    python3 src/to_bambu.py --template T.3mf --out out --manifest out/manifest.json

A template saved with fewer filaments than we need (e.g. 2) is expanded to 4
first (see expand_filaments). Writes out/*_bambu.3mf next to the standard
files and checks that every part's position and filament matches the source.
"""
import argparse
import json
import os
import re
import sys
import zipfile

import numpy as np
from lxml import etree

NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
P_NS = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
HDR = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
       'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
       'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
       'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n')


# Filament option keys, from BambuStudio v02.06.00.51 src/libslic3r/Preset.cpp
# (s_Preset_filament_options). Bambu Studio builds the project config by appending
# one block per filament for each of these (PresetBundle::full_fff_config).
FILAMENT_OPTION_KEYS = {
    'activate_air_filtration', 'additional_cooling_fan_speed', 'additional_fan_full_speed_layer',
    'chamber_temperatures', 'circle_compensation_speed', 'close_additional_fan_first_x_layers',
    'close_fan_the_first_x_layers', 'compatible_printers', 'compatible_printers_condition',
    'compatible_prints', 'compatible_prints_condition', 'complete_print_exhaust_fan_speed',
    'cool_plate_temp', 'cool_plate_temp_initial_layer', 'cooling_perimeter_transition_distance',
    'cooling_slowdown_logic', 'counter_coef_1', 'counter_coef_2', 'counter_coef_3',
    'counter_limit_max', 'counter_limit_min', 'default_filament_colour', 'diameter_limit',
    'during_print_exhaust_fan_speed', 'enable_overhang_bridge_fan', 'enable_pressure_advance',
    'eng_plate_temp', 'eng_plate_temp_initial_layer', 'fan_cooling_layer_time', 'fan_max_speed',
    'fan_min_speed', 'filament_adaptive_volumetric_speed', 'filament_adhesiveness_category',
    'filament_bridge_speed', 'filament_change_length', 'filament_change_length_nc',
    'filament_cooling_before_tower', 'filament_cost', 'filament_density',
    'filament_deretraction_speed', 'filament_dev_ams_drying_ams_limitations',
    'filament_dev_ams_drying_heat_distortion_temperature', 'filament_dev_ams_drying_temperature',
    'filament_dev_ams_drying_time', 'filament_dev_chamber_drying_bed_temperature',
    'filament_dev_chamber_drying_time', 'filament_dev_drying_cooling_temperature',
    'filament_dev_drying_softening_temperature', 'filament_diameter',
    'filament_enable_overhang_speed', 'filament_end_gcode', 'filament_extruder_compatibility',
    'filament_extruder_variant', 'filament_flow_ratio', 'filament_flush_temp',
    'filament_flush_volumetric_speed', 'filament_is_support', 'filament_long_retractions_when_cut',
    'filament_max_volumetric_speed', 'filament_metal_stickiness',
    'filament_minimal_purge_on_wipe_tower', 'filament_notes', 'filament_overhang_1_4_speed',
    'filament_overhang_2_4_speed', 'filament_overhang_3_4_speed', 'filament_overhang_4_4_speed',
    'filament_overhang_totally_speed', 'filament_pre_cooling_temperature',
    'filament_pre_cooling_temperature_nc', 'filament_prime_volume', 'filament_prime_volume_nc',
    'filament_printable', 'filament_ramming_travel_time', 'filament_ramming_travel_time_nc',
    'filament_ramming_volumetric_speed', 'filament_ramming_volumetric_speed_nc',
    'filament_retract_before_wipe', 'filament_retract_length_nc', 'filament_retract_restart_extra',
    'filament_retract_when_changing_layer', 'filament_retraction_distances_when_cut',
    'filament_retraction_length', 'filament_retraction_minimum_travel', 'filament_retraction_speed',
    'filament_scarf_gap', 'filament_scarf_height', 'filament_scarf_length',
    'filament_scarf_seam_type', 'filament_shrink', 'filament_soluble', 'filament_start_gcode',
    'filament_tower_interface_pre_extrusion_dist', 'filament_tower_interface_pre_extrusion_length',
    'filament_tower_interface_print_temp', 'filament_tower_interface_purge_volume',
    'filament_tower_ironing_area', 'filament_type', 'filament_velocity_adaptation_factor',
    'filament_vendor', 'filament_wipe', 'filament_wipe_distance', 'filament_z_hop',
    'filament_z_hop_types', 'first_x_layer_fan_speed', 'first_x_layer_part_fan_speed',
    'full_fan_speed_layer', 'hole_coef_1', 'hole_coef_2', 'hole_coef_3', 'hole_limit_max',
    'hole_limit_min', 'hot_plate_temp', 'hot_plate_temp_initial_layer', 'impact_strength_z',
    'inherits', 'ironing_fan_speed', 'long_retractions_when_ec',
    'no_slow_down_for_cooling_on_outwalls', 'nozzle_temperature',
    'nozzle_temperature_initial_layer', 'nozzle_temperature_range_high',
    'nozzle_temperature_range_low', 'overhang_fan_speed', 'overhang_fan_threshold',
    'overhang_threshold_participating_cooling', 'override_process_overhang_speed',
    'pre_start_fan_time', 'pressure_advance', 'reduce_fan_stop_start_freq',
    'retraction_distances_when_ec', 'slow_down_for_layer_cooling', 'slow_down_layer_time',
    'slow_down_min_speed', 'supertack_plate_temp', 'supertack_plate_temp_initial_layer',
    'temperature_vitrification', 'textured_plate_temp', 'textured_plate_temp_initial_layer',
    'volumetric_speed_coefficients',
}

# Project-level keys sized one entry per filament (PresetBundle.cpp s_project_options
# and PrintConfig.cpp). Checked against v02.06.00.51.
PROJECT_PER_FILAMENT = {
    'filament_colour', 'filament_multi_colour', 'filament_colour_type', 'filament_map',
    'filament_volume_map', 'filament_nozzle_map', 'filament_is_mixed', 'filament_mixed_gradient',
    'filament_ids', 'filament_settings_id', 'flush_volumes_vector',
}
# Per-filament in Bambu Studio but only read when a slot is a mixed filament; a saved
# project keeps them at one empty entry. Left as they are.
MIXED_ONLY = {'filament_mixed_components', 'filament_mixed_sublayer_ratios', 'filament_mixed_gradient_range'}


def expand_filaments(ps, n_new):
    """Grow a project config saved with n filaments to n_new filaments, using filament 1's
    settings for the new ones. Each per-filament list is n chunks (1 value per filament,
    or one per extruder variant, etc.); filament 1's chunk is repeated n_new times.
    filament_self_index is rebuilt (1,1,2,2,...); flush_volumes_matrix becomes n_new x n_new
    (to_bambu sets its values). Raises on any list whose length isn't a multiple of n.
    Returns {shape: [keys]} of what changed and a list of keys left alone on purpose."""
    n = len(ps['filament_colour'])
    if n_new <= n:
        return {}, []
    changed, skipped = {}, []
    for k, v in list(ps.items()):
        if not isinstance(v, list):
            continue
        if k in MIXED_ONLY:
            if len(v) not in (1, n):
                raise SystemExit(f'{k}: unexpected length {len(v)}')
            if len(v) == n and any(x not in ('', '0') for x in v):
                raise SystemExit(f'{k}: template uses mixed filaments; not expanding')
            if len(v) == n:
                ps[k] = v[:1] * n_new
                changed.setdefault('mixed (1 per filament)', []).append(k)
            else:
                skipped.append(k)
            continue
        if k == 'flush_volumes_matrix':
            if len(v) != n * n:
                raise SystemExit(f'flush_volumes_matrix has {len(v)} entries, expected {n * n}')
            ps[k] = ['0'] * (n_new * n_new)
            changed.setdefault('n x n matrix', []).append(k)
            continue
        if k == 'filament_self_index':
            if len(v) % n:
                raise SystemExit(f'filament_self_index length {len(v)} is not a multiple of {n}')
            c = len(v) // n
            ps[k] = [str(i + 1) for i in range(n_new) for _ in range(c)]
            changed.setdefault(f'{c} per filament', []).append(k)
            continue
        if k in FILAMENT_OPTION_KEYS or k in PROJECT_PER_FILAMENT:
            if len(v) % n:
                raise SystemExit(f'{k}: length {len(v)} is not a multiple of {n} filaments; refusing to guess')
            c = len(v) // n
            ps[k] = v[:c] * n_new
            changed.setdefault(f'{c} per filament', []).append(k)
    for k in ('different_settings_to_system', 'inherits_group'):   # sized n + 2 when present
        if k in ps:
            v = ps[k]
            if len(v) != n + 2:
                raise SystemExit(f'{k}: length {len(v)}, expected {n + 2}')
            ps[k] = [v[0]] + v[1:2] * n_new + [v[-1]]
            changed.setdefault('n + 2', []).append(k)
    return changed, skipped


def _esc(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')


def read_src(path):
    """Objects of a standard (generator) 3MF: name and parts with world vertices, faces, name, extruder."""
    z = zipfile.ZipFile(path)
    root = etree.fromstring(z.read('3D/3dmodel.model'))
    cfg = etree.fromstring(z.read('Metadata/model_settings.config'))
    objs = {o.get('id'): o for o in root.iterfind('.//m:resources/m:object', NS)}

    def mesh(o):
        v = np.array([[float(e.get(k)) for k in 'xyz'] for e in o.iterfind('.//m:vertex', NS)])
        t = np.array([[int(e.get(k)) for k in ('v1', 'v2', 'v3')] for e in o.iterfind('.//m:triangle', NS)])
        return v, t
    out = []
    for item in root.iterfind('.//m:build/m:item', NS):
        oid = item.get('objectid')
        off = np.array([float(x) for x in item.get('transform').split()][9:12])
        ocfg = cfg.find(f"object[@id='{oid}']")
        parts = []
        for comp in objs[oid].iterfind('.//m:component', NS):
            pcfg = ocfg.find(f"part[@id='{comp.get('objectid')}']")
            coff = np.array([float(x) for x in comp.get('transform').split()][9:12])
            v, t = mesh(objs[comp.get('objectid')])
            parts.append(dict(v=v + coff + off, t=t, name=pcfg.find("metadata[@key='name']").get('value'),
                              ext=pcfg.find("metadata[@key='extruder']").get('value')))
        out.append(dict(name=ocfg.find("metadata[@key='name']").get('value'), parts=parts))
    return out


def world_parts(path):
    """Per part of a written Bambu project: (name-free) triangle count, world min, world max."""
    z = zipfile.ZipFile(path)
    main = etree.fromstring(z.read('3D/3dmodel.model'))
    files = {}

    def objmesh(p, oid):
        if p not in files:
            files[p] = etree.fromstring(z.read(p.lstrip('/')))
        o = files[p].find(f".//m:object[@id='{oid}']", NS)
        return (np.array([[float(e.get(k)) for k in 'xyz'] for e in o.iterfind('.//m:vertex', NS)]),
                len(o.findall('.//m:triangle', NS)))
    objs = {o.get('id'): o for o in main.iterfind('.//m:resources/m:object', NS)}
    out = []
    for it in main.iterfind('.//m:build/m:item', NS):
        io = np.array([float(x) for x in it.get('transform').split()][9:])
        for c in objs[it.get('objectid')].iterfind('.//m:component', NS):
            co = np.array([float(x) for x in c.get('transform').split()][9:])
            v, nt = objmesh(c.get(P_NS + 'path'), c.get('objectid'))
            w = v + co + io
            out.append((nt, w.min(0), w.max(0)))
    return out


def write(objects, template, dst, title, colours, tower=None, sequence=None, plate_name=''):
    tz = zipfile.ZipFile(template)
    ps = json.loads(tz.read('Metadata/project_settings.config'))
    expand_filaments(ps, len(colours))
    ps['filament_colour'] = list(colours) + ps['filament_colour'][len(colours):]
    if 'filament_multi_colour' in ps:
        ps['filament_multi_colour'] = list(ps['filament_colour'])
    if len(ps.get('flush_volumes_matrix', [])) == 16:
        # purge (mm3), rows = from, cols = to, for 1 yellow, 2 orange, 3 white, 4 black:
        # more going dark -> light, less going light -> dark. Studio may recalc from the real spools.
        ps['flush_volumes_matrix'] = [str(x) for x in (0, 150, 250, 150,
                                                       300, 0, 350, 150,
                                                       200, 200, 0, 150,
                                                       600, 500, 700, 0)]
    if tower:
        ps['wipe_tower_x'] = [f'{tower[0]:g}']
        ps['wipe_tower_y'] = [f'{tower[1]:g}']
    if sequence:
        ps['print_sequence'] = sequence
    n = 0
    res, build, rels, plate, asm = [], [], [], [], []
    mset = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    cut = ['<?xml version="1.0" encoding="utf-8"?>\n<objects>\n']
    objfiles = {}
    for k, ob in enumerate(objects, 1):
        allv = np.vstack([p['v'] for p in ob['parts']])
        lo, hi = allv.min(0), allv.max(0)
        org = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0])
        fname = f'3D/Objects/object_{k}.model'
        body = [HDR, ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n']
        comps, mparts = [], []
        for j, p in enumerate(ob['parts']):
            n += 1
            pid = n
            v = p['v'] - org
            c = (v.min(0) + v.max(0)) / 2
            v = v - c
            body.append(f'  <object id="{pid}" p:UUID="{k:04x}{j:04x}-81cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                        '   <mesh>\n    <vertices>\n')
            body.append(''.join(f'     <vertex x="{a:.6g}" y="{b:.6g}" z="{d:.6g}"/>\n' for a, b, d in v))
            body.append('    </vertices>\n    <triangles>\n')
            body.append(''.join(f'     <triangle v1="{a}" v2="{b}" v3="{d}"/>\n' for a, b, d in p['t']))
            body.append('    </triangles>\n   </mesh>\n  </object>\n')
            ct = f'1 0 0 0 1 0 0 0 1 {c[0]:.6g} {c[1]:.6g} {c[2]:.6g}'
            comps.append(f'    <component p:path="/{fname}" objectid="{pid}" '
                         f'p:UUID="{k:04x}{j:04x}-b206-40ff-9872-83e8017abed1" transform="{ct}"/>\n')
            mparts.append(f'''    <part id="{pid}" subtype="normal_part">
      <metadata key="name" value="{_esc(p['name'])}"/>
      <metadata key="matrix" value="1 0 0 {c[0]:.6g} 0 1 0 {c[1]:.6g} 0 0 1 {c[2]:.6g} 0 0 0 1"/>
      <metadata key="source_file" value="{_esc(title)}.3mf"/>
      <metadata key="source_object_id" value="{k - 1}"/>
      <metadata key="source_volume_id" value="{j}"/>
      <metadata key="source_offset_x" value="{c[0]:.6g}"/>
      <metadata key="source_offset_y" value="{c[1]:.6g}"/>
      <metadata key="source_offset_z" value="{c[2]:.6g}"/>
      <metadata key="extruder" value="{p['ext']}"/>
      <mesh_stat face_count="{len(p['t'])}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
''')
        body.append(' </resources>\n <build/>\n</model>\n')
        objfiles[fname] = ''.join(body)
        n += 1
        oid = n
        res.append(f'  <object id="{oid}" p:UUID="{k:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                   f'   <components>\n{"".join(comps)}   </components>\n  </object>\n')
        it = f'1 0 0 0 1 0 0 0 1 {org[0]:.6g} {org[1]:.6g} 0'
        build.append(f'  <item objectid="{oid}" p:UUID="{oid:08x}-b1ec-4553-aec9-835e5b724bb4" transform="{it}" printable="1"/>\n')
        rels.append(f' <Relationship Target="/{fname}" Id="rel-{k}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n')
        mset.append(f'  <object id="{oid}">\n    <metadata key="name" value="{_esc(ob["name"])}"/>\n'
                    f'    <metadata key="extruder" value="{ob["parts"][0]["ext"]}"/>\n{"".join(mparts)}  </object>\n')
        plate.append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n'
                     '      <metadata key="instance_id" value="0"/>\n    </model_instance>\n')
        asm.append(f'   <assemble_item object_id="{oid}" instance_id="0" transform="{it}" offset="0 0 0" />\n')
        cut.append(f' <object id="{k}">\n  <cut_id id="0" check_sum="1" connectors_cnt="0"/>\n </object>\n')
    seq = f'    <metadata key="print_sequence" value="{sequence}"/>\n' if sequence else ''
    mset.append('  <plate>\n    <metadata key="plater_id" value="1"/>\n'
                f'    <metadata key="plater_name" value="{_esc(plate_name)}"/>\n    <metadata key="locked" value="false"/>\n'
                + seq + ''.join(plate) + '  </plate>\n  <assemble>\n' + ''.join(asm) + '  </assemble>\n</config>\n')
    cut.append('</objects>\n')
    main = re.sub(r'<resources>.*</build>', '<resources>\n' + ''.join(res).rstrip('\n') +
                  '\n </resources>\n <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n' + ''.join(build) + ' </build>',
                  tz.read('3D/3dmodel.model').decode(), flags=re.S)
    main = re.sub(r'<metadata name="Title">.*?</metadata>', f'<metadata name="Title">{_esc(title)}</metadata>', main)
    names = set(tz.namelist())
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', tz.read('[Content_Types].xml'))
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                   ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
        z.writestr('3D/3dmodel.model', main)
        z.writestr('3D/_rels/3dmodel.model.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                   + ''.join(rels) + '</Relationships>')
        for f, s in objfiles.items():
            z.writestr(f, s)
        z.writestr('Metadata/project_settings.config', json.dumps(ps, indent=4))
        z.writestr('Metadata/model_settings.config', ''.join(mset))
        z.writestr('Metadata/cut_information.xml', ''.join(cut))
        for extra in ('Metadata/slice_info.config', 'Metadata/filament_sequence.json'):
            if extra in names:
                z.writestr(extra, tz.read(extra))


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    out_default = os.path.join(os.path.dirname(here), 'out')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--template', required=True, help='a 3MF that Bambu Studio saved for the P2S (4 filaments)')
    ap.add_argument('--out', default=out_default)
    ap.add_argument('--manifest', default=None)
    a = ap.parse_args(argv)
    man = json.load(open(a.manifest or os.path.join(a.out, 'manifest.json')))
    ok = True
    ps = json.loads(zipfile.ZipFile(a.template).read('Metadata/project_settings.config'))
    n0 = len(ps['filament_colour'])
    changed, skipped = expand_filaments(ps, len(man['filament_hex']))
    if changed:
        print(f'template has {n0} filaments; expanded to {len(man["filament_hex"])}:')
        for shape, keys in sorted(changed.items()):
            print(f'  {shape}: {len(keys)} keys')
        if skipped:
            print('  left as is (mixed-filament only, 1 empty entry):', ', '.join(skipped))
    for pl in man['plates']:
        src = os.path.join(a.out, pl['file'])
        dst = os.path.join(a.out, pl['bambu_file'])
        objs = read_src(src)
        write(objs, a.template, dst, pl['title'], man['filament_hex'], tower=pl.get('wipe_tower_xy'),
              sequence=pl.get('print_sequence'), plate_name=pl['title'])
        want = [(len(p['t']), p['v'].min(0), p['v'].max(0)) for o in objs for p in o['parts']]
        got = world_parts(dst)
        cfg = etree.fromstring(zipfile.ZipFile(dst).read('Metadata/model_settings.config'))
        ext_got = [pt.find("metadata[@key='extruder']").get('value') for pt in cfg.iter('part')]
        ext_want = [p['ext'] for o in objs for p in o['parts']]
        if ext_got != ext_want:
            ok = False
            print(f"  filament mismatch: {ext_got} vs {ext_want}")
        err = max(max(np.abs(w[1] - g[1]).max(), np.abs(w[2] - g[2]).max()) for w, g in zip(want, got))
        same = len(want) == len(got) and all(w[0] == g[0] for w, g in zip(want, got)) and err < 1e-3
        ok &= same
        print(f"{pl['bambu_file']}: {len(got)} parts, filaments {ext_got}, max position error {err:.2e} mm, "
              f"{'ok' if same and ext_got == ext_want else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
