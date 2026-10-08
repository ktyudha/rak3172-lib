"""LoRaWAN node: join (OTAA, or ABP if LORAWAN_DEVADDR is set) and send an uplink every 30 s.

    python examples/lorawan/otaa.py

Credentials come from .env (LORAWAN_DEVEUI / LORAWAN_JOINEUI / LORAWAN_APPKEY).
"""

import time

from rak3172 import LoRaWANNode

node = LoRaWANNode.from_env(
    on_join=lambda: print("joined"),
    on_confirm=lambda ok: print(f"uplink confirmed: {ok}"),
)
if not node.connect(timeout=60):
    raise SystemExit("join timed out")
try:
    while True:
        node.send_uplink(b"FEED")
        time.sleep(30)
except KeyboardInterrupt:
    node.close()
