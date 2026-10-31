# Incomplete supplier accounts require conditional replacement ranges

31 October 2026 UTC. New source-informed finite uncertainty exercise. All existing source values and source-gate outcomes, including both years, are already visible. No network scenario result has been computed. This is not a blinded or untouched later-year forecast study.

## Preserve the original failed question

The original UN quantity gate and separate FAO 80% common-support gate remain failed. FAO Morocco 2020 common-import coverage is 79.478498%, below the unchanged 80% minimum. The original coverage-gated replacement-network study remains unexecuted. Do not change the threshold, replace countries/years/origins, fill missing flows with zero or describe its source gate as passed.

This distinct deliverable asks: in an explicitly restricted known network, how do conditional bounds on unmeasured outside replacement supply change feasibility classification, and how much can separate-country calculations overclaim a shared pool? A passing release requires a substantive uncertainty model and complete scenario arithmetic; the earlier source hold alone is not a research result. Retain HISTORY_SOURCE_HOLD.json and all its exact source/code/test bytes.

## Source, cohort and accounting identity

Use only the existing separately captured FAO projection, data/fao/source_projection.csv: the fixed three importers, ten origins, Wheat grain item 15/CPC0111, tonnes converted exactly to kg, TM bilateral imports/export mirrors and TCL national import/prior export totals. Do not mix UN values into the analysis. Preserve A official and I imputed flags, all 179 requested positions and all 39 missing values. Native captures and prior independent 4,706-condition source reconciliation remain private/unchanged as appropriate; recheck their hashes and complete factual projection before execution.

Current years are 2019 and 2020; prior routing/export years are 2018 and 2019. For each importer/year, common support is exactly those fixed origins with positive importer and mirror quantities. Source bases are import and mirror current quantities on the same support. Preserve every excluded pair and reason; a restricted-network zero is not evidence of zero physical trade.

For importer i and year y, let W_iy be its positive unique TCL import total and C_iy the sum of common-support import-reported quantities. Define the signed accounting residual r_iy=W_iy-C_iy. Require positive unique national/prior-export totals and r_iy>=0 for all six groups. If negative, stop the residual-envelope analysis; never clamp a discrepancy to zero. These observed nonnegative residuals are accounting differences across compiled sources, not verified unused capacity, a guarantee about omitted suppliers, or national food demand. Preserve all flags/source dates and report the exact residual/coverage accounts.

## Fixed known-network scenario grid

Keep the original authored alpha={0,0.05,0.10,0.25}, beta={0.5,1,2}, ten complete-origin losses, both source bases and both current years: 240 base configurations per year, 480 total. No coefficient is learned or selected. Removing origin k creates importer replacement demands equal to its qualified current-basis quantity, and removes k's replacement supply.

Each remaining origin j has hypothetical additional shared supply alpha times its prior TCL world exports. An observed positive prior import route has extra capacity beta times its prior import amount. All other routes are excluded from the restricted known-route model without asserting physical impossibility. Joint maximum flow maximizes total covered kg; it does not allocate by need, fairness, price, nutrition or political priority. Retain deterministic numeric-code node order, every source/route/demand flow, exact capacities/slacks and all importer accounts. Separate-country optima each claim the same supplier pool; their sum is an authored overpromise benchmark, not an observed policy.

## New conditional outside-supply envelope and sharp bounds

Keep the known-network assumptions fixed. Introduce a virtual outside origin representing unspecified replacement supply, not a real supplier or imputed trade record. For gamma in {0,1/2,1}, let its route caps be gamma*r_iy and its shared supply cap the sum of those route caps. These are authored sensitivity envelopes tied to the accounting residual for scale only. A past missing-import amount does not logically bound future spare supply. Do not call these data-identified real-world capacity bounds.

For each positive gamma, the uncertainty class permits every outside shared supply b in [0,sum_i gamma*r_iy] and every outside route cap u_i in [0,gamma*r_iy]. Unknown outside routes/supply may be zero; they are not filled source values. Let F_0 be the known-only maximum flow and F_gamma the maximum flow with all upper-envelope capacities. The sharp conditional interval for the scenario's optimal total coverage is [F_0,F_gamma]. The corresponding unmet interval is [D-F_gamma,D-F_0], where D is total modeled demand.

Proof: increasing a capacity cannot decrease feasible total flow, so every completion lies between the endpoint optima. Zero outside capacities attain the lower endpoint; all upper capacities attain the upper endpoint. Both completions belong to the declared class. Endpoint flow/cut certificates verify attainability and optimality in this finite network. This theorem does not certify actual shipments or the authored known capacities.

Also retain the assumption-light unrestricted-outside interval [F_0,D]: without an upper outside-supply assumption, arbitrarily large added routes can cover D. This deliberately broad interval shows the cost of unavailable information. A residual-capped upper value is only conditional on its envelope; never substitute it for a fact-derived upper bound.

For each gamma classify: ZERO_MODELED_LOSS if D=0 (loss ratios undefined); KNOWN_NETWORK_SUFFICIENT if F_0=D; CONDITIONAL_SHORTFALL if F_gamma<D; otherwise UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY. The first nonzero class proves feasibility only under known scenario capacities. The shortfall class is conditional on the authored outside cap. The unresolved class must abstain from a point full-replacement claim. Export all classifications and ratios with explicit denominators.

## Execution order, independent evidence and practical exercise

Implement and check meaningful synthetic fixtures first. Run all 2019 configurations as development. Commit a freeze of actual source projections/controls, original history, this protocol, solver, independent cut checker, analysis/input code, requests/tests and every development output before any 2020 scenario summary. Apply identical methods to 2020 with no tuning or outcome-driven subset changes. Both years' source values are already known; later application is not protected predictive validation.

Use exact Fraction arithmetic. Verify nonnegative flows, every source/route/demand capacity and node balance for each endpoint. Independently enumerate all eight importer-side cut subsets; for each subset S, add sum of demands in S and, for each origin, min(source cap, route capacity to importers outside S). Minimum cut must equal the supplied feasible flow total. The independent checker must import no production solver or scenario/input helper. Reconstruct all source support, residuals, demands, known and virtual capacities, classifications, independent-country optima and totals from the original projection.

Retain all 480 base cases and three gamma endpoints each (1,440 exact endpoint evaluations), every allocation, all 11,520 cut-subset certificates and complete importer/source-capacity accounts. Require F_0<=F_half<=F_full<=D and joint<=sum independent-country optima for every endpoint. Keep zero-supply and zero-loss cases. No p-value, confidence interval, probability or population frequency: parameter-grid counts are conditional finite accounting, not independent replications.

The implementation exercise reports the saved scenario interval under an explicit gamma/origin/source-basis contract, or abstains/rejects when its assumptions are absent, a caller seeks a guaranteed shipment, political priority, current shortage probability, actual spare capacity or arbitrary data certification. Present a practical instruction to obtain supplier-specific availability/routing evidence before promising full replacement.

## Presentation, rights and release gates

Lead with the actual finite result, useful decision and limits. Show all six coverage/residual groups, complete classifications by year/basis/gamma and every scenario underneath. Three source-bound figures: source coverage/residuals, classification counts and a declared maximum interval-width illustration (numeric parameter/source/origin tie order), with its complete assumptions and certificates. No preferred policy is selected from the maximum example. Inspect actual SVG geometry/labels/hashes and every rendered manuscript page/table/source binding.

Release requires original hold-byte preservation, native/source reconstruction, meaningful fixtures, actual development dependency freeze before later results, complete independent exact constraints/cuts, two isolated saved-data replays, readable figures/manuscript, bounded privacy checks and exact candidate/main CI/tree/annotated tag/metadata proof. Preserve failed authoring/check receipts and do not average unknown gates into passes. Current uncertainty deliverable review is bounded to at most three produce/check rounds, 45 active review minutes and 60 review-specific calls; earlier source-qualification review remains closed and its failure unchanged. Execution/source acquisition are recorded separately, with supported usage observations rather than invented quota estimates.

Apply DATA_RIGHTS.md and FAO_SOURCE_PLAN.md: minimal attributed FAO/FAOSTAT facts with UNSD/Eurostat upstream restrictions, free bounded independent research, no bulk service/resale or unrestricted third-party license grant. Native exports, private contacts, credentials and unrelated material remain private. Counts of new scenario calculations are not new original source records. This is no new max-flow method, actual capacity/shortage/food-security assessment, causal claim, political allocation recommendation, adoption or realized saving. Independent-program manuscript may be public; Azure and other formal-publication projects remain private.
