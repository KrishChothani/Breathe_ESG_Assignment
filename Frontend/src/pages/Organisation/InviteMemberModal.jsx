/**
 * InviteMemberModal.jsx
 * =====================
 * Modal for inviting a new user to the active organisation.
 * Admin-only. Sends POST /api/v1/organisations/members/invite/
 */

import { useState } from 'react'
import client from '../../api/client'

const ROLES = ['ANALYST', 'AUDITOR', 'VIEWER', 'ADMIN']

export default function InviteMemberModal({ orgName, onInvited, onClose }) {
  const [email,     setEmail]     = useState('')
  const [role,      setRole]      = useState('ANALYST')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await client.post('/organisations/members/invite/', { email, role })
      onInvited(`${email} has been invited as ${role}.`)
    } catch (err) {
      const data = err.response?.data
      setError(data?.email?.[0] || data?.error || data?.detail || 'Failed to invite member.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-emerald-50 to-teal-50">
          <div>
            <h2 className="text-base font-bold text-slate-900">Invite Team Member</h2>
            <p className="text-xs text-slate-500 mt-0.5">Adding to <strong>{orgName}</strong></p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:text-slate-700 hover:bg-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5" htmlFor="invite-email">
              Email Address
            </label>
            <input
              id="invite-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@company.com"
              className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all"
            />
            <p className="mt-1 text-xs text-slate-400">
              If no account exists, one will be created automatically.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5" htmlFor="invite-role">
              Role
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ROLES.map((r) => (
                <label
                  key={r}
                  className={`flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 cursor-pointer transition-all ${
                    role === r
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r}
                    checked={role === r}
                    onChange={() => setRole(r)}
                    className="accent-emerald-600"
                  />
                  <div>
                    <p className="text-xs font-semibold text-slate-700">{r}</p>
                    <p className="text-[10px] text-slate-400 leading-tight">
                      {r === 'ADMIN'   && 'Full access'}
                      {r === 'ANALYST' && 'Upload & review'}
                      {r === 'AUDITOR' && 'Read locked rows'}
                      {r === 'VIEWER'  && 'Read only'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-emerald-600 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-all shadow-sm hover:shadow-emerald-200"
            >
              {loading ? 'Sending Invite…' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
