import threading
from datetime import datetime
from typing import Optional
import csv
import os

from rak3172 import PayloadHandler

from ..payloads import Probe


class AliceHandler(PayloadHandler):
    """Alice (node): measure the RSSI of Bob's pong and wake up the sender loop waiting for it."""

    payload_type = Probe

    def __init__(self, csv_file: Optional[str] = None):
        self._pong = threading.Event()
        self._seq = -1
        self.rssi_at_bob: Optional[float] = None
        self.rssi_at_alice: Optional[float] = None
        self._csv_file = csv_file or "alice_connection_data.csv"
        self._csv_lock = threading.Lock()
        self._init_csv()

    def _init_csv(self) -> None:
        """Initialize CSV file with headers if it doesn't exist or is empty."""
        file_exists = os.path.exists(self._csv_file) and os.path.getsize(self._csv_file) > 0
        with self._csv_lock:
            with open(self._csv_file, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'seq', 'rssi_at_bob', 'rssi_at_alice', 'snr'])
                if not file_exists:
                    writer.writeheader()

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
        timestamp = datetime.now().isoformat()
        print(f"[alice] pong #{message.seq}: rssi_at_bob={message.rssi} rssi_at_alice={rssi} snr={snr}")
        self._save_to_csv(timestamp, message.seq, message.rssi, rssi, snr)
        self._pong.set()

    def _save_to_csv(self, timestamp: str, seq: int, rssi_at_bob: Optional[float], rssi_at_alice: float, snr: float) -> None:
        """Save connection data to CSV file."""
        with self._csv_lock:
            with open(self._csv_file, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'seq', 'rssi_at_bob', 'rssi_at_alice', 'snr'])
                writer.writerow({
                    'timestamp': timestamp,
                    'seq': seq,
                    'rssi_at_bob': rssi_at_bob,
                    'rssi_at_alice': rssi_at_alice,
                    'snr': snr
                })
