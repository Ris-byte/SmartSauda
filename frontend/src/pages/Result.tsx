import { useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ErrorNotice, Loading, ReportButton, UnusedInputs } from '../components'
import { useRemote } from '../hooks'
import type { Prediction } from '../types'
import { date, money, modelInputFields } from '../types'
export default function Result() {
  const { id } = useParams(); const [retry, setRetry] = useState(0)
  const { data: row, error, loading } = useRemote<Prediction>(`/predictions/${encodeURIComponent(id || '')}`, retry)
  if (loading) return <Loading text="Opening your saved estimate…" />
  if (error || !row) return <div className="page-wrap"><ErrorNotice>{error || 'Estimate unavailable.'}</ErrorNotice><button className="button secondary" onClick={() => setRetry(value => value + 1)}>Try again</button><Link to="/history" className="text-link">Back to your history</Link></div>
  const name = `${row.specifications.brand} ${row.specifications.model}`
  return <div className="page-wrap">
    <Link to="/history" className="back-link"><ArrowLeft size={16} aria-hidden="true" />Your prediction history</Link>
    <div className="result-heading">
      <div>
        <p className="eyebrow">YOUR RIDE, IN PERSPECTIVE</p>
        <h1>{name}</h1>
        <p className="muted">{row.specifications.manufacture_year} <i>·</i> {money(row.specifications.km_driven)} km <i>·</i> {row.specifications.vehicle_type}</p>
      </div>
      <span className="saved-badge"><CheckCircle2 size={16} aria-hidden="true" />Saved to your garage</span>
    </div>
    <UnusedInputs fields={row.result.ignored_input_fields} />
    <section className="panel valuation result-valuation" aria-label="Estimated resale value">
      <div className="result-valuation-summary">
        <p className="eyebrow">{row.specifications.vehicle_type === 'Car' ? 'NEPAL ASKING-PRICE ESTIMATE' : 'ESTIMATED RESALE VALUE'}</p>
        <p className="valuation-price"><span>NPR</span> {money(row.result.predicted_price)}</p>
        <p className="muted">{row.specifications.vehicle_type === 'Car' ? 'Based on advertised Nepal car prices; actual sale prices may differ.' : 'A starting point for your next conversation.'}</p>
        <div className="valuation-facts">
          <span>Estimated on<strong>{date(row.created_at)}</strong></span>
          <span>Age in {row.result.reference_year || new Date(row.created_at).getUTCFullYear()}<strong>{row.result.vehicle_age} years</strong></span>
        </div>
      </div>
      <div className="result-report">
        <ReportButton id={row.id} />
        <p className="small muted">Your price, vehicle details and limitations in one report.</p>
      </div>
    </section>
    <div className="detail-grid">
      <section className="panel">
        <div className="panel-heading"><h2>The vehicle details</h2><span className="tag">Your saved inputs</span></div>
        <dl className="spec-list">{Object.entries(row.specifications).filter(([field, value]) => value !== null && modelInputFields(row.specifications.vehicle_type).has(field)).map(([field, value]) => <div key={field}><dt>{field.replaceAll('_', ' ')}</dt><dd>{typeof value === 'number' && field !== 'manufacture_year' ? money(value) : value}</dd></div>)}</dl>
      </section>
      <section className="panel">
        <div className="panel-heading"><h2>What to keep in mind</h2></div>
        <ul className="warning-list">{row.result.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}</ul>
        <p className="model-note">Model {row.result.model_version}{row.specifications.vehicle_type === 'Car' ? ' · predicts advertised asking prices' : ` · ${row.result.brand_model_fit_rows} fitting records for this brand/model combination`}</p>
        <Link to="/about#data" className="text-link">How the estimates are built <ArrowRight size={15} aria-hidden="true" /></Link>
      </section>
    </div>
    <div className="bottom-actions">
      <Link className="button secondary" to="/predict">Value another vehicle <ArrowRight size={17} aria-hidden="true" /></Link>
      <Link className="text-link" to="/dashboard">Back to your garage</Link>
    </div>
  </div>
}
