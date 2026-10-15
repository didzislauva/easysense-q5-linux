import json
from pathlib import Path
import struct
import unittest

import q5_reader


ROOT = Path(__file__).resolve().parents[1]


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibrations = q5_reader.load_calibrations(ROOT / "q5_descriptors.json")

    def test_expected_sensor_names(self):
        names = [cal.name if cal else None for cal in self.calibrations]
        self.assertEqual(
            names,
            ["Temperature", None, "Sound", "Light", "Temperature", "Pressure", "Humidity", None],
        )

    def test_reference_values(self):
        references = {
            0: (20416, 22.5),
            2: (17562, 47.6),
            3: (14512, 888.0),
            4: (35072, 23.4),
            5: (59968, 102.9),
            6: (18608, 41.0),
        }
        for channel, (raw, expected) in references.items():
            calibration = self.calibrations[channel]
            self.assertIsNotNone(calibration)
            self.assertAlmostEqual(calibration.convert(raw), expected, delta=0.6)

    def test_calibration_clamps_outside_table(self):
        calibration = self.calibrations[3]
        self.assertEqual(calibration.convert(0), calibration.first_value)
        self.assertEqual(calibration.convert(65535), calibration.last_value)

    def test_default_calibration_file_exists(self):
        self.assertTrue(q5_reader.default_calibration_path().is_file())

    def test_external_sensor_name_is_not_hard_coded(self):
        calibration = q5_reader.Calibration(
            name="Heart Rate",
            units="bpm",
            decimal_places=0,
            first_value=0,
            last_value=200,
            first_adc=0,
            adc_increments=(65535,),
        )
        self.assertEqual(q5_reader.display_name(0, calibration), "Input 1 Heart Rate")
        self.assertEqual(q5_reader.display_name(1, calibration), "Input 2 Heart Rate")


class ProtocolTests(unittest.TestCase):
    def test_sample_request_checksum(self):
        request = q5_reader.SAMPLE_REQUEST
        self.assertEqual(sum(request[:-1]) & 0xFF, request[-1])

    def test_big_endian_channel_words(self):
        payload = bytes.fromhex("4f c0 99 00 18 80 38 c0 89 00 ea 40 49 00 da 80")
        self.assertEqual(
            struct.unpack(">8H", payload),
            (20416, 39168, 6272, 14528, 35072, 59968, 18688, 55936),
        )

    def test_live_detection_uses_returned_sensor_identity(self):
        records = json.loads((ROOT / "q5_descriptors.json").read_text())
        frames = [bytes.fromhex(record["response_hex"]) for record in records[:7]]

        def query(_fd, channel, _timeout):
            return frames[channel]

        calibrations = q5_reader.detect_calibrations(0, 1.0, query)
        self.assertEqual(calibrations[0].name, "Temperature")
        self.assertIsNone(calibrations[1])
        self.assertEqual(calibrations[6].units, "%RH")


if __name__ == "__main__":
    unittest.main()
