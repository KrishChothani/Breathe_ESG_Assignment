/**
 * Organisation/index.jsx
 * ======================
 * Members management page for the active organisation.
 * Admins can invite, change roles, and remove members.
 */

import { useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import InviteMemberModal from './InviteMemberModal'
import MemberRow from './MemberRow'

export default function OrganisationPage() {
  const activeOrg  = useSelector((s) => s.organisation.activeOrg)
  const activeRole = useSelector((s) => s.organisation.activeRole)

  const [members,       setMembers]       = useState([])
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [showInvite,    setShowInvite]    = useState(false)
  const [successMsg,    setSuccessMsg]    = useState('')

  const isAdmin = activeRole === 'ADMIN'

  const fetchMembers = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('access_token')
      const res   = await fetch('/api/v1/organisations/members/', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setMembers(await res.json())
    } catch (e) {
      setError('Failed to load members. Please refresh.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchMembers() }, [])

  const handleInvited = (msg) => {
    setShowInvite(false)
    setSuccessMsg(msg)
    fetchMembers()
    setTimeout(() => setSuccessMsg(''), 4000)
  }

  const handleRoleChange = async (memberId, newRole) => {
    const token = localStorage.getItem('access_token')
    const res   = await fetch(`/api/v1/organisations/members/${memberId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ role: newRole }),
    })
    if (res.ok) { fetchMembers() }
  }

  const handleRemove = async (memberId, name) => {
    if (!window.confirm(`Remove ${name} from ${activeOrg?.name}?`)) return
    const token = localStorage.getItem('access_token')
    const res   = await fetch(`/api/v1/organisations/members/${memberId}/`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      setSuccessMsg(`${name} has been removed.`)
      fetchMembers()
      setTimeout(() => setSuccessMsg(''), 4000)
    }
  }

  const ROLE_COUNTS = members.reduce((acc, m) => {
    acc[m.role] = (acc[m.role] || 0) + 1
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50/20 p-8">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
              {activeOrg?.name?.[0] || 'O'}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{activeOrg?.name}</h1>
              <p className="text-sm text-slate-500">
                {activeOrg?.industry} · {activeOrg?.country} ·{' '}
                <span className="font-semibold text-emerald-600">{activeOrg?.subscription_plan}</span>
              </p>
            </div>
          </div>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-emerald-700 transition-all hover:shadow-emerald-200/60 hover:-translate-y-0.5"
          >
            <span className="text-lg leading-none">+</span> Invite Member
          </button>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Members', value: members.length, color: 'from-slate-600 to-slate-800' },
          { label: 'Admins',        value: ROLE_COUNTS.ADMIN   || 0, color: 'from-violet-500 to-purple-700' },
          { label: 'Analysts',      value: ROLE_COUNTS.ANALYST || 0, color: 'from-emerald-500 to-teal-700' },
          { label: 'Auditors',      value: ROLE_COUNTS.AUDITOR || 0, color: 'from-amber-500 to-orange-700' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-2xl bg-white border border-slate-100 shadow-sm p-5">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">{label}</p>
            <p className={`text-3xl font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Success message */}
      {successMsg && (
        <div className="mb-4 flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 font-medium">
          <span>✓</span> {successMsg}
        </div>
      )}

      {/* Members table */}
      <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Members</h2>
          <span className="text-xs text-slate-400">{members.length} active member{members.length !== 1 ? 's' : ''}</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 rounded-full border-2 border-emerald-200 border-t-emerald-600 animate-spin" />
          </div>
        ) : error ? (
          <div className="py-12 text-center text-sm text-red-500">{error}</div>
        ) : members.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-400">No members yet. Invite someone!</div>
        ) : (
          <div className="divide-y divide-slate-50">
            {members.map((m) => (
              <MemberRow
                key={m.id}
                member={m}
                isAdmin={isAdmin}
                onRoleChange={handleRoleChange}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}
      </div>

      {showInvite && (
        <InviteMemberModal
          orgName={activeOrg?.name}
          onInvited={handleInvited}
          onClose={() => setShowInvite(false)}
        />
      )}
    </div>
  )
}
