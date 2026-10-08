"""Minimal P2P gateway: print every frame addressed to it and answer "ACK".

The smallest useful gateway, with no parsing. Start from this to see that two radios
can talk, then move on to sensor_gateway.py for real payload handling.

How to run (from the repo root, with .env configured, see ../README.md):
    python examples/p2p/minimal_gateway.py

What happens:
    1. P2PGateway.from_env() opens the serial port, switches the module to P2P mode,
       applies the radio settings from .env and starts listening.
    2. For each frame addressed to this gateway (LORA_ADDRESS) or broadcast (255),
       on_uplink() is called. Frames for other addresses are dropped by the library.
    3. send_to_node() transmits a reply to the node that sent the frame.
    4. run_forever() blocks until Ctrl-C, then closes the module cleanly.

Functions used:
    P2PGateway.from_env(on_uplink=...)   create the gateway from .env
    on_uplink(from_addr, payload, rssi, snr)
        from_addr  int    address of the sending node
        payload    bytes  raw message, decode it yourself
        rssi, snr  str    signal quality of this frame
    gateway.send_to_node(addr, data)     reply to one node (str or bytes), returns True/False
    gateway.broadcast(data)              send to every node
    gateway.run_forever()                keep the process alive
"""

from rak3172 import P2PGateway


def on_uplink(from_addr, payload, rssi, snr):
    print(f"from node {from_addr}: {payload!r} (rssi={rssi}, snr={snr})")
    gateway.send_to_node(from_addr, "ACK")


gateway = P2PGateway.from_env(on_uplink=on_uplink)
gateway.run_forever()
