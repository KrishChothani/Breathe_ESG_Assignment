import { useState } from 'react'
import UtilityCSVUploader from './UtilityCSVUploader'
import BulkBillScanner from './BulkBillScanner'

export default function UtilityUploader({ onSuccess }) {
  const [mode, setMode] = useState('CSV') // 'CSV' or 'OCR'

  return (
    <div>
      <div className="flex gap-2 mb-4 bg-slate-100 p-1 rounded-lg">
        <button
          className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all ${
            mode === 'CSV' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'
          }`}
          onClick={() => setMode('CSV')}
        >
          📄 Upload CSV
        </button>
        <button
          className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all ${
            mode === 'OCR' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'
          }`}
          onClick={() => setMode('OCR')}
        >
          🤖 Scan Bill with AI
        </button>
      </div>

      {mode === 'CSV' ? (
        <UtilityCSVUploader onSuccess={onSuccess} />
      ) : (
        <BulkBillScanner onSuccess={onSuccess} />
      )}
    </div>
  )
}
