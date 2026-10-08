"""`rak3172 init`: validate .env, apply it to the module, read it back."""

import sys

from .. import LoRaP2P, LoRaWAN, RAK3172, config

P2P_READBACK = [
    ("frequency", "AT+PFREQ=?"),
    ("spreading factor", "AT+PSF=?"),
    ("bandwidth", "AT+PBW=?"),
    ("coding rate", "AT+PCR=?"),
    ("preamble", "AT+PPL=?"),
    ("tx power", "AT+PTP=?"),
]


def _step(text):
    print(f"  [ok] {text}")


def _mask(secret):
    return secret[:4] + "*" * (len(secret) - 4) if secret and len(secret) > 4 else "****"


def _init_p2p(port, verbose):
    settings = {**config.p2p_settings(), "serial_port": port, "verbose": verbose}
    print(f"P2P, role={config.role()}, address={settings['address']}")
    dev = LoRaP2P(**settings)
    try:
        _step("module switched to P2P mode and radio configured")
        for label, cmd in P2P_READBACK:
            _status, value = dev.device.send_command(cmd)
            _step(f"{label}: {value}")
    finally:
        dev.close()


def _init_lorawan(port, verbose):
    settings = {**config.lorawan_settings(), "serial_port": port, "verbose": verbose}
    abp = bool(settings.get("devaddr"))
    print(f"LoRaWAN, {'ABP' if abp else 'OTAA'}")
    dev = LoRaWAN(**settings)
    try:
        _step("module switched to LoRaWAN mode and keys written")
        dev.device.set_join_mode(RAK3172.JOIN_MODES.ABP if abp else RAK3172.JOIN_MODES.OTAA)
        _step(f"join mode: {'ABP' if abp else 'OTAA'}")
        if abp:
            _step(f"DevAddr: {dev.device.devaddr}")
        else:
            _step(f"DevEUI: {dev.device.deveui}")
            _step(f"JoinEUI: {dev.device.joineui}")
            _step(f"AppKey: {_mask(dev.device.appkey)}")
    finally:
        dev.close()


def run_init(port=None, verbose=False):
    print("Checking .env ...")
    found = config.problems()
    if found:
        print("Fix these in .env first:")
        for item in found:
            print(f"  - {item}")
        sys.exit(1)
    _step("settings look valid")

    port = port or config.serial_port()
    print(f"Configuring module on {port} ...")
    if config.mode() == "p2p":
        _init_p2p(port, verbose)
    else:
        _init_lorawan(port, verbose)
    print("Done. Start it with `make run`.")
