"""Independently verify used values, all source/classification/overclaim rows and scope."""

from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pypdf import PdfReader
import json, csv, hashlib, re, unicodedata

ROOT = Path(__file__).resolve().parents[1]


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def value(b):
    x = load(b["file"])
    if b["query"] is not None:
        rs = [r for r in x if all(r[k] == v for k, v in b["query"].items())]
        assert len(rs) == 1
        x = rs[0]
    for k in b["path"]:
        x = x[k]
    op = b["operation"]
    if op in [
        "unresolved_full",
        "positive_full",
        "known_overclaims",
        "max_known_overclaim",
    ]:
        rows = [
            r
            for y in [2019, 2020]
            for r in load("results/bounds/endpoints_" + str(y) + ".csv")
        ]
        if op == "unresolved_full":
            x = sum(
                r["gamma"] == "1"
                and r["classification"] == "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY"
                for r in rows
            )
        elif op == "positive_full":
            x = sum(r["gamma"] == "1" and F(r["demand_kg"]) > 0 for r in rows)
        elif op == "known_overclaims":
            x = sum(r["gamma"] == "0" and F(r["shared_overclaim_kg"]) > 0 for r in rows)
        else:
            x = max(F(r["shared_overclaim_kg"]) for r in rows if r["gamma"] == "0")
    if op in ["tonnes2", "percent6", "max_known_overclaim"]:
        v = F(x) * (100 if op == "percent6" else F(1, 1000))
        digits = 6 if op == "percent6" else 2
        with localcontext() as c:
            c.prec = 80
            return format(
                (Decimal(v.numerator) / Decimal(v.denominator)).quantize(
                    Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN
                ),
                "," + "." + str(digits) + "f",
            )
    return format(int(x), ",") if op == "commas" else str(x)


def main():
    n = 0

    def ck(v, s):
        nonlocal n
        assert v, s
        n += 1

    pdf = PdfReader(ROOT / "paper/manuscript.pdf")
    ck(len(pdf.pages) == 6, "six current pages")
    pages = [
        re.sub(r"\s+", " ", unicodedata.normalize("NFKC", p.extract_text() or ""))
        for p in pdf.pages
    ]
    text = " ".join(pages)
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bindings = load("paper/bindings.json")
    ck(
        len(bindings) == 107 and len({b["name"] for b in bindings}) == 107,
        "all unique used source bindings",
    )
    for b in bindings:
        v = value(b)
        ck(v == b["display"], "independent source conversion/display")
        ck(
            chr(92) + "newcommand{" + chr(92) + b["name"] + "}{" + v + "}" in tex,
            "actual macro definition",
        )
        ck(
            len(re.findall(chr(92) * 2 + b["name"] + r"\b", tex)) >= 2,
            "actually used beyond definition",
        )
        ck(v in text, "actual rendered PDF value")
    rows = load("paper/table_rows.json")
    ck(
        len(rows["source"]) == 6
        and len(rows["classifications"]) == 12
        and len(rows["overclaims"]) == 4,
        "all complete table rows",
    )
    for r in rows["source"]:
        q = {k: r[k] for k in ["year", "importer"]}
        vals = [
            value(
                dict(
                    file="data/bounds_support.csv", path=[field], query=q, operation=op
                )
            )
            for field, op in [
                ("world_kg", "tonnes2"),
                ("common_import_kg", "tonnes2"),
                ("residual_kg", "tonnes2"),
                ("coverage", "percent6"),
            ]
        ]
        ck(
            " ".join([r["name"], r["year"], *vals]) in pages[1],
            "complete actual source/coverage table row",
        )
    summary = load("results/bounds/summary.json")
    for r in rows["classifications"]:
        g = summary["groups"][r["index"]]
        vals = [
            str(g["classifications"][k])
            for k in [
                "KNOWN_NETWORK_SUFFICIENT",
                "CONDITIONAL_SHORTFALL",
                "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
                "ZERO_MODELED_LOSS",
            ]
        ]
        ck(
            " ".join([str(r["year"]), r["basis"], r["gamma"], *vals]) in pages[3],
            "complete actual classification table row",
        )
    for r in rows["overclaims"]:
        g = summary["groups"][r["index"]]
        gap = value(
            dict(
                file="results/bounds/summary.json",
                path=["groups", r["index"], "max_overclaim_kg"],
                query=None,
                operation="tonnes2",
            )
        )
        ck(
            " ".join(
                [str(r["year"]), r["basis"], str(g["positive_overclaim_cases"]), gap]
            )
            in pages[4],
            "complete actual shared-overclaim table row",
        )
    scope = load("paper/PUBLICATION_SCOPE.json")
    ck(
        scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False,
        "independent publication scope",
    )
    ck(len(scope["public_files"]) == 5, "five scoped paper files")
    for name, h in scope["public_files"].items():
        ck(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == h,
            "current scoped file hash",
        )
    ck("not peer reviewed" in text.lower(), "review status")
    ck(
        "f9d4de7a01a2818461df34c9767395d86d9d3654" in text,
        "development freeze before later application",
    )
    ck(
        "original coverage-gated network study remains unexecuted" in text.lower(),
        "original failed scope preserved",
    )
    ck("not measured spare supply" in text.lower(), "outside-envelope qualification")
    ck(
        "not protected predictive validation" in text.lower(),
        "source-informed temporal qualification",
    )
    ck("Azure" in text, "private formal project boundary")
    for name in ["coverage_and_residual", "conditional_classes", "maximum_interval"]:
        ck(
            (ROOT / "paper/images" / (name + ".pdf")).read_bytes()
            == (ROOT / "figures" / (name + ".pdf")).read_bytes(),
            "actual included figure bytes",
        )
    result = dict(
        status="PASS",
        finite_conditions=n,
        used_bindings=len(bindings),
        source_table_rows=6,
        classification_table_rows=12,
        overclaim_table_rows=4,
        pages=6,
        scope_files=5,
        rendered_visual_review="separate",
    )
    (ROOT / "paper/verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(result)


if __name__ == "__main__":
    main()
