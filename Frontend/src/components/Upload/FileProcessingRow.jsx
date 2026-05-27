import { useEffect, useState } from 'react'

export default function FileProcessingRow({ fileItem, onRemove, onViewData, onReupload }) {
  const [thumbUrl, setThumbUrl] = useState(null)

  useEffect(() => {
    // Generate client-side thumbnail for images
    if (fileItem.file && fileItem.file.type.startsWith('image/')) {
      const url = URL.createObjectURL(fileItem.file)
      setThumbUrl(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [fileItem.file])

  const statusColors = {
    queued: 'bg-slate-100 text-slate-600 border-slate-200',
    processing: 'bg-blue-50 text-blue-600 border-blue-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    failed: 'bg-rose-50 text-rose-700 border-rose-200',
    saved: 'bg-emerald-100 text-emerald-800 border-emerald-300', // Added saved state
  }

  const isImage = fileItem.file.type.startsWith('image/')
  const sizeKB = (fileItem.file.size / 1024).toFixed(1)

  return (
    <div className={`flex items-center gap-4 p-3 rounded-lg border transition-colors ${fileItem.status === 'success' || fileItem.status === 'saved' ? 'bg-white shadow-sm hover:border-slate-300' : 'bg-slate-50'}`}>
      {/* Thumbnail */}
      <div className="h-12 w-12 shrink-0 rounded bg-slate-200 overflow-hidden flex items-center justify-center border border-slate-200">
        {thumbUrl ? (
          <img src={thumbUrl} alt="thumb" className="w-full h-full object-cover" />
        ) : isImage ? (
          <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
        ) : (
          <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
        )}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate" title={fileItem.file.name}>{fileItem.file.name}</p>
        <p className="text-xs text-slate-500">{sizeKB} KB</p>
      </div>

      {/* Status Badge */}
      <div className={`shrink-0 px-2.5 py-1 text-xs font-semibold rounded border flex items-center gap-1.5 ${statusColors[fileItem.status] || statusColors.queued}`}>
        {fileItem.status === 'processing' && (
          <svg className="animate-spin h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        )}
        {fileItem.status === 'queued' && "Waiting..."}
        {fileItem.status === 'processing' && "Extracting..."}
        {fileItem.status === 'success' && "Extracted"}
        {fileItem.status === 'saved' && "Saved to DB"}
        {fileItem.status === 'failed' && "Failed"}
      </div>

      {/* Error Reason */}
      {fileItem.status === 'failed' && fileItem.error && (
        <div className="shrink-0 max-w-[150px] truncate text-xs text-rose-600 bg-rose-100/50 px-2 py-1 rounded" title={fileItem.error}>
          {fileItem.error}
        </div>
      )}

      {/* Actions */}
      <div className="shrink-0 flex items-center gap-2">
        {(fileItem.status === 'success' || fileItem.status === 'saved') && (
          <button 
            className="text-xs font-medium px-3 py-1.5 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition-colors"
            onClick={() => onViewData(fileItem)}
          >
            {fileItem.status === 'saved' ? 'View/Edit Data' : 'Review & Save'}
          </button>
        )}
        
        {fileItem.status === 'failed' && (
          <div className="relative group">
            <input 
              type="file" 
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  onReupload(fileItem.id, e.target.files[0])
                }
              }}
              title="Upload replacement file"
            />
            <button className="text-xs font-medium px-3 py-1.5 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition-colors pointer-events-none">
              Re-upload
            </button>
          </div>
        )}

        {/* Remove Button (disabled during processing to prevent race conditions, or we can just cancel) */}
        {fileItem.status !== 'processing' && (
          <button 
            className="p-1.5 text-slate-400 hover:text-rose-500 rounded hover:bg-rose-50 transition-colors"
            onClick={() => onRemove(fileItem.id)}
            title="Remove from batch"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
          </button>
        )}
      </div>
    </div>
  )
}
