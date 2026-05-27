import { useState, useRef } from 'react'
import { bulkImportCSV } from '../../api/plantLookup'

const TEMPLATE_HEADERS = [
  'werks_code', 'plant_name', 'city', 'state', 'country',
  'postal_code', 'region', 'plant_type', 'default_scope',
  'address_line', 'notes',
]

const COLUMN_DOCS = [
  { col: 'werks_code',    req: true,  example: 'IN_MUM',          notes: 'Max 10 chars, exact SAP code' },
  { col: 'plant_name',    req: true,  example: 'Mumbai Factory',   notes: '' },
  { col: 'city',          req: true,  example: 'Mumbai',           notes: '' },
  { col: 'country',       req: true,  example: 'IN',               notes: '2-letter ISO code' },
  { col: 'region',        req: true,  example: 'ASIA_PACIFIC',     notes: 'See allowed values below' },
  { col: 'plant_type',    req: false, example: 'MANUFACTURING',    notes: 'Default: MANUFACTURING' },
  { col: 'default_scope', req: false, example: 'SCOPE_1',          notes: 'Default: SCOPE_1' },
  { col: 'state',         req: false, example: 'Maharashtra',      notes: '' },
  { col: 'postal_code',   req: false, example: '400099',           notes: '' },
  { col: 'address_line',  req: false, example: 'MIDC Andheri',     notes: '' },
  { col: 'notes',         req: false, example: '(free text)',      notes: '' },
]

function downloadTemplate() {
  const csv = TEMPLATE_HEADERS.join(',') + '\n'
  const url = window.URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'plant_lookup_template.csv')
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export default function BulkImportPanel({ onImported }) {
  const fileRef = useRef(null)
  const [dragOver, setDragOver]   = useState(false)
  const [file, setFile]           = useState(null)
  const [overwrite, setOverwrite] = useState(false)
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState('')

  const handleFile = (f) => {
    if (f && f.name.endsWith('.csv')) {
      setFile(f)
      setResult(null)
      setError('')
    } else {
      setError('Only .csv files are accepted.')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const res = await bulkImportCSV(file, overwrite)
      setResult(res.data)
      if (res.data.created > 0 || res.data.updated > 0) onImported()
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Section 1 — Template */}
      <div className="card space-y-4">
        <div>
          <h3 className="font-semibold text-slate-800 text-sm">Step 1 — Download the CSV template</h3>
          <p className="text-xs text-slate-500 mt-1">
            Fill in your plant codes using this template. Do not rename or remove any column headers.
          </p>
        </div>

        <button onClick={downloadTemplate}
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download Template CSV
        </button>

        {/* Column reference table */}
        <div className="overflow-x-auto rounded-lg border border-slate-100">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="th text-left">Column</th>
                <th className="th text-left">Required</th>
                <th className="th text-left">Example</th>
                <th className="th text-left">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {COLUMN_DOCS.map((c) => (
                <tr key={c.col} className="hover:bg-slate-50/50">
                  <td className="td font-mono text-slate-700">{c.col}</td>
                  <td className="td">
                    {c.req
                      ? <span className="text-rose-600 font-semibold">Yes</span>
                      : <span className="text-slate-400">No</span>}
                  </td>
                  <td className="td font-mono text-slate-500">{c.example}</td>
                  <td className="td text-slate-400">{c.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Allowed values hint */}
        <div className="rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 text-xs text-slate-500 space-y-1">
          <p><strong>region</strong> allowed values: ASIA_PACIFIC | EUROPE | NORTH_AMERICA | MIDDLE_EAST | AFRICA | LATIN_AMERICA</p>
          <p><strong>plant_type</strong> allowed values: MANUFACTURING | WAREHOUSE | OFFICE | RETAIL | CONSTRUCTION | DATA_CENTRE | OTHER</p>
          <p><strong>default_scope</strong> allowed values: SCOPE_1 | SCOPE_2 | SCOPE_1_2</p>
        </div>
      </div>

      {/* Section 2 — Upload */}
      <div className="card space-y-4">
        <div>
          <h3 className="font-semibold text-slate-800 text-sm">Step 2 — Upload your filled CSV</h3>
          <p className="text-xs text-slate-500 mt-1">Drop your completed file below or click to browse.</p>
        </div>

        {/* Drop zone */}
        <div
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors min-h-[120px] ${
            dragOver ? 'border-emerald-400 bg-emerald-50' : file ? 'border-emerald-300 bg-emerald-50/50' : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
          }`}
        >
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => handleFile(e.target.files[0])} />
          {file ? (
            <>
              <svg className="w-8 h-8 text-emerald-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-emerald-700">{file.name}</p>
              <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB — click to replace</p>
            </>
          ) : (
            <>
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <p className="text-sm text-slate-500">Drop CSV here or <span className="text-emerald-600 font-medium">click to browse</span></p>
            </>
          )}
        </div>

        {error && <p className="text-xs text-rose-600">{error}</p>}

        {/* Overwrite toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <button
            type="button"
            onClick={() => setOverwrite((o) => !o)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${overwrite ? 'bg-emerald-500' : 'bg-slate-300'}`}
          >
            <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${overwrite ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </button>
          <span className="text-sm text-slate-600">Update existing codes if WERKS already exists</span>
        </label>

        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="btn-primary w-full justify-center py-2.5"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Importing…
            </>
          ) : 'Upload and Import'}
        </button>

        {/* Result card */}
        {result && (
          <div className="rounded-xl border border-slate-100 overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">
              <p className="text-sm font-semibold text-slate-700">Import Complete</p>
            </div>
            <div className="grid grid-cols-4 divide-x divide-slate-100">
              {[
                { label: 'Created',  value: result.created, icon: '✅', color: 'text-emerald-600' },
                { label: 'Updated',  value: result.updated, icon: '🔄', color: 'text-blue-600' },
                { label: 'Skipped',  value: result.skipped, icon: '⏭',  color: 'text-slate-500' },
                { label: 'Errors',   value: result.errors?.length ?? 0, icon: '❌', color: 'text-rose-600' },
              ].map((s) => (
                <div key={s.label} className="px-4 py-3 text-center">
                  <p className="text-lg">{s.icon}</p>
                  <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-slate-400">{s.label}</p>
                </div>
              ))}
            </div>
            {result.errors?.length > 0 && (
              <div className="border-t border-slate-100">
                <p className="px-4 py-2 text-xs font-semibold text-slate-500 bg-rose-50">Error details</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-rose-50/50 border-y border-rose-100">
                        <th className="th">Row</th>
                        <th className="th">WERKS Code</th>
                        <th className="th">Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {result.errors.map((e, i) => (
                        <tr key={i}>
                          <td className="td text-slate-400 font-mono">{e.row}</td>
                          <td className="td font-mono text-amber-700">{e.werks_code || '—'}</td>
                          <td className="td text-rose-600">{e.error}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
