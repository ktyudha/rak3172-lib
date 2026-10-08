# rak3172

Python library to use a **RAK3172 / RAK3272S** LoRa module from a Raspberry Pi (or any computer).
You can send and receive messages between devices in a few lines, with no AT commands to learn.

It supports:

- **LoRa P2P**: a *node* sends data straight to a *gateway* (and the gateway can reply).
- **LoRaWAN**: join a network with OTAA or ABP and send uplinks.

## Get started

No code needed to try it: you only edit `.env`.

**1. Install**

```
git clone <this repo> && cd rak3172-lib
make install
```

On a Raspberry Pi, allow your user to use the serial port once, then log in again:
`sudo usermod -aG dialout $USER`

**2. Configure `.env`**

```
make env       # creates .env from .env.example
make ports     # shows your module's port, e.g. /dev/ttyUSB0
```

Edit `.env` (see [What goes in .env](#what-goes-in-env)). The important lines:

```
LORA_MODE=p2p            # p2p or lorawan
LORA_ROLE=gateway        # p2p only: gateway or node
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_ADDRESS=1
```

**3. Initialize the module (once per device)**

```
make init
```

This checks your `.env` for mistakes, switches the module to the chosen mode, writes the radio
settings (or LoRaWAN keys) into it, and reads them back so you can see they were applied.
Run it again whenever you change `.env`.

**4. Run**

```
make run
```

A gateway prints what it receives. A node sends a test message every 10 s
(To change the message or interval, call the CLI directly: `.venv/bin/rak3172 run --message hello --interval 5`).

## Use it in your own code

Keep three things separate: the **payload** (what a message looks like), the **handler** (what to do when
one arrives) and the **entry point** (which only wires them together).

```python
from rak3172 import P2PGateway, PayloadHandler

class ReadingHandler(PayloadHandler):           # handler
    payload_type = SensorReading                # payload: your Payload subclass

    def on_payload(self, from_addr, message, rssi, snr):
        print(from_addr, message.temperature)
        self.reply(from_addr, "ACK")

P2PGateway.from_env(on_uplink=ReadingHandler()).run_forever()   # entry point
```

Node side:

```python
node = P2PNode.from_env()
node.send_to_gateway(SensorReading(25.1, 60.0).to_payload())    # returns True/False
```

`from_env()` reads your `.env`, so the code is the same on every device. For plain functions instead of
classes, pass `on_uplink=my_function(from_addr, payload, rssi, snr)`.

Full working example with a temperature/humidity sensor: [examples/p2p/](examples/p2p/).
LoRaWAN: [examples/lorawan/](examples/lorawan/).

## What goes in .env

| Variable | Meaning | Default |
|---|---|---|
| `LORA_MODE` | `p2p` or `lorawan` | p2p |
| `LORA_ROLE` | P2P only: `gateway` or `node` | gateway |
| `LORA_SERIAL_PORT` | Serial port of the module | auto-detect |
| `LORA_ADDRESS` | This device's P2P address (1-254) | 1 |
| `LORA_GATEWAY_ADDRESS` | Gateway address (used by nodes) | 1 |
| `LORA_FREQUENCY` | Frequency in Hz | 915000000 |
| `LORA_SPREADING_FACTOR`, `LORA_BANDWIDTH`, `LORA_CODING_RATE`, `LORA_PREAMBLE`, `LORA_TX_POWER` | Radio settings | 7, 0, 0, 8, 22 |
| `LORA_VERBOSE` | Print all serial traffic (`true`/`false`) | false |
| `LORAWAN_DEVEUI`, `LORAWAN_JOINEUI`, `LORAWAN_APPKEY` | OTAA keys | none |
| `LORAWAN_DEVADDR`, `LORAWAN_NWKSKEY`, `LORAWAN_APPSKEY` | ABP keys (used instead of OTAA when `LORAWAN_DEVADDR` is set) | none |
| `LORAWAN_FPORT` | LoRaWAN port for uplinks | 2 |

Gateway and nodes must use the **same radio settings**, otherwise they cannot hear each other.
Variable names match the SmartNet ML project, so the same `.env` works for both.

## Commands

| Command | What it does |
|---|---|
| `make ports` | List serial ports |
| `make init` | Validate `.env` and configure the module with it |
| `make run` | Start whatever `.env` says (mode and role) |
| `make gateway` | Force a P2P gateway, ignoring `LORA_ROLE` |
| `make node MESSAGE=hello INTERVAL=10` | Run a P2P node that sends a message every 10 s |
| `make otaa` / `make abp` | Run a LoRaWAN node (keys from `.env`) |

The same commands exist without `make`: `rak3172 ports|init|run|gateway|node|otaa|abp`.
Flags override `.env`, e.g. `rak3172 node --address 3 --message hi` (see `rak3172 <command> --help`).

## Troubleshooting

| Problem | Try |
|---|---|
| `make init` lists problems | Fix the lines it prints in `.env`, then run it again. |
| `Unable to open serial port` | Run `make ports`, set `LORA_SERIAL_PORT`. On Raspberry Pi, check the `dialout` group step above. |
| `Unable to detect RAK3172` | Wrong port, or the module is not in AT mode. Check wiring/USB and try `LORA_VERBOSE=true`. |
| Gateway receives nothing | Radio settings differ between devices, or the gateway/node addresses don't match `LORA_ADDRESS` / `LORA_GATEWAY_ADDRESS`. |
| LoRaWAN join times out | Check the keys, that the device is registered on the network server, and gateway coverage. |

## Reference

| Role | Class | Main functions |
|---|---|---|
| P2P gateway | `P2PGateway` | `on_uplink` (function or `Handler`), `send_to_node(addr, data)`, `broadcast(data)` |
| P2P node | `P2PNode` | `send_to_gateway(data)`, `on_command` (function or `Handler`) |
| LoRaWAN node | `LoRaWANNode` | `connect(timeout)`, `send_uplink(data)` |

Lower-level building blocks: `LoRaP2P` (addressed frames `[from][to][payload]`, retries), `LoRaWAN`
(join state, `on_join` / `on_confirm` / `on_receive`) and `RAK3172` (raw AT driver: `send_command`,
`configure_p2p`, `join`, ...). They accept `encoders` / `decoders` (`bytes -> bytes`) as a hook for
encryption or signing, and recover automatically if the module reboots or the USB link drops.
Errors raise `RAK3172Error`. Default baud rate is 115200 (`baudrate=` to override).

### Using it in the SmartNet ML gateway

Replace the vendored `rak3172-at-lib` copy with this package and use `from rak3172 import LoRaP2P`
(same constructor and callbacks). MQTT and ML logic stay in that project.

---

Originally a fork of Oliv4945's quick AT library.
