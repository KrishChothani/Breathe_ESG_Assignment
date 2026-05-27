import { useState, useCallback } from 'react'
import { uploadSAPFile } from '../../api/ingestion'

export default function SAPUploader({ onSuccess }) {
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('idle') // idle | uploading | done | error
  const [error, setError] = useState('')

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setProgress(0)
    setError('')
    try {
      await uploadSAPFile(file, setProgress)
      setStatus('done')
      onSuccess?.()
    } catch (err) {
      setStatus('error')
      setError(err.response?.data?.detail ?? 'Upload failed. Please try again.')
    }
  }

  return (
    <div>
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('sap-file-input').click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? 'border-emerald-500 bg-emerald-50' : 'border-gray-300 hover:border-emerald-400 hover:bg-slate-50'
        }`}
      >
        <input
          id="sap-file-input"
          type="file"
          accept=".csv,.txt"
          className="hidden"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center">
          <svg className="h-6 w-6 text-slate-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        {file ? (
          <p className="text-sm font-medium text-slate-700">{file.name} <span className="text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span></p>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-700">Drop SAP ME2M CSV here</p>
            <p className="text-xs text-slate-400 mt-1">or click to browse — .csv, .txt accepted</p>
          </>
        )}
      </div>

      {/* Progress */}
      {status === 'uploading' && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Uploading…</span><span>{progress}%</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      {status === 'done' && <p className="mt-3 text-xs text-emerald-600 font-medium">✓ Upload successful — parsing queued.</p>}
      {status === 'error' && <p className="mt-3 text-xs text-rose-600">{error}</p>}

      {file && status !== 'done' && (
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={handleUpload} disabled={status === 'uploading'}>
            {status === 'uploading' ? 'Uploading…' : 'Upload File'}
          </button>
          <button className="btn-secondary" onClick={() => { setFile(null); setStatus('idle') }}>Clear</button>
        </div>
      )}
    </div>
  )
}
