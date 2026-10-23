# DUCK! clearance bar

A 3D-printed copy of the Quick Quack "DUCK! CLEARANCE" bar, set to 6'-7". It prints on a Bambu P2S with an AMS. The sign is about 25 × 2.75 in (637 × 70 mm). It prints as 3 pieces on one plate, and the pieces join with dovetails.

## Files

- `DUCK_clearance_6ft7.3mf`: open this in Bambu Studio. Each part already has its filament set.
- `DUCK_clearance_STLs.zip`: backup, one STL per color.
- `preview_sign.png`, `preview_plate.png`: the finished sign and the plate layout.
- `src/`, `fonts/`, `assets/`: the script that builds everything.

## Print

1. Set filaments 1–4 to yellow, orange, green, black. Parts go by filament number, not by color. Either load the AMS in that order and sync it, or reorder the filaments in the project.
2. Open the 3MF. Bambu Studio will warn that the file isn't from Bambu Lab and that it's loading only the shapes and colors. That's expected, and each part keeps its filament. If it asks how to open the file, pick "Import geometry only."
3. If the prime tower lands on a piece, drag it to the empty back-right corner.
4. After printing, glue the dovetails with CA glue.

To use the STLs instead: import all 4 at once and say yes to loading them as one object with multiple parts. Then set each part's filament.

Layers: the yellow base runs from 0 to 3.0 mm. On top of it, orange is 0.2 mm, green 0.4 mm, and black 0.6 mm, so each layer drops a color. That's about 4 filament swaps. Filament: about 102 g yellow, 1 g orange, 2 g green, and 7 g black, plus purge.

## Change the clearance

This needs Python 3.10 or newer.

```
pip install -r requirements.txt
python src/build.py --feet 7 --inches 2
```

The files go to `out/`. A build takes about 10 seconds and checks itself: watertight meshes, piece lengths, and plate fit. Run `python src/build.py --help` for the other options.

Fonts: Lilita One and Bebas Neue, both under the SIL Open Font License (included). The duck comes from the Quick Quack logo SVG in `assets/`. Only the duck is used.
