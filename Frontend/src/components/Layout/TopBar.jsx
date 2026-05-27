import { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useLocation, useNavigate } from 'react-router-dom'
import { clearOrganisation, setActiveOrganisation } from '../../store/organisationSlice'
import { clearAuth } from '../../store/authSlice'

const PAGE_TITLES = {
  '/':              'Dashboard',
  '/upload':        'Upload Data',
  '/review':        'Review Queue',
  '/audit':         'Audit Ledger',
  '/plant-lookup':  'WERKS Plant Codes',
  '/organisation':  'Organisation',
}

const ROLE_COLORS = {
  ADMIN:   'bg-violet-50 border-violet-200 text-violet-700',
  ANALYST: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  AUDITOR: 'bg-amber-50 border-amber-200 text-amber-700',
  VIEWER:  'bg-slate-100 border-slate-200 text-slate-600',
}

export default function TopBar() {
  const location   = useLocation()
  const navigate   = useNavigate()
  const dispatch   = useDispatch()
  const user       = useSelector((s) => s.auth.user)
  const activeOrg  = useSelector((s) => s.organisation.activeOrg)
  const activeRole = useSelector((s) => s.organisation.activeRole)
  const availOrgs  = useSelector((s) => s.organisation.availableOrgs)

  const [showOrgMenu, setShowOrgMenu] = useState(false)
  const title = PAGE_TITLES[location.pathname] ?? 'BreatheESG'
  const roleColor = ROLE_COLORS[activeRole] || ROLE_COLORS.VIEWER

  const orgName = activeOrg?.name ?? 'No Organisation'
  const plan    = activeOrg?.subscription_plan

  const handleLogout = () => {
    localStorage.clear()
    dispatch(clearAuth())
    dispatch(clearOrganisation())
    navigate('/login')
  }

  const handleSwitchOrg = async (orgId) => {
    try {
      const token = localStorage.getItem('access_token')
      const res   = await fetch('/api/v1/organisations/switch/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ organisation_id: orgId }),
      })
      const data = await res.json()
      if (res.ok) {
        localStorage.setItem('access_token',  data.access)
        localStorage.setItem('refresh_token', data.refresh)
        dispatch(setActiveOrganisation({ organisation: data.organisation, role: data.role }))
        setShowOrgMenu(false)
        window.location.reload()
      }
    } catch (err) {
      console.error('Org switch failed', err)
    }
  }

  return (
    <header className="fixed top-0 left-56 right-0 z-20 flex h-16 items-center justify-between border-b border-gray-200 bg-white/90 backdrop-blur px-6">
      {/* Page title */}
      <div>
        <h1 className="text-base font-semibold text-slate-800">{title}</h1>
        <p className="text-xs text-slate-400">Enterprise ESG Carbon Accounting</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Organisation pill — clickable if user has multiple orgs */}
        <div className="relative">
          <button
            onClick={() => availOrgs.length > 1 && setShowOrgMenu(!showOrgMenu)}
            className={`flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 ${availOrgs.length > 1 ? 'cursor-pointer hover:bg-slate-200' : 'cursor-default'} transition-colors`}
          >
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-medium text-slate-700">{orgName}</span>
            {plan && (
              <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-700 uppercase tracking-wide">
                {plan}
              </span>
            )}
            {availOrgs.length > 1 && (
              <span className="text-slate-400 text-xs">▾</span>
            )}
          </button>

          {/* Org switcher dropdown */}
          {showOrgMenu && availOrgs.length > 1 && (
            <div className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-slate-200 bg-white shadow-xl z-50 overflow-hidden">
              <div className="p-3 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Switch Organisation</p>
              </div>
              {availOrgs.map((org) => (
                <button
                  key={org.organisation_id}
                  onClick={() => handleSwitchOrg(org.organisation_id)}
                  className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors flex items-center justify-between ${
                    org.organisation_id === activeOrg?.id ? 'bg-emerald-50' : ''
                  }`}
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">{org.organisation_name}</p>
                    <p className="text-xs text-slate-400">{org.role}</p>
                  </div>
                  {org.organisation_id === activeOrg?.id && (
                    <span className="text-emerald-500 text-xs font-bold">Active</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Role badge */}
        {activeRole && (
          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${roleColor}`}>
            {activeRole}
          </span>
        )}

        {/* User info + logout */}
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-white text-xs font-bold">
            {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="hidden sm:block text-right">
            <p className="text-xs font-medium text-slate-700">
              {user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user?.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="ml-1 rounded-lg px-2 py-1 text-xs text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            title="Logout"
          >
            ✕
          </button>
        </div>
      </div>
    </header>
  )
}
