from rak3172 import Handler


class CommandHandler(Handler):
    """Node side: the gateway sent a command."""

    def handle(self, from_addr, payload, rssi, snr):
        print(f"gateway {from_addr} says {payload.decode('utf-8', 'replace')!r} (rssi={rssi})")
