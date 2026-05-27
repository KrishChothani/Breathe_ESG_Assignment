import { useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import { getPlantLookups, deactivatePlant, deletePlantLookup } from '../../api/plantLookup'

const REGION_COLORS = {
  ASIA_PACIFIC:  'bg-emerald-100 text-emerald-700',
  EUROPE:        'bg-blue-100 text-blue-700',
  NORTH_AMERICA: 'bg-violet-100 text-violet-700',
  MIDDLE_EAST:   'bg-amber-100 text-amber-700',
  AFRICA:        'bg-orange-100 text-orange-700',
  LATIN_AMERICA: 'bg-pink-100 text-pink-700',
}

const TYPE_COLORS = {
  MANUFACTURING: 'bg-blue-100 text-blue-700',
  WAREHOUSE:     'bg-cyan-100 text-cyan-700',
  OFFICE:        'bg-slate-100 text-slate-600',
  RETAIL:        'bg-purple-100 text-purple-700',
  CONSTRUCTION:  'bg-yellow-100 text-yellow-700',
  DATA_CENTRE:   'bg-indigo-100 text-indigo-700',
  OTHER:         'bg-gray-100 text-gray-600',
}

const SCOPE_COLORS = {
  SCOPE_1:   'bg-orange-100 text-orange-700',
  SCOPE_2:   'bg-teal-100 text-teal-700',
  SCOPE_1_2: 'bg-rose-100 text-rose-700',
}

const COUNTRY_FLAGS = {
  IN: '🇮🇳', DE: '🇩🇪', GB: '🇬🇧', US: '🇺🇸', AE: '🇦🇪',
  FR: '🇫🇷', JP: '🇯🇵', CN: '🇨🇳', AU: '🇦🇺', BR: '🇧🇷',
  CA: '🇨🇦', ZA: '🇿🇦', SG: '🇸🇬', MX: '🇲🇽', NL: '🇳🇱',
}

function Badge({ label, colorClass }) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  )
}

export default function PlantLookupTable({ refresh, onEdit, onRefresh }) {
  const user = useSelector((s) => s.auth.user)
  const [plants, setPlants]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')
  const [country, setCountry]   = useState('')
  const [region, setRegion]     = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [confirm, setConfirm]   = useState(null)  // { type: 'deactivate'|'delete', plant }

  const fetchPlants = async () => {
    setLoading(true)
    const params = {}
    if (search)  params.search   = search
    if (country) params.country  = country
    if (region)  params.region   = region
    if (activeFilter !== 'all') params.is_active = activeFilter === 'active' ? 'true' : 'false'
    try {
      const res = await getPlantLookups(params)
      setPlants(res.data.results ?? res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPlants() }, [search, country, region, activeFilter, refresh])

  const handleDeactivate = async () => {
    await deactivatePlant(confirm.plant.id)
    setConfirm(null)
    onRefresh()
  }

  const handleDelete = async () => {
    await deletePlantLookup(confirm.plant.id)
    setConfirm(null)
    onRefresh()
  }

  const isAdmin = user?.role === 'ADMIN'

  return (
    <div className="space-y-3">
      {/* Filters bar */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <svg className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by code, name, city…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-2 text-sm w-full rounded-lg border border-slate-200 focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
          />
        </div>
        <select value={country} onChange={(e) => setCountry(e.target.value)}
          className="text-sm rounded-lg border border-slate-200 px-3 py-2 focus:ring-1 focus:ring-emerald-500 outline-none">
          <option value="">All Countries</option>
          {['IN', 'DE', 'GB', 'US', 'AE', 'FR', 'JP', 'AU', 'BR', 'CA'].map((c) => (
            <option key={c} value={c}>{COUNTRY_FLAGS[c] || ''} {c}</option>
          ))}
        </select>
        <select value={region} onChange={(e) => setRegion(e.target.value)}
          className="text-sm rounded-lg border border-slate-200 px-3 py-2 focus:ring-1 focus:ring-emerald-500 outline-none">
          <option value="">All Regions</option>
          {['ASIA_PACIFIC', 'EUROPE', 'NORTH_AMERICA', 'MIDDLE_EAST', 'AFRICA', 'LATIN_AMERICA'].map((r) => (
            <option key={r} value={r}>{r.replace('_', ' ')}</option>
          ))}
        </select>
        <div className="flex rounded-lg border border-slate-200 overflow-hidden text-sm">
          {['all', 'active', 'inactive'].map((f) => (
            <button key={f} onClick={() => setActiveFilter(f)}
              className={`px-3 py-2 capitalize transition-colors ${activeFilter === f ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden relative min-h-[200px]">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="text-slate-500 text-sm">Loading plant codes…</div>
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b border-gray-200 bg-slate-50">
                {['WERKS Code', 'Plant Name', 'Location', 'Region', 'Type', 'Scope', 'SAP Rows', 'Status', ''].map((h) => (
                  <th key={h} className="th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plants.map((p) => (
                <tr key={p.id} className="group hover:bg-slate-50/80 transition-colors">
                  <td className="td">
                    <span className="font-mono font-bold text-slate-800">{p.werks_code}</span>
                  </td>
                  <td className="td font-medium text-slate-700 max-w-[200px]" title={p.plant_name}>
                    {p.plant_name}
                  </td>
                  <td className="td text-slate-500">
                    {COUNTRY_FLAGS[p.country] || ''} {p.city}, <span className="font-mono">{p.country}</span>
                  </td>
                  <td className="td">
                    <Badge label={p.region.replace('_', ' ')} colorClass={REGION_COLORS[p.region] || 'bg-slate-100 text-slate-600'} />
                  </td>
                  <td className="td">
                    <Badge label={p.plant_type.replace('_', ' ')} colorClass={TYPE_COLORS[p.plant_type] || 'bg-slate-100 text-slate-600'} />
                  </td>
                  <td className="td">
                    <Badge label={p.default_scope.replace('_', ' ')} colorClass={SCOPE_COLORS[p.default_scope] || 'bg-slate-100 text-slate-600'} />
                  </td>
                  <td className="td text-center">
                    {p.unresolved_sap_rows > 0 ? (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold bg-rose-100 text-rose-700">
                        {p.unresolved_sap_rows}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="td">
                    <button
                      onClick={() => !p.is_active && setConfirm({ type: 'activate', plant: p })}
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
                        p.is_active
                          ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                          : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${p.is_active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                      {p.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="td">
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {/* Edit */}
                      <button onClick={() => onEdit(p)} title="Edit"
                        className="rounded p-1.5 hover:bg-blue-100 text-blue-600 transition-colors">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {/* Deactivate */}
                      {p.is_active && (
                        <button onClick={() => setConfirm({ type: 'deactivate', plant: p })} title="Deactivate"
                          className="rounded p-1.5 hover:bg-amber-100 text-amber-600 transition-colors">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                          </svg>
                        </button>
                      )}
                      {/* Delete (admin only) */}
                      {isAdmin && (
                        <button onClick={() => setConfirm({ type: 'delete', plant: p })} title="Delete"
                          className="rounded p-1.5 hover:bg-rose-100 text-rose-600 transition-colors">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {plants.length === 0 && !loading && (
                <tr>
                  <td colSpan={9} className="text-center py-8 text-slate-400">
                    No plant codes found. Add one using the button above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirm dialog */}
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-slate-800 mb-2">
              {confirm.type === 'delete' ? '⚠️ Delete Plant Code' : '⚠️ Deactivate Plant Code'}
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              {confirm.type === 'delete'
                ? `Are you sure you want to permanently delete "${confirm.plant.werks_code}"? This cannot be undone.`
                : `This will deactivate "${confirm.plant.werks_code}". Historical rows are preserved but it won't be used in new calculations.`}
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirm(null)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
                Cancel
              </button>
              <button
                onClick={confirm.type === 'delete' ? handleDelete : handleDeactivate}
                className="px-4 py-2 text-sm rounded-lg bg-rose-600 text-white hover:bg-rose-700 font-medium">
                {confirm.type === 'delete' ? 'Delete' : 'Deactivate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
