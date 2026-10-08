"""LoRa P2P protocol layer for the RAK3172 module.

Wraps addressed send/receive over `AT+PSEND` / `+EVT:RXP2P` so application
code (a relay, a gateway, a node, ...) never has to touch AT commands or
packet framing directly.

Frame layout: [from_addr:1][to_addr:1][payload:N]

Extension point: `encoders`/`decoders` are lists of `bytes -> bytes`
transforms applied to the payload on send/receive, in order. This is where
a security layer (encryption, HMAC, ...) plugs in without touching the
framing/retry logic below.
"""

import logging
import threading
import time

from ..core import RAK3172

logger = logging.getLogger(__name__)

BROADCAST = 0xFF

DEFAULT_P2P = dict(
    frequency=915000000,
    spreading_factor=7,
    bandwidth=0,
    coding_rate=0,
    preamble=8,
    tx_power=22,
)


class LoRaP2P:
    def __init__(
        self,
        serial_port,
        address,
        frequency=DEFAULT_P2P["frequency"],
        spreading_factor=DEFAULT_P2P["spreading_factor"],
        bandwidth=DEFAULT_P2P["bandwidth"],
        coding_rate=DEFAULT_P2P["coding_rate"],
        preamble=DEFAULT_P2P["preamble"],
        tx_power=DEFAULT_P2P["tx_power"],
        on_receive=None,
        encoders=None,
        decoders=None,
        verbose=False,
    ):
        self.address = address
        self.on_receive = on_receive
        self.encoders = encoders or []
        self.decoders = decoders or []
        self._rearm_lock = threading.Lock()

        self._p2p_params = dict(
            frequency=frequency,
            spreading_factor=spreading_factor,
            bandwidth=bandwidth,
            coding_rate=coding_rate,
            preamble=preamble,
            tx_power=tx_power,
        )

        self.device = RAK3172(
            serial_port=serial_port,
            network_mode=RAK3172.NETWORK_MODES.P2P,
            verbose=verbose,
            callback_events=self._handle_event,
        )
        self.device.configure_p2p(**self._p2p_params)

    def _handle_event(self, event_type, parameter):
        # Runs on the RX thread (or, for RECONNECTED, a throwaway thread
        # spawned by it): never let a malformed frame or a failing
        # decoder/callback propagate, or the whole listener silently dies.
        if event_type == RAK3172.EVENTS.RECONNECTED:
            logger.warning("device reconnected, reapplying P2P config")
            try:
                self.device.configure_p2p(**self._p2p_params)
            except Exception:
                logger.exception("failed to reapply config after reconnect")
            return

        if event_type != RAK3172.EVENTS.RECEIVED:
            logger.debug("unhandled event %s: %s", event_type, parameter)
            return

        # This firmware drops back to idle after delivering a single packet
        # despite AT+PRECV=65535 claiming "continuous" reception - re-arm
        # unconditionally (even if the frame below turns out malformed), off
        # the RX thread since it sends AT commands and needs that same
        # thread free to read the responses.
        threading.Thread(target=self._rearm_rx, daemon=True).start()

        try:
            rssi, snr, hex_payload = parameter.split(":")
            raw = bytes.fromhex(hex_payload)
            from_addr, to_addr, payload = raw[0], raw[1], raw[2:]
        except (ValueError, IndexError) as exc:
            logger.warning("dropping malformed frame %r: %s", parameter, exc)
            return

        try:
            for decoder in reversed(self.decoders):
                payload = decoder(payload)
        except Exception as exc:
            logger.warning("dropping frame rejected by decoder: %s", exc)
            return

        if self.on_receive:
            try:
                self.on_receive(from_addr, to_addr, payload, rssi, snr)
            except Exception:
                logger.exception("on_receive callback raised")

    def _rearm_rx(self):
        # The disable/enable round trip needs ~0.5s of settle time each way
        # (see enable_p2p_rx) - going faster made the module reboot in
        # testing. The lock drops overlapping triggers from concurrent
        # RECEIVED events onto a single attempt at a time.
        if not self._rearm_lock.acquire(blocking=False):
            return
        try:
            self.device.enable_p2p_rx()
        except Exception:
            logger.exception("failed to re-arm P2P RX after receive")
        finally:
            self._rearm_lock.release()

    def send(self, to_addr, payload, retries=3, retry_delay=0.5):
        """Frame `payload` with the from/to address header and transmit it, retrying on failure."""
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        for encoder in self.encoders:
            payload = encoder(payload)

        frame = bytes([self.address, to_addr]) + payload
        return self._send_raw(frame.hex(), retries=retries, retry_delay=retry_delay)

    def _send_raw(self, hex_payload, retries, retry_delay):
        for attempt in range(1, retries + 1):
            try:
                self.device.send_command(f"AT+PRECV={RAK3172.P2P_RX.DISABLE}")
                time.sleep(0.2)
                if self.device.send_p2p_payload(hex_payload):
                    time.sleep(0.2)
                    self.device.send_command(f"AT+PRECV={RAK3172.P2P_RX.CONTINUOUS}")
                    return True
            except Exception as exc:
                logger.warning("send retry %d/%d failed: %s", attempt, retries, exc)
            time.sleep(retry_delay)

        logger.error("send failed after %d attempts", retries)
        return False

    def run_forever(self):
        """Block until Ctrl-C, then close the device."""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        self.device.send_command(f"AT+PRECV={RAK3172.P2P_RX.DISABLE}")
        self.device.close()
