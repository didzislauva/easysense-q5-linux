# Sensor Descriptors and Calibration

## Where sensor definitions live

The Python project does not contain a catalogue mapping sensor product names to
conversion formulas. For compatible analogue SmartQ sensors, the Q5 returns the
active sensor descriptor, including its physical units and calibration curve.

The practical data flow is:

```text
SmartQ sensor -> Q5 descriptor response -> Python decoder
raw Q5 channel word + decoded curve -> physical value
```

Built-in sensor descriptors are supplied by the logger. External SmartQ probes
identify themselves to the Q5. A selected multi-range sensor exposes the
descriptor for its currently selected range.

`q5_descriptors.json` is only a cached capture. It is not the source of sensor
identity and is not required during normal automatic detection.

## Binary layout

A descriptor is mixed binary and text. Only the sensor name and unit fields are
text. The currently decoded layout is:

| Offset | Size | Encoding | Meaning |
|---:|---:|---|---|
| 0 | 2 | bytes | Response marker `53 00` |
| 2 | 2 | little-endian | Declared response length |
| 4 | 1 | integer | Display decimal places |
| 5 | 1 | integer | Number of calibration points |
| 6 | 1 | integer | ADC-increment encoding |
| 7 | 4 | big-endian IEEE-754 | First physical value |
| 11 | 4 | big-endian IEEE-754 | Last physical value |
| 15 | 2 | big-endian | First ADC knot |
| 17 | variable | encoded integers | Remaining ADC-knot increments |
| variable | variable | Latin-1, CR terminated | Sensor name |
| variable | variable | Latin-1, CR terminated | Units |
| variable | variable | binary | Additional metadata not yet interpreted |
| final | 1 | integer | Additive checksum |

The number of increments is one less than the calibration-point count. Encoding
values observed and supported by the decoder are:

- `1`: one big-endian 16-bit value per increment;
- `2`: one 8-bit value per increment;
- `4`: two 4-bit increments packed into each byte.

The ADC knots are reconstructed cumulatively from `first_adc` and the increment
list.

## Piecewise-linear conversion

For `N` ADC increments there are `N + 1` knots and `N` equal physical-value
segments. The physical step is:

```text
step = (last_value - first_value) / N
```

For a raw ADC word between two adjacent ADC knots, the reader linearly
interpolates within that segment. Values below the first knot clamp to
`first_value`; values above the last knot clamp to `last_value`.

This supports both simple two-point linear sensors and nonlinear sensors with
many ADC segments. The external and internal temperature descriptors observed
during development use nonlinear tables; several other channels use two points.

## Fully decoded sound example

The built-in sound descriptor contained:

```text
53 00 20 00 01 02 01
42 20 00 00
42 dc 00 00
31 20
b3 60
53 6f 75 6e 64 0d
64 42 41 0d
00 c8 06
33
```

The relevant fields decode to:

```text
Name:          Sound
Units:         dBA
Decimals:      1
Physical span: 40.0 to 110.0
First ADC:     12576
Last ADC:      58496
Points:        2
```

Printable-character scans of a whole descriptor can show garbage because binary
floats and ADC data sometimes happen to be printable bytes. The `ascii_fields`
property in the JSON capture is diagnostic only. `parse_calibration()` locates
the real text fields after decoding the variable-length increment table.

## External sensor experiment

An unknown probe was connected to input 1 and identified entirely through its
descriptor as:

```text
Name:          Sound
Units:         mV
Decimals:      0
Physical span: -2000 to 2000 mV
First ADC:     816
Last ADC:      64816
Points:        2
```

Live values near silence were approximately `1–5 mV`. In the same sample stream,
the Q5's separate built-in sound channel continued to report `40–49 dBA`. This
demonstrated that the decoder can distinguish two channels with the same sensor
name but different units, ranges, and calibration.

For this two-point table, the 64,000-count ADC span represents a 4,000 mV span,
so ADC `32896` converts to approximately `5 mV`.

## Swapping sensors

Normal use requires no descriptor-file refresh:

```bash
python3 q5_reader.py
```

The reader detects current sensors at every startup. A changed input should
therefore acquire its new name, units, range, precision, and calibration without
Python changes.

To deliberately use the bundled or previously captured snapshot:

```bash
python3 q5_reader.py --cached
```

To capture the current descriptor packets for examination:

```bash
python3 q5_descriptors.py --output q5_descriptors.json
```

## Limitations

A descriptor is sufficient for standard calibrated analogue readings that use
this format. It is not proof that every SmartQ accessory follows the analogue
sample model. Digital switches, light gates, timing mats, counters, or sensors
with special acquisition requirements may need additional commands and logic.

Heart-rate measurements are educational sensor data and must not be treated as
medical diagnosis.
