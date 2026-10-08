# CLAUDE.md

Guidance for working in this repository. Keep it current when conventions change.

## What this is

`rak3172` is a Python library for the RAK3172 / RAK3272S LoRa module (RUI3 AT firmware), for Raspberry Pi
and similar hosts. It provides LoRa P2P and LoRaWAN (OTAA/ABP), ready-made gateway/node roles, `.env`
configuration and a small CLI. Application logic (MQTT, ML, databases) does not belong here; it lives in
projects that depend on this package, e.g. `../machine-learning`.

## Commands

```
make install     # venv + editable install
make env         # .env from .env.example
make ports       # list serial ports
make init        # validate .env and configure the module (rak3172 init)
make run         # start the mode/role chosen in .env (rak3172 run)
make gateway | node | otaa | abp
```

There is no test runner. Check changes with `python3 -c "import rak3172"`, `python3 -m rak3172 --help`
and, when hardware is available, the scripts in `examples/`. Say so when something was not tested on a real module.

## Library layout

Dependencies point one way only: lower layers never import higher ones.

```
rak3172/
  core/        device.py     RAK3172 - serial + AT commands + RX thread. No addressing, no roles.
               errors.py     RAK3172Error
  protocols/   p2p.py        LoRaP2P - addressed frames [from][to][payload], retries, RX re-arm.
               lorawan.py    LoRaWAN - join state (OTAA/ABP), uplink, callbacks.
  payloads/    base.py       Payload - abstract contract: to_payload() / from_payload() (None if malformed).
  handlers/    base.py       Handler, PayloadHandler - classes that react to received frames; `reply()` to answer.
  roles/       p2p_gateway.py, p2p_node.py, lorawan_node.py - thin, ready-to-use wrappers.
  cli/         main.py       command line, built only on the public API.
               init.py       `init`: validate .env, apply to module, read back.
  config.py    .env / environment -> kwargs for the classes above.
  ports.py     serial port discovery.
```

Where new code goes: a new AT command or module feature -> `core/`; a new way of talking over the air
-> `protocols/`; a reusable handler or payload base -> `handlers/` / `payloads/`; a ready-made device type -> `roles/` (one file per role, exported in `roles/__init__.py`
and `rak3172/__init__.py`); a new command -> `cli/`.

Rules for library code:

- Public API is what `rak3172/__init__.py` exports. Keep it small.
- Raise `RAK3172Error` for failures. Never `exit()` or `sys.exit()` outside the CLI.
- User callbacks run on the serial RX thread. Wrap every call in `try/except` and log; one bad callback must not kill the listener.
- Anything that sends AT commands must not run on the RX thread (it would deadlock waiting for its own reply). Use a short-lived thread, as `_rearm_rx` and `_notify_reconnected` do.
- Use `logging` with `logger = logging.getLogger(__name__)`. No `print` in the library; the CLI and examples may print.
- Env var names stay compatible with the SmartNet ML project (`LORA_*`); new LoRaWAN ones use `LORAWAN_*`. Document additions in `.env.example` and the Readme table.

## Comments and docstrings

Comment the *why* in one or two short lines: a hardware quirk, a timing constraint, a non-obvious decision.
Do not narrate what the code does or which function it calls.

```python
# Good: this firmware stops receiving after one packet, so re-arm RX every time.
# Bad:  # call enable_p2p_rx to enable RX
```

- Public classes and functions get a one-line docstring saying what they are for. Add details only for non-obvious behavior (blocking, return meaning, threading).
- Example files start with a docstring: purpose, how to run, expected output. Not a tour of every function.
- No commented-out code, no TODOs without a reason.

## Style

- Python 3.8+, PEP 8, type hints on public signatures and DTOs.
- Names: `snake_case` functions, `CapWords` classes, `UPPER_CASE` constants. Callbacks are `on_<event>`.
- Payload/frame bytes are `bytes`; hex strings only at the AT-command boundary.
- Keep functions short. Prefer a small helper over a long comment.

## Building an application on this library

Object-oriented, one class per concern. The gateway/node script is only the entry point (`main`): it builds
the device and hands it a handler. It contains no parsing or business logic.

We do not use full DDD. We take one idea from Clean Architecture, the **dependency rule**: business logic
must not import `rak3172`, `serial`, `paho` or other I/O libraries. I/O code calls the logic, never the reverse.

```
my_app/
  sensor_gateway.py   entry point: P2PGateway.from_env(on_uplink=ReadingHandler()).run_forever()
  sensor_node.py      entry point: build the node, read the sensor, send
  sensor/
    payloads/         one Payload subclass per message type (the wire contract)
    handlers/         one Handler / PayloadHandler subclass per reaction: parse -> call a service -> reply
    services/         business logic (decisions, ML prediction, state). Plain Python, easy to test.
    adapters/         other I/O: MQTT publisher, database
```

| You want to... | Put it in |
|---|---|
| Start the gateway or node | the entry-point script (wiring only) |
| Define what a message looks like | `payloads/` |
| React to a received frame | `handlers/` |
| Decide something from the data | `services/` |
| Publish or store a result | `adapters/` |

A handler does three things: **decode** (done by `PayloadHandler`), **call** a service, **reply**. If a
handler grows logic, move it to `services/`. Pass dependencies in through the handler's `__init__`
(e.g. `ReadingHandler(service=..., publisher=...)`) instead of importing them, so each piece is replaceable.

### Payloads are the contract

A `Payload` subclass is the single definition of what travels over the air, shared by sender and receiver.

- One class per message type. Field names, order and format are the contract; changing them breaks every device in the field. Add a version or a new class instead of silently editing one.
- `from_payload` returns `None` for malformed input and never raises.
- Keep payloads small (airtime). Fixed-order `;`-separated text is fine; use a compact binary layout if size matters.
- Reference: `examples/p2p/sensor/payloads/sensor_reading.py` and `../machine-learning/src/lora/dto/sensor_reading.py`.
