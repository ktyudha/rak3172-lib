"""Settings from environment / `.env`, using the same variable names as the SmartNet ML project.

The `.env` is searched from the current working directory upwards, so running
from the project folder on a Raspberry Pi just works. Real environment
variables take precedence over the file.

    LORA_SERIAL_PORT      serial port (auto-detected if unset)
    LORA_ADDRESS          P2P address of this device (1 byte)
    LORA_GATEWAY_ADDRESS  P2P address of the gateway (node role)
    LORA_FREQUENCY, LORA_SPREADING_FACTOR, LORA_BANDWIDTH, LORA_CODING_RATE,
    LORA_PREAMBLE, LORA_TX_POWER, LORA_VERBOSE
    LORAWAN_DEVEUI, LORAWAN_JOINEUI, LORAWAN_APPKEY            (OTAA)
    LORAWAN_DEVADDR, LORAWAN_NWKSKEY, LORAWAN_APPSKEY          (ABP)
    LORAWAN_FPORT
"""

import os

from dotenv import find_dotenv, load_dotenv

from .ports import find_port

load_dotenv(find_dotenv(usecwd=True))


def _get(name, default=None):
    value = os.getenv(name)
    return default if value in (None, "") else value


def serial_port():
    return _get("LORA_SERIAL_PORT") or find_port()


def radio_settings():
    return dict(
        frequency=int(_get("LORA_FREQUENCY", "915000000")),
        spreading_factor=int(_get("LORA_SPREADING_FACTOR", "7")),
        bandwidth=int(_get("LORA_BANDWIDTH", "0")),
        coding_rate=int(_get("LORA_CODING_RATE", "0")),
        preamble=int(_get("LORA_PREAMBLE", "8")),
        tx_power=int(_get("LORA_TX_POWER", "22")),
    )


def verbose():
    return _get("LORA_VERBOSE", "false").lower() == "true"


def p2p_settings(default_address=1):
    """Kwargs for `LoRaP2P` / `P2PGateway` / `P2PNode`."""
    return dict(
        serial_port=serial_port(),
        address=int(_get("LORA_ADDRESS", str(default_address))),
        verbose=verbose(),
        **radio_settings(),
    )


def gateway_address():
    return int(_get("LORA_GATEWAY_ADDRESS", "1"))


def lorawan_settings():
    """Kwargs for `LoRaWAN` / `LoRaWANNode`: ABP if LORAWAN_DEVADDR is set, else OTAA."""
    common = dict(serial_port=serial_port(), verbose=verbose())
    if _get("LORAWAN_DEVADDR"):
        return dict(
            devaddr=_get("LORAWAN_DEVADDR"),
            nwkskey=_get("LORAWAN_NWKSKEY"),
            appskey=_get("LORAWAN_APPSKEY"),
            **common,
        )
    return dict(
        deveui=_get("LORAWAN_DEVEUI"),
        joineui=_get("LORAWAN_JOINEUI"),
        appkey=_get("LORAWAN_APPKEY"),
        **common,
    )


def lorawan_fport():
    return int(_get("LORAWAN_FPORT", "2"))


def mode():
    return _get("LORA_MODE", "p2p").lower()


def role():
    return _get("LORA_ROLE", "gateway").lower()


def _hex_problem(name, value, length):
    if not value:
        return f"{name} is not set"
    if len(value) != length or any(c not in "0123456789abcdefABCDEF" for c in value):
        return f"{name} must be {length} hex characters"
    return None


def problems():
    """Human-readable list of mistakes in the current settings; empty when they look usable."""
    found = []
    if not serial_port():
        found.append("LORA_SERIAL_PORT is not set and no port was detected (run `make ports`)")

    if mode() == "p2p":
        if role() not in ("gateway", "node"):
            found.append("LORA_ROLE must be 'gateway' or 'node'")
        for name, value in (("LORA_ADDRESS", _get("LORA_ADDRESS", "1")), ("LORA_GATEWAY_ADDRESS", _get("LORA_GATEWAY_ADDRESS", "1"))):
            if not value.isdigit() or not 1 <= int(value) <= 254:
                found.append(f"{name} must be a number from 1 to 254")
    elif mode() == "lorawan":
        if _get("LORAWAN_DEVADDR"):
            checks = (("LORAWAN_DEVADDR", 8), ("LORAWAN_NWKSKEY", 32), ("LORAWAN_APPSKEY", 32))
        else:
            checks = (("LORAWAN_DEVEUI", 16), ("LORAWAN_JOINEUI", 16), ("LORAWAN_APPKEY", 32))
        found += [p for p in (_hex_problem(n, _get(n), length) for n, length in checks) if p]
    else:
        found.append("LORA_MODE must be 'p2p' or 'lorawan'")
    return found
