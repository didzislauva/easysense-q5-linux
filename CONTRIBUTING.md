# Contributing

Bug reports and tested support for other EasySense Q-series models are welcome.

Please include:

- logger model and firmware version;
- USB vendor/product IDs from `lsusb`;
- Python and Linux versions;
- whether the issue occurs with freshly downloaded descriptors;
- sanitized raw output from `python3 q5_reader.py --raw --count 10`.

Run the test suite before submitting a change:

```bash
python3 -m unittest discover -s tests -v
```

Do not commit vendor installers, Wine prefixes, or captures containing unrelated
system data.
