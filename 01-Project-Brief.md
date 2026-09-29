# Project Brief

## Goal

Win the office Halloween contest with a team costume plus a display people want to walk through. Keep it cheap, safe for an office, and easy to set up in under two hours.

## Event

| | |
|---|---|
| Event | Clyde Companies office Halloween contest, Lindon |
| Date | Fri Oct 30, 2026 (assumed. Oct 31 is a Saturday. Confirm.) |
| Time and judging | Unknown. Confirm criteria and whether display and costumes are judged together. |
| Space | Unknown. Plan for a 5 ft x 12 ft lane in a cubicle aisle. A conference room is the upgrade if we can get it. |
| Budget | $371 planned, $273 cheap version. Original target was $100-300. See `03-Materials-List.md`. |

## Concept

A mini Quick Quack tunnel. Judges "drive" through it on foot, in this order:

1. **Entrance.** The 3 ft printed Quick Quack sign hangs over the entrance, with an LED strip along the top.
2. **Pay station.** An attendant with a tablet greets them and sells them a wash. Once they "pay," the printed gate arm lifts.
3. **Soft-touch curtain.** Hanging tablecloth strips and pool noodles, our version of Flex Wrap cloth and foam. Bubbles and fog here.
4. **Brush.** The oscillating brush stands in the lane and swings side to side as they pass.
5. **Dryers.** Two box fans at the end of the lane. Blower sound on the speaker.
6. **Exit.** Free vacuum stall (a shop vac), towel rack, and the Duck Dunk towel hoop. The photo spot is here.

One button or PIR sensor (Home Assistant and ESPHome) starts the "wash cycle": gate, brush, lights, sound, bubbles, fog, fans.

Colors are the logo's: green, yellow, and orange, with white and black.

## Printed builds

Detail, file names, and assembly order are in `05-Build-Notes.md`. Printer is a Bambu P2S, one color per print.

| Build | Status |
|---|---|
| 3 ft sign (914 x 349 mm, multi-part, glued into a white jig) | Green parts and yellow duck body printed. White, orange, black, and the jig still to print. |
| Gate arm (printed pedestal, hub, 8 segments, servo, counterweight) | Designed, not printed |
| Oscillating brush (8" Sonotube on a printed servo turntable) | Designed, not printed. Needs the Sonotube and a lazy-susan bearing. |

## Team roles

Assumes four people. If we only have three, drop Attendant 2 and Matt covers the pay station.

| Role | Person | Costume | Job on the day |
|---|---|---|---|
| Lead / tunnel operator / Attendant 1 | Matt | Green or yellow polo, Quick Quack tie and visor (sent by Quick Quack), tablet, printed name badge | Runs the effects button, greets judges |
| Attendant 2 | [TBD] | Same as Attendant 1 | Pay station, pitches the membership tiers, cues the gate |
| Duck mascot | [TBD] | Yellow hoodie and sweats, felt wings, 3D-printed beak and feet. Optional Quackenstein version: green face paint and printed neck bolts. | Waves people in, hands out towels at the Duck Dunk |
| Soapy car | [TBD] | Cardboard box car on straps, covered in poly-fil "foam" | Rides through the tunnel on a loop. Photo prop. |

Quackenstein is listed as a Quick Quack Halloween character in one unverified source. Use it as a twist, not as a brand fact.

## Gags

- **Raincheck Policy sign.** Quick Quack gives a free rewash if it rains within 48 hours. Ours: "Raincheck Policy: free rewash if it rains within 48 hours. Does not cover the fire sprinklers."
- **"Don't Drive Dirty" banner** over the exit. It's their real tagline. Doubles as the photo backdrop.
- **Membership tiers, office edition.** Their tiers are Good, Lucky Duck, and Ceramic Duck. Good: one lap. Lucky Duck: one lap plus candy. Ceramic Duck: one lap, candy, and your name on the Unlimited Members board. Cancel anytime.
- **Adult frights signs.** Some Quick Quack locations run a haunted car wash with joke signs about adult frights like rent and student loans. Ours add office ones: month-end close, reply-all, "quick sync."

## What wins office contests

| Factor | How we cover it |
|---|---|
| Interaction | Judges walk through. Attendants sell them a wash. They shoot a towel at the Duck Dunk. |
| Moving parts | The gate lifts when they pay. The brush swings as they walk past. |
| Sound | Wash and blower sounds from a Bluetooth speaker, triggered with the effects |
| Lighting | LED strip over the entrance, color change when the wash starts |
| Craft | A 3 ft printed logo sign that looks like the real one |
| Photo moment | Exit under the "Don't Drive Dirty" banner with the duck and the soapy car |
| A bit for judges | See below |

## The judges' bit (about 60 seconds)

1. Attendant: "Welcome to Quick Quack. Which wash today?" Holds up the tablet menu.
2. Whatever they pick, it gets upgraded to Ceramic Duck for free.
3. Matt hits the button. The gate arm lifts. Lights change, wash sounds start, bubbles and fog.
4. Judge walks through the strips. The brush swings beside them. Soapy car rolls past. Fans at the end.
5. Duck hands them a towel. One shot at the Duck Dunk. Make it and they get candy. Miss and they get candy.
6. Attendant: "Don't drive dirty." Photo.

## Safety notes

- Fog in an office can set off smoke detectors. Get a yes from facilities or drop it.
- Bubbles make hard floors slippery. Run them over carpet or a mat only.
- Tape all cords down. Keep the lane clear for wheelchairs if the space allows.
- Keep the gate arm's swing and the brush's sweep clear of faces. Limit gate travel to 80 degrees.
- Cheap servos run warm. Trigger them per visitor, not on a loop all day.
