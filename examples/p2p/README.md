# P2P examples

| File | Role |
|---|---|
| [sensor_gateway.py](sensor_gateway.py) | Gateway entry point (wiring only) |
| [sensor_node.py](sensor_node.py) | Node entry point: reads the sensor, sends a reading every 10 s |
| [sensor/payloads/](sensor/payloads/) | The message contract (`SensorReading`) |
| [sensor/handlers/](sensor/handlers/) | What to do on receive (`ReadingHandler` for the gateway, `CommandHandler` for the node) |
| [minimal_node.py](minimal_node.py), [minimal_gateway.py](minimal_gateway.py) | Smallest working pair (see below) |

For LoRaWAN see [../lorawan/](../lorawan/).

## Start here: minimal pair

Run these first to check that both radios hear each other.

- Node sends `hello` every 10 s.
- Gateway prints it and replies `ACK`.

```
python examples/p2p/minimal_gateway.py
python examples/p2p/minimal_node.py
```

Each file starts with a docstring that explains what it does, how to run it, and every function it uses.
Then continue with the sensor example below.

## P2P sensor example

Two Raspberry Pis (or one Pi and one Mac), each with a RAK3172 attached.

### 1. Configure `.env` on each device

Run `make env` in the repo root, then edit `.env`.

Gateway:
```
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_ADDRESS=1
```

Node:
```
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_ADDRESS=2
LORA_GATEWAY_ADDRESS=1
```

`LORA_FREQUENCY`, `LORA_SPREADING_FACTOR`, `LORA_BANDWIDTH`, `LORA_CODING_RATE`,
`LORA_PREAMBLE` must be identical on both, or they will not hear each other.

### 2. Run

Start the gateway first, then the node, each from the repo root:

```
python examples/p2p/sensor_gateway.py     # on the gateway
python examples/p2p/sensor_node.py        # on the node
```

Expected output:

```
# node
sent '27.4;63.2' -> ok
command from gateway 1: ACK (rssi=-48)

# gateway
node 2: temperature=27.4 C humidity=63.2 % (rssi=-47 snr=9)
```

### How it works

Three small classes, each in its own place:

```
sensor_node.py      -> SensorReading(...).to_payload()  --radio-->  ReadingHandler.on_payload()  <- sensor_gateway.py
                       (payloads/)                                   (handlers/)
```

**Payload** ([sensor/payloads/sensor_reading.py](sensor/payloads/sensor_reading.py)). One class defines the
message, both directions: `to_payload()` on the node, `from_payload()` on the gateway. The wire format is
`"27.4;63.2"`. `from_payload()` returns `None` for garbage instead of raising.

**Handler** ([sensor/handlers/reading_handler.py](sensor/handlers/reading_handler.py)). A class that reacts to
received frames. `PayloadHandler` decodes the frame into your payload class, logs and drops malformed ones,
and calls your `on_payload(from_addr, message, rssi, snr)`. Use `self.reply(addr, data)` to answer.

```python
class ReadingHandler(PayloadHandler):
    payload_type = SensorReading

    def on_payload(self, from_addr, message, rssi, snr):
        print(message.temperature, message.humidity)
        self.reply(from_addr, "ACK")
```

**Entry point** ([sensor_gateway.py](sensor_gateway.py)). Only wiring: build the gateway, give it the handler, run.

```python
P2PGateway.from_env(on_uplink=ReadingHandler()).run_forever()
```

The node does the same with `P2PNode.from_env(on_command=CommandHandler())` and sends with
`node.send_to_gateway(reading.to_payload())`, which retries up to 3 times and returns `True`/`False`.

**Real sensor.** Replace `read_sensor()` in [sensor_node.py](sensor_node.py). For a DHT22 on a Raspberry Pi:
`pip install adafruit-circuitpython-dht`, then `SensorReading(dht.temperature, dht.humidity)`.

**Adding a field.** Add it to `SensorReading` (both `to_payload` and `from_payload`); the handlers see it automatically.
Existing devices in the field must be updated together, since the wire format changed. Keep payloads small (less airtime).

**Several nodes.** Give each its own `LORA_ADDRESS`; `from_addr` tells the handler which one sent it.

### Notes

- Callbacks run on the serial RX thread. Keep them quick; hand heavy work (database, MQTT) to another thread or queue.
- An exception inside a callback is logged and ignored; it does not stop the listener.
- Run the scripts as `python examples/p2p/<file>.py` so the `sensor` package next to them is found.
