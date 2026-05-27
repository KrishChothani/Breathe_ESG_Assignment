import { useState } from 'react'

function Field({ label, val, onChange, type = 'text' }) {
  const isMissing = val === '' || val === null || val === undefined
  return (
    <div>
      <label className="block text-xs font-medium text-slate-700 mb-1">{label}</label>
      <input 
        type={type}
        className={`w-full rounded-lg text-sm transition-colors ${
          isMissing 
            ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500 bg-rose-50/50' 
            : 'border-slate-300 focus:border-amber-500 focus:ring-amber-500'
        }`}
        value={val || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isMissing ? 'Not found — enter manually' : ''}
      />
    </div>
  )
}

export default function ExtractedDataModal({ fileItem, onClose, onSave }) {
  const [data, setData] = useState(fileItem.extractedData || {})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (field, val) => {
    setData(prev => ({ ...prev, [field]: val }))
  }

  const handleConfirm = async () => {
    setSaving(true)
    setError('')
    try {
      await onSave(fileItem.id, data, fileItem.uploadId)
    } catch (err) {
      setError(err.message || 'Failed to save data.')
      setSaving(false)
    }
  }

  const isFailed = data.confidence === 'FAILED'
  const confColors = {
    HIGH: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
    LOW: 'bg-rose-100 text-rose-700 border-rose-200',
    FAILED: 'bg-rose-100 text-rose-700 border-rose-200',
  }
  const confBadge = confColors[data.confidence] || confColors.LOW

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white rounded-t-xl z-10">
          <div>
            <h3 className="text-lg font-bold text-slate-800">Review Extracted Data</h3>
            <p className="text-xs text-slate-500 truncate max-w-sm">{fileItem.file.name}</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto">
          {data.confidence && (
            <div className={`mb-5 flex items-center gap-2 p-3 rounded-lg border ${confBadge}`}>
              <span className="text-sm font-medium">
                {data.confidence === 'HIGH' && "High Confidence"}
                {data.confidence === 'MEDIUM' && "Medium Confidence — Please review carefully"}
                {data.confidence === 'LOW' && "Low Confidence — Verify all fields"}
                {isFailed && "Extraction failed — Enter manually"}
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Field label="Utility Provider" val={data.provider_name} onChange={(v) => handleChange('provider_name', v)} />
            <Field label="Site / Address" val={data.site_name} onChange={(v) => handleChange('site_name', v)} />
            
            <Field label="Account Number" val={data.account_number} onChange={(v) => handleChange('account_number', v)} />
            <Field label="Meter ID" val={data.meter_id} onChange={(v) => handleChange('meter_id', v)} />
            
            <Field label="Period Start" type="date" val={data.billing_period_start} onChange={(v) => handleChange('billing_period_start', v)} />
            <Field label="Period End" type="date" val={data.billing_period_end} onChange={(v) => handleChange('billing_period_end', v)} />
            
            <div className="flex gap-2">
              <div className="flex-1">
                <Field label="Consumption" type="number" val={data.consumption_kwh} onChange={(v) => handleChange('consumption_kwh', v)} />
              </div>
              <div className="w-24">
                <label className="block text-xs font-medium text-slate-700 mb-1">Unit</label>
                <select 
                  className="w-full h-[38px] rounded-lg border-slate-300 text-sm focus:border-amber-500 focus:ring-amber-500"
                  value={data.consumption_unit || 'kWh'}
                  onChange={(e) => handleChange('consumption_unit', e.target.value)}
                >
                  <option value="kWh">kWh</option>
                  <option value="kVAh">kVAh</option>
                </select>
              </div>
            </div>
            
            <div className="flex gap-2">
              <div className="flex-1">
                <Field label="Total Amount" type="number" val={data.total_amount} onChange={(v) => handleChange('total_amount', v)} />
              </div>
              <div className="w-24">
                <label className="block text-xs font-medium text-slate-700 mb-1">Currency</label>
                <input 
                  type="text" 
                  className="w-full h-[38px] rounded-lg border-slate-300 text-sm focus:border-amber-500 focus:ring-amber-500"
                  value={data.currency || ''}
                  onChange={(e) => handleChange('currency', e.target.value)}
                />
              </div>
            </div>

            <Field label="Bill Date" type="date" val={data.bill_date} onChange={(v) => handleChange('bill_date', v)} />
            <Field label="Due Date" type="date" val={data.due_date} onChange={(v) => handleChange('due_date', v)} />
          </div>
          
          {error && <p className="mt-4 text-xs text-rose-600 bg-rose-50 p-3 rounded-lg font-medium">{error}</p>}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 sticky bottom-0 bg-white rounded-b-xl z-10">
          <button className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
          <button 
            className="btn-primary bg-amber-500 hover:bg-amber-600 focus:ring-amber-500 flex items-center gap-2"
            onClick={handleConfirm} 
            disabled={saving}
          >
            {saving ? 'Saving...' : '✓ Confirm & Save to Database'}
          </button>
        </div>
      </div>
    </div>
  )
}
