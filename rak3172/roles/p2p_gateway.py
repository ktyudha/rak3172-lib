"""Ready-to-use P2P gateway."""

from .. import config
from ..protocols import BROADCAST, LoRaP2P


class P2PGateway(LoRaP2P):
    """Listens for frames addressed to it (or broadcast) and can command nodes.

    `on_uplink(from_addr, payload, rssi, snr)` is called for each accepted frame.
    """

    def __init__(self, serial_port, address=1, on_uplink=None, **kwargs):
        self.on_uplink = on_uplink
        if hasattr(on_uplink, "attach"):
            on_uplink.attach(self)
        super().__init__(serial_port, address, on_receive=self._dispatch, **kwargs)

    @classmethod
    def from_env(cls, **overrides):
        """Build from `.env` / environment (see `rak3172.config`)."""
        return cls(**{**config.p2p_settings(default_address=1), **overrides})

    def _dispatch(self, from_addr, to_addr, payload, rssi, snr):
        if to_addr not in (self.address, BROADCAST):
            return
        if self.on_uplink:
            self.on_uplink(from_addr, payload, rssi, snr)

    def send_to_node(self, node_address, payload, **kwargs):
        return self.send(node_address, payload, **kwargs)

    def broadcast(self, payload, **kwargs):
        return self.send(BROADCAST, payload, **kwargs)
