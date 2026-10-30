"""Independently reconcile every projected field and original numeric lexeme."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    projection = list(
        csv.DictReader(
            (ROOT / "data/trade_rows.csv").open(encoding="utf-8", newline="")
        )
    )
    receipt = json.loads(
        (ROOT / "data/source_receipt.json").read_text(encoding="utf-8")
    )
    requests = json.loads(
        (ROOT / "data/source_requests.json").read_text(encoding="utf-8")
    )
    capture = json.loads(
        (args.private_dir / "requests.json").read_text(encoding="utf-8")
    )
    by_url = {r["url"]: r for r in capture}
    checks = 0
    seen = []
    source_rows = 0
    states = Counter()
    for request in requests:
        metadata = by_url[request["url"]]
        path = args.private_dir / metadata["file"]
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        assert digest == metadata["sha256"]
        checks += 1
        parsed = json.loads(body, parse_float=Decimal)
        records = parsed["data"]
        assert parsed["count"] == len(records) < 500 and parsed.get("error") == ""
        checks += 2
        rows = [r for r in projection if r["request_file"] == request["file"]]
        assert len(rows) == len(records)
        checks += 1
        raw_tokens = re.findall(rb'"netWgt"\s*:\s*([^,\}\s]+)', body)
        assert len(raw_tokens) == len(records)
        checks += 1
        for index, (native, row, token) in enumerate(
            zip(records, rows, raw_tokens, strict=True), 1
        ):
            assert (
                row["source_row"] == str(index)
                and row["request_kind"] == request["kind"]
            )
            checks += 2
            types = json.loads(row["native_types"])
            for name, kind in types.items():
                if name not in native:
                    assert kind == "absent" and row[name] == ""
                    checks += 2
                    continue
                value = native[name]
                if value is None:
                    expected_kind = "null"
                    expected = "null"
                elif isinstance(value, bool):
                    expected_kind = "boolean"
                    expected = "true" if value else "false"
                elif isinstance(value, (int, Decimal)):
                    expected_kind = "number"
                    expected = None
                else:
                    assert isinstance(value, str)
                    expected_kind = "string"
                    expected = value
                assert kind == expected_kind
                checks += 1
                if expected is None:
                    assert Decimal(row[name]) == Decimal(value)
                    checks += 1
                else:
                    assert row[name] == expected
                    checks += 1
            lexical = token.decode("ascii")
            assert row["netWgt"] == lexical
            checks += 1
            weight = native.get("netWgt")
            state = (
                "json_null"
                if weight is None
                else (
                    "non_numeric_source_type"
                    if isinstance(weight, (bool, str))
                    else (
                        "positive"
                        if weight > 0
                        else "zero_unavailable" if weight == 0 else "negative_invalid"
                    )
                )
            )
            assert state == row["net_weight_state"] and row["net_weight_unit"] == "kg"
            checks += 2
            states[state] += 1
            assert (
                native["typeCode"] == "C"
                and native["freqCode"] == "A"
                and int(native["period"]) == native["refYear"] == request["year"]
            )
            checks += 3
            assert (
                native["reporterCode"] == request["reporter"]
                and native["flowCode"] == request["flow"]
                and native["partnerCode"] in request["partners"]
            )
            checks += 3
            assert (
                native["cmdCode"] == "1001"
                and native["cmdDesc"].strip().casefold().rstrip(".")
                == "wheat and meslin"
                and native["aggrLevel"] == 4
                and native["partner2Code"] == 0
                and native["customsCode"] == "C00"
                and native["motCode"] == 0
            )
            checks += 6
            seen.append((request["file"], str(index)))
            source_rows += 1
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        checks += 1
    assert (
        len(seen)
        == len(set(seen))
        == len(projection)
        == receipt["records"]
        == source_rows
        < 10000
        and len(requests) == len(capture) == 49
    )
    checks += 3
    assert (
        dict(states) == receipt["net_weight_states"]
        and hashlib.sha256((ROOT / "data/trade_rows.csv").read_bytes()).hexdigest()
        == receipt["projection_sha256"]
    )
    checks += 2
    result = dict(
        status="pass",
        checks=checks,
        source_records=source_rows,
        source_requests=49,
        net_weight_states=dict(states),
        readers=[
            "Independent Decimal JSON parser",
            "Separate raw numeric-token extraction",
            "Original byte hashes before/after reads",
        ],
        scope="Full projected native fields reconciled; source observations/estimates and authored capacity remain distinct",
    )
    (ROOT / "data/source_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
