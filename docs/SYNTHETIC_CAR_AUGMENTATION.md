# Synthetic car data experiment

## Files

- `data/processed/nepal_used_cars_augmented_3000.json` contains the original 677 scraped records plus 2,323 explicitly marked synthetic records, for 3,000 total.
- `scripts/train_augmented_multisite_candidate.py` builds the synthetic set, trains candidate estimators, and evaluates only against held-out scraped rows.
- `models/car-market-candidate-augmented-v1/evaluation.json` contains candidate metrics and training limitations.
- `models/car-market-candidate-augmented-v1/one-off-fortuner-comparison.json` records the same-input, one-off Fortuner comparison.

## Synthetic generation

The generation seed is 42026. Where compatible ads share make/model and are within three model years, 60,000 km, and 500 cc, numeric features and asking prices are interpolated between two records; price receives up to 1.5% noise. Sparse groups retain the source features and get a clipped normal asking-price perturbation with a 2.5% standard deviation and a 5% cap. Each generated record stores its parent record IDs and method. Its status and label explicitly say synthetic. These values simulate plausible rows around the scraped sample; they are not new observations.

Training compares real-only models against models fitted with synthetic examples at 0.25 weight. Five-fold grouped cross-validation holds scraped records out for scoring and only adds synthetic records whose parent records belong to that fold's training portion. The selected augmented candidate uses Random Forest. On the held-out scraped folds it scores NPR 479,709 MAE, 9.42% median absolute percentage error, 4.54% mean signed percentage error, and 85.0% within 30%. The best real-only model under the same folds scores NPR 502,641 MAE, 10.85% median absolute percentage error, 4.30% mean signed percentage error, and 84.9% within 30%.

## Fortuner demonstration and limits

For the illustrative 2011 Fortuner input (assumed 100,000 km, 2,755 cc, diesel, automatic; drivetrain, variant, and condition missing), the scraped-only candidate predicted NPR 47.43 lakh. The augmented candidate predicted NPR 37.72 lakh. The scrape has just two Fortuner ads: a 2009 listing with an unverified 2,000 cc claim and missing odometer, and a 2019 sold listing whose transaction price is unknown. Nine synthetic Fortuner rows derive from these two records; they do not add new evidence. Synthetic augmentation reduced this demonstration by about NPR 9.71 lakh and does not establish a reliable 2011 estimate.

The scored rows are a held-out portion of the same unreviewed scrape, not a fresh independent sample. Synthetic labels may make these scores look better without improving real-world price estimates. Both candidates remain research-only. `models/current.json` still points to `v1.1.0`, and the public car-estimate safeguard remains in place.

Reproduce the experiment with:

```powershell
.\.venv\Scripts\python.exe scripts/train_augmented_multisite_candidate.py
```
