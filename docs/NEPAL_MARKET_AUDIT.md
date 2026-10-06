# Nepal vehicle-price data audit

Audit date: 4 October 2026.

**5 October update:** The four-phase replacement workflow, research retraining, external comparison and public car-price safety block are documented in `docs/CAR_MARKET_FOUR_PHASES.md`. This earlier audit describes the preceding state; the replacement candidate is not deployment-approved.

## Decision

The existing car cohort cannot support a reliable current Nepal market valuation claim. Its 1,110 prices all originate from the unverified local source. The bike and scooter cohorts mix that source with historical public listings, with conflicting price levels and several suspicious low prices. A high random-split score does not validate either source against today's market.

The original datasets, model artifacts and active version pointer are preserved. **The active model is still v1.1.0: a historical demonstration, not a corrected or independently validated market model.** No car-price multiplier, INR-to-NPR conversion, guessed replacement price, or new model activation has been applied.

## Implemented safeguards

- `data/processed/market-audit-v1/quarantine.csv`: 1,705 records, comprising 1,110 cars, 471 bikes and 124 scooters. This includes all 1,610 local-source records and 95 additional public records. Multiple review reasons can apply to one record.
- `data/processed/market-audit-v1/public_research_candidates.csv`: 1,611 public-source candidates, comprising 1,329 bikes and 282 scooters. These are candidates for further review, **not approved training data**. Per-row listing URLs and original observation dates are still missing.
- All 3,316 historical records occur exactly once across those two outputs; price labels are unchanged. The earlier four-record quarantine remains separate and unchanged.
- Prices below NPR 20,000 for bikes/scooters trigger manual review, not automatic rejection as false or automatic multiplication. Unknown used status and dates before documented model introductions are also flagged. This threshold is not a complete anomaly detector.
- Grand i10 records before 2013 are flagged using the manufacturer's [launch history](https://www.hyundai.com/in/en/hyundai-story/hyundai-motor-india/history-2011-2015). Historical files are not rewritten.
- Training on the frozen cohort is disabled. The trainer now rejects rows without training eligibility. Exporting a candidate no longer changes the active version by default; explicit activation also requires deployment approval.

The audit script and manifest retain input/output checksums. Reproduce into a new versioned directory rather than overwriting a completed audit:

```powershell
.\.venv\Scripts\python.exe scripts/audit_market_data.py
```

## Car body-type defect

The catalog previously offered SUV for every car. It now exposes model-appropriate SUV, hatchback or sedan categories. The catalog API applies this correction even when the database still contains the old constraints.

For v1.1.0 only, inference derives the original SUV/missing feature encoding from the selected car model. Omitting the optional field or supplying the correct body type therefore produces the same estimate. A sedan is no longer offered or accepted as an SUV. Frozen estimators and metadata remain untouched. This fixes input inconsistency; **it does not fix unreliable price labels**.

## Replacement car collection

`data/external/nepal_car_listings_2026-10-04/listings.csv` contains 79 parsed public asking-price records from [Atal Auto](https://www.atalauto.com/used-cars). Collection checked the site's robots policy and bounded requests to public listing pages. Eighty pages were inspected; one failed parsing and is recorded in the manifest. Saved HTML snapshots, source URLs, capture timestamps, variant text and checksums make the extracted fields reviewable.

This is deliberately a review pool, not a finished dataset:

- Coverage is heavily biased: 76 Hyundai, one Suzuki, one Renault and one Tata. It cannot represent Nepal's car market.
- All 79 remain `review_status=pending`, `training_eligible=False`.
- Collection time is not the original listing date. An available badge is not proof that a listing is recent or that the car remains available.
- Three listings show zero prices, one has another extreme price, and three require odometer review. Model-year, variant, transmission and engine fields also need human verification; passing these simple flags is not approval.
- Prices are seller asking prices, not completed sale prices. No currency uplift or negotiation discount is inferred.
- The first capture's Windows newline conversion was reversed only where the recovered bytes exactly matched the already-recorded SHA-256. All 79 listing snapshots now match their recorded hashes; subsequent collection writes bytes directly.
- Public accessibility does not establish permission to republish the pages. Keep snapshots for internal review and establish reuse terms before redistribution.

Verify the collected evidence without network access:

```powershell
.\.venv\Scripts\python.exe scripts/collect_nepal_car_listings.py --verify-snapshots data/external/nepal_car_listings_2026-10-04/listings.csv
```

## Follow-up evidence review

The current review output is `data/processed/car-listing-review-v3/`. All 79 CSV records were re-extracted from their checksum-verified saved pages. Model names and variant text are separate; i20 Active and Grand i10 Nios are not silently folded into the older models.

- **53 records passed the automated consistency screen; 26 require issue resolution.** Passing is not independent verification or training approval. All 79 still require human review, and their reviewer/date/notes fields are blank.
- Nine descriptions did not provide a parseable price for cross-checking. Four combustion-engine capacities were implausible, including 165, 172, 16,000 and 82,000 cc. Values were flagged, not repaired.
- Three title/description price disagreements were found: [Creta S](https://www.atalauto.com/used-cars/hyundai-creta-s-18) shows NPR 440,000 versus 4,400,000; [Creta SX](https://www.atalauto.com/used-cars/hyundai-creta-sx-49) shows 37,999,000 versus 3,799,000; Santro Xing differs by just NPR 5. The strict cross-check flags disagreements above NPR 1, including small differences; it does not infer which value is correct.
- Other flags include an AMT/manual contradiction, a petrol/diesel contradiction, zero prices, zero odometers and an ambiguous model name. Flag counts overlap.

`review_queue.csv` preserves all original prices, source URLs and evidence hashes alongside flags and blank reviewer fields. `legacy_model_diagnostic.csv` records each comparison's exact model input, output, warnings or exclusion reason. `manifest.json` records input/output, code and model hashes.

### Exploratory comparison, not a market-accuracy score

Of the 53 consistency-screened records, the existing API could price 26: 12 Grand i10, 11 Creta, two Verna and one Nexon. Twenty-seven were unsupported: 21 unknown model identities, five out-of-coverage years and one unsupported fuel. Validation was not bypassed to obtain a larger sample.

For those **26 selected asking-price comparisons**, every prediction was below the advertised price. Mean absolute difference was **NPR 2,122,537 (21.23 lakh)**; median absolute percentage difference was **71.68%**. These figures describe this biased subset only, not Nepal-wide accuracy or completed-sale values. Region and condition were unavailable and used fitted defaults; variants remain unmodeled. The sample is overwhelmingly Hyundai, listing dates are unknown, and seller claims are not independently verified. No multiplier was derived and no model was fitted to these comparisons.

The initial `car-listing-review-v1` diagnostic is superseded: CSV owner counts were initially passed as floats, causing API type rejection. Version 2 converts only whole-valued counts losslessly to integers and retains genuine validation rejections. The v1 diagnostic must not be used as evidence of model coverage.

Version 3 supersedes v2 by supporting additional price notation (`Price =` and `13.75 /- Lakhs`) and screening description-level automatic/manual contradictions. This changes the screened subset; v2's preliminary statistics are not the final results. Original price labels remain unchanged in every version.

Reproduce into a new directory without altering captured data or the active model:

```powershell
.\.venv\Scripts\python.exe scripts/review_nepal_car_listings.py --output data/processed/car-listing-review-reproduction
.\.venv\Scripts\python.exe -m pytest tests/test_car_listing_review.py tests/test_market_audit.py -q
```

## Before retraining or claiming market accuracy

1. Collect diverse, traceable listings across dealers/owners, brands, variants, fuel types, transmission types, model years and regions. Confirm NPR and total asking price rather than down payment, installment or placeholder values. Obtain original listing/update dates where possible; otherwise retain missingness honestly.
2. Review the existing public bike/scooter candidates separately. Resolve low-price and missing-status cases against original evidence; do not promote records merely because their prices look plausible.
3. Normalize model and variant independently; verify engine and electric specifications. Identify reposted vehicles using available listing identifiers/specifications, retaining evidence and review decisions. Do not infer that identical specifications prove identical vehicles.
4. Freeze a separately collected, dated market holdout before tuning, grouping reposts together and preferably holding out a dealer/source or later time period. Do not use the same 79 reviewed listings as both training data and an independent accuracy claim.
5. Record the reviewer, decision, evidence, price basis and approved dataset hash. Only then grant row-level eligibility and enable a new versioned training configuration. Define error tolerances before evaluating the holdout.
6. Report MAE in NPR, percentage error, under/overpricing bias, and coverage by brand/year/variant/source. Compare with a simple baseline and disclose small or unsupported segments. Asking-price accuracy must not be described as transaction-value accuracy.
7. Activate only after that evaluation is accepted. Retraining on the current unverified car labels would reproduce the problem, so no replacement model has been trained in this remediation.
