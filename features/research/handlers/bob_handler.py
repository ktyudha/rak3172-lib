import threading
import time
import csv
import os
from datetime import datetime
from typing import Optional

from rak3172 import PayloadHandler

from ..payloads import Probe


class BobHandler(PayloadHandler):
    """Bob (gateway): measure the ping's RSSI, then answer Alice with it after `reply_delay` seconds."""

    payload_type = Probe

    def __init__(self, reply_delay: float = 0.1, csv_file: Optional[str] = None):
        self.reply_delay = reply_delay
        self._csv_file = csv_file or "bob_connection_data.csv"
        self._csv_lock = threading.Lock()
        self._init_csv()

    def _init_csv(self) -> None:
        """Initialize CSV file with headers if it doesn't exist or is empty."""
        file_exists = os.path.exists(self._csv_file) and os.path.getsize(self._csv_file) > 0
        with self._csv_lock:
            with open(self._csv_file, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'seq', 'from_addr', 'rssi', 'snr'])
                if not file_exists:
                    writer.writeheader()

    def on_payload(self, from_addr, message, rssi, snr):
        timestamp = datetime.now().isoformat()
        print(f"[bob] ping #{message.seq} from {from_addr}: rssi={rssi} snr={snr}")
        self._save_to_csv(timestamp, message.seq, from_addr, rssi, snr)
        # Replying sends AT commands, which would deadlock on the RX thread.
        threading.Thread(target=self._pong, args=(from_addr, message.seq, rssi), daemon=True).start()

    def _pong(self, to_addr, seq, rssi):
        time.sleep(self.reply_delay)
        self.reply(to_addr, Probe(seq, rssi).to_payload())

    def _save_to_csv(self, timestamp: str, seq: int, from_addr: int, rssi: float, snr: float) -> None:
        """Save connection data to CSV file."""
        with self._csv_lock:
            with open(self._csv_file, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'seq', 'from_addr', 'rssi', 'snr'])
                writer.writerow({
                    'timestamp': timestamp,
                    'seq': seq,
                    'from_addr': from_addr,
                    'rssi': rssi,
                    'snr': snr
                })
