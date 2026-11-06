# Zehnder EVO Connect ModBus for Home Assistant

Custom Home Assistant integration for the **Zehnder EVO Connect ModBus** bridge,
connecting **Zehnder EVO heat-recovery ventilation units (EVO 2 / EVO 3 /
EVO 4)** over **Modbus RTU on RS485**. The register map is identical for all
EVO generations, so one integration works with any EVO unit.

Works with:

- a **USB RS485 adapter** connected directly to the Home Assistant host, or
- a **WiFi / Ethernet RS485 gateway** (RTU over TCP, e.g. Elfin EW11, USR-W630,
  Waveshare RS485-TO-WiFi).

Everything is local — no cloud, no Zehnder account.

## Features

| Platform | Entities |
|---|---|
| **Fan** | Ventilation: Off / Away / Low / Medium / High / Auto / Boost (register 41500) |
| **Sensors** | Extract, outdoor, discharge and supply air temperature; supply and extract airflow (m³/h); indoor/outdoor humidity; CO₂; air quality; bypass position; preheater/afterheater power; filter days remaining / interval / usage; current fan speed; temporary speed-disable countdown |
| **Binary sensors** | Dirty filter, defrosting, fan fault, RF communication lost |
| **Numbers** | Temporary speed-disable timers (41501–41503); standby and speed 1–3 airflow % (42001–42008); frost-protection, preheater and afterheater setpoints (42009–42016) |
| **Buttons** | Reset filter timer (42000) |

Sensor values that the unit reports as "not available" or "sensor error"
(the documented special values `EFh`, `7FFFh`, `7FFh`, NaN, < −273 °C) are shown
as *unknown* instead of garbage.

## Installation

### Marketplace (Home Assistant 2026.11+)

1. **Settings → Marketplace** → ⋮ → *Custom repositories*
2. Add `https://gitlab.com/larryare/zehnder_evo_modbus` with category *Integration*
3. Install "Zehnder EVO Connect ModBus" — the setup dialog opens right away, no restart needed

> Requires the repository to be public (or accessible with a token).

### HACS (Home Assistant 2026.10 and older)

1. HACS → Integrations → ⋮ → *Custom repositories*
2. Add `https://gitlab.com/larryare/zehnder_evo_modbus` with category *Integration*
3. Install "Zehnder EVO Connect ModBus", restart Home Assistant

### Manual

Copy `custom_components/zehnder_evo_modbus/` into your Home Assistant
`config/custom_components/` directory and restart.

## Wiring

```
USB-RS485 adapter          EVO Connect ModBus terminals
A  ───────────────────────── A
B  ───────────────────────── B
GND (optional) ───────────── G
```

The bridge is powered through its **USB-Micro port from any 5 V USB charger**
(official range is 5–24 V AC/DC, max 2 W). If your installation already provides
24 V AC/DC you can power it from the screw terminals (P/G) instead.

If you use a WiFi gateway, set it to **transparent RTU-over-TCP server mode**
(not "Modbus TCP" mode) and match its serial side to the bridge settings
(defaults in the config flow: 9600 baud, 8 data bits, no parity, 1 stop bit).

## One-time RF binding (bridge ↔ EVO unit)

The bridge talks to the ventilation unit wirelessly (868 MHz). If your bridge
has never been paired with the unit, do this **once** from a Windows PC using
the vendor's `ModbusTester` tool and a USB-RS485 adapter (or a virtual COM port
tunnelled to your WiFi adapter):

1. Wire the adapter A→A, B→B to the bridge and power the bridge from a 5 V charger.
2. **Power-cycle the EVO unit** (unplug from mains, wait 1 minute, plug back in)
   — it now listens for a new RF companion for **10 minutes**.
3. In ModbusTester, select your COM port and open the Modbus tab.
4. Enter RAW hex **`0001C892`** and press **SET**.
5. Enter the Modbus slave address in *Slave UID to bind to* (usually `1`).
6. Set *Initiate binding type* = **3 – Outgoing Product Type** and press **Bind**.
7. Press *Refresh current tabpage* — the EVO device card appears and values start
   syncing. Verify with the Debug tab: write `41500 = 3`, the unit should switch
   to speed 2.

If the card doesn't appear after *Bind*, repeat from step 2 (the 10-minute
window may have expired).

## Configuration

After restart: **Settings → Devices & Services → Add Integration → Zehnder EVO
Connect ModBus**.

- *Serial*: port, baud rate, parity, stop bits, data bits, **slave address
  (usually `1`)**
- *Network*: host, port (default 502), framing (RTU over TCP or Modbus TCP),
  slave address

Options (after setup): update interval (default 10 s), filter-register poll
interval (default 1 h — reading register 41040 triggers a slow RF query in the
unit, so it is deliberately polled rarely), and the float word order.

### If temperatures look wrong

The float word order is not documented by Zehnder. The integration defaults to
big-endian (`A B C D`). If your temperature/airflow sensors show nonsense
values, switch *Float word order* to *little endian word swap* in the options.

## Register reference

Register numbers in PLC convention (4xxxx); protocol address = 4xxxx − 40001.

| Register | R/W | Name | Unit | Type | Notes |
|---|---|---|---|---|---|
| 40101 | R | RF communication status | | UINT16 | 1 = no communication for ≥ 30 min |
| 40102 | R | Battery status | | UINT16 | FFFFh = no battery |
| 40103 | R | Fault status | | UINT8 | 1 = fan fault |
| 41000 | R | Current fan speed | | UINT8 | 0 off, 1–3 speeds, 11–13 timer disabled, 21 away, 23 boost, 24 auto |
| 41003 | R | Error code | | UINT8 | 0–8 errors, 254 connection mode, 255 identification |
| 41004 | R | Temporary speed-disable countdown | min | UINT6 | valid while speed is 11–13 |
| 41005–06 | R | Extraction temperature | °C | FLOAT | NaN / < −273 °C = unknown |
| 41007–08 | R | Outdoor temperature | °C | FLOAT | |
| 41009–10 | R | Air discharge temperature | °C | FLOAT | |
| 41011–12 | R | Supply (flow) temperature | °C | FLOAT | |
| 41013 | R | Preheater | % | UINT8 | EFh = n/a |
| 41014 | R | Dirty filter | | UINT8 | 1 = dirty |
| 41015 | R | Defrosting | | UINT8 | 1 = active |
| 41016 | R | Bypass position | % | UINT8 | > 120 % = fault |
| 41017 | R | Indoor humidity | % | UINT8 | EFh–FFh = n/a/error |
| 41018 | R | Outdoor humidity | % | UINT8 | |
| 41019–20 | R | Supply airflow | m³/h | FLOAT | 7FFFh = n/a, 8000h–85FFh = error |
| 41021–22 | R | Extract airflow | m³/h | FLOAT | |
| 41023 | R | Air quality | % | UINT8 | 0 = poor, 100 = excellent |
| 41024 | R | Air quality basis | | UINT8 | bit0 VOC, bit1 CO₂, bit2 RH |
| 41025 | R | CO₂ level | ppm | UINT16 | 7FFh = n/a, ≥ 8000h = error |
| 41026 | R | Afterheater | % | UINT8 | EFh = n/a |
| 41027 | R | Capability bits | | UINT16 | bit0 preheater, bit1 afterheater available |
| 41040 | R | Filter time remaining | days | UINT16 | read triggers a slow RF query |
| 41041 | R | Filter service interval | days | UINT16 | |
| 41042 | R | Filter usage | % | UINT8 | |
| 41500 | R/W | Required ventilation speed | | UINT8 | 0 off, 1 away, 2–4 speeds, 5 auto, 7 boost |
| 41501–03 | W | Disable speed 1/2/3 for | min | UINT6 | max 1080 min (18 h) |
| 42000 | W | Filter timer reset | | UINT8 | write 0 to reset |
| 42001–02 | R/W | Standby speed supply/extract | % | UINT8 | 0–40 (labels 61/62) |
| 42003–04 | R/W | Speed 1 supply/extract | % | UINT8 | 0–80 (labels 63/64) |
| 42005–06 | R/W | Speed 2 supply/extract | % | UINT8 | 0–100 / 10–100 (labels 65/66) |
| 42007–08 | R/W | Speed 3 supply/extract | % | UINT8 | 0–100 / 10–100 (labels 67/68) |
| 42009–10 | R/W | Frost protection setpoint | °C | FLOAT | −20…50 (label 39) |
| 42011–12 | R/W | Preheater setpoint | °C | FLOAT | −20…50 (label 46) |
| 42013–14 | R/W | Afterheater setpoint | °C | FLOAT | 0…30 (label 117) |
| 42015–16 | R/W | Afterheater differential | K | FLOAT | 1…10 (label 132) |

Source: *Zehnder EVO Connect ModBus – Installer and user manual* (V0625),
cross-checked against the vendor commissioning guide.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

## License

MIT
