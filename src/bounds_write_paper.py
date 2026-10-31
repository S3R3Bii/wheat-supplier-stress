"""Write an evidence-bound conditional supplier-replacement manuscript."""

from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import json, csv, shutil

ROOT = Path(__file__).resolve().parents[1]
bindings = []


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def letters(n):
    s = ""
    while True:
        s = chr(65 + n % 26) + s
        n = n // 26 - 1
        if n < 0:
            return s


def bind(file, path, query=None, op="value"):
    x = load(file)
    if query is not None:
        rr = [r for r in x if all(r[k] == v for k, v in query.items())]
        assert len(rr) == 1
        x = rr[0]
    for k in path:
        x = x[k]
    if op == "unresolved_full":
        x = sum(
            g["classifications"]["UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY"]
            for g in x
            if g["gamma"] == "1"
        )
    elif op == "positive_full":
        x = sum(g["positive_loss_cases"] for g in x if g["gamma"] == "1")
    elif op == "known_overclaims":
        x = sum(g["positive_overclaim_cases"] for g in x if g["gamma"] == "0")
    elif op == "max_known_overclaim":
        x = max(F(g["max_overclaim_kg"]) for g in x if g["gamma"] == "0")
    if op in ["tonnes2", "percent6", "max_known_overclaim"]:
        v = F(x) * (100 if op == "percent6" else F(1, 1000))
        with localcontext() as c:
            c.prec = 80
            digits = 6 if op == "percent6" else 2
            shown = format(
                (Decimal(v.numerator) / Decimal(v.denominator)).quantize(
                    Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN
                ),
                "," + "." + str(digits) + "f",
            )
    elif op == "commas":
        shown = format(int(x), ",")
    else:
        shown = str(x)
    name = "Bound" + letters(len(bindings))
    bindings.append(
        dict(name=name, file=file, path=path, query=query, operation=op, display=shown)
    )
    return chr(92) + name + "{}"


def summary(field, op="value"):
    return bind("results/bounds/summary.json", [field], op=op)


def maximum(field, op="value"):
    return bind(
        "results/bounds/summary.json", ["maximum_interval_illustration", field], op=op
    )


p = (
    r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=.68in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,array,graphicx,xcolor,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue,pdftitle={Return a range when supplier data are incomplete}}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\newcommand{\heading}[1]{\vspace{4pt}{\large\bfseries #1}\par}
%%BINDINGS%%
\begin{document}
{\LARGE\bfseries Return a range when supplier data are incomplete\par}
\vspace{5pt}Independent research program\hfill 31 October 2026 UTC\\
\textit{Not peer reviewed. Source-informed 2019/2020 wheat-network scenario arithmetic.}

\heading{Practical finding}
A planner should not turn missing supplier information into a single replacement promise. Under the full authored outside-capacity envelope, """
    + summary("groups", "unresolved_full")
    + r""" of """
    + summary("groups", "positive_full")
    + r""" positive-loss configurations cannot determine full replacement from the known network alone. The upper endpoint can cover modeled demand; the known-only endpoint cannot. Those cases require supplier-specific availability evidence before a delivery commitment.

Separate-country calculations also overclaim a shared supplier pool in """
    + summary("groups", "known_overclaims")
    + r""" known-only configurations, all on the exporter-mirror basis, with a maximum gap of """
    + summary("groups", "max_known_overclaim")
    + r""" tonnes. No import-basis configuration in this grid has a positive shared-capacity gap. The comparison retains this negative finding rather than implying that every replacement calculation double counts supply.

\heading{What the product returns}
The implementation returns a conditional interval for optimal covered and unmet mass under an explicit historical scenario and outside-capacity contract. It returns an unresolved classification when outside availability determines whether full modeled replacement is possible. It does not promise cargo, estimate a current shortage probability or allocate political priority.

The exercise retains all """
    + summary("base_cases", op="commas")
    + r""" base configurations, """
    + summary("endpoint_evaluations", op="commas")
    + r""" endpoint evaluations and """
    + summary("cut_subsets", op="commas")
    + r""" exact cut-subset certificates. Both years, both source bases, every loss origin and every parameter setting remain available underneath the first-layer finding.

\heading{An earlier failed question is preserved}
The original coverage-gated network study remains unexecuted. Morocco's 2020 FAO common-import share is """
    + bind(
        "data/bounds_support.csv",
        ["coverage"],
        dict(year="2020", importer="143"),
        "percent6",
    )
    + r"""\%, below its unchanged 80\% gate. The original UN attempt also remains failed. This distinct source-informed exercise models a restricted known network and explicit outside-capacity uncertainty; it does not pass, relax or rename that original source requirement.

\heading{The important limitation}
The accounting residual is not measured spare supply. All additional shared supply, route multipliers and outside caps are authored assumptions, applied to compiled historical records. The results are exact within those constraints, with no physical-delivery, food-security, causal, predictive, adoption, scientific-priority or realized-savings claim.

\newpage
\heading{Source support and the signed accounting residual}
Use only the separately captured FAO/FAOSTAT projection: Egypt, Morocco and Tunisia; ten fixed origins; Wheat grain item 15/CPC0111; TM bilateral import/export quantities and TCL national totals. Tonnes are converted exactly to kg without increasing measurement precision. The public projection preserves """
    + summary("source_positions")
    + r""" requested source positions: """
    + summary("positive_source_positions")
    + r""" positive and """
    + summary("missing_source_positions")
    + r""" missing. Among positive positions, """
    + summary("positive_imputed_positions")
    + r""" carry flag I (imputed by a receiving agency); other positive positions carry A (official value). These positions are not independent shipment observations.

A current modeled edge requires positive import and exporter-mirror quantities. Both bases use the identical common-support intersection, while retaining their differing amounts. The signed residual is national imports minus the common-support import-reported mass. All six are nonnegative; no discrepancy is clamped. This residual can reflect omitted flows, source revisions or accounting differences. It is a scale for an authored sensitivity envelope, not a fact-derived future-supply cap.

\begin{center}\small\begin{tabular}{llrrrr}\toprule
Importer & Year & National (t) & Common (t) & Residual (t) & Share (\%)\\\midrule
"""
)
support_rows = load("data/bounds_support.csv")
for r in support_rows:
    q = {k: r[k] for k in ["year", "importer"]}
    p += (
        r["name"]
        + " & "
        + r["year"]
        + " & "
        + " & ".join(
            bind("data/bounds_support.csv", [field], q, op)
            for field, op in [
                ("world_kg", "tonnes2"),
                ("common_import_kg", "tonnes2"),
                ("residual_kg", "tonnes2"),
                ("coverage", "percent6"),
            ]
        )
        + r"\\"
        + "\n"
    )
p += r"""\bottomrule\end{tabular}\end{center}
\begin{center}\includegraphics[width=\linewidth]{images/coverage_and_residual.pdf}\end{center}
The source is compiled and later revised: observed TM/TCL update dates differ, in December 2025 and July 2026. Current historical captures do not recover original operational delivery vintages. Preserve the source-specific country definitions and reporting limitations in FAO\_SOURCE\_PLAN.md. Import and mirror agreement is not independent ground truth. No UN quantity is mixed into these calculations.

\newpage
\heading{Known-network model and authored parameter grid}
For target year $y$ and lost origin $k$, replacement demand $d_i$ is its qualified current-basis amount to importer $i$. Other origin $j$ has hypothetical extra shared supply $s_j=\alpha X_{j,y-1}$ from prior national exports. Its extra route cap is $c_{ji}=\beta M_{ji,y-1}$ on a positive observed prior import link. Lost origin $k$ supplies no replacement. An unavailable route is excluded from this restricted model, not proven physically impossible.

Maximize total covered kg with nonnegative route flows $x_{ji}$ subject to
\[
 \sum_i x_{ji}\le s_j,\qquad x_{ji}\le c_{ji},\qquad
 \sum_j x_{ji}\le d_i.
\]
Use $\alpha\in\{0,.05,.10,.25\}$ and $\beta\in\{.5,1,2\}$, ten complete-origin losses, two current bases and both years. Nothing is fitted or selected. The objective maximizes total modeled coverage; tied allocations do not optimize fairness, nutrition, price or national welfare. Numeric code order makes the returned allocation deterministic.

\heading{Conditional uncertainty class and sharp endpoint bounds}
Let $r_i=W_i-C_i\ge0$ be the accounting residual and $\gamma\in\{0,1/2,1\}$. A virtual outside origin has unknown shared capacity $b$ and route capacities $u_i$ in the class
\[
 0\le b\le\gamma\sum_i r_i,\qquad 0\le u_i\le\gamma r_i.
\]
This is an authored outside-supply model; it is not implied by past imports. Let $F_0$ be the known-only optimum and $F_\gamma$ the optimum at all upper outside capacities. Capacity monotonicity gives $F_0\le F(b,u)\le F_\gamma$. Zero outside capacities attain the lower endpoint and all upper capacities attain the upper endpoint. Thus these are sharp conditional bounds. Unmet mass lies in $[D-F_\gamma,D-F_0]$, where $D=\sum_i d_i$.

Without a finite outside-capacity assumption, the same known-network assumptions allow the wider interval $[F_0,D]$: sufficiently large added routes can cover all modeled demand. Never substitute the residual-capped upper value for a data-identified real-world upper bound.

\heading{Independent finite optimality certificate}
For each of the eight importer-side cut subsets $S$, an origin's best cut placement is independent once $S$ is fixed. The objective is certified by
\[
 F=\min_{S\subseteq I}\left[\sum_{i\in S}d_i+
 \sum_j\min\left(s_j,\sum_{i\notin S}c_{ji}\right)\right].
\]
The virtual origin is included. Every stored nonnegative allocation respects source, route and demand caps and node conservation; its total equals this independently enumerated minimum. This is established max-flow/min-cut reasoning [3], not a new algorithm or a physical feasibility certificate. Separate-country optima each reuse the shared pool, so their sum can exceed the jointly feasible value.

\newpage
\heading{All classification counts, including zero modeled loss}
Each row contains 120 base configurations. K means the known network alone covers modeled demand; S means a shortfall persists even at the conditional upper envelope; U means full replacement depends on unavailable outside-capacity information; Z means zero loss within the restricted modeled support. Z is not proof of zero physical exposure. Loss-normalized ratios are undefined for Z.

\begin{center}\small\begin{tabular}{llrrrrr}\toprule
Year & Basis & $\gamma$ & K & S & U & Z\\\midrule
"""
summary_data = load("results/bounds/summary.json")
class_rows = []
for j, g in enumerate(summary_data["groups"]):
    p += (
        str(g["year"])
        + " & "
        + g["basis"]
        + " & "
        + g["gamma"]
        + " & "
        + " & ".join(
            bind("results/bounds/summary.json", ["groups", j, "classifications", k])
            for k in [
                "KNOWN_NETWORK_SUFFICIENT",
                "CONDITIONAL_SHORTFALL",
                "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY",
                "ZERO_MODELED_LOSS",
            ]
        )
        + r"\\"
        + "\n"
    )
    class_rows.append(dict(index=j, year=g["year"], basis=g["basis"], gamma=g["gamma"]))
p += (
    r"""\bottomrule\end{tabular}\end{center}
\begin{center}\includegraphics[width=.96\linewidth]{images/conditional_classes.pdf}\end{center}
The full-envelope U count is """
    + summary("groups", "unresolved_full")
    + r""" out of """
    + summary("groups", "positive_full")
    + r""" positive-loss configurations, counting both years and bases. The count describes this parameter grid, not the probability of a shortage or the fraction of independent real-world events. No outside supply is observed, and the envelope strengths are sensitivity assumptions rather than validated capacity estimates.

\newpage
\heading{Declared maximum-width illustration and shared-pool comparison}
The protocol requests the maximum interval width, retaining the first case in fixed year, source-basis, numeric parameter and origin order on ties. The selected example is """
    + maximum("year")
    + r""", import basis, loss of """
    + maximum("lost_name")
    + r""", $\alpha="""
    + maximum("alpha")
    + r"""$, $\beta="""
    + maximum("beta")
    + r"""$. Its modeled demand is """
    + maximum("demand_kg", "tonnes2")
    + r""" tonnes. At the full residual envelope, covered mass can range from """
    + maximum("known_covered_kg", "tonnes2")
    + r""" to """
    + maximum("endpoint_covered_kg", "tonnes2")
    + r""" tonnes; unmet mass ranges from """
    + maximum("lower_unmet_kg", "tonnes2")
    + r""" to """
    + maximum("upper_unmet_kg", "tonnes2")
    + r""" tonnes.

\begin{center}\includegraphics[width=\linewidth]{images/maximum_interval.pdf}\end{center}
The example has $\alpha=0$, so no additional known-origin supply is assumed. It is a declared maximum-width sanity/sensitivity case, not a typical loss, recommended policy or forecast. The half-envelope result in the chart comes from this same exact case; it need not equal half its full-envelope optimum because importer demands can bind. An unrestricted outside cap reaches total modeled demand by assumption.

\begin{center}\small\begin{tabular}{llrr}\toprule
Year & Known-only basis & Positive shared overclaims & Maximum gap (t)\\\midrule
"""
)
overclaim_rows = []
for j, g in enumerate(summary_data["groups"]):
    if g["gamma"] != "0":
        continue
    p += (
        str(g["year"])
        + " & "
        + g["basis"]
        + " & "
        + bind("results/bounds/summary.json", ["groups", j, "positive_overclaim_cases"])
        + " & "
        + bind(
            "results/bounds/summary.json",
            ["groups", j, "max_overclaim_kg"],
            op="tonnes2",
        )
        + r"\\"
        + "\n"
    )
    overclaim_rows.append(dict(index=j, year=g["year"], basis=g["basis"]))
p += (
    r"""\bottomrule\end{tabular}\end{center}
The shared-pool penalty is present in only four known-only mirror configurations in this grid. Source-basis sensitivity matters; mirror quantities are not truth and not independent corroboration. Every nonmaximum configuration, importer allocation, real/virtual supplier cap, slack and cut remains in the CSV accounts. No political priority is inferred from a tied maximum-flow allocation.

\newpage
\heading{Validation, execution order and practical use}
Native CSV/SQLite/70-digit Decimal reconciliation rechecks all four capture hashes and """
    + summary("source_positions")
    + r""" requested source positions with 4,706 finite conditions, confirming the original failed gate. The new checker reconstructs source support, residuals, all capacities, complete flows/slacks and every cut without importing production scenario helpers. It passes """
    + bind(
        "results/bounds/INDEPENDENT_2019.json",
        ["independent_sql_fraction_conditions"],
        op="commas",
    )
    + r""" conditions for 2019 and """
    + bind(
        "results/bounds/INDEPENDENT_2020.json",
        ["independent_sql_fraction_conditions"],
        op="commas",
    )
    + r""" for 2020. All 56 authored fixture methods pass, including 20 new outside-boundary cases.

The original 39 source/code/test files remain byte unchanged. A development checker initially compared CSV integer strings directly with JSON integers; its failed receipt/code and unchanged development-result hashes are preserved privately. The checker representation was corrected before the actual 64-dependency development freeze at \texttt{f9d4de7a01a2818461df34c9767395d86d9d3654}. Later-year results use identical frozen methods, with no tuning or outcome-driven subset change. Both years' source values were already visible; this is not protected predictive validation.

Separate full-history CPython 3.10.11 and 3.12.14 replays reproduce all 14 primary files byte for byte, preserving all 23 source-directory files each. Independent summary/exercise checks pass """
    + bind("results/bounds/SUMMARY_EXERCISE_CHECK.json", ["independent_conditions"])
    + r""" conditions. The eight exercise requests return two qualified intervals, two abstentions and four rejections. The product requires a saved scenario and explicit outside envelope; it rejects shipment guarantees, shortage probabilities, political priority and arbitrary caller data.

Run \texttt{python src/bounds\_replay.py --out ../bounds-replay} with the pinned requirements and a new output directory. Before a real delivery promise, obtain supplier-specific available volumes, compatible grain grades, freight/contract constraints and independently dated routing evidence. A mathematically feasible allocation is not an available commercial shipment.

\heading{Limits, sources and publication boundary}
This small country-level grain network omits domestic production, nutrition, inventories, prices, harvest timing and commodity-grade compatibility. Compiled import/mirror sources, imputed values, reporting territories and revision histories can differ. Scenario counts reuse annual inputs and shared origins. No p-value, probability, calibrated confidence interval, current food-risk assessment, causal benefit, deployment or saving is established. Residual-scaled caps are explicit hypotheses, not inferred physical bounds. The original coverage-gated study remains unexecuted.

[1] FAO/FAOSTAT, \href{https://www.fao.org/faostat/en/#data/TM/metadata}{Detailed trade matrix} and \href{https://www.fao.org/faostat/en/#data/TCL/metadata}{Crops and livestock products trade}. Wheat item definitions and source-specific metadata/flags are retained in the source plan and receipts. Authors convert units, filter support and construct new scenarios; publishers are not responsible for these changes and do not endorse them.

[2] \href{https://www.fao.org/contact-us/terms/db-terms-of-use/en/}{FAO database terms}, with \href{https://uncomtrade.org/docs/re-dissemination-of-data/}{UN redistribution} and \href{https://ec.europa.eu/eurostat/help/copyright-notice}{Eurostat copyright} restrictions. Minimal attributed facts only; no bulk/resale service or unrestricted commercial source license. Native exports, contacts, credentials and expressive source material stay private. MIT covers original code.

[3] MIT OpenCourseWare, \href{https://ocw.mit.edu/courses/18-200-principles-of-discrete-applied-mathematics-spring-2024/resources/18200-lecture-15-version-2_mp4/}{Max-Flow Min-Cut Theorem}, established method context. This finite implementation claims no new algorithm or exhaustive scientific priority. Independent-program manuscript, not peer reviewed or formally submitted. Azure and other formal-publication projects remain private.
\end{document}
"""
)
defs = chr(10).join(
    chr(92) + "newcommand{" + chr(92) + b["name"] + "}{" + b["display"] + "}"
    for b in bindings
)
paper = ROOT / "paper"
(paper / "images").mkdir(parents=True, exist_ok=True)
(paper / "main.tex").write_bytes(p.replace("%%BINDINGS%%", defs).encode())
(paper / "bindings.json").write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
(paper / "table_rows.json").write_bytes(
    (
        json.dumps(
            dict(
                source=support_rows,
                classifications=class_rows,
                overclaims=overclaim_rows,
            ),
            indent=2,
        )
        + "\n"
    ).encode()
)
for name in ["coverage_and_residual", "conditional_classes", "maximum_interval"]:
    shutil.copyfile(
        ROOT / "figures" / (name + ".pdf"), paper / "images" / (name + ".pdf")
    )
print("BOUNDS_PAPER_WRITTEN", len(bindings), "used bindings")
