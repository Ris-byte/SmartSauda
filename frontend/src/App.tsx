import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth } from './auth'
import Layout from './Layout'
import Home from './pages/Home'
import { Loading } from './components'
const Predict = lazy(() => import('./pages/Predict')), Result = lazy(() => import('./pages/Result')), Dashboard = lazy(() => import('./pages/Dashboard')), History = lazy(() => import('./pages/History')), About = lazy(() => import('./pages/About')), AuthPage = lazy(() => import('./pages/AuthPage')), Profile = lazy(() => import('./pages/Profile'))
export default function App() {
  return <BrowserRouter><AuthProvider><Suspense fallback={<Loading text="Opening SmartSauda…" />}><Routes><Route element={<Layout />}><Route index element={<Home />} /><Route path="about" element={<About />} /><Route path="signin" element={<AuthPage mode="signin" />} /><Route path="signup" element={<AuthPage mode="signup" />} /><Route path="predict" element={<RequireAuth><Predict /></RequireAuth>} /><Route path="predictions/:id" element={<RequireAuth><Result /></RequireAuth>} /><Route path="dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} /><Route path="history" element={<RequireAuth><History /></RequireAuth>} /><Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} /><Route path="*" element={<div className="empty"><p className="eyebrow">404 / WRONG TURN</p><h1>Let’s get you back on the road.</h1><Link to="/" className="button primary">Back to Explore</Link></div>} /></Route></Routes></Suspense></AuthProvider></BrowserRouter>
}
