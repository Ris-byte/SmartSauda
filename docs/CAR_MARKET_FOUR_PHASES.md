# Car-market replacement: four-phase execution

Target: seller asking prices in NPR observed on Nepal listing pages, not completed-sale valuations. A sold badge does not establish a transaction price. No currency multiplier or fabricated price is permitted.

## Phase 1 - Traceable acquisition

Preserve the old cohort; build separate replacement files with source URL, capture date, original publication date when provided, asking price, mileage, model/variant, drivetrain, transmission and seller-reported condition. Missing fields stay missing. Collect older Fortuners even when the evidence is too old or incomplete for admission. Capture evidence and checksums. Use a separate publisher for external evaluation.

## Phase 2 - Evidence review

Cross-check page fields against descriptions. Conflicting prices, dates, fuel, engine or transmission go to review; do not select the more convenient value. Normalize only explicit equivalent notation. Keep asking prices separate from sale prices. Record machine evidence review as such, not as human or seller verification. Check likely reposts across development and external sets before model fitting.

## Phase 3 - Candidate training and external evaluation

Predeclared protocol: train a research-only asking-price candidate on internally consistent traceable records; missing original listing dates remain a limitation. Use development-only grouped cross-validation to select among a simple baseline, ridge and random forest. Hold the separately collected publisher out of model selection. Exclude likely reposts using brand/model/year/odometer groups and source URLs. This is a heuristic, not proof of independent vehicle identity.

Deployment requires all of the following, set before training: at least 20 reviewed independent external observations overall; at least 10 development and 5 external observations per enabled brand/model/generation segment; median absolute percentage error <=20%; at least 80% of external predictions within 30% of asking price; absolute mean signed percentage error <=10%; MAE better than the baseline. Date freshness, essential specification coverage, and cross-source vehicle independence must also be reviewed and approved. Passing numerical checks alone is insufficient. No segment, including older Fortuners, is enabled merely because the global score passes.

## Phase 4 - Safe application behavior

Until a replacement release passes the complete review, car prediction requests must return `insufficient_verified_market_data` without a price or database insertion. The UI must display "Insufficient verified market data". Bikes and scooters retain their existing historical behavior and warnings. Historical model artifacts remain available for offline diagnostics, not approved car-market valuation.

## Execution status

Execution date: 5 October 2026. The four-phase research workflow has run. **Production car valuation remains deliberately unavailable: the deployment requirements did not pass.** The work does not establish a validated Nepal-wide pricing model.

### Phase 1 outcome

The replacement research pool contains **141 traceable records**: 84 Atal Auto records (79 existing captures plus five Fortuners), 56 separately collected Hamro Automobiles records, and one older Nepal Buy Sell Fortuner reference. Raw pages, robots policies, capture timestamps, URLs and SHA-256 checksums are retained under `data/external/car-market-2026-10-05-external/` and the original October 4 capture directory. No user-supplied local price labels enter the replacement pool.

All records represent advertised asking prices. `actual_sale_price_npr` remains blank. All original listing dates remain unverified; capture dates are recorded separately. Missing variant, drivetrain and condition evidence stays blank rather than being inferred from a model name. Seller condition claims are not independently verified inspections.

Six Fortuner references were retained:

| Year | Advertised NPR lakh | Mileage | Status/admission |
|---|---:|---:|---|
| 2010 | 75 | 118,000 km | Older Nepal Buy Sell reference; excluded |
| 2010 | 55 | 0 on source | Atal sold listing, missing usable odometer; excluded |
| 2014 | 75 | 129,000 km | Internally consistent asking-price research candidate |
| 2014 | 85 | 0 on source | Atal sold listing, missing usable odometer; excluded |
| 2015 | 85 | 116,000 km | Atal sold listing; excluded |
| 2018 | 128 | 60,000 km | Internally consistent asking-price research candidate |

These are references, not today's verified sale values. **No usable 2011 Fortuner example or independent Fortuner evaluation set was established.** A sold badge does not turn an asking amount into a transaction price. A second site's certificate verification failed; its pages were not imported and TLS checks were not bypassed.

### Phase 2 outcome

Current files are in `data/processed/nepal-car-market-v2/`:

- `reviewed_records.csv`: all 141 records with evidence and explicit review limitations.
- `research_development.csv`: 55 Atal records admitted only to research fitting.
- `external_evaluation.csv`: 47 Hamro records, from a separate publisher and never included in fitting.
- `quarantine.csv`: 39 excluded records with reasons.
- `fortuner_evidence.csv`: all six Fortuner references, including exclusions.
- `manifest.json`: frozen output hashes, counts and admission limitations.

Admission uses saved-page consistency screening and source separation, not a fabricated human approval. Standard `training_eligible` remains false; the separate `research_training_eligible` flag authorizes the isolated research trainer only. Sale prices are not mixed with asking prices. Likely reposts are screened by model/year/odometer grouping, but independent vehicle identity is not proven. Additional dealer/document review is required before any production approval.

Version 2 corrects condition extraction so wording such as "excellent comfort" cannot become an "excellent condition" claim. The earlier v1 dataset and candidate are marked superseded and preserved for audit. Price labels were not changed.

### Phase 3 outcome

The research-only replacement is `models/car-market-candidate-v2/`. Development-only three-fold grouped cross-validation selected **log-price ridge regression** over the median baseline and random forest. Features include model/variant, drivetrain, fuel, transmission and seller condition claim, plus year, mileage and engine capacity. Missing inputs use development-fitted imputation; imputation does not establish evidence for the missing specification.

On the 47 separately sourced asking-price records:

| Measure | Candidate | Median baseline |
|---|---:|---:|
| Mean absolute error | NPR 644,511 (6.45 lakh) | NPR 1,128,511 (11.29 lakh) |
| Median absolute percentage error | 13.21% | 32.39% |
| Within 30% of asking price | 80.85% | 44.68% |
| Mean signed percentage error | -13.24% | -0.07% |

The candidate **fails** the predeclared maximum 10% absolute signed-bias threshold. Coverage and provenance also fail deployment requirements. Creta performs substantially worse than the aggregate: approximately 29.21% median percentage error on 14 external examples. No car segment is approved.

The external source is geographically relevant but heavily Hyundai-biased, lacks original listing dates and has incomplete specifications. It was reused after the condition-parser correction, so the final result is an **exploratory external comparison, not a fresh untouched final holdout**. New independent records are required for the final deployment decision. No parameters or price multipliers were tuned on the external labels.

`evaluation.json` contains the full checks, segment statistics, source/code hashes, blockers and environment. The serialized candidate reproduces its exported external predictions. `models/current.json` remains unchanged at `v1.1.0`; the new candidate is not a drop-in active release.

### Phase 4 outcome

- Public car prediction requests now fail before inference and persistence with HTTP 422 and `insufficient_verified_market_data`.
- The frontend displays **Insufficient verified market data**, states that the eventual target is asking price, and disables car estimate submission. Missing market-status responses also keep car estimates disabled.
- Previously saved car amounts remain intact for audit but are withheld from the user-facing history/result price display. Car PDF valuation exports are blocked. Dashboard price aggregates are withheld when unvalidated car records are present.
- Bikes and scooters retain their existing historical estimates and warnings; this work does not validate them against the current market.
- Offline historical diagnostic tools remain available for research. They are not public market-valuation endpoints.

Validation completed: 274 Python tests and 15 subtests passed; the final replacement-data/safety subset passed eight tests; frontend production build and lint passed; all nine Edge browser tests passed, including the car form and direct-API safety block. The rendered car page was visually checked.

**Live-server reload completed on 5 October 2026:** after approval, the updated backend started on port 8000. Its readiness endpoint returned `ready`, its car market-status endpoint returned `available=false` with `insufficient_verified_market_data`, and the frontend on port 5173 returned HTTP 200. The safety policy is now loaded by the running backend. The frontend also fails closed if the market-status endpoint is unavailable.

### Remaining deployment prerequisites

Obtain dated, independently verified Nepal evidence covering the intended variants/generations, particularly older Fortuners. Confirm uncertain specifications and seller conditions, establish cross-source vehicle independence, collect a fresh external holdout, and pass all frozen numerical and evidence requirements. Until then, do not enable the car estimator or describe this candidate as validated.
