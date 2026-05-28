import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { login, getMe } from '../../api/auth'
import { setUser } from '../../store/authSlice'
import { setActiveOrganisation, setAvailableOrganisations } from '../../store/organisationSlice'

export default function Login() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [form,    setForm]    = useState({ username: 'adminkrish_cks', password: 'Krish@259' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  // Multi-org selection state
  const [orgs,          setOrgs]          = useState(null)   // array if requires selection
  const [selectingOrg,  setSelectingOrg]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await login(form.username, form.password)

      // Multi-org: server returns a list, not a token yet
      if (data.requires_org_selection) {
        setOrgs(data.organisations)
        dispatch(setAvailableOrganisations(data.organisations))
        setSelectingOrg(true)
        setLoading(false)
        return
      }

      // Single org — token is already stored by login()
      dispatch(setUser(data.user))
      dispatch(setActiveOrganisation({ organisation: data.organisation, role: data.role }))
      navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail ?? err.response?.data?.error
      setError(detail ?? 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectOrg = async (org) => {
    setLoading(true)
    try {
      const { TOKEN_KEY, REFRESH_KEY } = await import('../../utils/constants')
      const token = localStorage.getItem(TOKEN_KEY) || localStorage.getItem('access_token')
      const res = await fetch('/api/v1/organisations/switch/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ organisation_id: org.organisation_id }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data?.error || 'Org switch failed.'); return }

      localStorage.setItem('access_token',  data.access)
      localStorage.setItem('refresh_token', data.refresh)
      // Also store under the canonical app keys so axios client finds them
      localStorage.setItem('breathe_access',  data.access)
      localStorage.setItem('breathe_refresh', data.refresh)
      const { default: client } = await import('../../api/client')
      client.defaults.headers.common['Authorization'] = `Bearer ${data.access}`

      const meRes = await fetch('/api/v1/auth/me/', {
        headers: { Authorization: `Bearer ${data.access}` },
      })
      const meData = await meRes.json()
      dispatch(setUser(meData))
      dispatch(setActiveOrganisation({ organisation: data.organisation, role: data.role }))
      navigate('/dashboard')
    } catch (err) {
      setError('Failed to select organisation. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── Org selection screen ──────────────────────────────────────────────────
  if (selectingOrg && orgs) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30" />
        <div className="relative z-10 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-emerald-600 flex items-center justify-center mb-4 shadow-lg shadow-emerald-900/50">
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd"/>
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white">Select Organisation</h1>
            <p className="text-slate-400 text-sm mt-1">You belong to multiple organisations. Choose one to continue.</p>
          </div>
          <div className="space-y-3">
            {orgs.map((org) => (
              <button
                key={org.organisation_id}
                onClick={() => handleSelectOrg(org)}
                disabled={loading}
                className="w-full flex items-center justify-between bg-white/5 backdrop-blur-sm border border-white/10 hover:border-emerald-500/50 hover:bg-emerald-900/20 rounded-2xl p-5 text-left transition-all group"
              >
                <div>
                  <p className="font-semibold text-white group-hover:text-emerald-300 transition-colors">
                    {org.organisation_name}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">{org.role}</p>
                </div>
                <span className="text-slate-500 group-hover:text-emerald-400 transition-colors text-lg">→</span>
              </button>
            ))}
          </div>
          {error && (
            <div className="mt-4 rounded-lg bg-rose-500/10 border border-rose-500/30 px-4 py-3 text-sm text-rose-300">
              {error}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Normal login form ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-30" />
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-emerald-600 flex items-center justify-center mb-4 shadow-lg shadow-emerald-900/50">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">BreatheESG</h1>
          <p className="text-slate-400 text-sm mt-1">Carbon Accounting Platform</p>
        </div>

        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>
          {error && (
            <div className="mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 px-4 py-3 text-sm text-rose-300">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Username or Email</label>
              <input
                type="text"
                required
                autoFocus
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="block w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
                placeholder="your@email.com or username"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
              <input
                type="password"
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="block w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-colors"
                placeholder="Enter your password"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5 mt-2">
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Signing in…
                </>
              ) : 'Sign in'}
            </button>
          </form>
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">Demo credentials: <span className="text-slate-400 font-mono">adminkrish_cks</span> / <span className="text-slate-400 font-mono">Krish@259</span></p>
        </div>
        <p className="text-center text-xs text-slate-600 mt-4">BreatheESG © 2024 · Enterprise Carbon Accounting</p>
      </div>
    </div>
  )
}
