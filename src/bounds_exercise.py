"""Return an assumption-qualified saved interval, not a shipment promise."""

from bounds_common import ROOT, load, read, save


def answer(r):
    keys = {"scope", "year", "basis", "alpha", "beta", "lost_origin", "gamma"}
    if set(r) - keys:
        return dict(status="REJECT", reason="arbitrary caller fields/data unsupported")
    if set(r) != keys:
        return dict(
            status="ABSTAIN", reason="incomplete scenario and outside-envelope contract"
        )
    if r["scope"] != "conditional_replacement_interval":
        return dict(
            status="REJECT",
            reason="no guaranteed shipment, actual spare capacity, probability or political priority claim",
        )
    if r["year"] not in [2019, 2020]:
        return dict(status="ABSTAIN", reason="year outside saved historical cohort")
    rr = read(ROOT / ("results/bounds/endpoints_" + str(r["year"]) + ".csv"))
    matches = [
        x
        for x in rr
        if all(
            str(r[k]) == x[k]
            for k in ["basis", "alpha", "beta", "lost_origin", "gamma"]
        )
    ]
    if len(matches) != 1:
        return dict(status="ABSTAIN", reason="no unique committed scenario")
    x = matches[0]
    return dict(
        status="QUALIFIED_INTERVAL",
        classification=x["classification"],
        demand_kg=x["demand_kg"],
        lower_covered_kg=x["known_covered_kg"],
        upper_covered_kg=x["endpoint_covered_kg"],
        lower_unmet_kg=x["lower_unmet_kg"],
        upper_unmet_kg=x["upper_unmet_kg"],
        unrestricted_upper_covered_kg=x["demand_kg"],
        qualification="Historical restricted-network scenario with authored shared/route/outside capacity assumptions; residual is an accounting difference, not real spare supply. Obtain supplier-specific evidence before promising deliveries.",
    )


def main(out):
    save(
        out / "exercise.json",
        [
            dict(request=r, response=answer(r))
            for r in load("data/bounds_requests.json")
        ],
    )


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "results/bounds")
    main(p.parse_args().out)
