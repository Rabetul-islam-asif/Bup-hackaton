import copy
import unittest

from check_nvidia_model import ValidationError, validate_interpretations


VALID_SOLAR = {
    "directive_interpretation": [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [11, 12, 13], "factor": 0.2},
            "explanation": "An 80 percent reduction leaves 20 percent usable solar.",
        }
    ]
}


class ValidatorTests(unittest.TestCase):
    def validate(self, value):
        return validate_interpretations(value, note_count=1, battery_capacity=200)

    def test_accepts_valid_directive(self):
        self.assertEqual(self.validate(copy.deepcopy(VALID_SOLAR))[0]["note_index"], 0)

    def test_rejects_unsupported_directive(self):
        value = copy.deepcopy(VALID_SOLAR)
        value["directive_interpretation"][0]["directive_type"] = "turn_off_building"
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_wrong_note_index(self):
        value = copy.deepcopy(VALID_SOLAR)
        value["directive_interpretation"][0]["note_index"] = 1
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_invalid_factor(self):
        value = copy.deepcopy(VALID_SOLAR)
        value["directive_interpretation"][0]["structured_adjustment"]["factor"] = 1.2
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_duplicate_or_unsorted_hours(self):
        for hours in ([11, 11], [12, 11]):
            with self.subTest(hours=hours):
                value = copy.deepcopy(VALID_SOLAR)
                value["directive_interpretation"][0]["structured_adjustment"]["hours"] = hours
                with self.assertRaises(ValidationError):
                    self.validate(value)

    def test_rejects_false_for_active_directive(self):
        value = copy.deepcopy(VALID_SOLAR)
        value["directive_interpretation"][0]["applies"] = False
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_bad_no_op_semantics(self):
        value = copy.deepcopy(VALID_SOLAR)
        entry = value["directive_interpretation"][0]
        entry["directive_type"] = "no_op"
        entry["structured_adjustment"] = None
        entry["applies"] = True
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_reserve_above_capacity(self):
        value = copy.deepcopy(VALID_SOLAR)
        entry = value["directive_interpretation"][0]
        entry["directive_type"] = "minimum_battery_reserve"
        entry["structured_adjustment"] = {
            "hours": [18, 19],
            "minimum_energy_kwh": 201,
        }
        with self.assertRaises(ValidationError):
            self.validate(value)

    def test_rejects_extra_fields(self):
        value = copy.deepcopy(VALID_SOLAR)
        value["directive_interpretation"][0]["confidence"] = 0.9
        with self.assertRaises(ValidationError):
            self.validate(value)


if __name__ == "__main__":
    unittest.main()

