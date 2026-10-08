"""Serial port discovery, tuned for a Raspberry Pi with a RAK3172/RAK3272S attached."""

import glob

from serial.tools import list_ports

# Order matters: USB adapters first, then the Pi's hardware UART.
_CANDIDATE_GLOBS = [
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/serial0",
    "/dev/tty.usbserial*",
    "/dev/tty.usbmodem*",
]


def available_ports():
    """Return the serial ports the OS reports, as (device, description) tuples."""
    return [(p.device, p.description) for p in list_ports.comports()]


def find_port():
    """Return the first likely module port, or None if nothing is plugged in."""
    for pattern in _CANDIDATE_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None
