import threading
import time

from rak3172 import PayloadHandler

from ..payloads import Probe


class BobHandler(PayloadHandler):
    """Bob (gateway): measure the ping's RSSI, then answer Alice with it after `reply_delay` seconds."""

    payload_type = Probe

    def __init__(self, reply_delay: float = 0.1):
        self.reply_delay = reply_delay

    def on_payload(self, from_addr, message, rssi, snr):
        print(f"[bob] ping #{message.seq} from {from_addr}: rssi={rssi} snr={snr}")
        # Replying sends AT commands, which would deadlock on the RX thread.
        threading.Thread(target=self._pong, args=(from_addr, message.seq, rssi), daemon=True).start()

    def _pong(self, to_addr, seq, rssi):
        time.sleep(self.reply_delay)
        self.reply(to_addr, Probe(seq, rssi).to_payload())
