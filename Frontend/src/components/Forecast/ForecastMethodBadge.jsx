/**
 * src/components/Forecast/ForecastMethodBadge.jsx
 * Renders a labelled chip for the forecast method.
 */
const METHOD_META = {
  RUN_RATE:          { label: 'Run Rate',       cls: 'bg-orange-50 text-orange-700 border-orange-200' },
  ETS:               { label: 'ETS Model',      cls: 'bg-blue-50   text-blue-700   border-blue-200'   },
  ACTIVITY_DRIVEN:   { label: 'Activity-Driven',cls: 'bg-violet-50 text-violet-700 border-violet-200' },
  NOWCAST:           { label: 'Nowcast',         cls: 'bg-sky-50    text-sky-700    border-sky-200'    },
  RUN_RATE_FALLBACK: { label: 'Run Rate ↩',     cls: 'bg-slate-50  text-slate-500  border-slate-200'  },
  INSUFFICIENT:      { label: 'No Data',         cls: 'bg-rose-50   text-rose-500   border-rose-200'   },
}

export default function ForecastMethodBadge({ method }) {
  if (!method) return null
  const meta = METHOD_META[method] ?? { label: method, cls: 'bg-slate-50 text-slate-500 border-slate-200' }
  return (
    <span className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded border ${meta.cls}`}>
      {meta.label}
    </span>
  )
}
