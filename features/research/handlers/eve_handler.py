from typing import Dict, Optional

from ..payloads import Probe


class EveHandler:
    """Eve (listener): logs the RSSI of every Alice/Bob frame she overhears. Receive-only, never transmits.

    Pass as `on_receive` of a bare `LoRaP2P`: the gateway/node roles drop frames addressed to others.
    """

    def __init__(self, names: Optional[Dict[int, str]] = None):
        self.names = names or {}

    def __call__(self, from_addr, to_addr, payload, rssi, snr):
        probe = Probe.from_payload(payload)
        if probe is None:
            print(f"[eve] malformed frame from {from_addr}: {payload!r}")
            return
        sender = self.names.get(from_addr, from_addr)
        target = self.names.get(to_addr, to_addr)
        kind = "ping" if probe.rssi is None else "pong"
        print(f"[eve] {sender} -> {target} {kind} #{probe.seq}: rssi={rssi} snr={snr}")
