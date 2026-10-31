"""Combine all two-year finite accounts without selecting a policy or source truth."""

from fractions import Fraction as F
from bounds_common import ROOT, load, read, save


def main(out):
    years = [load("results/bounds/summary_" + str(y) + ".json") for y in [2019, 2020]]
    groups = [g for y in years for g in y["groups"]]
    cases = [
        r
        for y in [2019, 2020]
        for r in read(ROOT / ("results/bounds/endpoints_" + str(y) + ".csv"))
    ]
    maximum = max(cases, key=lambda r: F(r["interval_width_kg"]))
    source = read(ROOT / "data/fao/source_projection.csv")
    save(
        out / "summary.json",
        dict(
            base_cases=480,
            endpoint_evaluations=1440,
            cut_subsets=11520,
            groups=groups,
            maximum_interval_illustration=maximum,
            source_positions=179,
            positive_source_positions=sum(r["state"] == "positive" for r in source),
            missing_source_positions=sum(r["state"] == "missing" for r in source),
            positive_imputed_positions=sum(
                r["state"] == "positive" and r["flag"] == "I" for r in source
            ),
            original_FAO_gate="FAIL_SOURCE_QUALIFICATION",
            original_coverage_gated_scenarios="UNEXECUTED",
            qualification="All capacity and outside envelopes authored; old coverage gate failed; compiled 2019/2020 source informed, not a forecast, current-risk measure or physical-supply guarantee.",
        ),
    )
    print("COMPLETE_TWO_YEAR_BOUNDS_SUMMARY", 480, 1440)


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results/bounds")
    main(p.parse_args().out)
