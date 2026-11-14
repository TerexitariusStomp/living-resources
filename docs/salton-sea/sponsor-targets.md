# Sponsorship targets — specific hardware likely to be covered in-kind

For the sponsor ask and component-vendor outreach. **Vendor names are
deliberately not listed here** — describe by part; attribution goes on
the dashboard as "component sponsor" with serials, same as device
tiers. Prices are 2026 spot estimates; verify at order time.

**In-kind odds column:** `high` = the part is a vendor's own flagship
device or radio module — dev units and production runs are realistic
asks; `medium` = commodity part a vendor may bundle; `low` =
general-purpose commodity, cash purchase expected.

## Per-node BOM (the $35–45 unit — every head on every board)

| # | Part | Function | ~$ | In-kind odds | Why |
|---|------|----------|---:|---|---|
| 1 | XIAO ESP32-S3 Sense | MCU + OV2640 camera + PDM mic + microSD — the whole core | 14 | **high** | Flagship dev board; volume credibility |
| 2 | microSD 16–32 GB | store-and-forward spool | 4 | low | Commodity; bundled into kit |
| 3 | BME280 module | temp/RH/pressure | 2 | medium | I2C env head |
| 4 | BH1750 module | ambient light | 1 | medium | I2C env head |
| 5 | PIR (HC-SR501/AM312) | wake-on-wildlife | 1 | low | Low-power trigger |
| 6 | E22-900T20D LoRa module | 915 MHz mesh radio (µReticulum) | 12–15 | **high** | **Highest-value sponsor target** — the radio IS the network |
| 7 | Piezo hydrophone + MAX9814 preamp | underwater acoustic head | 5–8 | low | The sea-node differentiator |
| 8 | ICS-40730 ultrasonic MEMS | 20–100 kHz head | 4–5 | low | Niche capability |
| 9 | AD7746 C4D eval + electrodes | capacitance/biofilm readout | 5 | low | Novel sensing lane |
| 10 | SPS30 PM sensor | PM2.5 dust events | ~40 | medium | **Second-highest value** — the Salton Sea's core metric |
| 11 | 40 kHz emit transducer + MOSFET | consent-gated bio-write | 3 | low | The read+write differentiator |
| 12 | Enclosure + solar + battery | deployment kit | 15–25 | low | Per-form (garden/shore/float/pod) |

**Node ask envelope:** ~$60–80/shore node, ~$100–150/water node all-in
(waterproofing, mooring, hydrophone cabling) — matches the one-pager tiers.

## Site-level hardware (one per deployment)

| Part | Function | ~$ | Notes |
|------|----------|---:|---|
| Starlink Mini kit | real-time satellite uplink | ~600 | Sponsor artifact — "the dashboard went live" |
| Phone/Pi edge device | classifier + ingest + onward uplink | 0–150 | Used phone acceptable; Pi Zero + CAT-1 HAT variant |
| CAT-1 modem (SIM7600-class) | DTC fallback path | 50–100 | No-dish option for remote sites — **medium** in-kind odds (dev-kit programs common) |
| Gateway node + weatherproof enclosure | mesh→internet bridge | ~80 | One per cluster — rides the node BOM |

## The pitch per component

Every sponsored part gets: serial-tracked attribution on the public
dashboard, open hardware docs (BOM/PINOUT/ASSEMBLY), deployment data,
and a named **restoration-monitoring station** credit where it lands
inside the Bombay Beach footprint. For a component vendor, a sponsored
run = their silicon inside a published, citable scientific deployment —
cheaper and more credible than a dev-kit giveaway.
