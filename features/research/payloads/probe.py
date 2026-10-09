from dataclasses import dataclass
from typing import Optional

from rak3172 import Payload


@dataclass
class Probe(Payload):
    """Wire format: "<seq>;<rssi>". Ping has an empty rssi ("12;"), pong echoes the RSSI the sender measured ("12;-71.0")."""

    seq: int
    rssi: Optional[float] = None

    def to_payload(self) -> bytes:
        rssi = "" if self.rssi is None else f"{self.rssi:.0f}"
        return f"{self.seq};{rssi}".encode()

    @classmethod
    def from_payload(cls, payload: bytes) -> Optional["Probe"]:
        try:
            seq, rssi = payload.decode("utf-8").split(";")
            return cls(int(seq), float(rssi) if rssi else None)
        except (UnicodeDecodeError, ValueError):
            return None
