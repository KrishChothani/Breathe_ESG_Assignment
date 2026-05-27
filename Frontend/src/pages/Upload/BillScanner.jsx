import { useState, useCallback, useEffect } from 'react'
import { extractBill, confirmBill } from '../../api/ingestion'

const LOADING_STEPS = [
  "Reading your bill...",
  "Identifying fields...",
  "Almost done..."
]

export default function BillScanner({ onSuccess }) {
  const [step, setStep] = useState(1) // 1: Upload, 2: Review, 3: Success
  const [file, setFile] = useState(null)
  
  // Upload & extraction state
  const [dragging, setDragging] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [loadingText, setLoadingText] = useState(LOADING_STEPS[0])
  const [extractError, setExtractError] = useState('')
  
  // API result state
  const [uploadId, setUploadId] = useState(null)
  const [extractedData, setExtractedData] = useState({})
  
  // Confirmation state
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [successData, setSuccessData] = useState(null)

  // Rotate loading text
  useEffect(() => {
    if (!extracting) return
    let i = 0
    const interval = setInterval(() => {
      i = (i + 1) % LOADING_STEPS.length
      setLoadingText(LOADING_STEPS[i])
    }, 1500)
    return () => clearInterval(interval)
  }, [extracting])

  // File Drop
  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]; if (f) setFile(f)
  }, [])

  // Call OCR Extract API
  const handleExtract = async () => {
    if (!file) return
    setExtracting(true)
    setExtractError('')
    try {
      const res = await extractBill(file)
      setUploadId(res.data.upload_id)
      
      // Default nulls to empty string for the controlled form inputs
      const raw = res.data.extracted || {}
      const initForm = {}
      for (const [k, v] of Object.entries(raw)) {
        initForm[k] = v === null ? '' : v
      }
      // Keep confidence
      initForm.confidence = raw.confidence
      
      setExtractedData(initForm)
      setStep(2)
    } catch (err) {
      setExtractError(err.response?.data?.error || 'Extraction failed')
    } finally {
      setExtracting(false)
    }
  }

  // Handle Input Changes
  const handleChange = (field, val) => {
    setExtractedData(prev => ({ ...prev, [field]: val }))
  }

  // Call Confirm API
  const handleConfirm = async () => {
    setSaving(true)
    setSaveError('')
    try {
      const res = await confirmBill(uploadId, extractedData)
      setSuccessData({
        provider: extractedData.provider_name || 'Unknown',
        period: `${extractedData.billing_period_start || '?'} to ${extractedData.billing_period_end || '?'}`,
        consumption: res.data.consumption_kwh,
      })
      setStep(3)
      onSuccess?.()
    } catch (err) {
      setSaveError(err.response?.data?.error || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  // Reset to start
  const reset = () => {
    setStep(1)
    setFile(null)
    setUploadId(null)
    setExtractedData({})
    setSuccessData(null)
  }

  if (step === 3) {
    return (
      <div className="text-center py-6">
        <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-emerald-100 flex items-center justify-center">
          <svg className="h-8 w-8 text-emerald-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-slate-800">Bill saved successfully</h3>
        <p className="text-sm text-slate-500 mb-6">The utility row is now in your review queue.</p>
        
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 max-w-sm mx-auto mb-6 text-left text-sm text-slate-700">
          <div className="flex justify-between mb-2">
            <span className="text-slate-500">Provider</span>
            <span className="font-medium">{successData.provider}</span>
          </div>
          <div className="flex justify-between mb-2">
            <span className="text-slate-500">Period</span>
            <span className="font-medium">{successData.period}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Consumption</span>
            <span className="font-medium">{successData.consumption ? `${successData.consumption} kWh` : '—'}</span>
          </div>
        </div>

        <button className="btn-primary" onClick={reset}>Scan Another Bill</button>
      </div>
    )
  }

  if (step === 2) {
    const isFailed = extractedData.confidence === 'FAILED'
    const confColors = {
      HIGH: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
      LOW: 'bg-rose-100 text-rose-700 border-rose-200',
      FAILED: 'bg-rose-100 text-rose-700 border-rose-200',
    }
    const confBadge = confColors[extractedData.confidence] || confColors.LOW
    
    return (
      <div>
        <div className={`mb-4 flex items-center gap-2 p-3 rounded-lg border ${confBadge}`}>
          <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {isFailed ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            )}
          </svg>
          <span className="text-sm font-medium">
            {extractedData.confidence === 'HIGH' && "High Confidence"}
            {extractedData.confidence === 'MEDIUM' && "Medium Confidence — Please review carefully"}
            {extractedData.confidence === 'LOW' && "Low Confidence — Verify all fields"}
            {isFailed && "Extraction failed — Enter manually"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Utility Provider" val={extractedData.provider_name} onChange={(v) => handleChange('provider_name', v)} />
          <Field label="Site / Address" val={extractedData.site_name} onChange={(v) => handleChange('site_name', v)} />
          
          <Field label="Account Number" val={extractedData.account_number} onChange={(v) => handleChange('account_number', v)} />
          <Field label="Meter ID" val={extractedData.meter_id} onChange={(v) => handleChange('meter_id', v)} />
          
          <Field label="Period Start" type="date" val={extractedData.billing_period_start} onChange={(v) => handleChange('billing_period_start', v)} />
          <Field label="Period End" type="date" val={extractedData.billing_period_end} onChange={(v) => handleChange('billing_period_end', v)} />
          
          <div className="flex gap-2">
            <div className="flex-1">
              <Field label="Consumption" type="number" val={extractedData.consumption_kwh} onChange={(v) => handleChange('consumption_kwh', v)} />
            </div>
            <div className="w-24">
              <label className="block text-xs font-medium text-slate-700 mb-1">Unit</label>
              <select 
                className="w-full h-[38px] rounded-lg border-slate-300 text-sm focus:border-amber-500 focus:ring-amber-500"
                value={extractedData.consumption_unit}
                onChange={(e) => handleChange('consumption_unit', e.target.value)}
              >
                <option value="kWh">kWh</option>
                <option value="kVAh">kVAh</option>
              </select>
            </div>
          </div>
          
          <div className="flex gap-2">
            <div className="flex-1">
              <Field label="Total Amount" type="number" val={extractedData.total_amount} onChange={(v) => handleChange('total_amount', v)} />
            </div>
            <div className="w-24">
              <label className="block text-xs font-medium text-slate-700 mb-1">Currency</label>
              <input 
                type="text" 
                className="w-full h-[38px] rounded-lg border-slate-300 text-sm focus:border-amber-500 focus:ring-amber-500"
                value={extractedData.currency}
                onChange={(e) => handleChange('currency', e.target.value)}
              />
            </div>
          </div>

          <Field label="Bill Date" type="date" val={extractedData.bill_date} onChange={(v) => handleChange('bill_date', v)} />
          <Field label="Due Date" type="date" val={extractedData.due_date} onChange={(v) => handleChange('due_date', v)} />
        </div>

        {saveError && <p className="mt-4 text-xs text-rose-600 bg-rose-50 p-2 rounded">{saveError}</p>}

        <div className="mt-6 flex justify-between border-t border-slate-200 pt-4">
          <button className="text-sm font-medium text-slate-500 hover:text-slate-700" onClick={reset}>
            ← Upload Different Bill
          </button>
          <button 
            className="btn-primary bg-amber-500 hover:bg-amber-600 focus:ring-amber-500 flex items-center gap-2"
            onClick={handleConfirm} 
            disabled={saving}
          >
            {saving ? 'Saving...' : '✓ Confirm and Save'}
          </button>
        </div>
      </div>
    )
  }

  // STEP 1: Upload Form
  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !extracting && document.getElementById('ocr-file-input').click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? 'border-amber-400 bg-amber-50' : 'border-gray-300 hover:border-amber-400 hover:bg-slate-50'
        } ${extracting ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <input id="ocr-file-input" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" className="hidden" onChange={(e) => setFile(e.target.files[0])} />
        
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-amber-50 flex items-center justify-center">
          <svg className="h-6 w-6 text-amber-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
          </svg>
        </div>

        {file ? (
          <p className="text-sm font-medium text-slate-700">{file.name} <span className="text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span></p>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-700">Drop your electricity bill here</p>
            <p className="text-xs text-slate-400 mt-1">PDF, JPG, PNG or photo — any utility provider</p>
          </>
        )}
      </div>

      {extractError && <p className="mt-3 text-xs text-rose-600 font-medium">{extractError}</p>}
      
      {extracting && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm text-slate-600 font-medium animate-pulse">
          <svg className="animate-spin h-5 w-5 text-amber-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {loadingText}
        </div>
      )}

      {file && !extracting && (
        <div className="mt-4 flex gap-2">
          <button className="btn-primary bg-amber-500 hover:bg-amber-600 focus:ring-amber-500" onClick={handleExtract}>
            🤖 Extract with AI
          </button>
          <button className="btn-secondary" onClick={() => setFile(null)}>Clear</button>
        </div>
      )}
    </div>
  )
}

function Field({ label, val, onChange, type = 'text' }) {
  const isMissing = val === ''
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
        value={val}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isMissing ? 'Not found — please enter manually' : ''}
      />
    </div>
  )
}
