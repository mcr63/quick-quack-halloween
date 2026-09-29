# Build Notes — sign, gate arm, brush

Source: Matt's "Quick Quack Car Wash brand assets" chat, Sept 17–22, 2026. Pasted in verbatim on Sept 22. This is the canonical record of the 3D-printed builds. When it conflicts with the other docs, this wins.

Printer is a Bambu Lab P2S (256 mm bed, no AMS), 0.4 nozzle. Matt has Home Assistant + ESPHome experience.

## The event
Walk-through "car wash" tunnel at work for Halloween. Pieces in progress:
1. **3 ft Quick Quack sign** (3D printed, multi-part, glued)
2. **Gate arm** that lifts to let people through (printed, servo or string)
3. **Oscillating brush** — 8" Sonotube on a servo-driven turntable
4. General tunnel materials (see bottom)

## Source art
Brandfetch-style zip with the logo SVG (`Quick_Quack_Car_Wash_id-a7kFg2S_2.svg`, 1366x768 viewBox, full color) plus a PNG logo and a banner JPEG. Logo colors: green #007550, yellow #FFCF42, orange #F79239, white, black. Paths in draw order: white outline (1), green block (1), CAR WASH letters (7 white), green stripes (2), Quick Quack letters (10 green), duck (yellow 4, orange 4, black ~24, white ~14).

## 1. The sign — current design (3 ft = 914 x 349 mm)
All parts flat, 3 mm unless noted, no supports. One color per print (no AMS). Parts glue into a **white pocketed jig**.

**Already printed:** all green (18 parts) and the yellow duck body. Don't change those.

### Current part set (zip: `qq_sign_3ft_COMPLETE.zip`, plus `qq_sign_jig.zip`)
- **Green (printed):** block in 3 tiles with dovetails on the two seams; CAR WASH letters cut out of it (0.25 mm total clearance); tile 3 has a through-cutout for the yellow duck body and two 2 mm pockets for the orange feet. Plus 3 green counters (inside the A's and R), 10 Quick Quack letters, 2 stripes.
- **White:** 7 CAR WASH inlay letters (drop into the green cutouts); duck lens backing (2 mm); duck glints (1.5 mm, goes on last, or use a paint marker).
- **Yellow (printed):** duck body, 3 mm, full silhouette (runs *under* the black lines — it's clip art, not an inlay).
- **Orange:** beak + feet, 2 mm.
- **Black:** duck line work in 2 tiles, **stepped underside** — 2 mm thick over yellow/green, 3 mm over orange/lens backing, 5 mm where it reaches past everything to the board. Top is flat at 5 mm. Print top-face-up, no supports. It only sits flat when everything under it is placed right. (The original flat 2 mm black tiles also work with hot glue under the outer edge.)
- **Jig:** 8 white tiles (4x2), 1.2 mm floor + 0.6 mm recess = 1.8 mm; recess is the union of every on-board part (+0.3 mm); raised white = the logo's halo; dovetails on seams. **Open question:** Matt asked if 1.8 is too thin; recommendation was 1.6 + 0.8 = 2.4 mm (~560 g vs 420 g). Not yet regenerated.

### Assembly order (bottom up)
Jig glued to a backer → green tiles (dovetails) → white CAR WASH letters + green counters → Quick Quack letters + stripes → yellow body into tile 3 cutout → orange feet in pockets, beak and lens backing on the board → black tiles on top → glints.

### Superseded / don't use
Earlier 220 mm multi-color sign (AMS version); foam-board cut template PDF (jig replaces it); trimmed green tile 3 (167 mm); green filler; the white duck "backer" and "halo" pieces; plain white_CARWASH letters from the first set (use the `white_inlay_*` ones).

### Filament matches
Bambu: PETG Basic Green (#009639) or PLA Mistletoe Green; Sunflower Yellow; Pumpkin Orange; Jade White; Black/Matte Charcoal.
Sunlu: Grass Green (the deep blue-green one, not lawn "Green"); Vivid Yellow; Sunny Orange; White; Black.

## 2. Gate arm (zip: `gate_arm`)
Fully printed, no PVC. Base pedestal (120x90 flange, ears, pivot 150 mm up, servo pocket on one ear, 8 mm hole on the other), hub (M8 axle bore, round 25T horn recess, socket for the arm, tail with two M8 holes for ~1 kg counterweight, string hole), 8 arm segments 120 mm each (36x24 mm hollow rect, 2.4 mm walls, 40 mm tenon + M4 bolt per joint, 4 red + 4 white = 960 mm), rounded end segment. Print segments lying flat. Limit travel to ~80° so the tail clears the flange. ESPHome `number` entity 0–80.

## 3. Oscillating brush (zip: `brush_base`)
Vertical 8" Sonotube (assumed ID 203.2 mm — **measure it**) on a printed turntable. Base plate 240x240x6 with 48 mm legs, servo slot in the center (DS3225 body 40x20x40.5, flanges screw up against the underside, cable runs out under the plate), 4 radial slots for any 4–6" lazy-susan bearing. Turntable: flange + 35 mm ring with 8 crush ribs + spokes + horn recess underneath + 4 screw holes into the cardboard. Optional top cap. Bearing carries the load; servo only swings ±50° every 2 s. ESPHome `switch` "Brush Oscillate" running a loop script. Files are clean (watertight, 2D-profile built). **Check the horn:** recess is for a 21 mm disc, 4 screws on a 17 mm bolt circle; AliExpress kits often ship 25 mm — measure and adjust.

## Servos / electronics
Matt found a $5 AliExpress "25 kg" 180° DS3225-class servo — right size and type. Advice given: torque isn't the constraint (bearing + counterweight), buy 3–4 for spares, use a separate 6 V 5 A supply with shared ground, expect the cheap one to run warm — trigger from a PIR/button in HA rather than running for hours. A name-brand DS3225 (~$18) is the upgrade if the brush must run all night. Delivery ~Sept 23–27.

## Tunnel materials (ideas given)
Frame: PVC/canopy + black tablecloths. Brushes: pool-noodle strips on Sonotube or box fans, feather boas. Curtains: tablecloth strips, party fringe. Effects: bubble machine, fogger, cotton "foam", LED "wax." Dryer: leaf blower / fans at exit. Signage, "choose your wash" menu, vacuum station, duck costumes. Spin options: fan, drill on a stand, rotisserie motor, rotating tree stand, gearmotor on a smart plug.

## Working notes / lessons
- Build STLs from shapely 2D profiles + `trimesh.creation.extrude_polygon`, boolean with `engine='manifold'`. Always check `is_watertight` and `split()` piece count.
- Don't preview with matplotlib 3D — it sorts triangles wrong and looked like broken geometry twice. A small numpy z-buffer renderer (`render.py`) or 2D section drawings are reliable.
- Overlapping many small cylinders for slots = scalloped walls; use `LineString.buffer` stadiums instead.
- SVG even-odd fills: sort subpaths by area, subtract contained ones.
- Clearances used: inlays 0.25 mm total, jig/pockets 0.3 mm, dovetails 0.24 mm.
- Bed usable width taken as 245 mm.

## Files to drop into the folder
Not in this folder yet. From the brand-assets chat:
- `assets/` — logo SVG, PNG logo, banner JPEG
- `3d/` — `qq_sign_3ft_COMPLETE.zip`, `qq_sign_jig.zip`, `gate_arm` zip, `brush_base` zip, `render.py` and the generator scripts
