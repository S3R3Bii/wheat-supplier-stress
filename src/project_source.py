"""Project a minimal attributed trade snapshot without binary conversion of numeric tokens."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = [
    "typeCode",
    "freqCode",
    "period",
    "refYear",
    "reporterCode",
    "reporterISO",
    "reporterDesc",
    "flowCode",
    "partnerCode",
    "partnerISO",
    "partnerDesc",
    "partner2Code",
    "classificationCode",
    "classificationSearchCode",
    "isOriginalClassification",
    "cmdCode",
    "cmdDesc",
    "aggrLevel",
    "isLeaf",
    "customsCode",
    "motCode",
    "isReported",
    "isAggregate",
    "netWgt",
    "isNetWgtEstimated",
    "qty",
    "qtyUnitCode",
    "qtyUnitAbbr",
    "isQtyEstimated",
]


class Number(str):
    """Keep the original JSON numeric spelling as a distinct scalar type."""


def native_type(value):
    if isinstance(value, Number):
        return "number"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    raise TypeError("Unexpected non-scalar source field")


def scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def weight_state(value, present=True):
    if not present:
        return "absent"
    if value is None:
        return "json_null"
    if not isinstance(value, Number):
        return "non_numeric_source_type"
    try:
        value = Fraction(value)
        return (
            "positive"
            if value > 0
            else "zero_unavailable" if value == 0 else "negative_invalid"
        )
    except (ValueError, ZeroDivisionError):
        return "invalid_numeric_token"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    planned = json.loads(
        (ROOT / "data/source_requests.json").read_text(encoding="utf-8")
    )
    captures = json.loads(
        (args.private_dir / "requests.json").read_text(encoding="utf-8")
    )
    assert len(planned) == len(captures) == 49
    by_url = {r["url"]: r for r in captures}
    assert len(by_url) == 49 and set(by_url) == {r["url"] for r in planned}
    output = []
    receipts = []
    all_states = Counter()
    total = 0
    for request in planned:
        capture = by_url[request["url"]]
        assert capture["status"] == 200 and capture["error"] is None
        path = args.private_dir / capture["file"]
        body = path.read_bytes()
        assert hashlib.sha256(body).hexdigest() == capture["sha256"]
        envelope = json.loads(body, parse_float=Number, parse_int=Number)
        data = envelope["data"]
        assert not envelope.get("error") and int(envelope["count"]) == len(data) < 500
        total += len(data)
        assert total < 10000
        states = Counter()
        for index, record in enumerate(data, 1):
            assert record["typeCode"] == "C" and record["freqCode"] == "A"
            assert (
                str(record["period"]) == str(record["refYear"]) == str(request["year"])
            )
            assert (
                int(record["reporterCode"]) == request["reporter"]
                and record["flowCode"] == request["flow"]
                and int(record["partnerCode"]) in request["partners"]
            )
            assert (
                record["cmdCode"] == "1001"
                and record["cmdDesc"].strip().casefold().rstrip(".")
                == "wheat and meslin"
                and int(record["aggrLevel"]) == 4
            )
            assert (
                int(record["partner2Code"]) == 0
                and record["customsCode"] == "C00"
                and int(record["motCode"]) == 0
            )
            row = dict(
                request_file=request["file"],
                request_kind=request["kind"],
                source_row=str(index),
            )
            row.update({k: scalar(record[k]) if k in record else "" for k in NATIVE})
            row["native_types"] = json.dumps(
                {
                    k: native_type(record[k]) if k in record else "absent"
                    for k in NATIVE
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            row["net_weight_unit"] = "kg"
            row["net_weight_state"] = weight_state(
                record.get("netWgt"), "netWgt" in record
            )
            output.append(row)
            states[row["net_weight_state"]] += 1
            all_states[row["net_weight_state"]] += 1
        receipts.append(
            {
                k: capture[k]
                for k in [
                    "kind",
                    "year",
                    "reporter",
                    "flow",
                    "partners",
                    "file",
                    "url",
                    "started_utc",
                    "completed_utc",
                    "status",
                    "bytes",
                    "sha256",
                    "protocol_commit",
                    "python",
                ]
            }
            | {
                "records": len(data),
                "net_weight_states": dict(states),
                "inherited_original": bool(
                    capture.get("inherited_unchanged_identifier_request")
                    or capture.get("inherited_successful_original_no_refetch")
                ),
            }
        )
        assert hashlib.sha256(path.read_bytes()).hexdigest() == capture["sha256"]
    assert output
    target = ROOT / "data/trade_rows.csv"
    assert not target.exists()
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    receipt = dict(
        source="UN Comtrade public preview, original HS 1001 country-level annual flow records",
        source_requests=receipts,
        records=total,
        record_bound=10000,
        source_unit="netWgt kg; zero/null/unreported weight unavailable",
        net_weight_states=dict(all_states),
        projection_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        scope="Minimal attributed factual projection under the bounded-record rule; raw responses and unrelated fields excluded; new capacities/scenarios are authored separately",
    )
    (ROOT / "data/source_receipt.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(
        json.dumps(
            {
                "status": "projection_created_not_qualified",
                "records": total,
                "states": dict(all_states),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
