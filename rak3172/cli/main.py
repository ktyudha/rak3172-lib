"""CLI: `rak3172 <ports|init|run|gateway|node|otaa|abp>`."""

import argparse
import logging
import sys
import time

from .init import run_init
from .. import (
    LoRaWANNode,
    P2PGateway,
    P2PNode,
    RAK3172Error,
    available_ports,
    config,
)


def _add_port(p):
    p.add_argument("--port", help="serial port (default: LORA_SERIAL_PORT, else auto-detect)")
    p.add_argument("--verbose", action="store_true", help="print all serial traffic")


def _add_radio(p):
    r = config.radio_settings()
    p.add_argument("--freq", type=int, default=r["frequency"], help="Hz (LORA_FREQUENCY)")
    p.add_argument("--sf", type=int, default=r["spreading_factor"])
    p.add_argument("--bw", type=int, default=r["bandwidth"])
    p.add_argument("--cr", type=int, default=r["coding_rate"])
    p.add_argument("--preamble", type=int, default=r["preamble"])
    p.add_argument("--tx-power", type=int, default=r["tx_power"])


def _radio(a):
    return dict(
        frequency=a.freq,
        spreading_factor=a.sf,
        bandwidth=a.bw,
        coding_rate=a.cr,
        preamble=a.preamble,
        tx_power=a.tx_power,
    )


def _port(a):
    port = a.port or config.serial_port()
    if not port:
        sys.exit("No serial port found. Plug in the module or set LORA_SERIAL_PORT / --port.")
    return port


def build_parser():
    ap = argparse.ArgumentParser(prog="rak3172")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ports", help="list serial ports")

    i = sub.add_parser("init", help="validate .env and configure the module with it")
    _add_port(i)

    sub.add_parser("run", help="start the mode and role chosen in .env (LORA_MODE / LORA_ROLE)")

    g = sub.add_parser("gateway", help="P2P gateway: print uplinks, optionally send downlinks")
    _add_port(g)
    _add_radio(g)
    g.add_argument("--address", type=int, default=int(config._get("LORA_ADDRESS", "1")))

    n = sub.add_parser("node", help="P2P node: send a message to the gateway periodically")
    _add_port(n)
    _add_radio(n)
    n.add_argument("--address", type=int, default=int(config._get("LORA_ADDRESS", "2")))
    n.add_argument("--gateway", type=int, default=config.gateway_address(), help="gateway address")
    n.add_argument("--message", default="hello")
    n.add_argument("--interval", type=float, default=10)

    o = sub.add_parser("otaa", help="LoRaWAN OTAA node")
    _add_port(o)
    o.add_argument("--appkey", default=config._get("LORAWAN_APPKEY"))
    o.add_argument("--deveui", default=config._get("LORAWAN_DEVEUI"))
    o.add_argument("--joineui", default=config._get("LORAWAN_JOINEUI"))
    o.add_argument("--message", default="hello")
    o.add_argument("--interval", type=float, default=30)

    b = sub.add_parser("abp", help="LoRaWAN ABP node")
    _add_port(b)
    b.add_argument("--devaddr", default=config._get("LORAWAN_DEVADDR"))
    b.add_argument("--nwkskey", default=config._get("LORAWAN_NWKSKEY"))
    b.add_argument("--appskey", default=config._get("LORAWAN_APPSKEY"))
    b.add_argument("--message", default="hello")
    b.add_argument("--interval", type=float, default=30)

    return ap


def _loop_send(send, message, interval):
    try:
        while True:
            print(f"sent={send(message)}")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


def _resolve_run(argv):
    # `run` is a shortcut: pick gateway/node/otaa/abp from .env, keep any extra flags.
    rest = argv[1:]
    found = config.problems()
    if found:
        sys.exit("Fix .env first (run `make init`):\n  - " + "\n  - ".join(found))
    if config.mode() == "lorawan":
        cmd = "abp" if config._get("LORAWAN_DEVADDR") else "otaa"
    else:
        cmd = config.role()
    return [cmd] + rest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run":
        argv = _resolve_run(argv)
    a = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    if a.cmd == "ports":
        for dev, desc in available_ports():
            print(f"{dev}\t{desc}")
        return

    try:
        if a.cmd == "init":
            run_init(a.port, a.verbose)
        elif a.cmd == "gateway":
            gw = P2PGateway(
                _port(a),
                address=a.address,
                on_uplink=lambda f, p, rssi, snr: print(f"[{f}] rssi={rssi} snr={snr} {p!r}"),
                verbose=a.verbose,
                **_radio(a),
            )
            gw.run_forever()
        elif a.cmd == "node":
            node = P2PNode(
                _port(a),
                address=a.address,
                gateway_address=a.gateway,
                on_command=lambda f, p, rssi, snr: print(f"[cmd from {f}] {p!r}"),
                verbose=a.verbose,
                **_radio(a),
            )
            try:
                _loop_send(node.send_to_gateway, a.message, a.interval)
            finally:
                node.close()
        else:
            if a.cmd == "otaa" and not a.appkey:
                sys.exit("Missing appkey: set LORAWAN_APPKEY in .env or pass --appkey")
            if a.cmd == "abp" and not (a.devaddr and a.nwkskey and a.appskey):
                sys.exit("Missing ABP keys: set LORAWAN_DEVADDR/NWKSKEY/APPSKEY or pass flags")
            creds = (
                dict(appkey=a.appkey, deveui=a.deveui, joineui=a.joineui)
                if a.cmd == "otaa"
                else dict(devaddr=a.devaddr, nwkskey=a.nwkskey, appskey=a.appskey)
            )
            node = LoRaWANNode(
                _port(a),
                on_join=lambda: print("joined"),
                on_confirm=lambda ok: print(f"confirmed={ok}"),
                verbose=a.verbose,
                **creds,
            )
            try:
                if not node.connect():
                    sys.exit("Join timed out")
                _loop_send(node.send_uplink, a.message, a.interval)
            finally:
                node.close()
    except RAK3172Error as e:
        sys.exit(f"ERROR - {e}")

