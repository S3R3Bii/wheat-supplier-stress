"""Retain every fixed scenario endpoint, allocation and exact cut certificate."""

from fractions import Fraction as F
from pathlib import Path
import argparse, subprocess
from bounds_common import ROOT, load, read, table, save, history, sha
from bounds_model import capacities, endpoint, classify
from cut_certificate import verify_allocation


def main(year, out, replay=False):
    history()
    if year == 2020:
        freeze = load("BOUNDS_FREEZE.json")
        for n, h in freeze["hashes"].items():
            assert sha(ROOT / n) == h, n
        if not replay:
            assert (
                subprocess.check_output(
                    ["git", "show", "HEAD:BOUNDS_FREEZE.json"], cwd=ROOT
                )
                == (ROOT / "BOUNDS_FREEZE.json").read_bytes()
            ), "commit development freeze before later scenarios"
    assert not (
        out / ("endpoints_" + str(year) + ".csv")
    ).exists(), "use a new replay output"
    data = load("data/bounds_inputs.json")
    x = data["years"][str(year)]
    cases = []
    flowrows = []
    cutrows = []
    importerrows = []
    supplierrows = []
    base_count = 0
    for basis in ["import", "mirror"]:
        for alpha in ["0", "0.05", "0.10", "0.25"]:
            for beta in ["0.5", "1", "2"]:
                for lost in sorted(data["origins"], key=int):
                    ident = "-".join([str(year), basis, alpha, beta, lost])
                    s, r, d, res = capacities(x, basis, alpha, beta, lost)
                    demand = sum(d.values(), F())
                    lower = None
                    for gamma in ["0", "1/2", "1"]:
                        ss, rr, dd, total, flows, aug, separate = endpoint(
                            s, r, d, res, gamma
                        )
                        checks, cuts = verify_allocation(ss, rr, dd, total, flows)
                        if lower is None:
                            lower = total
                        independent = sum(separate.values(), F())
                        assert total <= independent and lower <= total <= demand
                        cases.append(
                            dict(
                                case_id=ident,
                                year=year,
                                basis=basis,
                                alpha=alpha,
                                beta=beta,
                                lost_origin=lost,
                                lost_name=data["origins"][lost],
                                gamma=gamma,
                                demand_kg=str(demand),
                                known_covered_kg=str(lower),
                                endpoint_covered_kg=str(total),
                                independent_kg=str(independent),
                                shared_overclaim_kg=str(independent - total),
                                interval_width_kg=str(total - lower),
                                lower_unmet_kg=str(demand - total),
                                upper_unmet_kg=str(demand - lower),
                                unrestricted_upper_covered_kg=str(demand),
                                unrestricted_width_kg=str(demand - lower),
                                covered_fraction=str(total / demand) if demand else "",
                                classification=classify(demand, lower, total),
                                augmentations=aug,
                                allocation_cut_conditions=checks,
                            )
                        )
                        for (start, end), value in flows.items():
                            cap = (
                                ss[end[7:]]
                                if start == "source"
                                else (
                                    dd[start[9:]]
                                    if end == "sink"
                                    else rr.get((start[7:], end[9:]), F())
                                )
                            )
                            flowrows.append(
                                dict(
                                    case_id=ident,
                                    gamma=gamma,
                                    start=start,
                                    end=end,
                                    capacity_kg=str(cap),
                                    flow_kg=str(value),
                                    slack_kg=str(cap - value),
                                )
                            )
                        for cut in cuts:
                            cutrows.append(dict(case_id=ident, gamma=gamma, **cut))
                        for i, amount in dd.items():
                            v = flows["importer:" + i, "sink"]
                            importerrows.append(
                                dict(
                                    case_id=ident,
                                    gamma=gamma,
                                    importer=i,
                                    demand_kg=str(amount),
                                    covered_kg=str(v),
                                    unmet_kg=str(amount - v),
                                    independent_kg=str(separate[i]),
                                )
                            )
                        for o, cap in ss.items():
                            v = flows["source", "origin:" + o]
                            supplierrows.append(
                                dict(
                                    case_id=ident,
                                    gamma=gamma,
                                    origin=o,
                                    virtual_outside=o == "999999",
                                    capacity_kg=str(cap),
                                    used_kg=str(v),
                                    slack_kg=str(cap - v),
                                )
                            )
                    base_count += 1
    assert base_count == 240 and len(cases) == 720 and len(cutrows) == 5760
    for n, values in [
        ("endpoints", cases),
        ("flows", flowrows),
        ("cuts", cutrows),
        ("importers", importerrows),
        ("suppliers", supplierrows),
    ]:
        table(out / (n + "_" + str(year) + ".csv"), values)
    groups = []
    for basis in ["import", "mirror"]:
        for gamma in ["0", "1/2", "1"]:
            rs = [r for r in cases if r["basis"] == basis and r["gamma"] == gamma]
            groups.append(
                dict(
                    year=year,
                    basis=basis,
                    gamma=gamma,
                    cases=len(rs),
                    positive_loss_cases=sum(F(r["demand_kg"]) > 0 for r in rs),
                    classifications={
                        k: sum(r["classification"] == k for r in rs)
                        for k in [
                            "ZERO_MODELED_LOSS",
                            "KNOWN_NETWORK_SUFFICIENT",
                            "CONDITIONAL_SHORTFALL",
                            "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
                        ]
                    },
                    positive_overclaim_cases=sum(
                        F(r["shared_overclaim_kg"]) > 0 for r in rs
                    ),
                    max_overclaim_kg=str(max(F(r["shared_overclaim_kg"]) for r in rs)),
                    max_interval_width_kg=str(
                        max(F(r["interval_width_kg"]) for r in rs)
                    ),
                )
            )
    maximum = max(cases, key=lambda r: F(r["interval_width_kg"]))
    save(
        out / ("summary_" + str(year) + ".json"),
        dict(
            year=year,
            base_cases=base_count,
            endpoint_evaluations=len(cases),
            flow_accounts=len(flowrows),
            cut_certificates=len(cutrows),
            groups=groups,
            maximum_interval_illustration=maximum,
            source_informed=True,
            not_a_predictive_test=True,
            qualification="All optima and intervals conditional on authored capacities and residual-scaled outside envelope; accounting residual is not measured spare supply. Original coverage-gated study remains unexecuted.",
        ),
    )
    print("COMPLETE_CONDITIONAL_SCENARIOS", year, base_count, len(cases), len(cutrows))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, choices=[2019, 2020], required=True)
    p.add_argument("--out", type=Path, default=ROOT / "results/bounds")
    p.add_argument("--replay", action="store_true")
    a = p.parse_args()
    main(a.year, a.out, a.replay)
