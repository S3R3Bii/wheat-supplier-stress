"""Independent SQLite source binding and exact feasible-flow/min-cut verification.

Imports no solver, scenario, input or summary implementation helper.
"""

from pathlib import Path
from fractions import Fraction as F
import json, csv, sqlite3, hashlib, argparse

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(year, folder):
    n = 0

    def ck(v, s):
        nonlocal n
        assert v, s
        n += 1

    hold = json.loads((ROOT / "HISTORY_SOURCE_HOLD.json").read_bytes())
    for name, h in hold["files"].items():
        ck(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == h,
            "original held-source/code bytes",
        )
    old = json.loads((ROOT / "data/fao/input_gate.json").read_bytes())
    ck(
        old["status"] == "FAIL_SOURCE_QUALIFICATION"
        and old["failed_gates"]
        == ["common_support:143:2020:coverage_80_to_105_percent"]
        and old["scenario_outputs_computed"] is False,
        "unchanged original failed source gate",
    )
    source = read(ROOT / "data/fao/source_projection.csv")
    db = sqlite3.connect(":memory:")
    db.execute(
        "create table source(kind text,reporter text,partner text,year int,value text,positive int,flag text)"
    )
    db.executemany(
        "insert into source values(?,?,?,?,?,?,?)",
        [
            (
                r["source_file"],
                r["reporter_fao"],
                r["partner_fao"],
                int(r["year"]),
                r["kg_fraction"],
                int(r["state"] == "positive"),
                r["flag"],
            )
            for r in source
        ],
    )
    ck(len(source) == 179, "all requested source positions")
    ck(
        db.execute(
            "select count(*) from (select kind,reporter,partner,year from source group by kind,reporter,partner,year)"
        ).fetchone()[0]
        == 179,
        "all native keys unique",
    )

    def value(kind, r, y, p=""):
        rs = db.execute(
            "select value,positive from source where kind=? and reporter=? and year=? and partner=?",
            (kind + ".csv", r, y, p),
        ).fetchall()
        ck(len(rs) == 1, "full source position exists")
        return F(rs[0][0]) if rs[0][1] else None

    data = json.loads((ROOT / "data/bounds_inputs.json").read_bytes())
    plan = json.loads((ROOT / "data/planned_fao_network.json").read_bytes())
    importers = [a["code"] for a in plan["importers"]]
    origins = [a["code"] for a in plan["origins"]]
    ck(
        data["importers"] == {a["code"]: a["name"] for a in plan["importers"]}
        and data["origins"] == {a["code"]: a["name"] for a in plan["origins"]},
        "source-specific country names/codes",
    )
    rebuilt = {}
    supports = {}
    pair_accounts = {}
    for y in [2019, 2020]:
        z = dict(
            world={},
            residual={},
            prior_exports={},
            prior_routes={},
            current_import={},
            current_mirror={},
            support={},
        )
        for o in origins:
            z["prior_exports"][o] = str(value("prior_world_exports", o, y - 1))
            ck(F(z["prior_exports"][o]) > 0, "positive prior export total")
        for i in importers:
            w = value("world_imports", i, y)
            ck(w is not None and w > 0, "positive national import total")
            z["world"][i] = str(w)
            query = "select i.partner,i.value from source i join source x on x.kind='export_mirrors.csv' and x.reporter=i.partner and x.partner=i.reporter and x.year=i.year where i.kind='import_pairs.csv' and i.reporter=? and i.year=? and i.positive=1 and x.positive=1 order by cast(i.partner as integer)"
            common = db.execute(query, (i, y)).fetchall()
            mass = sum((F(v) for o, v in common), F())
            residual = w - mass
            ck(residual >= 0, "signed residual never clamped")
            z["support"][i] = [o for o, v in common]
            z["residual"][i] = str(residual)
            supports[y, i] = (w, mass, residual, [o for o, v in common])
            for o in origins:
                im = value("import_pairs", i, y, o)
                mi = value("export_mirrors", o, y, i)
                prior = value("import_pairs", i, y - 1, o)
                key = o + ":" + i
                z["current_import"][key] = None if im is None else str(im)
                z["current_mirror"][key] = None if mi is None else str(mi)
                z["prior_routes"][key] = None if prior is None else str(prior)
                pair_accounts[y, o, i] = (im, mi, prior)
        rebuilt[str(y)] = z
    ck(data["years"] == rebuilt, "complete independent source/input reconstruction")
    support = read(ROOT / "data/bounds_support.csv")
    ck(len(support) == 6, "all coverage groups")
    for r in support:
        w, c, res, common = supports[int(r["year"]), r["importer"]]
        ck(
            tuple(
                F(r[k])
                for k in ["world_kg", "common_import_kg", "residual_kg", "coverage"]
            )
            == (w, c, res, c / w),
            "coverage/residual identity",
        )
        ck(r["common_origins"] == ";".join(common), "common support membership")
        ck(
            r["original_80_percent_gate"] == str(c / w >= F(4, 5)),
            "original 80 percent gate preserved",
        )
    pair_rows = read(ROOT / "data/bounds_pair_support.csv")
    ck(len(pair_rows) == 60, "all current bilateral support positions")
    for r in pair_rows:
        im, mi, prior = pair_accounts[int(r["year"]), r["origin"], r["importer"]]
        ck(
            [r[k] for k in ["import_kg", "mirror_kg", "prior_route_kg"]]
            == ["" if v is None else str(v) for v in [im, mi, prior]],
            "all pair quantities/missing states",
        )
        active = im is not None and mi is not None
        ck(r["common_support"] == str(active), "bilateral intersection")
        ck(
            r["reason"]
            == (
                "positive_both_sides"
                if active
                else "import_unavailable" if im is None else "mirror_unavailable"
            ),
            "full exclusion reason",
        )
    endpoints = read(folder / ("endpoints_" + str(year) + ".csv"))
    flow_rows = read(folder / ("flows_" + str(year) + ".csv"))
    cut_rows = read(folder / ("cuts_" + str(year) + ".csv"))
    ir = read(folder / ("importers_" + str(year) + ".csv"))
    sr = read(folder / ("suppliers_" + str(year) + ".csv"))
    ck(len(endpoints) == 720, "all 240 cases times three endpoints")
    ck(
        len(flow_rows) == 33840
        and len(cut_rows) == 5760
        and len(ir) == 2160
        and len(sr) == 7920,
        "complete flow/cut/importer/supplier accounts",
    )

    def index(rs, key):
        result = {}
        for r in rs:
            result.setdefault(tuple(r[k] for k in key), []).append(r)
        return result

    flow_index = index(flow_rows, ["case_id", "gamma"])
    cut_index = index(cut_rows, ["case_id", "gamma"])
    ii = index(ir, ["case_id", "gamma"])
    si = index(sr, ["case_id", "gamma"])
    seen = set()
    base_values = {}
    max_case = None
    groups = {}

    def cuts(s, r, d):
        values = []
        names = sorted(d, key=int)
        for mask in range(8):
            selected = [i for j, i in enumerate(names) if mask & (1 << j)]
            dc = sum((d[i] for i in selected), F())
            oc = F()
            source = []
            for o in sorted(s, key=int):
                outgoing = sum(
                    (r.get((o, i), F()) for i in names if i not in selected), F()
                )
                oc += min(s[o], outgoing)
                if outgoing <= s[o]:
                    source.append(o)
            values.append(
                dict(
                    mask=str(mask),
                    importers_source_side=",".join(selected),
                    origins_source_side=",".join(source),
                    demand_cut_exact=str(dc),
                    origin_cut_exact=str(oc),
                    cut_value_exact=str(dc + oc),
                )
            )
        return values

    for row in endpoints:
        key = row["case_id"], row["gamma"]
        ck(key not in seen, "unique endpoint")
        seen.add(key)
        z = rebuilt[str(year)]
        a = F(row["alpha"])
        b = F(row["beta"])
        g = F(row["gamma"])
        lost = row["lost_origin"]
        basis = row["basis"]
        ck(
            row["year"] == str(year)
            and row["alpha"] in ["0", "0.05", "0.10", "0.25"]
            and row["beta"] in ["0.5", "1", "2"]
            and row["gamma"] in ["0", "1/2", "1"]
            and basis in ["import", "mirror"]
            and lost in origins,
            "fixed parameter universe",
        )
        ck(
            row["case_id"]
            == "-".join([str(year), basis, row["alpha"], row["beta"], lost]),
            "complete scenario identity",
        )
        ck(row["lost_name"] == data["origins"][lost], "source origin label")
        s = {o: F() if o == lost else a * F(z["prior_exports"][o]) for o in origins}
        r = {
            tuple(k.split(":")): b * F(v)
            for k, v in z["prior_routes"].items()
            if v is not None and k.split(":")[0] != lost
        }
        d = {
            i: (
                F(z["current_" + basis][lost + ":" + i])
                if lost in z["support"][i]
                else F()
            )
            for i in importers
        }
        s["999999"] = sum((g * F(v) for v in z["residual"].values()), F())
        for i in importers:
            r["999999", i] = g * F(z["residual"][i])
        expected_caps = {("source", "origin:" + o): cap for o, cap in s.items()}
        expected_caps.update(
            {("origin:" + o, "importer:" + i): r.get((o, i), F()) for o in s for i in d}
        )
        expected_caps.update({("importer:" + i, "sink"): v for i, v in d.items()})
        flows = {}
        rr = flow_index[key]
        ck(len(rr) == len(expected_caps), "every finite-network arc")
        for q in rr:
            edge = q["start"], q["end"]
            ck(edge in expected_caps and edge not in flows, "unique valid arc")
            cap = expected_caps[edge]
            v = F(q["flow_kg"])
            ck(
                F(q["capacity_kg"]) == cap and F(q["slack_kg"]) == cap - v,
                "exact native-derived cap/slack",
            )
            ck(0 <= v <= cap, "arc feasibility")
            flows[edge] = v
        total = F(row["endpoint_covered_kg"])
        demand = sum(d.values(), F())
        for o, cap in s.items():
            ck(
                sum((flows["origin:" + o, "importer:" + i] for i in d), F())
                == flows["source", "origin:" + o],
                "origin conservation",
            )
        for i in d:
            ck(
                sum((flows["origin:" + o, "importer:" + i] for o in s), F())
                == flows["importer:" + i, "sink"],
                "importer conservation",
            )
        ck(
            sum((flows["source", "origin:" + o] for o in s), F())
            == total
            == sum((flows["importer:" + i, "sink"] for i in d), F()),
            "all total balances",
        )
        expected_cuts = cuts(s, r, d)
        actual_cuts = cut_index[key]
        ck(len(actual_cuts) == 8, "all eight cut subsets")
        for q, c in zip(actual_cuts, expected_cuts):
            ck({k: q[k] for k in c} == c, "complete independently reconstructed cut")
        ck(
            min(F(c["cut_value_exact"]) for c in expected_cuts) == total,
            "exact max-flow/min-cut optimality",
        )
        separate = {
            i: min(
                d[i], sum((min(cap, r.get((o, i), F())) for o, cap in s.items()), F())
            )
            for i in d
        }
        ind = sum(separate.values(), F())
        ck(total <= ind <= demand, "shared resource dominance")
        if row["gamma"] == "0":
            base_values[row["case_id"]] = total
        lower = base_values[row["case_id"]]
        ck(0 <= lower <= total <= demand, "conditional lower/upper endpoints")
        expected = dict(
            demand_kg=demand,
            known_covered_kg=lower,
            independent_kg=ind,
            shared_overclaim_kg=ind - total,
            interval_width_kg=total - lower,
            lower_unmet_kg=demand - total,
            upper_unmet_kg=demand - lower,
            unrestricted_upper_covered_kg=demand,
            unrestricted_width_kg=demand - lower,
        )
        for k, v in expected.items():
            ck(F(row[k]) == v, "endpoint arithmetic " + k)
        ck(
            row["covered_fraction"] == (str(total / demand) if demand else ""),
            "explicit loss denominator, zero loss undefined",
        )
        status = (
            "ZERO_MODELED_LOSS"
            if demand == 0
            else (
                "KNOWN_NETWORK_SUFFICIENT"
                if lower == demand
                else (
                    "CONDITIONAL_SHORTFALL"
                    if total < demand
                    else "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY"
                )
            )
        )
        ck(row["classification"] == status, "interval decision class")
        ck(
            int(row["allocation_cut_conditions"]) == 70,
            "production feasibility condition count",
        )
        importer_accounts = {q["importer"]: q for q in ii[key]}
        ck(set(importer_accounts) == set(d), "all importer accounts")
        for i, v in d.items():
            q = importer_accounts[i]
            used = flows["importer:" + i, "sink"]
            ck(
                [
                    F(q[k])
                    for k in ["demand_kg", "covered_kg", "unmet_kg", "independent_kg"]
                ]
                == [v, used, v - used, separate[i]],
                "complete importer allocation",
            )
        supplier_accounts = {q["origin"]: q for q in si[key]}
        ck(set(supplier_accounts) == set(s), "all supplier accounts")
        for o, cap in s.items():
            q = supplier_accounts[o]
            used = flows["source", "origin:" + o]
            ck(
                [F(q[k]) for k in ["capacity_kg", "used_kg", "slack_kg"]]
                == [cap, used, cap - used]
                and q["virtual_outside"] == str(o == "999999"),
                "complete real/virtual source account",
            )
        groups.setdefault((basis, row["gamma"]), []).append(row)
        if max_case is None or F(row["interval_width_kg"]) > F(
            max_case["interval_width_kg"]
        ):
            max_case = row
    ck(len(base_values) == 240 and len(seen) == 720, "all complete base configurations")
    for ident in base_values:
        rr = [q for q in endpoints if q["case_id"] == ident]
        ck([q["gamma"] for q in rr] == ["0", "1/2", "1"], "all monotone endpoints")
        v = [F(q["endpoint_covered_kg"]) for q in rr]
        ck(v == sorted(v), "capacity-envelope monotonicity")
    summary = json.loads((folder / ("summary_" + str(year) + ".json")).read_bytes())
    ck(
        (
            summary["base_cases"],
            summary["endpoint_evaluations"],
            summary["flow_accounts"],
            summary["cut_certificates"],
        )
        == (240, 720, 33840, 5760),
        "full summary account sizes",
    )
    ck(
        summary["maximum_interval_illustration"] == {k:(int(v) if k in ['year','augmentations','allocation_cut_conditions'] else v) for k,v in max_case.items()},
        "declared maximum with fixed first-tie order",
    )
    ck(len(summary["groups"]) == 6, "all basis/envelope summary groups")
    for q in summary["groups"]:
        rr = groups[q["basis"], q["gamma"]]
        expected = dict(
            year=year,
            basis=q["basis"],
            gamma=q["gamma"],
            cases=len(rr),
            positive_loss_cases=sum(F(v["demand_kg"]) > 0 for v in rr),
            classifications={
                k: sum(v["classification"] == k for v in rr)
                for k in [
                    "ZERO_MODELED_LOSS",
                    "KNOWN_NETWORK_SUFFICIENT",
                    "CONDITIONAL_SHORTFALL",
                    "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
                ]
            },
            positive_overclaim_cases=sum(F(v["shared_overclaim_kg"]) > 0 for v in rr),
            max_overclaim_kg=str(max(F(v["shared_overclaim_kg"]) for v in rr)),
            max_interval_width_kg=str(max(F(v["interval_width_kg"]) for v in rr)),
        )
        ck(q == expected, "all complete summary cells")
    result = dict(
        status="PASS",
        year=year,
        independent_sql_fraction_conditions=n,
        source_positions=179,
        original_held_files=len(hold["files"]),
        base_cases=240,
        endpoints=720,
        flows=33840,
        cut_subsets=5760,
        production_helper_imports=False,
    )
    (folder / ("INDEPENDENT_" + str(year) + ".json")).write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(result)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, choices=[2019, 2020], required=True)
    p.add_argument("--out", type=Path, default=ROOT / "results/bounds")
    a = p.parse_args()
    main(a.year, a.out)
