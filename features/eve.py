"""Eve (listener): prints RSSI/SNR of every frame Alice and Bob exchange. Never transmits.

    LORA_ADDRESS=3 python features/eve.py

Expected output: "[eve] alice -> bob ping #N: rssi=..." and "[eve] bob -> alice pong #N: rssi=...".
"""

from rak3172 import LoRaP2P, config
from research.handlers import EveHandler

NAMES = {1: "bob", 2: "alice"}

LoRaP2P(**config.p2p_settings(default_address=3), on_receive=EveHandler(NAMES)).run_forever()
