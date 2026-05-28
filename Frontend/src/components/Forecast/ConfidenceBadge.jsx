/**
 * src/components/Forecast/ConfidenceBadge.jsx
 * Renders a colour-coded confidence % pill.
 *   ≥85% → emerald
 *   70–84% → amber
 *   <70%  → rose
 */
export default function ConfidenceBadge({ value }) {
  if (value == null) return null
  const pct = Math.round(Number(value))

  const cls =
    pct >= 85 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
    pct >= 70 ? 'bg-amber-50   text-amber-700   border-amber-200'   :
                'bg-rose-50    text-rose-700     border-rose-200'

  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded-full border ${cls}`}>
      {pct}%
    </span>
  )
}
