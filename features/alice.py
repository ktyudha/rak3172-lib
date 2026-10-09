"""Alice (node): pings Bob, waits for his pong (which carries Bob's RSSI), measures its own RSSI, repeats.

    LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py
    # With custom CSV output path:
    LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 CSV_FILE=my_alice_data.csv python features/alice.py

Expected output: "[alice] pong #N: rssi_at_bob=... rssi_at_alice=..." once per round.
Connection data is saved to CSV file (default: alice_connection_data.csv).
"""

import time
import os

from rak3172 import P2PNode
from research.handlers import AliceHandler
from research.payloads import Probe

ROUND_DELAY = 0.1  # seconds between a pong and the next ping
PONG_TIMEOUT = 5.0 # seconds

csv_file = os.environ.get('CSV_FILE', 'alice_connection_data.csv')
handler = AliceHandler(csv_file=csv_file)
alice = P2PNode.from_env(on_command=handler)

print(f"[alice] saving connection data to {csv_file}")

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
    print(f"[alice] connection data saved to {csv_file}")
