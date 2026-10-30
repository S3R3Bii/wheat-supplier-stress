"""Independent exact cut oracle; this module imports no residual-flow implementation."""

from fractions import Fraction


def all_cuts(supplies, routes, demands):
    importers = sorted(demands, key=int)
    origins = sorted(supplies, key=int)
    cuts = []
    for mask in range(1 << len(importers)):
        selected = {
            importer for index, importer in enumerate(importers) if mask & (1 << index)
        }
        demand_cut = sum((Fraction(demands[i]) for i in selected), Fraction())
        origin_cut = Fraction()
        source_side = []
        for origin in origins:
            outgoing = sum(
                (
                    Fraction(routes.get((origin, i), 0))
                    for i in importers
                    if i not in selected
                ),
                Fraction(),
            )
            supply = Fraction(supplies[origin])
            if outgoing <= supply:
                origin_cut += outgoing
                source_side.append(str(origin))
            else:
                origin_cut += supply
        # Once importer placement is fixed, each origin's cut placement minimizes independently.
        cuts.append(
            dict(
                mask=mask,
                importers_source_side=",".join(
                    str(i) for i in importers if i in selected
                ),
                origins_source_side=",".join(source_side),
                demand_cut_exact=str(demand_cut),
                origin_cut_exact=str(origin_cut),
                cut_value_exact=str(demand_cut + origin_cut),
            )
        )
    return cuts


def verify_allocation(supplies, routes, demands, total, flows):
    checks = 0
    for origin, supply in supplies.items():
        node = "origin:" + str(origin)
        used = flows["source", node]
        assert 0 <= used <= Fraction(supply)
        checks += 1
        outgoing = Fraction()
        for importer in demands:
            assigned = flows[node, "importer:" + str(importer)]
            assert 0 <= assigned <= Fraction(routes.get((origin, importer), 0))
            checks += 1
            outgoing += assigned
        assert outgoing == used
        checks += 1
    covered = Fraction()
    for importer, demand in demands.items():
        node = "importer:" + str(importer)
        assigned = flows[node, "sink"]
        assert 0 <= assigned <= Fraction(demand)
        checks += 1
        assert (
            sum((flows["origin:" + str(o), node] for o in supplies), Fraction())
            == assigned
        )
        checks += 1
        covered += assigned
    assert (
        covered
        == total
        == sum((flows["source", "origin:" + str(o)] for o in supplies), Fraction())
    )
    checks += 1
    cuts = all_cuts(supplies, routes, demands)
    minimum = min(Fraction(c["cut_value_exact"]) for c in cuts)
    assert minimum == total
    checks += len(cuts)
    return checks, cuts
