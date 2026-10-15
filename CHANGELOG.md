# Changelog

## 0.1.0 - 2026-10-15

- Add native 38400-baud Q5 protocol reader.
- Validate sample and descriptor checksums.
- Download factory calibration descriptors from the logger.
- Reproduce the vendor's piecewise-linear calibration algorithm.
- Add CSV output, raw ADC mode, Linux setup scripts, tests, and documentation.
- Detect current external sensors and calibration descriptors at reader startup.
- Retry removable inputs briefly while newly connected SmartQ sensors initialize.
- Use descriptor-provided names and units instead of assuming input 1 is temperature.
