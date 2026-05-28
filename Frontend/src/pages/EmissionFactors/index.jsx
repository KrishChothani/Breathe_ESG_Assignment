/**
 * EmissionFactors/index.jsx
 * Admin-only page: view all emission factor records, see active vs historical,
 * and add new factor versions.
 */
import { useState, useEffect } from 'react'
import { Database, Plus, CheckCircle2, Clock, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { getEmissionFactors } from '../../api/reports'

const SCOPE_LABELS = {
  SCOPE_1: { label: 'Scope 1', color: 'bg-orange-100 text-orange-700' },
  SCOPE_2: { label: 'Scope 2', color: 'bg-blue-100 text-blue-700' },
  SCOPE_3: { label: 'Scope 3', color: 'bg-purple-100 text-purple-700' },
}

const SOURCE_LABELS = {
  CEA_V20:      'CEA V20.0',
  IPCC_2006:    'IPCC 2006',
  IPCC_AR6:     'IPCC AR6',
  DEFRA_2024:   'DEFRA 2024',
  ICAO_2023:    'ICAO 2023',
  INDIA_GHG:    'India GHG',
  GHG_PROTOCOL: 'GHG Protocol',
}

export default function EmissionFactors() {
  const [factors, setFactors]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [activeOnly, setActiveOnly] = useState(false)
  const [scopeFilter, setScopeFilter] = useState('')
  const [expandedId, setExpandedId]   = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (activeOnly) params.active_only = 'true'
      if (scopeFilter) params.scope = scopeFilter
      const res = await getEmissionFactors(params)
      setFactors(res.data.results || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [activeOnly, scopeFilter])

  const grouped = factors.reduce((acc, f) => {
    const key = f.fuel_or_activity_type
    if (!acc[key]) acc[key] = []
    acc[key].push(f)
    return acc
  }, {})

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Database size={22} className="text-emerald-600" />
          <div>
            <h1 className="text-xl font-bold text-slate-800">Emission Factor Registry</h1>
            <p className="text-xs text-slate-500">
              Official GHG factors — CEA V20.0 · IPCC 2006 · DEFRA 2024
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={scopeFilter}
            onChange={e => setScopeFilter(e.target.value)}
            className="input-field text-sm py-1.5 w-36"
          >
            <option value="">All Scopes</option>
            <option value="SCOPE_1">Scope 1</option>
            <option value="SCOPE_2">Scope 2</option>
            <option value="SCOPE_3">Scope 3</option>
          </select>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={e => setActiveOnly(e.target.checked)}
              className="rounded"
            />
            Active only
          </label>
          <button onClick={load} className="btn-secondary py-1.5">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        {['SCOPE_1', 'SCOPE_2', 'SCOPE_3'].map(s => {
          const count  = factors.filter(f => f.scope === s).length
          const active = factors.filter(f => f.scope === s && f.is_active).length
          const cfg    = SCOPE_LABELS[s]
          return (
            <div key={s} className="bg-white rounded-xl border border-slate-200 p-4">
              <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.color} mb-2`}>
                {cfg.label}
              </span>
              <p className="text-2xl font-bold text-slate-800">{active}</p>
              <p className="text-xs text-slate-400">{active} active / {count} total</p>
            </div>
          )
        })}
      </div>

      {/* Factor table */}
      {loading ? (
        <div className="text-center py-10 text-slate-400 text-sm">Loading factors...</div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="th">Activity / Fuel</th>
                <th className="th">Scope</th>
                <th className="th text-right">Factor Value</th>
                <th className="th">Unit</th>
                <th className="th">Source</th>
                <th className="th">FY From</th>
                <th className="th">Status</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {factors.length === 0 && (
                <tr>
                  <td colSpan={8} className="td text-center py-8 text-slate-400">
                    No emission factors found.
                  </td>
                </tr>
              )}
              {factors.map(f => (
                <>
                  <tr
                    key={f.id}
                    className={`hover:bg-slate-50 transition-colors cursor-pointer ${
                      !f.is_active ? 'opacity-50' : ''
                    }`}
                    onClick={() => setExpandedId(expandedId === f.id ? null : f.id)}
                  >
                    <td className="td font-medium">
                      {f.fuel_or_activity_type.replace(/_/g, ' ')}
                    </td>
                    <td className="td">
                      <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${SCOPE_LABELS[f.scope]?.color}`}>
                        {SCOPE_LABELS[f.scope]?.label}
                      </span>
                    </td>
                    <td className="td text-right font-mono font-semibold">
                      {f.factor_value}
                    </td>
                    <td className="td text-slate-500 text-xs">{f.factor_unit}</td>
                    <td className="td">
                      <span className="text-xs bg-slate-100 px-2 py-0.5 rounded">
                        {SOURCE_LABELS[f.source_name] || f.source_name}
                      </span>
                    </td>
                    <td className="td">{f.valid_from_fy}</td>
                    <td className="td">
                      {f.is_active ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-600">
                          <CheckCircle2 size={12} /> Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-slate-400">
                          <Clock size={12} /> Historical
                        </span>
                      )}
                    </td>
                    <td className="td">
                      {expandedId === f.id
                        ? <ChevronUp size={13} className="text-slate-400" />
                        : <ChevronDown size={13} className="text-slate-400" />}
                    </td>
                  </tr>
                  {expandedId === f.id && (
                    <tr key={`${f.id}-detail`} className="bg-slate-50">
                      <td colSpan={8} className="px-4 py-3">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <div>
                            <p className="text-slate-400 uppercase tracking-wide text-[10px]">Source Version</p>
                            <p className="text-slate-700">{f.source_version || '—'}</p>
                          </div>
                          <div>
                            <p className="text-slate-400 uppercase tracking-wide text-[10px]">Valid To FY</p>
                            <p className="text-slate-700">{f.valid_to_fy || 'Current'}</p>
                          </div>
                          <div>
                            <p className="text-slate-400 uppercase tracking-wide text-[10px]">Country</p>
                            <p className="text-slate-700">{f.country_code}</p>
                          </div>
                          <div>
                            <p className="text-slate-400 uppercase tracking-wide text-[10px]">Added</p>
                            <p className="text-slate-700">
                              {new Date(f.created_at).toLocaleDateString('en-IN')}
                            </p>
                          </div>
                          {f.notes && (
                            <div className="col-span-4">
                              <p className="text-slate-400 uppercase tracking-wide text-[10px]">Notes</p>
                              <p className="text-slate-600">{f.notes}</p>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
