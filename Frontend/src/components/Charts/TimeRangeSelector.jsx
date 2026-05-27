/**
 * src/components/Charts/TimeRangeSelector.jsx
 * Pill-button group for selecting the chart time window.
 */

const ALL_OPTIONS = ['7d', '30d', '90d', '6m', '1y', 'all']
const LABELS      = { '7d': '7D', '30d': '30D', '90d': '90D', '6m': '6M', '1y': '1Y', 'all': 'ALL' }

export default function TimeRangeSelector({ value, onChange, options = ALL_OPTIONS }) {
  return (
    <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`
            px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150
            ${value === opt
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200'
            }
          `}
        >
          {LABELS[opt]}
        </button>
      ))}
    </div>
  )
}
