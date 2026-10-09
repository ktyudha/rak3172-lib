"""Bob (gateway): measures RSSI of Alice's ping, answers 100 ms later with that RSSI.

    LORA_ADDRESS=1 python features/bob.py
    # With custom CSV output path:
    LORA_ADDRESS=1 CSV_FILE=my_bob_data.csv python features/bob.py

Expected output: "[bob] ping #N from 2: rssi=... snr=..." once per round.
Connection data is saved to CSV file (default: bob_connection_data.csv).
"""

import os
from rak3172 import P2PGateway
from research.handlers import BobHandler

csv_file = os.environ.get('CSV_FILE', 'bob_connection_data.csv')
handler = BobHandler(reply_delay=0.1, csv_file=csv_file)
print(f"[bob] saving connection data to {csv_file}")
P2PGateway.from_env(on_uplink=handler).run_forever()
