/**
 * src/components/Charts/ChartSkeleton.jsx
 * Animated loading skeleton for chart cards.
 */

export function ChartSkeleton({ height = 240 }) {
  return (
    <div className="animate-pulse space-y-3" style={{ height }}>
      {/* Fake bars */}
      <div className="flex items-end gap-2 h-full px-2 pb-2">
        {[0.4, 0.7, 0.55, 0.9, 0.65, 0.8, 0.5, 0.75, 0.6, 0.85, 0.45, 0.7].map((h, i) => (
          <div
            key={i}
            className="flex-1 bg-slate-200 rounded-t"
            style={{ height: `${h * 100}%` }}
          />
        ))}
      </div>
    </div>
  )
}

export function ChartEmpty({ message = 'No data for this period.' }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-center">
      <div className="text-4xl">📊</div>
      <p className="text-sm text-slate-400 max-w-xs">{message}</p>
      <a
        href="/upload"
        className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 underline underline-offset-2"
      >
        Upload data to see insights →
      </a>
    </div>
  )
}

export function ChartCard({ title, controls, children, className = '' }) {
  return (
    <div className={`bg-white border border-gray-200 rounded-xl p-6 shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        {controls && <div>{controls}</div>}
      </div>
      {children}
    </div>
  )
}
