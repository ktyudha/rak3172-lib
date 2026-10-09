"""Bob (gateway): measures RSSI of Alice's ping, answers 100 ms later with that RSSI.

    LORA_ADDRESS=1 python features/bob.py

Expected output: "[bob] ping #N from 2: rssi=... snr=..." once per round.
"""

from rak3172 import P2PGateway
from research.handlers import BobHandler

P2PGateway.from_env(on_uplink=BobHandler(reply_delay=0.1)).run_forever()
