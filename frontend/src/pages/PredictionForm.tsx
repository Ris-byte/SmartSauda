import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, Info, LoaderCircle, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError, errorMessage } from '../api'
import { ErrorNotice } from '../components'
import { useRemote } from '../hooks'
import type { CatalogModel, Prediction, VehicleType } from '../types'

const numeric = new Set(['manufacture_year', 'km_driven', 'engine_capacity_cc', 'owner_count', 'motor_power_kw'])
function OptionalSelect({ name, label, options }: { name: string; label: string; options: string[] }) {
  return <label className="field"><span>{label}</span><select name={name} defaultValue=""><option value="">Not specified</option>{options.map(value => <option key={value}>{value}</option>)}</select></label>
}
function NumberField({ name, label, min, max, integer = false }: { name: string; label: string; min: number; max: number; integer?: boolean }) {
  return <label className="field"><span>{label}</span><input name={name} type="number" min={min} max={max} step={integer ? 1 : 'any'} placeholder="Optional" /><small className="field-hint">Supported range: {min}–{max}</small></label>
}

export default function PredictionForm({ type, initialBrand }: { type: VehicleType; initialBrand: string }) {
  const navigate = useNavigate()
  const [brand, setBrand] = useState(initialBrand), [model, setModel] = useState(''), [year, setYear] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [retry, setRetry] = useState(0)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const brands = useRemote<string[]>(`/catalog/brands?vehicle_type=${type}`, retry)
  const market = useRemote<{ available: boolean; message: string; price_basis: string }>(`/market-status?vehicle_type=${type}`, retry)
  const models = useRemote<CatalogModel[]>(brand ? `/catalog/models?vehicle_type=${type}&brand=${encodeURIComponent(brand)}` : null, retry)
  const selected = models.data?.find(item => item.model === model)
  const rules = selected?.constraints
  const maxYear = selected ? Math.min(selected.max_year, new Date().getUTCFullYear()) : 0
  const years = selected ? Array.from({ length: Math.max(0, maxYear - selected.min_year + 1) }, (_, i) => maxYear - i) : []
  const electric = rules?.fuel_types.length === 1 && rules.fuel_types[0] === 'Electric'
  const referenceYear = rules?.reference_year ?? new Date().getUTCFullYear()
  const age = year ? Math.max(0, referenceYear - Number(year)) : 0
  const kmMax = rules ? Math.min(rules.km_driven_max, year ? (age ? age * rules.km_per_year_max : 1000) : rules.km_driven_max) : 0
  const marketUnavailable = type === 'Car' && market.data?.available !== true
  const ready = Boolean(selected && rules && year && years.includes(Number(year))) && !models.loading && !brands.loading && !marketUnavailable

  function clearSelection() { setYear(''); setError(''); setFieldErrors({}) }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!ready || busy) return
    const formElement = event.currentTarget
    setError(''); setFieldErrors({}); setBusy(true)
    const values: Record<string, string | number> = { vehicle_type: type, brand, model }
    for (const [name, value] of new FormData(formElement)) {
      const text = String(value).trim()
      if (text) values[name] = numeric.has(name) ? Number(text) : text
    }
    if (electric) values.engine_capacity_cc = 0
    try {
      const prediction = await api<Prediction>('/predictions', { method: 'POST', body: JSON.stringify(values) })
      navigate(`/predictions/${prediction.id}`)
    } catch (issue) {
      const message = errorMessage(issue)
      setError(message)
      if (issue instanceof ApiError) {
        setFieldErrors(Object.fromEntries(issue.fields.map(f => [f.field.replace('body.', ''), f.message || message])))
        const name = issue.fields[0]?.field.replace('body.', '')
        const control = name && formElement.elements.namedItem(name)
        if (control instanceof HTMLElement) control.focus()
      }
    } finally { setBusy(false) }
  }

  return <form className="panel prediction-form" onSubmit={submit}>
    {type === 'Car' && <p className="field-hint">Car estimates use advertised Nepal prices; actual sale prices may differ.</p>}
    <div className="form-section-heading"><span className="step-number">01</span><div><h2>Meet your {type.toLowerCase()}.</h2><p className="muted small">Choose a supported model and manufacture year. Required fields are marked *.</p></div></div>
    {(brands.error || models.error) && <div className="notice"><Info size={18} aria-hidden="true" /><div>We couldn’t load the catalog. Predictions are paused until supported years can be checked. <button type="button" className="inline-button" onClick={() => setRetry(n => n + 1)}>Try again</button>.</div></div>}
    <div className="field-grid">
      <label className="field"><span>Brand *</span><select required value={brand} disabled={brands.loading} onChange={e => { setBrand(e.target.value); setModel(''); clearSelection() }}><option value="">{brands.loading ? 'Loading brands…' : 'Select brand'}</option>{brands.data?.map(b => <option key={b}>{b}</option>)}</select></label>
      <label className="field"><span>Model *</span><select required value={model} disabled={!brand || models.loading || Boolean(models.error)} onChange={e => { setModel(e.target.value); clearSelection() }}><option value="">{models.loading ? 'Loading models…' : 'Select model'}</option>{models.data?.map(m => <option key={m.model}>{m.model}</option>)}</select></label>
      <label className="field"><span>Manufacture year *<small>AD</small></span><select name="manufacture_year" required value={year} disabled={!selected} aria-describedby="year-help" aria-invalid={Boolean(fieldErrors.manufacture_year)} onChange={e => { setYear(e.target.value); setFieldErrors({}) }}><option value="">{selected ? 'Select supported year' : 'Choose a model first'}</option>{years.map(y => <option key={y} value={y}>{y}</option>)}</select><small id="year-help" className="field-hint">{selected ? `Supported dataset years: ${selected.min_year}–${maxYear} AD. These are not verified production dates.` : 'Use the Gregorian year, not Bikram Sambat.'}{rules?.year_basis === 'observed_single_year_padded' && ' Only one year was observed; this window extends by at most one year each side.'}</small>{fieldErrors.manufacture_year && <small className="error-text">{fieldErrors.manufacture_year}</small>}</label>
      <label className="field"><span>Kilometres driven *<small>km</small></span><input name="km_driven" type="number" required min={0} max={kmMax} disabled={!selected} step="any" placeholder="e.g. 30,000" aria-invalid={Boolean(fieldErrors.km_driven)} /><small className="field-hint">{selected ? `Supported for this year: 0–${kmMax.toLocaleString()} km.` : 'Choose a model and year first.'}</small>{fieldErrors.km_driven && <small className="error-text">{fieldErrors.km_driven}</small>}</label>
    </div>
    <details className="optional-details"><summary>My vehicle or year isn’t listed</summary><p className="muted small">We cannot estimate an unsupported model or year. It needs a catalog review and supporting data first. Please use a local appraisal; selecting a different vehicle or year would give a misleading estimate.</p></details>
    <div className="form-section-heading"><span className="step-number">02</span><div><h2>A little more detail.</h2><p className="muted small">Only specifications used by the price model are collected here.</p></div></div>
    {rules ? <div className="field-grid" key={`${brand}/${model}`}>
      {type === 'Car' ? <OptionalSelect name="fuel_type" label="Fuel type" options={rules.fuel_types} /> : <p className="field-hint">Supported fuel: {rules.fuel_types.join(', ')}. Fuel is checked for compatibility but is not a price feature for {type.toLowerCase()}s.</p>}
      {electric ? <div className="field electric-note"><span>Electric vehicle</span><p>Engine capacity is recorded as 0 cc.</p></div> : <NumberField name="engine_capacity_cc" label="Engine capacity (cc)" min={rules.engine_capacity_cc[0]} max={rules.engine_capacity_cc[1]} />}
      {type === 'Car' && <><NumberField name="owner_count" label="Number of owners" min={1} max={year ? Math.min(4, age + 1) : 4} integer /><OptionalSelect name="transmission" label="Transmission" options={rules.transmissions} /><OptionalSelect name="condition" label="Condition" options={['Excellent', 'Good', 'Fair', 'Poor']} /><OptionalSelect name="body_type" label="Body type" options={rules.body_types} /><OptionalSelect name="region" label="Province" options={['Bagmati', 'Gandaki', 'Karnali', 'Koshi', 'Lumbini', 'Madhesh', 'Sudurpashchim']} /></>}
      {rules.motor_power_kw && <NumberField name="motor_power_kw" label="Electric motor power (kW)" min={rules.motor_power_kw[0]} max={rules.motor_power_kw[1]} />}
    </div> : <p className="muted small">Choose a model to see supported specifications.</p>}
    {error && <ErrorNotice>{error}</ErrorNotice>}
    <div className="form-submit"><p><ShieldCheck size={16} aria-hidden="true" />Saved privately to your garage.</p><button type="submit" className="button primary" disabled={busy || !ready}>{busy ? <><LoaderCircle className="spin" size={18} aria-hidden="true" />Calculating your estimate…</> : <>Get my estimate <ArrowRight size={18} aria-hidden="true" /></>}</button></div>
  </form>
}
