# Electronics: gate and brush servos

Working as of Oct 10, 2026. Updated Oct 25, 2026: the brush starts reliably, there's a new control page, the gate closes slowly, the servos start at their rest positions on power-up, and the hotspot serves the controls instead of a WiFi setup form.

## Hardware
- ESP32-WROOM-32 38-pin DevKit (CP2102, USB-C) on a screw-terminal breakout. USB port goes at the end labeled 5V / CLK.
- Servos: Deao 25 kg digital, **270°** (not 180°), 4.8–7.4 V. At 5 V it covers about 100° in 0.3 s.
- Servo power: BTF-Lighting 5 V 6 A brick through a barrel-to-screw-terminal adapter. The 6 V supply on the materials list isn't needed.

## Wiring
| Wire | From | To |
|---|---|---|
| Gate servo signal (orange) | servo | P18 |
| Brush servo signal (orange) | servo | P19 |
| Servo + (red) | servo | adapter + |
| Servo ground (brown) | servo | ESP32 GND (top row) |
| Ground link | ESP32 GND (top-left) | adapter − |
| Wash button | P13 | GND next to it (bottom row) |

Never connect servo power to the ESP32's 5V or 3V3 pins. All grounds must be tied together.

## Firmware
- Files in `Documents/Quick Quack/esphome/`:
  - `qq-tunnel.yaml`: the ESPHome config
  - `qq-ui.js`: the custom control page, built into the firmware. Keep it next to the config.
  - `secrets.yaml`: home WiFi, which gets built into the firmware
- Old versions kept there: `qq-tunnel.before-2026-10-25.yaml` (the Oct 10 config) and `bigbuttons.js` (no longer used, safe to delete).
- **How to update (since Oct 25):** build and send from the Mac mini with ESPHome 2026.10 in `~/esphome-qq`, while the board is on home WiFi. Copy both `qq-tunnel.yaml` and `qq-ui.js` there from the Quick Quack folder first, then run `.venv/bin/esphome run qq-tunnel.yaml --device qq-tunnel.local`.
- The ESPHome Device Builder add-on on Home Assistant still holds the **old** config. Don't install from it, or it will put the old firmware back.
- First flash was done with web.esphome.io. This board doesn't enter flash mode on its own: hold **IO0** while clicking Connect, then let go once it says Connected.
- Lesson learned: WiFi entered through the board's setup page is wiped by a firmware update. Keep it in `secrets.yaml`.

### Config gotchas (don't undo these)
- **No `captive_portal`.** When the board runs its own QQ Tunnel hotspot, the captive portal answers every page request with a WiFi setup form. With it in the config, 192.168.4.1 never showed the controls. That's true of the Oct 10 config too; it just never came up at home.
- **No `local: true` under `web_server`.** It serves ESPHome's own page bundle, which never loads `qq-ui.js`.
- **`js_url: ""`** keeps the page from waiting on the internet. ESPHome's built-in page (the link at the bottom of the control page) loads from the internet only when you tap the link, so it works at home but not on the hotspot.

### How it behaves
- **Gate speed:**
  - It opens 80° in 1.5 s and closes in Gate Close Time, 4 s by default (settable from 2 to 10 s).
  - Pressing Open while it's closing sends it back up from wherever it is.
  - The servo's speed setting covers its full 270°, so the code scales it for the 80° gate move. The Oct 10 version moved 80° in about 0.4 s both ways.
- **Power-up:** the board drives the gate down and the brush to center right away, at full servo speed. Power up with the gate down and nobody near it.
  - Why: ESPHome can't tell where a servo is at power-up, so it assumes the middle (135°). Without this step, the first gate command after power-up swung the arm out to 135° first.
- **Brush:** it swings from a 50 ms timer that only reads the on/off switch, so it starts every time. The Oct 10 version sometimes never started. Turning it off returns it to center.
- **Stop:** ends the wash and turns the brush off. It doesn't move the gate.
- **Wash cycle** (button or Start Wash): gate up, brush runs for Wash Length, brush stops, gate closes slowly. Presses during a cycle are ignored. A "Wash Remaining" reading drives the countdown on the page.

## Running it
- At home: http://qq-tunnel.local
- At the event: about a minute after power-up with no home WiFi, it creates WiFi **QQ Tunnel** (password: ask Matt). Join it, then open **http://192.168.4.1** in Safari. No Home Assistant, office WiFi, or internet needed; the page is built into the firmware.
  - If the phone pops up a WiFi sign-in sheet when joining, close it and use Safari.
  - The hotspot mode hasn't been tested yet. Test it away from home WiFi before the event.
- **Control page,** top to bottom:
  - **Header:** the Quick Quack logo and a Connected/Offline indicator.
  - **Status card:** Ready, or a yellow Washing card with a countdown and progress bar. If the phone can't reach the board, it shows "Can't reach the tunnel" and greys out the controls.
  - **Start Wash** (green) and **Stop** (red).
  - **Gate:** Open and Close, with the current position highlighted. It shows "Closing…" while the gate comes down.
  - **Brush:** an on/off switch.
  - **Settings** (folded): wash length, swing speed, swing width, and gate closing time.
  - **Horn setup** (folded): gate angle, brush position, and a Center button. These move the servos right away.
  - A link at the bottom opens ESPHome's built-in page (home only).
- Big brush sweeps can't go faster than the servo: 270° takes at least ~0.8 s.
- All settings are remembered after a restart.

## Setting horns
- Gate: open Horn setup, set Gate angle to 0, then fit the horn and hub with the arm level.
- Brush: open Horn setup, press Center (135°), then fit the horn.

## Still to do
- **Test hotspot mode before the event:** power the board somewhere it can't see home WiFi, wait about a minute, join QQ Tunnel, and open 192.168.4.1.
- Pick final brush swing angle and speed once the Sonotube is on (lighter on the servo: smaller sweep, slower swing).
- Try the gate closing time with the real arm, and slow it down if it still feels quick.
- Wire the second servo so gate (P18) and brush (P19) both run.
- Get a push button for P13 (or touch the two wires together to test).
- At the event, power the ESP32 from a USB wall charger, or from the 5 V brick through the board's 5V/GND terminals (not both at once).
