export default function BulkActions({ selected, allIds, onSelectAll, onClearAll, onLock, loading }) {
  const count = selected.length
  const allSelected = count === allIds.length && allIds.length > 0

  if (count === 0) return null

  return (
    <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-2.5">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-emerald-800">{count} row{count !== 1 ? 's' : ''} selected</span>
        {!allSelected && (
          <button onClick={onSelectAll} className="text-xs text-emerald-600 hover:text-emerald-800 underline underline-offset-2">
            Select all {allIds.length}
          </button>
        )}
        <button onClick={onClearAll} className="text-xs text-slate-500 hover:text-slate-700 underline underline-offset-2">
          Clear selection
        </button>
      </div>
      <div className="flex items-center gap-2">
        <button
          className="btn-primary text-xs py-1.5"
          onClick={onLock}
          disabled={loading}
        >
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd"/>
          </svg>
          {loading ? 'Locking…' : `Lock ${count} for Audit`}
        </button>
      </div>
    </div>
  )
}
