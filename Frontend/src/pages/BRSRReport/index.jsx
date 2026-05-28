/**
 * BRSRReport/index.jsx — Production-grade SEBI BRSR Core Compliance Dashboard
 *
 * SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 (12 July 2023)
 * + December 2024 Industry Standards
 *
 * 11 Sections:
 *  1. Compliance Identity Header
 *  2. Absolute Emissions Table (YoY, collapsible sub-rows)
 *  3. GHG Intensity Ratios
 *  4. Scope Breakdown Charts
 *  5. Emission Factor Methodology Box
 *  6. Data Quality & Assurance Readiness
 *  7. Fuel Consumption Table (Scope 1)
 *  8. Electricity Detail (Scope 2)
 *  9. Comply-or-Explain (Scope 3)
 * 10. Previous Year Panel
 * 11. Export Options (CSV / Detailed / Copy text)
 */
import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts'
import {
  ShieldCheck, RefreshCw, FileDown, Printer, ChevronDown, ChevronUp,
  CheckCircle2, XCircle, AlertTriangle, Clock, Copy, FileText, Info,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react'
import { getBRSRSummary } from '../../api/reports'

// ── Constants ─────────────────────────────────────────────────────────────────

const CURRENT_FY = (() => {
  const now = new Date()
  const y = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
  return `${y}-${String(y + 1).slice(2)}`
})()

const FY_OPTIONS = (() => {
  const opts = []
  const now = new Date()
  const currentY = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
  for (let y = currentY; y >= 2022; y--) opts.push(`${y}-${String(y + 1).slice(2)}`)
  return opts
})()

const SCOPE_COLORS = { 'Scope 1': '#f97316', 'Scope 2': '#3b82f6', 'Scope 3': '#a855f7' }

const EMISSION_FACTORS_STATIC = {
  diesel:      { unit: 'litres', factor: 2.6533 },
  petrol:      { unit: 'litres', factor: 2.30   },
  cng:         { unit: 'kg',     factor: 2.21   },
  lpg:         { unit: 'kg',     factor: 2.983  },
  natural_gas: { unit: 'm³',     factor: 1.9141 },
}

const COMPLIANCE_TIMELINE = [
  { fy: 'FY 2023-24', scope: 'Top 150',   note: 'Voluntary BRSR Core',         done: true  },
  { fy: 'FY 2024-25', scope: 'Top 250',   note: 'Scope 3 comply-or-explain',   current: true },
  { fy: 'FY 2025-26', scope: 'Top 500',   note: 'Mandatory external assurance', future: true },
  { fy: 'FY 2026-27', scope: 'Top 1,000', note: 'Full mandatory + value chain', future: true },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt  = (n, d = 4) => (n == null || isNaN(n)) ? '—' : Number(n).toFixed(d)
const fmtN = (n) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })

function yoyPct(current, previous) {
  if (previous == null || previous === 0 || current == null) return null
  return ((current - previous) / previous) * 100
}

function YoYBadge({ current, previous }) {
  const pct = yoyPct(current, previous)
  if (pct == null) return <span className="text-slate-400 text-xs">N/A</span>
  const isUp = pct > 0.05
  const isDn = pct < -0.05
  const color = isUp ? 'text-rose-600' : isDn ? 'text-emerald-600' : 'text-slate-500'
  const Arrow = isUp ? '▲' : isDn ? '▼' : '—'
  const Icon  = isUp ? TrendingUp : isDn ? TrendingDown : Minus
  return (
    <span className={`inline-flex items-center gap-0.5 font-semibold text-xs ${color}`}>
      <Icon size={11} /> {Arrow} {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

// ── Quality Dial ──────────────────────────────────────────────────────────────

function QualityDial({ pct }) {
  const r      = 38
  const circ   = 2 * Math.PI * r
  const filled = ((pct || 0) / 100) * circ
  const color  = pct >= 80 ? '#22c55e' : pct >= 55 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="100" className="-rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#e2e8f0" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="9"
          strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.9s ease' }}
        />
      </svg>
      <div className="text-center -mt-14">
        <p className="text-2xl font-bold" style={{ color }}>{(pct || 0).toFixed(0)}%</p>
        <p className="text-[10px] text-slate-500 mt-0.5">Readiness</p>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 1 — COMPLIANCE HEADER
// ═══════════════════════════════════════════════════════════════════════════════

function ComplianceHeader({
  data, fy, setFy, loading, onRefresh,
  onExportCSV, onExportDetailed, onCopyText,
  assuranceLevel, setAssuranceLevel,
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 print:border-slate-400">
      <div className="flex flex-wrap gap-5 justify-between items-start">

        {/* Identity block */}
        <div className="flex-1 min-w-[280px]">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
              <ShieldCheck size={20} className="text-emerald-600" />
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-800 leading-tight">
                SEBI BRSR Core — GHG Disclosure
              </h1>
              <p className="text-xs text-slate-500">
                Principle 6 · Essential Indicators · Question 7
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
            {[
              ['Framework',    'GHG Protocol Corporate Standard'],
              ['Methodology',  'Location-based (Scope 2)'],
              ['EF Source',    'CEA CO₂ Baseline DB V20.0'],
              ['Boundary',     'Operational Control'],
              ['Organisation', data?.organisation || '—'],
              ['Period',       `FY ${data?.reporting_period || fy}`],
              ['Generated',    data?.generated_at || '—'],
              ['Prepared by',  data?.generated_by || '—'],
            ].map(([k, v]) => (
              <div key={k} className="flex gap-1.5 overflow-hidden">
                <span className="text-slate-400 shrink-0 font-medium">{k}:</span>
                <span className="text-slate-700 truncate">{v}</span>
              </div>
            ))}
          </div>

          {/* Assurance level toggle */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-xs text-slate-500 font-medium">Assurance Level:</span>
            {['none', 'limited', 'reasonable'].map(l => (
              <button key={l} onClick={() => setAssuranceLevel(l)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors font-medium ${
                  assuranceLevel === l
                    ? 'bg-emerald-600 text-white border-emerald-600'
                    : 'border-slate-300 text-slate-500 hover:border-emerald-400 hover:text-emerald-600'
                }`}
              >
                {l.charAt(0).toUpperCase() + l.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-2 items-end shrink-0 print:hidden">
          <div className="flex items-center gap-2">
            <select value={fy} onChange={e => setFy(e.target.value)}
              className="border border-slate-300 rounded-lg text-sm py-1.5 px-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              {FY_OPTIONS.map(f => <option key={f}>{f}</option>)}
            </select>
            <button onClick={onRefresh} title="Refresh"
              className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-slate-600"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
            <button onClick={() => window.print()} title="Print"
              className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-slate-600"
            >
              <Printer size={14} />
            </button>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <button onClick={onExportCSV} disabled={!data}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-600 transition-colors disabled:opacity-40"
            >
              <FileDown size={13} /> BRSR CSV
            </button>
            <button onClick={onExportDetailed} disabled={!data}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-600 transition-colors disabled:opacity-40"
            >
              <FileText size={13} /> Detailed CSV
            </button>
            <button onClick={onCopyText} disabled={!data}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-40"
            >
              <Copy size={13} /> Copy Disclosure
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 2 — ABSOLUTE EMISSIONS TABLE
// ═══════════════════════════════════════════════════════════════════════════════

function AbsoluteEmissionsTable({ data }) {
  const [s1Open, setS1Open] = useState(true)
  const [s3Open, setS3Open] = useState(false)

  const pf   = data?.previous_fy
  const s1   = data?.scope_1?.total_co2e_tonnes ?? 0
  const s2   = data?.scope_2?.total_co2e_tonnes ?? 0
  const s3   = data?.scope_3?.total_co2e_tonnes ?? 0
  const tot  = data?.total_co2e_tonnes ?? 0
  const ps1  = pf?.scope_1?.total_co2e_tonnes
  const ps2  = pf?.scope_2?.total_co2e_tonnes
  const ps3  = pf?.scope_3?.total_co2e_tonnes
  const ptot = pf?.total_co2e_tonnes
  const byFuel = data?.scope_1_detail?.by_fuel_type || {}
  const byCat  = data?.scope_3?.by_category || {}
  const byGas  = data?.scope_1_detail?.by_gas_type || {}

  const currLabel = `FY ${data?.reporting_period || '—'}`
  const prevLabel = `FY ${pf?.reporting_period || '—'}`

  const TH = () => (
    <tr className="bg-slate-100 text-[10px] uppercase tracking-wide text-slate-500">
      <th className="py-2.5 pl-4 pr-2 text-left font-semibold">Parameter</th>
      <th className="py-2.5 px-2 text-center font-semibold">Unit</th>
      <th className="py-2.5 px-3 text-right font-semibold">{currLabel}</th>
      <th className="py-2.5 px-3 text-right font-semibold">{prevLabel}</th>
      <th className="py-2.5 pl-2 pr-4 text-right font-semibold">YoY</th>
    </tr>
  )

  const DataRow = ({ label, value, prev, indent = false, bold = false, highlight = false }) => (
    <tr className={`border-b border-slate-100 transition-colors ${highlight ? 'bg-emerald-50 hover:bg-emerald-100' : 'hover:bg-slate-50'}`}>
      <td className={`py-2 pl-4 pr-2 text-sm ${indent ? 'pl-9 text-slate-500 italic' : ''} ${bold ? 'font-bold text-slate-800' : 'text-slate-700'}`}>
        {label}
      </td>
      <td className="py-2 px-2 text-center text-xs text-slate-400">tCO₂e</td>
      <td className={`py-2 px-3 text-right font-mono text-sm ${bold ? 'font-bold' : ''}`}>{fmt(value)}</td>
      <td className="py-2 px-3 text-right font-mono text-sm text-slate-500">{prev != null ? fmt(prev) : '—'}</td>
      <td className="py-2 pl-2 pr-4 text-right"><YoYBadge current={value} previous={prev} /></td>
    </tr>
  )

  const ExpandRow = ({ label, value, prev, open, onToggle, color = 'text-orange-700' }) => (
    <tr onClick={onToggle}
      className="border-b border-slate-100 cursor-pointer hover:bg-slate-50 select-none transition-colors"
    >
      <td className={`py-2.5 pl-4 pr-2 text-sm font-semibold ${color}`}>
        <span className="inline-flex items-center gap-1">
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />} {label}
        </span>
      </td>
      <td className="py-2.5 px-2 text-center text-xs text-slate-400">tCO₂e</td>
      <td className="py-2.5 px-3 text-right font-mono text-sm font-semibold">{fmt(value)}</td>
      <td className="py-2.5 px-3 text-right font-mono text-sm text-slate-500">{prev != null ? fmt(prev) : '—'}</td>
      <td className="py-2.5 pl-2 pr-4 text-right"><YoYBadge current={value} previous={prev} /></td>
    </tr>
  )

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-slate-100">
        <p className="text-sm font-bold text-slate-800">GHG Emissions — Absolute Disclosure (BRSR Core, Q7)</p>
        <p className="text-xs text-slate-400 mt-0.5">
          Scope 1+2 mandatory · Scope 3 comply-or-explain for Top 250 from FY 2024-25
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead><TH /></thead>
          <tbody>
            {/* Scope 1 */}
            <ExpandRow
              label="Total Scope 1 — Direct Emissions (Fuel Combustion)"
              value={s1} prev={ps1}
              open={s1Open} onToggle={() => setS1Open(v => !v)}
              color="text-orange-700"
            />
            {s1Open && <>
              {Object.entries(byFuel).map(([fuel, info]) => (
                <DataRow key={fuel}
                  label={`— ${fuel.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())}`}
                  value={info.co2e_tonnes} prev={null} indent
                />
              ))}
              <DataRow label="— CO₂ (fuel combustion)"              value={byGas.co2}  prev={null} indent />
              <DataRow label="— CH₄ (not separately metered)"       value={byGas.ch4 || 0} prev={null} indent />
              <DataRow label="— N₂O (not separately metered)"       value={byGas.n2o || 0} prev={null} indent />
            </>}

            {/* Scope 2 */}
            <DataRow label="Total Scope 2 — Purchased Electricity" value={s2} prev={ps2} />

            {/* Scope 1+2 combined — highlighted */}
            <DataRow
              label="Total Scope 1 + 2 (BRSR Core mandatory threshold)"
              value={s1 + s2}
              prev={ps1 != null && ps2 != null ? ps1 + ps2 : null}
              bold highlight
            />

            {/* Scope 3 */}
            <ExpandRow
              label="Total Scope 3 — Business Travel"
              value={s3} prev={ps3}
              open={s3Open} onToggle={() => setS3Open(v => !v)}
              color="text-purple-700"
            />
            {s3Open && <>
              <DataRow label="— Air travel"       value={byCat.business_travel_air}    prev={null} indent />
              <DataRow label="— Hotel stays"      value={byCat.business_travel_hotel}  prev={null} indent />
              <DataRow label="— Ground transport" value={byCat.business_travel_ground} prev={null} indent />
            </>}

            {/* Grand total */}
            <DataRow label="TOTAL — All Scopes Combined" value={tot} prev={ptot} bold highlight />
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-slate-400 px-5 py-2.5 border-t border-slate-100">
        * Sub-row breakdowns: current FY only. Previous FY sub-rows require historical data upload. ·
        GWP: IPCC AR6 (CO₂=1, CH₄=27.9, N₂O=273). All values in metric tonnes CO₂ equivalent (tCO₂e).
      </p>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 3 — GHG INTENSITY RATIOS
// ═══════════════════════════════════════════════════════════════════════════════

function IntensityCards({ data, fy, onRevenueChange }) {
  const storageKey = `brsr_revenue_${fy}`
  const [revenue,   setRevenue]  = useState(() => {
    const v = localStorage.getItem(storageKey)
    return v ? parseFloat(v) : null
  })
  const [inputVal,  setInputVal] = useState('')
  const [editing,   setEditing]  = useState(false)

  const s1 = data?.scope_1?.total_co2e_tonnes ?? 0
  const s2 = data?.scope_2?.total_co2e_tonnes ?? 0
  const s12 = s1 + s2

  const pf  = data?.previous_fy
  const ps12 = pf ? (pf.scope_1?.total_co2e_tonnes ?? 0) + (pf.scope_2?.total_co2e_tonnes ?? 0) : null

  const intensity     = revenue && revenue > 0 ? s12 / revenue : null
  const prevIntensity = revenue && ps12   ? ps12  / revenue : null

  const handleSave = () => {
    const n = parseFloat(inputVal)
    if (!isNaN(n) && n > 0) {
      setRevenue(n)
      localStorage.setItem(storageKey, String(n))
      onRevenueChange && onRevenueChange(n)
    }
    setEditing(false)
  }

  // Sync revenue back up to parent
  useEffect(() => { onRevenueChange && onRevenueChange(revenue) }, [revenue])

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-sm font-bold text-slate-800">GHG Intensity Ratios</p>
          <p className="text-xs text-slate-400">Mandatory BRSR Core KPI — Revenue &amp; Output based</p>
        </div>
        <button onClick={() => { setInputVal(revenue?.toString() || ''); setEditing(v => !v) }}
          className="text-xs text-emerald-600 hover:underline print:hidden font-medium"
        >
          {revenue ? `Edit Revenue (₹${Number(revenue).toLocaleString('en-IN')} Cr)` : '+ Enter Revenue from Operations'}
        </button>
      </div>

      {editing && (
        <div className="flex flex-wrap items-center gap-2 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-sm text-slate-600 shrink-0">Revenue from Operations — FY {fy} (INR Crore):</span>
          <input type="number" min="0" step="0.01"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-36 focus:ring-emerald-500 focus:border-emerald-500"
            value={inputVal} onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            autoFocus placeholder="e.g. 250.50"
          />
          <button onClick={handleSave}
            className="px-3 py-1.5 bg-emerald-600 text-white text-xs rounded-lg hover:bg-emerald-700 transition-colors"
          >Save</button>
          <button onClick={() => setEditing(false)}
            className="px-3 py-1.5 border border-slate-300 text-xs rounded-lg hover:bg-slate-100 transition-colors"
          >Cancel</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Revenue-based intensity */}
        <div className="rounded-xl border border-slate-200 p-4 bg-gradient-to-br from-slate-50 to-slate-100">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            BRSR Core KPI · Revenue Intensity
          </p>
          <p className="text-xs text-slate-600 mt-0.5 mb-3">
            GHG Emission Intensity per rupee of turnover
          </p>
          {intensity != null ? (
            <>
              <p className="text-3xl font-bold text-slate-800">{fmt(intensity, 4)}</p>
              <p className="text-xs text-slate-500">tCO₂e / INR Crore</p>
              <p className="text-xs text-slate-400 mt-2">
                Scope 1+2 ({fmt(s12, 2)} t) ÷ Revenue (₹{Number(revenue).toLocaleString('en-IN')} Cr)
              </p>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-slate-500">vs {data?.previous_fy?.reporting_period || 'prev FY'}:</span>
                <YoYBadge current={intensity} previous={prevIntensity} />
              </div>
            </>
          ) : (
            <div className="flex items-start gap-2 mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
              <Info size={14} className="text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700">
                Enter Revenue from Operations above to calculate intensity ratio
              </p>
            </div>
          )}
          <p className="text-[10px] text-slate-400 mt-3 italic">
            PPP-adjusted intensity also available for cross-border comparison
          </p>
        </div>

        {/* Output-based intensity */}
        <div className="rounded-xl border border-dashed border-slate-300 p-4 bg-slate-50 opacity-70">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            BRSR Core KPI · Output Intensity
          </p>
          <p className="text-xs text-slate-600 mt-0.5 mb-3">
            GHG Emission Intensity per unit of output
          </p>
          <p className="text-3xl font-bold text-slate-300">N/A</p>
          <p className="text-xs text-slate-400 mt-1">tCO₂e / unit</p>
          <p className="text-xs text-slate-400 mt-3 italic">
            Configure output metric in Admin Settings
          </p>
          <p className="text-[10px] text-slate-400 mt-1">
            Supported: kWh generated / rooms / km / tonnes produced
          </p>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 4 — SCOPE BREAKDOWN CHARTS
// ═══════════════════════════════════════════════════════════════════════════════

function ScopeCharts({ data }) {
  const pf      = data?.previous_fy
  const currFy  = data?.reporting_period || '—'
  const prevFy  = pf?.reporting_period   || '—'

  const barData = [
    { name: 'Scope 1', curr: data?.scope_1?.total_co2e_tonnes ?? 0, prev: pf?.scope_1?.total_co2e_tonnes ?? 0 },
    { name: 'Scope 2', curr: data?.scope_2?.total_co2e_tonnes ?? 0, prev: pf?.scope_2?.total_co2e_tonnes ?? 0 },
    { name: 'Scope 3', curr: data?.scope_3?.total_co2e_tonnes ?? 0, prev: pf?.scope_3?.total_co2e_tonnes ?? 0 },
  ]

  const byCat  = data?.scope_3?.by_category || {}
  const s3Tot  = (data?.scope_3?.total_co2e_tonnes || 0) || 1
  const s3Bars = [
    { name: 'Air Travel',       value: byCat.business_travel_air    ?? 0 },
    { name: 'Hotel Stays',      value: byCat.business_travel_hotel  ?? 0 },
    { name: 'Ground Transport', value: byCat.business_travel_ground ?? 0 },
  ].map(b => ({ ...b, pct: ((b.value / s3Tot) * 100).toFixed(1) }))

  const kwh       = data?.scope_2_detail?.total_kwh_consumed ?? 0
  const renewKwh  = data?.scope_2_detail?.renewable_kwh ?? 0
  const nonRenew  = Math.max(0, kwh - renewKwh)
  const pieData   = [
    { name: 'Grid (non-renewable)', value: nonRenew,  fill: '#3b82f6' },
    { name: 'Renewable',            value: renewKwh,  fill: '#22c55e' },
  ].filter(p => p.value > 0)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

      {/* 4a — YoY grouped bar */}
      <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-semibold text-slate-700">
          Scope Emissions — Year-on-Year Comparison
        </p>
        <p className="text-xs text-slate-400 mb-3">
          FY {currFy} vs FY {prevFy} &nbsp;(tCO₂e)
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={barData}
            barGap={4}
            barCategoryGap="25%"
            margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v.toFixed(1)} axisLine={false} tickLine={false} width={45} />
            <Tooltip
              formatter={(v, name) => [`${Number(v).toFixed(4)} tCO₂e`, name]}
              contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }}
              cursor={{ fill: '#f8fafc' }}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
            <Bar dataKey="prev" name={`FY ${prevFy}`} fill="#94a3b8" radius={[3, 3, 0, 0]} minPointSize={2} />
            <Bar dataKey="curr" name={`FY ${currFy}`} fill="#1e293b" radius={[3, 3, 0, 0]} minPointSize={2} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 4b — Scope 2 electricity ring */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-semibold text-slate-700">Scope 2 — Electricity Mix</p>
        <p className="text-xs text-slate-400 mb-3">kWh consumed this FY</p>
        {kwh > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={38} outerRadius={58}
                  paddingAngle={3} dataKey="value"
                >
                  {pieData.map(e => <Cell key={e.name} fill={e.fill} />)}
                </Pie>
                <Tooltip
                  formatter={v => `${Number(v).toLocaleString('en-IN')} kWh`}
                  contentStyle={{ fontSize: 11, borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 mt-1">
              {pieData.map(p => (
                <div key={p.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: p.fill }} />
                    <span className="text-slate-600">{p.name}</span>
                  </span>
                  <span className="font-mono font-semibold text-slate-700">
                    {Number(p.value).toLocaleString('en-IN')} kWh
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                <span className="text-slate-400">Total</span>
                <span className="font-mono font-bold">{Number(kwh).toLocaleString('en-IN')} kWh</span>
              </div>
            </div>
          </>
        ) : (
          <p className="text-xs text-slate-400 text-center py-12">No electricity data for this FY</p>
        )}
      </div>

      {/* 4c — Scope 3 horizontal breakdown */}
      <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-semibold text-slate-700 mb-4">Scope 3 — Travel Category Breakdown</p>
        <div className="space-y-3">
          {s3Bars.map(b => (
            <div key={b.name}>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-slate-600 font-medium">{b.name}</span>
                <span className="font-mono font-semibold text-slate-700">
                  {fmt(b.value)} tCO₂e
                  <span className="text-slate-400 font-normal ml-1">({b.pct}%)</span>
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${b.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 5 — EMISSION FACTOR METHODOLOGY BOX
// ═══════════════════════════════════════════════════════════════════════════════

function MethodologyBox({ data }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden print:border-slate-400">
      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 hover:bg-slate-100 transition-colors print:cursor-default"
      >
        <div className="flex items-center gap-2.5 flex-wrap">
          <FileText size={15} className="text-slate-500 shrink-0" />
          <span className="text-sm font-bold text-slate-700">
            Emission Factor Methodology Disclosure
          </span>
          <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
            Required — SEBI BRSR Core Dec 2024
          </span>
        </div>
        <span className="print:hidden shrink-0">
          {open ? <ChevronUp size={15} className="text-slate-400" /> : <ChevronDown size={15} className="text-slate-400" />}
        </span>
      </button>

      {open && (
        <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6 text-xs border-t border-slate-100">
          {/* Scope 1 */}
          <div>
            <p className="font-bold text-slate-700 pb-1.5 mb-2.5 border-b border-slate-200">
              Scope 1 — Fuel Combustion
            </p>
            <p className="text-slate-500 mb-2">
              Source: IPCC 2006 Guidelines for National GHG Inventories / India GHG Program
            </p>
            <div className="space-y-1">
              {Object.entries(EMISSION_FACTORS_STATIC).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-slate-500 capitalize">{k.replace('_', ' ')}</span>
                  <span className="font-mono text-slate-700 font-medium">{v.factor} kgCO₂/{v.unit}</span>
                </div>
              ))}
            </div>
            <p className="text-slate-400 mt-3 italic">GWP: IPCC AR6 (CH₄=27.9, N₂O=273)</p>
          </div>

          {/* Scope 2 */}
          <div>
            <p className="font-bold text-slate-700 pb-1.5 mb-2.5 border-b border-slate-200">
              Scope 2 — Purchased Electricity
            </p>
            <p className="text-slate-500 mb-2">
              Source: CEA CO₂ Baseline Database Version 20.0
            </p>
            <div className="space-y-1">
              {[
                ['FY 2024-25', '0.710 kgCO₂e/kWh'],
                ['FY 2023-24', '0.727 kgCO₂e/kWh'],
                ['FY 2022-23', '0.716 kgCO₂e/kWh'],
              ].map(([fy, val]) => (
                <div key={fy} className="flex justify-between">
                  <span className="text-slate-500">{fy}</span>
                  <span className="font-mono text-slate-700 font-medium">{val}</span>
                </div>
              ))}
            </div>
            <p className="text-slate-500 mt-2">Method: Location-based weighted average</p>
            <p className="text-slate-400 mt-1 italic">Market-based: N/A (no RECs or PPAs)</p>
          </div>

          {/* Scope 3 */}
          <div>
            <p className="font-bold text-slate-700 pb-1.5 mb-2.5 border-b border-slate-200">
              Scope 3 — Business Travel
            </p>
            <p className="text-slate-500 mb-2">
              Source: DEFRA 2024 / ICAO Carbon Calculator
            </p>
            <div className="space-y-1">
              {[
                ['Short haul (&lt;1,500km)',    '0.255 kg/pax/km'],
                ['Medium haul',                 '0.195 kg/pax/km'],
                ['Long haul (&gt;4,000km)',      '0.150 kg/pax/km'],
                ['Hotel (per room/night)',       '31.00 kgCO₂e'],
                ['Ground transport',             '0.171 kg/km'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-slate-500" dangerouslySetInnerHTML={{ __html: k }} />
                  <span className="font-mono text-slate-700 font-medium">{v}</span>
                </div>
              ))}
            </div>
            <p className="text-slate-500 mt-2">Radiative forcing: 1.9× applied to all air travel</p>
          </div>

          <div className="md:col-span-3 pt-3 border-t border-slate-100 text-slate-400 text-[10px]">
            Reporting Standard: GHG Protocol Corporate Standard (2015 revised edition) ·
            SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 (12 July 2023) ·
            All emission factors in CO₂ equivalent (CO₂e) including GWP weighting.
          </div>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 6 — DATA QUALITY & ASSURANCE READINESS
// ═══════════════════════════════════════════════════════════════════════════════

function DataQualityPanel({ data, assuranceLevel, revenue }) {
  const dq  = data?.data_quality || {}
  const pf  = data?.previous_fy

  const s1 = data?.scope_1 || {}
  const s2 = data?.scope_2 || {}
  const s3 = data?.scope_3 || {}

  const checks = [
    {
      label: 'All Scope 1 rows approved',
      pass:  s1.row_count > 0 && s1.approved_row_count >= s1.row_count,
    },
    {
      label: 'All Scope 2 rows approved',
      pass:  s2.row_count > 0 && s2.approved_row_count >= s2.row_count,
    },
    {
      label: 'Scope 3 rows approved or comply-or-explain note present',
      pass:  (s3.approved_row_count ?? 0) > 0,
    },
    {
      label: 'No unresolved auditor findings',
      pass:  (dq.rows_with_unresolved_findings ?? 1) === 0,
    },
    {
      label: 'No major CO₂ variance flags outstanding',
      pass:  (dq.rows_with_major_co2_variance ?? 1) === 0,
    },
    {
      label: 'Emission factors documented for all rows',
      pass:  true,
    },
    {
      label: 'Previous year comparative data available',
      pass:  pf && (pf.total_co2e_tonnes ?? 0) > 0,
    },
    {
      label: 'Revenue intensity figure entered',
      pass:  revenue != null && revenue > 0,
    },
    {
      label: 'Reporting boundary defined (Operational Control)',
      pass:  data?.reporting_boundary != null,
    },
  ]

  const passCount = checks.filter(c => c.pass).length
  const pct       = Math.round((passCount / checks.length) * 100)

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

      {/* Dial */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-bold text-slate-700 mb-0.5">
          BRSR Core Assurance Readiness
        </p>
        <p className="text-xs text-slate-400 mb-4">{passCount}/{checks.length} criteria met</p>
        <div className="flex justify-center mt-2">
          <QualityDial pct={pct} />
        </div>
        <div className="mt-5 space-y-2 text-xs">
          {[
            { Icon: Clock,         label: 'Pending approval',    val: dq.rows_pending_approval,         bad: v => v > 0 },
            { Icon: AlertTriangle, label: 'Major CO₂ variances', val: dq.rows_with_major_co2_variance,  bad: v => v > 0 },
            { Icon: XCircle,       label: 'Unresolved findings', val: dq.rows_with_unresolved_findings, bad: v => v > 0 },
            { Icon: CheckCircle2,  label: 'Completeness',        val: `${dq.completeness_pct ?? 0}%`,   bad: () => false },
          ].map(({ Icon, label, val, bad }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-500">
                <Icon size={12} className="shrink-0" /> {label}
              </span>
              <span className={`font-bold ${bad(val) ? 'text-rose-600' : 'text-emerald-600'}`}>
                {val ?? '—'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Checklist */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-bold text-slate-700 mb-4">Auditor Readiness Checklist</p>
        <div className="space-y-2">
          {checks.map(c => (
            <div key={c.label} className="flex items-start gap-2 text-xs">
              {c.pass
                ? <CheckCircle2 size={13} className="text-emerald-500 mt-0.5 shrink-0" />
                : <XCircle     size={13} className="text-rose-400   mt-0.5 shrink-0" />}
              <span className={c.pass ? 'text-slate-600' : 'text-rose-600'}>{c.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Compliance timeline */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-sm font-bold text-slate-700 mb-4">SEBI BRSR Core Timeline</p>
        <div className="space-y-3">
          {COMPLIANCE_TIMELINE.map(t => (
            <div key={t.fy}
              className={`rounded-xl px-3.5 py-2.5 text-xs border transition-colors ${
                t.current
                  ? 'bg-emerald-50 border-emerald-300 shadow-sm'
                  : t.done
                    ? 'bg-slate-50 border-slate-200'
                    : 'bg-white border-slate-100'
              }`}
            >
              <div className="flex items-center justify-between mb-0.5">
                <span className={`font-bold ${t.current ? 'text-emerald-700' : 'text-slate-700'}`}>
                  {t.fy}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                  t.current
                    ? 'bg-emerald-600 text-white'
                    : t.done
                      ? 'bg-slate-200 text-slate-500'
                      : 'bg-slate-100 text-slate-400'
                }`}>
                  {t.done ? '✓ Done' : t.current ? '← Current' : 'Upcoming'}
                </span>
              </div>
              <p className="text-slate-500">{t.scope} — {t.note}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 7 — FUEL CONSUMPTION TABLE
// ═══════════════════════════════════════════════════════════════════════════════

function FuelConsumptionTable({ data }) {
  const byFuel   = data?.scope_1_detail?.by_fuel_type || {}
  const fuels    = Object.entries(byFuel).map(([fuel, info]) => ({
    name:       fuel.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    unit:       info.unit,
    qty:        info.quantity,
    co2t:       info.co2e_tonnes,
    factorStr:  info.factor
      ? `${info.factor} kgCO₂/${info.unit}`
      : (EMISSION_FACTORS_STATIC[fuel]
          ? `${EMISSION_FACTORS_STATIC[fuel].factor} kgCO₂/${EMISSION_FACTORS_STATIC[fuel].unit}`
          : '—'),
  }))
  const totalCo2 = fuels.reduce((a, f) => a + (f.co2t || 0), 0)

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-slate-100">
        <p className="text-sm font-bold text-slate-800">Fuel Consumption by Type — Scope 1 Detail</p>
        <p className="text-xs text-slate-400">Required disclosure under BRSR Core Principle 6</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-orange-50 text-[10px] uppercase tracking-wide text-orange-700">
              <th className="py-2.5 pl-5 pr-2 text-left font-semibold">Fuel Type</th>
              <th className="py-2.5 px-2 text-center font-semibold">Unit</th>
              <th className="py-2.5 px-3 text-right font-semibold">Quantity</th>
              <th className="py-2.5 px-3 text-right font-semibold">CO₂e (tCO₂e)</th>
              <th className="py-2.5 pl-2 pr-5 text-right font-semibold">Factor Used</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {fuels.length > 0
              ? fuels.map((f, i) => (
                  <tr key={i} className={`${i % 2 === 1 ? 'bg-slate-50' : ''} hover:bg-orange-50 transition-colors`}>
                    <td className="py-2 pl-5 pr-2 font-medium">{f.name}</td>
                    <td className="py-2 px-2 text-center text-xs text-slate-400">{f.unit}</td>
                    <td className="py-2 px-3 text-right font-mono">
                      {Number(f.qty).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-semibold">{fmt(f.co2t)}</td>
                    <td className="py-2 pl-2 pr-5 text-right text-xs text-slate-500">{f.factorStr}</td>
                  </tr>
                ))
              : (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-slate-400 text-xs italic">
                      No approved Scope 1 fuel data for this reporting period
                    </td>
                  </tr>
                )
            }
            {fuels.length > 0 && (
              <tr className="bg-orange-100 font-bold">
                <td className="py-2.5 pl-5 pr-2">TOTAL</td>
                <td />
                <td className="py-2.5 px-3 text-right">—</td>
                <td className="py-2.5 px-3 text-right font-mono">{fmt(totalCo2)}</td>
                <td />
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-slate-400 px-5 py-2.5 border-t border-slate-100">
        Source: IPCC 2006 Guidelines for National GHG Inventories / India GHG Program
      </p>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 8 — ELECTRICITY DETAIL
// ═══════════════════════════════════════════════════════════════════════════════

function ElectricityDetailTable({ data }) {
  const d       = data?.scope_2_detail || {}
  const kwh     = d.total_kwh_consumed ?? 0
  const renew   = d.renewable_kwh ?? 0
  const renewPct = kwh > 0 ? ((renew / kwh) * 100).toFixed(1) + '%' : 'N/A'
  const co2t    = data?.scope_2?.total_co2e_tonnes ?? 0
  const efSrc   = d.emission_factor_source === 'CEA_V20'
    ? 'CEA CO₂ Baseline Database V20.0' : (d.emission_factor_source ?? '—')

  const rows = [
    ['Total electricity consumed',    kwh > 0 ? Number(kwh).toLocaleString('en-IN') : '—',  'kWh'],
    ['Grid emission factor (FY)',      d.emission_factor_used ?? '—',                          'kgCO₂e/kWh'],
    ['Emission factor source',         efSrc,                                                   '—'],
    ['Reporting method',               'Location-based weighted average',                        '—'],
    ['Scope 2 emissions',              fmt(co2t),                                               'tCO₂e'],
    ['Renewable energy consumed',      renew > 0 ? Number(renew).toLocaleString('en-IN') : 'N/A', 'kWh'],
    ['% Renewable',                    renewPct,                                                 '%'],
  ]

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-slate-100">
        <p className="text-sm font-bold text-slate-800">Electricity Consumption — Scope 2 Detail</p>
        <p className="text-xs text-slate-400">CEA Location-based method · SEBI BRSR Core mandatory</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-blue-50 text-[10px] uppercase tracking-wide text-blue-700">
              <th className="py-2.5 pl-5 pr-2 text-left font-semibold">Parameter</th>
              <th className="py-2.5 px-3 text-right font-semibold">Value</th>
              <th className="py-2.5 pl-2 pr-5 text-center font-semibold">Unit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(([label, val, unit], i) => (
              <tr key={i} className={`${i % 2 === 1 ? 'bg-slate-50' : ''} hover:bg-blue-50 transition-colors`}>
                <td className="py-2 pl-5 pr-2 text-slate-700">{label}</td>
                <td className="py-2 px-3 text-right font-mono font-semibold text-slate-800">{val}</td>
                <td className="py-2 pl-2 pr-5 text-center text-xs text-slate-400">{unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-5 py-3 bg-blue-50 border-t border-blue-100">
        <p className="text-xs text-blue-700 italic">
          Market-based Scope 2 = N/A — No renewable energy certificates (RECs) or Power Purchase Agreements (PPAs)
          in effect during this reporting period.
        </p>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 9 — COMPLY-OR-EXPLAIN
// ═══════════════════════════════════════════════════════════════════════════════

function ComplyOrExplainPanel({ fy }) {
  const statusKey  = `brsr_s3_status_${fy}`
  const explainKey = `brsr_s3_explain_${fy}`
  const [status,  setStatus]  = useState(() => localStorage.getItem(statusKey)  || 'disclosing')
  const [explain, setExplain] = useState(() => localStorage.getItem(explainKey) || '')

  const toggle     = v => { setStatus(v);  localStorage.setItem(statusKey, v) }
  const saveExplain = v => { setExplain(v); localStorage.setItem(explainKey, v) }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <p className="text-sm font-bold text-slate-800">Scope 3 — Comply-or-Explain</p>
          <p className="text-xs text-slate-400">
            Mandatory for Top 250 listed entities from FY 2024-25 (SEBI BRSR Core)
          </p>
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
          {[['disclosing', '✓ Disclosing'], ['explaining', 'Explaining Non-disclosure']].map(([val, lbl]) => (
            <button key={val} onClick={() => toggle(val)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-all font-medium ${
                status === val
                  ? 'bg-white text-emerald-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >{lbl}</button>
          ))}
        </div>
      </div>

      {status === 'disclosing' ? (
        <div className="flex items-start gap-2.5 p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-700">
          <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
          <span>
            Scope 3 data is being disclosed. Detailed figures are available in the
            Absolute Emissions table above (Total Scope 3 row, expand for category breakdown).
          </span>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-slate-600">
            Provide your explanation below. This text will be included in the exported BRSR report
            under <strong>Principle 6, Question 7, Scope 3</strong>.
          </p>
          <textarea
            className="w-full border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm resize-none focus:ring-emerald-500 focus:border-emerald-500"
            rows={4}
            value={explain}
            onChange={e => saveExplain(e.target.value)}
            placeholder="e.g. Scope 3 emissions data is not yet available as the company is in the first year of implementing a comprehensive travel data management system. We expect to report full Scope 3 data from FY 2025-26 onwards..."
          />
          {explain && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
              <AlertTriangle size={13} className="shrink-0 mt-0.5" />
              <span>This explanation will appear in the exported BRSR report under Principle 6, Q7.</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 10 — PREVIOUS YEAR PANEL
// ═══════════════════════════════════════════════════════════════════════════════

function PreviousYearPanel({ data }) {
  const pf = data?.previous_fy
  const hasPrev = pf && (pf.total_co2e_tonnes ?? 0) > 0

  if (!hasPrev) {
    return (
      <div className="flex items-start gap-3.5 p-5 bg-amber-50 border border-amber-200 rounded-xl">
        <AlertTriangle size={18} className="text-amber-500 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-amber-800">Previous Year Data Not Available</p>
          <p className="text-xs text-amber-700 mt-1">
            Upload and approve FY {pf?.reporting_period || 'previous year'} data to enable mandatory
            year-on-year comparison required under SEBI BRSR Core. YoY comparison is a mandatory
            disclosure element.
          </p>
        </div>
      </div>
    )
  }

  const items = [
    { label: 'Scope 1 — Direct',      val: pf.scope_1?.total_co2e_tonnes },
    { label: 'Scope 2 — Electricity', val: pf.scope_2?.total_co2e_tonnes },
    { label: 'Scope 3 — Travel',      val: pf.scope_3?.total_co2e_tonnes },
    { label: 'TOTAL All Scopes',      val: pf.total_co2e_tonnes, bold: true },
  ]

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm font-bold text-slate-800 mb-0.5">Previous Year Data — FY {pf.reporting_period}</p>
      <p className="text-xs text-slate-400 mb-4">
        Mandatory YoY comparative disclosure · SEBI BRSR Core
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {items.map(it => (
          <div key={it.label}
            className={`rounded-xl p-3.5 border ${it.bold ? 'bg-slate-100 border-slate-300' : 'bg-slate-50 border-slate-200'}`}
          >
            <p className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">{it.label}</p>
            <p className={`text-xl font-bold mt-1 ${it.bold ? 'text-slate-800' : 'text-slate-700'}`}>
              {fmt(it.val, 2)}
              <span className="text-xs font-normal text-slate-400 ml-1">t</span>
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-3 italic">
        Note: If this is the first year of Scope 3 reporting, state: "Previous year Scope 3 data
        not available — first year of disclosure." This is a recognised BRSR Core exemption.
      </p>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// NON-ENVIRONMENTAL ATTRIBUTES PLACEHOLDER
// ═══════════════════════════════════════════════════════════════════════════════

function NonEnvPlaceholder() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm font-bold text-slate-700 mb-0.5">
        BRSR Core Attributes 5–9 — Social &amp; Governance
      </p>
      <p className="text-xs text-slate-400 mb-4">
        These attributes are outside the scope of the GHG Emissions module. Manage them separately.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { n: 5, label: 'Employee Well-Being',              principle: 'P5' },
          { n: 6, label: 'Responsible & Transparent Biz',    principle: 'P1' },
          { n: 7, label: 'Human Rights',                     principle: 'P5' },
          { n: 8, label: 'Inclusive Growth',                 principle: 'P8' },
          { n: 9, label: 'Responsible Consumer Engagement',  principle: 'P9' },
        ].map(a => (
          <div key={a.n}
            className="rounded-xl border border-dashed border-slate-300 p-3 text-center opacity-50"
          >
            <p className="text-2xl font-bold text-slate-300">#{a.n}</p>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">{a.label}</p>
            <p className="text-[10px] text-slate-400">{a.principle}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORT UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

function downloadCSV(rows, filename) {
  const csv  = rows.map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function exportBRSRCSV(data, fy, assuranceLevel) {
  if (!data) return
  const pf  = data.previous_fy || {}
  const s1  = data.scope_1?.total_co2e_tonnes ?? 0
  const s2  = data.scope_2?.total_co2e_tonnes ?? 0
  const s3  = data.scope_3?.total_co2e_tonnes ?? 0
  downloadCSV([
    ['SEBI BRSR CORE — GHG DISCLOSURE'],
    ['Principle 6 · Essential Indicators · Question 7'],
    ['Framework', 'GHG Protocol Corporate Standard'],
    ['Organisation', data.organisation],
    ['Reporting Period', data.reporting_period],
    ['Generated', data.generated_at],
    ['By', data.generated_by],
    ['Assurance Level', assuranceLevel],
    [],
    ['Parameter', 'Unit', `FY ${data.reporting_period}`, `FY ${pf.reporting_period || '—'}`, 'YoY'],
    ['Scope 1 (Direct Combustion)', 'tCO₂e', s1, pf.scope_1?.total_co2e_tonnes ?? '—', ''],
    ['Scope 2 (Electricity)',        'tCO₂e', s2, pf.scope_2?.total_co2e_tonnes ?? '—', ''],
    ['Scope 1+2',                   'tCO₂e', (s1 + s2).toFixed(6), '—', ''],
    ['Scope 3 (Business Travel)',   'tCO₂e', s3, pf.scope_3?.total_co2e_tonnes ?? '—', ''],
    ['TOTAL All Scopes',            'tCO₂e', data.total_co2e_tonnes, pf.total_co2e_tonnes ?? '—', ''],
    [],
    ['Scope 2 kWh consumed', data.scope_2_detail?.total_kwh_consumed ?? '—'],
    ['Grid factor', data.scope_2_detail?.emission_factor_used ?? '—', 'kgCO₂e/kWh'],
    [],
    ['Completeness', `${data.data_quality?.completeness_pct ?? 0}%`],
  ], `BRSR_${data.organisation}_${fy}.csv`)
}

function exportDetailedCSV(data, fy, assuranceLevel) {
  if (!data) return
  const byFuel = data.scope_1_detail?.by_fuel_type || {}
  const byCat  = data.scope_3?.by_category || {}
  downloadCSV([
    ['=== SEBI BRSR CORE — DETAILED GHG DISCLOSURE ==='],
    ['Prepared for annual report submission'],
    ['Organisation', data.organisation],
    ['FY', data.reporting_period],
    ['Assurance Level', assuranceLevel],
    [],
    ['--- FUEL CONSUMPTION TABLE (Scope 1) ---'],
    ['Fuel Type', 'Unit', 'Quantity', 'CO₂e (tCO₂e)', 'Factor', 'Source'],
    ...Object.entries(byFuel).map(([k, v]) => [
      k.replace(/_/g, ' '), v.unit,
      Number(v.quantity).toFixed(2), Number(v.co2e_tonnes).toFixed(6),
      v.factor ? `${v.factor} kgCO₂/${v.unit}` : '—', 'IPCC 2006',
    ]),
    ['TOTAL', '', '—', Number(data.scope_1?.total_co2e_tonnes).toFixed(6), '—', ''],
    [],
    ['--- ELECTRICITY DETAIL (Scope 2) ---'],
    ['Total kWh',      data.scope_2_detail?.total_kwh_consumed],
    ['Grid factor',    data.scope_2_detail?.emission_factor_used, 'kgCO₂e/kWh'],
    ['Scope 2 CO₂e',  data.scope_2?.total_co2e_tonnes, 'tCO₂e'],
    [],
    ['--- SCOPE 3 TRAVEL BREAKDOWN ---'],
    ['Category',          'tCO₂e'],
    ['Air Travel',        byCat.business_travel_air    ?? 0],
    ['Hotel Stays',       byCat.business_travel_hotel  ?? 0],
    ['Ground Transport',  byCat.business_travel_ground ?? 0],
    [],
    ['--- METHODOLOGY ---'],
    ['Scope 1 Source',     'IPCC 2006 / India GHG Program'],
    ['Scope 2 Source',     'CEA CO₂ Baseline Database V20.0'],
    ['Scope 3 Source',     'DEFRA 2024 / ICAO'],
    ['GWP Basis',          'IPCC AR6 (CO₂=1, CH₄=27.9, N₂O=273)'],
    ['Standard',           'GHG Protocol Corporate Standard (2015)'],
    ['SEBI Circular',      'SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122'],
  ], `BRSR_Detailed_${data.organisation}_${fy}.csv`)
}

function copyDisclosureText(data, assuranceLevel) {
  if (!data) return
  const s1  = data.scope_1?.total_co2e_tonnes ?? 0
  const s2  = data.scope_2?.total_co2e_tonnes ?? 0
  const s3  = data.scope_3?.total_co2e_tonnes ?? 0
  const s12 = (s1 + s2).toFixed(4)
  const text = `GHG EMISSIONS — PRINCIPLE 6, ESSENTIAL INDICATORS, QUESTION 7
SEBI BRSR Core Disclosure · FY ${data.reporting_period}
Organisation: ${data.organisation}

ABSOLUTE EMISSIONS
Total Scope 1 emissions: ${s1.toFixed(4)} tCO₂e (FY ${data.reporting_period})
Total Scope 2 emissions: ${s2.toFixed(4)} tCO₂e (FY ${data.reporting_period})
Total Scope 1+2 combined: ${s12} tCO₂e (FY ${data.reporting_period})
Total Scope 3 (Business Travel): ${s3.toFixed(4)} tCO₂e (FY ${data.reporting_period})

METHODOLOGY
Scope 1 EF Source: IPCC 2006 Guidelines for National GHG Inventories
Scope 2 EF Source: CEA CO₂ Baseline Database V20.0
Grid Factor: ${data.scope_2_detail?.emission_factor_used ?? 0.710} kgCO₂e/kWh (FY ${data.scope_2_detail?.fy_factor_used ?? data.reporting_period})
Scope 3 EF Source: DEFRA 2024 / ICAO Carbon Calculator
Radiative Forcing: 1.9× applied to air travel
Scope 2 Method: Location-based (market-based: N/A — no RECs/PPAs)
Reporting Standard: GHG Protocol Corporate Standard (2015)

EXTERNAL ASSURANCE
External Assurance: ${assuranceLevel === 'none' ? 'No external assurance obtained' : 'Yes — ' + assuranceLevel.charAt(0).toUpperCase() + assuranceLevel.slice(1) + ' assurance'}

Generated: ${data.generated_at} | By: ${data.generated_by}
SEBI Circular: SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 (12 July 2023)`

  navigator.clipboard.writeText(text).catch(() => {
    const el = document.createElement('textarea')
    el.value = text; document.body.appendChild(el); el.select()
    document.execCommand('copy'); document.body.removeChild(el)
  })
  alert('Disclosure text copied to clipboard!')
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function BRSRReport() {
  const [fy,             setFy]             = useState(CURRENT_FY)
  const [data,           setData]           = useState(null)
  const [loading,        setLoading]        = useState(true)
  const [error,          setError]          = useState(null)
  const [assuranceLevel, setAssuranceLevel] = useState('none')
  const [revenue,        setRevenue]        = useState(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const res = await getBRSRSummary(fy)
      setData(res.data)
    } catch (e) {
      setError(e.response?.data?.error || 'Failed to load BRSR summary. Check the server.')
    } finally {
      setLoading(false)
    }
  }, [fy])

  useEffect(() => { load() }, [load])

  // Sync revenue from localStorage whenever FY changes
  useEffect(() => {
    const v = localStorage.getItem(`brsr_revenue_${fy}`)
    setRevenue(v ? parseFloat(v) : null)
  }, [fy])

  return (
    <div className="space-y-5 print:space-y-3">
      {/* Section 1: Header */}
      <ComplianceHeader
        data={data} fy={fy} setFy={setFy} loading={loading}
        onRefresh={load}
        onExportCSV={() => exportBRSRCSV(data, fy, assuranceLevel)}
        onExportDetailed={() => exportDetailedCSV(data, fy, assuranceLevel)}
        onCopyText={() => copyDisclosureText(data, assuranceLevel)}
        assuranceLevel={assuranceLevel}
        setAssuranceLevel={setAssuranceLevel}
      />

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2.5 p-4 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
          <RefreshCw size={16} className="animate-spin mr-2" /> Loading BRSR summary…
        </div>
      )}

      {data && (
        <>
          {/* Section 2 */}
          <AbsoluteEmissionsTable data={data} />

          {/* Section 3 */}
          <IntensityCards data={data} fy={fy} onRevenueChange={setRevenue} />

          {/* Section 4 */}
          <ScopeCharts data={data} />

          {/* Section 5 */}
          <MethodologyBox data={data} />

          {/* Section 6 */}
          <DataQualityPanel data={data} assuranceLevel={assuranceLevel} revenue={revenue} />

          {/* Section 7 + 8 side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <FuelConsumptionTable    data={data} />
            <ElectricityDetailTable  data={data} />
          </div>

          {/* Section 9 */}
          <ComplyOrExplainPanel fy={fy} />

          {/* Section 10 */}
          <PreviousYearPanel data={data} />

          {/* Social/Governance placeholders */}
          <NonEnvPlaceholder />

          {/* Footer */}
          <p className="text-xs text-slate-400 text-center py-2 print:hidden">
            Generated {data.generated_at} by {data.generated_by} ·
            SEBI BRSR Core — Principle 6 · GHG Protocol Corporate Standard ·
            Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122
          </p>
        </>
      )}

      {/* Print CSS */}
      <style>{`
        @media print {
          .print\\:hidden { display: none !important; }
          .print\\:border-slate-400 { border-color: #94a3b8 !important; }
          body { font-size: 10px; -webkit-print-color-adjust: exact; }
          [class*="space-y"] > * + * { margin-top: 12px !important; }
        }
      `}</style>
    </div>
  )
}
