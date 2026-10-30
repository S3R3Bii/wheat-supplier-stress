"""Independently confirm the source hold; a correct diagnosis is not a passed source gate."""

import csv
import hashlib
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = list(
        csv.DictReader(
            (ROOT / "data/trade_rows.csv").open(encoding="utf-8", newline="")
        )
    )
    db = sqlite3.connect(":memory:")
    fields = list(raw[0])
    db.execute("CREATE TABLE q(" + ",".join('"' + k + '" TEXT' for k in fields) + ")")
    db.executemany(
        "INSERT INTO q VALUES (" + ",".join("?" for k in fields) + ")",
        [[r[k] for k in fields] for r in raw],
    )
    db.row_factory = sqlite3.Row
    network = json.loads(
        (ROOT / "data/planned_network.json").read_text(encoding="utf-8")
    )
    importers = sorted(network["importers"], key=int)
    origins = sorted(network["origins"], key=int)
    checks = 0
    lookup = {}
    groups = defaultdict(list)
    for record in db.execute("SELECT * FROM q ORDER BY rowid"):
        native_types = json.loads(record["native_types"])
        if native_types["netWgt"] != "number":
            continue
        quantity = Decimal(record["netWgt"])
        if not quantity.is_finite() or quantity <= 0:
            continue
        assert (
            record["net_weight_unit"] == "kg"
            and record["cmdCode"] == "1001"
            and record["aggrLevel"] == "4"
        )
        checks += 3
        groups[
            (
                record["period"],
                record["reporterCode"],
                record["flowCode"],
                record["partnerCode"],
            )
        ].append(dict(record))
    for key, copies in groups.items():
        assert (
            len(copies) == 1
        ), "Actual cohort has no key copies; diagnose any new ambiguity before proceeding"
        lookup[key] = copies[0]
        checks += 1

    def get(year, reporter, flow, partner):
        return lookup.get((str(year), str(reporter), flow, str(partner)))

    failures = []
    for year in [2018, 2019, 2020]:
        for importer in importers:
            if get(year, importer, "M", "0") is None:
                failures.append(f"world_import_unavailable:{year}:{importer}")
            checks += 1
    for year in [2018, 2019]:
        for origin in origins:
            if get(year, origin, "X", "0") is None:
                failures.append(f"prior_world_export_unavailable:{year}:{origin}")
            checks += 1
    coverage = {
        (r["year"], r["importer"]): r
        for r in csv.DictReader(
            (ROOT / "data/common_support.csv").open(encoding="utf-8", newline="")
        )
    }
    prior_coverage = {
        (r["year"], r["importer"]): r
        for r in csv.DictReader(
            (ROOT / "data/prior_route_coverage.csv").open(encoding="utf-8", newline="")
        )
    }
    details = []
    for year in [2019, 2020]:
        for importer in importers:
            pairs = [
                (get(year, importer, "M", o), get(year, o, "X", importer))
                for o in origins
            ]
            common = [a for a, b in pairs if a is not None and b is not None]
            world = get(year, importer, "M", "0")
            mass = sum((Fraction(r["netWgt"]) for r in common), Fraction())
            share = None if world is None else mass / Fraction(world["netWgt"])
            previous = sum(get(year - 1, importer, "M", o) is not None for o in origins)
            gate = (
                share is not None
                and Fraction(4, 5) <= share <= Fraction(21, 20)
                and len(common) >= 2
            )
            if not gate:
                failures.append(f"common_support_gate:{year}:{importer}")
            if previous < 2:
                failures.append(f"prior_link_gate:{year}:{importer}")
            row = coverage[str(year), importer]
            assert (
                row["common_import_kg"] == str(mass)
                and row["common_source_share"] == ("" if share is None else str(share))
                and row["common_origins"] == str(len(common))
                and row["gate"] == ("pass" if gate else "fail")
            )
            checks += 4
            assert prior_coverage[str(year), importer]["valid_prior_origins"] == str(
                previous
            )
            checks += 1
            details.append(
                dict(
                    year=year,
                    importer=importer,
                    world_weight_available=world is not None,
                    common_share_exact="" if share is None else str(share),
                    common_origins=len(common),
                    prior_origins=previous,
                    gate="pass" if gate else "fail",
                )
            )
    original = json.loads(
        (ROOT / "data/input_receipt.json").read_text(encoding="utf-8")
    )
    assert (
        failures == original["failures"]
        and original["status"] == "source_hold_do_not_score"
        and failures
    )
    checks += 3
    result = dict(
        check_status="pass_independent_reconstruction",
        source_gate="fail",
        status="CONFIRMED_SOURCE_HOLD_NOT_EXECUTED_STUDY",
        checks=checks,
        source_records=len(raw),
        failures=failures,
        common_support=details,
        source_projection_sha256=hashlib.sha256(
            (ROOT / "data/trade_rows.csv").read_bytes()
        ).hexdigest(),
        scenario_scores_run=False,
        scope="Original UN quantity/common-support criteria fail; no missing-to-zero coercion, selected-country replacement or threshold relaxation",
    )
    (ROOT / "data/input_gate_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
