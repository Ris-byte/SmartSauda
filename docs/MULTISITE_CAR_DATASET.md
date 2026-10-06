# Nepal used-car marketplace capture

## Deliverable and scope

The combined file is `data/processed/nepal_used_cars_multisite.json`. Its `records` array contains normalized advertisements, not certified valuations or completed-sale transactions. The five supplied URLs represent four websites. The capture covers the publicly discoverable inventory on 5 October 2026; it cannot establish that every historical, deleted, private or unlinked advertisement has been recovered.

The crawl captured **682 advertisements**. Five high-confidence reposts were consolidated using matching identity/odometer fields, compatible specifications and at least two byte-identical vehicle photos, leaving **677 main records**. All original advertisements remain represented, including full observations for consolidated records. Other suspected duplicates remain flagged rather than silently deleted. There were no listing-fetch or parser failures.

| Source | Public listings discovered | Assessment |
| --- | ---: | --- |
| UsedCarNepal | 134 | Useful Nepal asking-price source: structured NPR offers, odometer, condition claims and dates. Includes 126 active listings and the eight sold listings linked on the homepage. |
| KTM Car Sales / Baba Basera Auto Group | 330 | Useful dealer archive with publication dates and NPR prices. Many advertisements have expired, and expiry is not proof of sale. Specifications and odometers are sometimes missing or contradictory. |
| Hamro Automobiles | 186 | Useful Nepal dealer inventory with separate available and sold catalogues. Prices and specifications need screening; publication dates generally are not exposed. |
| SeeCar | 32 | Useful Nepal marketplace data. All three pages of its public used-car search were captured, including both sold and unsold entries. Some specifications come from generic model templates. |

All four sources are suitable for **collecting Nepal asking-price research candidates**, not for immediate unreviewed training. Dealer inventories are geographically and commercially selective. SeeCar's `country_of_origin` describes vehicle manufacturing origin; it does not mean that a Kathmandu advertisement is an Indian or Chinese market-price observation.

## Coverage evidence

- UsedCarNepal: listing sitemap, all 11 active catalogue pages, homepage sold cards and related public listing links. The homepage claims 19 successful deals, but exposes only eight sold detail links and no sold pagination/filter. The remaining historical sold inventory is not claimed as collected.
- KTM: advertisement sitemap, all 33 archive pages and related advertisements. No separate public sold archive was found in the discovered navigation. Explicit sold markings, expiry and uncertain availability are distinguished.
- Hamro: both `/car` and `/sold-car`, retaining the catalogue URLs that establish each advertisement's status. Both catalogues expose their listings without pagination.
- SeeCar: `/search-cars?is_used=true`, its frontend's public `POST /api/filter/vehicle` endpoint, and `POST /api/get/vehicle-by-id`. `sale_status=true` is rendered as SOLD by the site's own card component. No account or authentication bypass was used.

Robots rules were captured and checked. Requests were sequential within each host, with at least 0.65 seconds between new requests; separate sites ran concurrently. Snapshots, SHA-256 checksums, request parameters, capture timestamps, discovery manifests and coverage errors are under `data/external/multisite-used-cars-2026-10-05/`.

## Data dictionary and safeguards

The main columns are `source_site`, `source_url`, `listing_id`, `title`, `brand`, `model`, `variant`, `model_year`, `asking_price_npr`, `actual_sale_price_npr`, `odometer_km`, `engine_cc`, `fuel_type`, `transmission`, `drivetrain`, `condition_claim`, `body_type`, `color`, `location`, `ownership_raw`, `listing_status`, `listing_date`, `updated_at_source`, and `captured_at_utc`.

Additional fields include battery capacity, claimed electric range, fuel economy, manufacturing-country claim, raw field evidence, source snapshots, missing fields and quality flags. **Odometer distance is not fuel economy or EV range.** Capture date is not publication date, and an API update date is not a sold date. Missing or ambiguous values remain `null`.

- The target is **advertised asking price in NPR**, including historical advertised amounts on sold pages. SOLD badges and fields named `selling_price` do not establish the negotiated transaction amount. All actual-sale-price labels remain null.
- Raw monetary amounts are retained. Malformed prices are flagged instead of guessed. No inflation correction, currency conversion, uniform multiplier or invented labels are applied.
- Contradictory title/specification years, fuel/transmission claims, description prices, electric displacement, extreme values and stale dates are flagged for review. Automated screening is not physical inspection or independent verification.
- Three KTM advertisements are categorized as "New" while their descriptions and odometers describe vehicles already driven 1,900–3,000 km. They are retained with `vehicle_condition=conflicting_new_used_claims`, not silently relabeled as verified used cars. Exclude these from a strict used-only analysis until reviewed.
- Duplicate links and the same source listing ID are consolidated. Different advertisements with identical brand/model/year/odometer are **possible duplicates**, not automatically assumed to be the same vehicle. Photo hashes were checked for 131 images from suspected matches; only compatible records sharing two exact photos were consolidated. Their `duplicate_observations` retain original URLs, prices, status, dates, fields and evidence. The representative uses the latest exposed listing date, then capture time as a tie-breaker—not proof of the latest market price. Possible-duplicate groups must stay in the same partition during any future train/test split until resolved.
- Seller names, contact details, registration numbers, chassis numbers and engine numbers are omitted from normalized columns. Original public snapshots remain local evidence and should not be republished wholesale.
- Every record remains `training_eligible=false` and `independently_verified=false`. This collection does not change model deployment, the active model pointer or the application's insufficient-data safeguard.

## Fortuner finding

The KTM archive includes a [2009 Toyota Fortuner advertised for NPR 5,150,000](https://www.ktmcarsales.com/buy-cars-kathmandu-nepal/toyota-fortuner-2009/), listed on 19 February 2025. It is expired, has no reliable odometer field, and claims a 2,000 cc diesel engine that requires source verification. It is useful traceable historical asking-price evidence, **not** a verified 2011 comparable or a completed sale. Do not replace its engine specification or infer the missing odometer without further evidence.

## Reproduction

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-scraping.txt
.\.venv\Scripts\python.exe scripts/scrape_multisite_cars.py --crawl
.\.venv\Scripts\python.exe scripts/scrape_multisite_cars.py --seecar
.\.venv\Scripts\python.exe scripts/build_multisite_car_dataset.py
.\.venv\Scripts\python.exe scripts/check_car_duplicate_images.py
.\.venv\Scripts\python.exe scripts/build_multisite_car_dataset.py
.\.venv\Scripts\python.exe -m pytest tests/test_multisite_car_dataset.py -q
```

The capture is resumable and reads existing checksum-verified snapshots. It is intentionally not a freshness refresh. For a new dated collection, change the scraper's `OUTPUT` directory and retain the earlier evidence. Do not run two captures against the same host/output simultaneously.

Before training: resolve possible duplicates and contradictory fields, verify availability and pricing dates, obtain appropriate reuse permission before redistributing source content, review coverage by model/year/variant, and acquire a fresh independent Nepal evaluation set. Neither dealer reputation nor a clean parser makes a price label independently verified.
