export default function AnomalyAlert({ flags = [] }) {
  if (!flags.length) return null
  return (
    <div className="mt-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2">
      <div className="flex items-start gap-2">
        <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd"/>
        </svg>
        <div>
          <p className="text-xs font-semibold text-amber-800">Anomaly flags detected</p>
          <ul className="mt-1 space-y-0.5">
            {flags.map((f, i) => (
              <li key={i} className="text-xs text-amber-700">{f}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
