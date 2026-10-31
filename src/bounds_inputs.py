"""Bind the restricted FAO network and signed residual without passing the old gate."""

from fractions import Fraction as F
from bounds_common import ROOT, load, read, save, table, sha, history


def main():
    history()
    plan = load("data/planned_fao_network.json")
    rows = read(ROOT / "data/fao/source_projection.csv")
    lookup = {}
    for r in rows:
        key = (r["source_file"], r["reporter_fao"], r["partner_fao"], int(r["year"]))
        assert key not in lookup
        lookup[key] = r
        if r["state"] == "positive":
            assert (
                F(r["kg_fraction"]) > 0 and r["unit"] == "t" and r["flag"] in ["A", "I"]
            )
        else:
            assert r["state"] == "missing" and r["kg_fraction"] == ""

    def value(kind, reporter, year, partner=""):
        r = lookup.get((kind + ".csv", reporter, partner, year))
        return str(F(r["kg_fraction"])) if r and r["state"] == "positive" else None

    importers = {a["code"]: a["name"] for a in plan["importers"]}
    origins = {a["code"]: a["name"] for a in plan["origins"]}
    years = {}
    support = []
    pairs = []
    for year in [2019, 2020]:
        inputs = dict(
            world={},
            residual={},
            prior_exports={},
            prior_routes={},
            current_import={},
            current_mirror={},
            support={},
        )
        for o in origins:
            v = value("prior_world_exports", o, year - 1)
            assert v is not None
            inputs["prior_exports"][o] = v
        for i in importers:
            w = value("world_imports", i, year)
            assert w is not None
            inputs["world"][i] = w
            common = []
            mass = F()
            for o in origins:
                im = value("import_pairs", i, year, o)
                mi = value("export_mirrors", o, year, i)
                prior = value("import_pairs", i, year - 1, o)
                key = o + ":" + i
                inputs["current_import"][key] = im
                inputs["current_mirror"][key] = mi
                inputs["prior_routes"][key] = prior
                active = im is not None and mi is not None
                if active:
                    common.append(o)
                    mass += F(im)
                pairs.append(
                    dict(
                        year=year,
                        origin=o,
                        importer=i,
                        import_kg=im or "",
                        mirror_kg=mi or "",
                        prior_route_kg=prior or "",
                        common_support=active,
                        reason=(
                            "positive_both_sides"
                            if active
                            else (
                                "import_unavailable"
                                if im is None
                                else "mirror_unavailable"
                            )
                        ),
                    )
                )
            r = F(w) - mass
            assert r >= 0, "signed source discrepancy cannot be clamped"
            assert (
                len(common) >= 2
                and sum(
                    inputs["prior_routes"][o + ":" + i] is not None for o in origins
                )
                >= 2
            )
            inputs["support"][i] = common
            inputs["residual"][i] = str(r)
            support.append(
                dict(
                    year=year,
                    importer=i,
                    name=importers[i],
                    world_kg=w,
                    common_import_kg=str(mass),
                    residual_kg=str(r),
                    coverage=str(mass / F(w)),
                    common_origins=";".join(common),
                    original_80_percent_gate=mass / F(w) >= F(4, 5),
                )
            )
        years[str(year)] = inputs
    out = dict(
        importers=importers,
        origins=origins,
        years=years,
        source_projection_sha256=sha(ROOT / "data/fao/source_projection.csv"),
        qualification="Restricted common-positive FAO network plus authored residual-scaled outside-capacity model. Original coverage gate remains failed; residual is accounting difference, not spare capacity.",
    )
    save(ROOT / "data/bounds_inputs.json", out)
    table(ROOT / "data/bounds_support.csv", support)
    table(ROOT / "data/bounds_pair_support.csv", pairs)
    print(
        "BOUNDS_INPUTS",
        len(rows),
        "source positions",
        len(support),
        "signed residual groups",
        len(pairs),
        "pair-support accounts",
    )


if __name__ == "__main__":
    main()
