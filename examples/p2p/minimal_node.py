"""Minimal P2P node: send a text message to the gateway every 10 s and print its replies.

The smallest useful node, with no sensor. Start from this to see that two radios can
talk, then move on to sensor_node.py for real data.

How to run (from the repo root, with .env configured, see ../README.md):
    python examples/p2p/minimal_node.py

What happens:
    1. P2PNode.from_env() opens the serial port, switches the module to P2P mode and
       starts listening for replies. LORA_ADDRESS is this node's address and
       LORA_GATEWAY_ADDRESS is where messages go.
    2. send_to_gateway() adds the [from][to] address header, transmits, and retries up
       to 3 times. It returns True when the radio accepted the frame. That means it was
       transmitted, not that the gateway received it; wait for the gateway's reply
       (on_command) if you need to know.
    3. When the gateway replies, on_command() is called.
    4. Ctrl-C stops the loop and closes the module cleanly.

Functions used:
    P2PNode.from_env(on_command=...)   create the node from .env
    on_command(from_addr, payload, rssi, snr)
        from_addr  int    address of the sender (the gateway)
        payload    bytes  raw message, decode it yourself
        rssi, snr  str    signal quality of this frame
    node.send_to_gateway(data)         send str or bytes to the gateway, returns True/False
    node.send(addr, data)              send to any other address instead
    node.close()                       stop listening and release the serial port
"""

import time

from rak3172 import P2PNode


def on_command(from_addr, payload, rssi, snr):
    print(f"reply from {from_addr}: {payload!r} (rssi={rssi}, snr={snr})")


node = P2PNode.from_env(on_command=on_command)

try:
    while True:
        ok = node.send_to_gateway("hello")
        print(f"sent 'hello' -> {'ok' if ok else 'FAILED'}")
        time.sleep(10)
except KeyboardInterrupt:
    node.close()
