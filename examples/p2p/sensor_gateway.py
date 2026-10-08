"""Sensor gateway entry point: wiring only. Parsing lives in sensor/handlers/reading_handler.py.

    python examples/p2p/sensor_gateway.py
"""

from rak3172 import P2PGateway
from sensor.handlers import ReadingHandler

P2PGateway.from_env(on_uplink=ReadingHandler()).run_forever()
