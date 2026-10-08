"""Ready-to-use P2P node."""

from .. import config
from ..protocols import BROADCAST, LoRaP2P


class P2PNode(LoRaP2P):
    """Sends readings to a gateway and receives its commands.

    `on_command(from_addr, payload, rssi, snr)` is called for frames addressed to this node.
    """

    def __init__(self, serial_port, address=2, gateway_address=1, on_command=None, **kwargs):
        self.gateway_address = gateway_address
        self.on_command = on_command
        if hasattr(on_command, "attach"):
            on_command.attach(self)
        super().__init__(serial_port, address, on_receive=self._dispatch, **kwargs)

    @classmethod
    def from_env(cls, **overrides):
        """Build from `.env` / environment (see `rak3172.config`)."""
        settings = config.p2p_settings(default_address=2)
        settings["gateway_address"] = config.gateway_address()
        return cls(**{**settings, **overrides})

    def _dispatch(self, from_addr, to_addr, payload, rssi, snr):
        if to_addr not in (self.address, BROADCAST):
            return
        if self.on_command:
            self.on_command(from_addr, payload, rssi, snr)

    def send_to_gateway(self, payload, **kwargs):
        return self.send(self.gateway_address, payload, **kwargs)
