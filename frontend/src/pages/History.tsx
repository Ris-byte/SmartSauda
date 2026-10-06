import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowLeft, ArrowRight, Plus, Search } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Empty, ErrorNotice, Loading, PageTitle, PredictionList } from '../components'
import { useRemote } from '../hooks'
import type { History as HistoryData, VehicleType } from '../types'
import { vehicleTypes } from '../types'
export default function History() {
  const [params, setParams] = useSearchParams(), [retry, setRetry] = useState(0)
  const type = vehicleTypes.includes(params.get('type') as VehicleType) ? params.get('type')! : ''
  const page = Math.min(12501, Math.max(1, Math.floor(Number(params.get('page')) || 1)))
  const query = new URLSearchParams({ limit: '8', offset: String((page - 1) * 8) })
  if (type) query.set('vehicle_type', type)
  if (params.get('search')) query.set('search', params.get('search')!.slice(0, 160))
  if (params.get('from')) query.set('date_from', `${params.get('from')}T00:00:00+05:45`)
  if (params.get('to')) query.set('date_to', `${params.get('to')}T23:59:59+05:45`)
  const { data, loading, error } = useRemote<HistoryData>(`/predictions?${query}`, retry)
  function filter(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget), next = new URLSearchParams(); for (const [key, value] of form) if (String(value).trim()) next.set(key, String(value).trim()); setParams(next) }
  function turnPage(value: number) { const next = new URLSearchParams(params); next.set('page', String(value)); setParams(next) }
  return <div className="page-wrap"><PageTitle eyebrow="EVERY ESTIMATE. ALL TOGETHER." title="YOUR PREDICTION HISTORY." description="Revisit a vehicle, compare your estimates or pick up a report." action={<Link to="/predict" className="button primary"><Plus size={18} aria-hidden="true" />New estimate</Link>} /><form className="filter-bar panel" onSubmit={filter} key={params.toString()}><label className="field search-field"><span>Search vehicles</span><div className="input-icon"><Search size={17} aria-hidden="true" /><input name="search" placeholder="Brand or model" maxLength={160} defaultValue={params.get('search') || ''} /></div></label><label className="field"><span>Vehicle type</span><select name="type" defaultValue={type}><option value="">All vehicles</option>{vehicleTypes.map(item => <option key={item}>{item}</option>)}</select></label><label className="field"><span>From date</span><input type="date" name="from" defaultValue={params.get('from') || ''} /></label><label className="field"><span>To date</span><input type="date" name="to" defaultValue={params.get('to') || ''} /></label><button className="button secondary">Apply filters</button>{params.size > 0 && <button type="button" className="inline-button" onClick={() => setParams({})}>Clear</button>}</form>{loading ? <Loading /> : error ? <><ErrorNotice>{error}</ErrorNotice><button className="button secondary" onClick={() => setRetry(value => value + 1)}>Try again</button></> : data && <>{data.items.length ? <section className="panel"><div className="panel-heading"><h2>Saved estimates</h2><span className="muted small">{data.total} result{data.total !== 1 ? 's' : ''}</span></div><PredictionList predictions={data.items} /></section> : <Empty title={params.size ? 'No rides on this stretch.' : undefined} description={params.size ? 'Try another brand, date range or vehicle type.' : undefined} />}<div className="pagination"><span className="small muted">{data.total ? `${(page - 1) * 8 + 1}–${Math.min(page * 8, data.total)} of ${data.total} estimates` : 'No estimates to show'}</span><div><button className="button subtle compact" disabled={page === 1} onClick={() => turnPage(page - 1)}><ArrowLeft size={15} aria-hidden="true" />Previous</button><button className="button subtle compact" disabled={page * 8 >= data.total} onClick={() => turnPage(page + 1)}>Next<ArrowRight size={15} aria-hidden="true" /></button></div></div></>}</div>
}
