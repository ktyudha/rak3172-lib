# LoRaWAN examples

| File | What it does |
|---|---|
| [otaa.py](otaa.py) | OTAA node: join, then send an uplink every 30 s |
| [raw.py](raw.py) | Old low-level example using the raw `RAK3172` class (kept for reference) |

## OTAA

1. Register the device on your network server (e.g. ChirpStack, TTN) and note its DevEUI, JoinEUI and AppKey.
2. Put them in `.env` (`make env` creates it from `.env.example`):
   ```
   LORAWAN_DEVEUI=0807060504030201
   LORAWAN_JOINEUI=0102030405060708
   LORAWAN_APPKEY=11111111111111111111111111111113
   ```
3. Run from the repo root: `python examples/lorawan/otaa.py`

For ABP, set `LORAWAN_DEVADDR`, `LORAWAN_NWKSKEY` and `LORAWAN_APPSKEY` instead and use
`LoRaWANNode.from_env()` (ABP is chosen automatically when `LORAWAN_DEVADDR` is set).

The same flow is available without writing code: `make otaa` / `make abp`.
