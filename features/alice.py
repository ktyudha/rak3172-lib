"""Alice (node): pings Bob, waits for his pong (which carries Bob's RSSI), measures its own RSSI, repeats.

    LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py

Expected output: "[alice] pong #N: rssi_at_bob=... rssi_at_alice=..." once per round.
"""

import time

from rak3172 import P2PNode
from research.handlers import AliceHandler
from research.payloads import Probe

ROUND_DELAY = 0.1  # seconds between a pong and the next ping
PONG_TIMEOUT = 5.0 # seconds

handler = AliceHandler()
alice = P2PNode.from_env(on_command=handler)

try:
    seq = 0
    while True:
        seq += 1
        handler.expect(seq)
        if not alice.send_to_gateway(Probe(seq).to_payload()):
            print(f"[alice] ping #{seq} FAILED to send")
        elif not handler.wait_pong(PONG_TIMEOUT):
            print(f"[alice] pong #{seq} timed out")
        time.sleep(ROUND_DELAY)
except KeyboardInterrupt:
    alice.close()
