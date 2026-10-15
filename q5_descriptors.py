#!/usr/bin/env python3
"""Download channel descriptors and factory calibration bytes from an EasySense Q5."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from q5_reader import configure_port, default_device, read_exact


def command(channel: int) -> bytes:
    packet = bytearray((0x41, 0x4A, 0xFF, channel, 0, 0, 0, 0))
    packet[-1] = sum(packet[:-1]) & 0xFF
    return bytes(packet)


def query(fd: int, channel: int, timeout: float) -> bytes:
    os.write(fd, command(channel))
    header = read_exact(fd, 4, timeout)
    if header[:2] != b"S\x00":
        raise ValueError(f"channel {channel + 1}: unexpected header {header.hex(' ')}")
    declared_length = int.from_bytes(header[2:4], "little")
    if declared_length < 3:
        raise ValueError(f"channel {channel + 1}: invalid length {declared_length}")
    frame = header + read_exact(fd, declared_length - 3, timeout)
    if sum(frame[:-1]) & 0xFF != frame[-1]:
        raise ValueError(f"channel {channel + 1}: checksum failure")
    return frame


def ascii_fields(frame: bytes) -> list[str]:
    fields = []
    for part in frame[4:-1].split(b"\r"):
        text = bytes(byte for byte in part if 32 <= byte < 127).decode("ascii")
        if text:
            fields.append(text)
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=default_device())
    parser.add_argument("--output", type=Path, default=Path("q5_descriptors.json"))
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()

    try:
        fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except OSError as error:
        parser.error(f"cannot open {args.device}: {error.strerror}")
    records = []
    try:
        configure_port(fd)
        for channel in range(8):
            try:
                frame = query(fd, channel, args.timeout)
                record = {
                    "channel": channel + 1,
                    "command_hex": command(channel).hex(" "),
                    "response_hex": frame.hex(" "),
                    "ascii_fields": ascii_fields(frame),
                }
            except ValueError as error:
                record = {
                    "channel": channel + 1,
                    "command_hex": command(channel).hex(" "),
                    "error": str(error),
                }
            records.append(record)
            if "response_hex" in record:
                print(f"channel {channel + 1}: {record['ascii_fields']} ({len(frame)} bytes)")
            else:
                print(f"channel {channel + 1}: {record['error']}")
            time.sleep(0.05)
    finally:
        os.close(fd)

    with args.output.open("w", encoding="utf-8") as output:
        json.dump(records, output, indent=2)
        output.write("\n")
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
