# EasySense Q5 for Linux

Native, dependency-free Python access to the legacy **Data Harvest EasySense Q5**
data logger on Linux.

The project reads the Q5 over its FTDI USB connection, validates every protocol
frame, and converts raw readings using the factory calibration tables downloaded
from the logger. Wine and the discontinued EasySense application are not needed.

## Supported measurements

- Compatible analogue SmartQ sensors on external inputs 1 and 2, detected at startup
- Sound level in dBA
- Light level in lux
- Internal temperature in degrees Celsius
- Barometric pressure in kPa
- Relative humidity in %RH

External sensor names, units, ranges, precision, and calibration curves are read
from the Q5 rather than hard-coded in Python. Digital event/timing accessories
may require additional protocol support.

## Documentation

- [Hardware and Linux setup](docs/HARDWARE_AND_LINUX.md)
- [Q5 serial protocol](docs/PROTOCOL.md)
- [Sensor descriptors and calibration](docs/SENSOR_DESCRIPTORS.md)
- [Investigation and implementation notes](docs/PROJECT_NOTES.md)

## Requirements

- Linux with the `ftdi_sio` kernel module
- Python 3.10 or newer
- A user account allowed to access serial ports (`dialout` on Debian/Ubuntu)

The reader itself has no third-party Python dependencies.

## Quick start

Clone the repository and run the one-time Linux setup:

```bash
git clone https://github.com/didzislauva/easysense-q5-linux.git
cd easysense-q5-linux
sudo ./scripts/setup-linux.sh
```

Unplug and reconnect the Q5, then log out and back in if the setup script added
you to `dialout`. Verify the device:

```bash
ls -l /dev/easysense-q5 /dev/ttyUSB*
```

Read live calibrated values. The reader detects the currently connected sensors
and downloads their calibration descriptors every time it starts:

```bash
python3 q5_reader.py
```

To save a snapshot of the descriptors for inspection or later use:

```bash
python3 q5_descriptors.py
python3 q5_reader.py --cached
```

Save one reading per second as CSV:

```bash
python3 q5_reader.py --interval 1 > readings.csv
```

Collect 100 readings at 0.2-second intervals:

```bash
python3 q5_reader.py --count 100 --interval 0.2 > readings.csv
```

Show raw 16-bit ADC values:

```bash
python3 q5_reader.py --raw
```

Stop continuous collection with `Ctrl+C`.

Both commands prefer the stable `/dev/easysense-q5` name installed by the setup
script, and fall back to `/dev/ttyUSB0`. Use `--device` to override it.

## Optional installation

Installing into a virtual environment provides short commands without adding
runtime dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
easysense-q5-descriptors
easysense-q5
```

## How it works

The Q5 identifies as USB vendor/product `0403:fe5c`. It contains an FTDI FT232B,
but that custom product ID is not present in Linux's standard `ftdi_sio` table.
The setup script installs a narrowly scoped udev rule which registers only this
ID and gives the resulting `/dev/ttyUSB*` device the normal `dialout` access.

Communication uses 38400 baud, 8 data bits, no parity, and one stop bit. A live
sample request is:

```text
41 53 00 00 00 00 00 94
```

The logger returns a checksummed frame beginning with `53 43`, followed by eight
big-endian 16-bit channel readings. Channel descriptors contain the display
precision, unit, endpoints, initial ADC value, and compressed ADC increments.
The reader applies the same piecewise-linear interpolation used by Data Harvest's
legacy software.

The complete observed packet layouts and calibration algorithm are documented in
[docs/PROTOCOL.md](docs/PROTOCOL.md) and
[docs/SENSOR_DESCRIPTORS.md](docs/SENSOR_DESCRIPTORS.md).

## Calibration data

The reader normally obtains calibration directly from the Q5 at startup, so
external sensors can be swapped without editing Python or refreshing a file.
The included `q5_descriptors.json` is an example and fallback snapshot. Run
`q5_descriptors.py` to replace it with descriptors from your current setup, then
use `q5_reader.py --cached` when a saved configuration is specifically desired.

## Troubleshooting

### No `/dev/ttyUSB0`

Run:

```bash
sudo ./scripts/setup-linux.sh
```

Then unplug and reconnect the Q5. To bind a currently connected device without
installing the persistent udev rule, use:

```bash
sudo ./scripts/initialize-device.sh
```

### Permission denied

Check membership with `groups`. On Debian/Ubuntu:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in afterward.

### Device or resource busy

Close EasySense, Wine, a serial terminal, or any other process using the port.
Only one application can open the Q5 at a time.

### The logger is not `/dev/ttyUSB0`

Pass the actual path:

```bash
python3 q5_reader.py --device /dev/ttyUSB1
```

## Tests

Tests do not require hardware:

```bash
python3 -m unittest discover -s tests -v
```

## Scope

This is an independent interoperability project for hardware that is no longer
supported by the current EasySense software. Data Harvest and EasySense are
trademarks of their respective owner. No vendor software is distributed here.

## License

MIT. See [LICENSE](LICENSE).
