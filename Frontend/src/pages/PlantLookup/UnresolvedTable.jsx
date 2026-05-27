import { useState, useEffect } from 'react'
import { getUnresolvedWERKS } from '../../api/plantLookup'
import { formatDate } from '../../utils/formatters'

export default function UnresolvedTable({ refresh, onAddLookup }) {
  const [data, setData]   = useState({ total_unresolved_codes: 0, unresolved: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getUnresolvedWERKS()
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [refresh])

  const count = data.total_unresolved_codes

  return (
    <div className="space-y-4">
      {/* Banner */}
      {count > 0 ? (
        <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
          <svg className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-amber-800">
              {count} WERKS code{count !== 1 ? 's' : ''} in your SAP data {count !== 1 ? 'have' : 'has'} no plant lookup entry.
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              Rows with unresolved codes cannot have emissions calculated. Add them below.
            </p>
          </div>
        </div>
      ) : !loading && (
        <div className="flex items-center gap-3 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3">
          <svg className="w-5 h-5 text-emerald-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <p className="text-sm font-medium text-emerald-800">
            All WERKS codes are resolved. No unresolved codes found.
          </p>
        </div>
      )}

      {/* Table */}
      <div className="card p-0 overflow-hidden relative min-h-[200px]">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="text-slate-500 text-sm">Scanning SAP rows…</div>
          </div>
        )}
        {data.unresolved.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 bg-amber-50">
                  {['WERKS Code', 'SAP Rows', 'First Seen', 'Sample Material', ''].map((h) => (
                    <th key={h} className="th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.unresolved.map((row) => (
                  <tr key={row.plant_code} className="group hover:bg-amber-50/50 transition-colors">
                    <td className="td">
                      <span className="font-mono font-bold text-amber-700">{row.plant_code || '(blank)'}</span>
                    </td>
                    <td className="td">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-700">
                        {row.row_count}
                      </span>
                    </td>
                    <td className="td text-slate-500">{formatDate(row.first_seen)}</td>
                    <td className="td text-slate-500 max-w-[200px] truncate" title={row.sample_material}>
                      {row.sample_material || '—'}
                    </td>
                    <td className="td">
                      <button
                        onClick={() => onAddLookup(row.plant_code)}
                        className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors whitespace-nowrap"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                        Add Lookup
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.unresolved.length === 0 && !loading && (
          <div className="py-12 text-center text-slate-400 text-sm">
            No unresolved WERKS codes found in SAP data.
          </div>
        )}
      </div>
    </div>
  )
}
