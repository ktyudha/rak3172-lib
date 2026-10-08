import logging
from abc import ABC, abstractmethod
from typing import Optional, Type

from ..payloads import Payload

logger = logging.getLogger(__name__)


class Handler(ABC):
    """Reacts to frames a gateway or node receives. Pass an instance as `on_uplink` / `on_command`."""

    device = None

    def attach(self, device) -> None:
        """Called by the gateway/node that owns this handler, so `reply` works."""
        self.device = device

    def reply(self, to_addr: int, data) -> bool:
        return self.device.send(to_addr, data)

    def __call__(self, from_addr, payload, rssi, snr):
        self.handle(from_addr, payload, rssi, snr)

    @abstractmethod
    def handle(self, from_addr: int, payload: bytes, rssi: str, snr: str) -> None:
        ...


class PayloadHandler(Handler):
    """Decodes frames into `payload_type` and calls `on_payload`; malformed frames are logged and dropped."""

    payload_type: Type[Payload]

    def handle(self, from_addr, payload, rssi, snr):
        message: Optional[Payload] = self.payload_type.from_payload(payload)
        if message is None:
            logger.warning("node %s sent a malformed payload: %r", from_addr, payload)
            return
        self.on_payload(from_addr, message, float(rssi), float(snr))

    @abstractmethod
    def on_payload(self, from_addr: int, message: Payload, rssi: float, snr: float) -> None:
        ...
