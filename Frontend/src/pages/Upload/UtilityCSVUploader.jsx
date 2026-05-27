import { useState, useCallback } from 'react'
import { uploadUtilityCSV } from '../../api/ingestion'

export default function UtilityCSVUploader({ onSuccess }) {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]; if (f) setFile(f)
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading'); setProgress(0); setError('')
    try {
      await uploadUtilityCSV(file, setProgress)
      setStatus('done'); onSuccess?.()
    } catch (err) {
      setStatus('error'); setError(err.response?.data?.detail ?? 'Upload failed.')
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('util-file-input').click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? 'border-amber-400 bg-amber-50' : 'border-gray-300 hover:border-amber-400 hover:bg-slate-50'
        }`}
      >
        <input id="util-file-input" type="file" accept=".csv" className="hidden" onChange={(e) => setFile(e.target.files[0])} />
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-amber-50 flex items-center justify-center">
          <svg className="h-6 w-6 text-amber-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
        {file ? (
          <p className="text-sm font-medium text-slate-700">{file.name} <span className="text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span></p>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-700">Drop Utility Portal CSV here</p>
            <p className="text-xs text-slate-400 mt-1">Supports multi-meter, billing period crossing, kVAh rows</p>
          </>
        )}
      </div>
      {status === 'uploading' && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1"><span>Uploading…</span><span>{progress}%</span></div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-amber-400 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      {status === 'done' && <p className="mt-3 text-xs text-emerald-600 font-medium">✓ Upload successful — pro-rating queued.</p>}
      {status === 'error' && <p className="mt-3 text-xs text-rose-600">{error}</p>}
      {file && status !== 'done' && (
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={handleUpload} disabled={status === 'uploading'}>Upload File</button>
          <button className="btn-secondary" onClick={() => { setFile(null); setStatus('idle') }}>Clear</button>
        </div>
      )}
    </div>
  )
}
