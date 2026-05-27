import StatusBadge from '../../components/StatusBadge'
import AnomalyAlert from '../../components/AnomalyAlert'
import { formatCO2e, formatDate, formatNumber } from '../../utils/formatters'

function Field({ label, value }) {
  return (
    <div className="py-2 border-b border-gray-100 last:border-0 flex justify-between items-start gap-4">
      <dt className="text-xs font-medium text-slate-500 shrink-0 w-36">{label}</dt>
      <dd className="text-xs text-slate-800 font-mono text-right break-all">{value ?? '—'}</dd>
    </div>
  )
}

export default function RowDetailModal({ row, tab, onClose }) {
  if (!row) return null

  const sapFields = [
    ['PO Number', row.po_number], ['Line Item', row.line_item],
    ['Material Code', row.material_code], ['Description', row.material_description],
    ['Plant Code (WERKS)', row.plant_code], ['Plant Name', row.plant_name],
    ['Vendor ID', row.vendor_id], ['Quantity', row.quantity],
    ['Unit (Original)', row.unit_original], ['Unit (Normalised)', row.unit_normalised],
    ['Net Value', row.net_value], ['Currency', row.currency],
    ['Document Date', formatDate(row.document_date)], ['ESG Category', row.esg_category],
  ]
  const utilFields = [
    ['Account Number', row.account_number], ['Meter ID', row.meter_id],
    ['Site Name', row.site_name], ['Billing Start', formatDate(row.billing_start)],
    ['Billing End', formatDate(row.billing_end)], ['Period Month', row.period_month],
    ['Consumption (Original)', row.consumption_original], ['Unit (Original)', row.unit_original],
    ['Consumption (kWh)', row.consumption_kwh], ['Grid Factor Used', row.grid_factor_used],
    ['Grid Factor Year', row.grid_factor_vintage_year],
  ]
  const travelFields = [
    ['Report ID', row.report_id], ['Entry ID', row.entry_id],
    ['Traveller', row.traveller_email], ['Expense Type', row.expense_type],
    ['Origin', row.origin], ['Destination', row.destination],
    ['Cabin Class', row.cabin_class], ['Distance (km)', row.distance_km],
    ['Room Nights', row.room_nights], ['Emission Factor Used', row.emission_factor_used],
    ['Travel Date', formatDate(row.travel_date)],
  ]

  const fields = tab === 'SAP' ? sapFields : tab === 'UTILITY' ? utilFields : travelFields

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-xl bg-white rounded-xl border border-gray-200 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-slate-800">Row Detail</h3>
            <StatusBadge status={row.status} />
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-5 py-4">
          <AnomalyAlert flags={row.anomaly_flags ?? []} />

          <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-2 flex items-center justify-between mb-4">
            <span className="text-xs font-medium text-emerald-700">Estimated CO₂e</span>
            <span className="text-sm font-bold text-emerald-800 font-mono">{formatCO2e(row.co2e_kg)}</span>
          </div>

          <dl className="divide-y divide-gray-100">
            {fields.map(([label, value]) => <Field key={label} label={label} value={value} />)}
          </dl>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-200 flex justify-between items-center">
          <span className="text-xs text-slate-400 font-mono">ID: {row.id}</span>
          <button className="btn-secondary text-xs" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
