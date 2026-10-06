import { useState } from 'react'
import type { ReactNode } from 'react'
import { ArrowDownToLine, ArrowRight, Bike, CarFront, CircleAlert, LoaderCircle, Scooter } from 'lucide-react'
import { Link } from 'react-router-dom'
import { downloadReport, errorMessage } from './api'
import type { Prediction, VehicleType } from './types'
import { date, money } from './types'
export function VehicleIcon({ type, size = 24 }: { type: VehicleType; size?: number }) {
  if (type === 'Car') return <CarFront size={size} aria-hidden="true" />
  if (type === 'Bike') return <Bike size={size} aria-hidden="true" />
  return <Scooter size={size} aria-hidden="true" />
}
export function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) { return <div className="page-title"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p className="muted">{description}</p>}</div>{action}</div> }
export function UnusedInputs({ fields }: { fields: string[] }) {
  return fields.length ? <aside className="notice" aria-label="Inputs not used for this price"><CircleAlert size={20} aria-hidden="true" /><div><strong>These inputs did not affect your price.</strong><p>{fields.map(field => field.replaceAll('_', ' ')).join(', ')}.</p><p>They are not used by this vehicle’s price model and are excluded from the specifications below and the PDF specification table.</p></div></aside> : null
}
export function ErrorNotice({ children }: { children: ReactNode }) { return <div className="notice error" role="alert"><CircleAlert size={18} aria-hidden="true" /><div>{children}</div></div> }
export function Loading({ text = 'Loading your data…' }: { text?: string }) { return <div className="loading" role="status"><LoaderCircle className="spin" size={20} aria-hidden="true" />{text}</div> }
export function Empty({ title = 'Your next chapter starts here.', description = 'Create your first estimate and it will appear in your garage.' }: { title?: string; description?: string }) { return <div className="empty panel"><div className="empty-icon"><CarFront size={36} aria-hidden="true" /></div><h2>{title}</h2><p className="muted">{description}</p><Link className="button primary" to="/predict">Value a vehicle <ArrowRight size={16} aria-hidden="true" /></Link></div> }
export function ReportButton({ id, small = false }: { id: string; small?: boolean }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function download() { setBusy(true); setError(''); try { await downloadReport(id) } catch (error) { setError(errorMessage(error)) } finally { setBusy(false) } }
  return <div className="report-control"><button className={`button ${small ? 'subtle compact' : 'primary'}`} onClick={() => void download()} disabled={busy}>{busy ? <LoaderCircle size={17} className="spin" aria-hidden="true" /> : <ArrowDownToLine size={17} aria-hidden="true" />}{busy ? 'Preparing report…' : small ? 'PDF report' : 'Download PDF report'}</button>{error && <p className="error-text" role="alert">{error}</p>}</div>
}
export function PredictionList({ predictions }: { predictions: Prediction[] }) {
  return <div className="prediction-list">{predictions.map(row => <article className="prediction-row" key={row.id}><span className="vehicle-icon"><VehicleIcon type={row.specifications.vehicle_type} size={26} /></span><div className="prediction-name"><Link to={`/predictions/${row.id}`}>{row.specifications.brand} {row.specifications.model}</Link><span>{row.specifications.manufacture_year} <i>·</i> {money(row.specifications.km_driven)} km <i>·</i> {row.specifications.vehicle_type}</span></div><time dateTime={row.created_at}>{date(row.created_at)}</time><div className="row-price"><small>NPR</small> {money(row.result.predicted_price)}</div><Link to={`/predictions/${row.id}`} className="icon-button" aria-label={`View ${row.specifications.brand} ${row.specifications.model} estimate`}><ArrowRight size={19} aria-hidden="true" /></Link></article>)}</div>
}
