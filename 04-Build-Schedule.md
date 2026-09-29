# Build Schedule

Runs from Tue Sept 22 to the contest on Fri Oct 30 (assumed, confirm). Owner tags: **[Matt]**, **[Duck]**, **[Att2]**, **[Car]**, **[All]**. Swap in names once the team is set.

One printer, one color at a time, ~245 mm usable width. Print order follows the sign's assembly order, then gate, then brush. Costume prints go in whichever color batch is loaded.

## Milestones

| Date | Milestone |
|---|---|
| Fri Sept 25 | Jig thickness decided. Filament, bearing, hardware, and power supply ordered. |
| Sun Sept 27 | Servos in hand (due Sept 23-27) |
| Mon Sept 28 | Concept locked, team and roles set |
| Fri Oct 2 | White and orange printed. One servo moving from ESPHome. |
| Fri Oct 9 | Sign dry-fit complete. Banner ordered. |
| Thu Oct 15 | Costume fitting |
| Fri Oct 16 | Sign glued up. All gate and brush parts printed. |
| Fri Oct 23 | Gate arm and brush running from Home Assistant |
| Tue Oct 27 | Dry run |
| Fri Oct 30 | Setup and contest |

## Week 1: Sept 22-26. Decide, measure, order

- [ ] Decide jig thickness: 1.8 mm as built or 2.4 mm. If 2.4, regenerate `qq_sign_jig.zip`. **[Matt]**
- [ ] Buy the Sonotube. Measure its inside diameter (turntable assumes 203.2 mm). **[Matt]**
- [ ] When the servos land, measure the horn disc (recess assumes 21 mm; kits often ship 25 mm). Adjust files if needed. **[Matt]**
- [ ] Order white, black, and red filament, lazy-susan bearing, 6 V 5 A supply. Home Depot for backer, glue, M8 and M4 hardware, screws. **[Matt]**
- [ ] Copy the zips into `3d/` and the SVG and images into `assets/` **[Matt]**
- [ ] Confirm contest date, time, and judging criteria with the organizer **[Matt]**
- [ ] Ask what space we can use, and ask facilities about fog **[Matt]**
- [ ] Recruit the team. Assign duck, attendant 2, and car. **[Matt]**
- [ ] Sat Sept 26: reference visit to Quick Quack Orem, 1588 N State St. Photos of signs, pay station, uniforms, Duck Dunk. **[Matt]**

## Week 2: Sept 28-Oct 2. White and orange

- [ ] Mon: concept locked. Update the brief with any changes. **[Matt]**
- [ ] Print the 8 white jig tiles **[Matt]**
- [ ] Print the 7 white inlay letters, lens backing, and glints **[Matt]**
- [ ] Swap to orange. Print sign beak and feet, then costume beak and feet. **[Matt]**
- [ ] Bench-test one servo on the ESP32 with ESPHome and the 6 V supply **[Matt]**
- [ ] Check what we already own: polos, tablets, box fans, shop vac, LED strip, smart plugs, ESP32 **[All]**
- [x] Ties and visors: sent by Quick Quack **[Matt]**
- [ ] Thrift run for yellow hoodie and sweats **[Duck]**

## Week 3: Oct 5-9. Black, dry-fit, gate base

- [ ] Print the 2 black stepped tiles and the neck bolts **[Matt]**
- [ ] Dry-fit the whole sign on the jig. Fix any tight fits before gluing. **[Matt]**
- [ ] Print gate arm pedestal and hub **[Matt]**
- [ ] Yellow batch if the queue allows: Duck Dunk hoop, badges **[Matt]**
- [ ] Design the banner. Order by Fri Oct 9. **[Matt]**
- [ ] Measure the space. Sketch the lane layout and the sign mount. **[Matt]**
- [ ] Get a big cardboard box for the car **[Car]**

## Week 4: Oct 12-16. Glue up, arm, brush base

- [ ] Glue up the sign in assembly order: jig on backer, green tiles, white letters and counters, Quick Quack letters and stripes, yellow body, orange, black, glints **[Matt]**
- [ ] Print 8 arm segments (4 red, 4 white) and the end segment, lying flat **[Matt]**
- [ ] Print brush base plate and turntable **[Matt]**
- [ ] Walmart/Dollar Tree run: felt, tablecloths, pool noodles, foam boards, bubble machine, straps, poly-fil **[Att2]**
- [ ] Build the car body. Paint it and add the poly-fil foam. **[Car]**
- [ ] Make the wings and tail **[Duck]**
- [ ] Thu Oct 15: costume fitting. Adjust the beak, feet, and car straps. **[All]**

## Week 5: Oct 19-23. Assemble, tune, rehearse

- [ ] Assemble the gate arm with the counterweight. Tune travel to 0-80 degrees so the tail clears the flange. **[Matt]**
- [ ] Mount the brush on the Sonotube. Run the oscillate loop (+/-50 degrees every 2 s). **[Matt]**
- [ ] Build the HA wash-cycle script: gate, brush, LEDs, sound, smart plugs **[Matt]**
- [ ] Cut tablecloths into curtain strips **[Att2]**
- [ ] Write and print signs: wash menu, office tiers, Raincheck Policy, adult frights, Free Vacuums. Mount on foam board. **[Att2]**
- [ ] Test bubbles and fog with the fans **[Matt]**
- [ ] Rehearse the judges' bit once at lunch **[All]**
- [ ] Buy candy and Command strips **[Att2]**

## Week 6: Oct 26-30. Dry run and contest

- [ ] Tue Oct 27: dry run. Full setup at home or in the office after hours. Time the setup. **[All]**
- [ ] Fix whatever broke in the dry run **[Matt]**
- [ ] Thu Oct 29: pack the car. Sign flat on top. Charge the tablets and speaker. **[Matt]**
- [ ] Fri Oct 30: setup and contest (run-of-show below) **[All]**

## Setup day run-of-show

Judging time is unknown. Times are counted back from judging (J).

| Time | Task | Owner |
|---|---|---|
| J-2:30 | Arrive. Unload the car. Sign comes in last, carried flat. | Matt |
| J-2:15 | Tape the lane. Mount the sign over the entrance. | Matt, Att2 |
| J-2:00 | Place the gate arm at the pay station and the brush in the lane | Matt |
| J-1:45 | Hang the curtain strips and pool noodles | Att2 |
| J-1:30 | LED strip, fans, bubble and fog machines | Matt |
| J-1:20 | Wire and power check: 6 V supply on, shared ground, ESP32 online in HA, gate and brush move. Tape down all cords. | Matt |
| J-1:10 | Pay station, signs, banner, Duck Dunk, shop vac | Att2, Car |
| J-1:00 | Run the wash cycle twice. Fix problems. | Matt |
| J-0:45 | Costumes on | All |
| J-0:15 | Places. Bubble solution and fog fluid topped off. | All |
| J | Judges' bit, about 60 seconds per group | All |
| After | Free runs for anyone who walks by. Rest the servos between runs. | All |

## Teardown

About 30 minutes. Unplug everything first. The sign is fragile: take it down first and carry it flat. Unbolt the gate arm at the M4 joints. Lift the Sonotube off the turntable. Pull the floor tape, and wipe up any bubble residue on hard floors. Keep the sign, printed parts, servos, and LEDs in one tote for next year. Everything goes home that night.
