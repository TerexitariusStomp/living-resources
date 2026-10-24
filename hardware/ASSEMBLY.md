# ASSEMBLY — EcoCell universal node, hand build

Time: ~1–2 h per unit. Tools: soldering iron, hookup wire, perfboard or
header strips, multimeter. Skill level: through-hole soldering only.

## 1. Board prep

1. Solder the supplied headers to the XIAO ESP32-S3 Sense (both rows).
2. Mount the Sense on a perfboard or screw-terminal shield — this is the
   carrier every head lands on. Route 3V3 and GND rails along one edge.
3. Insert the microSD card.

## 2. I2C bus (env + C4D)

Daisy-chain on the D4 (SDA) / D5 (SCL) lines in any order:

- **BME280**: VIN→3V3, GND→GND, SDA→D4, SCL→D5
- **BH1750**: same four
- **AD7746 (C4D)**: same four; its two electrode pads go to the C4D
  electrode pair (copper tape strips on the vessel exterior — nothing
  enters the culture)

## 3. Analog heads

- **Hydrophone**: piezo disc leads → preamp input; preamp OUT → D1,
  VCC→3V3, GND→GND. Potted separately (see ENCLOSURE) — the lead exits
  the enclosure through the gland.
- **Ultrasonic ICS-40730**: OUT → D2, VCC→3V3, GND→GND.

## 4. Emit lane (populated, consent-gated)

- D3 → 100 Ω resistor → MOSFET gate
- MOSFET source → GND; drain → transducer (−)
- Transducer (+) → 3V3
- Flyback diode across the transducer (any small signal diode)

The lane ships disabled (`LANES["emit"]["enabled"] = False`) — hardware
verified at bench test, activated only by joint consent via the edge.

## 5. PIR wake

AM312/HC-SR501: VCC→3V3, GND→GND, OUT→D0.

## 6. Backhaul (pick per site)

| Option | Wiring |
|---|---|
| WiFi only | nothing — onboard antenna |
| LoRa RNode | SX1276 UART breakout: TX→D7, RX→D6, GND, 3V3 |
| Satellite/LTE-M | modem UART same pins |
| Serial gateway (submerged pod) | D6/D7 to shore cable pair |

## 7. Firmware flash

```bash
# flash MicroPython for ESP32-S3 (see micropython.org/download — ESP32-S3 build)
esptool.py --chip esp32s3 --port /dev/ttyACM0 write_flash -z 0 firmware.bin
# then copy the node files via mpremote/ampy:
mpremote cp firmware/node/main.py :main.py
```

Edit `NODE_ID`, `WAKE_WINDOWS`, and `edge_host` for the site before
sealing the enclosure — OTA handles everything after.

## 8. Bench test (before enclosure)

1. `python3 firmware/node/main.py` on a desktop → `sim ok` lines
   (spool, flush, emit gate, task path).
2. On device via REPL: confirm `LANES` dict, I2C scan shows 0x76/0x23/0x48,
   PIR toggles D0 on motion.
3. Emit path continuity: drive D3 manually — transducer should tick
   (still consent-gated in software).
4. Reference tone: play 1 kHz at a fixed distance — log as the node's
   `mic_cal` SAID seed (goes into every receipt).

## 9. Field commissioning

1. Deploy per `ENCLOSURE.md` for the site form.
2. Deploy-time calibration: reference tone + note orientation/depth.
3. First uplink window → check edge receives detections
   (`tools/edge/rns_edge.py` or the UDP listener in
   `adapters/reticulum.scm`).
4. Register subject + guardian consent on the edge; the node starts
   earning receipts from its first quorum.
