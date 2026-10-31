"""Render all source groups, all classifications and the declared maximum interval."""

from pathlib import Path
from fractions import Fraction as F
import csv, json, hashlib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
CLASSES = [
    "KNOWN_NETWORK_SUFFICIENT",
    "CONDITIONAL_SHORTFALL",
    "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
    "ZERO_MODELED_LOSS",
]
COLORS = ["#177f83", "#b24b5b", "#e4b34f", "#c5ccd5"]


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def lookup(file, path, query):
    x = load(file)
    if query is not None:
        rr = [r for r in x if all(r[k] == v for k, v in query.items())]
        assert len(rr) == 1
        x = rr[0]
    for k in path:
        x = x[k]
    return F(x)


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "wheat-supplier-bounds",
        }
    )
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    manifest = []
    items = []

    def bar(
        ax,
        file,
        path,
        query,
        i,
        color,
        category,
        factor="1",
        fmt=".0f",
        left=0,
        inside=False,
        omit_zero=False,
    ):
        value = float(lookup(file, path, query) * F(factor))
        gid = "source-" + str(len(manifest)) + "-" + str(len(items))
        patch = ax.barh(i, value, left=left, height=0.58, color=color)[0]
        patch.set_gid(gid)
        label = "" if omit_zero and value == 0 else format(value, fmt)
        if label:
            if inside:
                ax.text(
                    left + value / 2,
                    i,
                    label,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if color in COLORS[:2] else "#202020",
                )
            else:
                ax.annotate(
                    label,
                    (left + value, i),
                    xytext=(4, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    fontsize=9,
                )
        items.append(
            (
                dict(
                    gid=gid,
                    file=file,
                    path=path,
                    query=query,
                    factor=factor,
                    value=value,
                    left=float(left),
                    position=i,
                    thickness=0.58,
                    label=label,
                    format=fmt,
                    category=category,
                ),
                ax,
            )
        )

    def finish(fig, name):
        fig.canvas.draw()
        w, h = fig.get_size_inches() * 72
        for a, ax in items:
            box = ax.get_position()
            a["axis_points"] = dict(
                left=float(box.x0 * w),
                top=float((1 - box.y1) * h),
                width=float(box.width * w),
                height=float(box.height * h),
                xlim=list(map(float, ax.get_xlim())),
                ylim=list(map(float, ax.get_ylim())),
            )
        for ext in ["png", "svg", "pdf"]:
            meta = (
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None} if ext == "pdf" else None
            )
            fig.savefig(
                folder / (name + "." + ext), dpi=160, facecolor="white", metadata=meta
            )
        p = folder / (name + ".svg")
        p.write_bytes(
            (
                "\n".join(
                    x.rstrip() for x in p.read_text(encoding="utf-8").splitlines()
                )
                + "\n"
            ).encode()
        )
        manifest.append(
            dict(
                name=name,
                artists=[a for a, ax in items],
                asset_sha256={
                    e: hashlib.sha256(
                        (folder / (name + "." + e)).read_bytes()
                    ).hexdigest()
                    for e in ["png", "svg", "pdf"]
                },
            )
        )
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    fig.subplots_adjust(left=0.2, right=0.88, top=0.73, bottom=0.2, wspace=0.75)
    fig.suptitle(
        "The failed coverage gate remains visible",
        x=0.04,
        ha="left",
        y=0.97,
        fontsize=16,
    )
    fig.text(
        0.04,
        0.87,
        "FAO compiled 2019/2020 wheat accounts; signed national-minus-common-import differences are not spare capacity.",
        fontsize=10,
    )
    items = []
    rr = load("data/bounds_support.csv")
    labels = [r["name"] + " / " + r["year"] for r in rr]
    for i, r in enumerate(rr):
        query = {k: r[k] for k in ["year", "importer"]}
        color = "#b24b5b" if r["original_80_percent_gate"] == "False" else "#177f83"
        bar(
            axes[0],
            "data/bounds_support.csv",
            ["coverage"],
            query,
            i,
            color,
            labels[i],
            "100",
            ".6f",
        )
        bar(
            axes[1],
            "data/bounds_support.csv",
            ["residual_kg"],
            query,
            i,
            color,
            labels[i],
            "1/1000",
            ",.2f",
        )
    for ax in axes:
        ax.set_yticks(range(6), labels if ax == axes[0] else [""] * 6)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
    axes[0].set_xlim(0, 122)
    axes[0].axvline(80, color="#555555", linestyle="--", linewidth=0.8)
    axes[0].set_xlabel("Common import share of national total (%)")
    axes[0].set_title("Dashed line: original 80% minimum")
    axes[1].set_xlim(0, 1700000)
    axes[1].ticklabel_format(style="plain", axis="x")
    axes[1].set_xticks([0, 500000, 1000000], ["0", "500,000", "1,000,000"])
    axes[1].set_xlabel("Accounting residual (tonnes)")
    axes[1].set_title("No negative residual was clamped")
    fig.text(
        0.04,
        0.05,
        "Morocco 2020: 79.478498% fails the original gate. The new interval exercise does not pass or relax that gate.",
        fontsize=10,
    )
    finish(fig, "coverage_and_residual")
    summary = load("results/bounds/summary.json")
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.8))
    fig.subplots_adjust(
        left=0.13, right=0.96, top=0.77, bottom=0.18, wspace=0.27, hspace=0.65
    )
    fig.suptitle(
        "Outside-capacity assumptions change the decision class",
        x=0.04,
        ha="left",
        y=0.97,
        fontsize=15,
    )
    fig.text(
        0.04,
        0.9,
        "Each panel retains all 120 base configurations; repeated parameter settings are not independent observations.",
        fontsize=9,
    )
    items = []
    for ax, (year, basis) in zip(
        axes.flat,
        [(2019, "import"), (2019, "mirror"), (2020, "import"), (2020, "mirror")],
    ):
        groups = [
            (j, g)
            for j, g in enumerate(summary["groups"])
            if g["year"] == year and g["basis"] == basis
        ]
        for i, (j, g) in enumerate(groups):
            left = 0
            for k, color in zip(CLASSES, COLORS):
                bar(
                    ax,
                    "results/bounds/summary.json",
                    ["groups", j, "classifications", k],
                    None,
                    i,
                    color,
                    "γ = " + g["gamma"],
                    left=left,
                    inside=True,
                    omit_zero=True,
                )
                left += g["classifications"][k]
        ax.set_yticks(range(3), ["γ = " + g["gamma"] for j, g in groups])
        ax.invert_yaxis()
        ax.set_xlim(0, 120)
        ax.set_xticks([0, 40, 80, 120])
        ax.set_title(str(year) + " / " + basis)
        ax.set_xlabel("Configurations (count)")
    fig.legend(
        handles=[
            Patch(color=c, label=l)
            for c, l in zip(
                COLORS,
                [
                    "Known network sufficient",
                    "Conditional shortfall",
                    "Unresolved outside capacity",
                    "Zero modeled loss",
                ],
            )
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.045),
        ncol=2,
        frameon=False,
        fontsize=10,
    )
    fig.text(
        0.04,
        0.01,
        "γ scales an authored outside-route envelope from the accounting residual; it is not observed supply or a probability.",
        fontsize=9,
    )
    finish(fig, "conditional_classes")
    maximum = summary["maximum_interval_illustration"]
    year = maximum["year"]
    ident = maximum["case_id"]
    file = "results/bounds/endpoints_" + year + ".csv"
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(left=0.29, right=0.83, top=0.72, bottom=0.22)
    fig.suptitle(
        "The maximum-width example depends on its capacity assumption",
        x=0.04,
        ha="left",
        y=0.97,
        fontsize=14,
    )
    fig.text(
        0.04,
        0.86,
        year
        + " / "
        + maximum["basis"]
        + " / loss of "
        + maximum["lost_name"]
        + " / α = "
        + maximum["alpha"]
        + " / β = "
        + maximum["beta"],
        fontsize=11,
    )
    items = []
    labels = [
        "Known network / γ = 0",
        "Half residual envelope",
        "Full residual envelope",
        "Unrestricted outside cap",
    ]
    for i, (gamma, field, color) in enumerate(
        [
            ("0", "endpoint_covered_kg", "#657182"),
            ("1/2", "endpoint_covered_kg", "#d18a22"),
            ("1", "endpoint_covered_kg", "#177f83"),
            ("1", "demand_kg", "#5d59b1"),
        ]
    ):
        bar(
            ax,
            file,
            [field],
            dict(case_id=ident, gamma=gamma),
            i,
            color,
            labels[i],
            "1/1000000000",
            ".6f",
        )
    ax.set_yticks(range(4), labels)
    ax.invert_yaxis()
    d = float(F(maximum["demand_kg"]) / 1000000000)
    ax.set_xlim(0, d * 1.28)
    ax.set_xlabel("Maximum modeled coverage (million tonnes)")
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    fig.text(
        0.04,
        0.07,
        "Declared maximum interval width; α = 0 assumes no additional known supply. This is not a typical or preferred policy.",
        fontsize=9,
    )
    fig.text(
        0.04,
        0.02,
        "The full residual-capped interval starts at zero here. An unrestricted outside upper bound reaches total modeled loss.",
        fontsize=9,
    )
    finish(fig, "maximum_interval")
    (folder / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print("THREE_BOUNDS_FIGURES", sum(len(x["artists"]) for x in manifest))


if __name__ == "__main__":
    main()
