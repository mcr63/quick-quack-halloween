# Reference Footage: Tesla Dashcam, Sept 23

Three front-camera clips from Wed Sept 23, 2026, about 7:58 AM. They run from the street through the pay lane and gate to the conveyor at the tunnel mouth. The Tesla camera tints everything teal. The stills are color-corrected, so treat colors as close, not exact.

Stills: `photos/dashcam/`, numbered 01-12 (list at the bottom). Labeled board: `photos/qq_dashcam_board.jpg`.

## What's there, in drive order

| Stop | What we saw | Stills |
|---|---|---|
| Approach | Big orange balls along the curb under the side canopy, and on both sides of the tunnel mouth | 01, 06 |
| Pay lanes | Green canopy with lane signs on the front edge: CASHIER (green) and MEMBERS (yellow). Black-and-yellow speed humps. | 02 |
| Upsell sign | Ceramic Duck poster on an A-frame between two yellow bollards, before the kiosk | 02 |
| Kiosk | Tall portrait screen on a post between yellow bollards. Tiers stacked as color bands: Ceramic Duck purple, Lucky Duck green, a third tier light blue. Each price sits in a white circle. App promo with the duck at the bottom. | 03 |
| Clearance bar | One per lane, hung from the canopy on two chains. Yellow, with orange hazard stripes on both ends. Green "DUCK!", a duck icon, "CLEARANCE 7'-2"", three down arrows. | 04, 10 |
| Gate | White arm with three red bands. White pedestal with a green cap, a round badge, and a no-pedestrians sticker. | 04, 11 |
| Gate lift | Straight up, flat to vertical in about 1.2 s. Slow at the start and the end. | 05 |
| After the gate | "PLEASE NOTE" sign on a stand. Too blurry to read. | 04 |
| Tunnel mouth | Yellow front, gray stone pillars, rounded arch opening. Logo sign on a white panel at the top. A framed poster on each side. | 06 |
| Prep attendant | Black jacket, white shirt and dark tie, black cap, over-ear hearing protection, black gloves, tall black boots. Holds a yellow coiled hose with a spray gun. Waved the car onto the conveyor. Can't tell if the tie is duck print. | 07 |
| Conveyor | Two yellow guide rails with the track between them | 07 |
| Welcome arch | Green columns, sky-blue top. The duck leans over the top in round sunglasses, holding a sponge. Left column: WELCOME BACK! and three instruction icons on orange and red (the bottom one reads HANDS OFF WHEEL). Right column: YOUR WASH with an arrow, then one panel per tier, each with a round light: Ceramic Duck (purple), Lucky Duck (green), and a yellow one, likely Good. | 08, 12 |
| Inside | "HONK IF YOU NEED ASSISTANCE" sign on a post. Green foam wrap brushes behind the arch. | 08 |

## Top five ideas

1. **DUCK! clearance bar.** Best pun on the lot, and it's free. Print it on the office printer, mount it on a foam-board strip, and hang it on two strings over the pay station. Hang it above head height. People will duck anyway. Keep the real text.
2. **Make the entrance an arch.** The real site puts the logo on a white panel over a rounded arch, then has a second arch inside with WELCOME BACK! and YOUR WASH. In a 12 ft lane, combine them. A PVC goalpost (two uprights, a crossbar, weighted feet) holds the 3 ft sign on top, with a foam-board column on each side. This also answers the README's open question on how the sign mounts.
3. **Light the tier on the arch.** Put a round light on each tier panel under YOUR WASH. When the attendant sells a wash, Home Assistant lights that tier, then flips it to Ceramic Duck with a sound for the free upgrade. To wire it, run a short piece of addressable LED strip off the ESP32 that runs the servos, and split it into three lights with ESPHome's `partition` light.
4. **Prep attendant.** The most recognizable person in the footage: ear muffs over a cap, black gloves, a tie under a black jacket, tall boots, and a yellow coiled air hose. We have the real tie and visor from Quick Quack, so put the ear muffs over the visor. Swap the spray gun for a toy bubble gun as the pre-soak. Same rule as the bubble machine: carpet or a mat underneath. Guide each judge onto the conveyor tape with hand signals: forward, a little left, stop. Clyde's shops probably have ear muffs, gloves, and a coiled hose to borrow. Good fit for Attendant 1, who runs the button and greets judges.
5. **QUACK for assistance.** Their sign says HONK IF YOU NEED ASSISTANCE. Ours says QUACK, with a squeeze duck or bike horn clipped to the post. Or a spare HA button that plays a quack on the speaker.

## Changes to the printed builds

- **Gate arm colors.** The real arm is white with three red bands, not even stripes. From the pivot out: red, white, white, red, white, white, red, white. That's 3 red and 5 white segments instead of 4 and 4. Or print all 8 white and wrap three bands of red tape.
- **White filament.** Going to 5 white segments adds about 50 g of white. All 8 white adds about 200 g. With the 2.4 mm jig, that may need a second white spool.
- **Gate pedestal.** The real one is a white box with a green cap. Print ours white, or paint it, and stand it on a white box with a green top edge. That puts the arm about waist height. Add a no-pedestrians sticker. At a walk-through car wash, that's the joke.
- **Gate speed.** Match the real lift, about 1.2 s. The ESPHome servo's `transition_length` is the time for a full sweep. Start near 2.7 s, which gives about 1.2 s for 80 degrees, then tune by eye. A slower lift is also easier on the M4 joints and safer near faces.
- **Brush.** The real wrap brushes are green foam. Cover the Sonotube in green only: green pool noodles, or green tablecloth strips hung from the top cap so they flare when it swings.
- **Sign.** The jig's white halo already matches the real sign's white panel. Mount it on the arch crossbar, facing the aisle.

## Smaller adds

- **Orange balls.** Line the lane with orange pumpkins. Brand orange, Halloween, and they keep people in the lane.
- **Upsell A-frame.** A Ceramic Duck poster on a foam-board A-frame before the pay station, between two yellow pool noodles standing in weighted bases.
- **Speed humps.** Black and yellow tape stripes across the lane before the pay station. Flat tape only.
- **Lane signs.** CASHIER and MEMBERS signs over our one lane. Both go to the same place.
- **Conveyor.** At the arch, two yellow tape lines with black tape between them.
- **Tablet menu.** Copy the kiosk: portrait, three stacked color bands, price in a white circle, duck at the bottom. Ceramic Duck is purple on both the kiosk and the arch. Purple isn't in `02-Brand-Reference.md` yet.
- **Instruction icons, office edition.** For the arch's left column: PUT IT IN NEUTRAL, SET TEAMS TO AWAY, HANDS OFF THE KEYBOARD.
- **PLEASE NOTE sign** after the gate: "We are not responsible for loose lanyards, AirPods, coffee, or dignity."
- **Duck mascot.** Round sunglasses and a big sponge, like the duck on the arch.

## Lane order

The real order is pay kiosk, gate, tunnel mouth, prep attendant, welcome arch, brushes. The brief has the sign first and the pay station second. Suggested order:

1. Pay station and gate, with the DUCK! bar overhead
2. Arch with the 3 ft sign on top. Prep attendant stands here.
3. Soft-touch curtain
4. Brush
5. Dryers
6. Exit

The line forms outside the tunnel like the real one, and the gate opens onto the arch.

## New buys (rough)

| Item | Est. cost |
|---|---|
| PVC goalpost for the arch (3/4" pipe and fittings) | $25 |
| 6 more foam boards for the arch columns | $8 |
| Toy bubble gun | $5 |
| Squeeze duck or bike horn | $5 |
| Orange pumpkins, 4-6 | $8 |
| Round sunglasses and a sponge | $3 |
| Red tape, only if the arm prints all white | $4 |
| Ear muffs, gloves, coiled hose, boots | $0, borrow |
| **Total** | **about $58** |

The clearance bar, lane signs, instruction icons, and PLEASE NOTE sign print on the office printer and use foam board already on the list.

## Stills

| # | File | Shows |
|---|---|---|
| 01 | `01_orange-balls.jpg` | Side canopy with orange balls |
| 02 | `02_pay-lanes.jpg` | Canopy signs, Ceramic Duck A-frame, speed humps |
| 03 | `03_pay-kiosk.jpg` | Kiosk screen and bollards |
| 04 | `04_gate-and-duck-bar.jpg` | Gate down, DUCK! bar, PLEASE NOTE sign |
| 05 | `05_gate-lifting.jpg` | Gate mid-lift |
| 06 | `06_tunnel-mouth.jpg` | Yellow front, logo panel, arch, orange balls |
| 07 | `07_prep-attendant.jpg` | Prep attendant and conveyor |
| 08 | `08_welcome-arch.jpg` | Welcome arch, HONK sign, brushes |
| 09 | `09_screenshot-gate-and-duck-bar.jpg` | Matt's phone screenshot of the gate stop, higher res |
| 10 | `10_duck-bar-closeup.jpg` | DUCK! bar close-up |
| 11 | `11_gate-closeup.jpg` | Gate arm and pedestal close-up |
| 12 | `12_welcome-arch-closeup.jpg` | Welcome arch close-up |
