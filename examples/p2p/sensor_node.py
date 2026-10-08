"""Sensor node entry point: read the sensor and send a SensorReading every INTERVAL seconds.

    python examples/p2p/sensor_node.py

Replace read_sensor() with your real sensor driver.
"""

import random
import time

from rak3172 import P2PNode
from sensor.handlers import CommandHandler
from sensor.payloads import SensorReading

INTERVAL = 10


def read_sensor() -> SensorReading:
    return SensorReading(
        temperature=round(random.uniform(24, 32), 1),
        humidity=round(random.uniform(50, 80), 1),
    )


node = P2PNode.from_env(on_command=CommandHandler())

try:
    while True:
        reading = read_sensor()
        ok = node.send_to_gateway(reading.to_payload())
        print(f"sent {reading} -> {'ok' if ok else 'FAILED'}")
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    node.close()
