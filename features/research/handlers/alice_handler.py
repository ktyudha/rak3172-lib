import threading
from typing import Optional

from rak3172 import PayloadHandler

from ..payloads import Probe


class AliceHandler(PayloadHandler):
    """Alice (node): measure the RSSI of Bob's pong and wake up the sender loop waiting for it."""

    payload_type = Probe

    def __init__(self):
        self._pong = threading.Event()
        self._seq = -1
        self.rssi_at_bob: Optional[float] = None
        self.rssi_at_alice: Optional[float] = None

    def expect(self, seq: int) -> None:
        """Call before sending ping `seq`; ignores pongs from earlier rounds."""
        self._seq = seq
        self._pong.clear()

    def wait_pong(self, timeout: float) -> bool:
        """Block until the pong for the expected seq arrives. False on timeout."""
        return self._pong.wait(timeout)

    def on_payload(self, from_addr, message, rssi, snr):
        if message.seq != self._seq:
            return
        self.rssi_at_bob, self.rssi_at_alice = message.rssi, rssi
        print(f"[alice] pong #{message.seq}: rssi_at_bob={message.rssi} rssi_at_alice={rssi} snr={snr}")
        self._pong.set()
