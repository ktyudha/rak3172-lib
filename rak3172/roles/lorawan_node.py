"""Ready-to-use LoRaWAN end device (OTAA or ABP)."""

import logging

from .. import config
from ..protocols import LoRaWAN

logger = logging.getLogger(__name__)


class LoRaWANNode(LoRaWAN):
    """LoRaWAN end device. Joins on construction-time credentials, then `send_uplink`."""

    def __init__(self, serial_port, fport=2, **kwargs):
        self.fport = fport
        super().__init__(serial_port, **kwargs)

    @classmethod
    def from_env(cls, **overrides):
        """Build from `.env` / environment (OTAA, or ABP if LORAWAN_DEVADDR is set)."""
        settings = {**config.lorawan_settings(), "fport": config.lorawan_fport()}
        return cls(**{**settings, **overrides})

    def connect(self, timeout=60):
        """Join (OTAA) or activate (ABP); blocks until joined. Returns False on timeout."""
        return self.join(wait=True, timeout=timeout)

    def send_uplink(self, payload, fport=None, confirmed=False):
        if not self.is_joined():
            logger.warning("send_uplink while not joined")
        return self.send(fport or self.fport, payload, confirmed=confirmed)
