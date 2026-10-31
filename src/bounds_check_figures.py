"""Check all source values and actual stacked/nonstacked SVG rectangle corners."""

from pathlib import Path
from fractions import Fraction as F
import csv, json, re, hashlib, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CLASSES = [
    "KNOWN_NETWORK_SUFFICIENT",
    "CONDITIONAL_SHORTFALL",
    "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
    "ZERO_MODELED_LOSS",
]


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def key(file, path, query):
    return (file, tuple(path), None if query is None else tuple(sorted(query.items())))


def main():
    n = 0
    coordinates = 0
    seen = set()
    bindings = set()
    expected = {}

    def ck(v, s):
        nonlocal n
        assert v, s
        n += 1

    support = load("data/bounds_support.csv")
    for i, r in enumerate(support):
        q = {k: r[k] for k in ["year", "importer"]}
        for field, factor, fmt in [
            ("coverage", "100", ".6f"),
            ("residual_kg", "1/1000", ",.2f"),
        ]:
            expected[key("data/bounds_support.csv", [field], q)] = (
                F(r[field]) * F(factor),
                F(),
                i,
                0.58,
                factor,
                fmt,
                r["name"] + " / " + r["year"],
                False,
            )
    summary = load("results/bounds/summary.json")
    for j, g in enumerate(summary["groups"]):
        left = 0
        for c in CLASSES:
            expected[
                key(
                    "results/bounds/summary.json",
                    ["groups", j, "classifications", c],
                    None,
                )
            ] = (
                F(g["classifications"][c]),
                F(left),
                ["0", "1/2", "1"].index(g["gamma"]),
                0.58,
                "1",
                ".0f",
                "γ = " + g["gamma"],
                True,
            )
            left += g["classifications"][c]
    m = summary["maximum_interval_illustration"]
    file = "results/bounds/endpoints_" + m["year"] + ".csv"
    rows = load(file)
    labels = [
        "Known network / γ = 0",
        "Half residual envelope",
        "Full residual envelope",
        "Unrestricted outside cap",
    ]
    for i, (g, field) in enumerate(
        [
            ("0", "endpoint_covered_kg"),
            ("1/2", "endpoint_covered_kg"),
            ("1", "endpoint_covered_kg"),
            ("1", "demand_kg"),
        ]
    ):
        q = dict(case_id=m["case_id"], gamma=g)
        rr = [r for r in rows if all(r[k] == v for k, v in q.items())]
        ck(len(rr) == 1, "unique maximum-case source row")
        expected[key(file, [field], q)] = (
            F(rr[0][field]) / 1000000000,
            F(),
            i,
            0.58,
            "1/1000000000",
            ".6f",
            labels[i],
            False,
        )
    figures = load("figures/manifest.json")
    ck(len(figures) == 3, "three declared figures")
    for fig in figures:
        tree = ET.fromstring((ROOT / "figures" / (fig["name"] + ".svg")).read_bytes())
        groups = {x.attrib.get("id"): x for x in tree.iter() if x.tag.endswith("g")}
        texts = [
            "".join(x.itertext()).strip() for x in tree.iter() if x.tag.endswith("text")
        ]
        for ext, h in fig["asset_sha256"].items():
            ck(
                hashlib.sha256(
                    (ROOT / "figures" / (fig["name"] + "." + ext)).read_bytes()
                ).hexdigest()
                == h,
                "asset SHA256",
            )
        for a in fig["artists"]:
            k = key(a["file"], a["path"], a["query"])
            ck(k in expected and k not in bindings, "complete unique source binding")
            bindings.add(k)
            ck(a["gid"] not in seen, "unique source artist")
            seen.add(a["gid"])
            exact, left, pos, thick, factor, fmt, category, omit_zero = expected[k]
            v = float(exact)
            ck(
                (
                    a["value"],
                    a["left"],
                    a["position"],
                    a["thickness"],
                    a["factor"],
                    a["format"],
                    a["category"],
                )
                == (v, float(left), pos, thick, factor, fmt, category),
                "independent value/stack offset/position/format",
            )
            label = "" if omit_zero and v == 0 else format(v, fmt)
            ck(
                a["label"] == label and (not label or label in texts),
                "actual source numeric label",
            )
            ck(
                category in texts
                or (
                    fig["name"] == "coverage_and_residual"
                    and "residual_kg" in a["path"]
                ),
                "actual category labels; shared first-panel labels",
            )
            paths = [x for x in groups[a["gid"]].iter() if x.tag.endswith("path")]
            ck(len(paths) == 1, "actual single rectangle path")
            nums = list(
                map(
                    float,
                    re.findall(
                        r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", paths[0].attrib["d"]
                    ),
                )
            )
            ck(len(nums) == 8, "four corners")
            axis = a["axis_points"]
            lo, hi = axis["xlim"]
            bottom, top = axis["ylim"]
            x = lambda z: axis["left"] + (z - lo) / (hi - lo) * axis["width"]
            y = lambda z: axis["top"] + (top - z) / (top - bottom) * axis["height"]
            xx = [x(float(left)), x(float(left) + v)]
            yy = [y(pos - thick / 2), y(pos + thick / 2)]
            for actual, target in [
                (min(nums[::2]), min(xx)),
                (max(nums[::2]), max(xx)),
                (min(nums[1::2]), min(yy)),
                (max(nums[1::2]), max(yy)),
            ]:
                ck(abs(actual - target) < 0.02, "actual source SVG corner")
                coordinates += 1
    ck(bindings == set(expected) and len(seen) == 64, "all 64 complete bound artists")
    result = dict(
        status="PASS",
        finite_conditions=n,
        source_bound_artists=len(seen),
        svg_coordinate_conditions=coordinates,
        asset_hashes=9,
        visual_review="separate; no accessibility conformance claim",
    )
    (ROOT / "figures/verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(result)


if __name__ == "__main__":
    main()
