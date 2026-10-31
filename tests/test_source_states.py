import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_source import Number, native_type, weight_state


class NativeQuantityTests(unittest.TestCase):
    def test_zero_is_unavailable_not_confirmed_no_trade(self):
        self.assertEqual(weight_state(Number("0.0")), "zero_unavailable")

    def test_null_state_is_preserved(self):
        self.assertEqual(weight_state(None), "json_null")

    def test_absence_is_distinct_from_null(self):
        self.assertEqual(weight_state(None, False), "absent")

    def test_negative_weight_is_invalid(self):
        self.assertEqual(weight_state(Number("-1")), "negative_invalid")

    def test_numeric_string_is_not_a_native_json_number(self):
        self.assertEqual(weight_state("123"), "non_numeric_source_type")

    def test_boolean_is_not_a_weight(self):
        self.assertEqual(weight_state(True), "non_numeric_source_type")

    def test_small_positive_native_decimal_is_not_rounded_to_zero(self):
        self.assertEqual(weight_state(Number("1e-20")), "positive")

    def test_native_numeric_lexeme_is_retained(self):
        value = json.loads('{"netWgt":123456789.0012300}', parse_float=Number)["netWgt"]
        self.assertEqual(str(value), "123456789.0012300")
        self.assertEqual(Fraction(value), Fraction("123456789.0012300"))

    def test_json_types_are_not_silently_coerced(self):
        self.assertEqual(
            [native_type(v) for v in [Number("8"), "8", None, False]],
            ["number", "string", "null", "boolean"],
        )


if __name__ == "__main__":
    unittest.main()
