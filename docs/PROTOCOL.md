# EasySense Q5 Serial Protocol

This document records the portions of the protocol observed and implemented by
this project. Multi-byte byte order is field-specific; do not assume one byte
order for an entire packet.

## Framing and checksums

Commands observed here are eight bytes long. The final byte is the low eight
bits of the sum of all preceding bytes:

```text
checksum = sum(packet_without_checksum) & 0xff
```

Responses use the same additive checksum convention. The reader rejects frames
whose checksum does not match.

## Live sample request

The sample command is constant:

```text
41 53 00 00 00 00 00 94
```

The response is 19 bytes:

| Offset | Size | Meaning |
|---:|---:|---|
| 0 | 2 | Header `53 43` (`SC`) |
| 2 | 16 | Eight unsigned 16-bit channel words, big-endian |
| 18 | 1 | Additive checksum |

The eight raw words correspond to external inputs 1 and 2, the five built-in Q5
sensors, and an eighth word whose purpose has not been established. Calibrated
output only includes channels that returned a usable descriptor.

Example payload decoding:

```text
4f c0 99 00 18 80 38 c0 89 00 ea 40 49 00 da 80
```

becomes:

```text
20416, 39168, 6272, 14528, 35072, 59968, 18688, 55936
```

## Descriptor request

The implemented descriptor command is:

```text
41 4a ff CC 00 00 00 XX
```

`CC` is the zero-based channel index and `XX` is the additive checksum. Examples:

```text
Channel 1: 41 4a ff 00 00 00 00 8a
Channel 2: 41 4a ff 01 00 00 00 8b
```

Normal descriptor responses begin with `53 00`. Bytes 2–3 hold a little-endian
length field. The response is read to that declared size and its checksum is
validated before decoding.

The attempted channel-8 descriptor query returned:

```text
53 49 4e 56
```

which reads as `SINV` and is treated as an invalid/unsupported channel response.
The automatic detector therefore queries the seven usable measurement channels.

## Automatic startup sequence

`q5_reader.py` performs this sequence:

1. Open and configure the serial port.
2. Query descriptors for channels 1–7.
3. Retry external inputs 1 and 2 briefly if the first result is `No Sensor`.
4. Decode the returned calibration records in memory.
5. Repeatedly request sample frames.
6. Convert each raw channel word using its current descriptor.
7. Print timestamped CSV.

The brief retry was added after the Q5 occasionally reported `No Sensor` on the
first query immediately after opening the port.

## Confirmed and unknown scope

The protocol is confirmed on the tested EasySense Q5 with analogue SmartQ
sensors. The following remain outside the verified scope:

- the meaning of the eighth sample word;
- digital event and timing accessories such as light gates;
- logging into or retrieving data from Q5 internal memory;
- commands for changing a sensor's selected range;
- other Q-series models and firmware revisions.

Captured examples and new hardware reports are welcome, but raw protocol changes
should be backed by repeatable captures and tests.
