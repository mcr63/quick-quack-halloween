# Quick Quack Halloween Build

Team costume and walk-through display for the office Halloween contest. The theme is Quick Quack Car Wash. Judges walk through a mini car wash tunnel staffed by the team in costume. The display is built around three 3D-printed pieces: a 3 ft Quick Quack sign over the entrance, a servo gate arm at the pay station, and an oscillating brush in the lane.

- **Lead:** Matt Robertson
- **Contest:** Fri Oct 30, 2026 (assumed, see open questions)
- **Budget:** $371 planned, over the original $100-300 target because of the printed builds. A $273 cheap version that fits the target is in `03-Materials-List.md`.
- **Last updated:** Tue Sept 29, 2026

## Docs

| File | What's in it |
|---|---|
| `00-README.md` | This page |
| `01-Project-Brief.md` | Goal, concept, team roles, printed builds, gags, judging bit |
| `02-Brand-Reference.md` | Colors, filament matches, mascot, uniform, slogans, tunnel details, sources |
| `03-Materials-List.md` | What to buy, print, or bring. Costs and owners. |
| `04-Build-Schedule.md` | Weekly print and build checklist through setup day, plus run-of-show |
| `05-Build-Notes.md` | Canonical brief from the brand-assets chat: sign, gate arm, brush, servos. Wins on any conflict. |
| `06-Reference-Footage.md` | Sept 23 Tesla dashcam run through a real site: what's there, ideas for the build, stills list |

## Folder layout

```
Documents/Quick Quack/
  00-README.md ... 06-Reference-Footage.md
  assets/     logo SVG, PNG logo, banner JPEG
  print/      sign and banner files ready to print
  3d/         STL and 3MF zips and generator scripts for the Bambu P2S
  photos/     reference shots from the Orem location
    dashcam/  stills from the Sept 23 Tesla clips
  receipts/   receipts, for the budget tally
```

The same docs are also saved in the Claude Project "Quick Quack Car Wash" so any chat in the project can read them.

## Open questions

| Question | Why it matters | Status |
|---|---|---|
| Contest date and time. Oct 31 is a Saturday, so Fri Oct 30 is assumed. | Drives the whole schedule | Confirm |
| Judging criteria (costume only, display only, or both? group category?) | Sets where effort goes | Unknown |
| Space allowed: cubicle row, hallway, or conference room? | Sets the tunnel size | Unknown |
| Fog machine allowed? (smoke detectors) | Could lose $35 and a key effect | Ask facilities |
| Team members and who plays which role | Costume sizing and orders | TBD |
| Brand-assets chat imported? | Signs and prints wait on it | Done Sept 22. Brief is in `05-Build-Notes.md`. Zips go in `3d/`, SVG and images in `assets/`. Not copied yet. |
| Jig thickness: 1.8 mm as built, or 2.4 mm as recommended? | 2.4 is stiffer but uses ~140 g more white. 2.4 has not been regenerated. | Decide this week |
| Sonotube inside diameter and servo horn diameter | Turntable ring assumes 203.2 mm ID. Horn recess assumes a 21 mm disc; kits often ship 25 mm. | Measure when parts arrive |
| How the sign mounts over the entrance | Depends on the space. Sign plus backer is about 36 x 14 in. | TBD after space is known. Arch idea in `06-Reference-Footage.md`. |
