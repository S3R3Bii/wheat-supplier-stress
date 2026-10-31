"""Qualify a fixed common-support flow panel before any capacity scenario."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = [
    "period",
    "classificationCode",
    "cmdCode",
    "reporterCode",
    "flowCode",
    "partnerCode",
    "partner2Code",
    "customsCode",
    "motCode",
]


def write_csv(path, rows, fields=None):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields or list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def collapse(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in KEY)].append(row)
    lookup = defaultdict(list)
    ledger = []
    for key, copies in sorted(groups.items()):
        signatures = {
            tuple(
                (name, r[name])
                for name in sorted(r)
                if name not in {"request_file", "request_kind", "source_row"}
            )
            for r in copies
        }
        status = (
            "conflicting_copies"
            if len(signatures) > 1
            else copies[0]["net_weight_state"]
        )
        first = copies[0]
        if status == "positive":
            if (
                first["net_weight_unit"] != "kg"
                or first["cmdCode"] != "1001"
                or first["aggrLevel"] != "4"
            ):
                status = "unsupported_identity_or_unit"
            else:
                try:
                    assert (
                        json.loads(first["native_types"])["netWgt"] == "number"
                        and Fraction(first["netWgt"]) > 0
                    )
                    status = "eligible"
                except (ValueError, ZeroDivisionError, KeyError, AssertionError):
                    status = "invalid_source_weight"
        ledger.append(
            dict(zip(KEY, key))
            | dict(
                copies=len(copies),
                source_references=";".join(
                    r["request_file"] + ":" + r["source_row"] for r in copies
                ),
                status=status,
            )
        )
        if status == "eligible":
            lookup[
                (key[0], first["reporterCode"], first["flowCode"], first["partnerCode"])
            ].append(first)
    for record in ledger:
        key = (
            record["period"],
            record["reporterCode"],
            record["flowCode"],
            record["partnerCode"],
        )
        record["coarse_lookup_status"] = (
            "multiple_native_versions_unavailable"
            if record["status"] == "eligible" and len(lookup[key]) > 1
            else record["status"]
        )
    return {
        key: values[0] for key, values in lookup.items() if len(values) == 1
    }, ledger


def main():
    network = json.loads(
        (ROOT / "data/planned_network.json").read_text(encoding="utf-8")
    )
    importers = sorted(network["importers"], key=int)
    origins = sorted(network["origins"], key=int)
    raw = list(
        csv.DictReader(
            (ROOT / "data/trade_rows.csv").open(encoding="utf-8", newline="")
        )
    )
    lookup, keys = collapse(raw)
    world = []
    prior = []
    current = []
    coverage = []
    prior_coverage = []
    bilateral = []
    failures = []

    def row(year, reporter, flow, partner):
        return lookup.get((str(year), str(reporter), flow, str(partner)))

    def value(record):
        return "" if record is None else record["netWgt"]

    def state(record):
        return "unavailable_not_zero" if record is None else "positive_source"

    for year in [2018, 2019, 2020]:
        for importer in importers:
            r = row(year, importer, "M", "0")
            world.append(
                dict(
                    year=year,
                    importer=importer,
                    world_import_kg=value(r),
                    state=state(r),
                    estimated="unknown" if r is None else r["isNetWgtEstimated"],
                )
            )
            if r is None:
                failures.append(f"world_import_unavailable:{year}:{importer}")
    for year in [2018, 2019]:
        for origin in origins:
            r = row(year, origin, "X", "0")
            prior.append(
                dict(
                    prior_year=year,
                    origin=origin,
                    world_export_kg=value(r),
                    state=state(r),
                    estimated="unknown" if r is None else r["isNetWgtEstimated"],
                )
            )
            if r is None:
                failures.append(f"prior_world_export_unavailable:{year}:{origin}")
    for year in [2019, 2020]:
        for importer in importers:
            common_mass = Fraction()
            common_origins = 0
            prior_origins = 0
            estimated_mass = Fraction()
            observed_candidate_mass = Fraction()
            unpaired_mass = Fraction()
            for origin in origins:
                imported = row(year, importer, "M", origin)
                mirror = row(year, origin, "X", importer)
                history = row(year - 1, importer, "M", origin)
                common = imported is not None and mirror is not None
                prior_valid = history is not None
                if prior_valid:
                    prior_origins += 1
                if imported is not None:
                    observed_candidate_mass += Fraction(imported["netWgt"])
                if common:
                    common_origins += 1
                    common_mass += Fraction(imported["netWgt"])
                    if imported["isNetWgtEstimated"] == "true":
                        estimated_mass += Fraction(imported["netWgt"])
                elif imported is not None:
                    unpaired_mass += Fraction(imported["netWgt"])
                current.append(
                    dict(
                        year=year,
                        importer=importer,
                        origin=origin,
                        common_support=str(common).lower(),
                        import_kg=value(imported),
                        mirror_export_kg=value(mirror),
                        prior_import_kg=value(history),
                        prior_route_available=str(prior_valid).lower(),
                        import_estimated=(
                            "unknown"
                            if imported is None
                            else imported["isNetWgtEstimated"]
                        ),
                        mirror_estimated=(
                            "unknown" if mirror is None else mirror["isNetWgtEstimated"]
                        ),
                        prior_estimated=(
                            "unknown"
                            if history is None
                            else history["isNetWgtEstimated"]
                        ),
                        support_reason=(
                            "common_positive"
                            if common
                            else (
                                "import_unavailable"
                                if imported is None
                                else "mirror_unavailable"
                            )
                        ),
                    )
                )
                bilateral.append(
                    dict(
                        year=year,
                        importer=importer,
                        origin=origin,
                        import_state=state(imported),
                        mirror_state=state(mirror),
                        prior_state=state(history),
                        common_support=str(common).lower(),
                        mirror_minus_import_kg=(
                            ""
                            if not common
                            else str(
                                Fraction(mirror["netWgt"])
                                - Fraction(imported["netWgt"])
                            )
                        ),
                        mirror_to_import_ratio=(
                            ""
                            if not common
                            else str(
                                Fraction(mirror["netWgt"])
                                / Fraction(imported["netWgt"])
                            )
                        ),
                    )
                )
            world_row = row(year, importer, "M", "0")
            world_value = None if world_row is None else Fraction(world_row["netWgt"])
            share = None if world_value is None else common_mass / world_value
            gate = (
                share is not None
                and Fraction(4, 5) <= share <= Fraction(21, 20)
                and common_origins >= 2
            )
            if not gate:
                failures.append(f"common_support_gate:{year}:{importer}")
            if prior_origins < 2:
                failures.append(f"prior_link_gate:{year}:{importer}")
            coverage.append(
                dict(
                    year=year,
                    importer=importer,
                    world_import_kg="" if world_value is None else str(world_value),
                    common_import_kg=str(common_mass),
                    common_source_share="" if share is None else str(share),
                    common_origins=common_origins,
                    observed_candidate_import_kg=str(observed_candidate_mass),
                    known_import_without_positive_mirror_kg=str(unpaired_mass),
                    world_minus_common_kg=(
                        "" if world_value is None else str(world_value - common_mass)
                    ),
                    estimated_common_import_kg=str(estimated_mass),
                    gate="pass" if gate else "fail",
                    minimum_share="4/5",
                    maximum_share="21/20",
                    minimum_common_origins=2,
                )
            )
            prior_coverage.append(
                dict(
                    year=year,
                    prior_year=year - 1,
                    importer=importer,
                    valid_prior_origins=prior_origins,
                    minimum_prior_origins=2,
                    gate="pass" if prior_origins >= 2 else "fail",
                )
            )
    for name, rows in [
        ("source_key_ledger.csv", keys),
        ("world_imports.csv", world),
        ("prior_world_exports.csv", prior),
        ("network_inputs.csv", current),
        ("common_support.csv", coverage),
        ("prior_route_coverage.csv", prior_coverage),
        ("bilateral_support.csv", bilateral),
    ]:
        write_csv(ROOT / "data" / name, rows)
    receipt = dict(
        status="pass" if not failures else "source_hold_do_not_score",
        source_records=len(raw),
        native_key_groups=len(keys),
        identical_extra_copies=sum(
            int(r["copies"]) - 1 for r in keys if r["status"] == "eligible"
        ),
        conflicting_native_keys=sum(r["status"] == "conflicting_copies" for r in keys),
        fixed_importers=len(importers),
        fixed_origins=len(origins),
        target_years=[2019, 2020],
        common_support_groups=6,
        failures=failures,
        scope="Positive native net weight and common reported support only; absence not confirmed zero; additional capacity remains authored separately",
        sha256={
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "data").glob("*.csv"))
        },
    )
    (ROOT / "data/input_receipt.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt, indent=2))
    assert (
        not failures
    ), "Fixed source/common-support gate failed; preserve hold without scoring or changing cohort/gates"


if __name__ == "__main__":
    main()
