import { useState, useEffect } from 'react'
import { getNormalisedRows } from '../../api/emissions'
import StatusBadge from '../../components/StatusBadge'
import { formatCO2e, formatDate, truncate } from '../../utils/formatters'
import RowDetailModal from '../Review/RowDetailModal'
import AuditLogDrawer from '../../components/Drawers/AuditLogDrawer'

const TYPES = ['SAP', 'UTILITY', 'TRAVEL']

const Co2eCell = ({ row }) => (
  <td className="td text-right font-mono group/tooltip relative overflow-visible">
    <span className="border-b border-dashed border-gray-400 cursor-help" title="Hover for details">{formatCO2e(row.co2e_kg)}</span>
    {row.emission_factor_source && (
      <div className="absolute hidden group-hover/tooltip:block bg-gray-800 text-white text-xs rounded p-2 z-50 bottom-full right-0 mb-1 w-48 shadow-lg text-left">
        <div className="font-semibold mb-1 border-b border-gray-600 pb-1">Factor Details</div>
        <div>Source: {row.emission_factor_source}</div>
        <div>Year: {row.emission_factor_year || 'N/A'}</div>
        <div>Scope: {row.ghg_scope?.replace('_', ' ')}</div>
        <div>Unit: {row.emission_factor_unit}</div>
      </div>
    )}
  </td>
)

const SAP_COLS = ['Status', 'Plant', 'Material', 'Qty', 'Unit', 'Date', 'Category', 'CO₂e', '']
const UTIL_COLS = ['Status', 'Meter', 'Site', 'Period', 'kWh', 'CO₂e', '']
const TRAVEL_COLS = ['Status', 'Type', 'Origin', 'Destination', 'Class', 'Dist km', 'CO₂e', 'Traveller', '']

function SAPCols({ row }) {
  return (
    <>
      <td className="td">{row.plant_code}</td>
      <td className="td max-w-[200px]" title={row.material_description}>{truncate(row.material_description, 28)}</td>
      <td className="td text-right font-mono">{row.quantity ? parseFloat(row.quantity).toLocaleString() : '—'}</td>
      <td className="td">{row.unit_original}</td>
      <td className="td">{formatDate(row.document_date)}</td>
      <td className="td"><span className="rounded px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs">{row.esg_category}</span></td>
      <Co2eCell row={row} />
    </>
  )
}
function UtilCols({ row }) {
  return (
    <>
      <td className="td font-mono">{row.meter_id}</td>
      <td className="td">{row.site_name}</td>
      <td className="td font-mono">{row.period_month}</td>
      <td className="td text-right font-mono">{row.consumption_kwh ? parseFloat(row.consumption_kwh).toFixed(2) : '—'}</td>
      <Co2eCell row={row} />
    </>
  )
}
function TravelCols({ row }) {
  return (
    <>
      <td className="td"><span className="rounded px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs">{row.segment_type}</span></td>
      <td className="td font-mono">{row.departure_airport_code || row.departure_station || '—'}</td>
      <td className="td font-mono">{row.arrival_airport_code || row.arrival_station || row.hotel_name || '—'}</td>
      <td className="td">{row.cabin_class || row.car_category || row.rail_class || '—'}</td>
      <td className="td text-right font-mono">{row.distance_km ? parseFloat(row.distance_km).toFixed(0) : '—'}</td>
      <Co2eCell row={row} />
      <td className="td text-xs text-slate-500 max-w-[160px] truncate" title={row.traveller_email}>{row.traveller_email}</td>
    </>
  )
}

export default function Audit() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeType, setActiveType] = useState('SAP')
  const [detailRow, setDetailRow] = useState(null)
  const [auditRow, setAuditRow] = useState(null)

  useEffect(() => {
    setLoading(true)
    getNormalisedRows({ type: activeType, status: 'LOCKED' })
      .then(res => setRows(res.data.results ?? res.data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [activeType])

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-800">Audit Ledger</h2>
        <p className="text-sm text-slate-500 mt-1">Read-only view of all LOCKED rows available to auditors.</p>
      </div>

      {/* Type tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TYPES.map(t => (
          <button key={t} onClick={() => setActiveType(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeType === t ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >{t === 'SAP' ? '📦 SAP' : t === 'UTILITY' ? '⚡ Utility' : '✈️ Travel'}</button>
        ))}
      </div>

      <div className="card p-0 overflow-hidden relative min-h-[300px]">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60 z-10">
            <div className="text-slate-500">Loading locked rows...</div>
          </div>
        )}
        {rows.length === 0 && !loading ? (
          <div className="text-center py-16">
            <div className="mx-auto h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd"/>
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-600">No locked rows for {activeType}</p>
            <p className="text-xs text-slate-400 mt-1">Lock approved rows from the Review page to surface them here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 bg-slate-50">
                  {(activeType === 'SAP' ? SAP_COLS : activeType === 'UTILITY' ? UTIL_COLS : TRAVEL_COLS).map((c, i) => <th key={i} className="th">{c}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map(row => (
                  <tr key={row.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="td"><StatusBadge status={row.status} /></td>
                    {activeType === 'SAP' && <SAPCols row={row} />}
                    {activeType === 'UTILITY' && <UtilCols row={row} />}
                    {activeType === 'TRAVEL' && <TravelCols row={row} />}
                    <td className="td">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          className="rounded px-2 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                          onClick={() => setDetailRow(row)}
                        >Detail</button>
                        <button
                          className="rounded px-2 py-1 text-xs font-medium bg-blue-100 hover:bg-blue-200 text-blue-700 transition-colors"
                          onClick={() => setAuditRow(row)}
                        >Audit</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {auditRow && <AuditLogDrawer row={auditRow} source={activeType} onClose={() => setAuditRow(null)} />}
      {detailRow && <RowDetailModal row={detailRow} tab={activeType} onClose={() => setDetailRow(null)} />}
    </div>
  )
}
