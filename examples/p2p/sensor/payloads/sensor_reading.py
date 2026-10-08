from dataclasses import dataclass
from typing import Optional

from rak3172 import Payload


@dataclass
class SensorReading(Payload):
    """Wire format: "<temperature>;<humidity>", e.g. "27.4;63.2"."""

    temperature: float
    humidity: float

    def to_payload(self) -> bytes:
        return f"{self.temperature:.1f};{self.humidity:.1f}".encode()

    @classmethod
    def from_payload(cls, payload: bytes) -> Optional["SensorReading"]:
        try:
            temperature, humidity = payload.decode("utf-8").split(";")
            return cls(float(temperature), float(humidity))
        except (UnicodeDecodeError, ValueError):
            return None
