"""LoRaWAN protocol layer for the RAK3172 module (OTAA and ABP).

Wraps join/uplink/downlink handling behind a small callback-based API so
application code never has to touch AT commands or session state directly.

Extension point: `encoders`/`decoders` are lists of `bytes -> bytes`
transforms applied to the payload on send/receive, in order.
"""

import logging
import threading

from ..core import RAK3172

logger = logging.getLogger(__name__)


class LoRaWAN:
    class STATE:
        DISCONNECTED = 0
        JOINING = 1
        JOINED = 2

    def __init__(
        self,
        serial_port,
        deveui=None,
        joineui=None,
        appkey=None,
        devaddr=None,
        nwkskey=None,
        appskey=None,
        on_join=None,
        on_confirm=None,
        on_receive=None,
        encoders=None,
        decoders=None,
        verbose=False,
    ):
        """OTAA when `appkey` is given (deveui/joineui optional - the module's own are kept
        if omitted); ABP when `devaddr`, `nwkskey` and `appskey` are given."""
        self.abp = devaddr is not None
        if self.abp and not (nwkskey and appskey):
            raise ValueError("ABP needs devaddr, nwkskey and appskey")
        if not self.abp and not appkey:
            raise ValueError("OTAA needs an appkey (or pass devaddr/nwkskey/appskey for ABP)")

        self.on_join = on_join
        self.on_confirm = on_confirm
        self.on_receive = on_receive
        self.encoders = encoders or []
        self.decoders = decoders or []
        self.state = LoRaWAN.STATE.DISCONNECTED
        self._joined = threading.Event()

        self.device = RAK3172(
            serial_port=serial_port,
            network_mode=RAK3172.NETWORK_MODES.LORAWAN,
            verbose=verbose,
            callback_events=self._handle_event,
        )
        if self.abp:
            self.device.devaddr = devaddr
            self.device.nwkskey = nwkskey
            self.device.appskey = appskey
        else:
            if deveui:
                self.device.deveui = deveui
            if joineui:
                self.device.joineui = joineui
            self.device.appkey = appkey

    def _handle_event(self, event_type, parameter):
        # Runs on the RX thread: never let a failing callback propagate,
        # or the whole listener silently dies.
        if event_type == RAK3172.EVENTS.JOINED:
            self.state = LoRaWAN.STATE.JOINED
            self._joined.set()
            if self.on_join:
                try:
                    self.on_join()
                except Exception:
                    logger.exception("on_join callback raised")
        elif event_type == RAK3172.EVENTS.SEND_CONFIRMATION:
            if self.on_confirm:
                try:
                    self.on_confirm(parameter)
                except Exception:
                    logger.exception("on_confirm callback raised")
        elif event_type == RAK3172.EVENTS.RECONNECTED:
            logger.warning("device reconnected, rejoining")
            self.state = LoRaWAN.STATE.DISCONNECTED
            self._joined.clear()
            try:
                self.join()
            except Exception:
                logger.exception("rejoin after reconnect failed")
        else:
            logger.debug("unhandled event %s: %s", event_type, parameter)

    def join(self, wait=False, timeout=60):
        """Join the network. ABP has no join procedure, so it is marked joined immediately.

        With `wait=True`, block until joined; returns False on timeout.
        """
        if self.abp:
            self.device.set_join_mode(RAK3172.JOIN_MODES.ABP)
            self.state = LoRaWAN.STATE.JOINED
            self._joined.set()
            return True

        self.state = LoRaWAN.STATE.JOINING
        self.device.join()
        return self.wait_joined(timeout) if wait else True

    def wait_joined(self, timeout=None):
        return self._joined.wait(timeout)

    def is_joined(self):
        return self.state == LoRaWAN.STATE.JOINED

    def send(self, fport, payload, confirmed=False):
        """Encode `payload` to the hex-ASCII form `AT+SEND` expects and transmit it on `fport`."""
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        for encoder in self.encoders:
            payload = encoder(payload)

        return self.device.send_payload(fport, payload.hex().encode("ascii"), confirmed=confirmed)

    def receive(self):
        raw = self.device.getdata
        hex_payload = raw.split(":")[-1].strip()
        payload = bytes.fromhex(hex_payload)

        for decoder in reversed(self.decoders):
            payload = decoder(payload)

        if self.on_receive:
            self.on_receive(payload)

        return payload

    def close(self):
        self.device.close()
