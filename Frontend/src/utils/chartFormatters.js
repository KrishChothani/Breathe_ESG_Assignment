/**
 * src/utils/chartFormatters.js
 * Shared formatters for all chart components.
 */

/**
 * Format a CO₂e value in kg to a human-readable string.
 * < 1000 kg   → "850 kgCO₂e"
 * ≥ 1000 kg   → "1.2 tCO₂e"
 * ≥ 1,000,000 kg → "1.2 ktCO₂e"  (i.e. ≥ 1000 t)
 */
export function formatCO2e(kg) {
  if (kg === null || kg === undefined || isNaN(kg)) return '—'
  const n = Number(kg)
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} ktCO₂e`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)} tCO₂e`
  return `${Math.round(n)} kgCO₂e`
}

/**
 * formatTons — always render as tCO₂e (for chart axis ticks where kg is already /1000)
 */
export function formatTons(t) {
  if (t === null || t === undefined || isNaN(t)) return '—'
  const n = Number(t)
  if (n >= 1000) return `${(n / 1000).toFixed(0)}k`
  return `${n.toFixed(1)}`
}

/**
 * Convert ISO date string "2024-01-15" or "2024-01" → "Jan 24"
 */
export function formatMonth(isoDate) {
  if (!isoDate) return ''
  const parts = String(isoDate).split('-')
  const year  = parts[0]?.slice(2)
  const month = parseInt(parts[1], 10)
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${MONTHS[month - 1] ?? '?'} ${year}`
}

/**
 * Convert "2024-03-01" → "01 Mar 24"
 */
export function formatDate(isoDate) {
  if (!isoDate) return ''
  const [year, month, day] = String(isoDate).split('-')
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${day} ${MONTHS[parseInt(month, 10) - 1]} ${year?.slice(2)}`
}

/**
 * Source → chart colour
 */
export const SOURCE_COLORS = {
  SAP:              '#F59E0B',   // amber
  UTILITY:          '#14B8A6',   // teal
  TRAVEL:           '#8B5CF6',   // purple
  fuel:             '#F97316',   // orange
  electricity:      '#3B82F6',   // blue
  flights:          '#8B5CF6',   // purple
  hotels:           '#EC4899',   // pink
  ground_transport: '#14B8A6',   // teal
}

export function getSourceColor(source) {
  return SOURCE_COLORS[source] ?? '#94A3B8'
}

/** Scope → colour */
export const SCOPE_COLORS = {
  scope_1: '#F97316',   // orange — Scope 1 direct
  scope_2: '#3B82F6',   // blue   — Scope 2 electricity
  scope_3: '#22C55E',   // green  — Scope 3 travel
}
