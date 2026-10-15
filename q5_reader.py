#!/usr/bin/env python3
"""Read live sample frames from a Data Harvest EasySense Q5."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import select
import struct
import sys
import termios
import time
from typing import Callable


SAMPLE_REQUEST = bytes.fromhex("41 53 00 00 00 00 00 94")
CHANNEL_NAMES = (
    "external_1",
    "external_2",
    "sound",
    "light",
    "temperature",
    "pressure",
    "humidity",
    "unknown_8",
)
DISPLAY_NAMES = {
    2: "Sound",
    3: "Light",
    4: "Internal Temperature",
    5: "Pressure",
    6: "Humidity",
}


def default_device() -> str:
    """Prefer the stable udev name, while still working before setup."""
    stable_name = Path("/dev/easysense-q5")
    return str(stable_name if stable_name.exists() else Path("/dev/ttyUSB0"))


def default_calibration_path() -> Path:
    """Locate calibration data in a clone or an installed environment."""
    candidates = (
        Path.cwd() / "q5_descriptors.json",
        Path(__file__).with_name("q5_descriptors.json"),
        Path(sys.prefix) / "share" / "easysense-q5" / "q5_descriptors.json",
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


@dataclass(frozen=True)
class Calibration:
    name: str
    units: str
    decimal_places: int
    first_value: float
    last_value: float
    first_adc: int
    adc_increments: tuple[int, ...]

    def convert(self, raw: int) -> float:
        if raw < self.first_adc:
            return self.first_value
        step = (self.last_value - self.first_value) / len(self.adc_increments)
        previous_adc = self.first_adc
        for index, increment in enumerate(self.adc_increments):
            current_adc = previous_adc + increment
            if raw <= current_adc:
                fraction = (raw - previous_adc) / (current_adc - previous_adc)
                return self.first_value + (index + fraction) * step
            previous_adc = current_adc
        return self.last_value


def display_name(index: int, calibration: Calibration) -> str:
    if index < 2:
        return f"Input {index + 1} {calibration.name}"
    return DISPLAY_NAMES.get(index, calibration.name)


def parse_calibration(frame: bytes) -> Calibration:
    decimal_places, point_count, encoding = frame[4:7]
    first_value, last_value = struct.unpack(">ff", frame[7:15])
    first_adc = int.from_bytes(frame[15:17], "big")
    increment_count = point_count - 1
    position = 17
    increments: list[int] = []
    if encoding == 1:
        for _ in range(increment_count):
            increments.append(int.from_bytes(frame[position : position + 2], "big"))
            position += 2
    elif encoding == 2:
        increments.extend(frame[position : position + increment_count])
        position += increment_count
    elif encoding == 4:
        while len(increments) < increment_count:
            packed = frame[position]
            position += 1
            increments.extend((packed // 16, packed % 16))
        increments = increments[:increment_count]
    else:
        raise ValueError(f"unsupported calibration encoding {encoding}")

    end = frame.index(b"\r", position)
    name = frame[position:end].decode("latin-1")
    position = end + 1
    end = frame.index(b"\r", position)
    units = frame[position:end].decode("latin-1")
    return Calibration(
        name=name,
        units=units,
        decimal_places=decimal_places,
        first_value=first_value,
        last_value=last_value,
        first_adc=first_adc,
        adc_increments=tuple(increments),
    )


def load_calibrations(path: Path) -> list[Calibration | None]:
    records = json.loads(path.read_text(encoding="utf-8"))
    calibrations: list[Calibration | None] = [None] * 8
    for record in records:
        if "response_hex" not in record:
            continue
        calibration = parse_calibration(bytes.fromhex(record["response_hex"]))
        if calibration.name != "No Sensor":
            calibrations[record["channel"] - 1] = calibration
    return calibrations


def detect_calibrations(
    fd: int,
    timeout: float,
    descriptor_query: Callable[[int, int, float], bytes],
) -> list[Calibration | None]:
    """Read the current descriptors for the seven usable Q5 channels."""
    calibrations: list[Calibration | None] = [None] * 8
    for index in range(7):
        frame = descriptor_query(fd, index, timeout)
        calibration = parse_calibration(frame)
        if index < 2 and calibration.name == "No Sensor":
            # A newly connected SmartQ probe may need a moment to identify
            # itself after the serial port is opened.
            time.sleep(0.25)
            calibration = parse_calibration(descriptor_query(fd, index, timeout))
        if calibration.name != "No Sensor":
            calibrations[index] = calibration
        time.sleep(0.05)
    return calibrations


def configure_port(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[0] = termios.IGNBRK
    attrs[1] = 0
    attrs[2] = termios.B38400 | termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B38400
    attrs[5] = termios.B38400
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def read_exact(fd: int, length: int, timeout: float) -> bytes:
    result = bytearray()
    deadline = time.monotonic() + timeout
    while len(result) < length:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"received {len(result)} of {length} bytes")
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            continue
        chunk = os.read(fd, length - len(result))
        if chunk:
            result.extend(chunk)
    return bytes(result)


def read_sample(fd: int, timeout: float) -> tuple[int, ...]:
    os.write(fd, SAMPLE_REQUEST)
    frame = read_exact(fd, 19, timeout)
    if frame[:2] != b"SC":
        raise ValueError(f"unexpected frame header: {frame.hex(' ')}")
    if sum(frame[:-1]) & 0xFF != frame[-1]:
        raise ValueError(f"bad checksum: {frame.hex(' ')}")
    return struct.unpack(">8H", frame[2:-1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=default_device())
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count", type=int, default=0, help="0 means run until Ctrl-C")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=default_calibration_path(),
        help="cached descriptor file used with --cached",
    )
    parser.add_argument(
        "--cached",
        action="store_true",
        help="use the saved descriptor file instead of detecting connected sensors",
    )
    parser.add_argument("--raw", action="store_true", help="print raw ADC values")
    args = parser.parse_args()

    try:
        fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except OSError as error:
        parser.error(f"cannot open {args.device}: {error.strerror}")
    try:
        configure_port(fd)
        if args.cached:
            try:
                calibrations = load_calibrations(args.calibration)
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                parser.error(f"cannot load calibration file {args.calibration}: {error}")
        else:
            # Imported here to keep the two command-line tools independent while
            # sharing the descriptor request implementation.
            from q5_descriptors import query

            try:
                calibrations = detect_calibrations(fd, args.timeout, query)
            except (OSError, ValueError, TimeoutError) as error:
                parser.error(f"cannot detect connected sensors: {error}")

        selected = [
            (index, cal) for index, cal in enumerate(calibrations) if cal is not None
        ]
        if args.raw:
            print("timestamp," + ",".join(CHANNEL_NAMES), flush=True)
        else:
            headings = [
                f"{display_name(index, cal)} ({cal.units})"
                for index, cal in selected
            ]
            print("timestamp," + ",".join(headings), flush=True)
        sample_number = 0
        while not args.count or sample_number < args.count:
            started = time.monotonic()
            values = read_sample(fd, args.timeout)
            if args.raw:
                rendered = map(str, values)
            else:
                rendered = (
                    f"{cal.convert(values[index]):.{cal.decimal_places}f}"
                    for index, cal in selected
                )
            print(f"{time.time():.3f}," + ",".join(rendered), flush=True)
            sample_number += 1
            delay = args.interval - (time.monotonic() - started)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
