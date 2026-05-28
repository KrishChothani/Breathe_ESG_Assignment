/**
 * CO2ComparisonBadge.jsx
 * Shows document-claimed vs system-calculated CO2 comparison status.
 * MAJOR_VARIANCE adds a red border/glow to the parent row card.
 */
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'

const CONFIG = {
  MATCH: {
    icon:    CheckCircle2,
    label:   'CO₂ Verified',
    prefix:  '✓',
    classes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    ring:    '',
  },
  MINOR_VARIANCE: {
    icon:    AlertTriangle,
    label:   'Minor Variance',
    prefix:  '⚠',
    classes: 'bg-amber-50 text-amber-700 border-amber-200',
    ring:    '',
  },
  MAJOR_VARIANCE: {
    icon:    XCircle,
    label:   'CO₂ Mismatch',
    prefix:  '✗',
    classes: 'bg-rose-50 text-rose-700 border-rose-200',
    ring:    'ring-2 ring-rose-400',
  },
  NOT_APPLICABLE: null,
  MISSING_DOC_VALUE: null,
}

/**
 * @param {string}  status          - co2_comparison_status value from the row
 * @param {number}  variancePct     - co2_variance_pct from the row
 * @param {number}  documentClaimed - document_claimed_co2_kg
 * @param {number}  systemCalc      - system_calculated_co2_kg
 * @param {boolean} showDetails     - show the two values on hover
 */
export default function CO2ComparisonBadge({
  status,
  variancePct,
  documentClaimed,
  systemCalc,
  showDetails = true,
}) {
  const cfg = CONFIG[status]
  if (!cfg) return null

  const Icon = cfg.icon

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold
        ${cfg.classes} ${cfg.ring}
      `}
      title={showDetails && documentClaimed != null
        ? `Document: ${Number(documentClaimed).toFixed(2)} kg | System: ${Number(systemCalc).toFixed(2)} kg`
        : undefined}
    >
      <Icon size={12} />
      <span>{cfg.label}</span>
      {variancePct != null && (
        <span className="opacity-70">({Number(variancePct).toFixed(1)}%)</span>
      )}
    </div>
  )
}

/**
 * Returns Tailwind classes to apply a red border ring to a card when MAJOR_VARIANCE.
 */
export function getCardRingClass(status) {
  return status === 'MAJOR_VARIANCE' ? 'ring-2 ring-rose-400 ring-offset-1' : ''
}
