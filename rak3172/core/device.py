# Original author: Oliv4945
# AT commands documentation
# https://docs.rakwireless.com/Product-Categories/WisDuo/RAK3172-Module/AT-Command-Manual/

import logging
import threading
import time

import serial

from .errors import RAK3172Error

logger = logging.getLogger(__name__)


class RAK3172:
    serial = None
    STATUS_CODES = ["OK", "AT_ERROR", "AT_PARAM_ERROR", "AT_BUSY_ERROR"]

    class NETWORK_MODES:
        P2P = 0
        LORAWAN = 1

    class JOIN_MODES:
        ABP = 0
        OTAA = 1

    class JOIN_STATUS:
        NOT_JOINED = 0
        JOINED = 1

    class EVENTS:
        JOINED = 0
        SEND_CONFIRMATION = 1
        RECEIVED = 2
        ERROR = 3
        TIMEOUT = 4
        RECONNECTED = 5

    class P2P_RX:
        DISABLE = 0
        CONTINUOUS = 65535

    def __init__(
        self,
        serial_port,
        network_mode,
        verbose=False,
        callback_events=None,
        baudrate=115200,
    ):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.verbose = verbose
        self._callback_events = callback_events
        self._reconnecting_lock = threading.Lock()
        self.data_rx = ""

        try:
            self.serial = serial.Serial(serial_port, baudrate, timeout=1)
        except serial.SerialException as e:
            raise RAK3172Error(f"Unable to open serial port {serial_port}: {e}") from e
        self.serial.reset_input_buffer()

        # Open RX thread
        self.data_received = threading.Event()
        self.thread_rx_ready = threading.Event()
        self.thread_rx_kill = threading.Event()
        self.thread_rx_handle = threading.Thread(target=self.thread_rx, daemon=True)
        self.thread_rx_handle.start()

        # Check chip presence
        if self.status() is not True:
            self.close()
            raise RAK3172Error(f"Unable to detect RAK3172 on {serial_port}")

        # Ensure network mode
        self.network_mode = network_mode

    def _emit(self, event_type, parameter=None):
        if self._callback_events:
            self._callback_events(event_type, parameter)

    def thread_rx(self):
        self.thread_rx_ready.set()
        while not self.thread_rx_kill.is_set():
            try:
                rx = self.serial.read_until(b"\r\n").decode("ASCII", "ignore").rstrip().upper()
            except (serial.SerialException, OSError):
                self._reconnect()
                continue
            if not len(rx):
                # Drop empty lines
                continue
            self.thread_rx_ready.clear()
            if self.verbose:
                print(f"<- {rx}")
            if rx[0] == "+":
                if rx == "+EVT:JOINED":
                    self._emit(RAK3172.EVENTS.JOINED, None)

                if rx.startswith("+EVT:SEND CONFIRMED"):
                    self._emit(
                        RAK3172.EVENTS.SEND_CONFIRMATION,
                        rx == "+EVT:SEND CONFIRMED OK",
                    )

                if "+EVT:RXP2P" in rx:
                    # Format: +EVT:RXP2P:<rssi>:<snr>:<hex_payload>
                    parts = rx.split(":")
                    if len(parts) >= 5:
                        rssi, snr, payload = parts[2].strip(), parts[3].strip(), parts[4].strip()
                        self._emit(RAK3172.EVENTS.RECEIVED, f"{rssi}:{snr}:{payload}")

            elif "CURRENT WORK MODE" in rx:
                # The module reboots on its own sometimes (power/watchdog
                # reset) without the USB-serial link dropping at all - this
                # boot banner is the only sign. Radio config and RX mode
                # don't survive it, so callers must redo them.
                logger.warning("%s reported a reboot: %s", self.serial_port, rx)
                self._notify_reconnected()
            else:
                # RUI3 firmware (e.g. RUI_4.2.0) echoes the command name in
                # query replies, e.g. "AT+NWM=0" instead of a bare "0".
                if rx.startswith("AT+") and "=" in rx:
                    rx = rx.split("=", 1)[1]
                self.data_rx = rx
                self.data_received.set()
                time_start = time.time()
                while self.data_received.is_set():
                    # Wait for data to be processed or timeout
                    if time.time() > time_start + 0.1:
                        # Timeout, prepare for next RX
                        self.data_received.clear()
                        self.data_rx = ""
            self.thread_rx_ready.set()

    def _reconnect(self):
        # The module can reboot on its own (power/watchdog reset), which
        # drops the USB-serial device node until it re-enumerates. Radio
        # config and RX mode don't survive that, so callers must redo them
        # via the RECONNECTED event once the link is back.
        logger.warning("Serial port %s lost, reconnecting...", self.serial_port)
        self.thread_rx_ready.clear()
        try:
            self.serial.close()
        except Exception:
            pass

        while not self.thread_rx_kill.is_set():
            time.sleep(2)
            try:
                self.serial = serial.Serial(self.serial_port, self.baudrate, timeout=1)
                self.serial.reset_input_buffer()
                break
            except serial.SerialException:
                continue

        if self.thread_rx_kill.is_set():
            return

        logger.info("Reconnected to %s", self.serial_port)
        self.thread_rx_ready.set()
        self._notify_reconnected()

    def _notify_reconnected(self):
        # Runs the callback on its own thread: it typically re-sends AT
        # commands (e.g. configure_p2p), which needs this RX thread free to
        # read the responses - calling it inline here would deadlock.
        # The lock drops duplicate/overlapping triggers (e.g. a burst of
        # boot-banner lines) so only one reconfigure attempt runs at a time.
        if not self._callback_events:
            return
        if not self._reconnecting_lock.acquire(blocking=False):
            return

        def run():
            try:
                self._emit(RAK3172.EVENTS.RECONNECTED, None)
            finally:
                self._reconnecting_lock.release()

        threading.Thread(target=run, daemon=True).start()

    def _get(self, cmd, what):
        status, data = self.send_command(cmd)
        if status != "OK":
            raise RAK3172Error(f"Unable to get {what} (status={status})")
        return data

    def _set(self, cmd, what, restart=False):
        status, _ = self.send_command(cmd)
        if status != "OK":
            raise RAK3172Error(f"Unable to set {what} (status={status})")
        if restart:
            # RAK3172 needs to be restarted to take it into account
            self.reset_soft()

    @property
    def network_mode(self):
        return self.__network_mode

    @network_mode.setter
    def network_mode(self, network_mode):
        if int(self._get("AT+NWM=?", "network mode")) != network_mode:
            self._set(f"AT+NWM={network_mode}", "network mode")
        self.__network_mode = network_mode

    @property
    def appkey(self):
        return self._get("AT+APPKEY=?", "APPKEY")

    @appkey.setter
    def appkey(self, appkey):
        self._set(f"AT+APPKEY={appkey}", "AppKey", restart=True)

    @property
    def deveui(self):
        return self._get("AT+DEVEUI=?", "devEUI")

    @deveui.setter
    def deveui(self, deveui):
        self._set(f"AT+DEVEUI={deveui}", "devEUI", restart=True)

    @property
    def joineui(self):
        return self._get("AT+APPEUI=?", "joinEUI")

    @joineui.setter
    def joineui(self, joineui):
        self._set(f"AT+APPEUI={joineui}", "joinEUI", restart=True)

    @property
    def devaddr(self):
        return self._get("AT+DEVADDR=?", "devAddr")

    @devaddr.setter
    def devaddr(self, devaddr):
        self._set(f"AT+DEVADDR={devaddr}", "devAddr", restart=True)

    @property
    def nwkskey(self):
        return self._get("AT+NWKSKEY=?", "NwkSKey")

    @nwkskey.setter
    def nwkskey(self, nwkskey):
        self._set(f"AT+NWKSKEY={nwkskey}", "NwkSKey", restart=True)

    @property
    def appskey(self):
        return self._get("AT+APPSKEY=?", "AppSKey")

    @appskey.setter
    def appskey(self, appskey):
        self._set(f"AT+APPSKEY={appskey}", "AppSKey", restart=True)

    @property
    def getdata(self):
        return self._get("AT+RECV=?", "data")

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, verbose):
        self.__verbose = verbose

    @property
    def serial_port(self):
        return self.__serial_port

    @serial_port.setter
    def serial_port(self, port):
        self.__serial_port = port

    def close(self):
        self.thread_rx_kill.set()
        try:
            self.serial.close()
        except Exception:
            pass

    def set_join_mode(self, join_mode):
        self._set(f"AT+NJM={join_mode}", "join mode")

    def join(self):
        """Start an OTAA join; completion is reported through the JOINED event."""
        self.set_join_mode(RAK3172.JOIN_MODES.OTAA)
        self._set("AT+JOIN=1:0:8:0", "join")

    def join_status(self):
        return int(self._get("AT+NJS=?", "join status"))

    def reset_soft(self):
        self.send_command("ATZ", ignore=True)
        # Give some time to the device to restart
        time.sleep(1.0)
        self.serial.reset_input_buffer()

    def send_command(self, cmd, ignore=False):
        # Ensure case
        cmd = cmd.upper()
        # Clear RX buffer
        self.data_rx = ""
        # Send command as soon as RX thread is available
        if not self.thread_rx_ready.wait(10):
            return None, None
        self.serial.write(cmd.encode("ASCII") + b"\r\n")
        self.serial.flush()

        if self.verbose is True:
            print(f"-> {cmd}")

        if not ignore:
            if self.data_received.wait(10):
                # Get data or status code
                data = self.data_rx
                self.data_received.clear()
                if data in RAK3172.STATUS_CODES:
                    return data, None
                # Already got data, only status code remaining
                if self.data_received.wait(10):
                    status = self.data_rx
                    self.data_received.clear()
                    return status, data

        return None, None

    def send_payload(self, fport, payload, confirmed=False):
        """Send a LoRaWAN uplink. `payload` is hex-ASCII `bytes`."""
        # TODO - Implement confirm messages
        status, _ = self.send_command(f'AT+SEND={fport}:{payload.decode("ASCII")}')
        if status != "OK":
            logger.error("Unable to send payload (status=%s)", status)
            return False
        return True

    def status(self):
        status, _ = self.send_command("AT")
        return status == "OK"

    def configure_p2p(self, frequency, spreading_factor, bandwidth, coding_rate, preamble, tx_power):
        """Put the module in P2P mode with the given radio parameters and start RX."""
        self.network_mode = RAK3172.NETWORK_MODES.P2P

        # A prior session may have left continuous RX on (e.g. crashed
        # without calling close()); radio params can't be set while it's on.
        self.send_command(f"AT+PRECV={RAK3172.P2P_RX.DISABLE}")
        time.sleep(0.2)

        p2p_params = {
            "AT+PFREQ": frequency,
            "AT+PSF": spreading_factor,
            "AT+PBW": bandwidth,
            "AT+PCR": coding_rate,
            "AT+PPL": preamble,
            "AT+PTP": tx_power,
        }
        for cmd, value in p2p_params.items():
            self._set(f"{cmd}={value}", cmd)

        self.enable_p2p_rx()
        logger.info("P2P mode configured")

    def enable_p2p_rx(self):
        """Enable continuous P2P reception."""
        self.send_command(f"AT+PRECV={RAK3172.P2P_RX.DISABLE}")  # Reset RX
        time.sleep(0.5)
        self.send_command(f"AT+PRECV={RAK3172.P2P_RX.CONTINUOUS}")
        time.sleep(0.5)
        logger.debug("P2P RX enabled")

    @property
    def get_p2p_data(self):
        return self._get("AT+PRECV=?", "P2P data")

    def send_p2p_payload(self, payload, confirmed=False):
        """Send a raw P2P frame. `payload` is a hex string."""
        status, _ = self.send_command(f"AT+PSEND={payload}")
        if status != "OK":
            logger.error("Unable to send P2P payload (status=%s)", status)
            return False
        return True
