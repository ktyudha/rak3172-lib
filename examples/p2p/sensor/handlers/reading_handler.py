from rak3172 import PayloadHandler

from ..payloads import SensorReading


class ReadingHandler(PayloadHandler):
    """Gateway side: a node sent a reading."""

    payload_type = SensorReading

    def on_payload(self, from_addr, message, rssi, snr):
        print(
            f"node {from_addr}: {message.temperature} C, {message.humidity} % "
            f"(rssi={rssi}, snr={snr})"
        )
        # Store it / publish to MQTT / feed the ML model here (call a service, keep this short).
        self.reply(from_addr, "ACK")
