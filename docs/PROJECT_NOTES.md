# Investigation and Implementation Notes

## Objective

The project began with a Data Harvest EasySense Q5 visible in the Linux kernel
log but without a convenient native acquisition path. The goal became a
reproducible GitHub project that another Linux user can clone, initialize, and
run using Python commands.

## Investigation summary

The work established the following:

1. The Q5 is USB device `0403:fe5c` and uses an FTDI FT232B interface.
2. Registering that custom ID with `ftdi_sio` creates a standard serial device.
3. The legacy Windows software works through Wine and a COM-port mapping, which
   verified the logger and provided initial reference values.
4. Serial communication operates at 38400 8N1.
5. An eight-byte `AS` command requests a 19-byte live sample frame.
6. An `AJ` family of commands returns per-channel descriptors.
7. Descriptor responses carry sensor identity, units, precision, physical
   endpoints, and compressed ADC calibration knots.
8. The calibration behavior is piecewise-linear interpolation with endpoint
   clamping.
9. External sensors can be identified generically; Python does not need a sensor
   name database or vendor DLL at runtime.
10. The Q5 may briefly report `No Sensor` for a removable input immediately after
    opening, so automatic detection retries external inputs.

The legacy binaries were useful during interoperability research, particularly
for checking conversion behavior. They are not redistributed and are not a
runtime dependency.

## What was built

### Native reader

`q5_reader.py`:

- opens and configures the serial device without third-party packages;
- detects current sensors at startup;
- validates sample and descriptor checksums;
- decodes three observed calibration-table compression formats;
- interpolates raw ADC values into physical measurements;
- labels external inputs using descriptor-provided names and units;
- writes line-buffered CSV suitable for terminals, files, and pipelines;
- supports finite sample counts, adjustable intervals and timeouts, raw ADC
  output, alternate device paths, and an explicit cached-descriptor mode.

### Descriptor capture tool

`q5_descriptors.py`:

- queries each Q5 channel;
- records exact command and response bytes as hexadecimal;
- validates lengths and checksums;
- includes diagnostic printable fields;
- preserves unsupported-channel errors in JSON for investigation.

### Linux integration

The `scripts/` directory contains:

- transient driver initialization;
- persistent udev installation;
- an event helper for registering the custom FTDI product ID;
- stable device naming and `dialout` permissions.

### Packaging and repository support

The repository includes:

- dependency-free Python packaging through `pyproject.toml`;
- console commands `easysense-q5` and `easysense-q5-descriptors`;
- bundled fallback descriptor data in installed wheels;
- an MIT license, contribution guide, changelog, and focused `.gitignore`;
- GitHub Actions across Python 3.10–3.13;
- hardware-independent unit tests for framing, byte order, calibration,
  descriptor-driven naming, and live-detection behavior.

## Verification performed

The following were exercised during development:

- shell syntax checks for setup helpers;
- Python bytecode compilation;
- the complete unit-test suite;
- wheel construction without runtime dependencies;
- clean virtual-environment installation;
- both installed console entry points;
- discovery of bundled calibration data outside the source directory;
- live calibrated acquisition from the Q5;
- raw eight-channel acquisition;
- live automatic identification of an external sound sensor in millivolt mode.

## Design decisions

Automatic live detection is the default because cached descriptors become wrong
when an external probe or selected range changes. Cached mode is retained for
repeatability, offline inspection, and protocol debugging.

The code intentionally uses standard-library `termios`, `select`, and `os`
instead of adding `pyserial`. This keeps installation small, though it makes the
reader Linux/POSIX-specific.

Raw captures remain valuable. A sensor name alone is insufficient evidence of a
conversion: unit, range, precision, ADC knots, and the current selected range all
matter.

## Future work

- Test additional analogue SmartQ sensors and all selectable ranges.
- Capture and implement digital/timing accessories.
- Identify the eighth sample word and trailing descriptor metadata.
- Add commands for selecting sensor ranges where the protocol permits it.
- Investigate internal-memory logging and download operations.
- Test Q3, Q5+, QAdvanced, and other related hardware without assuming protocol
  compatibility.
- Add recorded-frame fixtures from more devices while avoiding redistribution of
  proprietary vendor software.
