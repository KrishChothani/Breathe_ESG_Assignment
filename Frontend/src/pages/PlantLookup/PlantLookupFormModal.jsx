import { useState, useEffect } from 'react'
import { createPlantLookup, updatePlantLookup } from '../../api/plantLookup'

const REGIONS = [
  { value: 'ASIA_PACIFIC',  label: 'Asia Pacific' },
  { value: 'EUROPE',        label: 'Europe' },
  { value: 'NORTH_AMERICA', label: 'North America' },
  { value: 'MIDDLE_EAST',   label: 'Middle East' },
  { value: 'AFRICA',        label: 'Africa' },
  { value: 'LATIN_AMERICA', label: 'Latin America' },
]

const PLANT_TYPES = [
  { value: 'MANUFACTURING', label: 'Manufacturing Factory' },
  { value: 'WAREHOUSE',     label: 'Warehouse / Distribution Centre' },
  { value: 'OFFICE',        label: 'Office / HQ' },
  { value: 'RETAIL',        label: 'Retail Outlet' },
  { value: 'CONSTRUCTION',  label: 'Construction Site' },
  { value: 'DATA_CENTRE',   label: 'Data Centre' },
  { value: 'OTHER',         label: 'Other' },
]

const SCOPES = [
  { value: 'SCOPE_1',   label: 'Scope 1', hint: 'Direct emissions (fuel burned on site)' },
  { value: 'SCOPE_2',   label: 'Scope 2', hint: 'Indirect from purchased electricity' },
  { value: 'SCOPE_1_2', label: 'Both Scope 1 & 2', hint: 'Site has both direct and grid consumption' },
]

const EMPTY = {
  werks_code: '', plant_name: '', plant_type: 'MANUFACTURING',
  city: '', state: '', country: '', postal_code: '',
  region: 'ASIA_PACIFIC', default_scope: 'SCOPE_1',
  address_line: '', notes: '', is_active: true,
}

function FieldError({ msg }) {
  if (!msg) return null
  return <p className="mt-1 text-xs text-rose-600">{msg}</p>
}

function Field({ label, required, hint, children, error }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1">
        {label}{required && <span className="text-rose-500 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
      <FieldError msg={error} />
    </div>
  )
}

export default function PlantLookupFormModal({ plant, prefillWerksCode, onClose, onSaved }) {
  const isEdit = !!plant
  const [form, setForm] = useState(() =>
    plant ? { ...EMPTY, ...plant } : { ...EMPTY, werks_code: prefillWerksCode || '' }
  )
  const [errors, setErrors] = useState({})
  const [apiError, setApiError] = useState('')
  const [saving, setSaving]     = useState(false)

  const set = (field, val) => {
    setForm((f) => ({ ...f, [field]: val }))
    setErrors((e) => ({ ...e, [field]: '' }))
  }

  const validate = () => {
    const e = {}
    if (!form.werks_code.trim()) e.werks_code = 'WERKS code is required.'
    if (form.werks_code.trim().length > 10) e.werks_code = 'Maximum 10 characters.'
    if (!form.plant_name.trim()) e.plant_name = 'Plant name is required.'
    if (!form.city.trim()) e.city = 'City is required.'
    if (!form.country.trim()) e.country = 'Country code is required.'
    else if (form.country.trim().length !== 2) e.country = 'Must be a 2-letter ISO code e.g. IN, DE, GB.'
    if (!form.region) e.region = 'Region is required.'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const valErrors = validate()
    if (Object.keys(valErrors).length) { setErrors(valErrors); return }

    setSaving(true)
    setApiError('')
    const payload = {
      ...form,
      werks_code: form.werks_code.trim().toUpperCase(),
      country:    form.country.trim().toUpperCase(),
    }

    try {
      if (isEdit) {
        await updatePlantLookup(plant.id, payload)
      } else {
        await createPlantLookup(payload)
      }
      onSaved()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        // Field-level errors from DRF
        const fieldErrs = {}
        Object.entries(data).forEach(([k, v]) => {
          fieldErrs[k] = Array.isArray(v) ? v.join(' ') : String(v)
        })
        if (Object.keys(fieldErrs).length) {
          setErrors(fieldErrs)
          setApiError('Please fix the errors below.')
        } else {
          setApiError(data.detail || 'Failed to save. Please try again.')
        }
      } else {
        setApiError('Failed to save. Please try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-slate-800">
            {isEdit ? `Edit Plant — ${plant.werks_code}` : 'Add New Plant Code'}
          </h2>
          <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-slate-100 text-slate-500 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
          {apiError && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 px-4 py-2 text-sm text-rose-700">
              {apiError}
            </div>
          )}

          {/* Row 1 — WERKS code + Plant Name */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="WERKS Code" required hint="Exact code from SAP e.g. 1000, IN_MUM, DE01" error={errors.werks_code}>
              <input
                type="text"
                value={form.werks_code}
                onChange={(e) => set('werks_code', e.target.value.toUpperCase().slice(0, 10))}
                disabled={isEdit}
                maxLength={10}
                className={`input-field font-mono uppercase ${isEdit ? 'bg-slate-50 text-slate-500 cursor-not-allowed' : ''} ${errors.werks_code ? 'border-rose-400' : ''}`}
                placeholder="e.g. IN_MUM"
              />
            </Field>
            <Field label="Plant Name" required error={errors.plant_name}>
              <input type="text" value={form.plant_name} onChange={(e) => set('plant_name', e.target.value)}
                className={`input-field ${errors.plant_name ? 'border-rose-400' : ''}`}
                placeholder="Mumbai Main Manufacturing Plant" maxLength={255} />
            </Field>
          </div>

          {/* Row 2 — Plant Type */}
          <Field label="Plant Type" required error={errors.plant_type}>
            <select value={form.plant_type} onChange={(e) => set('plant_type', e.target.value)} className="input-field">
              {PLANT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>

          {/* Row 3 — Location */}
          <div className="grid grid-cols-2 gap-4">
            <Field label="City" required error={errors.city}>
              <input type="text" value={form.city} onChange={(e) => set('city', e.target.value)}
                className={`input-field ${errors.city ? 'border-rose-400' : ''}`} placeholder="Mumbai" />
            </Field>
            <Field label="State / Province" error={errors.state}>
              <input type="text" value={form.state} onChange={(e) => set('state', e.target.value)}
                className="input-field" placeholder="Maharashtra" />
            </Field>
            <Field label="Country Code" required hint="2-letter ISO e.g. IN, DE, GB, US" error={errors.country}>
              <input type="text" value={form.country}
                onChange={(e) => set('country', e.target.value.toUpperCase().slice(0, 2))}
                className={`input-field font-mono uppercase ${errors.country ? 'border-rose-400' : ''}`}
                placeholder="IN" maxLength={2} />
            </Field>
            <Field label="Postal Code" error={errors.postal_code}>
              <input type="text" value={form.postal_code} onChange={(e) => set('postal_code', e.target.value)}
                className="input-field" placeholder="400093" />
            </Field>
          </div>

          {/* Row 4 — Region */}
          <Field label="Region" required error={errors.region}>
            <select value={form.region} onChange={(e) => set('region', e.target.value)} className="input-field">
              {REGIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </Field>

          {/* Row 5 — Scope (radio) */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-2">
              Default Emission Scope <span className="text-rose-500">*</span>
            </label>
            <div className="space-y-2">
              {SCOPES.map((s) => (
                <label key={s.value} className={`flex items-start gap-3 rounded-lg px-3 py-2.5 cursor-pointer border transition-colors ${
                  form.default_scope === s.value ? 'border-emerald-400 bg-emerald-50' : 'border-gray-200 hover:border-slate-300'
                }`}>
                  <input type="radio" name="scope" value={s.value}
                    checked={form.default_scope === s.value}
                    onChange={() => set('default_scope', s.value)}
                    className="mt-0.5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-medium text-slate-700">{s.label}</p>
                    <p className="text-xs text-slate-500">{s.hint}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Row 6 — Address */}
          <Field label="Address Line" error={errors.address_line}>
            <input type="text" value={form.address_line} onChange={(e) => set('address_line', e.target.value)}
              className="input-field" placeholder="MIDC Andheri Industrial Area" />
          </Field>

          {/* Row 7 — Notes */}
          <Field label="Notes" error={errors.notes}>
            <textarea rows={3} value={form.notes} onChange={(e) => set('notes', e.target.value)}
              className="input-field resize-none"
              placeholder="e.g. Plant decommissioned Dec 2023. Merged with IN_MUM." />
          </Field>

          {/* Row 8 — Active toggle */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => set('is_active', !form.is_active)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.is_active ? 'bg-emerald-500' : 'bg-slate-300'}`}
            >
              <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${form.is_active ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
            <span className="text-sm text-slate-600">
              {form.is_active ? 'Active — included in calculations' : 'Inactive — excluded from calculations'}
            </span>
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-2 bg-slate-50 rounded-b-2xl">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors">
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={saving}
            className="btn-primary"
          >
            {saving ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Saving…
              </>
            ) : isEdit ? 'Update Plant Code' : 'Save Plant Code'}
          </button>
        </div>
      </div>
    </div>
  )
}
