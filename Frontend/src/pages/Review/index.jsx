import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchRows } from '../../store/emissionsSlice'
import { doApprove, doReject, doLockBatch, toggleSelect, selectAll, clearSelected, setDetailRow } from '../../store/reviewSlice'
import StatusBadge from '../../components/StatusBadge'
import { formatCO2e, formatDate, truncate } from '../../utils/formatters'
import { ROW_STATUS } from '../../utils/constants'
import RowDetailModal from './RowDetailModal'
import BulkActions from './BulkActions'
import ConfirmModal from '../../components/ConfirmModal'
import FailedRowsTable from './FailedRowsTable'
import AuditLogDrawer from '../../components/Drawers/AuditLogDrawer'
import api from '../../api/client'

// Auto-scaling CO₂e cell — used by SAP & Utility (kg below 1000, t above)
const Co2eCell = ({ row }) => (
  <td className="td text-right font-mono group/tooltip relative overflow-visible">
    <span className="border-b border-dashed border-gray-400 cursor-help">{formatCO2e(row.co2e_kg)}</span>
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

// Always-in-tonnes CO₂e cell — used by Travel rows
const TravelCo2eCell = ({ row }) => {
  const kg = row.co2e_kg !== null && row.co2e_kg !== undefined ? parseFloat(row.co2e_kg) : null
  const tonnes = kg !== null ? (kg / 1000).toFixed(4) : null
  return (
    <td className="td text-right font-mono group/tooltip relative overflow-visible">
      <span
        className="border-b border-dashed border-emerald-400 cursor-help"
        title={kg !== null ? `${kg.toFixed(2)} kgCO₂e (raw)` : 'Not calculated'}
      >
        {tonnes !== null ? (
          <span>
            {tonnes} <span className="text-slate-400 font-normal text-[10px]">tCO₂e</span>
          </span>
        ) : '—'}
      </span>
      {row.emission_factor_source && (
        <div className="absolute hidden group-hover/tooltip:block bg-gray-800 text-white text-xs rounded p-2 z-50 bottom-full right-0 mb-1 w-52 shadow-lg text-left">
          <div className="font-semibold mb-1 border-b border-gray-600 pb-1">CO₂ Calculation</div>
          <div>Raw: {kg !== null ? `${kg.toFixed(2)} kg` : '—'}</div>
          <div>Tonnes: {tonnes !== null ? `${tonnes} t` : '—'}</div>
          <div className="mt-1 border-t border-gray-600 pt-1">Source: {row.emission_factor_source}</div>
          <div>Year: {row.emission_factor_year || 'N/A'}</div>
          <div>Scope: {row.ghg_scope?.replace('_', ' ')}</div>
          {row.formula && <div className="mt-1 text-gray-300 italic">{row.formula}</div>}
        </div>
      )}
    </td>
  )
}

const TABS = [
  { key: 'SAP', label: 'SAP Rows' },
  { key: 'UTILITY', label: 'Utility Rows' },
  { key: 'TRAVEL', label: 'Travel Rows' },
  { key: 'FAILED', label: 'Failed Rows' },
]

const SAP_COLS = ['Status', 'Plant', 'Material', 'Qty', 'Unit', 'Date', 'Category', 'CO₂e', '']
const UTIL_COLS = ['Status', 'Meter', 'Site', 'Billing Start', 'Billing End', 'Period', 'kWh', 'CO₂e', '']
const TRAVEL_COLS = ['Status', 'Type', 'Origin', 'Destination', 'Class', 'Dist km', 'CO₂e (tCO₂e)', 'Traveller', '']

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
      <td className="td font-mono text-blue-700">{formatDate(row.billing_start)}</td>
      <td className="td font-mono text-blue-700">{formatDate(row.billing_end)}</td>
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
      <TravelCo2eCell row={row} />
      <td className="td text-xs text-slate-500 max-w-[160px] truncate" title={row.traveller_email}>{row.traveller_email}</td>
    </>
  )
}

export default function Review() {
  const dispatch = useDispatch()
  const { rows, loading: rowsLoading, count } = useSelector((s) => s.emissions)
  const { selected, actionLoading, detailRow } = useSelector((s) => s.review)
  
  const [tab, setTab] = useState('SAP')
  const [scope, setScope] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [auditRow, setAuditRow] = useState(null)
  
  const allIds = rows.map((r) => r.id)

  useEffect(() => {
    dispatch(fetchRows({ type: tab, scope: scope || undefined }))
    dispatch(clearSelected())
  }, [tab, scope, dispatch])

  const handleAction = (action, row) => {
    setConfirm({ action, row })
  }
  const confirmAction = async () => {
    const { action, row } = confirm
    if (action === 'APPROVE') await dispatch(doApprove({ row_id: row.id }))
    if (action === 'REJECT') await dispatch(doReject({ row_id: row.id }))
    setConfirm(null)
    dispatch(fetchRows({ type: tab })) // Refresh rows after action
  }

  const handleLockBatch = async () => {
    await dispatch(doLockBatch(selected))
    dispatch(fetchRows({ type: tab, scope: scope || undefined })) // Refresh rows after lock
    dispatch(clearSelected())
  }

  const handleExport = () => {
    const token = localStorage.getItem('access')
    window.open(`http://127.0.0.1:8000/api/v1/ingestion/export/provenance/?source=${tab}&scope=${scope}&token=${token}`, '_blank')
  }

  const cols = tab === 'SAP' ? SAP_COLS : tab === 'UTILITY' ? UTIL_COLS : TRAVEL_COLS

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-end gap-1 border-b border-gray-200">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            {label}
            {tab === key && (
              <span className="ml-2 rounded-full px-1.5 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-700">
                {count}
              </span>
            )}
          </button>
        ))}
        
        <div className="ml-auto flex items-center gap-3 pb-1">
          <select value={scope} onChange={e => setScope(e.target.value)} className="border-gray-300 rounded text-sm py-1.5 focus:ring-emerald-500 focus:border-emerald-500">
            <option value="">All Scopes</option>
            <option value="SCOPE_1">Scope 1</option>
            <option value="SCOPE_2">Scope 2</option>
            <option value="SCOPE_3">Scope 3</option>
          </select>
          <button onClick={handleExport} className="bg-slate-800 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-slate-700 transition-colors">
            📥 Export for Audit
          </button>
        </div>
      </div>

      {tab === 'FAILED' ? (
        <FailedRowsTable rows={rows} onRefresh={() => dispatch(fetchRows({ type: tab }))} />
      ) : (
        <>
          {/* Bulk actions bar */}
          <BulkActions
            selected={selected}
            allIds={allIds}
            onSelectAll={() => dispatch(selectAll(allIds))}
            onClearAll={() => dispatch(clearSelected())}
            onLock={handleLockBatch}
            loading={actionLoading}
          />

          {/* Table */}
          <div className="card p-0 overflow-hidden relative min-h-[300px]">
            {rowsLoading && (
              <div className="absolute inset-0 bg-white/60 backdrop-blur-sm flex items-center justify-center z-10">
                <div className="text-slate-500 font-medium">Loading rows...</div>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-200 bg-slate-50">
                    <th className="th w-8 px-3">
                      <input type="checkbox"
                        className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                        checked={selected.length === allIds.length && allIds.length > 0}
                        onChange={(e) => dispatch(e.target.checked ? selectAll(allIds) : clearSelected())}
                      />
                    </th>
                    {cols.map((c) => <th key={c} className="th">{c}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      className={`group transition-colors ${
                        row.status === ROW_STATUS.FLAGGED ? 'bg-amber-50/60 hover:bg-amber-50' : 'hover:bg-slate-50/80'
                      }`}
                    >
                      <td className="td w-8">
                        <input type="checkbox"
                          className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                          checked={selected.includes(row.id)}
                          onChange={() => dispatch(toggleSelect(row.id))}
                        />
                      </td>
                      <td className="td"><StatusBadge status={row.status} /></td>
                      {tab === 'SAP' && <SAPCols row={row} />}
                      {tab === 'UTILITY' && <UtilCols row={row} />}
                      {tab === 'TRAVEL' && <TravelCols row={row} />}
                      <td className="td">
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            className="rounded px-2 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                            onClick={() => dispatch(setDetailRow(row))}
                          >Detail</button>
                          <button
                            className="rounded px-2 py-1 text-xs font-medium bg-blue-100 hover:bg-blue-200 text-blue-700 transition-colors"
                            onClick={() => setAuditRow(row)}
                          >Audit</button>
                          {(row.status === ROW_STATUS.PENDING || row.status === ROW_STATUS.FLAGGED) && (
                            <>
                              <button onClick={() => handleAction('APPROVE', row)} className="rounded px-2 py-1 text-xs font-medium bg-emerald-100 hover:bg-emerald-200 text-emerald-700 transition-colors">✓</button>
                              <button onClick={() => handleAction('REJECT', row)} className="rounded px-2 py-1 text-xs font-medium bg-rose-100 hover:bg-rose-200 text-rose-700 transition-colors">✗</button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && !rowsLoading && (
                    <tr>
                      <td colSpan={cols.length + 1} className="text-center py-8 text-slate-400">
                        No rows found for {tab}.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Modals */}
      {auditRow && <AuditLogDrawer row={auditRow} source={tab} onClose={() => setAuditRow(null)} />}
      {detailRow && <RowDetailModal row={detailRow} tab={tab} onClose={() => dispatch(setDetailRow(null))} />}
      <ConfirmModal
        isOpen={!!confirm}
        title={confirm?.action === 'APPROVE' ? 'Approve Row' : 'Reject Row'}
        message={`Are you sure you want to ${confirm?.action?.toLowerCase()} this row? This action will be recorded in the audit trail.`}
        confirmLabel={confirm?.action === 'APPROVE' ? 'Approve' : 'Reject'}
        danger={confirm?.action === 'REJECT'}
        onConfirm={confirmAction}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}
