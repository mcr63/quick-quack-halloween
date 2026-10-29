# WRONG WAY sign

A 3D-printed WRONG WAY sign with Matt's rear-view duck walking off to the right. It clips onto 1 in PVC pipe: a free-standing pole, or a vertical upright or horizontal crossbar on the car wash frame. It prints on a Bambu P2S with an AMS.

- Sign: 240 × 144 mm (5:3, like the real R5-1a), 12 mm corners. Orange base, yellow border, yellow WRONG / WAY (32.5 mm capitals) with a 0.8 mm black outline, and the duck on the right (about 69 × 105 mm).
- Receivers (4): 30 × 30 × 14 mm blocks with a 20.3 mm square pocket, 12 mm deep. They get glued to the back of the sign.
- Clips (2): a C that snaps onto 1 in Sch 40 PVC (33.4 mm), with a 20 × 20 mm square peg that pushes into a receiver. The peg is square, so the clip can turn 90° for a vertical or horizontal pipe.

## Files (in `out/`)

- `WRONG_WAY_A_sign_bambu.3mf`: plate A, the sign. Bambu Studio project for the P2S. Use this.
- `WRONG_WAY_B_mounts_bambu.3mf`: plate B, 4 receivers and 2 clips, black. Use this.
- `WRONG_WAY_A_sign.3mf`, `WRONG_WAY_B_mounts.3mf`: the same plates as plain 3MFs, in case the Bambu ones give trouble.
- `WRONG_WAY_STLs.zip`: backup, one STL per color per part, already placed on the plate.
- `preview_sign.png`: the finished sign.
- `preview_assembly.png`: the back of the sign on a vertical and a horizontal pipe, and a section through a clip.
- `preview_plate_A.png`, `preview_plate_B.png`: plate layouts.
- `manifest.json`, `build_report.json`: part list and check results.

## Print

1. Load the AMS: 1 yellow, 2 orange, 3 white, 4 black. Parts go by filament number, not by color.
2. Plate A, the sign: open `WRONG_WAY_A_sign_bambu.3mf`. It's set up for the P2S: 0.20 mm Standard, Bambu PLA Basic, Supertack plate, print by object, prime tower behind the sign. When you send it, match filaments 1–4 to the AMS slots if Studio asks.
3. Plate B, the mounts: open `WRONG_WAY_B_mounts_bambu.3mf`. Black only, so no filament changes.
4. No supports. The sign prints face up. Receivers print glue face down, pocket up. Clips print lying flat, with the C on the bed.

PETG is better for the clips if you have it, since the C has to flex to snap on. PLA works too. Just don't spread the clip wider than it takes to get it on the pipe.

Bambu Studio's estimate, purge and prime tower included:
- Plate A: 81 g orange, 5 g yellow, 1.4 g black, 1 g white. About 2 h 8 min, with 4 filament changes, all in the last 2 layers.
- Plate B: 35 g black, about 1 h 3 min.

Why two plates: all of it fits on one plate only if printed by layer. That would mean an orange-to-black swap on every one of the first 15 layers. Print by object doesn't work either: the P2S needs about 72 mm between objects once one of them is taller than 4.2 mm, and the clips are 20 mm tall. With the sign on the plate, that leaves a 30 mm strip, and the clips are 40 mm across.

If you use the plain 3MFs instead: Studio warns that the file isn't from Bambu Lab and loads only the shapes and colors, which is fine. Each part keeps its filament. Put the prime tower behind the sign.

## Assemble

1. Lay the sign face down. Glue the 4 receivers to the back with CA, pockets facing out, in a plus around the center of the sign:
   - top and bottom: centered left to right, 40 mm above and below center
   - left and right: centered top to bottom, 70 mm left and right of center
2. Vertical pipe: snap a clip onto the pipe at each of the top and bottom receivers, then push both pegs into those receivers. Horizontal pipe: same, using the left and right receivers. The pipe always runs through the center of the sign, about 38 mm behind it, and clears the two unused receivers.
3. If a peg is loose, put a dab of CA in the pocket. If it's too tight, sand the peg a little.

Scuff the glue faces with sandpaper before gluing. CA accelerator helps.

For a free-standing sign, use the floor base from the HONK sign. It takes the same 1 in pipe. Its file is on Matt's Mac in `Documents/Quick Quack/honk-sign`.

## Native Bambu files

The `_bambu` files are built from a project Matt saved in Bambu Studio 02.06.00.51 for the P2S. They keep that project's printer, process and filament settings, swap in these parts, and set the filament colors (yellow, orange, white, black), purge amounts, prime tower spot, and print sequence. To rebuild them:

```
python src/to_bambu.py --template "path/to/Bambu_saved_P2S.3mf"
```

The template can have any number of filaments. If it has fewer than 4, the script adds more, copying filament 1's settings. It uses Bambu Studio's own list of per-filament settings (from its source, v02.06.00.51) and stops if a setting doesn't have the expected size. It then checks that every part lands where it should, on the right filament.

Both files were sliced headless with the Bambu Studio 02.06.00.51 Linux CLI, with no errors or warnings.

## Rebuild

This needs Python 3.10 or newer.

```
pip install -r ../duck-clearance-bar/requirements.txt
python src/build.py
```

The files go to `out/`. A build takes about 15 seconds and checks itself:
- watertight meshes, no overlapping parts, plate margins and the prime tower area
- line widths: text and border at least 1 mm; duck lines and the text outline at least 0.8 mm
- the mount, on a vertical and a horizontal pipe: no part hits the pipe, the sign or another part

WRONG WAY is set to the largest size that fits beside the duck. There's at least 3 mm between the letters and the duck, and at least 1 mm of orange between the outline and the duck or border. To fit, the text sits 4 mm above center.

Font: Overpass Bold (SIL Open Font License, in `fonts/`), an open-source copy of the Highway Gothic road-sign look, from the `@fontsource/overpass` npm package. The duck is Matt's art, `assets/duck_rear.svg`.
