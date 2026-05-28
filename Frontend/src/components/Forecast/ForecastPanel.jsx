/**
 * src/components/Forecast/ForecastPanel.jsx
 *
 * Main container for the Predictive Forecasting feature.
 *
 * Features:
 *   - FY selector (button group): shows available FYs (current + 2 prior)
 *   - Instant display for already-fetched FYs (per-FY cache in store)
 *   - Past FYs (12/12 months elapsed) → all actuals, no forecast projection
 *   - Current FY → actuals + forward forecast + What-If controls
 *   - Nowcast badge for Scope 2 billing-lag estimation
 */
import { useEffect } from 'react'
import { useForecastStore, getAvailableFYs } from '../../store/forecastStore'
import ForecastTimelineChart from './ForecastTimelineChart'
import ForecastSummaryTable  from './ForecastSummaryTable'
import WhatIfControls        from './WhatIfControls'

// ── FY Selector ────────────────────────────────────────────────────────────────
function FYSelector({ fys, selected, onSelect, fyCache, loading }) {
  return (
    <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
      {fys.map(fy => {
        const isCurrent  = fy === fys[fys.length - 1]
        const isCached   = !!fyCache[fy]
        const isSelected = fy === selected

        return (
          <button
            key={fy}
            onClick={() => !isSelected && onSelect(fy)}
            disabled={loading && !isCached}
            className={[
              'relative px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150',
              isSelected
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50',
              loading && !isCached ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
            ].join(' ')}
          >
            FY {fy}
            {isCurrent && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full border border-white" />
            )}
            {isCached && !isSelected && (
              <span className="ml-1 text-[9px] text-slate-400">✓</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ── Past-FY banner ─────────────────────────────────────────────────────────────
function PastFYBanner({ fy }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-500 flex items-center gap-2">
      <span className="text-base">📋</span>
      <span>
        <strong>FY {fy}</strong> is complete — showing all 12 months of recorded actuals.
        No forecast projection is generated for a fully elapsed financial year.
      </span>
    </div>
  )
}

// ── Staleness / Nowcast badges ─────────────────────────────────────────────────
function StalenessNote({ generatedAt }) {
  if (!generatedAt) return null
  return (
    <span className="text-[10px] text-slate-400 bg-slate-50 border border-slate-200 rounded px-1.5 py-0.5">
      as of {generatedAt}
    </span>
  )
}

function NowcastBadge({ rmsfe }) {
  if (rmsfe == null) return null
  return (
    <span className="text-[10px] text-sky-700 bg-sky-50 border border-sky-200 rounded px-1.5 py-0.5">
      Nowcast active · RMSFE {Number(rmsfe).toFixed(2)} t
    </span>
  )
}

// ── Main Panel ─────────────────────────────────────────────────────────────────
export default function ForecastPanel({ fy: defaultFY }) {
  const {
    selectedFY, forecastData, loading, error,
    fyCache, fetchForecast, selectFY,
    activityDrivers,
  } = useForecastStore()

  const availableFYs = getAvailableFYs(defaultFY)
  const activeFY     = selectedFY ?? defaultFY

  // Initial load
  useEffect(() => {
    if (!selectedFY) {
      selectFY(defaultFY)
    }
  }, [defaultFY])

  const d = forecastData

  // A fully-elapsed FY has no future months to forecast
  const isPastFY   = d && d.months_remaining === 0
  const isFutureFY = d && d.months_elapsed === 0

  const showWhatIf    = !isPastFY && !isFutureFY && d && d.error !== 'INSUFFICIENT_DATA'
  const showTimeline  = d && d.error !== 'INSUFFICIENT_DATA' && d.monthly_timeline?.length

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4 border-b border-slate-100">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            📈 CO₂e Emissions Forecast
            {loading && (
              <span className="inline-block w-3.5 h-3.5 border-2 border-slate-300 border-t-slate-600
                               rounded-full animate-spin" />
            )}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {d && !isFutureFY
              ? isPastFY
                ? `FY ${activeFY} — 12/12 months · Full actuals`
                : `${d.months_elapsed} month${d.months_elapsed !== 1 ? 's' : ''} of actuals · ${d.months_remaining} projected · FY ${activeFY}`
              : 'Select a financial year'}
          </p>
        </div>

        {/* Right side: FY selector + badges */}
        <div className="flex flex-wrap items-center gap-2">
          <StalenessNote generatedAt={d?.generated_at} />
          <NowcastBadge rmsfe={d?.nowcast_quality?.rmsfe_scope2} />
          <FYSelector
            fys={availableFYs}
            selected={activeFY}
            onSelect={selectFY}
            fyCache={fyCache}
            loading={loading}
          />
        </div>
      </div>

      {/* ── Error ───────────────────────────────────────────────────────────── */}
      {error && (
        <div className="mx-5 mt-4 bg-rose-50 border border-rose-200 rounded-lg px-4 py-3 text-xs text-rose-700">
          ⚠️ {error}
        </div>
      )}

      {/* ── Insufficient data ─────────────────────────────────────────────── */}
      {!loading && d?.error === 'INSUFFICIENT_DATA' && (
        <div className="mx-5 my-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-700">
          ⏳ {d.message ?? `No approved data found for FY ${activeFY}.`}
        </div>
      )}

      {/* ── Loading skeleton ─────────────────────────────────────────────── */}
      {loading && !d && (
        <div className="p-5 animate-pulse space-y-3">
          <div className="h-10 w-48 bg-slate-100 rounded-lg" />
          <div className="h-52 bg-slate-100 rounded-xl" />
          <div className="h-28 bg-slate-50 rounded-xl" />
        </div>
      )}

      {/* ── Content ───────────────────────────────────────────────────────── */}
      {!loading && showTimeline && (
        <div className="p-5 space-y-5">

          {/* Past FY notice */}
          {isPastFY && <PastFYBanner fy={activeFY} />}

          {/* Chart + Summary table */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Timeline — 2/3 */}
            <div className="lg:col-span-2">
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {isPastFY ? '12-Month Actual Emissions' : '12-Month Emission Timeline'}
              </p>
              <ForecastTimelineChart
                monthlyTimeline={d.monthly_timeline}
                monthsElapsed={d.months_elapsed}
              />
              {/* Legend */}
              <div className="flex flex-wrap items-center gap-4 mt-2 text-[10px] text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-4 h-[2px] bg-slate-800 inline-block rounded" />
                  Actual
                </span>
                {!isPastFY && (
                  <>
                    <span className="flex items-center gap-1.5">
                      <span className="w-4 inline-block" style={{
                        borderTop: '2px dashed #94a3b8', marginTop: 1,
                      }} />
                      Forecast
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 bg-violet-100 border border-violet-200 inline-block rounded" />
                      90% CI
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Summary table — 1/3 */}
            <div className="lg:col-span-1">
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {isPastFY ? 'Final Actuals by Scope' : 'YTD · YTG · Run Rate'}
              </p>
              <ForecastSummaryTable
                ytdActuals={d.ytd_actuals}
                ytgForecast={isPastFY ? null : d.ytg_forecast}
                annualizedRunRate={isPastFY ? null : d.annualized_run_rate}
                monthsElapsed={d.months_elapsed}
                isPastFY={isPastFY}
              />
            </div>
          </div>

          {/* What-If sliders — current FY only */}
          {showWhatIf && <WhatIfControls loading={loading} />}
        </div>
      )}
    </div>
  )
}
