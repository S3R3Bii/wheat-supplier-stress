import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_inputs import collapse


def record():
    return dict(
        period="2019",
        classificationCode="H5",
        cmdCode="1001",
        reporterCode="504",
        flowCode="M",
        partnerCode="251",
        partner2Code="0",
        customsCode="C00",
        motCode="0",
        netWgt="10.00",
        net_weight_state="positive",
        net_weight_unit="kg",
        aggrLevel="4",
        native_types=json.dumps({"netWgt": "number"}),
        isNetWgtEstimated="false",
        isReported="true",
        isAggregate="false",
        isOriginalClassification="true",
        cmdDesc="Wheat and meslin",
        request_file="authored.json",
        request_kind="import_panel",
        source_row="1",
    )


class SourceKeyTests(unittest.TestCase):
    def test_identical_copies_collapse_with_both_references(self):
        a = record()
        b = a | {"source_row": "2"}
        lookup, ledger = collapse([a, b])
        self.assertEqual(len(lookup), 1)
        self.assertEqual(ledger[0]["copies"], 2)
        self.assertEqual(
            ledger[0]["source_references"], "authored.json:1;authored.json:2"
        )

    def test_conflicting_native_weight_is_unavailable(self):
        a = record()
        b = a | {"source_row": "2", "netWgt": "11"}
        lookup, ledger = collapse([a, b])
        self.assertFalse(lookup)
        self.assertEqual(ledger[0]["status"], "conflicting_copies")

    def test_other_source_content_conflict_is_not_called_identical(self):
        a = record()
        b = a | {"source_row": "2", "isNetWgtEstimated": "true"}
        lookup, ledger = collapse([a, b])
        self.assertFalse(lookup)

    def test_unknown_weight_not_zero(self):
        a = record() | {"netWgt": "null", "net_weight_state": "json_null"}
        lookup, ledger = collapse([a])
        self.assertFalse(lookup)
        self.assertEqual(ledger[0]["status"], "json_null")

    def test_wrong_mass_unit_is_unavailable(self):
        lookup, ledger = collapse([record() | {"net_weight_unit": "tonnes"}])
        self.assertFalse(lookup)
        self.assertEqual(ledger[0]["status"], "unsupported_identity_or_unit")

    def test_wrong_commodity_not_mixed_with_wheat(self):
        lookup, ledger = collapse([record() | {"cmdCode": "1005"}])
        self.assertFalse(lookup)

    def test_source_type_is_not_overridden_by_positive_label(self):
        lookup, ledger = collapse(
            [record() | {"native_types": json.dumps({"netWgt": "string"})}]
        )
        self.assertFalse(lookup)
        self.assertEqual(ledger[0]["status"], "invalid_source_weight")

    def test_multiple_native_editions_are_not_averaged(self):
        a = record()
        b = a | {"classificationCode": "H4", "source_row": "2"}
        lookup, ledger = collapse([a, b])
        self.assertFalse(lookup)
        self.assertTrue(
            all(
                r["coarse_lookup_status"] == "multiple_native_versions_unavailable"
                for r in ledger
            )
        )


if __name__ == "__main__":
    unittest.main()
