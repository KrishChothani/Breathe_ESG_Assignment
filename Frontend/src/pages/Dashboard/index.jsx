/**
 * src/pages/Dashboard/index.jsx
 * Analytics Dashboard — stat cards + 6 ESG charts with global time-range control
 */
import { useState, useEffect } from 'react'
import { getDashboardStats } from '../../api/emissions'
import { formatCO2e } from '../../utils/chartFormatters'

// Chart components
import EmissionsTrendChart    from '../../components/Charts/EmissionsTrendChart'
import ScopeDonutChart        from '../../components/Charts/ScopeDonutChart'
import EmissionsBySourceChart from '../../components/Charts/EmissionsBySourceChart'
import EmissionsByPlantChart  from '../../components/Charts/EmissionsByPlantChart'
import IngestionActivityChart from '../../components/Charts/IngestionActivityChart'
import ForecastPanel        from '../../components/Forecast/ForecastPanel'
import ReviewPipelineChart    from '../../components/Charts/ReviewPipelineChart'
import TimeRangeSelector      from '../../components/Charts/TimeRangeSelector'
import { useDashboardStore }  from '../../store/dashboardStore'

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon, accent = 'emerald' }) {
  const accentMap = {
    emerald: { dot: 'bg-emerald-500', sub: 'text-emerald-600' },
    amber:   { dot: 'bg-amber-400',   sub: 'text-amber-600'   },
    blue:    { dot: 'bg-blue-500',    sub: 'text-blue-600'    },
  }
  const a = accentMap[accent] ?? accentMap.emerald
  return (
    <div className="card flex flex-col gap-3 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider leading-tight">
          {label}
        </p>
        <span className="text-xl">{icon}</span>
      </div>
      <p className="text-3xl font-bold text-slate-800 leading-none">{value}</p>
      <p className={`text-xs font-medium ${a.sub}`}>{sub}</p>
    </div>
  )
}

// ── Source cards (Ingestion Summary) ─────────────────────────────────────────

function StatPill({ label, value, color }) {
  const colors = {
    slate: 'bg-slate-100 text-slate-700',
    green: 'bg-emerald-100 text-emerald-700',
    rose:  'bg-rose-100 text-rose-700',
    amber: 'bg-amber-100 text-amber-700',
  }
  return (
    <div className={`rounded-lg px-3 py-2 text-center ${colors[color] ?? colors.slate}`}>
      <p className="text-lg font-bold leading-none">{value}</p>
      <p className="text-xs mt-0.5 font-medium opacity-80">{label}</p>
    </div>
  )
}

function SourceCard({ source, label, total, parsed, failed, flagged }) {
  const pct  = total > 0 ? Math.round((parsed / total) * 100) : 0
  const icon = source === 'SAP' ? '📦' : source === 'UTILITY' ? '⚡' : '✈️'
  return (
    <div className="card hover:border-emerald-300 transition-colors group">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-2xl mb-1">{icon}</div>
          <h3 className="text-sm font-semibold text-slate-800">{label}</h3>
          <p className="text-xs text-slate-400 mt-0.5">{total} rows ingested</p>
        </div>
        <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
          {pct}% parsed
        </span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <StatPill label="Parsed"  value={parsed}  color="green" />
        <StatPill label="Flagged" value={flagged}  color="amber" />
        <StatPill label="Failed"  value={failed}   color={failed > 0 ? 'rose' : 'slate'} />
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

const GLOBAL_RANGE_OPTIONS = ['30d', '90d', '6m', '1y', 'all']

function currentFY() {
  const today = new Date()
  const month = today.getMonth() + 1 // 1-indexed
  const year  = today.getFullYear()
  const fyStart = month >= 4 ? year : year - 1
  const fyEnd   = String(fyStart + 1).slice(-2)
  return `${fyStart}-${fyEnd}`
}

export default function Dashboard() {
  const { stats, loadingStats, globalRange, setGlobalRange, fetchDashboardData } = useDashboardStore()

  useEffect(() => {
    // Only fetch on first mount, Zustand setGlobalRange handles refetching when range changes
    fetchDashboardData()
  }, [])

  return (
    <div className="space-y-6">

      {/* ── Hero stat cards ─────────────────────────────────────────────── */}
      {loadingStats ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse">
          {[1, 2, 3].map(i => (
            <div key={i} className="card h-28 bg-slate-50" />
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            label="Total Rows Ingested"
            value={stats.total_rows?.toLocaleString() ?? '—'}
            sub="across all sources"
            icon="📥"
            accent="emerald"
          />
          <StatCard
            label="Total CO₂e Emissions"
            value={formatCO2e(stats.total_co2e)}
            sub="normalised estimate"
            icon="🌍"
            accent="blue"
          />
          <StatCard
            label="Pending Review"
            value={stats.pending_review?.toLocaleString() ?? '—'}
            sub="rows awaiting analyst action"
            icon="🔍"
            accent="amber"
          />
        </div>
      ) : (
        <div className="card text-center text-rose-500 py-6">Failed to load stats</div>
      )}
      {stats?.sources && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Ingestion Summary by Source</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {stats.sources.map((s) => (
              <SourceCard key={s.source} {...s} />
            ))}
          </div>
        </div>
      )}

      {/* ── Global time-range selector ───────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
          Reporting Period:
        </span>
        <TimeRangeSelector
          value={globalRange}
          onChange={setGlobalRange}
          options={GLOBAL_RANGE_OPTIONS}
        />
      </div>

      {/* ── Row 1: Emissions trend (full width) ─────────────────────────── */}
      <EmissionsTrendChart globalRange={globalRange} />

      {/* ── Row 2: Donut 40% + Stacked bar 60% ─────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="md:col-span-2">
          <ScopeDonutChart globalRange={globalRange} />
        </div>
        <div className="md:col-span-3">
          <EmissionsBySourceChart globalRange={globalRange} />
        </div>
      </div>

      {/* ── Row 3: Plant chart 60% + Review pipeline 40% ───────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {/* Hidden on mobile per spec */}
        <div className="md:col-span-3 hidden md:block">
          <EmissionsByPlantChart globalRange={globalRange} />
        </div>
        <div className="md:col-span-2">
          <ReviewPipelineChart />
        </div>
      </div>

      {/* ── Row 4: Ingestion activity (full width) ──────────────────────── */}
      <IngestionActivityChart />

      {/* ── Row 5: Predictive Forecast Panel ───────────────────────────────── */}
      <ForecastPanel fy={currentFY()} />

      {/* ── Ingestion summary by source ─────────────────────────────────── */}
      {/* {stats?.sources && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Ingestion Summary by Source</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {stats.sources.map((s) => (
              <SourceCard key={s.source} {...s} />
            ))}
          </div>
        </div>
      )} */}

      {/* ── Recent Uploads section ───────────────────────────────────────── */}
      {/* <div className="card">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Recent Uploads</h2>
        <p className="text-sm text-slate-400 text-center py-8">
          No recent uploads.{' '}
          <a href="/upload" className="text-emerald-600 hover:underline">
            Upload data →
          </a>
        </p>
      </div> */}
    </div>
  )
}
