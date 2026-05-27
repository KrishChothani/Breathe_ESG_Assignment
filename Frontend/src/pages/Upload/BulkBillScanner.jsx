import { useState, useCallback, useEffect } from 'react'
import { extractBill, confirmBill } from '../../api/ingestion'
import FileProcessingRow from '../../components/Upload/FileProcessingRow'
import ExtractedDataModal from '../../components/Upload/ExtractedDataModal'

const MAX_CONCURRENT = 3

export default function BulkBillScanner({ onSuccess }) {
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [selectedFileItem, setSelectedFileItem] = useState(null)
  const [activeTab, setActiveTab] = useState('queue') // 'queue' or 'table'
  const [savingAll, setSavingAll] = useState(false)

  // -- QUEUE MANAGER --
  useEffect(() => {
    const processing = files.filter(f => f.status === 'processing').length
    if (processing >= MAX_CONCURRENT) return

    const queued = files.filter(f => f.status === 'queued')
    if (queued.length === 0) return

    // Pick as many as we can to reach MAX_CONCURRENT
    const toProcess = queued.slice(0, MAX_CONCURRENT - processing)
    if (toProcess.length === 0) return

    // Mark them as processing in state immediately
    const toProcessIds = toProcess.map(f => f.id)
    setFiles(prev => prev.map(f => 
      toProcessIds.includes(f.id) ? { ...f, status: 'processing', error: null } : f
    ))

    // Start API calls
    toProcess.forEach(async (fItem) => {
      try {
        const res = await extractBill(fItem.file)
        const raw = res.data.extracted || {}
        
        // Ensure nulls are strings for the form
        const initForm = {}
        for (const [k, v] of Object.entries(raw)) {
          initForm[k] = v === null ? '' : v
        }
        initForm.confidence = raw.confidence

        setFiles(prev => prev.map(f => 
          f.id === fItem.id ? { 
            ...f, 
            status: 'success', 
            uploadId: res.data.upload_id, 
            extractedData: initForm 
          } : f
        ))
      } catch (err) {
        setFiles(prev => prev.map(f => 
          f.id === fItem.id ? { 
            ...f, 
            status: 'failed', 
            error: err.response?.data?.error || err.message || 'Extraction failed'
          } : f
        ))
      }
    })
  }, [files])

  // -- FILE SELECTION --
  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [])

  const handleFileInput = (e) => {
    addFiles(e.target.files)
    // Reset input so the same file can be selected again if needed
    e.target.value = null
  }

  const addFiles = (fileList) => {
    if (!fileList || fileList.length === 0) return
    const newItems = Array.from(fileList).map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'queued', // queued | processing | success | saved | failed
      error: null,
      extractedData: null,
      uploadId: null
    }))
    setFiles(prev => [...prev, ...newItems])
  }

  // -- ACTIONS --
  const handleRemove = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const handleReupload = (id, newFile) => {
    setFiles(prev => prev.map(f => 
      f.id === id ? { 
        ...f, 
        file: newFile, 
        status: 'queued', 
        error: null,
        extractedData: null,
        uploadId: null
      } : f
    ))
  }

  const handleCancelAll = () => {
    setFiles(prev => prev.filter(f => f.status !== 'queued'))
  }

  const handleRetryFailed = () => {
    setFiles(prev => prev.map(f => 
      f.status === 'failed' ? { ...f, status: 'queued', error: null } : f
    ))
  }

  const handleSaveData = async (id, updatedData, uploadId) => {
    // Actually call confirm API
    await confirmBill(uploadId, updatedData)
    // On success, mark as saved in the list
    setFiles(prev => prev.map(f => 
      f.id === id ? { 
        ...f, 
        status: 'saved', 
        extractedData: updatedData 
      } : f
    ))
    setSelectedFileItem(null)
    onSuccess?.()
  }

  const handleSaveAll = async () => {
    const successFiles = files.filter(f => f.status === 'success')
    if (successFiles.length === 0) return

    setSavingAll(true)
    let anySaved = false

    // Save sequentially to not overload the DB/API
    for (const f of successFiles) {
      try {
        await confirmBill(f.uploadId, f.extractedData)
        setFiles(prev => prev.map(item => 
          item.id === f.id ? { ...item, status: 'saved' } : item
        ))
        anySaved = true
      } catch (err) {
        console.error("Failed to save bill", f.file.name, err)
        // Keep status as 'success' so user can try manually
      }
    }

    setSavingAll(false)
    if (anySaved) onSuccess?.()
  }

  const handleExportCSV = () => {
    const successFiles = files.filter(f => f.status === 'success' || f.status === 'saved')
    if (successFiles.length === 0) return

    // Collect headers from the first item
    const headers = Object.keys(successFiles[0].extractedData).filter(k => k !== 'confidence')
    
    // Create CSV rows
    const rows = successFiles.map(f => {
      const row = headers.map(h => {
        const val = f.extractedData[h]
        // Escape quotes and wrap in quotes if contains comma
        if (val === null || val === undefined) return '""'
        const str = String(val).replace(/"/g, '""')
        return `"${str}"`
      })
      // Prepend original filename
      return `"${f.file.name.replace(/"/g, '""')}",` + row.join(',')
    })

    const csvContent = "Filename," + headers.join(',') + "\n" + rows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'extracted_bills.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // -- SUMMARY STATS --
  const total = files.length
  const queued = files.filter(f => f.status === 'queued').length
  const processing = files.filter(f => f.status === 'processing').length
  const success = files.filter(f => f.status === 'success' || f.status === 'saved').length
  const failed = files.filter(f => f.status === 'failed').length

  return (
    <div className="space-y-6">
      {/* DRAG AND DROP ZONE */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('bulk-ocr-file-input').click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? 'border-amber-400 bg-amber-50' : 'border-gray-300 hover:border-amber-400 hover:bg-slate-50'
        }`}
      >
        <input id="bulk-ocr-file-input" type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp" className="hidden" onChange={handleFileInput} />
        <div className="mx-auto mb-3 h-12 w-12 rounded-full bg-amber-50 flex items-center justify-center">
          <svg className="h-6 w-6 text-amber-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-slate-700">Click or drag multiple bills here</p>
        <p className="text-xs text-slate-400 mt-1">PDF, JPG, PNG or WEBP</p>
      </div>

      {files.length > 0 && (
        <div className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden">
            
            {/* MODAL HEADER WITH TABS */}
            <div className="px-6 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
              <div className="flex items-center gap-6">
                <h2 className="text-xl font-bold text-slate-800 py-4">Bulk Bill Processing</h2>
                <div className="flex gap-4 pt-1">
                  <button 
                    className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'queue' ? 'border-amber-500 text-amber-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    onClick={() => setActiveTab('queue')}
                  >
                    Processing Queue
                  </button>
                  <button 
                    className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'table' ? 'border-amber-500 text-amber-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    onClick={() => setActiveTab('table')}
                  >
                    Extracted Data ({success})
                  </button>
                </div>
              </div>
              <button 
                onClick={() => {
                  if (processing > 0) {
                    if (window.confirm("You have bills currently extracting. Are you sure you want to close? This will stop pending extractions.")) {
                      handleCancelAll();
                      setFiles([]);
                    }
                  } else {
                    setFiles([]);
                  }
                }} 
                className="text-slate-400 hover:text-slate-600 p-2 rounded-full hover:bg-slate-100 transition-colors"
                title="Close Dashboard"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            {/* SUMMARY BAR */}
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
              <div className="flex gap-4 text-sm font-medium">
                <span className="text-slate-800">Total: {total}</span>
                {queued > 0 && <span className="text-slate-500">Queued: {queued}</span>}
                {processing > 0 && <span className="text-blue-600 animate-pulse">Extracting: {processing}</span>}
                {success > 0 && <span className="text-emerald-600">Extracted: {success}</span>}
                {failed > 0 && <span className="text-rose-600">Failed: {failed}</span>}
              </div>
              <div className="flex items-center gap-3">
                <button 
                  className="text-xs font-medium px-4 py-2 rounded border border-slate-300 hover:bg-white text-slate-700 transition-colors bg-slate-100 flex items-center gap-2" 
                  onClick={() => document.getElementById('bulk-ocr-file-input').click()}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
                  Add More Bills
                </button>
                {queued > 0 && (
                  <button className="text-xs font-medium px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 transition-colors" onClick={handleCancelAll}>
                    Cancel Queued
                  </button>
                )}
                {failed > 0 && (
                  <button className="text-xs font-medium px-4 py-2 rounded bg-slate-800 hover:bg-slate-900 text-white transition-colors" onClick={handleRetryFailed}>
                    Retry Failed
                  </button>
                )}
                {files.filter(f => f.status === 'success').length > 0 && (
                  <button 
                    className="text-xs font-medium px-4 py-2 rounded bg-emerald-500 hover:bg-emerald-600 text-white transition-colors flex items-center gap-1 shadow-sm disabled:opacity-50" 
                    onClick={handleSaveAll}
                    disabled={savingAll}
                  >
                    {savingAll ? (
                      <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    )}
                    {savingAll ? 'Saving...' : 'Save All to DB'}
                  </button>
                )}
                {success > 0 && (
                  <button className="text-xs font-medium px-4 py-2 rounded bg-amber-500 hover:bg-amber-600 text-white transition-colors flex items-center gap-1 shadow-sm" onClick={handleExportCSV}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                    Export Data
                  </button>
                )}
              </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <div className="flex-1 overflow-hidden flex flex-col bg-slate-100/50 relative">
              {activeTab === 'queue' ? (
                <div className="p-6 flex flex-col gap-3 overflow-y-auto h-full">
                  {files.map(f => (
                    <FileProcessingRow 
                      key={f.id} 
                      fileItem={f} 
                      onRemove={handleRemove} 
                      onViewData={setSelectedFileItem}
                      onReupload={handleReupload}
                    />
                  ))}
                  <div className="h-4 shrink-0"></div>
                </div>
              ) : (
                <div className="p-6 overflow-y-auto h-full">
                  <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto shadow-sm">
                    <table className="min-w-full divide-y divide-slate-200">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">File</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Provider</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Site / Address</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Account</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Meter ID</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Period</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Bill Date</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Due Date</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Consumption</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Amount</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-slate-200">
                        {files.filter(f => f.status === 'success' || f.status === 'saved').length === 0 ? (
                          <tr>
                            <td colSpan="11" className="px-4 py-8 text-center text-sm text-slate-500 font-medium">No extracted data yet.</td>
                          </tr>
                        ) : (
                          files.filter(f => f.status === 'success' || f.status === 'saved').map(f => (
                            <tr key={f.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setSelectedFileItem(f)}>
                              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-800 max-w-[150px] truncate" title={f.file.name}>{f.file.name}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{f.extractedData?.provider_name || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600 max-w-[150px] truncate" title={f.extractedData?.site_name}>{f.extractedData?.site_name || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{f.extractedData?.account_number || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{f.extractedData?.meter_id || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                                {f.extractedData?.billing_period_start && f.extractedData?.billing_period_end 
                                  ? `${f.extractedData.billing_period_start} to ${f.extractedData.billing_period_end}`
                                  : '—'}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{f.extractedData?.bill_date || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">{f.extractedData?.due_date || '—'}</td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                                {f.extractedData?.consumption_kwh ? `${f.extractedData.consumption_kwh} ${f.extractedData.consumption_unit || 'kWh'}` : '—'}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                                {f.extractedData?.total_amount ? `${f.extractedData.total_amount} ${f.extractedData.currency || ''}` : '—'}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-right text-sm">
                                {f.status === 'saved' 
                                  ? <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-100 text-emerald-800">Saved</span>
                                  : <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">Pending</span>
                                }
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedFileItem && (
        <ExtractedDataModal 
          fileItem={selectedFileItem} 
          onClose={() => setSelectedFileItem(null)} 
          onSave={handleSaveData}
        />
      )}
    </div>
  )
}
