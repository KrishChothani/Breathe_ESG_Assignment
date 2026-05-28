/**
 * CO2Breakdown.jsx
 * Collapsible card showing how the system calculated CO2e for a row.
 * Shows formula, emission factor source, FY used, and GHG scope.
 */
import { useState } from 'react'
import { ChevronDown, ChevronUp, Calculator, Leaf } from 'lucide-react'

const SCOPE_COLORS = {
  SCOPE_1: { bg: 'bg-orange-50', border: 'border-orange-200', badge: 'bg-orange-100 text-orange-700', label: 'Scope 1 — Direct' },
  SCOPE_2: { bg: 'bg-blue-50',   border: 'border-blue-200',   badge: 'bg-blue-100 text-blue-700',     label: 'Scope 2 — Electricity' },
  SCOPE_3: { bg: 'bg-purple-50', border: 'border-purple-200', badge: 'bg-purple-100 text-purple-700', label: 'Scope 3 — Travel' },
}

const SOURCE_LABELS = {
  CEA_V20:      'CEA CO₂ Baseline V20.0',
  IPCC_2006:    'IPCC 2006 Guidelines',
  IPCC_AR6:     'IPCC AR6 (2021)',
  DEFRA_2024:   'DEFRA / DESNZ 2024',
  ICAO_2023:    'ICAO 2023',
  INDIA_GHG:    'India GHG Program',
  GHG_PROTOCOL: 'GHG Protocol',
}

export default function CO2Breakdown({ row, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)

  const {
    co2e_kg,
    formula,
    ghg_scope,
    ghg_category,
    emission_factor_value,
    emission_factor_unit,
    emission_factor_source,
    emission_factor_year,
  } = row

  if (!co2e_kg && !formula) return null

  const scopeStyle = SCOPE_COLORS[ghg_scope] || SCOPE_COLORS.SCOPE_1
  const sourceLabel = SOURCE_LABELS[emission_factor_source] || emission_factor_source || 'Unknown'

  return (
    <div className={`rounded-lg border ${scopeStyle.border} ${scopeStyle.bg} overflow-hidden`}>
      {/* Toggle header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:brightness-95 transition-all"
      >
        <div className="flex items-center gap-2">
          <Calculator size={15} className="text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">CO₂ Calculation</span>
          {co2e_kg != null && (
            <span className="text-xs font-bold text-slate-900 ml-1">
              {Number(co2e_kg).toLocaleString('en-IN', { maximumFractionDigits: 2 })} kg CO₂e
            </span>
          )}
        </div>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div className="px-4 pb-3 pt-1 space-y-2 border-t border-slate-200">
          {/* Formula */}
          {formula && (
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-0.5">Formula</p>
              <code className="text-xs font-mono text-slate-800 bg-white/70 rounded px-2 py-1 block">
                {formula}
              </code>
            </div>
          )}

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-1">
            {/* Factor */}
            {emission_factor_value && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Factor</p>
                <p className="text-xs font-medium text-slate-700">
                  {emission_factor_value} {emission_factor_unit}
                </p>
              </div>
            )}
            {/* Source */}
            {emission_factor_source && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Source</p>
                <p className="text-xs font-medium text-slate-700">
                  {sourceLabel}
                  {emission_factor_year ? ` · FY ${emission_factor_year}-${String(emission_factor_year + 1).slice(2)}` : ''}
                </p>
              </div>
            )}
            {/* Scope */}
            {ghg_scope && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">GHG Scope</p>
                <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${scopeStyle.badge}`}>
                  {scopeStyle.label}
                </span>
              </div>
            )}
            {/* Category */}
            {ghg_category && (
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide">Category</p>
                <p className="text-xs text-slate-600">{ghg_category}</p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1 pt-1">
            <Leaf size={11} className="text-emerald-500" />
            <span className="text-[10px] text-slate-400">
              GHG Protocol Corporate Standard · SEBI BRSR Core compliant
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
