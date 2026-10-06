import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, Eye, EyeOff, LoaderCircle, ShieldCheck } from 'lucide-react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth-context'
import { api, errorMessage } from '../api'
import { ErrorNotice } from '../components'
export default function AuthPage({ mode }: { mode: 'signin' | 'signup' }) {
  const { user, signIn, loading } = useAuth(), navigate = useNavigate(), [params] = useSearchParams()
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [visible, setVisible] = useState(false)
  const target = params.get('next') || '/dashboard'
  const next = target.startsWith('/') && !target.startsWith('//') && !target.includes('\\') ? target : '/dashboard'
  const signup = mode === 'signup'
  if (user) return <Navigate to={next} replace />
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; setBusy(true); setError('')
    const data = new FormData(event.currentTarget), email = String(data.get('email')), password = String(data.get('password'))
    try {
      if (signup) {
        await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, display_name: String(data.get('display_name')) }) })
        navigate(`/signin?created=1&next=${encodeURIComponent(next)}`); return
      }
      await signIn(email, password); navigate(next, { replace: true })
    } catch (error) { setError(errorMessage(error)) } finally { setBusy(false) }
  }
  return <div className="auth-page"><section className="auth-visual"><img src="/images/nepal-rides-hero.webp" alt="" width="1672" height="941" /><div><p className="eyebrow">YOUR JOURNEY. YOUR GARAGE.</p><h1>GOOD RIDES.<br />SMARTER<br /><span>DECISIONS.</span></h1><p>A space for your vehicles,<br />and the possibilities ahead.</p></div><span className="auth-visual-bottom">SMARTSAUDA &nbsp; / &nbsp; NEPAL</span></section><section className="auth-form-wrap"><p className="eyebrow">{signup ? 'LET’S START SOMETHING GOOD' : 'YOUR GARAGE IS WAITING'}</p><h2>{signup ? 'Make room for your next ride.' : 'Welcome back.'}</h2><p className="muted">{signup ? 'Create an account to save estimates and download your reports.' : 'Sign in to pick up where you left off.'}</p>{params.get('created') && <div className="notice success" role="status">Your account is ready. Sign in to continue.</div>}{params.get('password') === 'changed' && <div className="notice success" role="status">Password updated. Sign in with your new password.</div>}<form onSubmit={submit} key={mode}>{signup && <label className="field"><span>Your name</span><input required name="display_name" autoComplete="name" maxLength={80} placeholder="What should we call you?" /></label>}<label className="field"><span>Email address</span><input required type="email" name="email" autoComplete="email" maxLength={254} placeholder="you@example.com" /></label><label className="field"><span>Password</span><div className="password-input"><input required type={visible ? 'text' : 'password'} name="password" autoComplete={signup ? 'new-password' : 'current-password'} minLength={signup ? 12 : 1} maxLength={128} aria-describedby={signup ? 'password-help' : undefined} placeholder={signup ? 'At least 12 characters' : 'Your password'} /><button type="button" aria-label={visible ? 'Hide password' : 'Show password'} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{signup && <small id="password-help" className="field-hint">Use a unique password of at least 12 characters.</small>}</label>{error && <ErrorNotice>{error}</ErrorNotice>}<button className="button primary full-width" disabled={busy || loading}>{busy ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <ArrowRight size={18} aria-hidden="true" />}{busy ? 'One moment…' : signup ? 'Create my account' : 'Sign in'}</button></form><p className="auth-switch">{signup ? 'Already part of the journey?' : 'New to SmartSauda?'} <Link to={`/${signup ? 'signin' : 'signup'}?next=${encodeURIComponent(next)}`} onClick={() => { setError(''); setVisible(false) }}>{signup ? 'Sign in' : 'Create an account'}</Link></p><div className="auth-privacy"><ShieldCheck size={17} aria-hidden="true" /><span>Your prediction history stays in your account.<br />No public listings. No selling your ride here.</span></div></section></div>
}
