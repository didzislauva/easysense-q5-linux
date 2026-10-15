# Hardware and Linux Setup

## Identified logger

The tested unit identifies itself over USB as:

```text
idVendor  = 0403
idProduct = fe5c
Product   = EasySense Q
Maker     = Data Harvest Group Ltd
USB speed = full speed
```

It uses an FTDI FT232B USB-to-serial interface. Linux has the `ftdi_sio` driver,
but the Q5's custom product ID is not normally included in the driver's built-in
device table. Without registering that ID, the USB device can appear in `lsusb`
without producing `/dev/ttyUSB0`.

## Driver initialization

For a one-time binding of a currently connected logger:

```bash
sudo ./scripts/initialize-device.sh
```

The script loads `ftdi_sio` and registers `0403 fe5c` through:

```text
/sys/bus/usb-serial/drivers/ftdi_sio/new_id
```

For persistent setup:

```bash
sudo ./scripts/setup-linux.sh
```

That command installs:

- a narrowly scoped udev rule for USB ID `0403:fe5c`;
- a small driver-binding helper;
- `dialout` group access with mode `0660`;
- the stable symlink `/dev/easysense-q5`.

It also adds the invoking user to `dialout` when that group exists. Group changes
normally require logging out and back in.

## Serial configuration

The working serial settings are:

```text
Baud:       38400
Data bits:  8
Parity:     none
Stop bits:  1
Flow:       none
```

The Python implementation configures the port directly through `termios` and has
no `pyserial` dependency.

## Device selection

The commands prefer `/dev/easysense-q5` when the udev rule has created it, then
fall back to `/dev/ttyUSB0`. Override the selection when needed:

```bash
python3 q5_reader.py --device /dev/ttyUSB1
```

Only one application can hold the serial port. Close the legacy EasySense
application, Wine, serial terminals, and other readers before running Python.

## Legacy software investigation

The discontinued Windows EasySense application was successfully run through
Wine with the logger exposed as `COM1`. It confirmed that the Q5 and sensors were
working and provided reference physical readings. The vendor application and
installer are not part of this repository.

The native Python implementation was then developed so Wine and the old software
are not required for ordinary acquisition.

## Measurements observed during development

The tested Q5 reported approximately:

| Channel | Typical reading |
|---|---:|
| External temperature, input 1 | 22.9–23.1 °C |
| Built-in sound | 40–49 dBA, changing with keyboard noise |
| Built-in light | about 594 lx in the initial test |
| Internal temperature | about 23.0 °C |
| Pressure | about 102.9 kPa |
| Humidity | about 42.4 %RH |

These are observations, not reference calibration standards.
