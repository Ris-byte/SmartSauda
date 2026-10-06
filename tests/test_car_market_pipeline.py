"""Replacement data, source separation and research-only release invariants."""
import json

import joblib
import numpy as np
import pandas as pd

from scripts.prepare_car_market import ROOT, OUTPUT as DATA, claim_fields, sha256
from scripts.train_car_market_candidate import OUTPUT as CANDIDATE, frame


def test_required_provenance_and_target_fields_are_retained():
    rows = pd.read_csv(DATA / 'reviewed_records.csv')
    assert len(rows) == 141
    assert rows.record_id.is_unique
    assert rows.source_url.notna().all() and rows.captured_at_utc.notna().all()
    assert rows.price_basis.eq('asking').all() and rows.actual_sale_price_npr.isna().all()
    assert rows.listing_date.isna().all()
    assert {'variant', 'drivetrain', 'condition_claim', 'transmission', 'km_driven'} <= set(rows.columns)
    assert not rows.training_eligible.any() and not rows.independently_verified.any()
    assert not rows.source_id.eq('nepal_user_2000').any()
    manifest = json.loads((DATA / 'manifest.json').read_text())
    for name, entry in manifest['outputs'].items():
        assert sha256(DATA / name) == entry['sha256']


def test_source_separation_and_repost_exclusion():
    development = pd.read_csv(DATA / 'research_development.csv')
    external = pd.read_csv(DATA / 'external_evaluation.csv')
    assert len(development) == 55 and len(external) == 47
    assert set(development.source_id).isdisjoint(external.source_id)
    assert set(development.group_id).isdisjoint(external.group_id)
    assert development.group_id.is_unique and external.group_id.is_unique
    assert development.research_training_eligible.all() and not development.external_evaluation_eligible.any()
    assert external.external_evaluation_eligible.all() and not external.research_training_eligible.any()


def test_fortuner_evidence_does_not_invent_2011_examples_or_sale_prices():
    rows = pd.read_csv(DATA / 'fortuner_evidence.csv')
    assert len(rows) == 6
    assert not rows.manufacture_year.eq(2011).any()
    sold = rows.loc[rows.listing_status.eq('sold')]
    assert len(sold) == 3 and not sold.research_training_eligible.any()
    assert sold.price_basis.eq('asking').all() and sold.actual_sale_price_npr.isna().all()
    assert (rows.research_training_eligible & rows.manufacture_year.eq(2014)).sum() == 1


def test_missing_condition_and_drivetrain_are_not_guessed():
    assert claim_fields('Luxury SUV with premium features') == ('', '')
    assert claim_fields('Excellent comfort and good performance') == ('', '')
    assert claim_fields('4x4, Fresh Condition') == ('4WD', 'Fresh Condition')


def test_candidate_reload_matches_exported_external_predictions():
    report = json.loads((CANDIDATE / 'evaluation.json').read_text())
    assert sha256(CANDIDATE / 'car.joblib') == report['artifact_sha256']
    assert not report['deployment_approved'] and report['validated_segments'] == []
    assert report['active_pointer_unchanged']
    assert json.loads((ROOT / 'models/current.json').read_text())['model_version'] == 'v1.1.0'
    external = pd.read_csv(DATA / 'external_evaluation.csv')
    expected = pd.read_csv(CANDIDATE / 'external_predictions.csv')
    prediction = joblib.load(CANDIDATE / 'car.joblib').predict(frame(external))
    np.testing.assert_allclose(prediction, expected.predicted_price_npr, rtol=1e-12)
    assert report['deployment_blockers']
